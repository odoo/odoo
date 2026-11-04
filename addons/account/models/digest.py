# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import AccessError


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_account_total_revenue = fields.Boolean('Revenue')
    kpi_account_total_revenue_value = fields.Monetary(compute='_compute_kpi_account_total_revenue_value')

    def _compute_kpi_account_total_revenue_value(self):
        if not self.env.user.has_group('account.group_account_invoice'):
            raise AccessError(_("Do not have access, skip this data for user's digest email"))

        start, end, companies = self._get_kpi_compute_parameters()

        total_per_companies = dict(self.env['account.move.line'].sudo()._read_group(
            groupby=['company_id'],
            aggregates=['balance:sum'],
            domain=[
                ('company_id', 'in', companies.ids),
                ('date', '>', start),
                ('date', '<=', end),
                ('account_id.internal_group', '=', 'income'),
                ('parent_state', '=', 'posted'),
            ],
        ))

        for record in self:
            company = record.company_id or self.env.company
            record.kpi_account_total_revenue_value = -total_per_companies.get(company, 0)

    def _compute_kpis_actions(self, company, user):
        res = super(Digest, self)._compute_kpis_actions(company, user)
        res['kpi_account_total_revenue'] = 'account.action_move_out_invoice_type?menu_id=%s' % self.env.ref('account.menu_finance').id
        return res
