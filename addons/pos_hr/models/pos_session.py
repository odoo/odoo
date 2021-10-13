# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.point_of_sale.models.pos_session import pos_loader


class PosSession(models.Model):
    _inherit = "pos.session"

    @pos_loader.info("hr.employee")
    def _loader_info_hr_employee(self):
        if len(self.config_id.employee_ids) > 0:
            domain = ["&", ("company_id", "=", self.config_id.company_id.id), "|", ("user_id", "=", self.user_id.id), ("id", "in", self.config_id.employee_ids.ids)]
        else:
            domain = [("company_id", "=", self.config_id.company_id.id)]
        return {"domain": domain, "fields": ["name", "id", "user_id"]}
