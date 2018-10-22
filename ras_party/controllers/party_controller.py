import logging

import structlog
from flask import current_app
from werkzeug.exceptions import BadRequest, NotFound

from ras_party.controllers.queries import query_business_by_party_uuid, query_business_by_ref
from ras_party.controllers.queries import query_respondent_by_party_uuid
from ras_party.models.models import Business, Respondent
from ras_party.support.session_decorator import with_db_session


logger = structlog.wrap_logger(logging.getLogger(__name__))


@with_db_session
def parties_post(party_data, session):
    """
    Post a new party (with sampleUnitType B)

    :param party_data: packet containing the data to post
    :type party_data: JSON data maching the schema described in schemas/party_schema.json
    """
    errors = Business.validate(party_data, current_app.config['PARTY_SCHEMA'])
    if errors:
        logger.debug("party schema validation failed", errors=[e.split('\n')[0] for e in errors])
        raise BadRequest([e.split('\n')[0] for e in errors])

    if party_data['sampleUnitType'] != Business.UNIT_TYPE:
        logger.debug("Wrong sampleUnitType", type=party_data['sampleUnitType'])
        raise BadRequest(f'sampleUnitType must be of type {Business.UNIT_TYPE}')

    business = query_business_by_ref(party_data['sampleUnitRef'], session)
    if business:
        party_data['id'] = str(business.party_uuid)
        business.add_versioned_attributes(party_data)
        session.merge(business)
    else:
        business = Business.from_party_dict(party_data)
        session.add(business)
    return business.to_post_response_dict()


@with_db_session
def get_party_by_ref(sample_unit_ref, session):
    """
    Get a Party by its unique reference (ruref / uprn)
    Returns a single Party
    :type sample_unit_ref: str
    :param session session passed in by decorator
    :rtype: Party
    """
    business = query_business_by_ref(sample_unit_ref, session)
    if not business:
        logger.debug("Business with reference does not exist.", reference=sample_unit_ref, status=404)
        raise NotFound("Business with reference does not exist.")

    return business.to_party_dict()


@with_db_session
def get_party_by_id(id, session):
    business = query_business_by_party_uuid(id, session)
    if not business:
        logger.debug("Business with id does not exist", business_id=id, status=404)
        raise NotFound("Business with id does not exist")
    return business.to_party_dict()


def get_party_with_enrolments_filtered_by_survey(party_id, survey_id, enrolment_status=None):
    party = get_party_by_id(party_id)

    filtered_associations = []
    for association in party['associations']:

        filtered_association = {'partyId': association['partyId']}

        filtered_enrolments = filter_enrolments(association['enrolments'], survey_id, enrolment_status)

        if filtered_enrolments:
            filtered_association['enrolments'] = filtered_enrolments
            filtered_associations.append(filtered_association)

    party['associations'] = filtered_associations

    return party


def filter_enrolments(existing_enrolments, survey_id, enrolment_status=None):
    filtered_enrolments = []
    for enrolment in existing_enrolments:
        if enrolment['surveyId'] == survey_id:
            filtered_enrolments.append(enrolment)

    if enrolment_status:
        for enrolment in filtered_enrolments:
            if enrolment['enrolmentStatus'] not in enrolment_status:
                filtered_enrolments.remove(enrolment)
    return filtered_enrolments
