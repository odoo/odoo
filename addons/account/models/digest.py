# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DigestDigest(models.Model):
    _inherit = 'digest.digest'

    kpi_account_total_revenue = fields.Boolean('Revenue')
    kpi_account_total_revenue_value = fields.Monetary(compute='_compute_kpi_account_total_revenue_value')

    def _compute_kpi_account_total_revenue_value(self):
        self._raise_if_not_member_of('account.group_account_invoice')
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

    def _get_kpi_custom_settings(self, company, user):
        res = super()._get_kpi_custom_settings(company, user)
        menu_id = self.env.ref('account.menu_finance').id
        res['kpi_action']['kpi_account_total_revenue'] = f'account.action_move_out_invoice_type?menu_id={menu_id}'
        res['kpi_sequence']['kpi_account_total_revenue'] = 5500
        return res
