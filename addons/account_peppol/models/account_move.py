# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    peppol_message_uuid = fields.Char(string='PEPPOL message ID')
    peppol_move_state = fields.Selection(
        selection=[
            ('to_send', 'To Send'),
            ('processing', 'Processing'),
            ('canceled', 'Canceled'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        string='PEPPOL status',
        copy=False,
        readonly=True,
    )
    ref = fields.Char(compute='_compute_payment_reference', readonly=False, store=True)

    def _compute_payment_reference(self):
        # EXTENDS account
        super()._compute_payment_reference()
        for move in self.filtered(lambda m: (
            m.state != 'cancelled'
            and m.move_type in ('out_invoice', 'out_refund')
            and not m.ref
        )):
            company = move.company_id or move.journal_id.company_id
            if company.is_account_peppol_participant:
                move.ref = move.payment_reference

    def action_cancel_peppol_documents(self):
        # if the peppol_move_state is processing/done
        # then it means it has been already sent to peppol proxy and we can't cancel
        if any(move.peppol_move_state in {'processing', 'done'} for move in self):
            raise UserError(_("Cannot cancel an entry that has already been sent to PEPPOL"))
        self.peppol_move_state = 'canceled'
