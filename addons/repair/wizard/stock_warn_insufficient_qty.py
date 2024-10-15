# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import stock


class StockWarnInsufficientQtyRepair(models.TransientModel, stock.StockWarnInsufficientQty):
    _description = 'Warn Insufficient Repair Quantity'

    repair_id = fields.Many2one('repair.order', string='Repair')

    def _get_reference_document_company_id(self):
        return self.repair_id.company_id

    def action_done(self):
        self.ensure_one()
        return self.repair_id._action_repair_confirm()
