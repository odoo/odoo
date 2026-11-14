# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrModuleModule(models.Model):
    _name = "ir.module.module"
    _inherit = ["ir.module.module"]

    def action_view_delivery_methods(self):
        self.ensure_one()
        delivery_type = self.state == "installed" and self._get_provided_delivery_type()
        if not delivery_type:
            return False

        action = self.env["ir.actions.act_window"]._for_xml_id(
            "delivery.action_delivery_carrier_form",
        )
        action["context"] = {"search_default_delivery_type": delivery_type}
        return action

    def _get_provided_delivery_type(self):
        """Return the delivery type added by the module.

        :return: The delivery type, or `False` if the module doesn't add any.
        :rtype: str | bool
        """
        self.ensure_one()
        if self.name == "delivery":
            return "in_house"
        if self.name.startswith("delivery_"):
            return self.name.removeprefix("delivery_")  # e.g., dhl_rest
        return False
