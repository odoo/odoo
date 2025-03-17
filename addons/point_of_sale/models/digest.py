# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import AccessError


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_pos_total = fields.Boolean('POS Sales')
    kpi_pos_total_value = fields.Monetary(compute='_compute_kpi_pos_total_value')

    def _compute_kpi_pos_total_value(self):
        if not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessError(_("Do not have access, skip this data for user's digest email"))

        self._calculate_company_based_kpi(
            'pos.order',
            'kpi_pos_total_value',
            date_field='date_order',
            additional_domain=[('state', 'not in', ['draft', 'cancel', 'invoiced'])],
            sum_field='amount_total',
        )

    def _compute_kpis_actions(self, company, user):
        res = super(Digest, self)._compute_kpis_actions(company, user)
        res['kpi_pos_total'] = 'point_of_sale.action_pos_sale_graph?menu_id=%s' % self.env.ref('point_of_sale.menu_point_root').id
        return res
