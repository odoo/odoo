from odoo import models, fields

class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'
    birthday = fields.Date(string="Birthday")