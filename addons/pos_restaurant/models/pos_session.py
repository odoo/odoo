# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.point_of_sale.models.pos_session import loader


class PosSession(models.Model):
    _inherit = "pos.session"

    @loader("restaurant.floor", ["name", "background_color", "table_ids", "sequence"])
    def _load_restaurant_floor(self, lcontext):
        if not self.config_id.module_pos_restaurant:
            return
        domain = [("pos_config_id", "=", self.config_id.id)]
        records = self.env[lcontext.model].search(domain).read(lcontext.fields, load=False)
        for record in records:
            lcontext.contents[record["id"]] = record

    @loader("restaurant.table", ["name", "width", "height", "position_h", "position_v", "shape", "floor_id", "color", "seats", "active"])
    def _load_restaurant_table(self, lcontext):
        if not self.config_id.module_pos_restaurant:
            return
        domain = [("floor_id", "in", [*lcontext.data["restaurant.floor"].keys()]), ("active", "=", True)]
        records = self.env[lcontext.model].search(domain).read(lcontext.fields, load=False)
        for record in records:
            lcontext.contents[record["id"]] = record

    @loader("restaurant.printer", ["name", "proxy_ip", "product_categories_ids", "printer_type"])
    def _load_restaurant_printer(self, lcontext):
        if not self.config_id.module_pos_restaurant:
            return
        domain = [("id", "in", self.config_id.printer_ids.ids)]
        records = self.env[lcontext.model].search(domain).read(lcontext.fields, load=False)
        for record in records:
            lcontext.contents[record["id"]] = record
