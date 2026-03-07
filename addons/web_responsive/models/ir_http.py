# Copyright 2023 Taras Shabaranskyi
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        session = super().session_info()
        user = self.env.user
        return {
            **session,
            "apps_menu": {
                "search_type": user.apps_menu_search_type,
                "theme": user.apps_menu_theme,
            },
        }
