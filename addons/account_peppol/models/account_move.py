# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    peppol_message_uuid = fields.Char(string='PEPPOL message ID')
    peppol_move_state = fields.Selection(
        selection=[
            ('ready', 'Ready to send'),
            ('processing', 'Pending Reception'),
            ('canceled', 'Canceled'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        compute='_compute_peppol_move_state', store=True,
        string='PEPPOL status',
        copy=False,
    )
    peppol_is_demo_uuid = fields.Boolean(compute="_compute_peppol_is_demo_uuid")

    @api.depends('peppol_message_uuid')
    def _compute_peppol_is_demo_uuid(self):
        for move in self:
            move.peppol_is_demo_uuid = (move.peppol_message_uuid or '').startswith('demo_')

    @api.depends('state')
    def _compute_peppol_move_state(self):
        for move in self:
            if all([
                move.company_id.account_peppol_proxy_state == 'active',
                move.commercial_partner_id.account_peppol_is_endpoint_valid,
                move.state == 'posted',
                move.move_type in ('out_invoice', 'out_refund', 'out_receipt'),
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

    def _get_peppol_document(self):
        return self.edi_document_ids.filtered(lambda doc: doc.edi_format_id.code == 'peppol')[-1:]
