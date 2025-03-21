# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrUserWorkEntryEmployee(models.Model):
    """ Personnal calendar filter """

    _name = 'hr.user.work.entry.employee'
    _description = 'Work Entries Employees'

    user_id = fields.Many2one('res.users', 'Me', required=True, default=lambda self: self.env.user, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    active = fields.Boolean('Active', default=True)
    is_checked = fields.Boolean(default=True)

    _user_id_employee_id_unique = models.Constraint(
        'UNIQUE(user_id,employee_id)',
        'You cannot have the same employee twice.',
    )
