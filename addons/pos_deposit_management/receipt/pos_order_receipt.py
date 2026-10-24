from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def _order_receipt_generate_line_data(self):
        lines = super()._order_receipt_generate_line_data()
        for line in lines:
            line['is_deposit_for_combo_child'] = False
        by_id = {line['id']: line for line in lines}

        def add_deposits(line, ordered):
            for deposit_id in line.get('deposit_line_ids') or []:
                deposit = by_id.get(deposit_id)
                if deposit:
                    deposit['is_deposit_for_combo_child'] = bool(line.get('combo_parent_id'))
                    ordered.append(deposit)

        ordered = []
        for line in lines:
            if line.get('deposit_main_line_id') in by_id or line.get('combo_parent_id') in by_id:
                continue
            ordered.append(line)
            for child in (l for l in lines if l.get('combo_parent_id') == line['id']):
                ordered.append(child)
                add_deposits(child, ordered)
            add_deposits(line, ordered)
        return ordered
