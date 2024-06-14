# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Digest(models.Model):
    _inherit = 'digest.digest'

    kpi_stock_delivery_count = fields.Boolean('Deliveries')
    kpi_stock_delivery_count_value = fields.Integer(compute='_compute_kpi_stock_delivery_count_value')
    kpi_stock_receipt_count = fields.Boolean('Receipts')
    kpi_stock_receipt_count_value = fields.Integer(compute='_compute_kpi_stock_receipt_count_value')

    def _compute_kpi_stock_delivery_count_value(self):
        self._ensure_user_has_one_of_the_group('stock.group_stock_manager')
        self._calculate_company_based_kpi(
            'stock.picking',
            'kpi_stock_delivery_count_value',
            date_field='date_done',
            additional_domain=[('state', '=', 'done'),
                               # view_move_search outgoing filter condition
                               ('location_id.usage', 'in', ('internal', 'transit')),
                               ('location_dest_id.usage', 'not in', ('internal', 'transit'))],
        )

    def _compute_kpi_stock_receipt_count_value(self):
        self._ensure_user_has_one_of_the_group('stock.group_stock_manager')
        self._calculate_company_based_kpi(
            'stock.picking',
            'kpi_stock_receipt_count_value',
            date_field='date_done',
            additional_domain=[('state', '=', 'done'),
                               # view_move_search incoming filter condition
                               ('location_id.usage', 'not in', ('internal', 'transit')),
                               ('location_dest_id.usage', 'in', ('internal', 'transit'))],
        )

    def _compute_kpis_actions(self, company, user):
        res = super()._compute_kpis_actions(company, user)
        menu_root_id = self.env.ref('stock.menu_stock_root').id
        res['kpi_stock_delivery_count'] = f'stock.stock_move_action_outgoing&menu_id={menu_root_id}'
        res['kpi_stock_receipt_count'] = f'stock.stock_move_action_incoming&menu_id={menu_root_id}'
        return res
