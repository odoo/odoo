# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class PosConfig(models.Model):
    _inherit = "pos.config"

    self_order_pay_after = fields.Selection(selection_add=[("meal", "Meal")], ondelete={'meal': lambda recs: recs.write({'self_order_pay_after': 'each'})})

    @api.model_create_multi
    def create(self, vals_list):
        """
        We want self ordering to be enabled by default
        (This would have been nicer to do using a default value
        directly on the fields, but `module_pos_restaurant` would not be
        known at the time that the function for this default value would run)
        """
        pos_config_ids = super().create(vals_list)

        for pos_config_id in pos_config_ids:
            if pos_config_id.module_pos_restaurant:
                pos_config_id.self_order_view_mode = True
                pos_config_id.self_order_ordering_mode = True

        return pos_config_ids

    @api.depends("module_pos_restaurant")
    def _compute_self_order(self):
        """
        Self ordering will only be enabled for restaurants
        """
        for record in self:
            if not record.module_pos_restaurant:
                record.self_order_view_mode = False
                record.self_order_ordering_mode = False

    def _get_self_order_route(self, table_id=None):
        self.ensure_one()
        base_route = super()._get_self_order_route()
        table_route = ""

        if not self.self_order_ordering_mode:
            return base_route

        table = self.env["restaurant.table"].search(
            [("active", "=", True), ("id", "=", table_id)], limit=1
        )

        if table:
            table_route = f"&table_identifier={table.identifier}"

        return f"{base_route}{table_route}"

    def _update_access_token(self):
        super()._update_access_token()
        self.floor_ids.table_ids._update_identifier()

    def _generate_qr_code(self):
        qr_code = super()._generate_qr_code()

        table_qr_code = [
            {
                'name': floor.name,
                'qr_codes':[{
                    'identifier': table.identifier,
                    'name': table.name,
                    'url': self._get_self_order_route(table.id),
                } for table in floor.table_ids]
            }
            for floor in self.floor_ids
        ]

        qr_code['data'].extend(table_qr_code)
        return qr_code
