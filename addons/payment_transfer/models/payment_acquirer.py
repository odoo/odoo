# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(
        selection_add=[('transfer', "Wire Transfer")], default='transfer',
        ondelete={'transfer': 'set default'})
    qr_code = fields.Boolean(
        string="Enable QR Codes", help="Enable the use of QR-codes when paying by wire transfer.")

    @api.depends('provider')
    def _compute_view_configuration_fields(self):
        """ Override of payment to hide the credentials page.

        :return: None
        """
        super()._compute_view_configuration_fields()
        self.filtered(lambda acq: acq.provider == 'transfer').write({
            'show_credentials_page': False,
            'show_payment_icon_ids': False,
            'show_pre_msg': False,
            'show_done_msg': False,
            'show_cancel_msg': False,
        })

    @api.model_create_multi
    def create(self, values_list):
        """ Make sure to have a pending_msg set. """
        # This is done here and not in a default to have access to all required values.
        acquirers = super().create(values_list)
        acquirers._transfer_ensure_pending_msg_is_set()
        return acquirers

    def write(self, values):
        """ Make sure to have a pending_msg set. """
        # This is done here and not in a default to have access to all required values.
        res = super().write(values)
        self._transfer_ensure_pending_msg_is_set()
        return res

    def _transfer_ensure_pending_msg_is_set(self):
        for acquirer in self.filtered(lambda a: a.provider == 'transfer' and not a.pending_msg):
            company_id = acquirer.company_id.id
            # filter only bank accounts marked as visible
            accounts = self.env['account.journal'].search([
                ('type', '=', 'bank'), ('company_id', '=', company_id)
            ]).bank_account_id
            acquirer.pending_msg = f'<div>' \
                f'<h3>{_("Please use the following transfer details")}</h3>' \
                f'<h4>{_("Bank Account") if len(accounts) == 1 else _("Bank Accounts")}</h4>' \
                f'<ul>{"".join(f"<li>{account.display_name}</li>" for account in accounts)}</ul>' \
                f'<h4>{_("Communication")}</h4>' \
                f'<p>{_("Please use the order name as communication reference.")}</p>' \
                f'</div>'
