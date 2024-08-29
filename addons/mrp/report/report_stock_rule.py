# -*- coding: utf-8 -*-
from odoo.addons import stock
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ReportStockReportStockRule(models.AbstractModel, stock.ReportStockReportStockRule):
    _name = "report.stock.report_stock_rule"


    @api.model
    def _get_rule_loc(self, rule, product_id):
        """ We override this method to handle manufacture rule which do not have a location_src_id.
        """
        res = super()._get_rule_loc(rule, product_id)
        if rule.action == 'manufacture':
            res['source'] = product_id.property_stock_production
        return res
