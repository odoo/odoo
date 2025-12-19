from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_fr_pdp.models.account_edi_xml_ubl_21_fr import PDP_CUSTOMIZATION_ID


class AccountMove(models.Model):
    _inherit = 'account.move'

    pdp_message_uuid = fields.Char(string='PDP message ID', copy=False)
    pdp_move_state = fields.Selection(
        selection=[
            ('ready', 'Ready to send'),
            ('to_send', 'Queued'),
            ('processing', 'Pending Reception'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        compute='_compute_pdp_move_state',
        store=True,
        string='PDP status',
        copy=False,
    )

    @api.depends('state')
    def _compute_pdp_move_state(self):
        for move in self:
            # We only support sale documents
            if not move.is_sale_document(include_receipts=True):
                continue
            # Roughly speaking we set the `pdp_move_state` to `ready` after posting
            # (in case the company and partner are on the PDP network and we have not sent it already)
            # and reset it to `False` when resetting to draft
            # (except if we have sent it already).
            if all([
                move.company_id.l10n_fr_pdp_proxy_state == 'receiver',
                move.commercial_partner_id.pdp_verification_state == 'valid',
                move.state == 'posted',
                not move.pdp_move_state,
            ]):
                move.pdp_move_state = 'ready'
            elif (
                move.state == 'draft'
                and move.pdp_move_state not in {'processing', 'done'}
            ):
                move.pdp_move_state = False
            # else we keep the old state

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        # Extends account_edi_ubl_cii
        customization_id = tree.find('{*}CustomizationID')
        if customization_id is not None and customization_id.text == PDP_CUSTOMIZATION_ID:
            return self.env['account.edi.xml.ubl_21_fr']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)

    def action_cancel_pdp_documents(self):
        # if the pdp_move_state is processing/done
        # then it means it has been already sent to pdp proxy and we can't cancel
        if any(move.pdp_move_state in {'processing', 'done'} for move in self):
            raise UserError(_("Cannot cancel an entry that has already been sent"))
        self.pdp_move_state = False
        self.sending_data = False
