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

    @api.depends('code')
    def _compute_view_configuration_fields(self):
        """ Override of payment to hide the credentials page.

        :return: None
        """
        super()._compute_view_configuration_fields()
        self.filtered(lambda p: p.code == 'custom').update({
            'show_credentials_page': False,
            'show_payment_icon_ids': False,
            'show_pre_msg': False,
            'show_done_msg': False,
            'show_cancel_msg': False,
        })

    def _transfer_ensure_pending_msg_is_set(self):
        transfer_providers_without_msg = self.filtered(
            lambda p: p.code == 'custom' and not p.pending_msg)
        if not transfer_providers_without_msg:
            return

        account_payment = self.env['ir.module.module']._get('account_payment')
        if account_payment.state != 'installed':
            return

        for provider in transfer_providers_without_msg:
            company_id = provider.company_id.id
            # filter only bank accounts marked as visible
            accounts = self.env['account.journal'].search([
                ('type', '=', 'bank'), ('company_id', '=', company_id)
            ]).bank_account_id
            provider.pending_msg = f'<div>' \
                f'<h3>{_("Please use the following transfer details")}</h3>' \
                f'<h4>{_("Bank Account") if len(accounts) == 1 else _("Bank Accounts")}</h4>' \
                f'<ul>{"".join(f"<li>{account.display_name}</li>" for account in accounts)}</ul>' \
                f'<h4>{_("Communication")}</h4>' \
                f'<p>{_("Please use the order name as communication reference.")}</p>' \
                f'</div>'
