# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models, modules
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class HrContract(models.Model):
    _name = 'hr.contract'
    _description = 'Contract'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # TODO: remove later
    _mail_post_access = 'read'
    _order = 'date_version'
    _rec_name = 'employee_id'

    company_id = fields.Many2one(related='employee_id.company_id')
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        index=True)
    display_name = fields.Char(compute='_compute_display_name')

    date_version = fields.Date(required=True, default=fields.Date.today)
    last_modified_uid = fields.Many2one('res.users', string='Last Modified by', default=lambda self: self.env.uid, required=True)
    last_modified_date = fields.Datetime(string='Last Modified on', default=fields.Datetime.now, required=True)

    # Personal Information
    country_id = fields.Many2one(
        'res.country', 'Nationality (Country)', groups="hr.group_hr_user", tracking=True)
    identification_id = fields.Char(string='Identification No', groups="hr.group_hr_user", tracking=True)
    ssnid = fields.Char('SSN No', help='Social Security Number', groups="hr.group_hr_user", tracking=True)
    passport_id = fields.Char('Passport No', groups="hr.group_hr_user", tracking=True)

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
    department_id = fields.Many2one('hr.department', check_company=True, tracking=True, groups="hr.group_hr_user")
    member_of_department = fields.Boolean("Member of department", compute='_compute_part_of_department', search='_search_part_of_department',
        help="Whether the employee is a member of the active user's department or one of it's child department.")
    job_id = fields.Many2one('hr.job', check_company=True, tracking=True, groups="hr.group_hr_user")
    job_title = fields.Char(related='job_id.name', readonly=False, string="Job Title")
    parent_id = fields.Many2one('hr.employee', 'Manager', compute="_compute_parent_id",
                                store=True, readonly=False,
                                domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]")
    coach_id = fields.Many2one(
        'hr.employee', 'Coach', compute='_compute_coach', store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]",
        help='Select the "Employee" who is the coach of this employee.\n'
             'The "Coach" has no specific rights or responsibilities by default.')

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
                                          groups="hr.group_hr_user", copy=False, ondelete='restrict', tracking=True)
    departure_description = fields.Html(string="Additional Information", groups="hr.group_hr_user", copy=False)
    departure_date = fields.Date(string="Departure Date", groups="hr.group_hr_user", copy=False, tracking=True)

    resource_calendar_id = fields.Many2one('resource.calendar', check_company=True, string="Working Hours")
    is_flexible = fields.Boolean(compute='_compute_is_flexible', store=True)
    is_fully_flexible = fields.Boolean(compute='_compute_is_flexible', store=True)
    tz = fields.Selection(
        _tz_get, string='Timezone', required=True,
        default=lambda self: self._context.get('tz') or self.env.user.tz or self.env.ref('base.user_admin').tz or 'UTC',
        help="This field is used in order to define in which timezone the employee will work.")

    # Contract Information
    contract_date_start = fields.Date('Contract Start Date', tracking=True)
    contract_date_end = fields.Date(
        'Contract End Date', tracking=True, help="End date of the contract (if it's a fixed-term contract).")
    trial_date_end = fields.Date('End of Trial Period', help="End date of the trial period (if there is one).")
    date_start = fields.Date(compute='_compute_dates')
    date_end = fields.Date(compute='_compute_dates')

    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type", compute="_compute_structure_type_id", readonly=False, store=True, tracking=True)
    active_employee = fields.Boolean(related="employee_id.active", string="Active Employee")
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    wage = fields.Monetary('Wage', tracking=True, help="Employee's monthly gross wage.", aggregator="avg")
    contract_wage = fields.Monetary('Contract Wage', compute='_compute_contract_wage')
    notes = fields.Html('Notes')
    company_country_id = fields.Many2one('res.country', string="Company country", related='company_id.country_id', readonly=True)
    country_code = fields.Char(related='company_country_id.code', depends=['company_country_id'], readonly=True)
    contract_type_id = fields.Many2one('hr.contract.type', "Contract Type", tracking=True)

    def _get_hr_responsible_domain(self):
        return "[('share', '=', False), ('company_ids', 'in', company_id), ('all_group_ids', 'in', %s)]" % self.env.ref('hr.group_hr_user').id

    hr_responsible_id = fields.Many2one('res.users', 'HR Responsible', tracking=True,
        help='Person responsible for validating the employee\'s contracts.', domain=_get_hr_responsible_domain)

    @api.constrains('contract_date_start', 'contract_date_end')
    def _check_dates(self):
        for contract in self:
            if contract.contract_date_end and not contract.contract_date_start:
                raise ValidationError(_('The contract must have a start date.'))
            elif contract.contract_date_end and contract.contract_date_start > contract.contract_date_end:
                raise ValidationError(_(
                    'Start date (%(start)s) must be earlier than contract end date (%(end)s).',
                    start=contract.contract_date_start, end=contract.contract_date_end,
                ))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_last_version(self):
        if self.employee_id.versions_count == len(self):
            raise ValidationError(_('An employee must always have at least one version.'))

    @api.depends('date_version')
    def _compute_display_name(self):
        for version in self:
            version.display_name = date.strftime(version.date_version, '%-d %b %Y')

    @api.depends('resource_calendar_id.flexible_hours')
    def _compute_is_flexible(self):
        for employee in self:
            employee.is_fully_flexible = not employee.resource_calendar_id
            employee.is_flexible = employee.is_fully_flexible or employee.resource_calendar_id.flexible_hours

    @api.depends('wage')
    def _compute_contract_wage(self):
        for contract in self:
            contract.contract_wage = contract._get_contract_wage()

    def _get_contract_wage(self):
        if not self:
            return 0
        self.ensure_one()
        return self[self._get_contract_wage_field()]

    def _get_contract_wage_field(self):
        self.ensure_one()
        return 'wage'

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
            for employee in self:
                employee.member_of_department = employee.department_id in child_departments

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

        for contract in self:
            if not contract.structure_type_id or (contract.structure_type_id.country_id and contract.structure_type_id.country_id != contract.company_id.country_id):
                contract.structure_type_id = _default_salary_structure(contract.company_id.country_id.id)

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

    def _compute_dates(self):
        for version in self:
            version.date_start = max(version.date_version, version.contract_date_start) \
                if version.contract_date_start \
                else version.date_version

            next_version = self.env['hr.contract'].search([
                ('employee_id', '=', version.employee_id.id),
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

    @api.depends('department_id')
    def _compute_parent_id(self):
        for version in self.filtered('department_id.manager_id'):
            version.parent_id = version.department_id.manager_id

    @api.depends('parent_id')
    def _compute_coach(self):
        for employee in self:
            manager = employee.parent_id
            previous_manager = employee._origin.parent_id
            if manager and (employee.coach_id == previous_manager or not employee.coach_id):
                employee.coach_id = manager
            elif not employee.coach_id:
                employee.coach_id = False

    @api.depends('employee_id.company_id')
    def _compute_address_id(self):
        for version in self:
            address = version.employee_id.company_id.partner_id.address_get(['default'])
            version.address_id = address['default'] if address else False

    def _get_salary_costs_factor(self):
        self.ensure_one()
        return 12.0

    def _is_struct_from_country(self, country_code):
        self.ensure_one()
        self_sudo = self.sudo()
        return self_sudo.structure_type_id and self_sudo.structure_type_id.country_id.code == country_code
