# -*- coding: utf-8 -*-

from openerp import api, fields, models, tools, SUPERUSER_ID, _
from openerp.exceptions import ValidationError
from openerp.modules.module import get_resource_path


class HrEmployeeCategory(models.Model):
    _name = "hr.employee.category"
    _description = "Employee Category"

    @api.multi
    def name_get(self):
        result = []
        for category in self:
            name = category.name
            if category.parent_id:
                name = category.parent_id.name + ' / ' + name
            result.append((category.id, name))
        return result

    name = fields.Char(string="Employee Tag", required=True)
    complete_name = fields.Char(compute='_compute_complete_name', string='Name')
    parent_id = fields.Many2one('hr.employee.category', string='Parent Employee Tag', index=True)
    child_ids = fields.One2many('hr.employee.category', 'parent_id', string='Child Categories')
    employee_ids = fields.Many2many('hr.employee',
        'employee_category_rel', 'category_id', 'emp_id',
        string='Employees')

    @api.one
    def _compute_complete_name(self):
        self.complete_name = self.name_get()[0][1]

    @api.one
    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Error! You cannot create recursive category.'))


class HrJob(models.Model):
    _name = "hr.job"
    _description = "Job Position"
    _inherit = ['mail.thread']

    name = fields.Char(string='Job Name', required=True, index=True, translate=True)
    expected_employees = fields.Integer(compute='_compute_employees',
         string='Total Forecasted Employees', store=True,
         help='Expected number of employees for this job position after new recruitment.')
    no_of_employee = fields.Integer(compute='_compute_employees',
         string='Current Number of Employees', store=True,
         help='Number of employees currently occupying this job position.')
    no_of_recruitment = fields.Integer(string='Expected New Employees', copy=False,
        help='Number of new employees you expect to recruit.', default=1)
    no_of_hired_employee = fields.Integer(string='Hired Employees', copy=False,
        help='Number of hired employees for this job position during recruitment phase.')
    employee_ids = fields.One2many('hr.employee', 'job_id',string='Employees',
        groups='base.group_user')
    description = fields.Text(string='Job Description')
    requirements = fields.Text()
    department_id = fields.Many2one('hr.department', string='Department')
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env['res.company']._company_default_get('hr.job'))
    state = fields.Selection([
            ('recruit', 'Recruitment in Progress'),
            ('open', 'Recruitment Closed')
        ], string='Status', readonly=True, required=True, track_visibility='always',
        copy=False, default='recruit',
        help='Set whether the recruitment process is open or closed for this job position.')
    write_date = fields.Datetime(string='Update Date', readonly=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, department_id)',
        'The name of the job position must be unique per department in company!'),
    ]

    @api.one
    @api.depends('no_of_recruitment', 'employee_ids')
    def _compute_employees(self):
        nb_employees = len(self.employee_ids)
        self.no_of_employee = nb_employees
        self.expected_employees = nb_employees + self.no_of_recruitment

    @api.one
    def copy(self, default=None):
        if default is None:
            default = {}
        if 'name' not in default:
            default['name'] = _("%s (copy)") % (self.name)
        return super(HrJob, self).copy(default=default)

    @api.multi
    def set_recruit(self):
        for job in self:
            no_of_recruitment = job.no_of_recruitment == 0 and 1 or job.no_of_recruitment
            job.write({'state': 'recruit', 'no_of_recruitment': no_of_recruitment})
        return True

    @api.multi
    def set_open(self):
        return self.write({
            'state': 'open',
            'no_of_recruitment': 0,
            'no_of_hired_employee': 0
        })

    # ----------------------------------------
    # Compatibility methods
    # ----------------------------------------
    job_open = set_open  # v7 compatibility
    job_recruitment = set_recruit  # v7 compatibility


class HrEmployee(models.Model):
    _name = "hr.employee"
    _description = "Employee"
    _order = 'name_related'
    _inherits = {'resource.resource': "resource_id"}
    _inherit = ['mail.thread']
 
    _mail_post_access = 'read'

    def _get_default_image(self):
        image_path = get_resource_path('hr', 'static/src/img/', 'default_image.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))

    #we need a related field in order to be able to sort the employee by name
    name_related = fields.Char(string='Name', related='resource_id.name', readonly=True, store=True)
    country_id = fields.Many2one('res.country', string='Nationality (Country)')
    birthday = fields.Date(string='Date of Birth')
    ssnid = fields.Char(string='SSN No', help='Social Security Number')
    sinid = fields.Char(string='SIN No', help='Social Insurance Number')
    identification_id = fields.Char(string='Identification No')
    otherid = fields.Char(string='Other Id')
    gender = fields.Selection([
         ('male', 'Male'),
         ('female', 'Female'),
         ('other', 'Other')
     ])
    marital = fields.Selection([
         ('single', 'Single'),
         ('married', 'Married'),
         ('widower', 'Widower'),
         ('divorced', 'Divorced')
     ], string='Marital Status')
    department_id = fields.Many2one('hr.department', string='Department')
    address_id = fields.Many2one('res.partner', string='Working Address')
    address_home_id = fields.Many2one('res.partner', string='Home Address')
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account Number',
            domain="[('partner_id', '=', address_home_id)]", help='Employee bank salary account')
    work_phone = fields.Char()
    mobile_phone = fields.Char(string='Work Mobile')
    work_email = fields.Char()
    work_location = fields.Char()
    notes = fields.Text()
    parent_id = fields.Many2one('hr.employee', string='Manager')
    category_ids = fields.Many2many('hr.employee.category',
        'employee_category_rel', 'emp_id', 'category_id',
        string='Tags')
    child_ids = fields.One2many('hr.employee', 'parent_id', 'Subordinates')
    resource_id = fields.Many2one('resource.resource', string='Resource',
        ondelete='cascade', required=True, auto_join=True)
    coach_id = fields.Many2one('hr.employee', string='Coach')
    job_id = fields.Many2one('hr.job', string='Job Title')
    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary(string='Photo',
        default=lambda self: self._get_default_image(),
        help='This field holds the image used as photo for the employee, limited to 1024x1024px.')
    image_medium = fields.Binary(string='Medium-sized photo', store=True,
        compute='_compute_image', inverse='_inverse_image_medium',
        help='Medium-sized photo of the employee. It is automatically '\
             'resized as a 128x128px image, with aspect ratio preserved. '\
             'Use this field in form views or some kanban views.')
    image_small = fields.Binary(string='Small-sized photo', store=True,
        compute='_compute_image', inverse='_inverse_image_small',
        help='Small-sized photo of the employee. It is automatically '\
             'resized as a 64x64px image, with aspect ratio preserved. '\
             'Use this field anywhere a small image is required.')
    passport_id = fields.Char(string='Passport No')
    color = fields.Integer(string='Color Index')
    city = fields.Char(related='address_id.city')
    login = fields.Char(related='user_id.login', readonly=1)
    last_login = fields.Datetime(related='user_id.login_date',
        string='Latest Connection', readonly=1)
    active = fields.Boolean(default=True)

    @api.one
    @api.depends('image')
    def _compute_image(self):
        self.image_medium = tools.image_resize_image_medium(self.image)
        self.image_small = tools.image_resize_image_small(self.image)

    @api.one
    def _inverse_image_medium(self):
        self.image = tools.image_resize_image_big(self.image_medium)

    @api.one
    def _inverse_image_small(self):
        self.image = tools.image_resize_image_big(self.image_small)

    @api.one
    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('Error! You cannot create recursive hierarchy of Employee(s).'))

    @api.onchange('address_id')
    def address_id_change(self):
        self.work_phone = self.address_id.phone
        self.mobile_phone = self.address_id.mobile

    @api.onchange('company_id')
    def company_id_change(self):
        address = self.company_id.partner_id.address_get(['default'])
        self.address_id = address and address['default'] or False

    @api.onchange('department_id')
    def onchange_department_id(self):
        self.parent_id = self.department_id.manager_id.id

    @api.onchange('user_id')
    def onchange_user(self):
        self.work_email = self.user_id.email

    @api.multi
    def unlink(self):
        Resource = self.env['resource.resource']
        for employee in self:
            Resource += employee.resource_id
        Resource.unlink()
        return super(HrEmployee, self).unlink()

    @api.multi
    def action_follow(self):
        """ Wrapper because message_subscribe_users take a user_ids=None
            that receive the context without the wrapper. """
        return self.message_subscribe_users()

    @api.multi
    def action_unfollow(self):
        """ Wrapper because message_unsubscribe_users take a user_ids=None
            that receive the context without the wrapper. """
        return self.message_unsubscribe_users()

    @api.model
    def get_suggested_thread(self, removed_suggested_threads=None):
        """Show the suggestion of employees if display_employees_suggestions if the
        user perference allows it. """
        if not self.env.user.display_employees_suggestions:
            return []
        else:
            return super(HrEmployee, self).get_suggested_thread(removed_suggested_threads)

    @api.model
    def _message_get_auto_subscribe_fields(self, updated_fields, auto_follow_fields=None):
        """ Overwrite of the original method to always follow user_id field,
        even when not track_visibility so that a user will follow it's employee
        """
        if auto_follow_fields is None:
            auto_follow_fields = ['user_id']
        user_field_lst = []
        for name, field in self._fields.items():
            if name in auto_follow_fields and name in updated_fields and field.comodel_name == 'res.users':
                user_field_lst.append(name)
        return user_field_lst


class HrDepartment(models.Model):
    _name = "hr.department"
    _description = "HR Department"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    @api.multi
    def name_get(self):
        result = []
        for department in self:
            name = department.name
            if department.parent_id:
                name = department.parent_id.name + ' / ' + name
            result.append((department.id, name))
        return result

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


class ResUsers(models.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    @api.multi
    def write(self, vals):
        Employee = self.env['hr.employee']
        if vals.get('name'):
            for user in self.filtered(lambda user: user.id == SUPERUSER_ID):
                employees = Employee.search([('user_id', '=', user.id)])
                employees.write({'name': vals['name']})
        return super(ResUsers, self).write(vals)
