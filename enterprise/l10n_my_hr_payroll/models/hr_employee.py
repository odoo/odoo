# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Employee(models.Model):
    _inherit = "hr.employee"

    l10n_my_socso_exempted = fields.Boolean(
        string="SOCSO Exempted",
        groups="hr.group_hr_user",
        help="Employee over 60 years old / Employee has reached 55 years and without any previous contribution payments. For foreign workers who have reached 55 years and above as of 1st July 2024.")

