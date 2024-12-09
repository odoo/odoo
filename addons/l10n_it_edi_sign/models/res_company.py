import base64
import json
import requests

from odoo import models
from odoo.tools import zeep, file_open, file_path


URL = 'https://sws-companynamesaas.test.namirialtsp.com/SignEngineWeb/sign-services'
SERVICE_NAME = '{http://service.ws.nam/}SignServiceSoapBinding'
WSDL_URL = f'{URL}?wsdl'
TIMEOUT = 5

HIDDEN_FOLDER = 'l10n_it_edi_sign/.certificates'
TEST_INVOICE_PATH = 'l10n_it_edi/tests/import_xmls/IT01234567888_FPR01.xml'


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_it_edi_sign_test(self):
        def skip(*args):
            skipvalue = zeep.client.zeep.xsd.SkipValue
            if len(args) > 1:
                return {k: skipvalue for k in args}
            else:
                return skipvalue

        with file_open(f"{HIDDEN_FOLDER}/credentials.json") as infile:
            credentials = json.load(infile)
        with file_open(TEST_INVOICE_PATH, "rb") as infile:
            content = infile.read()

        session = requests.Session()
        session.cert = [file_path(f"{HIDDEN_FOLDER}/certificate.{x}") for x in ('pem', 'pkey')]

        client = zeep.Client(WSDL_URL, session=session, operation_timeout=TIMEOUT, timeout=TIMEOUT)
        service = client.create_service(SERVICE_NAME, URL)

        return service.signXAdES(
            credentials={
                "username": credentials['username'],
                "password": credentials['password'],
                "idOtp": skip(),
            },
            buffer=base64.b64encode(content).decode(),
            XAdESPreferences=skip(
                'outputAsPDF',
                'outputAsTSD',
                'outputBase64Encoded',
                'signType',
                'withTimestamp',
                'detached',
                'en319132',
                'withoutSignatureExclusion',
            ))
