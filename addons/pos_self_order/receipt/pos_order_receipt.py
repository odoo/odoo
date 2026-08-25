# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'
    _description = 'Point of Sale Order Receipt Generator'

    def order_receipt_generate_data(self, basic_receipt=False):
        data = super().order_receipt_generate_data(basic_receipt)
        data['conditions']['from_self'] = self.source in ['mobile', 'kiosk']
        return data

    def _order_change_receipt_generate_data(self, prep_categ_ids=None):
        data = super()._order_change_receipt_generate_data(prep_categ_ids)
        if self.source not in ['mobile', 'kiosk']:
            return data

        for receipt in data:
            if self.source == 'mobile':
                receipt['extra_data']['prefix'] = _("Self Order")
            elif self.source == 'kiosk':
                receipt['extra_data']['prefix'] = _("Kiosk Order")

            receipt['extra_data']['employee_name'] = False

            if self.table_stand_number:
                receipt['extra_data']['order_label'] = _("Table Tracker %s", self.table_stand_number)
            elif not self.table_id:
                receipt['extra_data']['order_label'] = self.floating_order_name

            if not self.table_id and self.self_ordering_table_id:
                receipt['extra_data']['table_name'] = self.self_ordering_table_id.table_number if self.self_ordering_table_id else False
                receipt['extra_data']['floor_name'] = self.self_ordering_table_id.floor_id.name if self.self_ordering_table_id and self.self_ordering_table_id.floor_id else False

        return data
