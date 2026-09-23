from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def action_view_in_store_delivery_methods(self):
        in_store_dms = self.env["delivery.carrier"].search(
            [("delivery_type", "=", "in_store")]
        )
        if len(in_store_dms) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "delivery.carrier",
                "view_mode": "form",
                "res_id": in_store_dms.id,
            }
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Delivery Methods"),
            "res_model": "delivery.carrier",
            "view_mode": "list,form",
            "context": '{"search_default_delivery_type": "in_store"}',
        }
