# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import choice
from pytz import timezone, UTC, utc
from datetime import timedelta, datetime
from string import digits

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_time
from odoo.addons.base.models.res_partner import _tz_get

class HrEmployeeVersion(models.Model):
    _name = 'hr.employee.version'
    _description = "Employee Version"
    _order = 'date_to'

    name = fields.Char(string='Name', compute='_compute_name', store=True, readonly=False)
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')

    # Employee Permanent Fields
    employee_id = fields.Many2one('hr.employee')
    user_id = fields.Many2one(related='employee_id.user_id', store=True, readonly=False)
    company_id = fields.Many2one(related='employee_id.company_id')
    work_contact_id = fields.Many2one(related='employee_id.work_contact_id')
    employee_active = fields.Boolean(related='employee_id.active')
    hr_presence_state = fields.Selection(related='employee_id.hr_presence_state')
    child_ids = fields.One2many(related='employee_id.child_ids')
    selected_history_id = fields.Many2one(related='employee_id.selected_version_id', store=True, readonly=False,
                                          domain="[('employee_id', '=', employee_id)]")

    avatar_128 = fields.Image(related='employee_id.avatar_128', readonly=False)
    image_1920 = fields.Image(related='employee_id.image_1920', readonly=False)
    hr_icon_display = fields.Selection(related='employee_id.hr_icon_display', readonly=False)
    show_hr_icon_display = fields.Boolean(related='employee_id.show_hr_icon_display', readonly=False)

    # Global Information
    employee_name = fields.Char(related='employee_id.name', readonly=False)
    category_ids = fields.Many2many(related='employee_id.category_ids', readonly=False)

    private_phone = fields.Char(related='employee_id.private_phone', readonly=False)
    private_email = fields.Char(related='employee_id.private_email', readonly=False)
    bank_account_id = fields.Many2one(related='employee_id.bank_account_id', readonly=False)

    work_phone = fields.Char(related='employee_id.work_phone', readonly=False)
    mobile_phone = fields.Char(related='employee_id.mobile_phone', readonly=False)
    work_email = fields.Char(related='employee_id.work_email', readonly=False)

    emergency_contact = fields.Char(related='employee_id.emergency_contact', readonly=False)
    emergency_phone = fields.Char(related='employee_id.emergency_phone', readonly=False)

    sex = fields.Selection(related='employee_id.sex', readonly=False)
    place_of_birth = fields.Char(related='employee_id.place_of_birth', readonly=False)
    country_of_birth = fields.Many2one(related='employee_id.country_of_birth', readonly=False)
    birthday = fields.Date(related='employee_id.birthday', readonly=False)
    birthday_public_display = fields.Boolean(related='employee_id.birthday_public_display', readonly=False)
    birthday_public_display_string = fields.Char(related='employee_id.birthday_public_display_string', readonly=False)

    visa_no = fields.Char(related='employee_id.visa_no', readonly=False)
    visa_expire = fields.Date(related='employee_id.visa_expire', readonly=False)

    permit_no = fields.Char(related='employee_id.permit_no', readonly=False)
    work_permit_expiration_date = fields.Date(related='employee_id.work_permit_expiration_date', readonly=False)
    work_permit_name = fields.Char(related='employee_id.work_permit_name', readonly=False)
    work_permit_scheduled_activity = fields.Boolean(related='employee_id.work_permit_scheduled_activity', readonly=False)
    has_work_permit = fields.Binary(related='employee_id.has_work_permit', readonly=False)

    barcode = fields.Char(related='employee_id.barcode', readonly=False)
    pin = fields.Char(related='employee_id.pin', readonly=False)

    # Personal Information
    country_id = fields.Many2one('res.country', 'Nationality (Country)', groups="hr.group_hr_user")
    identification_id = fields.Char(string='Identification No', groups="hr.group_hr_user")
    ssnid = fields.Char('SSN No', help='Social Security Number', groups="hr.group_hr_user")
    passport_id = fields.Char('Passport No', groups="hr.group_hr_user")

    private_street = fields.Char(string="Private Street", groups="hr.group_hr_user")
    private_street2 = fields.Char(string="Private Street2", groups="hr.group_hr_user")
    private_city = fields.Char(string="Private City", groups="hr.group_hr_user")
    private_state_id = fields.Many2one(
        "res.country.state", string="Private State",
        domain="[('country_id', '=?', private_country_id)]",
        groups="hr.group_hr_user")
    private_zip = fields.Char(string="Private Zip", groups="hr.group_hr_user")
    private_country_id = fields.Many2one("res.country", string="Private Country",
                                         groups="hr.group_hr_user")

    distance_home_work = fields.Integer(string="Home-Work Distance", groups="hr.group_hr_user")
    km_home_work = fields.Integer(string="Home-Work Distance in Km", groups="hr.group_hr_user",
                                  compute="_compute_km_home_work", inverse="_inverse_km_home_work", store=True)
    distance_home_work_unit = fields.Selection([
        ('kilometers', 'km'),
        ('miles', 'mi'),
    ], 'Home-Work Distance unit', groups="hr.group_hr_user", default='kilometers', required=True)

    marital = fields.Selection(
        selection='_get_marital_status_selection',
        string='Marital Status',
        groups="hr.group_hr_user",
        default='single',
        required=True)
    spouse_complete_name = fields.Char(string="Spouse Legal Name", groups="hr.group_hr_user")
    spouse_birthdate = fields.Date(string="Spouse Birthdate", groups="hr.group_hr_user")
    children = fields.Integer(string='Dependent Children', groups="hr.group_hr_user")

    certificate = fields.Selection([
        ('graduate', 'Graduate'),
        ('bachelor', 'Bachelor'),
        ('master', 'Master'),
        ('doctor', 'Doctor'),
        ('other', 'Other'),
    ], 'Certificate Level', groups="hr.group_hr_user")
    study_field = fields.Char("Field of Study", groups="hr.group_hr_user")

    # Work Information
    department_id = fields.Many2one('hr.department', check_company=True)
    job_id = fields.Many2one('hr.job', check_company=True)
    job_title = fields.Char(related='job_id.name', readonly=False)
    parent_id = fields.Many2one('hr.employee', 'Manager', compute="_compute_parent_id",
                                store=True, readonly=False,
                                domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]")

    address_id = fields.Many2one(
        'res.partner',
        string='Work Address',
        compute="_compute_address_id",
        store=True,
        readonly=False,
        check_company=True)
    work_location_id = fields.Many2one('hr.work.location', 'Work Location',
                                       domain="[('address_id', '=', address_id)]")
    work_location_name = fields.Char("Work Location Name", compute="_compute_work_location_name_type")
    work_location_type = fields.Selection([
        ("home", "Home"),
        ("office", "Office"),
        ("other", "Other")], compute="_compute_work_location_name_type")

    departure_reason_id = fields.Many2one("hr.departure.reason", string="Departure Reason",
                                          groups="hr.group_hr_user", copy=False, ondelete='restrict')
    departure_description = fields.Html(string="Additional Information", groups="hr.group_hr_user", copy=False)
    departure_date = fields.Date(string="Departure Date", groups="hr.group_hr_user", copy=False)

    resource_calendar_id = fields.Many2one('resource.calendar', check_company=True)
    tz = fields.Selection(
        _tz_get, string='Timezone', required=True,
        default=lambda self: self._context.get('tz') or self.env.user.tz or self.env.ref('base.user_admin').tz or 'UTC',
        help="This field is used in order to define in which timezone the employee will work.")

    @api.depends('date_from', 'date_to')
    def _compute_name(self):
        for record in self:
            if record.date_from:
                record.name = datetime.strftime(record.date_from, '%-d %b %Y')
            else:
                record.name = _('Original')

    @api.depends("work_location_id.name", "work_location_id.location_type")
    def _compute_work_location_name_type(self):
        for employee in self:
            employee.work_location_name = employee.work_location_id.name or None
            employee.work_location_type = employee.work_location_id.location_type or 'other'

    @api.depends('distance_home_work', 'distance_home_work_unit')
    def _compute_km_home_work(self):
        for employee in self:
            employee.km_home_work = employee.distance_home_work * 1.609 if employee.distance_home_work_unit == "miles" else employee.distance_home_work

    def _inverse_km_home_work(self):
        for employee in self:
            employee.distance_home_work = employee.km_home_work / 1.609 if employee.distance_home_work_unit == "miles" else employee.km_home_work

    @api.model
    def _get_marital_status_selection(self):
        return [
            ('single', _('Single')),
            ('married', _('Married')),
            ('cohabitant', _('Legal Cohabitant')),
            ('widower', _('Widower')),
            ('divorced', _('Divorced')),
        ]

    @api.depends('department_id')
    def _compute_parent_id(self):
        for employee in self.filtered('department_id.manager_id'):
            employee.parent_id = employee.department_id.manager_id

    @api.depends('company_id')
    def _compute_address_id(self):
        for employee in self:
            address = employee.company_id.partner_id.address_get(['default'])
            employee.address_id = address['default'] if address else False

    def action_create_user(self):
        self.ensure_one()
        if self.user_id:
            raise ValidationError(_("This employee already has an user."))
        return {
            'name': _('Create User'),
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'form',
            'view_id': self.env.ref('hr.view_users_simple_form').id,
            'target': 'new',
            'context': dict(self._context, **{
                'default_create_employee_id': self.employee_id.id,
                'default_name': self.employee_name,
                'default_phone': self.work_phone,
                'default_mobile': self.mobile_phone,
                'default_login': self.work_email,
                'default_partner_id': self.work_contact_id.id,
            })
        }

    def generate_random_barcode(self):
        for history in self:
            history.barcode = '041' + ''.join(choice(digits) for _ in range(9))

    # department_id = fields.Many2one('hr.department', 'Department', check_company=True)
    # member_of_department = fields.Boolean("Member of department", compute='_compute_part_of_department',
    #                                       search='_search_part_of_department',
    #                                       help="Whether the employee is a member of the active user's department or one of it's child department.")
    # job_id = fields.Many2one('hr.job', 'Job Position', check_company=True)
    # job_title = fields.Char("Job Title", compute="_compute_job_title", store=True, readonly=False)
    # company_id = fields.Many2one('res.company', 'Company')
    # address_id = fields.Many2one(
    #     'res.partner',
    #     string='Work Address',
    #     compute="_compute_address_id",
    #     precompute=True,
    #     store=True,
    #     readonly=False,
    #     check_company=True)
    # work_phone = fields.Char('Work Phone', compute="_compute_phones", store=True, readonly=False)
    # phone = fields.Char(related="user_id.phone")
    # mobile_phone = fields.Char('Work Mobile', compute="_compute_work_contact_details", store=True,
    #                            inverse='_inverse_work_contact_details')
    # work_email = fields.Char('Work Email', compute="_compute_work_contact_details", store=True,
    #                          inverse='_inverse_work_contact_details')
    # email = fields.Char(related="user_id.email")
    # work_contact_id = fields.Many2one('res.partner', 'Work Contact', copy=False)
    # work_location_id = fields.Many2one('hr.work.location', 'Work Location', domain="[('address_id', '=', address_id)]")
    # work_location_name = fields.Char("Work Location Name", compute="_compute_work_location_name_type")
    # work_location_type = fields.Selection([
    #     ("home", "Home"),
    #     ("office", "Office"),
    #     ("other", "Other")], compute="_compute_work_location_name_type")
    # user_id = fields.Many2one('res.users', help="")
    # share = fields.Boolean(related='user_id.share')
    # resource_calendar_id = fields.Many2one('resource.calendar', check_company=True)
    # is_flexible = fields.Boolean(compute='_compute_is_flexible', store=True)
    # is_fully_flexible = fields.Boolean(compute='_compute_is_flexible', store=True)
    # parent_id = fields.Many2one('hr.employee', 'Manager', compute="_compute_parent_id", store=True, readonly=False,
    #                             domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]")
    # coach_id = fields.Many2one(
    #     'hr.employee', 'Coach', compute='_compute_coach', store=True, readonly=False,
    #     domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]",
    #     help='Select the "Employee" who is the coach of this employee.\n'
    #          'The "Coach" has no specific rights or responsibilities by default.')
    # tz = fields.Selection(
    #     string='Timezone', related='resource_id.tz', readonly=False,
    #     help="This field is used in order to define in which timezone the employee will work.")
    # hr_presence_state = fields.Selection([
    #     ('present', 'Present'),
    #     ('absent', 'Absent'),
    #     ('archive', 'Archived'),
    #     ('out_of_working_hour', 'Out of Working hours')], compute='_compute_presence_state',
    #     default='out_of_working_hour')
    # last_activity = fields.Date(compute="_compute_last_activity")
    # last_activity_time = fields.Char(compute="_compute_last_activity")
    # hr_icon_display = fields.Selection([
    #     ('presence_present', 'Present'),
    #     ('presence_out_of_working_hour', 'Out of Working hours'),
    #     ('presence_absent', 'Absent'),
    #     ('presence_archive', 'Archived'),
    #     ('presence_undetermined', 'Undetermined')], compute='_compute_presence_icon')
    # show_hr_icon_display = fields.Boolean(compute='_compute_presence_icon')
    # im_status = fields.Char(related="user_id.im_status")
    # newly_hired = fields.Boolean('Newly Hired', compute='_compute_newly_hired', search='_search_newly_hired')
    #
    # # resource and user
    # # required on the resource, make sure required="True" set in the view
    # name = fields.Char(string="Employee Name", related='resource_id.name', store=True, readonly=False, tracking=True)
    # user_id = fields.Many2one(
    #     'res.users', 'User',
    #     related='resource_id.user_id',
    #     store=True,
    #     readonly=False,
    #     check_company=True,
    #     precompute=True,
    #     ondelete='restrict')
    # user_partner_id = fields.Many2one(related='user_id.partner_id', related_sudo=False, string="User's partner")
    # active = fields.Boolean('Active', related='resource_id.active', default=True, store=True, readonly=False)
    # resource_calendar_id = fields.Many2one(tracking=True)
    # department_id = fields.Many2one(tracking=True)
    # company_id = fields.Many2one('res.company', required=True)
    # company_country_id = fields.Many2one('res.country', 'Company Country', related='company_id.country_id', readonly=True, groups="base.group_system,hr.group_hr_user")
    # company_country_code = fields.Char(related='company_country_id.code', depends=['company_country_id'], readonly=True, groups="base.group_system,hr.group_hr_user")
    # # private info
    # private_street = fields.Char(string="Private Street", groups="hr.group_hr_user")
    # private_street2 = fields.Char(string="Private Street2", groups="hr.group_hr_user")
    # private_city = fields.Char(string="Private City", groups="hr.group_hr_user")
    # private_state_id = fields.Many2one(
    #     "res.country.state", string="Private State",
    #     domain="[('country_id', '=?', private_country_id)]",
    #     groups="hr.group_hr_user")
    # private_zip = fields.Char(string="Private Zip", groups="hr.group_hr_user")
    # private_country_id = fields.Many2one("res.country", string="Private Country", groups="hr.group_hr_user")
    # private_phone = fields.Char(string="Private Phone", groups="hr.group_hr_user")
    # private_email = fields.Char(string="Private Email", groups="hr.group_hr_user")
    # lang = fields.Selection(selection=_lang_get, string="Lang", groups="hr.group_hr_user")
    # country_id = fields.Many2one(
    #     'res.country', 'Nationality (Country)', groups="hr.group_hr_user", tracking=True)
    # gender = fields.Selection([
    #     ('male', 'Male'),
    #     ('female', 'Female'),
    #     ('other', 'Other')
    # ], groups="hr.group_hr_user", tracking=True)
    # marital = fields.Selection(
    #     selection='_get_marital_status_selection',
    #     string='Marital Status',
    #     groups="hr.group_hr_user",
    #     default='single',
    #     required=True,
    #     tracking=True)
    #
    # spouse_complete_name = fields.Char(string="Spouse Complete Name", groups="hr.group_hr_user", tracking=True)
    # spouse_birthdate = fields.Date(string="Spouse Birthdate", groups="hr.group_hr_user", tracking=True)
    # children = fields.Integer(string='Number of Dependent Children', groups="hr.group_hr_user", tracking=True)
    # place_of_birth = fields.Char('Place of Birth', groups="hr.group_hr_user", tracking=True)
    # country_of_birth = fields.Many2one('res.country', string="Country of Birth", groups="hr.group_hr_user", tracking=True)
    # birthday = fields.Date('Birthday', groups="hr.group_hr_user", tracking=True)
    # birthday_public_display = fields.Boolean('Show to all employees', groups="hr.group_hr_user", default=False)
    # birthday_public_display_string = fields.Char("Public Date of Birth", compute="_compute_birthday_public_display_string", default="hidden")
    # ssnid = fields.Char('SSN No', help='Social Security Number', groups="hr.group_hr_user", tracking=True)
    # sinid = fields.Char('SIN No', help='Social Insurance Number', groups="hr.group_hr_user", tracking=True)
    # identification_id = fields.Char(string='Identification No', groups="hr.group_hr_user", tracking=True)
    # passport_id = fields.Char('Passport No', groups="hr.group_hr_user", tracking=True)
    # bank_account_id = fields.Many2one(
    #     'res.partner.bank', 'Bank Account',
    #     domain="[('partner_id', '=', work_contact_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    #     groups="hr.group_hr_user",
    #     tracking=True,
    #     help='Employee bank account to pay salaries')
    # permit_no = fields.Char('Work Permit No', groups="hr.group_hr_user", tracking=True)
    # visa_no = fields.Char('Visa No', groups="hr.group_hr_user", tracking=True)
    # visa_expire = fields.Date('Visa Expiration Date', groups="hr.group_hr_user", tracking=True)
    # work_permit_expiration_date = fields.Date('Work Permit Expiration Date', groups="hr.group_hr_user", tracking=True)
    # has_work_permit = fields.Binary(string="Work Permit", groups="hr.group_hr_user")
    # work_permit_scheduled_activity = fields.Boolean(default=False, groups="hr.group_hr_user")
    # work_permit_name = fields.Char('work_permit_name', compute='_compute_work_permit_name', groups="hr.group_hr_user")
    # additional_note = fields.Text(string='Additional Note', groups="hr.group_hr_user", tracking=True)
    # certificate = fields.Selection([
    #     ('graduate', 'Graduate'),
    #     ('bachelor', 'Bachelor'),
    #     ('master', 'Master'),
    #     ('doctor', 'Doctor'),
    #     ('other', 'Other'),
    # ], 'Certificate Level', groups="hr.group_hr_user", tracking=True)
    # study_field = fields.Char("Field of Study", groups="hr.group_hr_user", tracking=True)
    # study_school = fields.Char("School", groups="hr.group_hr_user", tracking=True)
    # emergency_contact = fields.Char("Contact Name", groups="hr.group_hr_user", tracking=True)
    # emergency_phone = fields.Char("Contact Phone", groups="hr.group_hr_user", tracking=True)
    # distance_home_work = fields.Integer(string="Home-Work Distance", groups="hr.group_hr_user", tracking=True)
    # km_home_work = fields.Integer(string="Home-Work Distance in Km", groups="hr.group_hr_user", compute="_compute_km_home_work", inverse="_inverse_km_home_work", store=True)
    # distance_home_work_unit = fields.Selection([
    #     ('kilometers', 'km'),
    #     ('miles', 'mi'),
    # ], 'Home-Work Distance unit', tracking=True, groups="hr.group_hr_user", default='kilometers', required=True)
    # employee_type = fields.Selection([
    #         ('employee', 'Employee'),
    #         ('worker', 'Worker'),
    #         ('student', 'Student'),
    #         ('trainee', 'Trainee'),
    #         ('contractor', 'Contractor'),
    #         ('freelance', 'Freelancer'),
    #     ], string='Employee Type', default='employee', required=True, groups="hr.group_hr_user",
    #     help="Categorize your Employees by type. This field also has an impact on contracts. Only Employees, Students and Trainee will have contract history.")
    #
    # job_id = fields.Many2one(tracking=True)
    # # employee in company
    # child_ids = fields.One2many('hr.employee', 'parent_id', string='Direct subordinates')
    # category_ids = fields.Many2many(
    #     'hr.employee.category', 'employee_category_rel',
    #     'employee_id', 'category_id', groups="hr.group_hr_user",
    #     string='Tags')
    # # misc
    # notes = fields.Text('Notes', groups="hr.group_hr_user")
    # color = fields.Integer('Color Index', default=0)
    # barcode = fields.Char(string="Badge ID", help="ID used for employee identification.", groups="hr.group_hr_user", copy=False)
    # pin = fields.Char(string="PIN", groups="hr.group_hr_user", copy=False,
    #     help="PIN used to Check In/Out in the Kiosk Mode of the Attendance application (if enabled in Configuration) and to change the cashier in the Point of Sale application.")
    # departure_reason_id = fields.Many2one("hr.departure.reason", string="Departure Reason", groups="hr.group_hr_user",
    #                                       copy=False, tracking=True, ondelete='restrict')
    # departure_description = fields.Html(string="Additional Information", groups="hr.group_hr_user", copy=False)
    # departure_date = fields.Date(string="Departure Date", groups="hr.group_hr_user", copy=False, tracking=True)
    # message_main_attachment_id = fields.Many2one(groups="hr.group_hr_user")
    # id_card = fields.Binary(string="ID Card Copy", groups="hr.group_hr_user")
    # driving_license = fields.Binary(string="Driving License", groups="hr.group_hr_user")
    # private_car_plate = fields.Char(groups="hr.group_hr_user", help="If you have more than one car, just separate the plates by a space.")
    # currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True, groups="hr.group_hr_user")
    # related_partners_count = fields.Integer(compute="_compute_related_partners_count", groups="hr.group_hr_user")

    # @api.model
    # def _get_new_hire_field(self):
    #     return 'create_date'
    #
    # def _compute_newly_hired(self):
    #     new_hire_field = self._get_new_hire_field()
    #     new_hire_date = fields.Datetime.now() - timedelta(days=90)
    #     for employee in self:
    #         if not employee[new_hire_field]:
    #             employee.newly_hired = False
    #         elif not isinstance(employee[new_hire_field], datetime):
    #             employee.newly_hired = employee[new_hire_field] > new_hire_date.date()
    #         else:
    #             employee.newly_hired = employee[new_hire_field] > new_hire_date
    #
    # def _search_newly_hired(self, operator, value):
    #     new_hire_field = self._get_new_hire_field()
    #     new_hires = self.env['hr.employee'].sudo().search([
    #         (new_hire_field, '>', fields.Datetime.now() - timedelta(days=90))
    #     ])
    #
    #     op = 'in' if value and operator == '=' or not value and operator != '=' else 'not in'
    #     return [('id', op, new_hires.ids)]
    #
    # @api.depends("work_location_id.name", "work_location_id.location_type")
    # def _compute_work_location_name_type(self):
    #     for employee in self:
    #         employee.work_location_name = employee.work_location_id.name or None
    #         employee.work_location_type = employee.work_location_id.location_type or 'other'
    #
    # def _get_valid_employee_for_user(self):
    #     user = self.env.user
    #     # retrieve the employee of the current active company for the user
    #     employee = user.employee_id
    #     if not employee:
    #         # search for all employees as superadmin to not get blocked by multi-company rules
    #         user_employees = user.employee_id.sudo().search([
    #             ('user_id', '=', user.id)
    #         ])
    #         # the default company employee is most likely the correct one, but fallback to the first if not available
    #         employee = user_employees.filtered(lambda r: r.company_id == user.company_id) or user_employees[:1]
    #     return employee
    #
    # @api.depends_context('uid', 'company')
    # @api.depends('department_id')
    # def _compute_part_of_department(self):
    #     user_employee = self._get_valid_employee_for_user()
    #     active_department = user_employee.department_id
    #     if not active_department:
    #         self.member_of_department = False
    #     else:
    #         def get_all_children(department):
    #             children = department.child_ids
    #             if not children:
    #                 return self.env['hr.department']
    #             return children + get_all_children(children)
    #
    #         child_departments = active_department + get_all_children(active_department)
    #         for employee in self:
    #             employee.member_of_department = employee.department_id in child_departments
    #
    # def _search_part_of_department(self, operator, value):
    #     if operator not in ('=', '!=') or not isinstance(value, bool):
    #         raise UserError(_('Operation not supported'))
    #
    #     user_employee = self._get_valid_employee_for_user()
    #     # Double negation
    #     if not value:
    #         operator = '!=' if operator == '=' else '='
    #     if not user_employee.department_id:
    #         return [('id', operator, user_employee.id)]
    #     return (['!'] if operator == '!=' else []) + [('department_id', 'child_of', user_employee.department_id.id)]
    #
    # @api.depends('user_id')
    # def _compute_last_activity(self):
    #     for employee in self:
    #         tz = employee.tz
    #         # sudo: res.users - can access presence of accessible user
    #         if last_presence := employee.user_id.sudo().presence_ids.last_presence:
    #             last_activity_datetime = last_presence.replace(tzinfo=UTC).astimezone(timezone(tz)).replace(tzinfo=None)
    #             employee.last_activity = last_activity_datetime.date()
    #             if employee.last_activity == fields.Date.today():
    #                 employee.last_activity_time = format_time(self.env, last_presence, time_format='short')
    #             else:
    #                 employee.last_activity_time = False
    #         else:
    #             employee.last_activity = False
    #             employee.last_activity_time = False
    #
    # @api.depends('parent_id')
    # def _compute_coach(self):
    #     for employee in self:
    #         manager = employee.parent_id
    #         previous_manager = employee._origin.parent_id
    #         if manager and (employee.coach_id == previous_manager or not employee.coach_id):
    #             employee.coach_id = manager
    #         elif not employee.coach_id:
    #             employee.coach_id = False
    #
    # @api.depends('job_id.name')
    # def _compute_job_title(self):
    #     for employee in self.filtered('job_id'):
    #         employee.job_title = employee.job_id.name
    #
    # @api.depends('address_id')
    # def _compute_phones(self):
    #     for employee in self:
    #         if employee.address_id and employee.address_id.phone:
    #             employee.work_phone = employee.address_id.phone
    #         else:
    #             employee.work_phone = False
    #
    # @api.depends('work_contact_id', 'work_contact_id.phone', 'work_contact_id.email')
    # def _compute_work_contact_details(self):
    #     for employee in self:
    #         if employee.work_contact_id:
    #             employee.mobile_phone = employee.work_contact_id.phone
    #             employee.work_email = employee.work_contact_id.email
    #
    # def _create_work_contacts(self):
    #     if any(employee.work_contact_id for employee in self):
    #         raise UserError(_('Some employee already have a work contact'))
    #     work_contacts = self.env['res.partner'].create([{
    #         'email': employee.work_email,
    #         'phone': employee.mobile_phone,
    #         'name': employee.name,
    #         'image_1920': employee.image_1920,
    #         'company_id': employee.company_id.id
    #     } for employee in self])
    #     for employee, work_contact in zip(self, work_contacts):
    #         employee.work_contact_id = work_contact
    #
    # def _inverse_work_contact_details(self):
    #     employees_without_work_contact = self.env['hr.employee']
    #     for employee in self:
    #         if not employee.work_contact_id:
    #             employees_without_work_contact += employee
    #         else:
    #             employee.work_contact_id.sudo().write({
    #                 'email': employee.work_email,
    #                 'phone': employee.mobile_phone,
    #             })
    #     if employees_without_work_contact:
    #         employees_without_work_contact.sudo()._create_work_contacts()
    #
    # @api.depends('company_id')
    # def _compute_address_id(self):
    #     for employee in self:
    #         address = employee.company_id.partner_id.address_get(['default'])
    #         employee.address_id = address['default'] if address else False
    #
    # @api.depends('department_id')
    # def _compute_parent_id(self):
    #     for employee in self.filtered('department_id.manager_id'):
    #         employee.parent_id = employee.department_id.manager_id
    #
    # @api.depends('resource_calendar_id', 'hr_presence_state')
    # def _compute_presence_icon(self):
    #     """
    #     This method compute the state defining the display icon in the kanban view.
    #     It can be overriden to add other possibilities, like time off or attendances recordings.
    #     """
    #     for employee in self:
    #         employee.hr_icon_display = 'presence_' + employee.hr_presence_state
    #         employee.show_hr_icon_display = bool(employee.user_id)
    #
    # @api.depends('resource_calendar_id')
    # def _compute_is_flexible(self):
    #     for employee in self:
    #         employee.is_fully_flexible = not employee.resource_calendar_id
    #         employee.is_flexible = employee.is_fully_flexible or employee.resource_calendar_id.flexible_hours
