# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tools import mute_logger
from odoo.tests import tagged

from .common import PaypalCommon
from ..controllers.main import PaypalController


@tagged('post_install', '-at_install')
class PaypalForm(PaypalCommon):

    def _get_expected_values(self):
        return_url = self._build_url(PaypalController._return_url)
        values = {
            'address1': 'Huge Street 2/543',
            'amount': str(self.amount),
            'business': self.paypal.paypal_email_account,
            'cancel_return': return_url,
            'city': 'Sin City',
            'cmd': '_xclick',
            'country': 'BE',
            'currency_code': self.currency.name,
            'email': 'norbert.buyer@example.com',
            'first_name': 'Norbert',
            'item_name': f'{self.paypal.company_id.name}: {self.reference}',
            'item_number': self.reference,
            'last_name': 'Buyer',
            'lc': 'en_US',
            'notify_url': self._build_url(PaypalController._notify_url),
            'return': return_url,
            'rm': '2',
            'zip': '1000',
        }

        if self.paypal.fees_active:
            fees = self.currency.round(self.paypal._compute_fees(self.amount, self.currency, self.partner.country_id))
            if fees:
                # handling input is only specified if truthy
                values['handling'] = str(fees)

        return values

    def test_redirect_form_values(self):
        tx = self.create_transaction(flow='redirect')
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx._get_processing_values()

        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        self.assertEqual(
            form_info['action'],
            'https://www.sandbox.paypal.com/cgi-bin/webscr')

        expected_values = self._get_expected_values()
        self.assertDictEqual(
            expected_values, form_info['inputs'],
            "Paypal: invalid inputs specified in the redirect form.")

    def test_redirect_form_with_fees(self):
        self.paypal.write({
            'fees_active': True,
            'fees_dom_fixed': 1.0,
            'fees_dom_var': 0.35,
            'fees_int_fixed': 1.5,
            'fees_int_var': 0.50,
        })
        expected_values = self._get_expected_values()

        tx = self.create_transaction(flow='redirect')
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])

        self.assertEqual(form_info['action'], 'https://www.sandbox.paypal.com/cgi-bin/webscr')
        self.assertDictEqual(
            expected_values, form_info['inputs'],
            "Paypal: invalid inputs specified in the redirect form.")

    def test_feedback_processing(self):
        # typical data posted by paypal after client has successfully paid
        paypal_post_data = {
            'protection_eligibility': u'Ineligible',
            'last_name': u'Poilu',
            'txn_id': u'08D73520KX778924N',
            'receiver_email': 'dummy',
            'payment_status': u'Pending',
            'payment_gross': u'',
            'tax': u'0.00',
            'residence_country': u'FR',
            'address_state': u'Alsace',
            'payer_status': u'verified',
            'txn_type': u'web_accept',
            'address_street': u'Av. de la Pelouse, 87648672 Mayet',
            'handling_amount': u'0.00',
            'payment_date': u'03:21:19 Nov 18, 2013 PST',
            'first_name': u'Norbert',
            'item_name': self.reference,
            'address_country': u'France',
            'charset': u'windows-1252',
            'notify_version': u'3.7',
            'address_name': u'Norbert Poilu',
            'pending_reason': u'multi_currency',
            'item_number': self.reference,
            'receiver_id': u'dummy',
            'transaction_subject': u'',
            'business': u'dummy',
            'test_ipn': u'1',
            'payer_id': u'VTDKRZQSAHYPS',
            'verify_sign': u'An5ns1Kso7MWUdW4ErQKJJJ4qi4-AVoiUf-3478q3vrSmqh08IouiYpM',
            'address_zip': u'75002',
            'address_country_code': u'FR',
            'address_city': u'Paris',
            'address_status': u'unconfirmed',
            'mc_currency': u'EUR',
            'shipping': u'0.00',
            'payer_email': u'tde+buyer@odoo.com',
            'payment_type': u'instant',
            'mc_gross': str(self.amount),
            'ipn_track_id': u'866df2ccd444b',
            'quantity': u'1'
        }

        # should raise error about unknown tx
        with self.assertRaises(ValidationError):
            self.env['payment.transaction']._handle_feedback_data('paypal', paypal_post_data)

        tx = self.create_transaction(flow='redirect')

        # Validate the transaction (pending feedback)
        self.env['payment.transaction']._handle_feedback_data('paypal', paypal_post_data)
        self.assertEqual(tx.state, 'pending', 'paypal: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.state_message, 'multi_currency', 'paypal: wrong state message after receiving a valid pending notification')
        self.assertEqual(tx.acquirer_reference, '08D73520KX778924N', 'paypal: wrong txn_id after receiving a valid pending notification')

        # Reset the transaction
        tx.write({'state': 'draft', 'acquirer_reference': False})

        # Validate the transaction ('completed' feedback)
        paypal_post_data['payment_status'] = 'Completed'
        self.env['payment.transaction']._handle_feedback_data('paypal', paypal_post_data)
        self.assertEqual(tx.state, 'done', 'paypal: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.acquirer_reference, '08D73520KX778924N', 'paypal: wrong txn_id after receiving a valid pending notification')

    def test_fees_computation(self):
        #If the merchant needs to keep 100€, the transaction will be equal to 103.30€.
        #In this way, Paypal will take 103.30 * 2.9% + 0.30 = 3.30€
        #And the merchant will take 103.30 - 3.30 = 100€
        self.paypal.write({
            'fees_active': True,
            'fees_int_fixed': 0.30,
            'fees_int_var': 2.90,
        })
        total_fee = self.paypal._compute_fees(100, False, False)
        self.assertEqual(round(total_fee, 2), 3.3, 'Wrong computation of the Paypal fees')

    def test_parsing_pdt_validation_response_returns_notification_data(self):
        """ Test that the notification data are parsed from the content of a validation response."""
        response_content = 'SUCCESS\nkey1=val1\nkey2=val+2\n'
        notification_data = PaypalController._parse_pdt_validation_response(response_content)
        self.assertDictEqual(notification_data, {'key1': 'val1', 'key2': 'val 2'})

    def test_fail_to_parse_pdt_validation_response_if_not_successful(self):
        """ Test that no notification data are returned from parsing unsuccessful PDT validation."""
        response_content = 'FAIL\ndoes-not-matter'
        notification_data = PaypalController._parse_pdt_validation_response(response_content)
        self.assertIsNone(notification_data)
