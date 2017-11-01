from flask import Blueprint, request, current_app, make_response, jsonify
from flask_httpauth import HTTPBasicAuth

import ras_party.controllers.account_controller
import ras_party.controllers.business_controller
import ras_party.controllers.party_controller
import ras_party.controllers.respondent_controller
from ras_party.support.log_decorator import log_route

account_view = Blueprint('account_view', __name__)


auth = HTTPBasicAuth()


@account_view.before_request
@auth.login_required
@log_route
def before_account_view():
    pass


@auth.get_password
def get_pw(username):
    config_username = current_app.config['SECURITY_USER_NAME']
    config_password = current_app.config['SECURITY_USER_PASSWORD']
    if username == config_username:
        return config_password


@account_view.route('/respondents/change_email', methods=['PUT'])
@account_view.route('/respondents/email', methods=['PUT'])
def put_respondent_by_email():
    payload = request.get_json() or {}
    response = ras_party.controllers.account_controller.change_respondent(payload)
    return make_response(jsonify(response), 200)


@account_view.route('/tokens/verify/<token>', methods=['GET'])
def get_verify_token(token):
    response = ras_party.controllers.account_controller.verify_token(token)
    return make_response(jsonify(response), 200)


@account_view.route('/respondents/change_password/<token>', methods=['PUT'])
def change_respondent_password(token):
    payload = request.get_json() or {}
    response = ras_party.controllers.account_controller.change_respondent_password(token, payload)
    return make_response(jsonify(response), 200)


@account_view.route('/respondents/request_password_change', methods=['POST'])
def post_respondent_reset_password_by_email():
    payload = request.get_json() or {}
    response = ras_party.controllers.account_controller.request_password_change(payload)
    return make_response(jsonify(response), 200)


@account_view.route('/respondents', methods=['POST'])
def post_respondent():
    payload = request.get_json() or {}
    response = ras_party.controllers.account_controller.post_respondent(payload)
    return make_response(jsonify(response), 200)


@account_view.route('/emailverification/<token>', methods=['PUT'])
def put_email_verification(token):
    response = ras_party.controllers.account_controller.put_email_verification(token)
    return make_response(jsonify(response), 200)


@account_view.route('/resend-verification-email/<party_uuid>', methods=['GET'])
def resend_verification_email(party_uuid):
    response = ras_party.controllers.account_controller.resend_verification_email(party_uuid)
    return make_response(jsonify(response), 200)