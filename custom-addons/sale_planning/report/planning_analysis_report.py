# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class PlanningAnalysisReport(models.Model):
    _inherit = "planning.analysis.report"

    sale_order_id = fields.Many2one("sale.order", string="Sales Order", readonly=True)
    sale_line_id = fields.Many2one("sale.order.line", string="Sales Order Item", readonly=True)
    # Not using a related as we want to avoid having a depends.
    role_product_ids = fields.One2many('product.template', compute='_compute_role_product_ids', search='_search_role_product_ids')

    def _compute_role_product_ids(self):
        for slot in self:
            slot.role_product_ids = slot.role_id.product_ids

    @api.model
    def _search_role_product_ids(self, operator, value):
        return [('role_id.product_ids', operator, value)]

    @property
    def _table_query(self):
        return "%s %s %s %s %s" % (self._select(), self._from(), self._join(), self._where(), self._group_by())

    @api.model
    def _select(self):
        return super()._select() + """,
            S.sale_order_id AS sale_order_id,
            S.sale_line_id AS sale_line_id
        """

    @api.model
    def _where(self):
        return """
            WHERE start_datetime IS NOT NULL
        """

    @api.model
    def _group_by(self):
        return super()._group_by() + """,
            S.sale_order_id, S.sale_line_id
        """
