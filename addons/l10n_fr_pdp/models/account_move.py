from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_fr_pdp.models.account_edi_xml_ubl_21_fr import PDP_CUSTOMIZATION_ID

UNSENT_PDP_MOVE_STATES = {'ready', 'to_send', 'error'}


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
            ('submitted', 'Submitted'),
            ('received', 'Received'),
            ('made_available', 'Made Available'),
            ('in_hand', 'In Hand'),
            ('approved', 'Approved'),
            ('contested', 'Contested'),
            ('refused', 'Refused'),
            ('payment_sent', 'Payment Sent'),
            ('paid', 'Paid'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        compute='_compute_pdp_move_state',
        store=True,
        string='PDP status',
        copy=False,
    )
    pdp_response_ids = fields.One2many('pdp.response', 'move_id')
    pdp_can_send_response = fields.Boolean(compute='_compute_pdp_can_send_response')

    @api.depends('state', 'pdp_response_ids')
    def _compute_pdp_move_state(self):
        for move in self:
            # Handle sale and purchase documents in case we sent / received the document.
            if response_status := move._pdp_get_response_status():
                move.pdp_move_state = response_status
                continue

            if not move.is_sale_document(include_receipts=True):
                continue
            # Handle the cases that we have not sent the move yet.
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
                and move.pdp_move_state in UNSENT_PDP_MOVE_STATES
            ):
                move.pdp_move_state = False

    @api.depends("pdp_message_uuid")
    def _compute_pdp_can_send_response(self):
        for move in self:
            move.pdp_can_send_response = bool(move.pdp_message_uuid)

    def _pdp_get_response_status(self):
        """Return the PDP response status of the message"""
        self.ensure_one()
        # Non-PDP messages do not have a response status
        if not self.pdp_message_uuid:
            return False

        # Take the latest response status if we have any
        # TODO: I suppose "partially paid" is possible? Since 'paid' lifecyle does not have to be the full amount
        response_message = self.pdp_response_ids.filtered(lambda l: l.pdp_state == 'done')
        if latest_status := response_message.sorted(lambda l: (l.issue_date or datetime.min, l.id), reverse=True)[:1].response_code:
            return latest_status

        # We have received the purchase document so it is 'in_hand'
        if self.is_purchase_document(include_receipts=True):
            return 'in_hand'

        # We don't have any fallback for sale documents
        return False

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
        if any(move.pdp_move_state not in UNSENT_PDP_MOVE_STATES for move in self):
            raise UserError(_("Cannot cancel an entry that has already been sent"))
        self.pdp_move_state = False
        self.sending_data = False

    def action_pdp_open_response_wizard(self):
        pdp_moves = self.filtered('pdp_can_send_response')
        if not pdp_moves:
            raise UserError(_("Cannot send response for any of the journal entries."))
        wizard = self.env['pdp.response.wizard'].create({'move_ids': pdp_moves.ids})
        return wizard._get_records_action(name="Send Response Message", target='new')
