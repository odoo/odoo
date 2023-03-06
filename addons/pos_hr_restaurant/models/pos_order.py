# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def get_table_draft_orders(self, table_ids):
        table_orders = super().get_table_draft_orders(table_ids)
        for order in table_orders:
            if order['employee_id']:
                order['employee_id'] = order['employee_id'][0]

        return table_orders
