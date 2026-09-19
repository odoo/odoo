from odoo import _, api, models


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def _apply_activity_bucket_subkey(self, group, model_name, subkey, res_ids):
        group = super()._apply_activity_bucket_subkey(
            group, model_name, subkey, res_ids
        )
        if model_name == "mailing.mailing":
            group["name"] = _("Email Marketing")
        return group
