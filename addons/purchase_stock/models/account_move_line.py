# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('purchase_line_id.move_ids.state')
    def _compute_cogs_move_ids(self):
        super()._compute_cogs_move_ids()
        for aml in self:
            if aml.purchase_line_id:
                aml.cogs_move_ids = aml.purchase_line_id.move_ids.filtered(lambda m: m.is_valued)
