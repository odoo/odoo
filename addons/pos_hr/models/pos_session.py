# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.point_of_sale.models.pos_session import loader


class PosSession(models.Model):
    _inherit = "pos.session"

    @loader("hr.employee", ["name", "id", "user_id"])
    def _load_hr_employee(self, lcontext):
        if len(self.config_id.employee_ids) > 0:
            domain = ["&", ("company_id", "=", self.config_id.company_id.id), "|", ("user_id", "=", self.user_id.id), ("id", "in", self.config_id.employee_ids.ids)]
        else:
            domain = [("company_id", "=", self.config_id.company_id.id)]
        records = self.env[lcontext.model].search(domain).read(lcontext.fields, load=False)
        for record in records:
            lcontext.contents[record["id"]] = record
