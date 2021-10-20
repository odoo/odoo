# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        result.extend(["restaurant.floor", "restaurant.table", "restaurant.printer"])
        return result

    def _loader_info_restaurant_floor(self):
        return {
            "domain": [("pos_config_id", "=", self.config_id.id)],
            "fields": ["name", "background_color", "table_ids", "sequence"]
        }

    def _get_pos_ui_restaurant_floor(self, params):
        return self.env["restaurant.floor"].search_read(params["domain"], params["fields"])

    def _loader_info_restaurant_table(self):
        return {
            "domain": [("active", "=", True)],
            "fields": ["name", "width", "height", "position_h", "position_v", "shape", "floor_id", "color", "seats", "active"],
        }

    def _get_pos_ui_restaurant_table(self, params):
        return self.env["restaurant.table"].search_read(params["domain"], params["fields"])

    def _loader_info_restaurant_printer(self):
        return {
            "domain": [("id", "in", self.config_id.printer_ids.ids)],
            "fields": ["name", "proxy_ip", "product_categories_ids", "printer_type"],
        }

    def _get_pos_ui_restaurant_printer(self, params):
        return self.env["restaurant.printer"].search_read(params["domain"], params["fields"])
