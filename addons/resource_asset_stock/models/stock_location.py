from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    asset_count = fields.Integer(compute="_compute_asset_count")

    def _compute_asset_count(self):
        counts = dict(
            self.env["resource.asset"]._read_group(
                [("location_id", "in", self.ids)], ["location_id"], ["__count"]
            )
        )
        for location in self:
            location.asset_count = counts.get(location, 0)

    def action_view_assets(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "resource_asset.action_resource_asset"
        )
        action["domain"] = [("location_id", "=", self.id)]
        action["context"] = {"default_location_id": self.id}
        return action
