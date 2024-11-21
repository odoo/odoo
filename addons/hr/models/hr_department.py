# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Department(models.Model):
    _name = "hr.department"
    _description = "Department"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "name"
    _rec_name = 'complete_name'
    _parent_store = True

    name = fields.Char('Department Name', required=True, translate=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', recursive=True, store=True)
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    parent_id = fields.Many2one('hr.department', string='Parent Department', index=True, check_company=True)
    child_ids = fields.One2many('hr.department', 'parent_id', string='Child Departments')
    manager_id = fields.Many2one('hr.employee', string='Manager', tracking=True, domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]")
    member_ids = fields.One2many('hr.employee', 'department_id', string='Members', readonly=True)
    has_read_access = fields.Boolean(search="_search_has_read_access", store=False, export_string_translation=False)
    total_employee = fields.Integer(compute='_compute_total_employee', string='Total Employee',
        export_string_translation=False)
    jobs_ids = fields.One2many('hr.job', 'department_id', string='Jobs')
    plan_ids = fields.One2many('mail.activity.plan', 'department_id')
    plans_count = fields.Integer(compute='_compute_plan_count')
    note = fields.Text('Note')
    color = fields.Integer('Color Index')
    parent_path = fields.Char(index=True)
    master_department_id = fields.Many2one(
        'hr.department', 'Master Department', compute='_compute_master_department_id', store=True)

    @api.depends_context('hierarchical_naming')
    def _compute_display_name(self):
        if self.env.context.get('hierarchical_naming', True):
            return super()._compute_display_name()
        for record in self:
            record.display_name = record.name

    def _search_has_read_access(self, operator, value):
        supported_operators = ["="]
        if operator not in supported_operators or not isinstance(value, bool):
            raise NotImplementedError()
        if not value:
            return [(1, "=", 0)]
        if self.env['hr.employee'].has_access('read'):
            return [(1, "=", 1)]
        departments_ids = self.env['hr.department'].sudo().search([('manager_id', 'in', self.env.user.employee_ids.ids)]).ids
        return [('id', 'child_of', departments_ids)]

    @api.model
    def name_create(self, name):
        record = self.create({'name': name})
        return record.id, record.display_name

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for department in self:
            if department.parent_id:
                department.complete_name = '%s / %s' % (department.parent_id.complete_name, department.name)
            else:
                department.complete_name = department.name

    @api.depends('parent_path')
    def _compute_master_department_id(self):
        for department in self:
            department.master_department_id = int(department.parent_path.split('/')[0])

    def _compute_total_employee(self):
        emp_data = self.env['hr.employee'].sudo()._read_group([('department_id', 'in', self.ids)], ['department_id'], ['__count'])
        result = {department.id: count for department, count in emp_data}
        for department in self:
            department.total_employee = result.get(department.id, 0)

    def _compute_plan_count(self):
        plans_data = self.env['mail.activity.plan']._read_group([('department_id', 'in', self.ids)], ['department_id'], ['__count'])
        plans_count = {department.id: count for department, count in plans_data}
        for department in self:
            department.plans_count = plans_count.get(department.id, 0)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(_('You cannot create recursive departments.'))

    @api.model_create_multi
    def create(self, vals_list):
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        departments = super(Department, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        for department, vals in zip(departments, vals_list):
            manager = self.env['hr.employee'].browse(vals.get("manager_id"))
            if manager.user_id:
                department.message_subscribe(partner_ids=manager.user_id.partner_id.ids)
        return departments

    def write(self, vals):
        """ If updating manager of a department, we need to update all the employees
            of department hierarchy, and subscribe the new manager.
        """
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        if 'manager_id' in vals:
            manager_id = vals.get("manager_id")
            if manager_id:
                manager = self.env['hr.employee'].browse(manager_id)
                # subscribe the manager user
                if manager.user_id:
                    self.message_subscribe(partner_ids=manager.user_id.partner_id.ids)
            manager_to_unsubscribe = set()
            for department in self:
                if department.manager_id and department.manager_id.user_id:
                    manager_to_unsubscribe.update(department.manager_id.user_id.partner_id.ids)
            self.message_unsubscribe(partner_ids=list(manager_to_unsubscribe))
            # set the employees's parent to the new manager
            self._update_employee_manager(manager_id)
        return super(Department, self).write(vals)

    def _update_employee_manager(self, manager_id):
        employees = self.env['hr.employee']
        for department in self:
            employees = employees | self.env['hr.employee'].search([
                ('id', '!=', manager_id),
                ('department_id', '=', department.id),
                ('parent_id', '=', department.manager_id.id)
            ])
        employees.write({'parent_id': manager_id})

    def get_formview_action(self, access_uid=None):
        res = super().get_formview_action(access_uid=access_uid)
        if (not self.env.user.has_group('hr.group_hr_user') and
           self.env.context.get('open_employees_kanban', False)):
            res.update({
                'name': self.name,
                'res_model': 'hr.employee.public',
                'view_mode': 'kanban',
                'views': [(False, 'kanban'), (False, 'form')],
                'context': {'searchpanel_default_department_id': self.id},
                'res_id': False,
            })
        return res

    def action_plan_from_department(self):
        action = self.env['ir.actions.actions']._for_xml_id('hr.mail_activity_plan_action')
        action['context'] = {'default_department_id': self.id, 'search_default_department_id': self.id}
        return action

    def action_employee_from_department(self):
        if self.env['hr.employee'].has_access('read'):
            res_model = "hr.employee"
            search_view_id = self.env.ref('hr.view_employee_filter').id
        else:
            res_model = "hr.employee.public"
            search_view_id = self.env.ref('hr.hr_employee_public_view_search').id
        return {
            'name': _("Employees"),
            'type': 'ir.actions.act_window',
            'res_model': res_model,
            'view_mode': 'list,kanban,form',
            'search_view_id': [search_view_id, 'search'],
            'context': {
                'searchpanel_default_department_id': self.id,
                'default_department_id': self.id,
                'search_default_group_department': 1,
                'search_default_department_id': self.id,
                'expand': 1
            },
        }

    def get_children_department_ids(self):
        return self.env['hr.department'].search([('id', 'child_of', self.ids)])

    def action_open_view_child_departments(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.department",
            "views": [[False, "kanban"], [False, "list"], [False, "form"]],
            "domain": [['id', 'in', self.get_children_department_ids().ids]],
            "name": "Child departments",
        }

    def get_department_hierarchy(self):
        if not self:
            return {}

        hierarchy = {
            'parent': {
                'id': self.parent_id.id,
                'name': self.parent_id.name,
                'employees': self.parent_id.total_employee,
            } if self.parent_id else False,
            'self': {
                'id': self.id,
                'name': self.name,
                'employees': self.total_employee,
            },
            'children': [
                {
                    'id': child.id,
                    'name': child.name,
                    'employees': child.total_employee
                } for child in self.child_ids
            ]
        }

        return hierarchy
