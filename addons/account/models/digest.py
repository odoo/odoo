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
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            self._cr.execute('''
                SELECT -SUM(line.balance)
                FROM account_move_line line
                JOIN account_move move ON move.id = line.move_id
                JOIN account_account account ON account.id = line.account_id
                WHERE line.company_id = %s AND line.date >= %s AND line.date < %s
                AND account.internal_group = 'income'
                AND move.state = 'posted'
            ''', [company.id, start, end])
            query_res = self._cr.fetchone()
            record.kpi_account_total_revenue_value = query_res and query_res[0] or 0.0

    def _compute_kpis_actions(self, company, user):
        res = super(Digest, self)._compute_kpis_actions(company, user)
        res['kpi_account_total_revenue'] = 'account.action_move_out_invoice_type&menu_id=%s' % self.env.ref('account.menu_finance').id
        return res
