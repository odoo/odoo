from odoo import models


class PosPreparationDisplayOrder(models.Model):
    _inherit = 'pos_preparation_display.order'

    def change_order_stage(self, stage_id, preparation_display_id):
        res = super().change_order_stage(stage_id, preparation_display_id)
        self.env['pos_preparation_display.display'].browse(int(preparation_display_id))._send_orders_to_customer_display()
        return res
