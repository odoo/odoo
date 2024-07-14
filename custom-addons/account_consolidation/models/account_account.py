# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression


class Account(models.Model):
    _inherit = 'account.account'

    consolidation_account_ids = fields.Many2many('consolidation.account')
    consolidation_account_chart_filtered_ids = fields.Many2many('consolidation.account',
        readonly=False,
        compute="_compute_filtered_consolidation_account_ids",
        search="_search_filtered_consolidation_account_ids",
        inverse='_inverse_filtered_consolidation_account_ids',
        )
    consolidation_color = fields.Integer('Color', related="company_id.consolidation_color", readonly=True)

    @api.depends('consolidation_account_ids')
    @api.depends_context('chart_id')
    def _compute_filtered_consolidation_account_ids(self):
        """
        Compute filtered_consolidation_account_ids field which is the list of consolidation account ids linked to this
        account filtered to only contains the ones linked to the chart contained in the context
        """
        chart_id = self.env.context.get('chart_id')
        for record in self:
            consolidation_account_ids = record.consolidation_account_ids
            if chart_id:
                consolidation_account_ids = consolidation_account_ids.filtered(
                    lambda x: x.chart_id.id == chart_id)
            record.consolidation_account_chart_filtered_ids = consolidation_account_ids

    def _inverse_filtered_consolidation_account_ids(self):
        """
        Allow the write back of filtered field to the not filtered one. This method makes sure to not erase the
        consolidation accounts from other charts.
        """
        chart_id = self.env.context.get('chart_id', False)
        for record in self:
            from_other_charts = record.consolidation_account_ids
            if chart_id:
                from_other_charts = from_other_charts.filtered(lambda x: x.chart_id.id != chart_id)
            record.consolidation_account_ids = record.consolidation_account_chart_filtered_ids.union(from_other_charts)

    def _search_filtered_consolidation_account_ids(self, operator, operand):
        """
        Allow the "mapped" and "not mapped" filters in the account list views.
        """
        if operator in ('!=', '=') and operand is False:
            chart_id = self.env.context.get('chart_id', False)
            domain = [('consolidation_account_ids', '!=', False)]
            if chart_id:
                domain = expression.AND([domain, [('consolidation_account_ids.chart_id', '=', chart_id)]])
            if operator == '=':
                domain = [('id', 'not in', self._search(domain))]
            return domain
        else:
            return [('consolidation_account_ids', operator, operand)]
