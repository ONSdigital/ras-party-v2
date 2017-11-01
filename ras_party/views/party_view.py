from flask import Blueprint, request, current_app, make_response, jsonify
from flask_httpauth import HTTPBasicAuth

import ras_party.controllers.account_controller
import ras_party.controllers.business_controller
import ras_party.controllers.party_controller
import ras_party.controllers.respondent_controller
from ras_party.support.log_decorator import log_route

party_view = Blueprint('party_view', __name__)


auth = HTTPBasicAuth()


@party_view.before_request
@auth.login_required
@log_route
def before_party_view():
    pass


@auth.get_password
def get_pw(username):
    config_username = current_app.config['SECURITY_USER_NAME']
    config_password = current_app.config['SECURITY_USER_PASSWORD']
    if username == config_username:
        return config_password


@party_view.route('/parties', methods=['POST'])
def post_party():
    payload = request.get_json() or {}
    response = ras_party.controllers.party_controller.parties_post(payload)
    return make_response(jsonify(response), 200)


@party_view.route('/parties/type/<sample_unit_type>/ref/<sample_unit_ref>', methods=['GET'])
def get_party_by_ref(sample_unit_type, sample_unit_ref):
    response = ras_party.controllers.party_controller.get_party_by_ref(sample_unit_type, sample_unit_ref)
    return make_response(jsonify(response), 200)


@party_view.route('/parties/type/<sample_unit_type>/id/<id>', methods=['GET'])
def get_party_by_id(sample_unit_type, id):
    response = ras_party.controllers.party_controller.get_party_by_id(sample_unit_type, id)
    return make_response(jsonify(response), 200)
