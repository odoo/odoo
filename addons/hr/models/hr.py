# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from random import choice
from string import digits
import base64
import logging
from werkzeug import url_encode

from odoo import api, fields, models, SUPERUSER_ID
from odoo import tools, _
from odoo.exceptions import ValidationError, AccessError
from odoo.modules.module import get_module_resource

_logger = logging.getLogger(__name__)


class EmployeeCategory(models.Model):

    _name = "hr.employee.category"
    _description = "Employee Category"

    name = fields.Char(string="Employee Tag", required=True)
    color = fields.Integer(string='Color Index')
    employee_ids = fields.Many2many('hr.employee', 'employee_category_rel', 'category_id', 'emp_id', string='Employees')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class Job(models.Model):

    _name = "hr.job"
    _description = "Job Position"
    _inherit = ['mail.thread']

    name = fields.Char(string='Job Position', required=True, index=True, translate=True)
    expected_employees = fields.Integer(compute='_compute_employees', string='Total Forecasted Employees', store=True,
        help='Expected number of employees for this job position after new recruitment.')
    no_of_employee = fields.Integer(compute='_compute_employees', string="Current Number of Employees", store=True,
        help='Number of employees currently occupying this job position.')
    no_of_recruitment = fields.Integer(string='Expected New Employees', copy=False,
        help='Number of new employees you expect to recruit.', default=1)
    no_of_hired_employee = fields.Integer(string='Hired Employees', copy=False,
        help='Number of hired employees for this job position during recruitment phase.')
    employee_ids = fields.One2many('hr.employee', 'job_id', string='Employees', groups='base.group_user')
    description = fields.Text(string='Job Description')
    requirements = fields.Text('Requirements')
    department_id = fields.Many2one('hr.department', string='Department')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    state = fields.Selection([
        ('recruit', 'Recruitment in Progress'),
        ('open', 'Not Recruiting')
    ], string='Status', readonly=True, required=True, tracking=True, copy=False, default='recruit', help="Set whether the recruitment process is open or closed for this job position.")

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, department_id)', 'The name of the job position must be unique per department in company!'),
    ]

    @api.depends('no_of_recruitment', 'employee_ids.job_id', 'employee_ids.active')
    def _compute_employees(self):
        employee_data = self.env['hr.employee'].read_group([('job_id', 'in', self.ids)], ['job_id'], ['job_id'])
        result = dict((data['job_id'][0], data['job_id_count']) for data in employee_data)
        for job in self:
            job.no_of_employee = result.get(job.id, 0)
            job.expected_employees = result.get(job.id, 0) + job.no_of_recruitment

    @api.model
    def create(self, values):
        """ We don't want the current user to be follower of all created job """
        return super(Job, self.with_context(mail_create_nosubscribe=True)).create(values)

    @api.multi
    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if 'name' not in default:
            default['name'] = _("%s (copy)") % (self.name)
        return super(Job, self).copy(default=default)

    @api.multi
    def set_recruit(self):
        for record in self:
            no_of_recruitment = 1 if record.no_of_recruitment == 0 else record.no_of_recruitment
            record.write({'state': 'recruit', 'no_of_recruitment': no_of_recruitment})
        return True

    @api.multi
    def set_open(self):
        return self.write({
            'state': 'open',
            'no_of_recruitment': 0,
            'no_of_hired_employee': 0
        })


class Employee(models.Model):
    _name = "hr.employee"
    _description = "Employee"
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'resource.mixin']

    _mail_post_access = 'read'

    @api.model
    def _default_image(self):
        image_path = get_module_resource('hr', 'static/src/img', 'default_image.png')
        return tools.image_resize_image_big(base64.b64encode(open(image_path, 'rb').read()))

    # resource and user
    # required on the resource, make sure required="True" set in the view
    name = fields.Char(related='resource_id.name', store=True, oldname='name_related', readonly=False, tracking=True)
    user_id = fields.Many2one('res.users', 'User', related='resource_id.user_id', store=True, readonly=False)
    user_partner_id = fields.Many2one(related='user_id.partner_id', related_sudo=False, string="User's partner")
    active = fields.Boolean('Active', related='resource_id.active', default=True, store=True, readonly=False)
    # private partner
    address_home_id = fields.Many2one(
        'res.partner', 'Private Address', help='Enter here the private address of the employee, not the one linked to your company.',
        groups="hr.group_hr_user", tracking=True)
    is_address_home_a_company = fields.Boolean(
        'The employee adress has a company linked',
        compute='_compute_is_address_home_a_company',
    )
    country_id = fields.Many2one(
        'res.country', 'Nationality (Country)', groups="hr.group_hr_user", tracking=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], groups="hr.group_hr_user", default="male", tracking=True)
    marital = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('cohabitant', 'Legal Cohabitant'),
        ('widower', 'Widower'),
        ('divorced', 'Divorced')
    ], string='Marital Status', groups="hr.group_hr_user", default='single', tracking=True)
    spouse_complete_name = fields.Char(string="Spouse Complete Name", groups="hr.group_hr_user", tracking=True)
    spouse_birthdate = fields.Date(string="Spouse Birthdate", groups="hr.group_hr_user", tracking=True)
    children = fields.Integer(string='Number of Children', groups="hr.group_hr_user", tracking=True)
    place_of_birth = fields.Char('Place of Birth', groups="hr.group_hr_user", tracking=True)
    country_of_birth = fields.Many2one('res.country', string="Country of Birth", groups="hr.group_hr_user", tracking=True)
    birthday = fields.Date('Date of Birth', groups="hr.group_hr_user", tracking=True)
    ssnid = fields.Char('SSN No', help='Social Security Number', groups="hr.group_hr_user", tracking=True)
    sinid = fields.Char('SIN No', help='Social Insurance Number', groups="hr.group_hr_user", tracking=True)
    identification_id = fields.Char(string='Identification No', groups="hr.group_hr_user", tracking=True)
    passport_id = fields.Char('Passport No', groups="hr.group_hr_user", tracking=True)
    bank_account_id = fields.Many2one(
        'res.partner.bank', 'Bank Account Number',
        domain="[('partner_id', '=', address_home_id)]",
        groups="hr.group_hr_user",
        tracking=True,
        help='Employee bank salary account')
    permit_no = fields.Char('Work Permit No', groups="hr.group_hr_user", tracking=True)
    visa_no = fields.Char('Visa No', groups="hr.group_hr_user", tracking=True)
    visa_expire = fields.Date('Visa Expire Date', groups="hr.group_hr_user", tracking=True)
    additional_note = fields.Text(string='Additional Note', groups="hr.group_hr_user", tracking=True)
    certificate = fields.Selection([
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('other', 'Other'),
    ], 'Certificate Level', default='master', groups="hr.group_hr_user", tracking=True)
    study_field = fields.Char("Field of Study", placeholder='Computer Science', groups="hr.group_hr_user", tracking=True)
    study_school = fields.Char("School", groups="hr.group_hr_user", tracking=True)
    emergency_contact = fields.Char("Emergency Contact", groups="hr.group_hr_user", tracking=True)
    emergency_phone = fields.Char("Emergency Phone", groups="hr.group_hr_user", tracking=True)
    km_home_work = fields.Integer(string="Km home-work", groups="hr.group_hr_user", tracking=True)
    google_drive_link = fields.Char(string="Employee Documents", groups="hr.group_hr_user", tracking=True)
    job_title = fields.Char("Job Title")

    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary(
        "Photo", default=_default_image,
        help="This field holds the image used as photo for the employee, limited to 1024x1024px.")
    image_medium = fields.Binary(
        "Medium-sized photo",
        help="Medium-sized photo of the employee. It is automatically "
             "resized as a 128x128px image, with aspect ratio preserved. "
             "Use this field in form views or some kanban views.")
    image_small = fields.Binary(
        "Small-sized photo",
        help="Small-sized photo of the employee. It is automatically "
             "resized as a 64x64px image, with aspect ratio preserved. "
             "Use this field anywhere a small image is required.")
    # work
    address_id = fields.Many2one(
        'res.partner', 'Work Address')
    work_phone = fields.Char('Work Phone')
    mobile_phone = fields.Char('Work Mobile')
    phone = fields.Char(related='address_home_id.phone', related_sudo=False, string="Private Phone", groups="hr.group_hr_user")
    work_email = fields.Char('Work Email')
    work_location = fields.Char('Work Location')
    # employee in company
    job_id = fields.Many2one('hr.job', 'Job Position')
    department_id = fields.Many2one('hr.department', 'Department')
    parent_id = fields.Many2one('hr.employee', 'Manager')
    child_ids = fields.One2many('hr.employee', 'parent_id', string='Direct subordinates')
    coach_id = fields.Many2one('hr.employee', 'Coach')
    category_ids = fields.Many2many(
        'hr.employee.category', 'employee_category_rel',
        'emp_id', 'category_id',
        string='Tags')
    # misc
    notes = fields.Text('Notes')
    color = fields.Integer('Color Index', default=0)
    barcode = fields.Char(string="Badge ID", help="ID used for employee identification.", copy=False)
    pin = fields.Char(string="PIN", help="PIN used to Check In/Out in Kiosk Mode (if enabled in Configuration).", copy=False)
    departure_reason = fields.Selection([
        ('fired', 'Fired'),
        ('resigned', 'Resigned'),
        ('retired', 'Retired')
    ], string="Departure Reason", copy=False, tracking=True)
    departure_description = fields.Text(string="Additional Information", copy=False, tracking=True)

    _sql_constraints = [
        ('barcode_uniq', 'unique (barcode)', "The Badge ID must be unique, this one is already assigned to another employee."),
        ('user_uniq', 'unique (user_id, company_id)', "A user cannot be linked to multiple employees in the same company.")
    ]

    @api.constrains('pin')
    def _verify_pin(self):
        for employee in self:
            if employee.pin and not employee.pin.isdigit():
                raise ValidationError(_("The PIN must be a sequence of digits."))

    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        manager = self.parent_id
        previous_manager = self._origin.parent_id
        if manager and (self.coach_id == previous_manager or not self.coach_id):
            self.coach_id = manager

    @api.onchange('job_id')
    def _onchange_job_id(self):
        if self.job_id:
            self.job_title = self.job_id.name

    @api.onchange('address_id')
    def _onchange_address(self):
        self.work_phone = self.address_id.phone
        self.mobile_phone = self.address_id.mobile

    @api.onchange('company_id')
    def _onchange_company(self):
        address = self.company_id.partner_id.address_get(['default'])
        self.address_id = address['default'] if address else False

    @api.onchange('department_id')
    def _onchange_department(self):
        self.parent_id = self.department_id.manager_id

    @api.onchange('user_id')
    def _onchange_user(self):
        if self.user_id:
            self.update(self._sync_user(self.user_id))

    @api.onchange('resource_calendar_id')
    def _onchange_timezone(self):
        if self.resource_calendar_id and not self.tz:
            self.tz = self.resource_calendar_id.tz

    def _sync_user(self, user):
        vals = dict(
            name=user.name,
            image=user.image,
            work_email=user.email,
        )
        if user.tz:
            vals['tz'] = user.tz
        return vals

    @api.model
    def create(self, vals):
        if vals.get('user_id'):
            vals.update(self._sync_user(self.env['res.users'].browse(vals['user_id'])))
        tools.image_resize_images(vals)
        employee = super(Employee, self).create(vals)
        url = '/web#%s' % url_encode({'action': 'hr.plan_wizard_action', 'active_id': employee.id, 'active_model': 'hr.employee'})
        employee._message_log(_('<b>Congratulations !</b> May I recommand you to setup an <a href="%s">onboarding plan ?</a>') % (url))
        if employee.department_id:
            self.env['mail.channel'].sudo().search([
                ('subscription_department_ids', 'in', employee.department_id.id)
            ])._subscribe_users()
        return employee

    @api.multi
    def write(self, vals):
        if 'address_home_id' in vals:
            account_id = vals.get('bank_account_id') or self.bank_account_id.id
            if account_id:
                self.env['res.partner.bank'].browse(account_id).partner_id = vals['address_home_id']
        if vals.get('user_id'):
            vals.update(self._sync_user(self.env['res.users'].browse(vals['user_id'])))
        tools.image_resize_images(vals)
        res = super(Employee, self).write(vals)
        if vals.get('department_id') or vals.get('user_id'):
            department_id = vals['department_id'] if vals.get('department_id') else self[:1].department_id.id
            # When added to a department or changing user, subscribe to the channels auto-subscribed by department
            self.env['mail.channel'].sudo().search([
                ('subscription_department_ids', 'in', department_id)
            ])._subscribe_users()
        return res

    @api.multi
    def unlink(self):
        resources = self.mapped('resource_id')
        super(Employee, self).unlink()
        return resources.unlink()

    def toggle_active(self):
        res = super(Employee, self).toggle_active()
        self.filtered(lambda employee: employee.active).write({
            'departure_reason': False,
            'departure_description': False,
        })
        if len(self) == 1 and not self.active:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Register Departure'),
                'res_model': 'hr.departure.wizard',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': {'active_id': self.id},
            }
        return res

    @api.multi
    def generate_random_barcode(self):
        for i in self: i.barcode = "".join(choice(digits) for i in range(8))

    @api.depends('address_home_id.parent_id')
    def _compute_is_address_home_a_company(self):
        """Checks that choosen address (res.partner) is not linked to a company.
        """
        for employee in self:
            try:
                employee.is_address_home_a_company = employee.address_home_id.parent_id.id is not False
            except AccessError:
                employee.is_address_home_a_company = False

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Employees'),
            'template': '/hr/static/xls/hr_employee.xls'
        }]

    def _post_author(self):
        """
        When a user updates his own employee's data, all operations are performed
        by super user. However, tracking messages should not be posted as OdooBot
        but as the actual user.
        This method is used in the overrides of `_message_log` and `message_post`
        to post messages as the correct user.
        """
        real_user = self.env.context.get('binary_field_real_user')
        if self.env.user.id == SUPERUSER_ID and real_user:
            self = self.sudo(real_user)
        return self

    def _message_log(self, *args, **kwargs):
        return super(Employee, self._post_author())._message_log(*args, **kwargs)

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *args, **kwargs):
        return super(Employee, self._post_author()).message_post(*args, **kwargs)


class Department(models.Model):
    _name = "hr.department"
    _description = "HR Department"
    _inherit = ['mail.thread']
    _order = "name"
    _rec_name = 'complete_name'

    name = fields.Char('Department Name', required=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id)
    parent_id = fields.Many2one('hr.department', string='Parent Department', index=True)
    child_ids = fields.One2many('hr.department', 'parent_id', string='Child Departments')
    manager_id = fields.Many2one('hr.employee', string='Manager', tracking=True)
    member_ids = fields.One2many('hr.employee', 'department_id', string='Members', readonly=True)
    jobs_ids = fields.One2many('hr.job', 'department_id', string='Jobs')
    note = fields.Text('Note')
    color = fields.Integer('Color Index')

    @api.multi
    def name_get(self):
        if not self.env.context.get('hierarchical_naming', True):
            return [(record.id, record.name) for record in self]
        return super(Department, self).name_get()

    @api.model
    def name_create(self, name):
        return self.create({'name': name}).name_get()[0]

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for department in self:
            if department.parent_id:
                department.complete_name = '%s / %s' % (department.parent_id.complete_name, department.name)
            else:
                department.complete_name = department.name

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive departments.'))

    @api.model
    def create(self, vals):
        # TDE note: auto-subscription of manager done by hand, because currently
        # the tracking allows to track+subscribe fields linked to a res.user record
        # An update of the limited behavior should come, but not currently done.
        department = super(Department, self.with_context(mail_create_nosubscribe=True)).create(vals)
        manager = self.env['hr.employee'].browse(vals.get("manager_id"))
        if manager.user_id:
            department.message_subscribe(partner_ids=manager.user_id.partner_id.ids)
        return department

    @api.multi
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
