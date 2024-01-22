# © 2023 David BEAL @ Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models

# R8180 rule asks for merging demo/base.py and models/base.py content
# We need to keep these class separated because of demo mode.
# pylint: disable=R8180


class Base(models.AbstractModel):
    _inherit = "base"

    def _get_field_styles(self):
        res = super()._get_field_styles()
        style = self.env.context.get("style")
        if style == "nice":
            # only this entry is correct
            res["res.users"] = {
                "bg-info": ["login", "type"],
                "bg-warning": ["partner_id"],
            }
        elif style == "no_dict":
            res = "any"
        elif style == "no_field_list":
            res["res.users"] = {"bg-info": "any"}
        elif style == "empty_dict":
            res["res.users"] = {}
        elif style == "no_style":
            res["res.users"] = False
        return res
