# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResGroups(models.Model):
    _inherit = 'res.groups'

    def _get_light_group_xmlids(self):
        return super()._get_light_group_xmlids() + (
            'stock.group_production_lot',
            'stock.group_adv_location',
            'stock.group_stock_multi_locations',
            'stock.group_stock_picking_batch',
            'stock.group_tracking_lot',
            'stock.group_tracking_owner',
            'stock.group_lot_on_delivery_slip',
            'stock.group_stock_lot_print_gs1',
            'stock.group_stock_sign_delivery',
            'stock.group_warning_stock',
            'stock.group_stock_user',
        )
