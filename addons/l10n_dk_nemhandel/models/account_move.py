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
            ('error', 'Error'),
        ],
        compute='_compute_nemhandel_move_state',
        store=True,
        string='Nemhandel status',
        copy=False,
    )

    @api.depends('state')
    def _compute_nemhandel_move_state(self):
        for move in self:
            if all([
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
