import json
import random

from swagger_server.controllers.util import partition_dict
from swagger_server.models.models import Business


class MockBusiness:

    def __init__(self):
        self._attributes = {
            'sampleUnitType': 'B',
            'businessRef': str(random.randrange(100000000, 999999999)),
            'contactName': "John Doe",
            'employeeCount': 50,
            'enterpriseName': "ABC Limited",
            'facsimile': "+44 1234 567890",
            'fulltimeCount': 35,
            'legalStatus': "Private Limited Company",
            'name': "Bolts and Ratchets Ltd",
            'sic2003': "2520",
            'sic2007': "2520",
            'telephone': "+44 1234 567890",
            'tradingName': "ABC Trading Ltd",
            'turnover': 350
        }

    def attributes(self, **kwargs):
        self._attributes.update(kwargs)
        return self

    def as_business(self):
        props, attrs = partition_dict(self._attributes,
                                      Business.REQUIRED_ATTRIBUTES + ['id', 'sampleUnitType', 'businessRef'])
        props['attributes'] = attrs
        return props

    def as_party(self):

        def translate(k):
            return 'sampleUnitRef' if k == 'businessRef' else k

        attributes = {translate(k): v for k, v in self._attributes.items()}
        props, attrs = partition_dict(attributes, ['id', 'sampleUnitType', 'sampleUnitRef'])

        props['attributes'] = attrs
        return props


class MockRespondent:
    def __init__(self):
        self._attributes = {
            'sampleUnitType': 'BI',
            'firstName': 'A',
            'lastName': 'Z',
            'emailAddress': 'a@z.com',
            'telephone': '123',
            'enrolmentCode': 'fb747cq725lj',
            'password': 'banana'
        }

    def attributes(self, **kwargs):
        self._attributes.update(kwargs)
        return self

    def as_respondent(self):
        return self._attributes

    def as_party(self):
        props, attrs = partition_dict(self._attributes, ['id', 'sampleUnitType'])
        props['attributes'] = attrs
        return props


class MockResponse:

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return json.loads(self.payload)


class MockRequests:

    def get(self, uri):

        if uri == 'http://mockhost:1111/cases/iac/fb747cq725lj':
            return self._get
        with open('./fixtures/get_case_by_iac.json') as json_file:
            data = json_file.read()
            return MockResponse(data)
