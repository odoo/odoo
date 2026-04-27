# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_ke_shif_number = fields.Char("SHIF Number", groups="hr.group_hr_user")
