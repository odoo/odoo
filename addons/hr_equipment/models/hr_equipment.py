# -*- coding: utf-8 -*-

from openerp import api, fields, models, fields
from openerp import _, tools
from openerp.exceptions import UserError


class HrEquipmentStage(models.Model):
    """ Model for case stages. This models the main stages of a Maintenance Request management flow. """

    _name = 'hr.equipment.stage'
    _description = 'Maintenance Stage'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=20)
    fold = fields.Boolean('Folded in Recruitment Pipe')
    done = fields.Boolean('Request Done')


class HrEquipmentCategory(models.Model):
    _name = 'hr.equipment.category'
    _inherits = {"mail.alias": "alias_id"}
    _inherit = ['mail.thread']
    _description = 'Asset Category'

    @api.one
    @api.depends('equipment_ids')
    def _compute_fold(self):
        self.fold = False if self.equipment_count else True

    name = fields.Char('Category Name', required=True, translate=True)
    user_id = fields.Many2one('res.users', 'Responsible', track_visibility='onchange', default=lambda self: self.env.uid)
    color = fields.Integer('Color Index')
    note = fields.Text('Comments', translate=True)
    equipment_ids = fields.One2many('hr.equipment', 'category_id', string='Equipments', copy=False)
    equipment_count = fields.Integer(string="Equipment", compute='_compute_equipment_count')
    maintenance_ids = fields.One2many('hr.equipment.request', 'category_id', copy=False)
    maintenance_count = fields.Integer(string="Maintenance", compute='_compute_maintenance_count')
    alias_id = fields.Many2one(
        'mail.alias', 'Alias', ondelete='cascade', required=True,
        help="Email alias for this equipment category. New emails will automatically "
        "create new maintenance request for this equipment category.")
    fold = fields.Boolean(string='Folded in Maintenance Pipe', compute='_compute_fold', store=True)

    @api.multi
    def _compute_equipment_count(self):
        equipment_data = self.env['hr.equipment'].read_group([('category_id', 'in', self.ids)], ['category_id'], ['category_id'])
        mapped_data = dict([(m['category_id'][0], m['category_id_count']) for m in equipment_data])
        for category in self:
            category.equipment_count = mapped_data.get(category.id, 0)

    @api.multi
    def _compute_maintenance_count(self):
        maintenance_data = self.env['hr.equipment.request'].read_group([('category_id', 'in', self.ids)], ['category_id'], ['category_id'])
        mapped_data = dict([(m['category_id'][0], m['category_id_count']) for m in maintenance_data])
        for category in self:
            category.maintenance_count = mapped_data.get(category.id, 0)

    @api.model
    def create(self, vals):
        self = self.with_context(alias_model_name='hr.equipment.request', alias_parent_model_name=self._name)
        category_id = super(HrEquipmentCategory, self).create(vals)
        category_id.alias_id.write({'alias_parent_thread_id': category_id.id, 'alias_defaults': {'category_id': category_id.id}})
        return category_id

    @api.multi
    def unlink(self):
        for category in self:
            if category.equipment_ids or category.maintenance_ids:
                raise UserError(_("You cannot delete an equipment category containing equipments or maintenance requests."))
        res = super(HrEquipmentCategory, self).unlink()
        return res


class HrEquipment(models.Model):
    _name = 'hr.equipment'
    _inherit = ['mail.thread']
    _description = 'Equipment'

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if ('employee_id' in init_values and self.employee_id) or ('department_id' in init_values and self.department_id):
            return 'hr_equipment.mt_mat_assign'
        return super(HrEquipment, self)._track_subtype(init_values)

    @api.multi
    def name_get(self):
        result = []
        for record in self:
            if record.name and record.serial_no:
                result.append((record.id, record.name + '/' + record.serial_no))
            if record.name and not record.serial_no:
                result.append((record.id, record.name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if name:
            recs = self.search([('name', '=', name)] + args, limit=limit)
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    name = fields.Char('Asset Name', required=True, translate=True)
    user_id = fields.Many2one('res.users', string='Technician', track_visibility='onchange')
    employee_id = fields.Many2one('hr.employee', string='Assigned to Employee', track_visibility='onchange')
    department_id = fields.Many2one('hr.department', string='Assigned to Department', track_visibility='onchange')
    category_id = fields.Many2one('hr.equipment.category', string='Asset Category', track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', string='Vendor', domain="[('supplier', '=', 1)]")
    partner_ref = fields.Char('Vendor Reference')
    location = fields.Char('Location')
    model = fields.Char('Model')
    serial_no = fields.Char('Serial Number', copy=False)
    assign_date = fields.Date('Assigned Date', track_visibility='onchange')
    cost = fields.Float('Cost')
    note = fields.Text('Note')
    warranty = fields.Date('Warranty')
    color = fields.Integer('Color Index')
    scrap_date = fields.Date('Scrap Date')
    equipment_assign_to = fields.Selection(
        [('department', 'Department'), ('employee', 'Employee')],
        string='Used By',
        required=True,
        default='employee')
    maintenance_ids = fields.One2many('hr.equipment.request', 'equipment_id')
    maintenance_count = fields.Integer(compute='_compute_maintenance_count', string="Maintenance", store=True)
    maintenance_open_count = fields.Integer(compute='_compute_maintenance_count', string="Current Maintenance", store=True)

    @api.one
    @api.depends('maintenance_ids.stage_id.done')
    def _compute_maintenance_count(self):
        self.maintenance_count = len(self.maintenance_ids)
        self.maintenance_open_count = len(self.maintenance_ids.filtered(lambda x: not x.stage_id.done))


    @api.onchange('equipment_assign_to')
    def _onchange_equipment_assign_to(self):
        if self.equipment_assign_to == 'employee':
            self.department_id = False
        if self.equipment_assign_to == 'department':
            self.employee_id = False
        self.assign_date = fields.Date.context_today(self)

    @api.onchange('category_id')
    def _onchange_category_id(self):
        self.user_id = self.category_id.user_id

    _sql_constraints = [
        ('serial_no', 'unique(serial_no)', "Another asset already exists with this serial number!"),
    ]

    @api.model
    def create(self, vals):
        equipment = super(HrEquipment, self).create(vals)
        # subscribe employee or department manager when equipment assign to him.
        user_ids = []
        if equipment.employee_id and equipment.employee_id.user_id:
            user_ids.append(equipment.employee_id.user_id.id)
        if equipment.department_id and equipment.department_id.manager_id and equipment.department_id.manager_id.user_id:
            user_ids.append(equipment.department_id.manager_id.user_id.id)
        if user_ids:
            equipment.message_subscribe_users(user_ids=user_ids)
        return equipment

    @api.multi
    def write(self, vals):
        user_ids = []
        # subscribe employee or department manager when equipment assign to employee or department.
        if vals.get('employee_id'):
            user_id = self.env['hr.employee'].browse(vals['employee_id'])['user_id']
            if user_id:
                user_ids.append(user_id.id)
        if vals.get('department_id'):
            department = self.env['hr.department'].browse(vals['department_id'])
            if department and department.manager_id and department.manager_id.user_id:
                user_ids.append(department.manager_id.user_id.id)
        if user_ids:
            self.message_subscribe_users(user_ids=user_ids)
        return super(HrEquipment, self).write(vals)

    @api.model
    def _message_get_auto_subscribe_fields(self, updated_fields, auto_follow_fields=None):
        """ mail.thread override so user_id which has no special access allowance is not
            automatically subscribed.
        """
        if auto_follow_fields is None:
            auto_follow_fields = []
        return super(HrEquipment, self)._message_get_auto_subscribe_fields(updated_fields, auto_follow_fields)

    @api.multi
    def _read_group_category_ids(self, domain, read_group_order=None, access_rights_uid=None):
        """ Read group customization in order to display all the category in the
            kanban view, even if they are empty
        """
        category_obj = self.env['hr.equipment.category']
        order = category_obj._order
        access_rights_uid = access_rights_uid or self._uid
        if read_group_order == 'category_id desc':
            order = '%s desc' % order

        category_ids = category_obj._search([], order=order, access_rights_uid=access_rights_uid)
        result = [category.name_get()[0] for category in category_obj.browse(category_ids)]
        # restore order of the search
        result.sort(lambda x, y: cmp(category_ids.index(x[0]), category_ids.index(y[0])))

        fold = {}
        for category in category_obj.browse(category_ids):
            fold[category.id] = category.fold
        return result, fold

    _group_by_full = {
        'category_id': _read_group_category_ids
    }


class HrEquipmentRequest(models.Model):
    _name = 'hr.equipment.request'
    _inherit = ['mail.thread']
    _description = 'Maintenance Requests'

    @api.returns('self')
    def _default_employee_get(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    @api.returns('self')
    def _default_stage(self):
        return self.env['hr.equipment.stage'].search([], limit=1)

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage_id' in init_values and self.stage_id.sequence <= 1:
            return 'hr_equipment.mt_req_created'
        elif 'stage_id' in init_values and self.stage_id.sequence > 1:
            return 'hr_equipment.mt_req_status'
        return super(HrEquipmentRequest, self)._track_subtype(init_values)

    name = fields.Char('Subjects', required=True)
    description = fields.Text('Description')
    request_date = fields.Date('Request Date', track_visibility='onchange', default=fields.Date.context_today)
    employee_id = fields.Many2one('hr.employee', string='Employee', default=_default_employee_get)
    department_id = fields.Many2one('hr.department', string='Department')
    category_id = fields.Many2one('hr.equipment.category', string='Category')
    equipment_id = fields.Many2one('hr.equipment', string='Asset', index=True)
    user_id = fields.Many2one('res.users', string='Assigned to', track_visibility='onchange')
    stage_id = fields.Many2one('hr.equipment.stage', string='Stage', track_visibility='onchange', default=_default_stage)
    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string='Priority')
    color = fields.Integer('Color Index')
    close_date = fields.Date('Close Date')
    kanban_state = fields.Selection([('normal', 'In Progress'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')],
                                    string='Kanban State', required=True, default='normal', track_visibility='onchange')
    active = fields.Boolean(default=True, help="Set active to false to hide the maintenance request without deleting it.")


    @api.multi
    def archive_equipment_request(self):
        self.write({'active': False})

    @api.multi
    def reset_equipment_request(self):
        """ Reinsert the equipment request into the maintenance pipe in the first stage"""
        first_stage_obj = self.env['hr.equipment.stage'].search([], order="sequence asc", limit=1)
        self.write({'active': True, 'stage_id': first_stage_obj.id})

    @api.onchange('employee_id', 'department_id')
    def onchange_department_or_employee_id(self):
        domain = []
        if self.department_id:
            domain = [('department_id', '=', self.department_id.id)]
        if self.employee_id and self.department_id:
            domain = ['|'] + domain
        if self.employee_id:
            domain = domain + ['|', ('employee_id', '=', self.employee_id.id), ('employee_id', '=', None)]
        equipment = self.env['hr.equipment'].search(domain, limit=2)
        if len(equipment) == 1:
            self.equipment_id = equipment
        return {'domain': {'equipment_id': domain}}

    @api.onchange('equipment_id')
    def onchange_equipment_id(self):
        self.user_id = self.equipment_id.user_id if self.equipment_id.user_id else self.equipment_id.category_id.user_id
        self.category_id = self.equipment_id.category_id

    @api.onchange('category_id')
    def onchange_category_id(self):
        if not self.user_id or not self.equipment_id or (self.user_id and not self.equipment_id.user_id):
            self.user_id = self.category_id.user_id

    @api.model
    def create(self, vals):
        # context: no_log, because subtype already handle this
        self = self.with_context(mail_create_nolog=True)
        result = super(HrEquipmentRequest, self).create(vals)
        if result.employee_id.user_id:
            result.message_subscribe_users(user_ids=[result.employee_id.user_id.id])
        return result

    @api.multi
    def write(self, vals):
        # Overridden to reset the kanban_state to normal whenever
        # the stage (stage_id) of the Maintenance Request changes.
        if vals and 'kanban_state' not in vals and 'stage_id' in vals:
            vals['kanban_state'] = 'normal'
        if vals.get('employee_id'):
            employee = self.env['hr.employee'].browse(vals['employee_id'])
            if employee and employee.user_id:
                self.message_subscribe_users(user_ids=[employee.user_id.id])
        return super(HrEquipmentRequest, self).write(vals)

    @api.multi
    def _read_group_stage_ids(self, domain, read_group_order=None, access_rights_uid=None):
        """ Read group customization in order to display all the stages in the
            kanban view, even if they are empty
        """
        stage_obj = self.env['hr.equipment.stage']
        order = stage_obj._order
        access_rights_uid = access_rights_uid or self._uid

        if read_group_order == 'stage_id desc':
            order = '%s desc' % order

        stage_ids = stage_obj._search([], order=order, access_rights_uid=access_rights_uid)
        result = [stage.name_get()[0] for stage in stage_obj.browse(stage_ids)]

        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stage_obj.browse(stage_ids):
            fold[stage.id] = stage.fold or False
        return result, fold

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

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
        return super(HrEquipmentRequest, self).message_new(msg, custom_values=custom_values)
