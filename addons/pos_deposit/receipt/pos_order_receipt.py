# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def _is_item_count_excluded_line(self, line):
        return super()._is_item_count_excluded_line(line) or line.product_id.is_deposit

    def _order_receipt_generate_line_data(self):
        lines = super()._order_receipt_generate_line_data()
        line_by_id = {line['id']: line for line in lines}

        def get_deposit_lines(line):
            deposit_lines = [line_by_id[line_id] for line_id in line['deposit_line_ids'] if line_id in line_by_id]
            for deposit_line in deposit_lines:
                deposit_line['is_deposit_line'] = True
                deposit_line['is_combo_child_deposit'] = bool(line['combo_parent_id'])
            return deposit_lines

        sorted_lines = []
        for line in lines:
            if line['deposit_main_line_id'] in line_by_id or line['combo_parent_id'] in line_by_id:
                continue
            sorted_lines.append(line)
            for child in (line_by_id[line_id] for line_id in line['combo_line_ids'] if line_id in line_by_id):
                sorted_lines.append(child)
                sorted_lines.extend(get_deposit_lines(child))
            sorted_lines.extend(get_deposit_lines(line))
        return sorted_lines
