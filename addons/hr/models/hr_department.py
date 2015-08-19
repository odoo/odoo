# -*- coding: utf-8 -*-

from openerp import api, fields, models, _
from openerp.exceptions import ValidationError


class HrDepartment(models.Model):
    _name = "hr.department"
    _description = "HR Department"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    name = fields.Char(string='Department Name', required=True)
    complete_name = fields.Char(compute='_compute_complete_name', string='Name')
    company_id = fields.Many2one('res.company', string='Company', index=True, required=False,
         default=lambda self: self.env['res.company']._company_default_get('hr.department'))
    parent_id = fields.Many2one('hr.department', string='Parent Department', index=True)
    child_ids = fields.One2many('hr.department', 'parent_id', string='Child Departments')
    manager_id = fields.Many2one('hr.employee', string='Manager', track_visibility='onchange')
    member_ids = fields.One2many('hr.employee', 'department_id', string='Members', readonly=True)
    jobs_ids = fields.One2many('hr.job', 'department_id', string='Jobs')
    note = fields.Text()
    color = fields.Integer(string='Color Index')

    @api.multi
    def name_get(self):
        result = []
        for department in self:
            name = department.name
            if department.parent_id:
                name = department.parent_id.name + ' / ' + name
            result.append((department.id, name))
        return result

    @api.one
    def _compute_complete_name(self):
        self.complete_name = self.name_get()[0][1]

    @api.one
    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Error! You cannot create recursive departments.'))

    @api.model
    def create(self, vals):
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        department = super(HrDepartment, self).create(vals)
        employee = self.env['hr.employee'].browse(vals.get("manager_id"))
        if employee.user_id:
            department.message_subscribe_users([employee.user_id.id])
        return department

    @api.multi
    def write(self, vals):
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        if vals.get('manager_id'):
            Employee = employees = self.env['hr.employee']
            manager_id = vals['manager_id']
            employee = Employee.browse(manager_id)
            if employee.user_id:
                self.message_subscribe_users(user_ids=[employee.user_id.id])
            for department in self:
                employees |= Employee.search(
                    [
                        ('id', '!=', manager_id),
                        ('department_id', '=', department.id),
                        ('parent_id', '=', department.manager_id.id)
                    ])
            employees.write({'parent_id': manager_id})
        return super(HrDepartment, self).write(vals)
