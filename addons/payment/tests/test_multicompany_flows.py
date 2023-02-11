# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment.tests.multicompany_common import PaymentMultiCompanyCommon


@tagged('post_install', '-at_install')
class TestMultiCompanyFlows(PaymentMultiCompanyCommon, PaymentHttpCommon):

    def test_pay_logged_in_another_company(self):
        """User pays for an amount in another company."""
        # for another res.partner than the user's one
        route_values = self._prepare_pay_values(partner=self.user_company_b.partner_id)

        # Log in as user from Company A
        self.authenticate(self.user_company_a.login, self.user_company_a.login)

        # Pay in company B
        route_values['company_id'] = self.company_b.id

        tx_context = self.get_tx_checkout_context(**route_values)
        for key, val in tx_context.items():
            if key in route_values:
                if key == 'access_token':
                    continue # access_token was modified due to the change of partner.
                elif key == 'partner_id':
                    # The partner is replaced by the partner of the user paying.
                    self.assertEqual(val, self.user_company_a.partner_id.id)
                else:
                    self.assertEqual(val, route_values[key])

        available_acquirers = self.env['payment.acquirer'].sudo().browse(tx_context['acquirer_ids'])
        self.assertIn(self.acquirer_company_b, available_acquirers)
        self.assertEqual(available_acquirers.company_id, self.company_b)

        validation_values = {
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
        validation_values.update({
            'flow': 'direct',
            'payment_option_id': self.acquirer_company_b.id,
            'tokenization_requested': False,
        })
        with mute_logger('odoo.addons.payment.models.payment_transaction'):
            processing_values = self.get_processing_values(**validation_values)
        tx_sudo = self._get_tx(processing_values['reference'])

        # Tx values == given values
        self.assertEqual(tx_sudo.acquirer_id.id, self.acquirer_company_b.id)
        self.assertEqual(tx_sudo.amount, self.amount)
        self.assertEqual(tx_sudo.currency_id.id, self.currency.id)
        self.assertEqual(tx_sudo.partner_id.id, self.user_company_a.partner_id.id)
        self.assertEqual(tx_sudo.reference, self.reference)
        self.assertEqual(tx_sudo.company_id, self.company_b)
        # processing_values == given values
        self.assertEqual(processing_values['acquirer_id'], self.acquirer_company_b.id)
        self.assertEqual(processing_values['amount'], self.amount)
        self.assertEqual(processing_values['currency_id'], self.currency.id)
        self.assertEqual(processing_values['partner_id'], self.user_company_a.partner_id.id)
        self.assertEqual(processing_values['reference'], self.reference)

    def test_archive_token_logged_in_another_company(self):
        """User archives his token from another company."""
        # get user's token from company A
        token = self.create_token(partner_id=self.portal_partner.id)

        # assign user to another company
        company_b = self.env['res.company'].create({'name': 'Company B'})
        self.portal_user.write({'company_ids': [company_b.id], 'company_id': company_b.id})

        # Log in as portal user
        self.authenticate(self.portal_user.login, self.portal_user.login)

        # Archive token in company A
        url = self._build_url('/payment/archive_token')
        self._make_json_request(url, {'token_id': token.id})

        self.assertFalse(token.active)
