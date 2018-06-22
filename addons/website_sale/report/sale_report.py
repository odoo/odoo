# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    website_id = fields.Many2one('website', readonly=True)

    def _select(self):
        select = super(SaleReport, self)._select()
        select += ', s.website_id as website_id'

        return select

    def _group_by(self):
        group_by = super(SaleReport, self)._group_by()
        group_by += ', s.website_id'

        return group_by
