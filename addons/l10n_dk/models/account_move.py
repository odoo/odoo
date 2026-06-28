from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    nemhandel_message_uuid = fields.Char(string='Nemhandel message ID', copy=False)
    nemhandel_move_state = fields.Selection(
        selection=[
            ('ready', 'Ready to send'),
            ('to_send', 'Queued'),
            ('processing', 'Pending Reception'),
            ('done', 'Done'),
            ('BusinessAccept', 'Approved'),
            ('BusinessReject', 'Rejected'),
            ('error', 'Error'),
        ],
        compute='_compute_nemhandel_move_state',
        store=True,
        string='Nemhandel status',
        copy=False,
    )
    nemhandel_response_ids = fields.One2many('nemhandel.response', 'move_id')
    nemhandel_can_send_response = fields.Boolean(compute='_compute_nemhandel_can_send_response')

    @api.depends('state', 'nemhandel_response_ids.nemhandel_state')
    def _compute_nemhandel_move_state(self):
        for move in self:
            if valid_status := move.nemhandel_response_ids.filtered(lambda r: r.nemhandel_state == 'done').mapped('response_code'):
                move.nemhandel_move_state = valid_status[0]
            elif all([
                move.company_id.l10n_dk_nemhandel_proxy_state == 'receiver',
                move.commercial_partner_id.nemhandel_verification_state == 'valid',
                move.state == 'posted',
                move.is_sale_document(include_receipts=True),
                not move.nemhandel_move_state,
            ]):
                move.nemhandel_move_state = 'ready'
            elif (
                move.state == 'draft'
                and move.is_sale_document(include_receipts=True)
                and move.nemhandel_move_state not in {'processing', 'done'}
            ):
                move.nemhandel_move_state = False
            else:
                move.nemhandel_move_state = move.nemhandel_move_state

    @api.depends("nemhandel_response_ids.nemhandel_state")
    def _compute_nemhandel_can_send_response(self):
        for move in self:
            move.nemhandel_can_send_response = (
                move.nemhandel_message_uuid
                and move.move_type in ('in_invoice', 'in_refund')
                and not move.nemhandel_response_ids.filtered(
                    lambda r: r.nemhandel_state == 'not_serviced' or r.nemhandel_state != 'error',
                )
                and move.partner_id.nemhandel_response_support
            )

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        # Deprecated
        # Extends account_edi_ubl_cii
        customization_id = tree.find('{*}CustomizationID')
        if customization_id is not None and 'OIOUBL-2' in customization_id.text:
            return self.env['account.edi.xml.oioubl_21']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)

    def _get_import_file_type(self, file_data):
        """ Identify OIOUBL files. """
        # EXTENDS 'account'
        if (
            file_data['xml_tree'] is not None
            and (customization_id := file_data['xml_tree'].findtext('{*}CustomizationID'))
            and customization_id == 'OIOUBL-2.1'
        ):
            return 'account.edi.xml.oioubl_21'

        return super()._get_import_file_type(file_data)

    def _post(self, soft=True):
        res = super()._post(soft)
        self.action_nemhandel_send_approval_response()
        return res

    def action_cancel_nemhandel_documents(self):
        # if the nemhandel_move_state is processing/done
        # then it means it has been already sent to nemhandel proxy and we can't cancel
        if any(move.nemhandel_move_state in {'processing', 'done'} for move in self):
            raise UserError(_("Cannot cancel an entry that has already been sent to Nemhandel"))
        self.nemhandel_move_state = False
        self.sending_data = False

    def action_send_and_print(self):
        for move in self:
            move.commercial_partner_id.button_nemhandel_check_partner_endpoint(company=move.company_id)
        return super().action_send_and_print()

    def _need_ubl_cii_xml(self, ubl_cii_format):
        res = super()._need_ubl_cii_xml(ubl_cii_format)
        if ubl_cii_format == 'oioubl_21' and (not self.partner_id.vat or self.partner_id._get_nemhandel_verification_state(ubl_cii_format) != 'valid'):
            return False
        return res

    def button_cancel(self):
        res = super().button_cancel()
        if action := self.action_nemhandel_open_rejection_wizard():
            action['context'] = {'cancel_res': res}
            return action
        return res

    def action_nemhandel_send_approval_response(self):
        moves_to_respond_by_company = self.filtered('nemhandel_can_send_response').grouped('company_id')
        for company in moves_to_respond_by_company:
            company.nemhandel_edi_user._nemhandel_send_response(moves_to_respond_by_company[company], 'BusinessAccept')

    def action_nemhandel_open_rejection_wizard(self):
        nemhandel_moves = self.filtered('nemhandel_can_send_response')
        if nemhandel_moves:
            return {
                'type': 'ir.actions.act_window',
                'name': self.env._("Reject Nemhandel Document"),
                'view_mode': 'form',
                'res_model': 'nemhandel.rejection.wizard',
                'target': 'new',
                'res_id': self.env['nemhandel.rejection.wizard'].create({'move_ids': nemhandel_moves.ids}).id,
            }
        return {}

    def action_open_nemhandel_reponses(self):
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._("Nemhandel Responses"),
            'view_mode': 'list',
            'res_model': 'nemhandel.response',
            'domain': [('id', 'in', self.nemhandel_response_ids.ids)],
        }
