# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.point_of_sale.models.pos_session import pos_loader


class PosSession(models.Model):
    _inherit = "pos.session"

    @pos_loader.meta("restaurant.floor")
    def _meta_restaurant_floor(self):
        if not self.config_id.module_pos_restaurant:
            return
        return {
            "domain": [("pos_config_id", "=", self.config_id.id)],
            "fields": ["name", "background_color", "table_ids", "sequence"]
        }

    @pos_loader.meta("restaurant.table", requires=[('floors', 'restaurant.floor')])
    def _meta_restaurant_table(self, floors, **kwargs):
        if not self.config_id.module_pos_restaurant:
            return
        return {
            "domain": [("floor_id", "in", [*floors.keys()]), ("active", "=", True)],
            "fields": ["name", "width", "height", "position_h", "position_v", "shape", "floor_id", "color", "seats", "active"],
        }

    @pos_loader.meta("restaurant.printer")
    def _meta_restaurant_printer(self):
        if not self.config_id.module_pos_restaurant:
            return
        return {
            "domain": [("id", "in", self.config_id.printer_ids.ids)],
            "fields": ["name", "proxy_ip", "product_categories_ids", "printer_type"],
        }
