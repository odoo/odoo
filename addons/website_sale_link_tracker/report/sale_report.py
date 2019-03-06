# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SaleReport(models.Model):
    _inherit = 'sale.report'

    campaign_id = fields.Many2one('utm.campaign', 'Campaign')
    medium_id = fields.Many2one('utm.medium', 'Medium')
    source_id = fields.Many2one('utm.source', 'Source')

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['campaign_id'] = ', s.campaign_id as campaign_id'
        fields['medium_id'] = ', s.medium_id as medium_id'
        fields['source_id'] = ', s.source_id as source_id'

        groupby += """, s.campaign_id
        , s.medium_id
        , s.source_id
        """

        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)
