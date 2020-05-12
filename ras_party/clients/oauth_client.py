from flask import current_app

from ras_party.support.requests_wrapper import Requests


class OauthClient:
    def __init__(self):
        self.service = current_app.config['OAUTH_SERVICE']

    @property
    def admin_url(self):
        return f'{self.service}/api/account/create'

    def create_account(self, username, password):
        payload = {
            'username': username,
            'password': password,
        }
        return Requests.post(self.admin_url, data=payload)

    def update_account(self, **kwargs):
        payload = {}
        payload.update(kwargs)
        return Requests.put(self.admin_url, data=payload)
