# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta
from babel.dates import format_date, get_date_format

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.exceptions import ValidationError
from odoo.tools import get_lang, babel_locale_parse

import logging
_logger = logging.getLogger(__name__)


def format_date_abbr(env, date):
    lang = get_lang(env)
    locale = babel_locale_parse(lang.code)
    date_format = get_date_format('medium', locale=locale).pattern
    return format_date(date, date_format, locale=locale)


class HrVersion(models.Model):
    _name = 'hr.version'
    _description = 'Version'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # TODO: remove later ? (see if still needed because contract template)
    _mail_post_access = 'read'
    _order = 'date_version'
    _rec_name = 'employee_id'

    def _get_default_address_id(self):
        address = self.env.user.company_id.partner_id.address_get(['default'])
        return address['default'] if address else False

    def _default_salary_structure(self):
        return (
                self.env['hr.payroll.structure.type'].sudo().search([('country_id', '=', self.env.company.country_id.id)], limit=1)
                or self.env['hr.payroll.structure.type'].sudo().search([('country_id', '=', False)], limit=1)
        )

    company_id = fields.Many2one('res.company', compute='_compute_company_id', readonly=False,
                                 store=True, default=lambda self: self.env.company)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        index=True)
    name = fields.Char()
    display_name = fields.Char(compute='_compute_display_name')
    active = fields.Boolean(default=True)

    date_version = fields.Date(required=True, default=fields.Date.today, tracking=True, groups="hr.group_hr_user")
    last_modified_uid = fields.Many2one('res.users', string='Last Modified by',
                                        default=lambda self: self.env.uid, required=True, groups="hr.group_hr_user")
    last_modified_date = fields.Datetime(string='Last Modified on', default=fields.Datetime.now, required=True,
                                         groups="hr.group_hr_user")

    # Personal Information
    country_id = fields.Many2one(
        'res.country', 'Nationality (Country)', groups="hr.group_hr_user", tracking=True)
    identification_id = fields.Char(string='Identification No', groups="hr.group_hr_user", tracking=True)
    ssnid = fields.Char('SSN No', help='Social Security Number', groups="hr.group_hr_user", tracking=True)
    passport_id = fields.Char('Passport No', groups="hr.group_hr_user", tracking=True)
    sex = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ], groups="hr.group_hr_user", tracking=True, help="This is the legal sex recognized by the state.", string='Gender')

    private_street = fields.Char(string="Private Street", groups="hr.group_hr_user", tracking=True)
    private_street2 = fields.Char(string="Private Street2", groups="hr.group_hr_user", tracking=True)
    private_city = fields.Char(string="Private City", groups="hr.group_hr_user", tracking=True)
    private_state_id = fields.Many2one(
        "res.country.state", string="Private State",
        domain="[('country_id', '=?', private_country_id)]",
        groups="hr.group_hr_user", tracking=True)
    private_zip = fields.Char(string="Private Zip", groups="hr.group_hr_user", tracking=True)
    private_country_id = fields.Many2one("res.country", string="Private Country",
                                         groups="hr.group_hr_user", tracking=True)

    distance_home_work = fields.Integer(string="Home-Work Distance", groups="hr.group_hr_user", tracking=True)
    km_home_work = fields.Integer(string="Home-Work Distance in Km", groups="hr.group_hr_user",
                                  compute="_compute_km_home_work", inverse="_inverse_km_home_work", store=True)
    distance_home_work_unit = fields.Selection([
        ('kilometers', 'km'),
        ('miles', 'mi'),
    ], 'Home-Work Distance unit', groups="hr.group_hr_user", default='kilometers', required=True, tracking=True)

    marital = fields.Selection(
        selection='_get_marital_status_selection',
        string='Marital Status',
        groups="hr.group_hr_user",
        default='single',
        required=True,
        tracking=True)
    spouse_complete_name = fields.Char(string="Spouse Legal Name", groups="hr.group_hr_user", tracking=True)
    spouse_birthdate = fields.Date(string="Spouse Birthdate", groups="hr.group_hr_user", tracking=True)
    children = fields.Integer(string='Dependent Children', groups="hr.group_hr_user", tracking=True)

    # Work Information
    employee_type = fields.Selection([
            ('employee', 'Employee'),
            ('worker', 'Worker'),
            ('student', 'Student'),
            ('trainee', 'Trainee'),
            ('contractor', 'Contractor'),
            ('freelance', 'Freelancer'),
        ], string='Employee Type', default='employee', required=True, groups="hr.group_hr_user", tracking=True)
    department_id = fields.Many2one('hr.department', check_company=True, tracking=True)
    member_of_department = fields.Boolean("Member of department", compute='_compute_part_of_department', search='_search_part_of_department',
        help="Whether the employee is a member of the active user's department or one of it's child department.")
    job_id = fields.Many2one('hr.job', check_company=True, tracking=True)
    job_title = fields.Char(compute="_compute_job_title", inverse="_inverse_job_title", store=True, readonly=False,
        string="Job Title", tracking=True)
    is_custom_job_title = fields.Boolean(default=False, groups="hr.group_hr_user")
    address_id = fields.Many2one(
        'res.partner',
        string='Work Address',
        default=_get_default_address_id,
        store=True,
        readonly=False,
        check_company=True,
        tracking=True)
    work_location_id = fields.Many2one('hr.work.location', 'Work Location',
                                       domain="[('address_id', '=', address_id)]", tracking=True)
    work_location_name = fields.Char("Work Location Name", compute="_compute_work_location_name_type")
    work_location_type = fields.Selection([
        ("home", "Home"),
        ("office", "Office"),
        ("other", "Other")], compute="_compute_work_location_name_type", tracking=True)

    departure_reason_id = fields.Many2one("hr.departure.reason", string="Departure Reason",
                                          groups="hr.group_hr_user", copy=False, ondelete='restrict', tracking=True)
    departure_description = fields.Html(string="Additional Information", groups="hr.group_hr_user", copy=False)
    departure_date = fields.Date(string="Departure Date", groups="hr.group_hr_user", copy=False, tracking=True)

    resource_calendar_id = fields.Many2one('resource.calendar', inverse='_inverse_resource_calendar_id', check_company=True, string="Working Hours", tracking=True)
    is_flexible = fields.Boolean(compute='_compute_is_flexible', store=True, groups="hr.group_hr_user")
    is_fully_flexible = fields.Boolean(compute='_compute_is_flexible', store=True, groups="hr.group_hr_user")
    tz = fields.Selection(related='employee_id.tz')

    # Contract Information
    contract_date_start = fields.Date('Contract Start Date', tracking=True, groups="hr.group_hr_manager")
    contract_date_end = fields.Date(
        'Contract End Date', tracking=True, help="End date of the contract (if it's a fixed-term contract).",
        groups="hr.group_hr_manager")
    trial_date_end = fields.Date('End of Trial Period', help="End date of the trial period (if there is one).",
                                 groups="hr.group_hr_manager")
    date_start = fields.Date(compute='_compute_dates', groups="hr.group_hr_manager")
    date_end = fields.Date(compute='_compute_dates', groups="hr.group_hr_manager")
    is_current = fields.Boolean(compute='_compute_is_current', groups="hr.group_hr_manager")
    is_past = fields.Boolean(compute='_compute_is_past', groups="hr.group_hr_manager")
    is_future = fields.Boolean(compute='_compute_is_future', groups="hr.group_hr_manager")
    is_in_contract = fields.Boolean(compute='_compute_is_in_contract', groups="hr.group_hr_manager")

    contract_template_id = fields.Many2one(
        'hr.version', string="Contract Template", groups="hr.group_hr_user",
        domain="[('company_id', '=', company_id), ('employee_id', '=', False)]", tracking=True,
        help="Select a contract template to auto-fill the contract form with predefined values. You can still edit the fields as needed after applying the template.")
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type",
                                        compute="_compute_structure_type_id", readonly=False, store=True, tracking=True,
                                        groups="hr.group_hr_user", default=_default_salary_structure)
    active_employee = fields.Boolean(related="employee_id.active", string="Active Employee", groups="hr.group_hr_user")
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    wage = fields.Monetary('Wage', tracking=True, help="Employee's monthly gross wage.", aggregator="avg",
                           groups="hr.group_hr_manager")
    contract_wage = fields.Monetary('Contract Wage', compute='_compute_contract_wage', groups="hr.group_hr_manager")
    # [XBO] TODO: remove me in master
    company_country_id = fields.Many2one('res.country', string="Company country",
                                         related='company_id.country_id', readonly=True)
    country_code = fields.Char(related='company_country_id.code', depends=['company_country_id'], readonly=True)
    contract_type_id = fields.Many2one('hr.contract.type', "Contract Type", tracking=True,
                                       groups="hr.group_hr_user")

    def _get_hr_responsible_domain(self):
        return "[('share', '=', False), ('company_ids', 'in', company_id), ('all_group_ids', 'in', %s)]" % self.env.ref('hr.group_hr_user').id

    hr_responsible_id = fields.Many2one(
        'res.users', 'HR Responsible', tracking=True,
        help='Person responsible for validating the employee\'s contracts.', domain=_get_hr_responsible_domain,
        default=lambda self: self.env.user, required=True, groups="hr.group_hr_user")

    _check_contract_start_date_defined = models.Constraint(
        'CHECK(contract_date_end IS NULL OR contract_date_start IS NOT NULL)',
        'The contract must have a start date.',
    )

    _check_unique_date_version = models.UniqueIndex(
        '(employee_id, date_version) WHERE active = TRUE AND employee_id IS NOT NULL',
        'An employee cannot have multiple active versions sharing the same effective date.',
    )

    @api.depends('employee_id.company_id')
    def _compute_company_id(self):
        for version in self:
            if version.employee_id:
                version.company_id = version.employee_id.company_id

    @api.depends('job_id.name')
    def _compute_job_title(self):
        for version in self.filtered('job_id'):
            if version._origin.job_id != version.job_id or not version.is_custom_job_title:
                version.job_title = version.job_id.name

    def _inverse_job_title(self):
        for version in self:
            version.is_custom_job_title = version.job_title != version.job_id.name

    @api.constrains('employee_id', 'contract_date_start', 'contract_date_end')
    def _check_dates(self):
        version_read_group = self.env['hr.version'].sudo()._read_group(
            [
                ('id', 'not in', self.ids),
                ('employee_id', 'in', self.employee_id.ids),
                ('contract_date_start', '!=', False),
            ],
            ['employee_id', 'contract_date_start:day', 'contract_date_end:day'],
            ['id:recordset'],
        )
        dates_per_employee = defaultdict(list)
        for employee, date_start, date_end, versions in version_read_group:
            dates_per_employee[employee].append((date_start, date_end, versions))
        for version in self.sudo():  # sudo needed to read contract dates
            if not version.contract_date_start or not version.employee_id:
                continue
            if version.contract_date_end and version.contract_date_start > version.contract_date_end:
                raise ValidationError(_(
                    'Start date (%(start)s) must be earlier than contract end date (%(end)s).',
                    start=version.contract_date_start, end=version.contract_date_end,
                ))
            if not version.active:
                continue
            contract_date_end = version.contract_date_end or date.max
            contract_period_exists = False
            for date_start, date_end, versions in dates_per_employee[version.employee_id]:
                date_to = date_end or date.max
                if date_start == version.contract_date_start and date_to == contract_date_end:
                    contract_period_exists = True
                    continue
                if date_start <= contract_date_end and version.contract_date_start <= date_to:
                    raise ValidationError(_(
                        'You have some overlapping contracts for %(employee)s:\n%(overlaps)s',
                        employee=version.employee_id.display_name,
                        overlaps='\n'.join(
                            [self.env._('Version') + f' ({format_date_abbr(v.env, v.date_version)}): '
                             f'{format_date_abbr(v.env, v.contract_date_start)} '
                             f'- {format_date_abbr(v.env, v.contract_date_end) if v.contract_date_end else self.env._("Indefinite")}'
                             for v in (versions | version)])))
            if not contract_period_exists:
                dates_per_employee[version.employee_id].append((version.contract_date_start, version.contract_date_end, version))

    @api.model_create_multi
    def create(self, vals_list):
        Version = self.env['hr.version']
        for vals in vals_list:
            if 'contract_template_id' in vals:
                contract_vals = Version.get_values_from_contract_template(Version.browse(vals['contract_template_id']))
                # take vals from template, but priority given to the original vals
                vals.update({**contract_vals, **vals})
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_last_version(self):
        for employee_id, versions in self.grouped('employee_id').items():
            if employee_id.versions_count == len(versions):
                raise ValidationError(
                    self.env._('Employee %s must always have at least one active version.') % employee_id.name
                )

    def write(self, values):
        # Employee Versions Validation
        # ARPI TODO: what if mass edit ?
        if 'employee_id' in values:
            if self.filtered(lambda v: len(v.employee_id.version_ids) == 1 and values['employee_id'] != v.employee_id.id):
                raise ValidationError(self.env._("Cannot unassign the only active version of an employee."))
        if 'active' in values and not values['active']:
            if self.filtered(lambda v: len(v.employee_id.version_ids) == 1):
                raise ValidationError(self.env._("Cannot archive the only active version of an employee."))

        if self.env.context.get('sync_contract_dates'):
            return super().write(values)

        new_vals = {
            f_name: f_value
            for f_name, f_value in values.items()
            if (f_name != 'contract_date_start' or not f_value) and f_name != 'contract_date_end'
        }
        dates_vals = {}
        if 'contract_date_start' in values:
            dates_vals['contract_date_start'] = values['contract_date_start']
        if 'contract_date_end' in values:
            dates_vals['contract_date_end'] = values['contract_date_end']
        if dates_vals:
            new_contract_date_start = dates_vals.get('contract_date_start')
            if new_contract_date_start:
                new_contract_date_start = fields.Date.to_date(new_contract_date_start)
            min_contract_date_start = new_contract_date_start or date.max
            max_date_end = date.min
            for version in self:
                if version.contract_date_start and min_contract_date_start > version.contract_date_start:
                    min_contract_date_start = version.contract_date_start
                if max_date_end is False:
                    continue
                if not version.contract_date_end:
                    max_date_end = False
                max_date_end = max(max_date_end, version.contract_date_end)
            version_domain = [
                ('contract_date_start', '>=', min_contract_date_start),
                ('id', 'not in', self.ids),
            ]
            date_end_domain = [('contract_date_end', '=', False)]
            if max_date_end:
                date_end_domain = Domain.OR([date_end_domain, [('contract_date_end', '<=', max_date_end)]])
            version_domain = Domain.AND([version_domain, date_end_domain])
            versions_to_sync_per_employee = dict(self.env['hr.version']._read_group(version_domain, ['employee_id'], ['id:recordset']))
            if not versions_to_sync_per_employee:
                return super().write(values)
            for version in self:
                versions_to_sync = versions_to_sync_per_employee.get(version.employee_id)
                if versions_to_sync:
                    sync_versions = versions_to_sync.filtered(
                        lambda v:
                            v.contract_date_start == version.contract_date_start
                            or (
                                new_contract_date_start
                                and new_contract_date_start == v.contract_date_start
                            )
                    )
                    if new_contract_date_start and 'contract_date_end' not in dates_vals:
                        dates_vals['contract_date_end'] = version.contract_date_end
                    (sync_versions + version).with_context(sync_contract_dates=True).write(dates_vals)
                else:
                    version.with_context(sync_contract_dates=True).write(dates_vals)
        return super().write(new_vals)

    @api.depends_context('lang')
    @api.depends('date_version')
    def _compute_display_name(self):
        for version in self:
            version.display_name = version.name if not version.employee_id else format_date_abbr(version.env, version.date_version)

    def _compute_is_current(self):
        today = fields.Date.today()
        for version in self:
            version.is_current = version.date_start <= today and (not version.date_end or version.date_end >= today)

    def _compute_is_past(self):
        today = fields.Date.today()
        for version in self:
            version.is_past = version.date_end and version.date_end < today

    def _compute_is_future(self):
        today = fields.Date.today()
        for version in self:
            version.is_future = version.date_start > today

    def _compute_is_in_contract(self):
        for version in self:
            version.is_in_contract = version._is_in_contract()

    def _is_in_contract(self, date=fields.Date.today()):
        # Return True if the employee is in contract on a given date
        if not self.contract_date_start:
            return False
        return self.date_start <= date and (not self.date_end or self.date_end >= date)

    def _is_overlapping_period(self, date_from, date_to):
        """
        Return True if the employee is at least in contract one day during the period given
        :param date date_from: the start of the period
        :param date date_to: the stop of the period
        """
        if not self.contract_date_start:
            return False
        return self.date_start <= date_to and (not self.date_end or self.date_end >= date_from)

    def _is_fully_flexible(self):
        """ return True if the version has a fully flexible working calendar """
        self.ensure_one()
        return not self.resource_calendar_id

    @api.depends('resource_calendar_id.flexible_hours')
    def _compute_is_flexible(self):
        for version in self:
            version.is_fully_flexible = version._is_fully_flexible()
            version.is_flexible = version.is_fully_flexible or version.resource_calendar_id.flexible_hours

    @api.model
    def _get_whitelist_fields_from_template(self):
        # Add here any field that you want to copy from a contract template
        # Those fields should have tracking=True in hr.version to see the change
        return ['job_id', 'department_id', 'contract_type_id', 'structure_type_id', 'wage', 'resource_calendar_id']

    def get_values_from_contract_template(self, contract_template_id):
        if not contract_template_id:
            return {}
        whitelist = self._get_whitelist_fields_from_template()
        contract_template_vals = contract_template_id.copy_data()[0]
        return {
            field: value
                for field, value in contract_template_vals.items()
                if field in whitelist and not self.env['hr.version']._fields[field].related
        }

    @api.depends('wage')
    def _compute_contract_wage(self):
        for version in self:
            version.contract_wage = version._get_contract_wage()

    def _get_contract_wage(self):
        if not self:
            return 0
        self.ensure_one()
        return self[self._get_contract_wage_field()]

    def _get_contract_wage_field(self):
        self.ensure_one()
        return 'wage'

    def _get_normalized_wage(self):
        """ This method is overridden in hr_payroll, as without that module, nothing allows to know
        there's no way to determine the employee's pay frequency.
        """
        wage = self._get_contract_wage()
        # without payroll installed, we suppose that the employee with a specific schedule has a monthly salary
        if self.resource_calendar_id:
            if not self.resource_calendar_id.hours_per_week:
                return 0
            return wage * 12 / 52 / self.resource_calendar_id.hours_per_week
        # without any calendar, the employee has a fully flexible schedule and is supposedly working on an hourly wage
        return wage

    def _get_valid_employee_for_user(self):
        user = self.env.user
        # retrieve the employee of the current active company for the user
        employee = user.employee_id
        if not employee:
            # search for all employees as superadmin to not get blocked by multi-company rules
            user_employees = user.employee_id.sudo().search([
                ('user_id', '=', user.id)
            ])
            # the default company employee is most likely the correct one, but fallback to the first if not available
            employee = user_employees.filtered(lambda r: r.company_id == user.company_id) or user_employees[:1]
        return employee

    @api.constrains('ssnid')
    def _check_ssnid(self):
        # By default, a Social Security Number is always valid, but each localization
        # may want to add its own constraints
        pass

    @api.depends_context('uid', 'company')
    @api.depends('department_id')
    def _compute_part_of_department(self):
        user_employee = self._get_valid_employee_for_user()
        active_department = user_employee.department_id
        if not active_department:
            self.member_of_department = False
        else:
            def get_all_children(department):
                children = department.child_ids
                if not children:
                    return self.env['hr.department']
                return children + get_all_children(children)

            child_departments = active_department + get_all_children(active_department)
            for version in self:
                version.member_of_department = version.department_id in child_departments

    def _search_part_of_department(self, operator, value):
        if operator != 'in':
            return NotImplemented

        user_employee = self._get_valid_employee_for_user()
        if not user_employee.department_id:
            return [('id', 'in', user_employee.ids)]
        return [('department_id', 'child_of', user_employee.department_id.ids)]

    @api.depends('company_id')
    def _compute_structure_type_id(self):

        default_structure_by_country = {}

        def _default_salary_structure(country_id):
            default_structure = default_structure_by_country.get(country_id)
            if default_structure is None:
                default_structure = default_structure_by_country[country_id] = (
                    self.env['hr.payroll.structure.type'].search([('country_id', '=', country_id)], limit=1)
                    or self.env['hr.payroll.structure.type'].search([('country_id', '=', False)], limit=1)
                )
            return default_structure

        for version in self:
            if not version.structure_type_id or (version.structure_type_id.country_id and version.structure_type_id.country_id != version.company_id.country_id):
                version.structure_type_id = _default_salary_structure(version.company_id.country_id.id)

    @api.depends("work_location_id.name", "work_location_id.location_type")
    def _compute_work_location_name_type(self):
        for version in self:
            version.work_location_name = version.work_location_id.name or None
            version.work_location_type = version.work_location_id.location_type or 'other'

    @api.depends('distance_home_work', 'distance_home_work_unit')
    def _compute_km_home_work(self):
        for version in self:
            version.km_home_work = version.distance_home_work * 1.609 if version.distance_home_work_unit == "miles" else version.distance_home_work

    def _inverse_km_home_work(self):
        for version in self:
            version.distance_home_work = version.km_home_work / 1.609 if version.distance_home_work_unit == "miles" else version.km_home_work

    @api.depends(
        'contract_date_start', 'contract_date_end', 'date_version', 'employee_id',
        'employee_id.version_ids.date_version')
    def _compute_dates(self):
        for version in self:
            version.date_start = max(version.date_version, version.contract_date_start) \
                if version.contract_date_start \
                else version.date_version

            next_version = self.env['hr.version'].search([
                ('employee_id', 'in', version.employee_id.ids),
                ('date_version', '>', version.date_version)], limit=1)
            date_version_end = next_version.date_version + relativedelta(days=-1) if next_version else False

            if date_version_end and version.contract_date_end:
                version.date_end = min(date_version_end, version.contract_date_end)
            elif date_version_end:
                version.date_end = date_version_end
            else:
                version.date_end = version.contract_date_end

    @api.model
    def _get_marital_status_selection(self):
        return [
            ('single', _('Single')),
            ('married', _('Married')),
            ('cohabitant', _('Legal Cohabitant')),
            ('widower', _('Widower')),
            ('divorced', _('Divorced')),
        ]

    def _inverse_resource_calendar_id(self):
        for employee, versions in self.grouped('employee_id').items():
            current_version = employee.current_version_id
            for version in versions:
                if version == current_version and employee.resource_id.calendar_id != version.resource_calendar_id:
                    employee.resource_id.calendar_id = version.resource_calendar_id

    def _get_salary_costs_factor(self):
        self.ensure_one()
        return 12.0

    def _is_struct_from_country(self, country_code):
        self.ensure_one()
        self_sudo = self.sudo()
        return self_sudo.structure_type_id and self_sudo.structure_type_id.country_id.code == country_code
