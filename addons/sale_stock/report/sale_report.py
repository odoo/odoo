# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = "sale.report"

    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)

    def _select(self):
        return super(SaleReport, self)._select() + ", so.warehouse_id as warehouse_id"

    def _group_by(self):
        return super(SaleReport, self)._group_by() + ", so.warehouse_id"

    def get_main_request_select(self):
        return super(SaleReport, self).get_main_request_select() + ", warehouse_id"
