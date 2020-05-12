# flake8: noqa
import os
from distutils.util import strtobool

from ras_party.cloud.cloudfoundry import ONSCloudFoundry


cf = ONSCloudFoundry()


def _is_true(value):
    try:
        return value.lower() in ('true', 't', 'yes', 'y', '1')
    except AttributeError:
        return value is True


class Config(object):
    VERSION = '1.13.0'
    SCHEME = os.getenv('http')
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = os.getenv('PORT', 8081)
    DEBUG = _is_true(os.getenv('DEBUG', False))
    LOGGING_LEVEL = os.getenv('LOGGING_LEVEL', 'INFO')
    SECRET_KEY = os.getenv('SECRET_KEY', 'aardvark')
    EMAIL_TOKEN_SALT = os.getenv('EMAIL_TOKEN_SALT', 'aardvark')
    EMAIL_TOKEN_EXPIRY = int(os.getenv('EMAIL_TOKEN_EXPIRY', '306000'))
    PARTY_SCHEMA = os.getenv('PARTY_SCHEMA', 'ras_party/schemas/party_schema.json')

    DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
    DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '10'))
    DB_POOL_RECYCLE = int(os.getenv('DB_POOL_RECYCLE', '-1'))

    if cf.detected:
        DATABASE_SCHEMA = 'partysvc'
        DATABASE_URI = cf.db.credentials['uri']
    else:
        DATABASE_SCHEMA = os.getenv('DATABASE_SCHEMA', 'partysvc')
        DATABASE_URI = os.getenv('DATABASE_URI', "postgresql://postgres:postgres@localhost:6432/postgres")

    # Zipkin
    ZIPKIN_DISABLE = bool(strtobool(os.getenv("ZIPKIN_DISABLE", "False")))
    ZIPKIN_DSN = os.getenv("ZIPKIN_DSN", None)
    ZIPKIN_SAMPLE_RATE = int(os.getenv("ZIPKIN_SAMPLE_RATE", '0'))

    REQUESTS_GET_TIMEOUT = os.getenv('REQUESTS_GET_TIMEOUT', 20)
    REQUESTS_POST_TIMEOUT = os.getenv('REQUESTS_POST_TIMEOUT', 20)
    SECURITY_USER_NAME = os.getenv('SECURITY_USER_NAME', 'admin')
    SECURITY_USER_PASSWORD = os.getenv('SECURITY_USER_PASSWORD', 'secret')
    SECURITY_REALM = os.getenv('SECURITY_REALM', 'sdc')

    # dependencies

    FRONTSTAGE_PROTOCOL = os.getenv('FRONTSTAGE_PROTOCOL', 'http')
    FRONTSTAGE_HOST = os.getenv('FRONTSTAGE_HOST', 'localhost')
    FRONTSTAGE_PORT = os.getenv('FRONTSTAGE_PORT', 8082)
    FRONTSTAGE_URL = f'{FRONTSTAGE_PROTOCOL}://{FRONTSTAGE_HOST}:{FRONTSTAGE_PORT}'

    CASE_SERVICE_PROTOCOL = os.getenv('CASE_SERVICE_PROTOCOL', 'http')
    CASE_SERVICE_HOST = os.getenv('CASE_SERVICE_HOST', 'localhost')
    CASE_SERVICE_PORT = os.getenv('CASE_SERVICE_PORT', 8171)
    CASE_SERVICE = f'{CASE_SERVICE_PROTOCOL}://{CASE_SERVICE_HOST}:{CASE_SERVICE_PORT}'

    COLLECTION_EXERCISE_SERVICE_PROTOCOL = os.getenv('COLLECTION_EXERCISE_SERVICE_PROTOCOL', 'http')
    COLLECTION_EXERCISE_SERVICE_HOST = os.getenv('COLLECTION_EXERCISE_SERVICE_HOST', 'localhost')
    COLLECTION_EXERCISE_SERVICE_PORT = os.getenv('COLLECTION_EXERCISE_SERVICE_PORT', 8145)
    COLLECTION_EXERCISE_SERVICE = f'{COLLECTION_EXERCISE_SERVICE_PROTOCOL}://{COLLECTION_EXERCISE_SERVICE_HOST}:{COLLECTION_EXERCISE_SERVICE_PORT}'

    SURVEY_SERVICE_PROTOCOL = os.getenv('SURVEY_SERVICE_PROTOCOL', 'http')
    SURVEY_SERVICE_HOST = os.getenv('SURVEY_SERVICE_HOST', 'localhost')
    SURVEY_SERVICE_PORT = os.getenv('SURVEY_SERVICE_PORT', 8080)
    SURVEY_SERVICE = f'{SURVEY_SERVICE_PROTOCOL}://{SURVEY_SERVICE_HOST}:{SURVEY_SERVICE_PORT}'

    NOTIFY_SERVICE_URL = os.getenv('NOTIFY_SERVICE_URL', 'http://notify-gateway-service/emails/')
    NOTIFY_EMAIL_VERIFICATION_TEMPLATE = os.getenv('NOTIFY_EMAIL_VERIFICATION_TEMPLATE', 'email_verification_id')
    NOTIFY_REQUEST_PASSWORD_CHANGE_TEMPLATE = os.getenv('NOTIFY_REQUEST_PASSWORD_CHANGE_TEMPLATE',
                                                            'request_password_change_id')
    NOTIFY_CONFIRM_PASSWORD_CHANGE_TEMPLATE = os.getenv('NOTIFY_CONFIRM_PASSWORD_CHANGE_TEMPLATE',
                                                            'confirm_password_change_id')
    NOTIFY_ACCOUNT_LOCKED_TEMPLATE = os.getenv('NOTIFY_ACCOUNT_LOCKED_TEMPLATE', 'account_locked_id')

    IAC_SERVICE_PROTOCOL = os.getenv('IAC_SERVICE_PROTOCOL', 'http')
    IAC_SERVICE_HOST = os.getenv('IAC_SERVICE_HOST', 'localhost')
    IAC_SERVICE_PORT = os.getenv('IAC_SERVICE_PORT', 8121)
    IAC_SERVICE = f'{IAC_SERVICE_PROTOCOL}://{IAC_SERVICE_HOST}:{IAC_SERVICE_PORT}'

    OAUTH_SERVICE_PROTOCOL = os.getenv('OAUTH_SERVICE_PROTOCOL', 'http')
    OAUTH_SERVICE_HOST = os.getenv('OAUTH_SERVICE_HOST', 'localhost')
    OAUTH_SERVICE_PORT = os.getenv('OAUTH_SERVICE_PORT', 8041)
    OAUTH_SERVICE = f'{OAUTH_SERVICE_PROTOCOL}://{OAUTH_SERVICE_HOST}:{OAUTH_SERVICE_PORT}'

    DEPENDENCIES = [
        'ras-party-db',
        'public-website',
        'case-service',
        'collectionexercise-service',
        'survey-service',
        'notify-service',
        'iac-service',
        'oauth2-service',
    ]

    # features

    REPORT_DEPENDENCIES = _is_true(os.getenv('REPORT_DEPENDENCIES', False))
    SEND_EMAIL_TO_GOV_NOTIFY = _is_true(os.getenv('SEND_EMAIL_TO_GOV_NOTIFY', False))


class DevelopmentConfig(Config):

    DEBUG = True
    LOGGING_LEVEL = 'DEBUG'


class TestingConfig(DevelopmentConfig):

    DEBUG = True
    LOGGING_LEVEL = 'ERROR'
    SECRET_KEY = 'aardvark'
    PARTY_SCHEMA = 'ras_party/schemas/party_schema.json'
    SECURITY_USER_NAME = 'username'
    SECURITY_USER_PASSWORD = 'password'
    REQUESTS_GET_TIMEOUT = 99
    REQUESTS_POST_TIMEOUT = 99
    DATABASE_SCHEMA = 'partysvc'

    FRONTSTAGE_URL = 'http://dummy.ons.gov.uk'
    CASE_SERVICE = 'http://mockhost:1111'
    COLLECTION_EXERCISE_SERVICE = 'http://mockhost:2222'
    SURVEY_SERVICE = 'http://mockhost:3333'
    OAUTH_SERVICE = 'http://mockhost:4444'
    NOTIFY_SERVICE_URL = 'http://mockhost:5555/emails/'
    NOTIFY_EMAIL_VERIFICATION_TEMPLATE = 'email_verification_id'
    NOTIFY_REQUEST_PASSWORD_CHANGE_TEMPLATE = 'request_password_change_id'
    NOTIFY_CONFIRM_PASSWORD_CHANGE_TEMPLATE = 'confirm_password_change_id'
    NOTIFY_ACCOUNT_LOCKED_TEMPLATE = 'account_locked_id'
    IAC_SERVICE = 'http://mockhost:6666'

    SEND_EMAIL_TO_GOV_NOTIFY = True
