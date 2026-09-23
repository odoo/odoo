from odoo import models


class Website(models.Model):
    _inherit = "website"

    def get_suggested_controllers(self):
        suggested_controllers = super().get_suggested_controllers()
        suggested_controllers.append(
            (
                self.env._("Resellers"),
                self.env["ir.http"]._url_for("/partners"),
                "website_crm_partner_assign",
            )
        )
        return suggested_controllers
