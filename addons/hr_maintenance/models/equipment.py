# -*- coding: utf-8 -*-
from openerp import api, fields, models, tools


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    employee_id = fields.Many2one('hr.employee', string='Assigned to Employee', track_visibility='onchange')
    department_id = fields.Many2one('hr.department', string='Assigned to Department', track_visibility='onchange')
    equipment_assign_to = fields.Selection(
        [('department', 'Department'), ('employee', 'Employee') ,('other', 'Other')],
        string='Used By',
        required=True,
        default='employee')
    owner_user_id = fields.Many2one(compute='_compute_owner')

    @api.depends('employee_id', 'department_id', 'equipment_assign_to')
    def _compute_owner(self):
        self.owner_user_id = self.env.user.id
        if self.equipment_assign_to == 'employee':
            self.owner_user_id = self.employee_id.user_id.id
        elif self.equipment_assign_to == 'department':
            self.owner_user_id = self.department_id.manager_id.user_id.id

    @api.onchange('equipment_assign_to')
    def _onchange_equipment_assign_to(self):
        if self.equipment_assign_to == 'employee':
            self.department_id = False
        if self.equipment_assign_to == 'department':
            self.employee_id = False
        self.assign_date = fields.Date.context_today(self)

    @api.multi
    def write(self, vals):
        users = self.env['res.users']
        # subscribe employee or department manager when equipment assign to employee or department.
        if vals.get('employee_id'):
            user_id = self.env['hr.employee'].browse(vals['employee_id']).user_id
            if user_id:
                users = users | user_id
        if vals.get('department_id'):
            department = self.env['hr.department'].browse(vals['department_id'])
            if department and department.manager_id and department.manager_id.user_id:
                users = users | department.manager_id.user_id.id
        if users:
            self.message_subscribe_users(user_ids=users.ids)
        return super(MaintenanceEquipment, self).write(vals)


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    @api.returns('self')
    def _default_employee_get(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    employee_id = fields.Many2one('hr.employee', string='Employee', default=_default_employee_get)
    department_id = fields.Many2one('hr.department', string='Department')
    owner_user_id = fields.Many2one(compute='_compute_owner', store=True)

    @api.depends('employee_id', 'department_id')
    def _compute_owner(self):
        if self.equipment_id.equipment_assign_to == 'employee':
            self.owner_user_id = self.employee_id.user_id.id
        elif self.equipment_id.equipment_assign_to == 'department':
            self.owner_user_id = self.department_id.manager_id.user_id.id

    @api.onchange('employee_id', 'department_id')
    def onchange_department_or_employee_id(self):
        domain = []
        if self.department_id:
            domain = [('department_id', '=', self.department_id.id)]
        if self.employee_id and self.department_id:
            domain = ['|'] + domain
        if self.employee_id:
            domain = domain + ['|', ('employee_id', '=', self.employee_id.id), ('employee_id', '=', None)]
        equipment = self.env['maintenance.equipment'].search(domain, limit=2)
        if len(equipment) == 1:
            self.equipment_id = equipment
        return {'domain': {'equipment_id': domain}}

    @api.multi
    def write(self, vals):
        if vals.get('employee_id'):
            employee = self.env['hr.employee'].browse(vals['employee_id'])
            if employee and employee.user_id:
                self.message_subscribe_users(user_ids=[employee.user_id.id])
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
            employee = self.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
            if employee:
                custom_values['employee_id'] = employee and employee[0].id
        return super(MaintenanceRequest, self).message_new(msg, custom_values=custom_values)
