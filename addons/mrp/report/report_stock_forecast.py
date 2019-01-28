# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ReportStockForecat(models.Model):
    _inherit = 'report.stock.forecast'

    production_id = fields.Many2one('mrp.production', string='Manufacturing Order', readonly=True)

    @api.model
    def _select(self):
        select_query = super(ReportStockForecat, self)._select()
        return select_query + ", mo.id AS production_id"

    @api.model
    def _left_join(self):
        left_join_query = super(ReportStockForecat, self)._left_join()
        return left_join_query + """LEFT JOIN
            mrp_production mo ON final.reference=mo.name
        """

    @api.model
    def _groupby(self):
        groupby_query = super(ReportStockForecat, self)._groupby()
        return groupby_query + ",mo.id"
