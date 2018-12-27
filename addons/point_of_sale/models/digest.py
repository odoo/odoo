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
        for record in self:
            start, end, company = record._get_kpi_compute_parameters()
            record.kpi_pos_total_value = sum(self.env['pos.order'].search([
                ('date_order', '>=', start),
                ('date_order', '<', end),
                ('state', 'not in', ['draft', 'cancel', 'invoiced']),
                ('company_id', '=', company.id)
            ]).mapped('amount_total'))

    def compute_kpis_actions(self, company, user):
        res = super(Digest, self).compute_kpis_actions(company, user)
        res['kpi_pos_total'] = 'point_of_sale.action_pos_sale_graph&menu_id=%s' % self.env.ref('point_of_sale.menu_point_root').id
        return res
