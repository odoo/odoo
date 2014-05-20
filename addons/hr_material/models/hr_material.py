# -*- coding: utf-8 -*-
from openerp import models, fields, api, _, tools
from openerp.exceptions import Warning


class HrMaterialStage(models.Model):

    """Model for case stages. This models the main stages of a Maintenance Request management flow.
       Stages are for example used to display the kanban view of records.
    """

    _name = 'hr.material.stage'
    _description = 'Material Stage'
    _order = 'sequence asc'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence')
    fold = fields.Boolean('Folded in Kanban View')


class HrMaterialCategory(models.Model):
    _name = 'hr.material.category'
    _inherits = {"mail.alias": "alias_id"}
    _inherit = ['mail.thread']
    _description = 'Material Category'

    @api.multi
    def _compute_material_count(self):
        material_data = self.env['hr.material'].read_group(
        [('category_id', 'in', self.ids)], ['category_id'], ['category_id'])
        mapped_data = dict([(m['category_id'][0], m['category_id_count']) for m in material_data])
        for category in self:
            category.material_count = mapped_data.get(category.id, 0)

    @api.multi
    def _compute_maintenance_count(self):
        maintenance_data = self.env['hr.material.request'].read_group(
        [('category_id', 'in', self.ids)], ['category_id'], ['category_id'])
        mapped_data = dict([(m['category_id'][0], m['category_id_count']) for m in maintenance_data])
        for category in self:
            category.maintenance_count =  mapped_data.get(category.id, 0)

    @api.one
    @api.depends('material_ids')
    def _compute_fold(self):
        self.fold = False if self.material_count else True

    name = fields.Char('Category Name', required=True, translate=True)
    user_id = fields.Many2one('res.users', 'Responsible', track_visibility='onchange', default=lambda self: self.env.uid)
    color = fields.Integer('Color Index')
    note = fields.Text('Comments', translate=True)
    material_ids = fields.One2many('hr.material', 'category_id', string='Materials', copy=False)
    material_count = fields.Integer(compute='_compute_material_count', string="Material")
    maintenance_ids = fields.One2many('hr.material.request', 'category_id', copy=False, domain=[('stage_id.fold', '=', False)])
    maintenance_count = fields.Integer(compute='_compute_maintenance_count', string="Maintenance")
    alias_id = fields.Many2one(
        'mail.alias', 'Alias', ondelete='cascade', required=True,
        help="Email alias for this material category. New emails will automatically "
        "create new maintenance request for this material category.")
    fold = fields.Boolean(compute='_compute_fold', string='Folded in Kanban View', store=True)

    @api.model
    def create(self, vals):
        self = self.with_context(alias_model_name='hr.material.request', alias_parent_model_name=self._name)
        category_id = super(HrMaterialCategory, self).create(vals)
        category_id.alias_id.write({'alias_parent_thread_id': category_id.id, 'alias_defaults': {'category_id': category_id.id}})
        return category_id

    @api.multi
    def unlink(self):
        for category in self:
            if category.material_ids or category.maintenance_ids:
                raise Warning(_('You cannot delete a Material Category containing Material/Maintenance Request. You can either delete all the material/maintenance which belongs to in this category and then delete the material category.'))
        res = super(HrMaterialCategory, self).unlink()
        return res


class HrMaterial(models.Model):
    _name = 'hr.material'
    _inherit = ['mail.thread']
    _description = 'Material'

    _track = {
        'employee_id': {
            'hr_material.mt_mat_assign': lambda self, cr, uid, obj, ctx = None: obj.employee_id,
        },
        'department_id': {
            'hr_material.mt_mat_assign': lambda self, cr, uid, obj, ctx = None: obj.department_id,
        },
    }

    @api.one
    def _maintenance_count(self):
        self.maintenance_count = len(self.maintenance_ids)

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

    name = fields.Char('Name', required=True, translate=True)
    user_id = fields.Many2one('res.users', string='Technician', track_visibility='onchange')
    employee_id = fields.Many2one('hr.employee', string='Assigned to Employee', track_visibility='onchange')
    department_id = fields.Many2one('hr.department', string='Assigned to Department', track_visibility='onchange')
    category_id = fields.Many2one('hr.material.category', string='Material Category', track_visibility='onchange')
    partner_id = fields.Many2one('res.partner', string='Supplier', domain="[('supplier', '=', 1)]")
    model = fields.Char('Model')
    serial_no = fields.Char('Serial Number', copy=False)
    assign_date = fields.Date('Assigned Date', track_visibility='onchange')
    cost = fields.Float('Cost')
    note = fields.Text('Note', translate=True)
    color = fields.Integer('Color Index')
    scrap_date = fields.Date('Scrap Date')
    material_assign_to = fields.Selection(
        [('department', 'By Department'), ('employee', 'By Employee')],
        string='Allocate To',
        help='By Employee: Material assigned to individual Employee, By Department: Material assigned to group of employees in department',
        required=True,
        default='employee')
    maintenance_ids = fields.One2many('hr.material.request', 'material_id', domain=[('stage_id.fold', '=', False)])
    maintenance_count = fields.Integer(compute='_maintenance_count', string="Maintenance")

    _sql_constraints = [
        ('serial_no', 'unique(serial_no)', "The serial number of this material must be unique !"),
    ]

    @api.model
    def create(self, vals):
        material = super(HrMaterial, self).create(vals)
        # subscribe employee or department manager when material assign to him.
        user_ids = []
        if material.employee_id and material.employee_id.user_id:
            user_ids.append(material.employee_id.user_id.id)
        if material.department_id and material.department_id.manager_id and material.department_id.manager_id.user_id:
            user_ids.append(material.department_id.manager_id.user_id.id)
        if user_ids:
            material.message_subscribe_users(user_ids=user_ids)
        return material

    @api.multi
    def write(self, vals):
        user_ids = []
        # subscribe employee or department manager when material assign to employee or department.
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
        return super(HrMaterial, self).write(vals)

    @api.multi
    def _read_group_category_ids(self, domain, read_group_order=None, access_rights_uid=None):
        """ Read group customization in order to display all the category in the
        kanban view, even if they are empty """
        category_obj = self.env['hr.material.category']
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

    @api.onchange('material_assign_to')
    def _onchange_material_assign_to(self):
        if self.material_assign_to == 'employee':
            self.department_id = False
        if self.material_assign_to == 'department':
            self.employee_id = False
        self.assign_date = fields.Date.context_today(self)

    @api.onchange('category_id')
    def _onchange_category_id(self):
        self.user_id = self.category_id.user_id


class HrMaterialRequest(models.Model):
    _name = 'hr.material.request'
    _inherit = ['mail.thread']
    _description = 'Material Request'
    _track = {
        'stage_id': {
            'hr_material.mt_req_created': lambda self, cr, uid, obj, ctx = None: obj.stage_id and obj.stage_id.sequence <= 1,
            'hr_material.mt_req_status': lambda self, cr, uid, obj, ctx = None: obj.stage_id and obj.stage_id.sequence > 1,
        }}

    @api.returns('self')
    def _employee_get(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)

    @api.returns('self')
    def _default_stage(self):
        return self.env['hr.material.stage'].search([], limit=1)

    name = fields.Char('Subjects', required=True, translate=True)
    description = fields.Text('Description')
    request_date = fields.Date('Request Date', track_visibility='onchange', default=fields.Date.context_today)
    employee_id = fields.Many2one('hr.employee', string='Employee', default=_employee_get)
    department_id = fields.Many2one('hr.department', string='Department')
    category_id = fields.Many2one('hr.material.category', string='Category')
    material_id = fields.Many2one('hr.material', string='Material')
    user_id = fields.Many2one('res.users', string='Assigned to', track_visibility='onchange')
    stage_id = fields.Many2one(
        'hr.material.stage',
        string='Stage', ondelete='set null',
        track_visibility='onchange',
        default=_default_stage,
    )
    priority = fields.Selection(
        [('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')],
        string='Priority', select=True)
    color = fields.Integer('Color Index')
    close_date = fields.Date('Close Date')
    kanban_state = fields.Selection(
        [('normal', 'In Progress'), ('blocked', 'Blocked'), ('done', 'Ready for next stage')],
        string='Kanban State',
        required=False,
        default='normal',
        track_visibility='onchange')

    @api.multi
    def _read_group_stage_ids(self, domain, read_group_order=None, access_rights_uid=None):
        """ Read group customization in order to display all the stages in the
        kanban view, even if they are empty """
        stage_obj = self.env['hr.material.stage']
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
    def get_empty_list_help(self, help):
        res = super(HrMaterialRequest, self).get_empty_list_help(help)
        alias_record = self.env.ref('hr_material.mail_alias_material')
        check_alias_manage = self.env['ir.values'].get_default('hr.config.settings', 'alias_manage')
        if alias_record.alias_domain and alias_record.alias_name and res and check_alias_manage:
            return _("""<p class="oe_view_nocontent_create">
                            Click to add a new maintenance request or send an email to: <a>%(alias_name)s</a>
                        </p>
                        <p>
                            Follow the process of the request and communicate with the collaborator.
                        </p>"""
                     ) % {'alias_name': alias_record.alias_name + '@' + alias_record.alias_domain}
        return res

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        email = tools.email_split(msg.get('from')) and tools.email_split(msg.get('from'))[0] or False
        user = self.env['res.users'].search([('login', '=', email)])
        employee = self.env['hr.employee'].search([('user_id', '=', user.id)])
        custom_values['employee_id'] = employee and employee[0].id
        result = super(HrMaterialRequest, self).message_new(msg, custom_values=custom_values)
        if 'category_id' in custom_values:
            material_request = self.browse(result)
            material_request.onchange_category_id()
        return result

    @api.model
    def create(self, vals):
        # context: no_log, because subtype already handle this
        self = self.with_context(mail_create_nolog=True)
        result = super(HrMaterialRequest, self).create(vals)
        if result.employee_id.user_id:
            result.message_subscribe_users(user_ids=[result.employee_id.user_id.id])
        return result

    @api.multi
    def write(self, vals):
        # Overridden to reset the kanban_state to normal whenever
        # the stage (stage_id) of the Maintenance Request changes.
        if vals and not 'kanban_state' in vals and 'stage_id' in vals:
            new_stage = vals.get('stage_id')
            vals_reset_kstate = dict(vals, kanban_state='normal')
            for material_request in self:
                write_vals = vals_reset_kstate if material_request.stage_id.id != new_stage else vals
                material_request.write(write_vals)
        if vals.get('employee_id'):
            user_id = self.env['hr.employee'].browse(vals['employee_id'])['user_id']
            if user_id:
                self.message_subscribe_users(user_ids=[user_id.id])
        return super(HrMaterialRequest, self).write(vals)

    @api.onchange('employee_id', 'department_id')
    def onchange_department_or_employee_id(self):
        domain = []
        if self.department_id:
            domain = [('department_id', '=', self.department_id.id)]
        if self.employee_id and self.department_id:
            domain = ['|'] + domain
        if self.employee_id:
            domain = domain + ['|', ('employee_id', '=', self.employee_id.id), ('employee_id', '=', None)]
        material = self.env['hr.material'].search(domain)
        if len(material) == 1:
            self.material_id = material
        return {'domain': {'material_id': domain}}

    @api.onchange('material_id')
    def onchange_material_id(self):
        self.user_id = self.material_id.user_id if self.material_id.user_id else self.material_id.category_id.user_id
        self.category_id = self.material_id.category_id

    @api.onchange('category_id')
    def onchange_category_id(self):
        if not self.user_id or not self.material_id or (self.user_id and not self.material_id.user_id):
            self.user_id = self.category_id.user_id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
