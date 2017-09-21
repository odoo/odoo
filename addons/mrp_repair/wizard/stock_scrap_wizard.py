
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class StockScrapWizard(models.TransientModel):
    _inherit = 'stock.scrap.wizard'

    repair_id = fields.Many2one('mrp.repair', string='Repair')

    def action_done(self):
        self.ensure_one()
        if self.repair_id:
            return self.repair_id.action_repair_confirm()
        return super(StockScrapWizard, self).action_done()
