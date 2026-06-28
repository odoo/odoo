# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.account.models.company import PEPPOL_MAILING_COUNTRIES


class AccountMove(models.Model):
    _inherit = 'account.move'

    peppol_message_uuid = fields.Char(string='Peppol message ID', copy=False)
    peppol_move_state = fields.Selection(
        selection=[
            ('ready', 'Ready to send'),
            ('to_send', 'Queued'),
            ('processing', 'Pending Reception'),
            ('done', 'Done'),
            ('AB', 'Received'),
            ('AP', 'Approved'),
            ('RE', 'Rejected'),
            ('error', 'Error'),
        ],
        compute='_compute_peppol_move_state', store=True,
        string='Peppol status',
        copy=False,
    )
    peppol_is_sent = fields.Boolean(compute='_compute_peppol_is_sent')
    peppol_response_ids = fields.One2many('account.peppol.response', 'move_id')
    peppol_can_send_response = fields.Boolean(compute='_compute_peppol_can_send_response')

    def button_cancel(self):
        res = super().button_cancel()
        if action := self.action_peppol_open_rejection_wizard():
            action['context'] = {'cancel_res': res}
            return action
        return res

    def action_peppol_send_approval_response(self):
        moves_to_respond_by_company = self.filtered('peppol_can_send_response').grouped('company_id')
        for company in moves_to_respond_by_company:
            company.account_peppol_edi_user._peppol_send_response(moves_to_respond_by_company[company], 'AP')

    def action_peppol_open_rejection_wizard(self):
        peppol_moves = self.filtered('peppol_can_send_response')
        if peppol_moves:
            return {
                'type': 'ir.actions.act_window',
                'name': self.env._("Reject Peppol Document"),
                'view_mode': 'form',
                'res_model': 'account.peppol.rejection.wizard',
                'target': 'new',
                'res_id': self.env['account.peppol.rejection.wizard'].create({'move_ids': peppol_moves.ids}).id,
            }
        return {}

    def action_open_peppol_reponses(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Peppol Responses"),
            'view_mode': 'list',
            'res_model': 'account.peppol.response',
            'domain': [('id', 'in', self.peppol_response_ids.ids)],
        }

    def action_send_and_print(self):
        for move in self:
            move.commercial_partner_id.button_account_peppol_check_partner_endpoint(company=move.company_id)
        return super().action_send_and_print()

    def action_cancel_peppol_documents(self):
        # if the peppol_move_state is processing/done/has been replied to
        # then it means it has been already sent to peppol proxy and we can't cancel
        if any(move.peppol_is_sent for move in self):
            raise UserError(_("Cannot cancel an entry that has already been sent to Peppol"))
        self.peppol_move_state = False
        self.sending_data = False

    def _compute_display_send_button(self):
        # EXTENDS 'account'
        super()._compute_display_send_button()
        for move in self:
            if move._is_exportable_as_self_invoice():
                move.display_send_button = True

    @api.depends('state', 'peppol_response_ids.peppol_state')
    def _compute_peppol_move_state(self):
        for move in self:
            if valid_statuses := move.peppol_response_ids.filtered(lambda r: r.peppol_state == 'done').mapped('response_code'):
                if 'RE' in valid_statuses:
                    move.peppol_move_state = 'RE'
                elif any(status in {'AP', 'PD'} for status in valid_statuses):
                    move.peppol_move_state = 'AP'
                else:
                    move.peppol_move_state = 'AB'
            elif all([
                move.company_id.peppol_can_send,
                move.commercial_partner_id.peppol_verification_state == 'valid',
                move.state == 'posted',
                move.is_sale_document(include_receipts=True),
                not move.peppol_move_state,
            ]):
                move.peppol_move_state = 'ready'
            elif (
                move.state == 'draft'
                and move.is_sale_document(include_receipts=True)
                and not move.peppol_is_sent
            ):
                move.peppol_move_state = False
            else:
                move.peppol_move_state = move.peppol_move_state

    @api.depends('peppol_move_state')
    def _compute_peppol_is_sent(self):
        for move in self:
            move.peppol_is_sent = move.peppol_move_state not in {False, 'ready', 'to_send', 'error'}

    @api.depends("peppol_response_ids.peppol_state")
    def _compute_peppol_can_send_response(self):
        for move in self:
            move.peppol_can_send_response = (
                move.peppol_message_uuid
                and move.move_type in ('in_invoice', 'in_refund')
                and not move.peppol_response_ids.filtered(
                    lambda r: r.peppol_state == 'not_serviced' or (r.peppol_state != 'error' and r.response_code in ('AP', 'RE')),
                )
                and move.partner_id.peppol_response_support
            )

    def _notify_by_email_prepare_rendering_context(self, message, model_description=False,
                                                   force_email_company=False, force_email_lang=False,
                                                   force_record_name=False, force_header=False, force_footer=False):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message, model_description=model_description,
            force_email_company=force_email_company, force_email_lang=force_email_lang,
            force_record_name=force_record_name, force_header=force_header, force_footer=force_footer,
        )
        invoice = render_context['record']
        invoice_country = invoice.commercial_partner_id.country_code
        company_country = invoice.company_id.country_code
        can_send = self.env['account_edi_proxy_client.user']._get_can_send_domain()
        company_on_peppol = invoice.company_id.account_peppol_proxy_state in can_send
        if company_on_peppol and company_country in PEPPOL_MAILING_COUNTRIES and invoice_country in PEPPOL_MAILING_COUNTRIES:
            render_context['peppol_info'] = {
                'peppol_country': invoice_country,
                'is_peppol_sent': invoice.peppol_is_sent,
                'is_partner_b2c': invoice.commercial_partner_id._is_vat_void(invoice.commercial_partner_id.vat),
                'partner_on_peppol': invoice.commercial_partner_id.peppol_verification_state in ('valid', 'not_valid_format'),
            }
        return render_context

    def _post(self, soft=True):
        res = super()._post(soft)
        self.action_peppol_send_approval_response()
        return res

    def action_peppol_cancel_and_remove_sequence(self):
        self.button_cancel()
        self.write({'name': '/'})

    def action_peppol_reset_documents(self, ids_to_delete=None):
        self.filtered(lambda m: m.state == 'draft').action_peppol_cancel_and_remove_sequence()
        self.filtered(lambda m: m.state not in ('draft', 'cancel') and not m.inalterable_hash).button_draft()
        if ids_to_delete:
            self.env['account.move'].browse(ids_to_delete).exists().unlink()
