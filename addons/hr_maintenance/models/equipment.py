# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools
from odoo.fields import Domain


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    employee_id = fields.Many2one('hr.employee', compute='_compute_equipment_assign_to_date',
        store=True, readonly=False, string='Assigned Employee', tracking=True, index='btree_not_null')
    department_id = fields.Many2one('hr.department', compute='_compute_equipment_assign_to_date',
        store=True, readonly=False, string='Assigned Department', tracking=True)
    equipment_assign_to = fields.Selection(
        selection_add=[('department', 'Department'), ('employee', 'Employee')], default='employee')
    is_assigned = fields.Boolean(compute='_compute_is_assigned', search='_search_is_assigned')

    @api.depends(lambda self: self._get_assign_fields() + ['equipment_assign_to'])
    def _compute_owner(self):
        hr_equipments = self.filtered(lambda e: e.equipment_assign_to in ('employee', 'department', 'other'))
        other_equipments = self - hr_equipments
        if other_equipments:
            super(MaintenanceEquipment, other_equipments)._compute_owner()
        for equipment in hr_equipments:
            if equipment.equipment_assign_to == 'employee':
                equipment.owner_user_id = equipment.employee_id.user_id.id or self.env.user.id
            elif equipment.equipment_assign_to == 'department':
                equipment.owner_user_id = equipment.department_id.manager_id.user_id.id or self.env.user.id
            else:
                equipment.owner_user_id = self.env.user.id

    @api.depends('equipment_assign_to')
    def _compute_equipment_assign_to_date(self):
        hr_equipments = self.filtered(lambda e: e.equipment_assign_to in ('employee', 'department', 'other'))
        other_equipments = self - hr_equipments
        if other_equipments:
            super(MaintenanceEquipment, other_equipments)._compute_equipment_assign_to_date()
        assign_fields = self._get_assign_fields()
        for equipment in hr_equipments:
            values = dict.fromkeys(assign_fields, False)
            if equipment.equipment_assign_to == 'employee':
                values['employee_id'] = equipment.employee_id
            elif equipment.equipment_assign_to == 'department':
                values['department_id'] = equipment.department_id
            else:
                values = {field: equipment[field] or False for field in assign_fields}
            values['assign_date'] = fields.Date.context_today(self)
            equipment.update(values)

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

    def _search_is_assigned(self, operator, value):
        if operator not in ('=', '!=') or value not in (True, False):
            return NotImplemented

        assign_fields = self._get_assign_fields()
        is_assigned = (operator == "=") == value
        if is_assigned:
            return Domain.OR(Domain(field, "!=", False) for field in assign_fields)
        else:
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
