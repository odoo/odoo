from odoo import fields, models


class ResourceAsset(models.Model):
    _name = "resource.asset"
    _inherit = ["resource.asset", "mixin.maintenance"]

    maintenance_ids = fields.One2many(
        comodel_name="maintenance.request",
        inverse_name="asset_id",
    )

    def action_view_maintenance(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "maintenance.hr_equipment_request_action"
        )
        action["domain"] = [("asset_id", "=", self.id)]
        action["context"] = {
            "default_asset_id": self.id,
            "default_company_id": self.company_id.id,
        }
        return action
