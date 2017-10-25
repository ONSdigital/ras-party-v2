from flask import Blueprint, request, current_app, make_response, jsonify
from flask_httpauth import HTTPBasicAuth

import ras_party.controllers.account_controller
import ras_party.controllers.business_controller
import ras_party.controllers.party_controller
import ras_party.controllers.respondent_controller
from ras_party.support.log_decorator import log_route

party_view = Blueprint('party_view', __name__)


auth = HTTPBasicAuth()


@auth.get_password
def get_pw(username):
    config_username = current_app.config['SECURITY_USER_NAME']
    config_password = current_app.config['SECURITY_USER_PASSWORD']
    if username == config_username:
        return config_password


@party_view.route('/parties', methods=['POST'])
@auth.login_required
@log_route
def post_party():
    payload = request.get_json() or {}
    response = ras_party.controllers.party_controller.parties_post(payload)
    return make_response(jsonify(response), 200)


@party_view.route('/parties/type/<sampleUnitType>/ref/<sampleUnitRef>', methods=['GET'])
@auth.login_required
@log_route
def get_party_by_ref(sampleUnitType, sampleUnitRef):
    response = ras_party.controllers.party_controller.get_party_by_ref(sampleUnitType, sampleUnitRef)
    return make_response(jsonify(response), 200)


@party_view.route('/parties/type/<sampleUnitType>/id/<id>', methods=['GET'])
@auth.login_required
@log_route
def get_party_by_id(sampleUnitType, id):
    response = ras_party.controllers.party_controller.get_party_by_id(sampleUnitType, id)
    return make_response(jsonify(response), 200)
