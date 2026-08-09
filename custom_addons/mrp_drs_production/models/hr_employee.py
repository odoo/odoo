from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_drs_supervisor = fields.Boolean(string="Is DRS Supervisor", default=False)
    is_drs_technician = fields.Boolean(string="Is DRS Technician", default=False)
