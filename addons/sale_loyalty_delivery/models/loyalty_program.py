# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Command


class LoyaltyProgram(models.Model):
    _inherit = "loyalty.program"

    @api.model
    def _program_type_default_values(self):
        res = super()._program_type_default_values()
        # Add a loyalty reward for free shipping
        if "loyalty" in res:
            res["loyalty"]["reward_ids"].append(
                Command.create({"reward_type": "shipping", "required_points": 100})
            )
        return res

    @api.model
    def _get_template_values(self):
        res = super()._get_template_values()
        if "promotion" in res:
            res["promotion"]["reward_ids"] = [
                Command.clear(),
                Command.create({"reward_type": "shipping"}),
            ]
        return res
