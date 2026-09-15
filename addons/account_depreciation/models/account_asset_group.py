from odoo import fields, models


class AccountAssetGroup(models.Model):
    """Groups related assets for reporting and bulk actions."""

    _name = "account.asset.group"
    _description = "Asset Group"
    _order = "name"

    name = fields.Char(
        index="trigram",
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    linked_asset_ids = fields.One2many(
        comodel_name="resource.asset",
        inverse_name="asset_group_id",
        string="Related Assets",
    )
    count_linked_assets = fields.Count(count_of="linked_asset_ids")

    def action_view_linked_assets(self):
        self.check_singleton()
        return {
            "name": self.name,
            "view_mode": "list,form",
            "res_model": "resource.asset",
            "type": "ir.actions.act_window",
            "views": self.env["resource.asset"]._get_depreciation_views(),
            "domain": [("id", "in", self.linked_asset_ids.ids)],
        }
