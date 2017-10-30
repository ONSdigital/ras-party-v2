from flask import Blueprint, current_app, make_response, jsonify
from flask_httpauth import HTTPBasicAuth

import ras_party.controllers.account_controller
import ras_party.controllers.business_controller
import ras_party.controllers.party_controller
import ras_party.controllers.respondent_controller
from ras_party.support.log_decorator import log_route

respondent_view = Blueprint('respondent_view', __name__)


auth = HTTPBasicAuth()


@respondent_view.before_request
@auth.login_required
@log_route
def before_respondent_view():
    pass


@auth.get_password
def get_pw(username):
    config_username = current_app.config['SECURITY_USER_NAME']
    config_password = current_app.config['SECURITY_USER_PASSWORD']
    if username == config_username:
        return config_password


@respondent_view.route('/respondents/id/<id>', methods=['GET'])
def get_respondent_by_id(id):
    response = ras_party.controllers.respondent_controller.get_respondent_by_id(id)
    return make_response(jsonify(response), 200)


@respondent_view.route('/respondents/email/<string:email>', methods=['GET'])
def get_respondent_by_email(email):
    response = ras_party.controllers.respondent_controller.get_respondent_by_email(email)
    return make_response(jsonify(response), 200)
