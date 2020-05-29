# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    employee_id = fields.Many2one('hr.employee', compute='_compute_equipment_assign',
        store=True, readonly=False, string='Assigned Employee', tracking=True)
    department_id = fields.Many2one('hr.department', compute='_compute_equipment_assign',
        store=True, readonly=False, string='Assigned Department', tracking=True)
    equipment_assign_to = fields.Selection(
        [('department', 'Department'), ('employee', 'Employee'), ('other', 'Other')],
        string='Used By',
        required=True,
        default='employee')
    owner_user_id = fields.Many2one(compute='_compute_owner', store=True)
    assign_date = fields.Date(compute='_compute_equipement_assign', store=True, readonly=False, copy=True)

    @api.depends('employee_id', 'department_id', 'equipment_assign_to')
    def _compute_owner(self):
        for equipment in self:
            equipment.owner_user_id = self.env.user.id
            if equipment.equipment_assign_to == 'employee':
                equipment.owner_user_id = equipment.employee_id.user_id.id
            elif equipment.equipment_assign_to == 'department':
                equipment.owner_user_id = equipment.department_id.manager_id.user_id.id

    @api.depends('equipment_assign_to')
    def _compute_equipment_assign(self):
        for equipment in self:
            if equipment.equipment_assign_to == 'employee':
                equipment.department_id = False
                equipment.employee_id = equipment.employee_id
            elif equipment.equipment_assign_to == 'department':
                equipment.employee_id = False
                equipment.department_id = equipment.department_id
            else:
                equipment.department_id = equipment.department_id
                equipment.employee_id = equipment.employee_id
            equipment.assign_date = fields.Date.context_today(self)

    @api.model
    def create(self, vals):
        equipment = super(MaintenanceEquipment, self).create(vals)
        # subscribe employee or department manager when equipment assign to him.
        partner_ids = []
        if equipment.employee_id and equipment.employee_id.user_id:
            partner_ids.append(equipment.employee_id.user_id.partner_id.id)
        if equipment.department_id and equipment.department_id.manager_id and equipment.department_id.manager_id.user_id:
            partner_ids.append(equipment.department_id.manager_id.user_id.partner_id.id)
        if partner_ids:
            equipment.message_subscribe(partner_ids=partner_ids)
        return equipment

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


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    @api.returns('self')
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

    @api.model
    def create(self, vals):
        result = super(MaintenanceRequest, self).create(vals)
        if result.employee_id.user_id:
            result.message_subscribe(partner_ids=[result.employee_id.user_id.partner_id.id])
        return result

    def write(self, vals):
        if vals.get('employee_id'):
            employee = self.env['hr.employee'].browse(vals['employee_id'])
            if employee and employee.user_id:
                self.message_subscribe(partner_ids=[employee.user_id.partner_id.id])
        return super(MaintenanceRequest, self).write(vals)

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        email = tools.email_split(msg.get('from')) and tools.email_split(msg.get('from'))[0] or False
        user = self.env['res.users'].search([('login', '=', email)], limit=1)
        if user:
            employee = self.env.user.employee_id
            if employee:
                custom_values['employee_id'] = employee and employee[0].id
        return super(MaintenanceRequest, self).message_new(msg, custom_values=custom_values)
