from odoo import api, fields, models

from odoo.addons.team.models.team import TeamUsage


class Team(models.Model):
    _inherit = "team.team"

    use_alpha = fields.Boolean(string="Alpha")
    use_beta = fields.Boolean(string="Beta")

    @api.model
    def _get_usages(self):
        return super()._get_usages() | {
            "alpha": TeamUsage(
                key="alpha",
                flag="use_alpha",
                label="Alpha",
                manager_group="test_team.group_alpha_manager",
                alias_model="test.team.ticket",
                membership_multi_param="test_team.alpha_membership_multi",
            ),
            "beta": TeamUsage(
                key="beta",
                flag="use_beta",
                label="Beta",
                manager_group="test_team.group_beta_manager",
                membership_multi_param="test_team.beta_membership_multi",
            ),
        }

    def _prepare_usage_alias_defaults(self, key):
        defaults = super()._prepare_usage_alias_defaults(key)
        if key == "alpha":
            defaults["kind"] = "incoming"
        return defaults
