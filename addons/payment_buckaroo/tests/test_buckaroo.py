# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import BuckarooCommon
from ..controllers.main import BuckarooController


@tagged('post_install', '-at_install')
class BuckarooTest(BuckarooCommon):

    def test_redirect_form_values(self):
        return_url = self._build_url(BuckarooController._return_url)
        expected_values = {
            'Brq_websitekey': self.buckaroo.buckaroo_website_key,
            'Brq_amount': str(self.amount),
            'Brq_currency': self.currency.name,
            'Brq_invoicenumber': self.reference,
            'Brq_signature': '04c26578116990496770687a8bf225200e0f56e6',
            'Brq_return': return_url,
            'Brq_returncancel': return_url,
            'Brq_returnerror': return_url,
            'Brq_returnreject': return_url,
            'Brq_culture': 'en-US',
        }

        tx_sudo = self.create_transaction(flow='redirect')
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx_sudo._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])

        self.assertEqual(form_info['action'], "https://testcheckout.buckaroo.nl/html/")
        self.assertDictEqual(expected_values, form_info['inputs'],
            "Buckaroo: invalid inputs specified in the redirect form.")

    def test_feedback_processing(self):
        self.amount = 2240.0
        self.reference = 'SO004'

        # typical data posted by buckaroo after client has successfully paid
        buckaroo_post_data = {
            'BRQ_RETURNDATA': u'',
            'BRQ_AMOUNT': str(self.amount),
            'BRQ_CURRENCY': self.currency.name,
            'BRQ_CUSTOMER_NAME': u'Jan de Tester',
            'BRQ_INVOICENUMBER': self.reference,
            'brq_payment': u'573311D081B04069BD6336001611DBD4',
            'BRQ_PAYMENT_METHOD': u'paypal',
            'BRQ_SERVICE_PAYPAL_PAYERCOUNTRY': u'NL',
            'BRQ_SERVICE_PAYPAL_PAYEREMAIL': u'fhe@odoo.com',
            'BRQ_SERVICE_PAYPAL_PAYERFIRSTNAME': u'Jan',
            'BRQ_SERVICE_PAYPAL_PAYERLASTNAME': u'Tester',
            'BRQ_SERVICE_PAYPAL_PAYERMIDDLENAME': u'de',
            'BRQ_SERVICE_PAYPAL_PAYERSTATUS': u'verified',
            'Brq_signature': u'e439f3af06b9752197631715628d6a198a25900f',
            'BRQ_STATUSCODE': u'190',
            'BRQ_STATUSCODE_DETAIL': u'S001',
            'BRQ_STATUSMESSAGE': u'Transaction successfully processed',
            'BRQ_TIMESTAMP': u'2014-05-08 12:41:21',
            'BRQ_TRANSACTIONS': u'D6106678E1D54EEB8093F5B3AC42EA7B',
            'BRQ_WEBSITEKEY': u'5xTGyGyPyl',
        }

        with self.assertRaises(ValidationError):  # unknown transaction
            self.env['payment.transaction']._handle_feedback_data('buckaroo', buckaroo_post_data)

        tx = self.create_transaction(flow='redirect')

        # validate it
        tx._handle_feedback_data('buckaroo', buckaroo_post_data)
        self.assertEqual(tx.state, 'done', 'Buckaroo: validation did not put tx into done state')
        self.assertEqual(tx.acquirer_reference, buckaroo_post_data.get('BRQ_TRANSACTIONS'),
            'Buckaroo: validation did not update tx payid')

        # New reference for new tx
        self.reference = 'SO004-2'
        tx = self.create_transaction(flow='redirect')

        buckaroo_post_data['BRQ_INVOICENUMBER'] = self.reference
        # now buckaroo post is ok: try to modify the SHASIGN
        buckaroo_post_data['Brq_signature'] = '54d928810e343acf5fb0c3ee75fd747ff159ef7a'
        with self.assertRaises(ValidationError):
            self.env['payment.transaction']._handle_feedback_data('buckaroo', buckaroo_post_data)

        # simulate an error
        buckaroo_post_data['BRQ_STATUSCODE'] = '2'
        buckaroo_post_data['Brq_signature'] = 'b8e54e26b2b5a5e697b8ed5085329ea712fd48b2'

        # Avoid warning log bc of unknown status code
        with mute_logger('odoo.addons.payment_buckaroo.models.payment_transaction'):
            self.env['payment.transaction']._handle_feedback_data('buckaroo', buckaroo_post_data)

        self.assertEqual(tx.state, 'error',
            'Buckaroo: unexpected status code should put tx in error state')
