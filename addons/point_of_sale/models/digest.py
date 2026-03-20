# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class DigestDigest(models.Model):
    _inherit = 'digest.digest'

    kpi_pos_total = fields.Boolean('POS Sales')
    kpi_pos_total_value = fields.Monetary(compute='_compute_kpi_pos_total_value')

    def _compute_kpi_pos_total_value(self):
        self._raise_if_not_member_of('point_of_sale.group_pos_user')
        self._calculate_kpi(
            'pos.order',
            'kpi_pos_total_value',
            date_field='date_order',
            additional_domain=[('state', 'not in', ['draft', 'cancel']), ('account_move', '=', False)],
            sum_field='amount_total',
        )

    def _get_kpi_custom_settings(self, company, user):
        res = super()._get_kpi_custom_settings(company, user)
        menu_id = self.env.ref('point_of_sale.menu_point_root').id
        res['kpi_action']['kpi_pos_total'] = f'point_of_sale.action_pos_sale_graph?menu_id={menu_id}'
        res['kpi_sequence']['kpi_pos_total'] = 1500
        return res
