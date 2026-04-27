# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    l10n_ch_telework_percentage = fields.Float(string="Telework Percentage", groups="hr_payroll.group_hr_payroll_user")
