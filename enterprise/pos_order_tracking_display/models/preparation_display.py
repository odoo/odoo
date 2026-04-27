from odoo import models


class PosPreparationDisplay(models.Model):
    _inherit = "pos_preparation_display.display"

    def _get_pos_orders(self):
        self.ensure_one()
        if len(self.stage_ids) <= 1:
            return {"done": [], "notDone": []}
        last_stage = self.stage_ids[-1]  # last stage always means that the order is done.
        second_last_stage = self.stage_ids[-2]  # order will be displated as ready.

        orders_completed = set()
        orders_not_completed = set()
        Orders = self.env["pos_preparation_display.order"]
        pdis_orders = Orders.get_preparation_display_order(self.id)
        pdis_order_ids = Orders.browse(obj["id"] for obj in pdis_orders).filtered(lambda o: o.order_stage_ids[-1].stage_id != last_stage)

        for pdis_order_id in pdis_order_ids:
            order_stage_id = pdis_order_id.order_stage_ids[-1].stage_id
            pos_order_tracking_ref = pdis_order_id.pos_order_id.tracking_number
            unfinished_pdis_orders = (
                (
                    order.pos_order_id == pdis_order_id.pos_order_id
                    and order.order_stage_ids[-1].stage_id != second_last_stage
                    and pdis_order_id != order
                )
                for order in pdis_order_ids
            )
            if order_stage_id == second_last_stage and not any(unfinished_pdis_orders):
                orders_completed.add(pos_order_tracking_ref)
            elif order_stage_id != last_stage:
                orders_not_completed.add(pos_order_tracking_ref)
        return {
            "done": list(orders_completed),
            "notDone": list(orders_not_completed),
        }

    def _send_orders_to_customer_display(self):
        self.ensure_one()
        orders = self._get_pos_orders()
        self._notify("NEW_ORDERS", orders)

    def _send_load_orders_message(self, sound=False):
        super()._send_load_orders_message(sound)
        self._send_orders_to_customer_display()

    def open_customer_display(self):
        return {
            "type": "ir.actions.act_url",
            "url": f"/pos-order-tracking?access_token={self.access_token}",
            "target": "new",
        }
