# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.account.models.company import PEPPOL_MAILING_COUNTRIES


class AccountMove(models.Model):
    _inherit = 'account.move'

    peppol_message_uuid = fields.Char(string='PEPPOL message ID')
    peppol_move_state = fields.Selection(
        selection=[
            ('ready', 'Ready to send'),
            ('to_send', 'Queued'),
            ('skipped', 'Skipped'),  # TODO remove this state in master, we now put a regular error.
            ('processing', 'Pending Reception'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        compute='_compute_peppol_move_state', store=True,
        string='PEPPOL status',
        copy=False,
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

    def _notify_by_email_prepare_rendering_context(self, message, msg_vals=False, model_description=False,
                                                   force_email_company=False, force_email_lang=False):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message, msg_vals=msg_vals, model_description=model_description,
            force_email_company=force_email_company, force_email_lang=force_email_lang
        )
        invoice = render_context['record']
        invoice_country = invoice.commercial_partner_id.country_code
        company_country = invoice.company_id.country_code
        can_send = self.env['account_edi_proxy_client.user']._get_can_send_domain()
        company_on_peppol = invoice.company_id.account_peppol_proxy_state in can_send
        if company_on_peppol and company_country in PEPPOL_MAILING_COUNTRIES and invoice_country in PEPPOL_MAILING_COUNTRIES:
            render_context['peppol_info'] = {
                'peppol_country': invoice_country,
                'is_peppol_sent': invoice.peppol_move_state in ('processing', 'done'),
                'partner_on_peppol': invoice.commercial_partner_id.peppol_verification_state in ('valid', 'not_valid_format'),
            }
        return render_context
