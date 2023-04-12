# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountMove(models.Model):

    _inherit = 'account.move'

    withholding_ids = fields.One2many(
        'account.move.line', 'move_id', string='Withholdings',
        copy=False, readonly=True, domain=[('tax_line_id', '!=', False)],
        states={'draft': [('readonly', False)]})
