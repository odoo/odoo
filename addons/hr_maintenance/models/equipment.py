# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools
from odoo.fields import Domain


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    employee_id = fields.Many2one('hr.employee', compute='_compute_equipment_assignment_fields',
        store=True, readonly=False, string='Assigned Employee', tracking=True, index='btree_not_null')
    department_id = fields.Many2one('hr.department', compute='_compute_equipment_assignment_fields',
        store=True, readonly=False, string='Assigned Department', tracking=True)
    equipment_assign_to = fields.Selection(
        selection_add=[('department', 'Department'), ('employee', 'Employee')], required=True,
        ondelete={'department': 'set other', 'employee': 'set other'}, default='employee')

    @api.depends(lambda self: self._get_assign_fields())
    def _compute_is_assigned(self):
        assign_fields = self._get_assign_fields()
        for equipment in self:
            equipment.is_assigned = any(equipment[field] for field in assign_fields)

    @api.model_create_multi
    def create(self, vals_list):
        equipments = super().create(vals_list)
        for equipment in equipments:
            # TDE FIXME: check if we can use suggested recipients for employee and department manager
            # subscribe employee or department manager when equipment assign to him.
            partner_ids = []
            if equipment.employee_id and equipment.employee_id.user_id:
                partner_ids.append(equipment.employee_id.user_id.partner_id.id)
            if equipment.department_id and equipment.department_id.manager_id and equipment.department_id.manager_id.user_id:
                partner_ids.append(equipment.department_id.manager_id.user_id.partner_id.id)
            if partner_ids:
                equipment.message_subscribe(partner_ids=partner_ids)
        return equipments

    def write(self, vals):
        partner_ids = []
        # subscribe employee or department manager when equipment assign to employee or department.
        if vals.get('employee_id'):
            user_id = self.env['hr.employee'].browse(vals['employee_id'])['user_id']
            if user_id:
                partner_ids.append(user_id.partner_id.id)
        if vals.get('department_id'):
            department = self.env['hr.department'].browse(vals['department_id'])
            if department and department.manager_id and department.manager_id.user_id:
                partner_ids.append(department.manager_id.user_id.partner_id.id)
        if partner_ids:
            self.message_subscribe(partner_ids=partner_ids)
        return super(MaintenanceEquipment, self).write(vals)

    def _track_subtype(self, init_values):
        self.ensure_one()
        if ('employee_id' in init_values and self.employee_id) or ('department_id' in init_values and self.department_id):
            return self.env.ref('maintenance.mt_mat_assign')
        return super(MaintenanceEquipment, self)._track_subtype(init_values)

    def _get_assign_fields(self):
        return super()._get_assign_fields() + ['employee_id', 'department_id']

    def _get_owner_methods_by_equipment_assign_to(self):
        owner_methods = super()._get_owner_methods_by_equipment_assign_to()
        owner_methods.update({
            'employee': lambda eq: eq.employee_id.user_id.id or self.env.user.id,
            'department': lambda eq: eq.department_id.manager_id.user_id.id or self.env.user.id,
        })
        return owner_methods

    def _get_assignment_handlers_by_equipment_assign_to(self):
        handlers = super()._get_assignment_handlers_by_equipment_assign_to()
        handlers.update({
            'employee': lambda eq: {
                field: eq[field] if field == 'employee_id' else False
                for field in self._get_assign_fields()
            },
            'department': lambda eq: {
                field: eq[field] if field == 'department_id' else False
                for field in self._get_assign_fields()
            },
        })
        return handlers

    def _search_is_assigned(self, operator, value):
        if operator not in ('=', '!=') or value not in (True, False):
            return NotImplemented
        assign_fields = self._get_assign_fields()
        is_equipment_assigned = (operator == "=") == value
        if is_equipment_assigned:
            return Domain.OR(Domain(field, "!=", False) for field in assign_fields)
        return Domain.AND(Domain(field, "=", False) for field in assign_fields)


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    def _default_employee_get(self):
        return self.env.user.employee_id

    employee_id = fields.Many2one('hr.employee', string='Employee', default=_default_employee_get)
    owner_user_id = fields.Many2one(compute='_compute_owner', store=True)
    equipment_id = fields.Many2one(domain="['|', ('employee_id', '=', employee_id), ('employee_id', '=', False)]")

    @api.depends('employee_id')
    def _compute_owner(self):
        for r in self:
            if r.equipment_id.equipment_assign_to == 'employee':
                r.owner_user_id = r.employee_id.user_id.id
            else:
                r.owner_user_id = False

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)
        for request in requests:
            # TDE FIXME: check default recipients (master)
            if request.employee_id.user_id:
                request.message_subscribe(partner_ids=[request.employee_id.user_id.partner_id.id])
        return requests

    def write(self, vals):
        if vals.get('employee_id'):
            employee = self.env['hr.employee'].browse(vals['employee_id'])
            if employee and employee.user_id:
                self.message_subscribe(partner_ids=[employee.user_id.partner_id.id])
        return super(MaintenanceRequest, self).write(vals)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        if custom_values is None:
            custom_values = {}
        # TDE FIXME: check author_id, should be set (master-)
        email = tools.email_normalize(msg_dict.get('from'), strict=False)
        user = self.env['res.users'].search([('login', '=', email)], limit=1) if email else self.env['res.users']
        if user:
            employee = self.env.user.employee_id
            if employee:
                custom_values['employee_id'] = employee and employee[0].id
        return super().message_new(msg_dict, custom_values=custom_values)
