# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        self._set_pos_restaurant_receipt_common_data(data)
        return data

    def _order_receipt_generate_line_data(self):
        lines = super()._order_receipt_generate_line_data()
        if not self.course_ids:
            return lines
        # Mirror the order summary: lines grouped by course, the service fee at the very
        # bottom. The fee is moved to the last course once created, so its position in
        # the creation order says nothing about where it is displayed.
        course_rank = {course.id: rank for rank, course in enumerate(self.course_ids.sorted('index'))}
        return sorted(lines, key=lambda line: (
            line['is_service_fee_line'],
            course_rank.get(line.get('course_id'), -1),
        ))

    def _generate_preparation_receipt_data(self, order_change, is_split_per_product=False):
        data = super()._generate_preparation_receipt_data(order_change, is_split_per_product)
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
