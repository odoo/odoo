# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.sql import create_column, column_exists


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    no_followup = fields.Boolean(
        string="No Follow-Up",
        compute='_compute_no_followup',
        inverse='_inverse_no_followup',
        store=True,
        readonly=False,
        help="Exclude this journal item from follow-up reports.",
    )

    def _auto_init(self):
        if not column_exists(self.env.cr, 'account_move_line', 'no_followup'):
            create_column(self.env.cr, 'account_move_line', 'no_followup', 'boolean')
        return super()._auto_init()

    @api.depends('move_id.move_type')
    def _compute_no_followup(self):
        for aml in self:
            aml.no_followup = aml.move_id.is_entry() and not aml.move_id.origin_payment_id

    def _inverse_no_followup(self):
        # If one line of an invoice gets excluded from or included in the follow up report, we want all
        # payable/receivable lines of that invoice to do the same.
        for aml in self:
            move = aml.move_id
            if move.is_invoice():
                move.no_followup = aml.no_followup
