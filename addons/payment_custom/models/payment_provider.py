# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.osv.expression import AND

from odoo.addons.payment_custom import const


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    _sql_constraints = [(
        'custom_providers_setup',
        "CHECK(custom_mode IS NULL OR (code = 'custom' AND custom_mode IS NOT NULL))",
        "Only custom providers should have a custom mode."
    )]

    code = fields.Selection(
        selection_add=[('custom', "Custom")], ondelete={'custom': 'set default'}
    )
    custom_mode = fields.Selection(
        string="Custom Mode",
        selection=[('wire_transfer', "Wire Transfer")],
        required_if_provider='custom',
    )
    qr_code = fields.Boolean(
        string="Enable QR Codes", help="Enable the use of QR-codes when paying by wire transfer.")

    @api.model_create_multi
    def create(self, values_list):
        providers = super().create(values_list)
        providers.filtered(lambda p: p.custom_mode == 'wire_transfer').pending_msg = None
        return providers

    def action_recompute_pending_msg(self):
        """ Recompute the pending message to include the existing bank accounts. """
        account_payment_module = self.env['ir.module.module']._get('account_payment')
        if account_payment_module.state == 'installed':
            for provider in self.filtered(lambda p: p.custom_mode == 'wire_transfer'):
                company_id = provider.company_id.id
                accounts = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company_id),
                    ('type', '=', 'bank'),
                ]).bank_account_id
                account_names = "".join(f"<li><pre>{account.display_name}</pre></li>" for account in accounts)
                provider.pending_msg = f'<div>' \
                    f'<h5>{_("Please use the following transfer details")}</h5>' \
                    f'<p><br></p>' \
                    f'<h6>{_("Bank Account") if len(accounts) == 1 else _("Bank Accounts")}</h6>' \
                    f'<ul>{account_names}</ul>'\
                    f'<p><br></p>' \
                    f'</div>'

    @api.model
    def _get_removal_domain(self, provider_code, custom_mode='', **kwargs):
        res = super()._get_removal_domain(provider_code, custom_mode=custom_mode, **kwargs)
        if provider_code == 'custom' and custom_mode:
            return AND([res, [('custom_mode', '=', custom_mode)]])
        return res

    @api.model
    def _get_removal_values(self):
        """ Override of `payment` to nullify the `custom_mode` field. """
        res = super()._get_removal_values()
        res['custom_mode'] = None
        return res

    def _transfer_ensure_pending_msg_is_set(self):
        transfer_providers_without_msg = self.filtered(
            lambda p: p.custom_mode == 'wire_transfer' and not p.pending_msg
        )
        if transfer_providers_without_msg:
            transfer_providers_without_msg.action_recompute_pending_msg()

    def _get_default_payment_method_codes(self):
        """ Override of `payment` to return the default payment method codes. """
        default_codes = super()._get_default_payment_method_codes()
        if self.code != 'custom' or self.custom_mode != 'wire_transfer':
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES
