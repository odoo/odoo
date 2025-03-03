from odoo import fields, models


class POSOrder(models.Model):
    _inherit = "pos.order"

    select_date = fields.Date()

    def _process_saved_order(self, draft):
        if draft and self.select_date:
            self._create_order_picking()
            self._compute_total_cost_in_real_time()

        return super()._process_saved_order(draft)
