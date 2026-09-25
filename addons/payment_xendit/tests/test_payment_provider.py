# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.payment_xendit.tests.common import XenditCommon


@tagged('post_install', '-at_install')
class TestPaymentProvider(XenditCommon):
    def test_incompatible_with_unsupported_currencies(self):
        """ Test that Xendit providers are filtered out from compatible providers when the currency
        is not supported. """
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref('base.AFN').id
        )
        self.assertNotIn(self.xendit, compatible_providers)

    def test_validation_currency_prefers_company_currency(self):
        """ Test that the validation currency is the company's own currency when Xendit supports
        it, since payment channels are activated per country and an unrelated currency picked by
        the generic fallback could be rejected. """
        currency_php = self.env.ref('base.PHP')
        company_php = self.env['res.company'].create({
            'name': "Xendit PH test company", 'currency_id': currency_php.id,
        })
        xendit_php = self.xendit.copy({'company_id': company_php.id})
        self.assertEqual(xendit_php._get_validation_currency(), currency_php)

    def test_webhook_migration_notice_is_only_sent_once(self):
        """ Test that admins are reminded of the webhook migration only once, so that they aren't
        notified again after marking the reminder as done. """
        def get_notices():
            return self.env['mail.activity'].search([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', self.xendit.company_id.partner_id.id),
                ('summary', '=', "Update the Xendit webhook configuration"),
            ])

        self.env['payment.provider']._autovacuum_notify_xendit_webhook_migration()
        notices = get_notices()
        self.assertIn(self.env.ref('base.user_admin'), notices.user_id)

        notices.action_done()
        self.env['payment.provider']._autovacuum_notify_xendit_webhook_migration()
        self.assertFalse(get_notices())
