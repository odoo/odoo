# -*- coding: utf-8 -*-

from openerp import api, fields, models, tools, _
from openerp.exceptions import ValidationError
from openerp.modules.module import get_resource_path


class HrEmployeeCategory(models.Model):
    _name = "hr.employee.category"
    _description = "Employee Category"

    name = fields.Char(string="Employee Tag", required=True)
    employee_ids = fields.Many2many('hr.employee',
        'employee_category_rel', 'category_id', 'emp_id',
        string='Employees')

    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class HrEmployee(models.Model):
    _name = "hr.employee"
    _description = "Employee"
    _order = 'name_related'
    _inherits = {'resource.resource': "resource_id"}
    _inherit = ['mail.thread']
 
    _mail_post_access = 'read'

    def _default_image(self):
        image_path = get_resource_path('hr', 'static/src/img/', 'default_image.png')
        return tools.image_resize_image_big(open(image_path, 'rb').read().encode('base64'))

    name_related = fields.Char(string='Name', related='resource_id.name', readonly=True, store=True)
    country_id = fields.Many2one('res.country', string='Nationality (Country)')
    birthday = fields.Date(string='Date of Birth')
    ssnid = fields.Char(string='SSN No', help='Social Security Number')
    sinid = fields.Char(string='SIN No', help='Social Insurance Number')
    identification_id = fields.Char(string='Identification No')
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
    child_ids = fields.One2many('hr.employee', 'parent_id', string='Subordinates')
    resource_id = fields.Many2one('resource.resource', string='Resource',
        ondelete='cascade', required=True, auto_join=True)
    coach_id = fields.Many2one('hr.employee', string='Coach')
    job_id = fields.Many2one('hr.job', string='Job Title')
    # image: all image fields are base64 encoded and PIL-supported
    image = fields.Binary(string='Photo',
        default=lambda self: self._default_image(),
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
    color = fields.Integer(string='Color Index', default=0)
    city = fields.Char(related='address_id.city')
    login = fields.Char(related='user_id.login', readonly=True)
    last_login = fields.Datetime(related='user_id.login_date',
        string='Latest Connection', readonly=True)
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
        self.work_email = self.user_id.email
        self.name = self.user_id.name
        self.image = self.user_id.image

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
        self.ensure_one()
        return self.message_subscribe_users()

    @api.multi
    def action_unfollow(self):
        """ Wrapper because message_unsubscribe_users take a user_ids=None
            that receive the context without the wrapper. """
        self.ensure_one()
        return self.message_unsubscribe_users()

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
