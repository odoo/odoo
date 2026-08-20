# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _compute_cogs_move_ids(self):
        super()._compute_cogs_move_ids()
        for aml in self:
            finished_move_ids = set()
            for m in aml.purchase_line_id.move_ids:
                if mo := m._get_subcontract_production():
                    finished_move_ids |= set(mo.move_finished_ids.filtered(lambda mf: mf.product_id == m.product_id).ids)
            if finished_move_ids:
                aml.cogs_move_ids |= self.env['stock.move'].browse(finished_move_ids)
