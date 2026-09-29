# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta
from babel.dates import format_date, get_date_format
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import ValidationError
from odoo.tools import SQL, get_lang, babel_locale_parse

import logging
_logger = logging.getLogger(__name__)


def format_date_abbr(env, date):
    lang = get_lang(env)
    locale = babel_locale_parse(lang.code)
    date_format = get_date_format('medium', locale=locale).pattern
    return format_date(date, date_format, locale=locale)


class HrVersion(models.Model):
    _name = 'hr.version'
    _description = 'Employee Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # TODO: remove later ? (see if still needed because contract template)
    _mail_post_access = 'read'
    _order = 'date_version'
    _rec_name = 'name'

    def _get_default_address_id(self):
        address = self.env.company.partner_id.address_get(['default'])
        return address['default'] if address else False

    def _default_salary_structure(self):
        return (
                self.env['hr.payroll.structure.type'].sudo().search([('country_id', '=', self.env.company.country_id.id)], limit=1)
                or self.env['hr.payroll.structure.type'].sudo().search([('country_id', '=', False)], limit=1)
        )

    def _get_hr_responsible_domain(self):
        return [('share', '=', False), ('company_ids', 'in', self.env.company.ids), ('all_group_ids', 'in', self.env.ref('hr.group_hr_user').id)]

    company_id = fields.Many2one('res.company', compute='_compute_company_id', readonly=False,
                                 store=True, index=True, default=lambda self: self.env.company, tracking=1)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        index=True,
        ondelete='cascade')
    name = fields.Char(tracking=1)
    display_name = fields.Char(compute='_compute_display_name')
    active = fields.Boolean(default=True, tracking=1)

    date_version = fields.Date(string="Effective Date", required=True, default=fields.Date.context_today, tracking=1, groups="hr.group_hr_user")
    last_modified_uid = fields.Many2one('res.users', string='Last Modified by',
                                        default=lambda self: self.env.uid, required=True, groups="hr.group_hr_user")
    last_modified_date = fields.Datetime(string='Last Modified on', default=fields.Datetime.now, required=True,
                                         groups="hr.group_hr_user")

    # Personal Information
    country_id = fields.Many2one(
        'res.country', 'Nationality (Country)', index='btree_not_null', groups="hr.group_hr_user", tracking=1)
    identification_id = fields.Char(
        string='Identification No',
        help="Enter the employee's National Identification Number issued by the government (e.g., Aadhaar, SIN, NIN). This is used for official records and statutory compliance.",
        groups="hr.group_hr_user",
        tracking=1)
    passport_id = fields.Char('Passport No', groups="hr.group_hr_user", tracking=1)
    passport_expiration_date = fields.Date('Passport Expiration Date', groups="hr.group_hr_user", tracking=1)
    sex = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], groups="hr.group_hr_user", tracking=1, help="This is the legal sex as recognized by the state, used for official and statutory purposes.")

    private_street = fields.Char(string="Private Street", groups="hr.group_hr_user", tracking=1)
    private_street2 = fields.Char(string="Private Street2", groups="hr.group_hr_user", tracking=1)
    private_city = fields.Char(string="Private City", groups="hr.group_hr_user", tracking=1)
    allowed_country_state_ids = fields.Many2many("res.country.state", compute='_compute_allowed_country_state_ids', groups="hr.group_hr_user")
    private_state_id = fields.Many2one(
        "res.country.state", string="Private State",
        domain="[('id', 'in', allowed_country_state_ids)]",
        groups="hr.group_hr_user", tracking=1)
    private_zip = fields.Char(string="Private Zip", groups="hr.group_hr_user", tracking=1)
    private_country_id = fields.Many2one("res.country", string="Private Country", index='btree_not_null',
                                         groups="hr.group_hr_user", tracking=1, default=lambda self: self.env.company.country_id)

    distance_home_work = fields.Integer(string="Home-Work Distance", groups="hr.group_hr_user", tracking=1)
    km_home_work = fields.Integer(string="Home-Work Distance in Km", groups="hr.group_hr_user",
                                  compute="_compute_km_home_work", inverse="_inverse_km_home_work", store=True, tracking=1)
    distance_home_work_unit = fields.Selection([
        ('kilometers', 'km'),
        ('miles', 'mi'),
    ], 'Home-Work Distance unit', groups="hr.group_hr_user", default='kilometers', required=True, tracking=1)

    marital = fields.Selection(
        selection='_get_marital_status_selection',
        string='Marital Status',
        groups="hr.group_hr_user",
        default='single',
        required=True,
        tracking=1)
    spouse_complete_name = fields.Char(string="Spouse Legal Name", groups="hr.group_hr_user", tracking=1)
    spouse_birthdate = fields.Date(string="Spouse Birthdate", groups="hr.group_hr_user", tracking=1)
    children = fields.Integer(string='Dependent Children', groups="hr.group_hr_user", tracking=1)

    # Work Information
    department_id = fields.Many2one('hr.department', check_company=True, tracking=1, index=True)
    member_of_department = fields.Boolean("Member of department", compute='_compute_part_of_department', search='_search_part_of_department',
        help="Whether the employee is a member of the active user's department or one of it's child department.")
    job_id = fields.Many2one('hr.job', check_company=True, tracking=1, index=True)
    parent_id = fields.Many2one(
        'hr.employee', 'Manager', tracking=1, index='btree_not_null',
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]")
    coach_id = fields.Many2one(
        'hr.employee', 'Coach', compute='_compute_coach', store=True, readonly=False, index='btree_not_null',
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]",
        help='Select the "Employee" who is the coach of this employee.\n'
             'The "Coach" has no specific rights or responsibilities by default.')
    job_title = fields.Char(compute="_compute_job_title", inverse="_inverse_job_title", store=True, readonly=False,
        string="Job Title", tracking=True)
    is_custom_job_title = fields.Boolean(compute='_compute_is_custom_job_title', store=True, default=False, groups="hr.group_hr_user")
    address_id = fields.Many2one(
        'res.partner',
        string='Work Address',
        default=_get_default_address_id,
        store=True,
        index='btree_not_null',
        readonly=False,
        check_company=True,
        tracking=1)
    work_location_id = fields.Many2one('hr.work.location', 'Work Location', compute='_compute_work_location_id',
                                       store=True, readonly=False,
                                       domain="[('address_id', '=', address_id), ('location_type', '=', 'office')]", index=True, tracking=1)

    departure_id = fields.Many2one('hr.employee.departure', string="Departure", copy=False, index='btree_not_null')
    departure_reason_id = fields.Many2one(related='departure_id.departure_reason_id', readonly=False, groups="hr.group_hr_user", tracking=1)
    departure_description = fields.Html(related='departure_id.departure_description', readonly=False, groups="hr.group_hr_user")
    dismissal_date = fields.Date(related='departure_id.dismissal_date', readonly=False, groups="hr.group_hr_user", tracking=1)
    departure_date = fields.Date(related='departure_id.departure_date', readonly=False, groups="hr.group_hr_user", tracking=1)
    departure_action_date = fields.Date(related='departure_id.action_date', readonly=False, groups="hr.group_hr_user")
    departure_apply_immediately = fields.Boolean(related='departure_id.apply_immediately', groups="hr.group_hr_user")
    departure_apply_date = fields.Date(related='departure_id.apply_date', groups="hr.group_hr_user")

    resource_calendar_id = fields.Many2one(
        'resource.calendar', required=True, default=lambda self: self.env.company.resource_calendar_id, inverse='_inverse_resource_calendar_id', string="Working Hours", index='btree_not_null', tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id.id', 'parent_of', company_id)]")
    tz = fields.Selection(_tz_get, string='Timezone', required=True, default=lambda self: self.env.context.get('tz') or self.env.user.tz or 'UTC')

    # Contract Information
    contract_date_start = fields.Date('Contract Start Date', tracking=1, groups="hr.group_hr_user")
    contract_date_end = fields.Date(
        'Contract End Date', tracking=1, help="End date of the contract (if it's a fixed-term contract).",
        groups="hr.group_hr_user")
    fixed_term = fields.Boolean('Fixed Term', tracking=1, groups='hr.group_hr_user')
    trial_date_end = fields.Date('End of Trial Period', help="End date of the trial period (if there is one).",
                                 groups="hr.group_hr_user", tracking=1)
    date_start = fields.Date(compute='_compute_dates', groups="hr.group_hr_user", search="_search_start_date")
    date_end = fields.Date(compute='_compute_dates', groups="hr.group_hr_user", search="_search_end_date")
    is_current = fields.Boolean(compute='_compute_is_current', groups="hr.group_hr_user")
    is_past = fields.Boolean(compute='_compute_is_past', groups="hr.group_hr_user")
    is_future = fields.Boolean(compute='_compute_is_future', groups="hr.group_hr_user")
    is_in_contract = fields.Boolean(compute='_compute_is_in_contract', groups="hr.group_hr_user")

    contract_template_id = fields.Many2one(
        'hr.version', string="Contract Template", groups="hr.group_hr_user",
        domain="[('company_id', '=', company_id), ('employee_id', '=', False)]", tracking=1,
        help="Select a contract template to auto-fill the contract form with predefined values. You can still edit the fields as needed after applying the template.")
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type",
                                        compute="_compute_structure_type_id", readonly=False, store=True, index='btree_not_null', tracking=1,
                                        groups="hr.group_hr_manager", default=_default_salary_structure)
    active_employee = fields.Boolean(related="employee_id.active", string="Active Employee", groups="hr.group_hr_user")
    currency_id = fields.Many2one(string="Currency", related='company_id.currency_id', readonly=True)
    wage = fields.Monetary('Wage', tracking=1, help="Employee's monthly gross wage.", aggregator="avg",
                           groups="hr.group_hr_manager")
    # [XBO] TODO: remove me in master
    company_country_id = fields.Many2one('res.country', string="Company country",
                                         related='company_id.country_id', readonly=True)
    country_code = fields.Char(related='company_country_id.code', depends=['company_country_id'], readonly=True)
    employee_type_id = fields.Many2one('hr.employee.type', "Employee Type", tracking=1, index=True,
                                       groups="hr.group_hr_manager")

    hr_responsible_id = fields.Many2one(
        'res.users', 'HR Responsible', tracking=1,
        help='Person responsible for validating the employee\'s contracts.', domain=lambda self: self._get_hr_responsible_domain(),
        default=lambda self: self.env.user, required=True, groups="hr.group_hr_user")

    _check_contract_start_date_defined = models.Constraint(
        'CHECK(contract_date_end IS NULL OR contract_date_start IS NOT NULL)',
        'The contract must have a start date.',
    )

    _check_unique_date_version = models.UniqueIndex(
        '(employee_id, date_version) WHERE active = TRUE AND employee_id IS NOT NULL',
        'An employee cannot have multiple active versions sharing the same effective date.',
    )

    _check_wage_positive = models.Constraint(
        'CHECK(wage >= 0)',
        'The wage must be a positive value.',
    )

    @api.depends('employee_id.company_id')
    def _compute_company_id(self):
        for version in self:
            if version.employee_id:
                version.company_id = version.employee_id.company_id

    @api.depends('company_id')
    def _compute_work_location_id(self):
        for version in self:
            if version.work_location_id and version.work_location_id.company_id in version.company_id.parent_ids:
                continue
            work_locations = self.env['hr.work.location']
            if version.company_id and self.env['hr.work.location'].has_access('read'):
                work_locations = self.env['hr.work.location'].search([
                    ('company_id', 'in', version.company_id.parent_ids.ids),
                    ('location_type', '=', 'office'),
                ])
            version.work_location_id = work_locations if len(work_locations) == 1 else False

    @api.depends('job_id.name')
    def _compute_job_title(self):
        for version in self.filtered('job_id'):
            if version._origin.job_id != version.job_id or not version.is_custom_job_title:
                version.job_title = version.job_id.name

    def _inverse_job_title(self):
        for version in self:
            version.is_custom_job_title = version.job_title != version.job_id.name

    @api.depends('parent_id')
    def _compute_coach(self):
        for version in self:
            manager = version.parent_id
            previous_manager = version._origin.parent_id
            if manager and (version.coach_id == previous_manager or not version.coach_id):
                version.coach_id = manager
            elif not version.coach_id:
                version.coach_id = False

    @api.depends('job_id')
    def _compute_is_custom_job_title(self):
        for version in self.filtered('job_id'):
            if version._origin.job_id != version.job_id:
                version.is_custom_job_title = False

    @api.depends("private_country_id")
    def _compute_allowed_country_state_ids(self):
        versions_with_countries = self.filtered("private_country_id")
        for version in versions_with_countries:
            version.allowed_country_state_ids = version.private_country_id.state_ids
        if versions_without_countries := (self - versions_with_countries):
            states = self.env["res.country.state"].search([])
            for version in versions_without_countries:
                version.allowed_country_state_ids = states

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
                raise ValidationError(self.env._(
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
                    raise ValidationError(self.env._(
                        "%s already has a contract running during the selected period.\n\n"
                        "Please either:\n\n"
                        "- Change the start date so that it doesn't overlap with the existing contract, or\n"
                        "- Create a new employee if this employee should have multiple active contracts.",
                        version.employee_id.display_name))
            if not contract_period_exists:
                dates_per_employee[version.employee_id].append((version.contract_date_start, version.contract_date_end, version))

    def check_contract_finished(self):
        """Raise if the version has an open-ended contract (start date but no end date).

        :raise ValidationError: if ``contract_date_start`` is set and ``contract_date_end`` is not
        """
        if self.contract_date_start and not self.contract_date_end:
            raise ValidationError(self.env._("Before creating a new contract, close the current one by setting an end date."))

    @api.model_create_multi
    def create(self, vals_list):
        """Create versions, pre-filling them from ``contract_template_id`` when given.

        Template values (see :meth:`get_values_from_contract_template`) only
        fill the keys absent from ``vals``. To add a version to an existing
        employee, prefer ``hr.employee.create_version``, which copies the
        version in effect and keeps the contract dates consistent.
        """
        Version = self.env['hr.version']
        for vals in vals_list:
            if 'contract_template_id' in vals:
                contract_vals = Version.get_values_from_contract_template(Version.browse(vals['contract_template_id']))
                # take vals from template, but priority given to the original vals
                vals.update({**contract_vals, **vals})
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_last_version(self):
        deleted_employee_ids = set(self.env.context.get('hr_unlink_employee_ids', ()))
        for employee_id, versions in self.grouped('employee_id').items():
            if employee_id.id in deleted_employee_ids:
                continue
            if employee_id.version_ids == versions:
                raise ValidationError(
                    self.env._('Employee %s must always have at least one active version.') % employee_id.name
                )

    def write(self, vals):
        """Write on versions, keeping the contract dates consistent across the versions of a contract.

        All versions of a contract share the same ``contract_date_start`` and
        ``contract_date_end``: writing one of these fields on a version writes
        them on every active version of the same contract (writing a start date
        on the only version of an employee also moves its ``date_version``;
        on versions not yet in contract, only the written versions are affected).
        Writing them on versions of different contracts of the same employee at
        once is refused. Pass ``sync_contract_dates=True`` in the context to
        bypass the propagation and write the values as is.

        Also notifies the employee when ``hr_responsible_id`` changes.

        :raise ValidationError: when unassigning or archiving all the versions
            of an employee, or writing contract dates on versions of different
            contracts at once
        """
        if 'hr_responsible_id' in vals:
            new_responsible = self.env['res.users'].browse(vals['hr_responsible_id'])
            for version in self:
                if version.hr_responsible_id.id != vals['hr_responsible_id'] and version.employee_id:
                    recipient = version.employee_id.user_id.partner_id or version.employee_id.work_contact_id
                    if recipient:
                        self.env['mail.thread'].sudo().message_notify(
                            body=self.env._("Your HR Responsible has been updated to %s.", new_responsible.name),
                            partner_ids=recipient.ids,
                            subject=self.env._('HR Responsible Update'),
                        )

        # Employee Versions Validation
        if 'employee_id' in vals:
            if self.filtered(lambda v: v.employee_id and v.employee_id.version_ids <= self and vals['employee_id'] != v.employee_id.id):
                raise ValidationError(self.env._("Cannot unassign all the active versions of an employee."))
        if 'active' in vals and not vals['active']:
            if self.filtered(lambda v: v.employee_id and v.employee_id.version_ids <= self):
                raise ValidationError(self.env._("Cannot archive all the active versions of an employee."))

        if self.env.context.get('sync_contract_dates') or ("contract_date_start" not in vals and "contract_date_end" not in vals):
            return super().write(vals)

        for versions_by_employee in self.grouped('employee_id').values():
            if len(versions_by_employee.grouped('contract_date_start').keys()) > 1:
                raise ValidationError(self.env._("Cannot modify multiple versions contract dates with different contracts at once."))

        multiple_versions = self
        if vals.get("contract_date_start"):
            unique_versions = multiple_versions.filtered(lambda v: len(v.employee_id.version_ids) == 1)
            multiple_versions -= unique_versions
            if len(unique_versions):
                unique_versions.with_context(sync_contract_dates=True).write({
                    **vals,
                    "date_version": vals["contract_date_start"]
                })

        if not any(multiple_versions.mapped('contract_date_start')):
            return super(HrVersion, multiple_versions).write(vals)

        new_vals = {
            f_name: f_value
            for f_name, f_value in vals.items()
            if (f_name != 'contract_date_start' or not f_value) and f_name != 'contract_date_end'
        }
        for employee, versions in multiple_versions.grouped('employee_id').items():

            dates_vals = {}
            first_version = next(iter(versions), versions)

            if "contract_date_start" in vals:
                dates_vals["contract_date_start"] = fields.Date.to_date(vals.get('contract_date_start'))
            else:
                dates_vals["contract_date_start"] = first_version.contract_date_start
            if "contract_date_end" in vals:
                dates_vals["contract_date_end"] = fields.Date.to_date(vals.get('contract_date_end'))
            else:
                dates_vals["contract_date_end"] = first_version.contract_date_end

            if first_version.contract_date_start:
                versions_to_sync = employee._get_contract_versions(
                    date_start=first_version.contract_date_start,
                    date_end=first_version.contract_date_end,
                )
                all_versions_to_sync = self.env['hr.version']
                for contract_versions in versions_to_sync.values():
                    all_versions_to_sync |= next(iter(contract_versions.values()))

                if all_versions_to_sync:
                    all_versions_to_sync.with_context(sync_contract_dates=True).write(dates_vals)

            else:
                versions.with_context(sync_contract_dates=True).write(dates_vals)

        return super(HrVersion, multiple_versions).write(new_vals)

    def get_record_default_action(self, access_uid=None):
        """Return the action opening the version: the employee form for employee versions.

        - Version of an employee: opens the employee (``hr.employee``, or
          ``hr.employee.public`` for non HR officers) with ``version_id`` in the
          context, so that the form shows this version.
        - Contract template (no employee): opens the version with the contract
          template form view.

        :param int access_uid: the user to check instead of the current user
        :rtype: dict
        """
        res = super().get_record_default_action(access_uid=access_uid)
        context = res.get('context', {})
        if self.employee_id:
            user = self.env.user
            if access_uid:
                user = self.env['res.users'].browse(access_uid)
            res['res_model'] = 'hr.employee' if user.has_group('hr.group_hr_user') else 'hr.employee.public'
            res['res_id'] = self.employee_id.id
            res['context'] = dict(context, version_id=self.id)
        else:
            if not context.get('form_view_ref', False):
                res['context'] = dict(context, form_view_ref='hr.hr_contract_template_form_view')
        return res

    @api.depends_context('lang')
    @api.depends('date_version')
    def _compute_display_name(self):
        for version in self:
            version.display_name = version.name if not version.employee_id else format_date_abbr(version.env, version.date_version)

    def _compute_is_current(self):
        today = fields.Date.context_today(self)
        for version in self:
            version.is_current = version.date_start <= today and (not version.date_end or version.date_end >= today)

    def _compute_is_past(self):
        today = fields.Date.context_today(self)
        for version in self:
            version.is_past = version.date_end and version.date_end < today

    def _compute_is_future(self):
        today = fields.Date.context_today(self)
        for version in self:
            version.is_future = version.date_start > today

    def _compute_is_in_contract(self):
        for version in self:
            version.is_in_contract = version._is_in_contract()

    def _is_in_contract(self, date=None):
        """Return whether this version has a contract and is in effect on ``date``.

        Checks ``date_start <= date <= date_end`` of the **version**, not of the
        whole contract: an older version of a still running contract answers
        ``False``. Use ``hr.employee._is_in_contract`` to check the contract
        itself. Single version only.

        :param date: the date to check, today (user's timezone) by default
        :type date: datetime.date or None
        :rtype: bool
        """
        # Return True if the employee is in contract on a given date (today by default)
        if not self.contract_date_start:
            return False
        if date is None:
            date = fields.Date.context_today(self)
        return self.date_start <= date and (not self.date_end or self.date_end >= date)

    def _is_flexible(self):
        """Return whether the version's working schedule is flexible.

        :rtype: bool
        """
        self.ensure_one()
        return bool(self.resource_calendar_id) and self.resource_calendar_id._is_flexible()

    def _is_fully_flexible(self):
        """Return whether the version's working schedule is fully flexible.

        :rtype: bool
        """
        self.ensure_one()
        return bool(self.resource_calendar_id) and self.resource_calendar_id._is_fully_flexible()

    def _is_overlapping_period(self, date_from, date_to):
        """Return whether this version is in contract and in effect at least one day of the period.

        Compares the version's ``date_start``/``date_end`` (not the whole
        contract) with the period. Returns ``False`` if the version has no
        contract or if a bound is missing.

        :param datetime.date date_from: start of the period (inclusive)
        :param datetime.date date_to: end of the period (inclusive)
        :rtype: bool
        """
        if not (self.contract_date_start and date_from and date_to):
            return False
        period_start = date_from or date.min
        period_end = date_to or date.max
        contract_end = self.date_end or date.max
        return period_start <= contract_end and self.date_start <= period_end

    def _get_reference_calendar(self, date=None):
        """Return the reference calendar (full-time equivalent) of the version's working schedule.

        That is the calendar's ``reference_calendar_id``, or the company's
        default calendar. With ``date``, the employee's version in effect on
        that date is used instead of ``self``.

        :param date: reference date
        :type date: datetime.date or None
        :rtype: resource.calendar
        """
        self.ensure_one()
        version = self.employee_id._get_version(date) if date else self
        return version.resource_calendar_id.reference_calendar_id or version.company_id.resource_calendar_id

    @api.model
    def _get_whitelist_fields_from_template(self):
        """Return the names of the fields copied from a contract template.

        Extend it to have a new ``hr.version`` field filled by contract templates
        (related fields are never copied). The fields should be tracked so that
        the change is visible.

        :rtype: list[str]
        """
        # Add here any field that you want to copy from a contract template
        # Those fields should have tracking=1 in hr.version to see the change
        return ['job_id', 'department_id', 'employee_type_id', 'structure_type_id', 'wage', 'resource_calendar_id', 'reference_calendar_id', 'hr_responsible_id']

    def get_values_from_contract_template(self, contract_template_id):
        """Return the values to copy from a contract template onto a version.

        Contract templates are ``hr.version`` records without employee. Only
        the whitelisted fields (:meth:`_get_whitelist_fields_from_template`,
        evaluated in the template's company) are returned.

        :param contract_template_id: the template (may be empty)
        :type contract_template_id: hr.version
        :return: values in ``copy_data`` format, ``{}`` without template
        :rtype: dict
        """
        if not contract_template_id:
            return {}
        company = contract_template_id.company_id or self.env.company
        whitelist = self.with_company(company)._get_whitelist_fields_from_template()
        contract_template_vals = contract_template_id.copy_data()[0]
        return {
            field: value
                for field, value in contract_template_vals.items()
                if field in whitelist and not self.env['hr.version']._fields[field].related
        }

    def _get_contract_wage(self):
        """Return the contractual wage, read from the field given by :meth:`_get_contract_wage_field`.

        :return: the wage, 0 for an empty recordset
        :rtype: float
        """
        if not self:
            return 0
        self.ensure_one()
        return self[self._get_contract_wage_field()]

    def _get_contract_wage_field(self):
        """Return the name of the field holding the contractual wage (``'wage'``).

        Overridden e.g. by ``hr_payroll`` (hourly wage) and localizations.

        :rtype: str
        """
        self.ensure_one()
        return 'wage'

    def _get_normalized_wage(self):
        """Return the hourly wage, assuming a monthly wage (``wage * 12 / 52 / hours_per_week``).

        Without calendar, the wage is returned as is (supposed hourly); with a
        calendar without hours, 0. Overridden in ``hr_payroll``, which knows
        the pay frequency.

        :rtype: float
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
        """Return the employee of the current user, preferably in the current company.

        Falls back on the user's employee in their default company, then on any
        of their employees (searched in sudo, across companies).

        :return: at most one employee
        :rtype: hr.employee
        """
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

    @api.depends('distance_home_work', 'distance_home_work_unit')
    def _compute_km_home_work(self):
        for version in self:
            version.km_home_work = version.distance_home_work * 1.609 if version.distance_home_work_unit == "miles" else version.distance_home_work

    def _inverse_km_home_work(self):
        for version in self:
            version.distance_home_work = version.km_home_work / 1.609 if version.distance_home_work_unit == "miles" else version.km_home_work

    @api.depends(
        'contract_date_start', 'contract_date_end', 'date_version', 'employee_id',
        'employee_id.version_ids.date_version', 'departure_date')
    def _compute_dates(self):
        """Compute ``date_start`` and ``date_end``, the period during which the version is in effect.

        - ``date_start``: ``max(date_version, contract_date_start)``, or
          ``date_version`` without contract;
        - ``date_end``: the day before the next active version of the employee,
          capped by ``contract_date_end``; ``False`` if it is the last version
          of an open-ended (or no) contract.

        Both dates are inclusive. These fields are not stored but searchable.
        """
        for version in self:
            version.date_start = max(version.date_version, version.contract_date_start) \
                if version.contract_date_start \
                else version.date_version

        all_versions = self.search_fetch([
            ('employee_id', 'in', self.employee_id.ids),
            ('active', '=', True),
            ('date_version', '>', min(self.mapped('date_start'), default=date.today())),
        ], ['employee_id', 'date_version'], order='date_version').grouped('employee_id')
        for version in self:
            date_version_end = False
            if next_versions := all_versions.get(version.employee_id):
                date_version_end = next((d for d in next_versions.mapped('date_version') if d > version.date_version), None)
                if date_version_end:
                    date_version_end -= relativedelta(days=1)

            if date_version_end and version.contract_date_end:
                version.date_end = min(date_version_end, version.contract_date_end)
            elif date_version_end:
                version.date_end = date_version_end
            else:
                version.date_end = version.contract_date_end

    def _search_start_date(self, operator, value):
        if operator in ('>', '>='):
            return [
                '|',
                    ('date_version', operator, value),
                    ('contract_date_start', operator, value),
            ]

        if operator in ('<', '<='):
            return [
                '&',
                    ('date_version', operator, value),
                    '|',
                        ('contract_date_start', '=', False),
                        ('contract_date_start', operator, value),
            ]

        if operator == '=':
            return [
                '|',
                    '&',
                        ('date_version', '=', value),
                        '|',
                            ('contract_date_start', '=', False),
                            ('contract_date_start', '<=', value),
                    '&',
                        ('contract_date_start', '=', value),
                        ('date_version', '<=', value),
            ]

        if operator == '!=':
            return ['!', *self._search_start_date('=', value)]

        return NotImplemented

    def _search_end_date(self, operator, value):
        if operator not in ('<', '<=', '>', '>=', 'in'):
            return NotImplemented
        # Same logic as _compute_dates: the version ends the day before the next
        # active version of the employee, or at the end of its contract.
        date_end_sql = SQL("""
            LEAST(
                (
                    SELECT MIN(next_version.date_version)
                      FROM hr_version next_version
                     WHERE next_version.employee_id = hr_version.employee_id
                       AND next_version.active
                       AND next_version.date_version > hr_version.date_version
                ) - 1,
                hr_version.contract_date_end
            )
        """)
        if operator == 'in':
            dates = [fields.Date.to_date(d) for d in value if d]
            conditions = []
            if dates:
                conditions.append(SQL("%s IN %s", date_end_sql, tuple(dates)))
            if False in value:
                conditions.append(SQL("%s IS NULL", date_end_sql))
            if not conditions:
                return Domain.FALSE
            condition = SQL(" OR ").join(conditions)
        else:
            sql_operator = {'<': SQL('<'), '<=': SQL('<='), '>': SQL('>'), '>=': SQL('>=')}[operator]
            condition = SQL("%s %s %s::date", date_end_sql, sql_operator, value)
        return [('id', 'in', SQL("(SELECT hr_version.id FROM hr_version WHERE %s)", condition))]

    @api.model
    def _get_marital_status_selection(self):
        return [
            ('single', self.env._('Single')),
            ('married', self.env._('Married')),
            ('cohabitant', self.env._('Legal Cohabitant')),
            ('widower', self.env._('Widower')),
            ('divorced', self.env._('Divorced')),
        ]

    @api.model
    def _get_current_versions_domain(self):
        """Return a domain matching the employee versions whose contract covers today.

        All versions of a running contract match (not only the version in
        effect today); contract templates (no employee) are excluded.

        :rtype: list
        """
        today = fields.Date.context_today(self)
        return [
            ("contract_date_start", "<=", today),
            "|",
                ("contract_date_end", "=", False),
                ("contract_date_end", ">=", today),
            ('employee_id', '!=', False),
        ]

    def _inverse_resource_calendar_id(self):
        """Copy the calendar of current versions onto their employee's ``resource.resource``.

        The resource's ``calendar_id`` mirrors the current version's calendar
        (it is what ``resource`` methods use for employees without contract).
        """
        for employee, versions in self.grouped('employee_id').items():
            current_version = employee.current_version_id
            for version in versions:
                if version == current_version and employee.resource_id.calendar_id != version.resource_calendar_id:
                    employee.resource_id.calendar_id = version.resource_calendar_id

    def _get_salary_costs_factor(self):
        """Return the factor turning the wage into a yearly cost (12, i.e. a monthly wage).

        Overridden in ``hr_payroll`` (based on the pay schedule) and by
        localizations (e.g. 13th month, employer contributions).

        :rtype: float
        """
        self.ensure_one()
        return 12.0

    def _is_struct_from_country(self, country_code):
        """Return whether the version's salary structure type belongs to the given country.

        :param str country_code: ISO country code, e.g. ``'BE'``
        :rtype: bool
        """
        self.ensure_one()
        self_sudo = self.sudo()
        return self_sudo.structure_type_id and self_sudo.structure_type_id.country_id.code == country_code

    def _get_tz(self):
        """Return the timezone name of the version.

        Falls back on the employee's user partner timezone, the employee's
        company timezone, then ``'UTC'``.

        :rtype: str
        """
        self.ensure_one()
        return self.tz or self.employee_id.user_partner_id.tz or self.employee_id.company_id.tz or 'UTC'

    def _get_resources_per_tz(self):
        """Group the resources of the versions' employees by the versions' timezone.

        :return: ``{ZoneInfo: resource.resource}``
        :rtype: dict
        """
        version_per_tz = self.grouped(lambda e: ZoneInfo(e._get_tz()))
        return {
            tz: versions.employee_id.resource_id
            for tz, versions in version_per_tz.items()
        }

    def _get_field_block_start_date(self, field_name):
        """Return since when ``field_name`` continuously has its current value.

        Walks back the employee's versions from ``self`` as long as the
        previous version has the same value and is continuous with the next
        one (:meth:`_is_continuous_with`), and returns the ``date_start`` of the
        earliest one. Useful for seniority in a job, salary scale, ...

        :param str field_name: the ``hr.version`` field to track
        :return: the start date, or ``None`` if the field is empty on ``self``
        :rtype: datetime.date or None
        """
        self.ensure_one()
        current_value = self[field_name]
        if not current_value:
            return None

        # version_ids are ordered by date_version, which is also the date_start
        # order as the contracts of an employee cannot overlap
        versions = self.employee_id.version_ids

        try:
            idx = next(i for i, v in enumerate(versions) if v.id == self.id)
        except StopIteration:
            idx = len(versions) - 1

        start_version = versions[idx]
        for j in range(idx - 1, -1, -1):
            prev = versions[j]
            if prev[field_name] != current_value or not prev._is_continuous_with(start_version):
                break
            start_version = prev

        return start_version.date_start

    def _has_work_hours_between_versions(self, version_to):
        """Return whether there are working hours between the end of ``self`` and the start of ``version_to``.

        Uses ``self``'s calendar, without leaves. Back-to-back versions never
        have work hours in between; without calendar, ``False``. Used to decide
        whether two versions are consecutive (see
        ``hr.employee._get_last_consecutive_versions``).

        :param version_to: the next version
        :type version_to: hr.version
        :rtype: bool
        """
        # we consider two versions to be consecutive if no work hours are
        # in the period between the two versions
        tz = ZoneInfo(self._get_tz())
        date_from = datetime.combine(self.date_end, time.max, tz) if self.date_end else date.max
        date_to = datetime.combine(version_to.date_start, time.min, tz)
        calendar_id = self.resource_calendar_id
        if not calendar_id:
            return False
        if self.date_end and self.date_end + relativedelta(days=1) == version_to.date_start:
            # fast path: back-to-back versions cannot have work hours between them.
            # We can bypass the expensive calendar lookup
            return False
        return bool(calendar_id.get_work_hours_count(date_from, date_to, compute_leaves=False))

    def _is_continuous_with(self, next_version):
        """Return whether ``next_version`` continues ``self`` without breaking continuity.

        Used by :meth:`_get_field_block_start_date`. By default any gap between
        versions is tolerated (always ``True``); localizations may override it
        (e.g. ``l10n_be_hr_payroll``).

        :param next_version: the version following ``self``
        :type next_version: hr.version
        :rtype: bool
        """
        self.ensure_one()
        return True

    def action_open_version(self):
        self.ensure_one()

        return {
            'type': "ir.actions.act_window",
            'res_model': "hr.employee",
            'res_id': self.employee_id.id,
            'views': [[False, "form"]],
            'target': "current",
            'context': {
                'version_id': self.id,
            },
        }

    def action_open_version_form_view(self):
        self.ensure_one()
        view_id = self.env.ref('hr.hr_contract_template_form_view').id

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.version',
            'res_id': self.id,
            'views': [[view_id, "form"]],
            'target': 'current',
            'context': self.env.context
        }
