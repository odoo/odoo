# Copyright 2023 Taras Shabaranskyi
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    apps_menu_search_type = fields.Selection(
        [
            ("canonical", "Canonical"),
            ("fuse", "Fuse"),
            ("command_palette", "Command Palette"),
        ],
        default="canonical",
        required=True,
    )
    apps_menu_theme = fields.Selection(
        [
            ("milk", "Milk"),
            ("community", "Community"),
        ],
        default="milk",
        required=True,
    )
    is_redirect_home = fields.Boolean(
        string="Redirect to Home",
        help="Redirect to dashboard after signing in",
        compute="_compute_redirect_home",
        store=True,
        readonly=False,
    )

    @api.depends("action_id")
    def _compute_redirect_home(self):
        """
        Set is_redirect_home to False
        when action_id has a value.
        :return:
        """
        self.filtered("action_id").is_redirect_home = False
