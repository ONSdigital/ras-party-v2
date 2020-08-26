from concurrent.futures import TimeoutError
from unittest.mock import MagicMock

from flask import current_app
from flask_testing import TestCase

from ras_party.controllers.notify_gateway import NotifyGateway
from ras_party.exceptions import RasNotifyError
from ras_party.support.requests_wrapper import Requests
from run import create_app
from test.mocks import MockRequests
from test.party_client import PartyTestClient


class TestNotifyGateway(PartyTestClient):
    """ Notify gateway test class"""
    def setUp(self):
        self.mock_requests = MockRequests()
        Requests._lib = self.mock_requests

    def test_notify_sends_notification_with_basic_message(self):
        # Given a mocked notify gateway and response
        self.mock_requests.post.response_payload = '{"id": "notification id"}'

        notify = NotifyGateway(current_app.config)
        # When an email is sent
        notify.request_to_notify('email', 'email_verification')
        # Then send_email_notification is called

        expected_data = {"emailAddress": "email"}

        expected_request = {"auth": (current_app.config['SECURITY_USER_NAME'],
                                     current_app.config['SECURITY_USER_PASSWORD']),
                            "timeout": 20, "json": expected_data}

        self.mock_requests.post.assert_called_with(
            "http://mockhost:5555/emails/email_verification_id",
            expected_request)

    def test_notify_sends_notification_with_extended_message(self):
        # Given a mocked notify gateway and response
        self.mock_requests.post.response_payload = '{"id": "notification id"}'

        notify = NotifyGateway(current_app.config)
        # When an email is sent
        personalisation = {
            "name": "A person"
        }
        notify.request_to_notify("email", 'request_password_change', personalisation=personalisation,
                                 reference="reference")
        # Then send_email_notification is called
        expected_data = {"emailAddress": "email", "personalisation": personalisation, "reference": "reference"}
        expected_request = {"auth": (current_app.config['SECURITY_USER_NAME'],
                                     current_app.config['SECURITY_USER_PASSWORD']),
                            "timeout": 20, "json": expected_data}

        self.mock_requests.post.assert_called_with(
            "http://mockhost:5555/emails/request_password_change_id",
            expected_request)

    def test_notify_exception_is_translated_to_ras_exception(self):
        # Given a mocked gov.uk notify and exception
        def mock_post_notify(*args, **kwargs):
            raise Exception("Generic Error")

        self.mock_requests.post = mock_post_notify

        # When an email is sent
        notify = NotifyGateway(current_app.config)
        # Then a RasNotifyError is raised
        with self.assertRaises(RasNotifyError):
            notify.request_to_notify('email', 'request_password_change')


class TestNotifyGatewayUnit(TestCase):
    """
    Unit tests for NotifyGateway controller

    Note: Even though these are unit tests, we have a create_app function to let us easily access the config
    as a dictionary as it's difficult to do otherwise.
    """

    @staticmethod
    def create_app():
        return create_app('TestingConfig')

    def test_get_template_with_fake_template_name(self):
        # Given a mocked notify gateway

        notify = NotifyGateway(current_app.config)
        # When given a fake template name
        template_name = 'fake_name'
        # Then a key error is raised
        with self.assertRaises(KeyError):
            notify._get_template_id(template_name)

    def test_request_to_notify_with_pubsub_no_personalisation(self):
        """Tests what is sent to pubsub when no personalisation is added"""
        publisher = MagicMock()
        publisher.topic_path.return_value = 'projects/test-project-id/topics/ras-rm-notify-test'
        # Given a mocked notify gateway
        notify = NotifyGateway(current_app.config)
        notify.publisher = publisher
        result = notify.request_to_notify('test@email.com', 'notify_account_locked')
        data = b'{"notify": {"email_address": "test@email.com", ' \
               b'"template_id": "account_locked_id", "personalisation": {}}}'

        publisher.publish.assert_called()
        publisher.publish.assert_called_with('projects/test-project-id/topics/ras-rm-notify-test', data=data)
        self.assertIsNone(result)

    def test_request_to_notify_with_pubsub_with_personalisation(self):
        """Tests what is sent to pubsub when personalisation is added"""
        publisher = MagicMock()
        publisher.topic_path.return_value = 'projects/test-project-id/topics/ras-rm-notify-test'
        # Given a mocked notify gateway
        notify = NotifyGateway(current_app.config)
        notify.publisher = publisher
        personalisation = {"first_name": "testy", "last_name": "surname"}
        result = notify.request_to_notify('test@email.com', 'notify_account_locked', personalisation)
        data = b'{"notify": {"email_address": "test@email.com", "template_id": "account_locked_id",' \
               b' "personalisation": {"first_name": "testy", "last_name": "surname"}}}'
        publisher.publish.assert_called()
        publisher.publish.assert_called_with('projects/test-project-id/topics/ras-rm-notify-test', data=data)
        self.assertIsNone(result)

    def test_request_to_notify_with_pubsub_timeout_error(self):
        """Tests if the future.result() raises a TimeoutError then the function raises a RasNotifyError"""
        future = MagicMock()
        future.result.side_effect = TimeoutError("bad")
        publisher = MagicMock()
        publisher.publish.return_value = future

        # Given a mocked notify gateway
        notify = NotifyGateway(current_app.config)
        notify.publisher = publisher
        with self.assertRaises(RasNotifyError):
            notify.request_to_notify('test@email.com', 'notify_account_locked')
