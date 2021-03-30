# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from freezegun import freeze_time

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import SipsCommon
from ..controllers.main import SipsController
from ..models.payment_acquirer import SUPPORTED_CURRENCIES

@tagged('post_install', '-at_install')
class SipsTest(SipsCommon):

    def test_compatible_acquirers(self):
        for curr in SUPPORTED_CURRENCIES:
            currency = self._prepare_currency(curr)
            acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
                partner_id=self.partner.id,
                company_id=self.company.id,
                currency_id=currency.id,
            )
            self.assertIn(self.sips, acquirers)

        unsupported_currency = self._prepare_currency('VEF')
        acquirers = self.env['payment.acquirer']._get_compatible_acquirers(
            partner_id=self.partner.id,
            company_id=self.company.id,
            currency_id=unsupported_currency.id,
        )
        self.assertNotIn(self.sips, acquirers)

    # freeze time for consistent singularize_prefix behavior during the test
    @freeze_time("2011-11-02 12:00:21")
    def test_reference(self):
        tx = self.create_transaction(flow="redirect", reference="")
        self.assertEqual(tx.reference, "tx20111102120021",
            "Payulatam: transaction reference wasn't correctly singularized.")

    def test_redirect_form_values(self):
        tx = self.create_transaction(flow="redirect")

        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        form_inputs = form_info['inputs']

        self.assertEqual(form_info['action'], self.sips.sips_test_url)
        self.assertEqual(form_inputs['InterfaceVersion'], self.sips.sips_version)
        return_url = self._build_url(SipsController._return_url)
        notify_url = self._build_url(SipsController._notify_url)
        self.assertEqual(form_inputs['Data'],
            f'amount=111111|currencyCode=978|merchantId=dummy_mid|normalReturnUrl={return_url}|' \
            f'automaticResponseUrl={notify_url}|transactionReference={self.reference}|' \
            f'statementReference={self.reference}|keyVersion={self.sips.sips_key_version}|' \
            f'returnContext={json.dumps(dict(reference=self.reference))}'
        )
        self.assertEqual(form_inputs['Seal'],
            '4d7cc67c0168e8ce11c25fbe1937231c644861e320702ab544022b032b9eb4a2')

    def test_feedback_processing(self):
        # typical data posted by Sips after client has successfully paid
        sips_post_data = {
            'Data': 'captureDay=0|captureMode=AUTHOR_CAPTURE|currencyCode=840|'
                    'merchantId=002001000000001|orderChannel=INTERNET|'
                    'responseCode=00|transactionDateTime=2020-04-08T06:15:59+02:00|'
                    'transactionReference=SO100x1|keyVersion=1|'
                    'acquirerResponseCode=00|amount=31400|authorisationId=0020000006791167|'
                    'paymentMeanBrand=IDEAL|paymentMeanType=CREDIT_TRANSFER|'
                    'customerIpAddress=127.0.0.1|returnContext={"return_url": '
                    '"/payment/process", "reference": '
                    '"SO100x1"}|holderAuthentRelegation=N|holderAuthentStatus=|'
                    'transactionOrigin=INTERNET|paymentPattern=ONE_SHOT|customerMobilePhone=null|'
                    'mandateAuthentMethod=null|mandateUsage=null|transactionActors=null|'
                    'mandateId=null|captureLimitDate=20200408|dccStatus=null|dccResponseCode=null|'
                    'dccAmount=null|dccCurrencyCode=null|dccExchangeRate=null|'
                    'dccExchangeRateValidity=null|dccProvider=null|'
                    'statementReference=SO100x1|panEntryMode=MANUAL|walletType=null|'
                    'holderAuthentMethod=NO_AUTHENT_METHOD',
            'Encode': '',
            'InterfaceVersion': 'HP_2.4',
            'Seal': 'f03f64da6f57c171904d12bf709b1d6d3385131ac914e97a7e1db075ed438f3e',
            'locale': 'en',
        }

        with self.assertRaises(ValidationError): # unknown transaction
            self.env['payment.transaction']._handle_feedback_data('sips', sips_post_data)

        self.amount = 314.0
        self.reference = 'SO100x1'

        tx = self.create_transaction(flow="redirect")

        # Validate the transaction
        self.env['payment.transaction']._handle_feedback_data('sips', sips_post_data)
        self.assertEqual(tx.state, 'done', 'Sips: validation did not put tx into done state')
        self.assertEqual(tx.acquirer_reference, self.reference, 'Sips: validation did not update tx id')

        # same process for an payment in error on sips's end
        sips_post_data = {
            'Data': 'captureDay=0|captureMode=AUTHOR_CAPTURE|currencyCode=840|'
                    'merchantId=002001000000001|orderChannel=INTERNET|responseCode=12|'
                    'transactionDateTime=2020-04-08T06:24:08+02:00|transactionReference=SO100x2|'
                    'keyVersion=1|amount=31400|customerIpAddress=127.0.0.1|returnContext={"return_url": '
                    '"/payment/process", "reference": '
                    '"SO100x2"}|paymentPattern=ONE_SHOT|customerMobilePhone=null|mandateAuthentMethod=null|'
                    'mandateUsage=null|transactionActors=null|mandateId=null|captureLimitDate=null|'
                    'dccStatus=null|dccResponseCode=null|dccAmount=null|dccCurrencyCode=null|'
                    'dccExchangeRate=null|dccExchangeRateValidity=null|dccProvider=null|'
                    'statementReference=SO100x2|panEntryMode=null|walletType=null|holderAuthentMethod=null',
            'InterfaceVersion': 'HP_2.4',
            'Seal': '6e1995ea5432580860a04d8515b6eb1507996f97b3c5fa04fb6d9568121a16a2'
        }
        self.reference = 'SO100x2'
        tx2 = self.create_transaction(flow="redirect")

        self.env['payment.transaction']._handle_feedback_data('sips', sips_post_data)
        self.assertEqual(tx2.state, 'cancel', 'Sips: erroneous validation did not put tx into error state')
