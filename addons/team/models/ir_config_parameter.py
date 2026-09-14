from odoo import api, models


class IrConfigParameter(models.Model):
    _inherit = "ir.config_parameter"

    def _invalidate_membership_multi(self, keys):
        params = {
            usage.membership_multi_param
            for usage in self.env["team.team"]._get_usages().values()
        }
        if not params & set(keys):
            return
        self.env["team.team"].invalidate_model(
            ["is_membership_multi", "member_warning"]
        )
        self.env["team.member"].invalidate_model(["member_warning"])

    @api.model_create_multi
    def create(self, vals_list):
        params = super().create(vals_list)
        params._invalidate_membership_multi(params.mapped("key"))
        return params

    def write(self, vals):
        keys = set(self.mapped("key"))
        res = super().write(vals)
        self._invalidate_membership_multi(keys | set(self.mapped("key")))
        return res

    def unlink(self):
        keys = self.mapped("key")
        res = super().unlink()
        self._invalidate_membership_multi(keys)
        return res
