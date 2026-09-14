from odoo import api, models

MEMBERSHIP_MULTI_KEY = "sales_team.membership_multi"


class IrConfigParameter(models.Model):
    _inherit = "ir.config_parameter"

    def _invalidate_membership_multi(self, keys):
        if MEMBERSHIP_MULTI_KEY not in keys:
            return
        self.env["crm.team"].invalidate_model(["is_membership_multi", "member_warning"])
        self.env["crm.team.member"].invalidate_model(["member_warning"])

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
