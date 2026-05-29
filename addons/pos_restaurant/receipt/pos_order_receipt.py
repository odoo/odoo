# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        self._set_pos_restaurant_receipt_common_data(data)
        return data

    def _generate_preparation_receipt_data(self, order_change):
        data = super()._generate_preparation_receipt_data(order_change)
        if not self.config_id.module_pos_restaurant:
            return data
        for receipt in data:
            self._set_pos_restaurant_receipt_common_data(receipt)
            if receipt["extra_data"].get("table_name"):
                receipt["extra_data"]["order_label"] = False
        return data

    def _set_pos_restaurant_receipt_common_data(self, data):
        if self.config_id.module_pos_restaurant:
            data['extra_data']['table_name'] = self.table_id.table_number if self.table_id else False
            data['extra_data']['floor_name'] = self.table_id.floor_id.name if self.table_id and self.table_id.floor_id else False
