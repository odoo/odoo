# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    crm_team_id = fields.Many2one('crm.team', related='config_id.crm_team_id', string="Sales Team", readonly=True)

    def _load_data_params(self, config_id):
        params = super()._load_data_params(config_id)
        params['product.product']['fields'].extend(['invoice_policy', 'optional_product_ids', 'type'])
        params['pos.order.line']['fields'].extend(['sale_order_origin_id', 'sale_order_line_id', 'down_payment_details'])
        params['sale.order'] = {
            'domain': [['pos_order_line_ids.order_id.state', '=', 'draft']],
            'fields': ['name', 'state', 'user_id', 'order_line', 'partner_id', 'pricelist_id', 'fiscal_position_id', 'amount_total', 'amount_untaxed', 'amount_unpaid',
                'picking_ids', 'partner_shipping_id', 'partner_invoice_id', 'date_order']
        }
        params['sale.order.line'] = {
            'domain': lambda data: [('order_id', 'in', [order['id'] for order in data['sale.order']])],
            'fields': ['discount', 'display_name', 'price_total', 'price_unit', 'product_id', 'product_uom_qty', 'qty_delivered',
                'qty_invoiced', 'qty_to_invoice', 'display_type', 'name', 'tax_id']
        }
        return params
