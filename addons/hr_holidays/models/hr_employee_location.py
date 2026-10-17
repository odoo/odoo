from odoo import fields, models


class HrEmployeeLocation(models.Model):
    _inherit = 'hr.employee.location'

    leave_id = fields.Many2one('hr.leave', ondelete='cascade')
