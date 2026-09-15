from odoo import _, api, models


class LoyaltyProgram(models.Model):
    _inherit = "loyalty.program"

    @api.model
    def _program_type_default_values(self):
        res = super()._program_type_default_values()
        if "loyalty" in res:
            highest_points = max(
                (
                    vals.get("required_points", 0)
                    for command, _id, vals in res["loyalty"]["reward_ids"]
                    if command == 0
                ),
                default=0,
            )
            res["loyalty"]["reward_ids"].append(
                (
                    0,
                    0,
                    {
                        "reward_type": "shipping",
                        "required_points": highest_points + 1,
                    },
                )
            )
        return res

    @api.model
    def get_program_templates(self):
        res = super().get_program_templates()
        if "promotion" in res:
            res["promotion"]["description"] = _(
                "Automatic promotion: free shipping on orders higher than $50"
            )
        return res

    @api.model
    def _prepare_program_template_vals(self):
        res = super()._prepare_program_template_vals()
        if "promotion" in res:
            res["promotion"]["reward_ids"] = [
                (5, 0, 0),
                (
                    0,
                    0,
                    {
                        "reward_type": "shipping",
                    },
                ),
            ]
        return res
