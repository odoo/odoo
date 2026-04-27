# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    slot_id = fields.Many2one('planning.slot', 'Planning Shift', index='btree_not_null')
