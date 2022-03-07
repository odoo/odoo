# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from freezegun import freeze_time

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon


@tagged('post_install', '-at_install')
class TestFlows(PaymentCommon, PaymentHttpCommon):

    def _test_flow(self, flow):
        """ Simulate the given online payment flow and tests the tx values at each step.

        :param str flow: The online payment flow to test ('direct', 'redirect', or 'token')
        :return: The transaction created by the payment flow
        :rtype: recordset of `payment.transaction`
        """
        self.reference = f"Test Transaction ({flow} - {self.partner.name})"
        route_values = self._prepare_pay_values()

        # /payment/pay
        tx_context = self.get_tx_checkout_context(**route_values)
        for key, val in tx_context.items():
            if key in route_values:
                self.assertEqual(val, route_values[key])

        # Route values are taken from tx_context result of /pay route to correctly simulate the flow
        route_values = {
            k: tx_context[k]
            for k in [
                'amount',
                'currency_id',
                'reference_prefix',
                'partner_id',
                'access_token',
                'landing_route',
            ]
        }
        route_values.update({
            'flow': flow,
            'payment_option_id': self.acquirer.id,
            'tokenization_requested': False,
        })

        if flow == 'token':
            route_values['payment_option_id'] = self.create_token().id

        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self.get_processing_values(**route_values)
        tx_sudo = self._get_tx(processing_values['reference'])

        # Tx values == given values
        self.assertEqual(tx_sudo.acquirer_id.id, self.acquirer.id)
        self.assertEqual(tx_sudo.amount, self.amount)
        self.assertEqual(tx_sudo.currency_id.id, self.currency.id)
        self.assertEqual(tx_sudo.partner_id.id, self.partner.id)
        self.assertEqual(tx_sudo.reference, self.reference)

        # processing_values == given values
        self.assertEqual(processing_values['acquirer_id'], self.acquirer.id)
        self.assertEqual(processing_values['amount'], self.amount)
        self.assertEqual(processing_values['currency_id'], self.currency.id)
        self.assertEqual(processing_values['partner_id'], self.partner.id)
        self.assertEqual(processing_values['reference'], self.reference)

        # Verify computed values not provided, but added during the flow
        self.assertIn("tx_id=", tx_sudo.landing_route)
        self.assertIn("access_token=", tx_sudo.landing_route)

        if flow == 'redirect':
            # In redirect flow, we verify the rendering of the dummy test form
            redirect_form_info = self._extract_values_from_html_form(
                processing_values['redirect_form_html'])

            # Test content of rendered dummy redirect form
            self.assertEqual(redirect_form_info['action'], 'dummy')
            # Public user since we didn't authenticate with a specific user
            self.assertEqual(
                redirect_form_info['inputs']['user_id'],
                str(self.user.id))
            self.assertEqual(
                redirect_form_info['inputs']['view_id'],
                str(self.dummy_acquirer.redirect_form_view_id.id))

        return tx_sudo

    def test_10_direct_checkout_public(self):
        # No authentication needed, automatic fallback on public user
        self.user = self.public_user
        self._test_flow('direct')

    def test_11_direct_checkout_portal(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self.user = self.portal_user
        self.partner = self.portal_partner
        self._test_flow('direct')

    def test_12_direct_checkout_internal(self):
        self.authenticate(self.internal_user.login, self.internal_user.login)
        self.user = self.internal_user
        self.partner = self.internal_partner
        self._test_flow('direct')

    def test_20_redirect_checkout_public(self):
        self.partner = self.default_partner
        self.user = self.env.ref('base.public_user')
        self._test_flow('redirect')

    def test_21_redirect_checkout_portal(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self.user = self.portal_user
        self.partner = self.portal_partner
        self._test_flow('redirect')

    def test_22_redirect_checkout_internal(self):
        self.authenticate(self.internal_user.login, self.internal_user.login)
        self.user = self.internal_user
        self.partner = self.internal_partner
        self._test_flow('redirect')

    # Payment by token #
    ####################

    # NOTE: not tested as public user because a public user cannot save payment details

    def test_31_tokenize_portal(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self.partner = self.portal_partner
        self.user = self.portal_user
        self._test_flow('token')

    def test_32_tokenize_internal(self):
        self.authenticate(self.internal_user.login, self.internal_user.login)
        self.partner = self.internal_partner
        self.user = self.internal_user
        self._test_flow('token')

    # VALIDATION #
    ##############

    # NOTE: not tested as public user because the validation flow is only available when logged in

    # freeze time for consistent singularize_prefix behavior during the test
    @freeze_time("2011-11-02 12:00:21")
    def _test_validation(self, flow):
        # Fixed with freezegun
        expected_reference = 'validation-20111102120021'

        validation_amount = self.acquirer._get_validation_amount()
        validation_currency = self.acquirer._get_validation_currency()

        tx_context = self.get_tx_manage_context()
        expected_values = {
            'partner_id': self.partner.id,
            'access_token': self._generate_test_access_token(self.partner.id, None, None),
            'reference_prefix': expected_reference
        }
        for key, val in tx_context.items():
            if key in expected_values:
                self.assertEqual(val, expected_values[key])

        transaction_values = {
            'amount': None,
            'currency_id': None,
            'partner_id': tx_context['partner_id'],
            'access_token': tx_context['access_token'],
            'flow': flow,
            'payment_option_id': self.acquirer.id,
            'tokenization_requested': True,
            'reference_prefix': tx_context['reference_prefix'],
            'landing_route': tx_context['landing_route'],
            'is_validation': True,
        }
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self.get_processing_values(**transaction_values)
        tx_sudo = self._get_tx(processing_values['reference'])

        # Tx values == given values
        self.assertEqual(tx_sudo.acquirer_id.id, self.acquirer.id)
        self.assertEqual(tx_sudo.amount, validation_amount)
        self.assertEqual(tx_sudo.currency_id.id, validation_currency.id)
        self.assertEqual(tx_sudo.partner_id.id, self.partner.id)
        self.assertEqual(tx_sudo.reference, expected_reference)
        # processing_values == given values
        self.assertEqual(processing_values['acquirer_id'], self.acquirer.id)
        self.assertEqual(processing_values['amount'], validation_amount)
        self.assertEqual(processing_values['currency_id'], validation_currency.id)
        self.assertEqual(processing_values['partner_id'], self.partner.id)
        self.assertEqual(processing_values['reference'], expected_reference)

    def test_51_validation_direct_portal(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self.partner = self.portal_partner
        self._test_validation(flow='direct')

    def test_52_validation_direct_internal(self):
        self.authenticate(self.internal_user.login, self.internal_user.login)
        self.partner = self.internal_partner
        self._test_validation(flow='direct')

    def test_61_validation_redirect_portal(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self.partner = self.portal_partner
        self._test_validation(flow='direct')

    def test_62_validation_redirect_internal(self):
        self.authenticate(self.internal_user.login, self.internal_user.login)
        self.partner = self.internal_partner
        self._test_validation(flow='direct')

    # Specific flows #
    ##################

    def test_pay_redirect_if_no_partner_exist(self):
        route_values = self._prepare_pay_values()
        route_values.pop('partner_id')

        # Pay without a partner specified --> redirection to login page
        response = self.portal_pay(**route_values)
        self.assertTrue(response.url.startswith(self._build_url('/web/login?redirect=')))

        # Pay without a partner specified (but logged) --> pay with the partner of current user.
        self.authenticate(self.portal_user.login, self.portal_user.login)
        tx_context = self.get_tx_checkout_context(**route_values)
        self.assertEqual(tx_context['partner_id'], self.portal_partner.id)

    def test_pay_no_token(self):
        route_values = self._prepare_pay_values()
        route_values.pop('partner_id')
        route_values.pop('access_token')

        # Pay without a partner specified --> redirection to login page
        response = self.portal_pay(**route_values)
        self.assertTrue(response.url.startswith(self._build_url('/web/login?redirect=')))

        # Pay without a partner specified (but logged) --> pay with the partner of current user.
        self.authenticate(self.portal_user.login, self.portal_user.login)
        tx_context = self.get_tx_checkout_context(**route_values)
        self.assertEqual(tx_context['partner_id'], self.portal_partner.id)

    def test_pay_wrong_token(self):
        route_values = self._prepare_pay_values()
        route_values['access_token'] = "abcde"

        # Pay with a wrong access token --> Not found (404)
        response = self.portal_pay(**route_values)
        self.assertEqual(response.status_code, 404)

    def test_pay_wrong_currency(self):
        # Pay with a wrong currency --> Not found (404)
        self.currency = self.env['res.currency'].browse(self.env['res.currency'].search([], order='id desc', limit=1).id + 1000)
        route_values = self._prepare_pay_values()
        response = self.portal_pay(**route_values)
        self.assertEqual(response.status_code, 404)

        # Pay with an inactive currency --> Not found (404)
        self.currency = self.env['res.currency'].search([('active', '=', False)], limit=1)
        route_values = self._prepare_pay_values()
        response = self.portal_pay(**route_values)
        self.assertEqual(response.status_code, 404)

    def test_invoice_payment_flow(self):
        """Test the payment of an invoice through the payment/pay route"""

        # Pay for this invoice (no impact even if amounts do not match)
        route_values = self._prepare_pay_values()
        route_values['invoice_id'] = self.invoice.id
        tx_context = self.get_tx_checkout_context(**route_values)
        self.assertEqual(tx_context['invoice_id'], self.invoice.id)

        # payment/transaction
        route_values = {
            k: tx_context[k]
            for k in [
                'amount',
                'currency_id',
                'reference_prefix',
                'partner_id',
                'access_token',
                'landing_route',
                'invoice_id',
            ]
        }
        route_values.update({
            'flow': 'direct',
            'payment_option_id': self.acquirer.id,
            'tokenization_requested': False,
        })
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self.get_processing_values(**route_values)
        tx_sudo = self._get_tx(processing_values['reference'])
        # Note: strangely, the check
        # self.assertEqual(tx_sudo.invoice_ids, invoice)
        # doesn't work, and cache invalidation doesn't work either.
        self.invoice.invalidate_cache(['transaction_ids'])
        self.assertEqual(self.invoice.transaction_ids, tx_sudo)

    def test_transaction_wrong_flow(self):
        transaction_values = self._prepare_pay_values()
        transaction_values.update({
            'flow': 'this flow does not exist',
            'payment_option_id': self.acquirer.id,
            'tokenization_requested': False,
            'reference_prefix': 'whatever',
            'landing_route': 'whatever',
        })
        # Transaction step with a wrong flow --> UserError
        with mute_logger('odoo.http'):
            response = self.portal_transaction(**transaction_values)
        self.assertIn(
            "odoo.exceptions.UserError: The payment should either be direct, with redirection, or made by a token.",
            response.text)

    def test_transaction_wrong_token(self):
        route_values = self._prepare_pay_values()
        route_values['access_token'] = "abcde"

        # Transaction step with a wrong access token --> ValidationError
        with mute_logger('odoo.http'):
            response = self.portal_transaction(**route_values)
        self.assertIn(
            "odoo.exceptions.ValidationError: The access token is invalid.",
            response.text)

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_direct_payment_triggers_no_payment_request(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self.partner = self.portal_partner
        self.user = self.portal_user
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._send_payment_request'
        ) as patched:
            self.portal_transaction(
                **self._prepare_transaction_values(self.acquirer.id, 'direct')
            )
            self.assertEqual(patched.call_count, 0)

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_payment_with_redirect_triggers_no_payment_request(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self.partner = self.portal_partner
        self.user = self.portal_user
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._send_payment_request'
        ) as patched:
            self.portal_transaction(
                **self._prepare_transaction_values(self.acquirer.id, 'redirect')
            )
            self.assertEqual(patched.call_count, 0)

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_payment_by_token_triggers_exactly_one_payment_request(self):
        self.authenticate(self.portal_user.login, self.portal_user.login)
        self.partner = self.portal_partner
        self.user = self.portal_user
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._send_payment_request'
        ) as patched:
            self.portal_transaction(
                **self._prepare_transaction_values(self.create_token().id, 'token')
            )
            self.assertEqual(patched.call_count, 1)
