# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    insz_or_bis_number = fields.Char("INSZ or BIS number", groups="hr.group_hr_manager")
    clocked_session_ids = fields.Many2many(
        "pos.session",
        "employees_session_clocking_info",
        string="Users Clocked In",
        groups="hr.group_hr_user",
        help="This is a technical field used for tracking the status of the session for each employees.",
    )

    @api.constrains("insz_or_bis_number")
    def _check_insz_or_bis_number(self):
        for emp in self:
            insz_number = emp.insz_or_bis_number
            if insz_number and not self.env['res.users'].is_valid_insz_or_bis_number(insz_number):
                raise ValidationError(_("The INSZ or BIS number is not valid."))
