# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def check_ups_service_type(self, value):
        if value.get('sale_id'):
            order = self.browse(int(value['sale_id']))
            check = order.carrier_id.ups_rate_shipment(order)
            if check['success']:
                return {}
            else:
                order.ups_service_type = order.carrier_id.ups_default_service_type
                return {'error': check['error_message']}
