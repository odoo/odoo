# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


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

    @api.depends('code')
    def _compute_view_configuration_fields(self):
        """ Override of payment to hide the credentials page.

        :return: None
        """
        super()._compute_view_configuration_fields()
        self.filtered(lambda p: p.code == 'custom').update({
            'show_credentials_page': False,
            'show_pre_msg': False,
            'show_done_msg': False,
            'show_cancel_msg': False,
        })

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
