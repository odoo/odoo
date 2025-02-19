from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    nemhandel_message_uuid = fields.Char(string='Nemhandel message ID')
    nemhandel_move_state = fields.Selection(
        selection=[
            ('ready', 'Ready to send'),
            ('to_send', 'Queued'),
            ('skipped', 'Skipped'),
            ('processing', 'Pending Reception'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        compute='_compute_nemhandel_move_state', store=True,
        string='Nemhandel status',
        copy=False,
    )

    def _need_oioubl_21_xml(self):
        self.ensure_one()

        res = super()._need_ubl_cii_xml()
        partner = self.partner_id.commercial_partner_id
        if partner.ubl_cii_format != 'oioubl_21':
            return res
        if not partner.nemhandel_identifier_type or not partner.nemhandel_identifier_value:
            return False
        if partner.nemhandel_verification_label == 'not_verified':
            partner.button_nemhandel_check_partner_endpoint()
        return res and partner.nemhandel_is_endpoint_valid

    def action_cancel_nemhandel_documents(self):
        # if the nemhandel_move_state is processing/done
        # then it means it has been already sent to nemhandel proxy and we can't cancel
        if any(move.nemhandel_move_state in {'processing', 'done'} for move in self):
            raise UserError(_("Cannot cancel an entry that has already been sent to Nemhandel"))
        self.nemhandel_move_state = 'canceled'
        self.send_and_print_values = False

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
        customization_id = tree.find('{*}CustomizationID')
        if customization_id is not None and 'OIOUBL-2' in customization_id.text:
            return self.env['account.edi.xml.oioubl_21']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)
