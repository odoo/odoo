# Part of Odoo. See LICENSE file for full copyright and licensing details.

from random import choice
from datetime import datetime
from string import digits
from datetime import date

from odoo import _, api, fields, models
from odoo.addons.base.models.res_partner import _tz_get

class HrEmployeeVersion(models.Model):
    _name = 'hr.employee.version'
    _description = "Employee Version"
    _order = 'date_version'

    display_name = fields.Char(compute='_compute_display_name')
    date_version = fields.Date(default=date.min, required=True)
    date_from = fields.Date()
    date_to = fields.Date()
    employee_id = fields.Many2one('hr.employee')

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

    @api.depends('date_version', 'employee_id.name')
    def _compute_display_name(self):
        for record in self:
            if record.date_version > date.min:
                record.display_name = datetime.strftime(record.date_version, '%-d %b %Y')
            else:
                record.display_name = record.employee_id.name

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

    @api.depends('employee_id.company_id')
    def _compute_address_id(self):
        for version in self:
            address = version.employee_id.company_id.partner_id.address_get(['default'])
            version.address_id = address['default'] if address else False

    def generate_random_barcode(self):
        for history in self:
            history.barcode = '041' + ''.join(choice(digits) for _ in range(9))
