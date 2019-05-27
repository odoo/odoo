# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    website_id = fields.Many2one('website', readonly=True)

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['website_id'] = ", s.website_id as website_id"
        groupby += ', s.website_id'
        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)
