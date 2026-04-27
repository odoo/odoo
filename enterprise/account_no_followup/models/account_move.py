# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    no_followup = fields.Boolean(
        string="No Follow-Up",
        compute='_compute_no_followup',
        inverse='_inverse_no_followup',
        readonly=False,
        help="Exclude this journal entry from follow-up reports."
    )

    @api.depends('line_ids.no_followup')
    def _compute_no_followup(self):
        for move in self:
            if move.is_invoice():
                move.no_followup = move.line_ids.filtered(
                    lambda line: line.account_type in ('asset_receivable', 'liability_payable'),
                )[:1].no_followup
            else:
                move.no_followup = True

    def _inverse_no_followup(self):
        for move in self:
            if move.is_invoice():
                move.line_ids.filtered(
                    lambda line: line.account_type in ('asset_receivable', 'liability_payable'),
                ).no_followup = move.no_followup
