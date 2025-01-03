# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.account.models.company import PEPPOL_DEFAULT_COUNTRIES


class AccountMove(models.Model):
    _inherit = 'account.move'

    peppol_message_uuid = fields.Char(string='PEPPOL message ID')
    peppol_move_state = fields.Selection(
        selection=[
            ('ready', 'Ready to send'),
            ('to_send', 'Queued'),
            ('skipped', 'Skipped'),
            ('processing', 'Pending Reception'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        compute='_compute_peppol_move_state', store=True,
        string='PEPPOL status',
        copy=False,
    )
    peppol_notify_pending = fields.Boolean(
        string="Notify User About Peppol Invoice",
        default=False,
        help="Indicates whether this invoice requires user notification about its receipt via Peppol",
    )

    def action_cancel_peppol_documents(self):
        # if the peppol_move_state is processing/done
        # then it means it has been already sent to peppol proxy and we can't cancel
        if any(move.peppol_move_state in {'processing', 'done'} for move in self):
            raise UserError(_("Cannot cancel an entry that has already been sent to PEPPOL"))
        self.peppol_move_state = False
        self.sending_data = False

    @api.depends('state')
    def _compute_peppol_move_state(self):
        can_send = self.env['account_edi_proxy_client.user']._get_can_send_domain()
        for move in self:
            if all([
                move.company_id.account_peppol_proxy_state in can_send,
                move.commercial_partner_id.peppol_verification_state == 'valid',
                move.state == 'posted',
                move.is_sale_document(include_receipts=True),
                not move.peppol_move_state,
            ]):
                move.peppol_move_state = 'ready'
            elif (
                move.state == 'draft'
                and move.is_sale_document(include_receipts=True)
                and move.peppol_move_state not in ('processing', 'done')
            ):
                move.peppol_move_state = False
            else:
                move.peppol_move_state = move.peppol_move_state

    def _notify_by_email_prepare_rendering_context(self, message, **kwargs):
        render_context = super()._notify_by_email_prepare_rendering_context(message, **kwargs)
        invoice = render_context['record']
        invoice_country = invoice.commercial_partner_id.country_code
        if invoice_country in PEPPOL_DEFAULT_COUNTRIES:
            render_context['peppol_info'] = {
                'peppol_country': invoice_country,
                'is_peppol_sent': invoice.peppol_move_state in ('processing', 'done'),
            }
        return render_context
