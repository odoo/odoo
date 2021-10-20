# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        result.append("hr.employee")
        return result

    def _loader_info_hr_employee(self):
        if len(self.config_id.employee_ids) > 0:
            domain = ["&", ("company_id", "=", self.config_id.company_id.id), "|", ("user_id", "=", self.user_id.id), ("id", "in", self.config_id.employee_ids.ids)]
        else:
            domain = [("company_id", "=", self.config_id.company_id.id)]
        return {"domain": domain, "fields": ["name", "id", "user_id"]}

    def _get_pos_ui_hr_employee(self, params):
        return self.env["hr.employee"].search_read(params["domain"], params["fields"])
