# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _get_fields_for_draft_order(self):
        fields = super()._get_fields_for_draft_order()
        fields.append('employee_id')
        return fields

    @api.model
    def get_table_draft_orders(self, table_ids):
        table_orders = super().get_table_draft_orders(table_ids)
        for order in table_orders:
            if order['employee_id']:
                order['employee_id'] = order['employee_id'][0]

        return table_orders
