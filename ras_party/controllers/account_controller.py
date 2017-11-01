import uuid

from flask import current_app
from itsdangerous import SignatureExpired, BadSignature, BadData
from ras_common_utils.ras_error.ras_error import RasError, RasNotifyError
from sqlalchemy import orm
from structlog import get_logger

from ras_party.clients.oauth_client import OauthClient
from ras_party.controllers.notify_gateway import NotifyGateway
from ras_party.controllers.queries import query_business_by_party_uuid, query_respondent_by_email, \
    query_respondent_by_party_uuid
from ras_party.controllers.validate import Validator, IsUuid, Exists
from ras_party.models.models import Respondent, RespondentStatus, BusinessRespondent, PendingEnrolment, \
    Enrolment, EnrolmentStatus
from ras_party.support.public_website import PublicWebsite
from ras_party.support.requests_wrapper import Requests
from ras_party.support.session_decorator import with_db_session
from ras_party.support.transactional import transactional
from ras_party.support.util import build_url
from ras_party.support.verification import decode_email_token

log = get_logger()

NO_RESPONDENT_FOR_PARTY_ID = 'There is no respondent with that party ID '
EMAIL_VERIFICATION_SENT = 'A new verification email has been sent'


@transactional
@with_db_session
def post_respondent(party, tran, session):
    """
    This function is quite complicated, as it performs a number of steps to complete a new respondent enrolment:
    1. Validate the enrolment code and email address
    2. Register the respondent as a new user with the remote OAuth2 service.
    3. Lookup the case context from the case service
    4. Lookup the collection exercise from the collection exercise service
    5. Lookup the survey from the survey service
    6. Generate an email verification token, and an email verification url
    7. Invoke the email verification
    8. Update the database with the new respondent, establishing an association to the business, and an entry
       in the enrolment table (along with the survey id / survey name)
    9. Post a case event to the case service to notify that a new respondent has been created
    10. If something goes wrong after step 1, attempt to perform a compensating action to remove the OAuth2 user
       (this is currently mocked out as the OAuth2 server doesn't implement an endpoint to achieve this)
    """

    # Validation, curation and checks
    expected = ('emailAddress', 'firstName', 'lastName', 'password', 'telephone', 'enrolmentCode')

    v = Validator(Exists(*expected))
    if 'id' in party:
        # Note: there's not strictly a requirement to be able to pass in a UUID, this is currently supported to
        # aid with testing.
        log.debug("'id' in respondent post message. Adding validation rule IsUuid")
        v.add_rule(IsUuid('id'))

    if not v.validate(party):
        raise RasError(v.errors, 400)

    iac = request_iac(party['enrolmentCode'])
    if not iac.get('active'):
        raise RasError("Enrolment code is not active.", status_code=400)

    existing = query_respondent_by_email(party['emailAddress'], session)
    if existing:
        raise RasError("User with email address {} already exists.".format(party['emailAddress']), status_code=400)

    case_context = request_case(party['enrolmentCode'])
    case_id = case_context['id']
    business_id = case_context['partyId']
    collection_exercise_id = case_context['caseGroup']['collectionExerciseId']
    collection_exercise = request_collection_exercise(collection_exercise_id)

    try:
        survey_id = collection_exercise['surveyId']
        survey = request_survey(survey_id)
        survey_name = survey['longName']
    except KeyError:
        raise RasError("There is no survey bound for this user with email address: {}".format(party['emailAddress']))

    business = query_business_by_party_uuid(business_id, session)
    if not business:
        msg = "Could not locate business with id '{}' when creating business association.".format(business_id)
        raise RasError(msg, status_code=404)

    # Chain of enrolment processes
    translated_party = {
        'party_uuid': party.get('id') or str(uuid.uuid4()),
        'email_address': party['emailAddress'],
        'first_name': party['firstName'],
        'last_name': party['lastName'],
        'telephone': party['telephone'],
        'status': RespondentStatus.CREATED
    }

    try:
        #  Create the enrolment respondent-business-survey associations
        respondent = Respondent(**translated_party)
        br = BusinessRespondent(business=business, respondent=respondent)
        pending_enrolment = PendingEnrolment(case_id=case_id,
                                             respondent=respondent,
                                             business_id=business_id,
                                             survey_id=survey_id)
        Enrolment(business_respondent=br,
                  survey_id=survey_id,
                  survey_name=survey_name,
                  status=EnrolmentStatus.PENDING)
        session.add(respondent)
        session.add(pending_enrolment)

        # Notify the case service of this account being created
        post_case_event(case_id, respondent.party_uuid, "RESPONDENT_ACCOUNT_CREATED", "New respondent account created")

        _send_email_verification(respondent.party_uuid, party['emailAddress'])
    except (orm.exc.ObjectDeletedError, orm.exc.FlushError, orm.exc.StaleDataError, orm.exc.DetachedInstanceError):
        msg = "Error updating database for user id: {} ".format(party['id'])
        raise RasError(msg, status_code=500)
    except KeyError:
        msg = "Missing config keys during enrolment"
        raise RasError(msg, status_code=500)
    except Exception as e:
        msg = "Error during enrolment process {}".format(e)
        raise RasError(msg, status_code=500)

    register_user(party, tran)

    return respondent.to_respondent_dict()


@transactional
@with_db_session
def change_respondent(payload, tran, session):
    """
    Modify an existing respondent's email address, identified by their current email address.
    """
    v = Validator(Exists('email_address', 'new_email_address'))
    if not v.validate(payload):
        raise RasError(v.errors, 400)

    email_address = payload['email_address']
    new_email_address = payload['new_email_address']

    respondent = query_respondent_by_email(email_address, session)
    if not respondent:
        raise RasError("Respondent does not exist.", status_code=404)

    if new_email_address == email_address:
        return respondent.to_respondent_dict()

    respondent_with_new_email = query_respondent_by_email(new_email_address, session)
    if respondent_with_new_email:
        raise RasError("New email address already taken.", status_code=409)

    respondent.email_address = new_email_address

    oauth_response = OauthClient(current_app.config).update_account(username=email_address,
                                                                    new_username=new_email_address,
                                                                    account_verified='false')

    if oauth_response.status_code != 201:
        raise RasError("Failed to change respondent email")

    def compensate_oauth_change():
        rollback_response = OauthClient(current_app.config).update_account(username=new_email_address,
                                                                           new_username=email_address,
                                                                           account_verified='true')
        if rollback_response.status_code != 201:
            raise RasError("Failed to rollback change to repsondent email. Please investigate.")

    tran.compensate(compensate_oauth_change)

    _send_email_verification(respondent.party_uuid, respondent.email_address)

    # This ensures the log message is only written once the DB transaction is committed
    tran.on_success(
        lambda: log.info('Respondent with id {} has changed their email address'.format(respondent.party_uuid)))

    return respondent.to_respondent_dict()


@with_db_session
def verify_token(token, session):
    try:
        duration = int(current_app.config.get("EMAIL_TOKEN_EXPIRY", '86400'))
        email_address = decode_email_token(token, duration, current_app.config)
    except SignatureExpired:
        msg = "Expired email verification token {}".format(token)
        raise RasError(msg, 409)
    except (BadSignature, BadData) as e:
        msg = "Unknown email verification token {} error {}".format(token, e)
        raise RasError(msg, 404)

    respondent = query_respondent_by_email(email_address, session)
    if not respondent:
        raise RasError("Respondent does not exist.", status_code=404)

    return {'response': "Ok"}


@transactional
@with_db_session
def change_respondent_password(token, payload, tran, session):
    v = Validator(Exists('new_password'))
    if not v.validate(payload):
        raise RasError(v.errors, 400)

    try:
        duration = int(current_app.config.get("EMAIL_TOKEN_EXPIRY", '86400'))
        email_address = decode_email_token(token, duration, current_app.config)
    except SignatureExpired:
        msg = "Expired email verification token {}".format(token)
        raise RasError(msg, 409)
    except (BadSignature, BadData) as e:
        msg = "Unknown email verification token {} error {}".format(token, e)
        raise RasError(msg, 404)

    respondent = query_respondent_by_email(email_address, session)
    if not respondent:
        raise RasError("Respondent does not exist.", status_code=404)

    new_password = payload['new_password']

    oauth_response = OauthClient(current_app.config).update_account(username=email_address,
                                                                    password=new_password,
                                                                    account_verified='true')

    if oauth_response.status_code != 201:
        raise RasError("Failed to change respondent password.")

    personalisation = {
        'FIRST_NAME': respondent.first_name
    }

    party_id = respondent.party_uuid

    try:
        NotifyGateway(current_app.config).confirm_password_change(email_address, personalisation, str(party_id))
    except RasNotifyError:
        log.error("Error sending notification email for party_id {}".format(party_id))

    # This ensures the log message is only written once the DB transaction is committed
    tran.on_success(lambda: log.info('Respondent with id {} has changed their password'.format(party_id)))

    return {'response': "Ok"}


@with_db_session
def request_password_change(payload, session):
    v = Validator(Exists('email_address'))
    if not v.validate(payload):
        raise RasError(v.errors, 400)

    email_address = payload['email_address']

    respondent = query_respondent_by_email(email_address, session)
    if not respondent:
        raise RasError("Respondent does not exist.", status_code=404)

    email_address = respondent.email_address
    verification_url = PublicWebsite(current_app.config).reset_password_url(email_address)

    personalisation = {
        'RESET_PASSWORD_URL': verification_url,
        'FIRST_NAME': respondent.first_name
    }

    log.info('Reset password url: {}'.format(verification_url))

    party_id = respondent.party_uuid
    try:
        NotifyGateway(current_app.config).request_password_change(email_address, personalisation, str(party_id))
    except RasNotifyError:
        # Note: intentionally suppresses exception
        log.error("Error sending notification email for party_id {}".format(party_id))

    return {'response': "Ok"}


@with_db_session
def put_email_verification(token, session):
    try:
        duration = int(current_app.config.get("EMAIL_TOKEN_EXPIRY", '86400'))
        email_address = decode_email_token(token, duration, current_app.config)
    except SignatureExpired:
        msg = "Expired email verification token {}".format(token)
        raise RasError(msg, 409)
    except (BadSignature, BadData) as e:
        msg = "Bad email verification token {} error {}".format(token, e)
        raise RasError(msg, 404)

    r = query_respondent_by_email(email_address, session)
    if not r:
        raise RasError("Unable to find user while checking email verification token", status_code=404)

    if r.status != RespondentStatus.ACTIVE:
        # We set the party as ACTIVE in this service
        r.status = RespondentStatus.ACTIVE

        # Next we check if this respondent has a pending enrolment (there WILL be only one, set during registration)
        if r.pending_enrolment:
            enrol_respondent_for_survey(r, session)
        else:
            log.info("No pending enrolment for respondent {} while checking email verification token"
                     .format(str(r.party_uuid)))

    # We set the user as verified on the OAuth2 server.
    set_user_verified(email_address)
    return r.to_respondent_dict()


@with_db_session
def resend_verification_email(party_uuid, session):
    """
    Check and resend an email verification email
    :param party_uuid: the party uuid
    :return: make_response
    """
    log.debug('Attempting to resend verification_email with party_uuid {}'.format(party_uuid))

    respondent = query_respondent_by_party_uuid(party_uuid, session)
    if not respondent:
        raise RasError(NO_RESPONDENT_FOR_PARTY_ID, status_code=404)

    _send_email_verification(party_uuid, respondent.email_address)

    return {'message': EMAIL_VERIFICATION_SENT}


def _send_email_verification(party_id, email):
    """
    Send an email verification to the respondent
    """
    verification_url = PublicWebsite(current_app.config).activate_account_url(email)
    log.info("Verification URL for party_id: {} {}".format(party_id, verification_url))

    personalisation = {
        'ACCOUNT_VERIFICATION_URL': verification_url
    }

    try:
        NotifyGateway(current_app.config).verify_email(email, personalisation, str(party_id))
        log.info("Verification email sent", party_id=party_id)
    except RasNotifyError:
        # Note: intentionally suppresses exception
        log.error("Error sending verification email for party_id {}".format(party_id))


def set_user_verified(email_address):
    """ Helper function to set the 'verified' flag on the OAuth2 server for a user.
        If it fails a raise_for_status is executed
    """
    log.info("Setting user active on OAuth2 server")
    oauth_response = OauthClient(current_app.config).update_account(username=email_address, account_verified='true')
    if oauth_response.status_code != 201:
        log.error("Unable to set the user active on the OAuth2 server")
        oauth_response.raise_for_status()


def enrol_respondent_for_survey(r, sess):
    pending_enrolment_id = r.pending_enrolment[0].id
    pending_enrolment = sess.query(PendingEnrolment).filter(PendingEnrolment.id == pending_enrolment_id).one()
    enrolment = sess.query(Enrolment) \
        .filter(Enrolment.business_id == str(pending_enrolment.business_id)) \
        .filter(Enrolment.survey_id == str(pending_enrolment.survey_id)) \
        .filter(Enrolment.respondent_id == r.id).one()
    enrolment.status = EnrolmentStatus.ENABLED
    sess.add(enrolment)
    log.info("Enabling pending enrolment for respondent {} to survey_id {} for business_id {}"
             .format(str(r.party_uuid),
                     str(pending_enrolment.survey_id),
                     str(pending_enrolment.business_id)))
    # Send an enrolment event to the case service
    case_id = pending_enrolment.case_id
    log.info("Pending enrolment for case_id :: " + str(case_id))
    post_case_event(str(case_id), str(r.party_uuid), "RESPONDENT_ENROLED", "Respondent enrolled")
    sess.delete(pending_enrolment)


def register_user(party, tran):
    oauth_response = OauthClient(current_app.config).create_account(party['emailAddress'], party['password'])
    if not oauth_response.status_code == 201:
        log.info("Registering respondent OAuth2 server responded with {} {}"
                 .format(oauth_response.status_code, oauth_response.content))
        oauth_response.raise_for_status()

    def dummy_compensating_action():
        """
        TODO: Undo the user registration.
        """
        log.info("Placeholder for deleting the user from oauth server")

    # Add a compensating action to try and avoid an exception leaving the user in an invalid state.
    tran.compensate(dummy_compensating_action)
    log.info("New user has been registered via the oauth2-service")


def request_iac(enrolment_code):
    # TODO: factor out commonality from these request_* functions
    # TODO: Comments and expladummy_compensating_actionnation
    iac_svc = current_app.config.dependency['iac-service']
    iac_url = build_url('{}://{}:{}/iacs/{}', iac_svc, enrolment_code)
    log.info("GET URL {}".format(iac_url))
    response = Requests.get(iac_url)
    log.info("IAC service responded with {}".format(response.status_code))
    response.raise_for_status()
    return response.json()


def request_case(enrolment_code):
    case_svc = current_app.config.dependency['case-service']
    case_url = build_url('{}://{}:{}/cases/iac/{}', case_svc, enrolment_code)
    log.info("GET URL {}".format(case_url))
    response = Requests.get(case_url)
    log.info("Case service responded with {}".format(response.status_code))
    response.raise_for_status()
    return response.json()


def request_collection_exercise(collection_exercise_id):
    ce_svc = current_app.config.dependency['collectionexercise-service']
    ce_url = build_url('{}://{}:{}/collectionexercises/{}', ce_svc, collection_exercise_id)
    log.info("GET {}".format(ce_url))
    response = Requests.get(ce_url)
    log.info("Collection exercise service responded with {}".format(response.status_code))
    response.raise_for_status()
    return response.json()


def request_survey(survey_id):
    survey_svc = current_app.config.dependency['survey-service']
    survey_url = build_url('{}://{}:{}/surveys/{}', survey_svc, survey_id)
    log.info("GET {}".format(survey_url))
    response = Requests.get(survey_url)
    log.info("Survey service responded with {}".format(response.status_code))
    response.raise_for_status()
    return response.json()


def post_case_event(case_id, party_id, category="Default category message", desc="Default description message"):
    case_svc = current_app.config.dependency['case-service']
    case_url = build_url('{}://{}:{}/cases/{}/events', case_svc, case_id)
    payload = {
        'description': desc,
        'category': category,
        'partyId': party_id,
        'createdBy': "Party Service"
    }

    log.info("POST {} payload={}".format(case_url, payload))
    response = Requests.post(case_url, json=payload)
    log.info("Case service responded with {}".format(response.status_code))
    response.raise_for_status()
    return response.json()