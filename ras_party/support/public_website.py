from flask import current_app

from ras_party.support.verification import generate_email_token


class PublicWebsite:

    def __init__(self):
        self.website_uri = current_app.config['FRONTSTAGE_URL']

    def reset_password_url(self, email):
        return f'{self.website_uri}/passwords/reset-password/{self._generate_token(email)}'

    def activate_account_url(self, email):
        return f'{self.website_uri}/register/activate-account/{self._generate_token(email)}'

    def confirm_account_email_change_url(self, email):
        return f'{self.website_uri}/my-account/confirm-account-email-change/{self._generate_token(email)}'

    @staticmethod
    def _generate_token(email):
        return generate_email_token(email)
