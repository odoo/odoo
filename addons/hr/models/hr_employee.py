# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from collections import defaultdict

from pytz import timezone, UTC, utc
from datetime import datetime, time, timedelta, date
from random import choice
from string import digits
from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models, _, tools
from odoo.fields import Domain
from odoo.exceptions import ValidationError, AccessError, RedirectWarning, UserError
from odoo.tools import convert, format_time, email_normalize, SQL, Query
from odoo.tools.intervals import Intervals
from odoo.addons.mail.tools.discuss import Store


class HrEmployee(models.Model):
    """
    NB: Any field only available on the model hr.employee (i.e. not on the
    hr.employee.public model) should have `groups="hr.group_hr_user"` on its
    definition to avoid being prefetched when the user hasn't access to the
    hr.employee model. Indeed, the prefetch loads the data for all the fields
    that are available according to the group defined on them.
    """
    _name = 'hr.employee'
    _description = "Employee"
    _order = 'name'
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin', 'resource.mixin', 'avatar.mixin']
    _mail_post_access = 'read'
    _primary_email = 'work_email'
    _inherits = {'hr.version': 'version_id'}

    # versions
    version_id = fields.Many2one(
        'hr.version',
        compute='_compute_version_id',
        search='_search_version_id',
        ondelete='cascade',
        required=True,
        store=False,
        compute_sudo=True,
        groups="hr.group_hr_user")
    current_version_id = fields.Many2one(
        'hr.version',
        compute='_compute_current_version_id',
        store=True,
        groups="hr.group_hr_user",
    )
    current_date_version = fields.Date(
        related="current_version_id.date_version",
        string="Current Date Version",
        groups="hr.group_hr_user"
    )
    version_ids = fields.One2many(
        'hr.version',
        'employee_id',
        string='Employee Versions',
        groups="hr.group_hr_user",
        required=True
    )
    versions_count = fields.Integer(compute='_compute_versions_count', groups="hr.group_hr_user")

    @api.model
    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    # resource and user
    # required on the resource, make sure required="True" set in the view
    name = fields.Char(string="Employee Name", related='resource_id.name', store=True, readonly=False, tracking=True)
    resource_id = fields.Many2one('resource.resource', required=True)
    # required because the mixin already creates it so it is not related to the version_id
    resource_calendar_id = fields.Many2one(related='version_id.resource_calendar_id', index=False, store=False, check_company=True)
    user_id = fields.Many2one(
        'res.users', 'User',
        related='resource_id.user_id',
        store=True,
        readonly=False,
        check_company=True,
        precompute=True,
        index='btree_not_null',
        ondelete='restrict')
    user_partner_id = fields.Many2one(related="user_id.partner_id", related_sudo=False, string="User's partner")
    share = fields.Boolean(related="user_id.share")
    phone = fields.Char(related="user_id.phone")
    im_status = fields.Char(related="user_id.im_status")
    email = fields.Char(related="user_id.email")
    hr_presence_state = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('archive', 'Archived'),
        ('out_of_working_hour', 'Out of Working hours')], compute='_compute_presence_state', default='out_of_working_hour')
    last_activity = fields.Date(compute="_compute_last_activity")
    last_activity_time = fields.Char(compute="_compute_last_activity")
    hr_icon_display = fields.Selection([
        ('presence_present', 'Present'),
        ('presence_out_of_working_hour', 'Out of Working hours'),
        ('presence_absent', 'Absent'),
        ('presence_archive', 'Archived'),
        ('presence_undetermined', 'Undetermined')], compute='_compute_presence_icon')
    show_hr_icon_display = fields.Boolean(compute='_compute_presence_icon')
    newly_hired = fields.Boolean('Newly Hired', compute='_compute_newly_hired', search='_search_newly_hired')

    active = fields.Boolean('Active', related='resource_id.active', default=True, store=True, readonly=False)
    company_id = fields.Many2one('res.company', required=True, tracking=True)
    company_country_id = fields.Many2one('res.country', 'Company Country', related='company_id.country_id', readonly=True, groups="base.group_system,hr.group_hr_user")
    company_country_code = fields.Char(related='company_country_id.code', depends=['company_country_id'], readonly=True, groups="base.group_system,hr.group_hr_user", string='Company Country Code')
    work_phone = fields.Char('Work Phone', compute="_compute_phones", store=True, readonly=False, tracking=True)
    mobile_phone = fields.Char('Work Mobile', compute="_compute_work_contact_details", store=True, inverse='_inverse_work_contact_details')
    work_email = fields.Char('Work Email', compute="_compute_work_contact_details", store=True, inverse='_inverse_work_contact_details')
    work_contact_id = fields.Many2one('res.partner', 'Work Contact', copy=False, index='btree_not_null')
    # private info
    legal_name = fields.Char(compute='_compute_legal_name', store=True, readonly=False, groups="hr.group_hr_user")
    private_phone = fields.Char(string="Private Phone", groups="hr.group_hr_user")
    private_email = fields.Char(string="Private Email", groups="hr.group_hr_user")
    lang = fields.Selection(selection=_lang_get, string="Lang", groups="hr.group_hr_user")
    place_of_birth = fields.Char('Place of Birth', groups="hr.group_hr_user", tracking=True)
    country_of_birth = fields.Many2one('res.country', string="Country of Birth", groups="hr.group_hr_user", tracking=True)
    birthday = fields.Date('Birthday', groups="hr.group_hr_user", tracking=True)
    birthday_public_display = fields.Boolean('Show to all employees', groups="hr.group_hr_user", default=False)
    birthday_public_display_string = fields.Char("Public Date of Birth", compute="_compute_birthday_public_display_string", default="hidden")
    bank_account_id = fields.Many2one(
        'res.partner.bank', 'Bank Account',
        domain="[('partner_id', '=', work_contact_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        groups="hr.group_hr_user",
        tracking=True,
        help='Employee bank account to pay salaries')
    permit_no = fields.Char('Work Permit No', groups="hr.group_hr_user", tracking=True)
    visa_no = fields.Char('Visa No', groups="hr.group_hr_user", tracking=True)
    visa_expire = fields.Date('Visa Expiration Date', groups="hr.group_hr_user", tracking=True)
    work_permit_expiration_date = fields.Date('Work Permit Expiration Date', groups="hr.group_hr_user", tracking=True)
    has_work_permit = fields.Binary(string="Work Permit", groups="hr.group_hr_user")
    work_permit_scheduled_activity = fields.Boolean(default=False, groups="hr.group_hr_user")
    work_permit_name = fields.Char('work_permit_name', compute='_compute_work_permit_name', groups="hr.group_hr_user")
    certificate = fields.Selection(selection='_get_certificate_selection', string='Certificate Level', groups="hr.group_hr_user", tracking=True)
    study_field = fields.Char("Field of Study", groups="hr.group_hr_user", tracking=True)
    study_school = fields.Char("School", groups="hr.group_hr_user", tracking=True)
    emergency_contact = fields.Char(groups="hr.group_hr_user", tracking=True)
    emergency_phone = fields.Char(groups="hr.group_hr_user", tracking=True)

    # employee in company
    parent_id = fields.Many2one('hr.employee', 'Manager', tracking=True, index=True,
                                domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]")
    child_ids = fields.One2many('hr.employee', 'parent_id', string='Direct subordinates')
    coach_id = fields.Many2one(
        'hr.employee', 'Coach', compute='_compute_coach', store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]",
        help='Select the "Employee" who is the coach of this employee.\n'
             'The "Coach" has no specific rights or responsibilities by default.')
    category_ids = fields.Many2many(
        'hr.employee.category', 'employee_category_rel',
        'employee_id', 'category_id', groups="hr.group_hr_user",
        string='Tags')
    # misc
    color = fields.Integer('Color Index', default=0)
    barcode = fields.Char(string="Badge ID", help="ID used for employee identification.", groups="hr.group_hr_user", copy=False)
    pin = fields.Char(string="PIN", groups="hr.group_hr_user", copy=False,
        help="PIN used to Check In/Out in the Kiosk Mode of the Attendance application (if enabled in Configuration) and to change the cashier in the Point of Sale application.")
    message_main_attachment_id = fields.Many2one(groups="hr.group_hr_user")
    id_card = fields.Binary(string="ID Card Copy", groups="hr.group_hr_user")
    driving_license = fields.Binary(string="Driving License", groups="hr.group_hr_user")
    private_car_plate = fields.Char(groups="hr.group_hr_user", help="If you have more than one car, just separate the plates by a space.")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True, groups="hr.group_hr_user")
    related_partners_count = fields.Integer(compute="_compute_related_partners_count", groups="hr.group_hr_user")
    # properties
    employee_properties = fields.Properties('Properties', definition='company_id.employee_properties_definition', precompute=False, groups="hr.group_hr_user")

    # mail.activity.mixin
    activity_ids = fields.One2many(groups="hr.group_hr_user")
    activity_state = fields.Selection(groups="hr.group_hr_user")
    activity_user_id = fields.Many2one(groups="hr.group_hr_user")
    activity_type_id = fields.Many2one(groups="hr.group_hr_user")
    activity_type_icon = fields.Char(groups="hr.group_hr_user")
    activity_date_deadline = fields.Date(groups="hr.group_hr_user")
    my_activity_date_deadline = fields.Date(groups="hr.group_hr_user")
    activity_summary = fields.Char(groups="hr.group_hr_user")
    activity_exception_decoration = fields.Selection(groups="hr.group_hr_user")
    activity_exception_icon = fields.Char(groups="hr.group_hr_user")

    # mail.thread mixin
    message_is_follower = fields.Boolean(groups="hr.group_hr_user")
    message_follower_ids = fields.One2many(groups="hr.group_hr_user")
    message_partner_ids = fields.Many2many(groups="hr.group_hr_user")
    message_ids = fields.One2many(groups="hr.group_hr_user")
    has_message = fields.Boolean(groups="hr.group_hr_user")
    message_needaction = fields.Boolean(groups="hr.group_hr_user")
    message_needaction_counter = fields.Integer(groups="hr.group_hr_user")
    message_has_error = fields.Boolean(groups="hr.group_hr_user")
    message_has_error_counter = fields.Integer(groups="hr.group_hr_user")
    message_attachment_count = fields.Integer(groups="hr.group_hr_user")

    _barcode_uniq = models.Constraint(
        'unique (barcode)',
        'The Badge ID must be unique, this one is already assigned to another employee.',
    )
    _user_uniq = models.Constraint(
        'unique (user_id, company_id)',
        'A user cannot be linked to multiple employees in the same company.',
    )

    @api.model
    def _create(self, data_list):
        versions = [vals['stored'].pop('version_id', None) for vals in data_list]
        result = super()._create(data_list)
        for (employee, version_id, vals) in zip(result, versions, data_list):
            version = self.env['hr.version'].browse(version_id)
            version.employee_id = employee.id
            version.write({**vals.get('inherited', {})['hr.version'], 'employee_id': employee.id})
        return result

    @api.model
    def check_field_access_rights(self, operation, field_names):
        # DISCLAIMER: Dirty hack to avoid having to create a bridge module to override only a
        # groups on a field which is not prefetched (because not stored) but would crash anyway
        # if we try to read them directly (very uncommon use case). Don't add your field on this
        # list if you can specify the group on the field directly (as all the other fields).
        result = super().check_field_access_rights(operation, field_names)
        if not self.env.user.has_group("hr.group_hr_user"):
            result = [field for field in result if field not in ['activity_calendar_event_id', 'rating_ids', 'website_message_ids', 'message_has_sms_error']]
        return result

    def _has_field_access(self, field, operation):
        # DISCLAIMER: Dirty hack to avoid having to create a bridge module to override only a
        # groups on a field which is not prefetched (because not stored) but would crash anyway
        # if we try to read them directly (very uncommon use case). Don't add your field on this
        # list if you can specify the group on the field directly (as all the other fields).
        return super()._has_field_access(field, operation) and (
            self.env.su
            or self.env.user.has_group("hr.group_hr_user")
            or field.name not in ('activity_calendar_event_id', 'rating_ids', 'website_message_ids', 'message_has_sms_error')
        )

    @api.onchange('contract_template_id')
    def _onchange_contract_template_id(self):
        if self.contract_template_id:
            whitelist = self.env['hr.version']._get_whitelist_fields_from_template()
            for field in self.contract_template_id._fields:
                if field in whitelist and not self.env['hr.version']._fields[field].related:
                    self[field] = self.contract_template_id[field]

    @api.onchange('contract_date_start')
    def _onchange_contract_date_start(self):
        if not self.contract_date_start:
            self.contract_date_end = False

    @api.model
    def _get_new_hire_field(self):
        return 'create_date'

    def _compute_newly_hired(self):
        new_hire_field = self._get_new_hire_field()
        new_hire_date = fields.Datetime.now() - timedelta(days=90)
        for employee in self:
            if not employee[new_hire_field]:
                employee.newly_hired = False
            elif not isinstance(employee[new_hire_field], datetime):
                employee.newly_hired = employee[new_hire_field] > new_hire_date.date()
            else:
                employee.newly_hired = employee[new_hire_field] > new_hire_date

    @api.depends('resource_calendar_id', 'hr_presence_state')
    def _compute_presence_icon(self):
        """
        This method compute the state defining the display icon in the kanban view.
        It can be overriden to add other possibilities, like time off or attendances recordings.
        """
        for employee in self:
            employee.hr_icon_display = 'presence_' + employee.hr_presence_state
            employee.show_hr_icon_display = bool(employee.user_id)

    @api.model
    def _get_certificate_selection(self):
        return [
            ('graduate', self.env._('Graduate')),
            ('bachelor', self.env._('Bachelor')),
            ('master', self.env._('Master')),
            ('doctor', self.env._('Doctor')),
            ('other', self.env._('Other')),
        ]

    def _get_first_versions(self):
        self.ensure_one()
        versions = self.version_ids
        if self.env.context.get('before_date'):
            versions = versions.filtered(lambda c: c.date_start <= self.env.context['before_date'])
        return versions

    def _get_first_version_date(self, no_gap=True):
        self.ensure_one()
        if not self.env.user.has_group("hr.group_hr_user"):
            raise AccessError(_("Only HR users can access first version date on an employee."))

        def remove_gap(versions):
            # We do not consider a gap of more than 4 days to be a same occupation
            # versions are considered to be ordered correctly
            if not versions:
                return self.env['hr.version']
            if len(versions) == 1:
                return versions
            current_version = versions[0]
            older_versions = versions[1:]
            current_date = current_version.date_start
            for i, other_version in enumerate(older_versions):
                # Consider current_version.date_end being false as an error and cut the loop
                gap = (current_date - (other_version.date_end or date(2100, 1, 1))).days
                current_date = other_version.date_start
                if gap >= 4:
                    return older_versions[0:i] + current_version
            return older_versions + current_version

        versions = self._get_first_versions().sorted('date_start', reverse=True)
        if no_gap:
            versions = remove_gap(versions)
        return min(versions.mapped('date_start')) if versions else False

    @api.depends('name')
    def _compute_legal_name(self):
        for employee in self:
            if not employee.legal_name:
                employee.legal_name = employee.name

    @api.depends('current_version_id')
    @api.depends_context('version_id')
    def _compute_version_id(self):
        context_version = self.env['hr.version'].browse(self.env.context.get('version_id', False))
        for employee in self:
            if context_version.employee_id == self:
                version = context_version
            else:
                version = employee.current_version_id
            employee.version_id = version

    @api.depends('version_ids.date_version', 'version_ids.active', 'active')
    def _compute_current_version_id(self):
        for employee in self:
            version = self.env['hr.version'].search(
                [('employee_id', 'in', employee.ids), ('date_version', '<=', fields.Date.today())],
                order='date_version desc',
                limit=1,
            )
            if version:
                employee.current_version_id = version
            elif employee.version_ids:
                employee.current_version_id = employee.version_ids[0]
            else:
                employee.current_version_id = False

    def _cron_update_current_version_id(self):
        self.search([])._compute_current_version_id()

    def _search_version_id(self, operator, value):
        if operator in ('any', 'any!'):
            return Domain('current_version_id', operator, value)
        domain = Domain('id', operator, value)
        return Domain('id', 'in', self.env['hr.version']._search(domain).select('employee_id'))

    def _field_to_sql(self, alias: str, field_expr: str, query: (Query | None) = None) -> SQL:
        """This is required to search for the related fields of version_id as version_id is not stored"""
        if field_expr == 'version_id':
            field_expr = 'current_version_id'
        return super()._field_to_sql(alias, field_expr, query)

    def _get_version(self, date=fields.Date.today()):
        """
        Return the version that should be used for the given date.
        If no valid version is found, we return the very first version of the employee.
        """
        version = self.env['hr.version'].search([
            ('employee_id', '=', self.id),
            ('date_version', '<=', date)],
            order='date_version desc', limit=1)
        return version or self.version_ids[0]

    def create_version(self, values):
        self.ensure_one()

        if 'date_version' not in values:
            raise ValueError("date_version is required")
        if isinstance(values['date_version'], str):
            date = fields.Date.to_date(values['date_version'])
        elif isinstance(values['date_version'], datetime):
            date = values['date_version'].date()
        else:
            date = values['date_version']

        version_to_copy = self._get_version(date)
        if not version_to_copy:
            version_to_copy = self.env['hr.version'].search([('employee_id', '=', self.id)], limit=1)
        if version_to_copy.date_version == date:
            return version_to_copy

        date_from, date_to = self._get_contract_dates(date)
        contract_date_start = values['contract_date_start'] = values.get('contract_date_start', date_from)
        contract_date_end = values['contract_date_end'] = values.get('contract_date_end', date_to)
        if isinstance(contract_date_start, str):
            contract_date_start = fields.Date.to_date(contract_date_start)
        if isinstance(contract_date_end, str):
            contract_date_end = fields.Date.to_date(contract_date_end)

        if 'employee_id' not in values:
            values['employee_id'] = self.id

        if contract_date_start == date_from and contract_date_end != date_to:
            versions_to_sync = self.env['hr.version'].with_context(sync_contract_dates=True).search([
                ('employee_id', '=', values['employee_id']),
                ('contract_date_start', '=', date_from),
            ])
            if versions_to_sync:
                versions_to_sync.write({
                    'contract_date_end': contract_date_end,
                })
        return version_to_copy.copy(values)

    def _is_in_contract(self, date):
        return self._get_version(date)._is_in_contract(date)

    def _get_contracts(self, date_start=None, date_end=None, use_latest_version=True, domain=None):
        """
        Retrieve the contracts for employees within a specified date range and based
        on specified criteria, such as domain filtering and version selection.

        This method is used to collect and organize employee contracts based on their
        versions, date ranges, and other specified options. The resulting contracts are
        grouped by employee, and their selection logic depends on whether the latest
        version should be used or not. It supports flexibility in contract retrieval by
        allowing optional filters for date range and domain.

        Args:
            date_start (Optional[datetime.date]): The start date to filter the contracts
                by. If provided, only contract versions <= this date are considered
                based on the selection logic.
            date_end (Optional[datetime.date]): The end date to filter the contracts by.
                Only contract versions within the range will be retrieved. Defaults to
                None if not specified.
            domain (Optional[dict]): A dictionary representing additional filters or
                constraints to apply to the contract versions retrieved. Defaults to
                None.
            use_latest_version (bool): Indicates whether to retrieve the version
            effective at the end of the contract (or before the date_end) for each employee (True) or
            at the start of the contract (before the date_start) (False). Defaults to True.

        Returns:
            collections.defaultdict: A dictionary mapping each employee's identifier
            (employee.id) to a set of their corresponding contracts. Each set contains
            version records retrieved and filtered based on the specified criteria.
        """
        contract_versions_by_employee = self._get_contract_versions(date_start, date_end, domain)
        contracts_by_employee = defaultdict(lambda: self.env["hr.version"])
        for employee_id in contract_versions_by_employee:
            for contract_versions in contract_versions_by_employee[employee_id].values():
                effective_date = date_end if use_latest_version else date_start
                if use_latest_version:
                    if effective_date:
                        correct_versions = contract_versions.filtered(lambda v: v.date_version <= effective_date)
                        contracts_by_employee[employee_id] |= correct_versions[-1] if correct_versions else contract_versions[0]
                    else:
                        contracts_by_employee[employee_id] |= contract_versions[-1] if use_latest_version else contract_versions[0]
        return contracts_by_employee

    def _get_contract_versions(self, date_start=None, date_end=None, domain=None):
        """
        Retrieves contract versions for employees within the specified date range and
        domain. The function constructs a dynamic domain to filter contracts based on
        the provided arguments and retrieves grouped results. The grouping ensures
        organization by employee and date, and the results are stored in a structured
        format for ease of use.

        Args:
            date_start (datetime.date | None): The start date for filtering contracts.
            date_end (datetime.date | None): The end date for filtering contracts.
            domain (list | None): Additional domain constraints for filtering.

        Returns:
            dict: A dictionary where keys are employee IDs and values are lists of
                  contract version records organized by contract date start and date
                  range.
        """
        version_domain = Domain('contract_date_start', '!=', False)
        if self.ids:
            version_domain &= Domain('employee_id', 'in', self.ids)
        if date_start:
            version_domain &= Domain('contract_date_end', '=', False) | Domain('contract_date_end', '>', date_start)
        if date_end:
            version_domain &= Domain('contract_date_start', '<', date_end)
        if domain:
            version_domain &= domain
        all_versions = self.env['hr.version']._read_group(
            domain=version_domain,
            groupby=['employee_id', 'date_version:day'],
            aggregates=['id:recordset'],
        )
        contract_versions_by_employee = defaultdict(lambda: defaultdict(lambda: self.env["hr.version"]))
        for employee, _date_version, version in all_versions:
            contract_versions_by_employee[employee.id][version.contract_date_start] |= version
        return contract_versions_by_employee

    def _get_all_contract_dates(self):
        """
        Return a list of intervals (date_from, date_to) where the employee is in contract.
        For a permanent contract, the interval is (date_from, False).
        """
        self.ensure_one()
        return self.env['hr.version']._read_group(
            [('employee_id', '=', self.id), ('contract_date_start', '!=', False)],
            ['contract_date_start:day', 'contract_date_end:day'])

    def _get_contract_dates(self, date):
        """
        Return a tuple (date_from, date_to) of the contract at the date given.
        (False, False) if the employee is not in contract at that date.
        """
        self.ensure_one()
        for date_from, date_to in self._get_all_contract_dates():
            if date_from <= date and (date_to is False or date_to >= date):
                return date_from, date_to
        return False, False

    def _compute_versions_count(self):
        version_count_per_employee = dict(
            self.env['hr.version']._read_group(
                [('employee_id', 'in', self.ids)],
                ['employee_id'],
                ['id:count'],
            ),
        )
        for employee in self:
            employee.versions_count = version_count_per_employee.get(employee, 0)

    def _search_newly_hired(self, operator, value):
        if operator not in ('in', 'not in'):
            return NotImplemented
        new_hire_field = self._get_new_hire_field()
        new_hires = self.env['hr.employee'].sudo().search([
            (new_hire_field, '>', fields.Datetime.now() - timedelta(days=90))
        ])
        return [('id', operator, new_hires.ids)]

    @api.depends('address_id.phone')
    def _compute_phones(self):
        for employee in self:
            if employee.address_id.phone:
                employee.work_phone = employee.address_id.phone

    def _create_work_contacts(self):
        if any(employee.work_contact_id for employee in self):
            raise UserError(_('Some employee already have a work contact'))
        work_contacts = self.env['res.partner'].create([{
            'email': employee.work_email,
            'phone': employee.mobile_phone,
            'name': employee.name,
            'image_1920': employee.image_1920,
            'company_id': employee.company_id.id
        } for employee in self])
        for employee, work_contact in zip(self, work_contacts):
            employee.work_contact_id = work_contact

    @api.depends('parent_id')
    def _compute_coach(self):
        for version in self:
            manager = version.parent_id
            previous_manager = version._origin.parent_id
            if manager and (version.coach_id == previous_manager or not version.coach_id):
                version.coach_id = manager
            elif not version.coach_id:
                version.coach_id = False

    @api.depends('work_contact_id', 'work_contact_id.phone', 'work_contact_id.email')
    def _compute_work_contact_details(self):
        for employee in self:
            if employee.work_contact_id:
                employee.mobile_phone = employee.work_contact_id.phone
                employee.work_email = employee.work_contact_id.email

    def _inverse_work_contact_details(self):
        employees_without_work_contact = self.env['hr.employee']
        for employee in self:
            if not employee.work_contact_id:
                employees_without_work_contact += employee
            else:
                employee.work_contact_id.sudo().write({
                    'email': employee.work_email,
                    'phone': employee.mobile_phone,
                })
        if employees_without_work_contact:
            employees_without_work_contact.sudo()._create_work_contacts()

    @api.model
    def _get_employee_working_now(self):
        """ Sudo needed to get resource_calendar_id as its normally only accessible by hr_users on version model
        (accessible on employee by inherits)."""
        working_now = []
        # We loop over all the employee tz and the resource calendar_id to detect working hours in batch.
        all_employee_tz = set(self.mapped('tz'))
        for tz in all_employee_tz:
            employee_ids = self.filtered(lambda e: e.tz == tz)
            resource_calendar_ids = employee_ids.sudo().mapped('resource_calendar_id')
            for calendar_id in resource_calendar_ids:
                res_employee_ids = employee_ids.sudo().filtered(lambda e: e.resource_calendar_id.id == calendar_id.id)
                start_dt = fields.Datetime.now()
                stop_dt = start_dt + timedelta(hours=1)
                from_datetime = utc.localize(start_dt).astimezone(timezone(tz or 'UTC'))
                to_datetime = utc.localize(stop_dt).astimezone(timezone(tz or 'UTC'))
                # Getting work interval of the first is working. Functions called on resource_calendar_id
                # are waiting for singleton
                work_interval = res_employee_ids[0].resource_calendar_id._work_intervals_batch(from_datetime, to_datetime)[False]
                # Employee that is not supposed to work have empty items.
                if len(work_interval._items) > 0:
                    # The employees should be working now according to their work schedule
                    working_now += res_employee_ids.ids
        return working_now

    @api.depends('user_id.im_status')
    def _compute_presence_state(self):
        """
        This method is overritten in several other modules which add additional
        presence criterions. e.g. hr_attendance, hr_holidays
        """
        # sudo: res.users - can access presence of accessible user
        employee_to_check_working = self.filtered(
            lambda e: (e.user_id.sudo().presence_ids.status or "offline") == "offline"
        )
        working_now_list = employee_to_check_working._get_employee_working_now()
        for employee in self:
            state = 'out_of_working_hour'
            if employee.company_id.sudo().hr_presence_control_login:
                # sudo: res.users - can access presence of accessible user
                presence_status = employee.user_id.sudo().presence_ids.status or "offline"
                if presence_status == "online":
                    state = 'present'
                elif presence_status == "offline" and employee.id in working_now_list:
                    state = 'absent'
            if not employee.active:
                state = 'archive'
            employee.hr_presence_state = state

    @api.depends('user_id')
    def _compute_last_activity(self):
        for employee in self:
            tz = employee.tz
            # sudo: res.users - can access presence of accessible user
            if last_presence := employee.user_id.sudo().presence_ids.last_presence:
                last_activity_datetime = last_presence.replace(tzinfo=UTC).astimezone(timezone(tz)).replace(tzinfo=None)
                employee.last_activity = last_activity_datetime.date()
                if employee.last_activity == fields.Date.today():
                    employee.last_activity_time = format_time(self.env, last_presence, time_format='short')
                else:
                    employee.last_activity_time = False
            else:
                employee.last_activity = False
                employee.last_activity_time = False

    @api.depends('name', 'user_id.avatar_1920', 'image_1920')
    def _compute_avatar_1920(self):
        super()._compute_avatar_1920()

    @api.depends('name', 'user_id.avatar_1024', 'image_1024')
    def _compute_avatar_1024(self):
        super()._compute_avatar_1024()

    @api.depends('name', 'user_id.avatar_512', 'image_512')
    def _compute_avatar_512(self):
        super()._compute_avatar_512()

    @api.depends('name', 'user_id.avatar_256', 'image_256')
    def _compute_avatar_256(self):
        super()._compute_avatar_256()

    @api.depends('name', 'user_id.avatar_128', 'image_128')
    def _compute_avatar_128(self):
        super()._compute_avatar_128()

    def _compute_avatar(self, avatar_field, image_field):
        employee_wo_user_and_image = self.env['hr.employee']
        for employee in self:
            if not employee.user_id and not employee._origin[image_field]:
                employee_wo_user_and_image += employee
                continue
            avatar = employee._origin[image_field]
            if not avatar and employee.user_id:
                avatar = employee.user_id.sudo()[avatar_field]
            employee[avatar_field] = avatar
        super(HrEmployee, employee_wo_user_and_image)._compute_avatar(avatar_field, image_field)

    @api.depends('birthday_public_display')
    def _compute_birthday_public_display_string(self):
        for employee in self:
            if employee.birthday and employee.birthday_public_display:
                employee.birthday_public_display_string = datetime.strftime(employee.birthday, "%d %B")
            else:
                employee.birthday_public_display_string = "hidden"

    @api.depends('name', 'permit_no')
    def _compute_work_permit_name(self):
        for employee in self:
            name = employee.name.replace(' ', '_') + '_' if employee.name else ''
            permit_no = '_' + employee.permit_no if employee.permit_no else ''
            employee.work_permit_name = "%swork_permit%s" % (name, permit_no)

    @api.depends('distance_home_work', 'distance_home_work_unit')
    def _compute_km_home_work(self):
        for employee in self:
            employee.km_home_work = employee.distance_home_work * 1.609 if employee.distance_home_work_unit == "miles" else employee.distance_home_work

    def _inverse_km_home_work(self):
        for employee in self:
            employee.distance_home_work = employee.km_home_work / 1.609 if employee.distance_home_work_unit == "miles" else employee.km_home_work

    def _get_partner_count_depends(self):
        return ['user_id']

    @api.depends(lambda self: self._get_partner_count_depends())
    def _compute_related_partners_count(self):
        self.related_partners_count = len(self._get_related_partners())

    def _get_related_partners(self):
        return self.work_contact_id | self.user_id.partner_id

    def action_related_contacts(self):
        related_partners = self._get_related_partners()
        action = {
            'name': _("Related Contacts"),
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
        }
        if len(related_partners) > 1:
            action['view_mode'] = 'kanban,list,form'
            action['domain'] = [('id', 'in', related_partners.ids)]
            return action
        else:
            action['res_id'] = related_partners.id
        return action

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
            'context': {
                **self.env.context,
                'default_create_employee_id': self.id,
                'default_name': self.name,
                'default_phone': self.work_phone,
                'default_mobile': self.mobile_phone,
                'default_login': self.work_email,
                'default_partner_id': self.work_contact_id.id,
            },
        }

    def action_create_users_confirmation(self):
        raise RedirectWarning(
                message=_("You're about to invite new users. %s users will be created with the default user template's rights. "
                "Adding new users may increase your subscription cost. Do you wish to continue?", len(self.ids)),
                action=self.env.ref('hr.action_hr_employee_create_users').id,
                button_text=_('Confirm'),
                additional_context={
                    'selected_ids': self.ids,
                },
            )

    def action_create_users(self):
        def _get_user_creation_notification_action(message, message_type, next_action):
            return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': self.env._("User Creation Notification"),
                        'type': message_type,
                        'message': message,
                        'next': next_action
                    }
                }

        employee_emails = [
            normalized_email
            for employee in self
            for normalized_email in tools.mail.email_normalize_all(employee.work_email)
        ]
        conflicting_users = self.env['res.users']
        if employee_emails:
            conflicting_users = self.env['res.users'].search([
                '|', ('email_normalized', 'in', employee_emails),
                ('login', 'in', employee_emails),
            ])
        old_users = []
        new_users = []
        users_without_emails = []
        users_with_invalid_emails = []
        users_with_existing_email = []
        for employee in self:
            if employee.user_id:
                old_users.append(employee.name)
                continue
            if not employee.work_email:
                users_without_emails.append(employee.name)
                continue
            if not tools.email_normalize(employee.work_email):
                users_with_invalid_emails.append(employee.name)
                continue
            if email_normalize(employee.work_email) in conflicting_users.mapped('email_normalized'):
                users_with_existing_email.append(employee.name)
                continue
            new_users.append({
                'create_employee_id': employee.id,
                'name': employee.name,
                'phone': employee.work_phone,
                'login': tools.email_normalize(employee.work_email),
                'partner_id': employee.work_contact_id.id,
            })

        next_action = {'type': 'ir.actions.act_window_close'}
        if new_users:
            self.env['res.users'].create(new_users)
            message = _('Users %s creation successful', ', '.join([user['name'] for user in new_users]))
            next_action = _get_user_creation_notification_action(message, 'success', {
                "type": "ir.actions.client",
                "tag": "soft_reload",
                "params": {"next": next_action},
            })

        if old_users:
            message = _('User already exists for Those Employees %s', ', '.join(old_users))
            next_action = _get_user_creation_notification_action(message, 'warning', next_action)

        if users_without_emails:
            message = _("You need to set the work email address for %s", ', '.join(users_without_emails))
            next_action = _get_user_creation_notification_action(message, 'danger', next_action)

        if users_with_invalid_emails:
            message = _("You need to set a valid work email address for %s", ', '.join(users_with_invalid_emails))
            next_action = _get_user_creation_notification_action(message, 'danger', next_action)

        if users_with_existing_email:
            message = _('User already exists with the same email for Employees %s', ', '.join(users_with_existing_email))
            next_action = _get_user_creation_notification_action(message, 'warning', next_action)

        return next_action

    def _compute_display_name(self):
        if self.browse().has_access('read'):
            return super()._compute_display_name()
        for employee_private, employee_public in zip(self, self.env['hr.employee.public'].browse(self.ids)):
            employee_private.display_name = employee_public.display_name

    @api.model
    def search_fetch(self, domain, field_names=None, offset=0, limit=None, order=None):
        if self.browse().has_access('read'):
            return super().search_fetch(domain, field_names, offset, limit, order)

        # HACK: retrieve publicly available values from hr.employee.public and
        # copy them to the cache of self; non-public data will be missing from
        # cache, and interpreted as an access error
        if field_names is None:
            field_names = [field.name for field in self._determine_fields_to_fetch()]
        self._check_private_fields(field_names)
        self.flush_model(field_names)
        # HACK: suppress warning if domain is optimized for another model
        domain = list(domain) if isinstance(domain, Domain) else domain
        public = self.env['hr.employee.public'].search_fetch(domain, field_names, offset, limit, order)
        employees = self.browse(public._ids)
        employees._copy_cache_from(public, field_names)
        return employees

    def fetch(self, field_names=None):
        if self.browse().has_access('read'):
            return super().fetch(field_names)

        # HACK: retrieve publicly available values from hr.employee.public and
        # copy them to the cache of self; non-public data will be missing from
        # cache, and interpreted as an access error
        if field_names is None:
            field_names = [field.name for field in self._determine_fields_to_fetch()]
        self._check_private_fields(field_names)
        self.flush_recordset(field_names)
        public = self.env['hr.employee.public'].browse(self._ids)
        public.fetch(field_names)
        self._copy_cache_from(public, field_names)

    def _check_private_fields(self, field_names):
        """ Check whether ``field_names`` contain private fields. """
        public_fields = self.env['hr.employee.public']._fields
        private_fields = [fname for fname in field_names if fname not in public_fields]
        if private_fields:
            raise AccessError(_('The fields “%s”, which you are trying to read, are not available for employee public profiles.', ','.join(private_fields)))

    def _copy_cache_from(self, public, field_names):
        # HACK: retrieve publicly available values from hr.employee.public and
        # copy them to the cache of self; non-public data will be missing from
        # cache, and interpreted as an access error
        for fname in field_names:
            values = self.env.cache.get_values(public, public._fields[fname])
            if self._fields[fname].translate:
                values = [(value.copy() if value else None) for value in values]
            self.env.cache.update_raw(self, self._fields[fname], values)

    @api.model
    def notify_expiring_contract_work_permit(self):
        companies = self.env['res.company'].search([])
        employees_contract_expiring = self.env['hr.employee']
        employees_work_permit_expiring = self.env['hr.employee']

        for company in companies:
            employees_contract_expiring += self.env['hr.employee'].search([
                ('company_id', '=', company.id),
                ('contract_date_start', '!=', False),
                ('contract_date_start', '<', fields.Date.today()),
                ('contract_date_end', '=', fields.Date.today() + relativedelta(days=company.contract_expiration_notice_period)),
            ])

            employees_work_permit_expiring += self.env['hr.employee'].search([
                ('company_id', '=', company.id),
                ('work_permit_expiration_date', '!=', False),
                ('work_permit_expiration_date', '=', fields.Date.today() + relativedelta(days=company.work_permit_expiration_notice_period)),
            ])

        for employee in employees_contract_expiring:
            employee.with_context(mail_activity_quick_update=True).activity_schedule(
                'mail.mail_activity_data_todo', employee.contract_date_end,
                _("The contract of %s is about to expire.", employee.name),
                user_id=employee.hr_responsible_id.id or self.env.uid)

        for employee in employees_work_permit_expiring:
            employee.with_context(mail_activity_quick_update=True).activity_schedule(
                'mail.mail_activity_data_todo', employee.work_permit_expiration_date,
                _("The work permit of %s is about to expire.", employee.name),
                user_id=employee.hr_responsible_id.id or self.env.uid)

        return True

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        if self.browse().has_access('read'):
            return super().get_view(view_id, view_type, **options)
        return self.env['hr.employee.public'].get_view(view_id, view_type, **options)

    @api.model
    def get_views(self, views, options=None):
        if self.browse().has_access('read'):
            return super().get_views(views, options)
        res = self.env['hr.employee.public'].get_views(views, options)
        res['models'].update({'hr.employee': res['models']['hr.employee.public']})
        return res

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, *, bypass_access=False, **kwargs):
        """
            We override the _search because it is the method that checks the access rights
            This is correct to override the _search. That way we enforce the fact that calling
            search on an hr.employee returns a hr.employee recordset, even if you don't have access
            to this model, as the result of _search (the ids of the public employees) is to be
            browsed on the hr.employee model. This can be trusted as the ids of the public
            employees exactly match the ids of the related hr.employee.
        """
        if self.browse().has_access('read') or bypass_access:
            return super()._search(domain, offset, limit, order, bypass_access=bypass_access, **kwargs)
        try:
            # HACK: suppress warning if domain is optimized for another model
            domain = list(domain) if isinstance(domain, Domain) else domain
            ids = self.env['hr.employee.public']._search(domain, offset, limit, order, **kwargs)
        except ValueError:
            raise AccessError(_('You do not have access to this document.'))
        # the result is expected from this table, so we should link tables
        return super(HrEmployee, self.sudo())._search([('id', 'in', ids)], order=order)

    def _load_demo_data(self):
        dep_rd = self.env.ref('hr.dep_rd', raise_if_not_found=False)
        action_reload = {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
        if dep_rd:
            return action_reload
        convert.convert_file(env=self.sudo().env, module='hr', filename='data/scenarios/hr_scenario.xml', idref=None, mode='init')
        if 'resume_line_ids' in self:
            convert.convert_file(env=self.env, module='hr_skills', filename='data/scenarios/hr_skills_scenario.xml', idref=None, mode='init')
        return action_reload

    def get_formview_id(self, access_uid=None):
        """ Override this method in order to redirect many2one towards the right model depending on access_uid """
        user = self.env.user
        if access_uid:
            user = self.env['res.users'].browse(access_uid).sudo()

        if user.has_group('hr.group_hr_user'):
            return super().get_formview_id(access_uid=access_uid)
        # Hardcode the form view for public employee
        return self.env.ref('hr.hr_employee_public_view_form').id

    def get_formview_action(self, access_uid=None):
        """ Override this method in order to redirect many2one towards the right model depending on access_uid """
        res = super().get_formview_action(access_uid=access_uid)
        user = self.env.user
        if access_uid:
            user = self.env['res.users'].browse(access_uid).sudo()

        if not user.has_group('hr.group_hr_user'):
            res['res_model'] = 'hr.employee.public'

        return res

    @api.constrains('pin')
    def _verify_pin(self):
        for employee in self:
            if employee.pin and not employee.pin.isdigit():
                raise ValidationError(_("The PIN must be a sequence of digits."))

    @api.constrains('barcode')
    def _verify_barcode(self):
        for employee in self:
            if employee.barcode:
                if not (re.match(r'^[A-Za-z0-9]+$', employee.barcode) and len(employee.barcode) <= 18):
                    raise ValidationError(_("The Badge ID must be alphanumeric without any accents and no longer than 18 characters."))

    @api.onchange('user_id')
    def _onchange_user(self):
        self.update(self._sync_user(self.user_id, (bool(self.image_1920))))
        if not self.name:
            self.name = self.user_id.name

    @api.onchange('resource_calendar_id')
    def _onchange_timezone(self):
        if self.resource_calendar_id and not self.tz:
            self.tz = self.resource_calendar_id.tz

    def _remove_work_contact_id(self, user, employee_company):
        """ Remove work_contact_id for previous employee if the user is assigned to a new employee """
        employee_company = employee_company or self.company_id.id
        # For employees with a user_id, the constraint (user can't be linked to multiple employees) is triggered
        old_partner_employee_ids = user.partner_id.employee_ids.filtered(lambda e:
            not e.user_id
            and e.company_id.id == employee_company
            and e != self
        )
        old_partner_employee_ids.work_contact_id = None

    def _sync_user(self, user, employee_has_image=False):
        vals = dict(
            work_contact_id=user.partner_id.id if user else self.work_contact_id.id,
            user_id=user.id,
        )
        if not employee_has_image:
            vals['image_1920'] = user.image_1920
        if user.tz:
            vals['tz'] = user.tz
        return vals

    def _prepare_resource_values(self, vals, tz):
        resource_vals = super()._prepare_resource_values(vals, tz)
        vals.pop('name')  # Already considered by super call but no popped
        # We need to pop it to avoid useless resource update (& write) call
        # on every newly created resource (with the correct name already)
        user_id = vals.pop('user_id', None)
        if user_id:
            resource_vals['user_id'] = user_id
        active_status = vals.get('active')
        if active_status is not None:
            resource_vals['active'] = active_status
        return resource_vals

    @api.model
    def new(self, values=None, origin=None, ref=None):
        if not values:
            values = {}
        new_vals = values.copy()
        version_vals = {val: new_vals.pop(val) for val in values if val in self._fields and self._fields[val].inherited}

        employee = super().new(new_vals, origin, ref)
        version_vals['employee_id'] = employee
        self.env['hr.version'].new(version_vals)
        return employee

    @api.model_create_multi
    def create(self, vals_list):
        vals_per_company = defaultdict(list)
        for idx, vals in enumerate(vals_list):
            if vals.get('user_id'):
                user = self.env['res.users'].browse(vals['user_id'])
                vals.update(self._sync_user(user, bool(vals.get('image_1920'))))
                vals['name'] = vals.get('name', user.name)
                self._remove_work_contact_id(user, vals.get('company_id'))
            # Having one create per company is necessary to pass the company in the context to correctly set it in
            # the underlying version created by the framework
            vals_per_company[vals.get('company_id', self.env.company)].append((idx, vals))
        index_per_employee = {}
        employees = self.env['hr.employee']
        for company, vals_list in vals_per_company.items():
            idxs, vals_list = zip(*vals_list)
            new_employees = super(HrEmployee, self.with_company(company)).create(vals_list)
            index_per_employee.update(dict(zip(new_employees, idxs)))
            employees |= new_employees
        # As we do a custom batch by company, we must reorder the records to respect the original order.
        employees = employees.sorted(key=lambda employee: index_per_employee[employee])
        # Sudo in case HR officer doesn't have the Contact Creation group
        employees.filtered(lambda e: not e.work_contact_id).sudo()._create_work_contacts()
        for employee_sudo in employees.sudo():
            # creating 'svg/xml' attachments requires specific rights
            if not employee_sudo.image_1920 and self.env['ir.ui.view'].sudo(False).has_access('write'):
                employee_sudo.image_1920 = employee_sudo._avatar_generate_svg()
                employee_sudo.work_contact_id.image_1920 = employee_sudo.image_1920
        if self.env.context.get('salary_simulation'):
            return employees
        employee_departments = employees.department_id
        if employee_departments:
            self.env['discuss.channel'].sudo().search([
                ('subscription_department_ids', 'in', employee_departments.ids)
            ])._subscribe_users_automatically()
        onboarding_notes_bodies = {}
        hr_root_menu = self.env.ref('hr.menu_hr_root')
        for employee in employees:
            # Launch onboarding plans
            url = '/odoo/%s/action-hr.plan_wizard_action?active_model=hr.employee&menu_id=%s' % (employee.id, hr_root_menu.id)
            onboarding_notes_bodies[employee.id] = Markup(_(
                '<b>Congratulations!</b> May I recommend you to setup an <a href="%s">onboarding plan?</a>',
            )) % url
        employees._message_log_batch(onboarding_notes_bodies)
        employees.invalidate_recordset()
        return employees

    def write(self, vals):
        if 'work_contact_id' in vals:
            account_ids = vals.get('bank_account_id') or self.bank_account_id.ids
            if account_ids:
                bank_accounts = self.env['res.partner.bank'].sudo().browse(account_ids)
                for bank_account in bank_accounts:
                    if vals['work_contact_id'] != bank_account.partner_id.id:
                        if bank_account.allow_out_payment:
                            bank_account.allow_out_payment = False
                        if vals['work_contact_id']:
                            bank_account.partner_id = vals['work_contact_id']
            self.message_unsubscribe(self.work_contact_id.ids)
        if 'user_id' in vals:
            # Update the profile pictures with user, except if provided
            user = self.env['res.users'].browse(vals['user_id'])
            vals.update(self._sync_user(user, (bool(all(emp.image_1920 for emp in self)))))
            self._remove_work_contact_id(user, vals.get('company_id'))
        if 'work_permit_expiration_date' in vals:
            vals['work_permit_scheduled_activity'] = False
        if 'tz' in vals:
            users_to_update = self.env['res.users']
            for employee in self:
                if employee.user_id and employee.company_id == employee.user_id.company_id and vals['tz'] != employee.user_id.tz:
                    users_to_update |= employee.user_id
            if users_to_update:
                users_to_update.write({'tz': vals['tz']})
        if vals.get('department_id') or vals.get('user_id'):
            department_id = vals['department_id'] if vals.get('department_id') else self[:1].department_id.id
            # When added to a department or changing user, subscribe to the channels auto-subscribed by department
            self.env['discuss.channel'].sudo().search([
                ('subscription_department_ids', 'in', department_id)
            ])._subscribe_users_automatically()
        if vals.get('departure_description'):
            for employee in self:
                employee.message_post(body=_(
                    'Additional Information: \n %(description)s',
                    description=vals.get('departure_description')))
        # Only one write call for all the fields from hr.version
        new_vals = vals.copy()
        version_vals = {val: new_vals.pop(val) for val in vals if val in self._fields and self._fields[val].inherited}
        res = super().write(new_vals)
        if version_vals:
            version_vals['last_modified_date'] = fields.Datetime.now()
            version_vals['last_modified_uid'] = self.env.uid
            self.version_id.write(version_vals)

            for employee in self:
                employee._track_set_log_message(Markup("<b>Modified on the Version '%s'</b>") % employee.version_id.display_name)
        if res and 'resource_calendar_id' in vals:
            resources_per_calendar_id = defaultdict(lambda: self.env['resource.resource'])
            for employee in self:
                if employee.version_id == employee.current_version_id:
                    resources_per_calendar_id[employee.resource_calendar_id.id] += employee.resource_id
            for calendar_id, resources in resources_per_calendar_id.items():
                resources.write({'calendar_id': calendar_id})
        return res

    def unlink(self):
        resources = self.mapped('resource_id')
        super().unlink()
        return resources.unlink()

    def _get_employee_m2o_to_empty_on_archived_employees(self):
        return ['parent_id', 'coach_id']

    def _get_user_m2o_to_empty_on_archived_employees(self):
        return []

    def action_unarchive(self):
        res = super().action_unarchive()
        self.write({
            'departure_reason_id': False,
            'departure_description': False,
            'departure_date': False
        })
        return res

    def action_archive(self):
        archived_employees = self.filtered('active')
        res = super().action_archive()
        if archived_employees:
            # Empty links to this employees (example: manager, coach, time off responsible, ...)
            employee_fields_to_empty = self._get_employee_m2o_to_empty_on_archived_employees()
            user_fields_to_empty = self._get_user_m2o_to_empty_on_archived_employees()
            employee_domain = Domain.OR(Domain(field, 'in', archived_employees.ids) for field in employee_fields_to_empty)
            user_domain = Domain.OR(Domain(field, 'in', archived_employees.user_id.ids) for field in user_fields_to_empty)
            employees = self.env['hr.employee'].search(employee_domain | user_domain)
            for employee in employees:
                for field in employee_fields_to_empty:
                    if employee[field] in archived_employees:
                        employee[field] = False
                for field in user_fields_to_empty:
                    if employee[field] in archived_employees.user_id:
                        employee[field] = False

            if len(archived_employees) == 1 and not self.env.context.get('no_wizard', False):
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Register Departure'),
                    'res_model': 'hr.departure.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'active_id': self.id},
                    'views': [[False, 'form']]
                }
        return res

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self._origin:
            return {'warning': {
                'title': _("Warning"),
                'message': _("To avoid multi company issues (losing the access to your previous contracts, leaves, ...), you should create another employee in the new company instead.")
            }}

    def _load_scenario(self):
        demo_tag = self.env.ref('hr.employee_category_demo', raise_if_not_found=False)
        if demo_tag:
            return
        convert.convert_file(self.env, 'hr', 'data/scenarios/hr_scenario.xml', None, mode='init')

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    def generate_random_barcode(self):
        for employee in self:
            employee.barcode = '041'+"".join(choice(digits) for i in range(9))

    def _get_tz(self):
        self.ensure_one()
        return self.tz or\
               self.resource_calendar_id.tz or\
               self.company_id.resource_calendar_id.tz or\
               'UTC'

    def _get_tz_batch(self):
        # Finds the first valid timezone in his tz, his work hours tz,
        #  the company calendar tz or UTC
        # Returns a dict {employee_id: tz}
        return {emp.id: emp._get_tz() for emp in self}

    def _get_calendar_tz_batch(self, dt=None):
        """ Return a mapping { employee id : employee's effective schedule's (at dt) timezone }
        """
        employees_by_id = self.grouped('id')
        if not dt:
            calendars = self._get_calendars()
            return {
                emp_id: calendar.sudo().tz or employees_by_id[emp_id].tz \
                    for emp_id, calendar in calendars.items()
            }

        employees_by_tz = self.grouped(lambda emp: emp._get_tz())

        employee_timezones = {}
        for tz, employee_ids in employees_by_tz.items():
            date_at = timezone(tz).localize(dt).date()
            calendars = self._get_calendars(date_at)
            employee_timezones |= {
                emp_id: cal.sudo().tz or employees_by_id[emp_id].tz \
                    for emp_id, cal in calendars.items()
            }
        return employee_timezones

    def _get_calendars(self, date_from=None):
        res = super()._get_calendars(date_from=date_from)
        if not date_from:
            return res

        date_from = fields.Date.to_date(date_from)
        for employee in self:
            employee_versions = employee.version_ids.filtered(lambda v: v._is_in_contract(date_from))
            if employee_versions:
                res[employee.id] = employee_versions[0].resource_calendar_id.sudo(False)
        return res

    def _get_calendar_periods(self, start, stop):
        """
        :param datetime start: the start of the period
        :param datetime stop: the stop of the period
        """
        calendar_periods_by_employee = defaultdict(list)
        for employee in self.sudo():
            for version in employee._get_versions_with_contract_overlap_with_period(start.date(), stop.date()):
                # if employee is under fully flexible contract, use timezone of the employee
                calendar_tz = timezone(version.resource_calendar_id.tz) if version.resource_calendar_id else timezone(employee.resource_id.tz)
                date_start = datetime.combine(
                    version.date_start,
                    time(0, 0, 0)
                ).replace(tzinfo=calendar_tz).astimezone(utc)
                if version.date_end:
                    date_end = datetime.combine(
                        version.date_end + relativedelta(days=1),
                        time(0, 0, 0)
                    ).replace(tzinfo=calendar_tz).astimezone(utc)
                else:
                    date_end = stop
                calendar_periods_by_employee[employee].append(
                    (max(date_start, start), min(date_end, stop), version.resource_calendar_id))
        return calendar_periods_by_employee

    @api.model
    def _get_all_versions_with_contract_overlap_with_period(self, date_from, date_to):
        """
        Returns the versions of all employees between date_from and date_to
        that have at least 1 day in contract during that period
        """
        all_employees = self.search(['|', ('active', '=', True), ('active', '=', False)])
        return all_employees._get_versions_with_contract_overlap_with_period(date_from, date_to)

    def _get_unusual_days(self, date_from, date_to=None):
        date_from_date = datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S').date()
        date_to_date = datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S').date() if date_to else None
        employee_versions = self.env['hr.version'].sudo().search([('employee_id', '=', self.id)]).filtered(
            lambda v: v._is_overlapping_period(date_from_date, date_to_date))
        if not employee_versions:
            # Checking the calendar directly allows to not grey out the leaves taken
            # by the employee or fallback to the company calendar
            return (self.resource_calendar_id or self.env.company.resource_calendar_id)._get_unusual_days(
                datetime.combine(fields.Date.from_string(date_from), time.min).replace(tzinfo=UTC),
                datetime.combine(fields.Date.from_string(date_to), time.max).replace(tzinfo=UTC),
                self.company_id,
            )
        unusual_days = {}
        for version in employee_versions:
            tmp_date_from = max(date_from_date, version.date_start)
            tmp_date_to = min(date_to_date, version.date_end) if version.date_end else date_to_date
            unusual_days.update(version.resource_calendar_id.sudo(False)._get_unusual_days(
                datetime.combine(fields.Date.from_string(tmp_date_from), time.min).replace(tzinfo=UTC),
                datetime.combine(fields.Date.from_string(tmp_date_to), time.max).replace(tzinfo=UTC),
                self.company_id,
            ))
        return unusual_days

    def _employee_attendance_intervals(self, start, stop, lunch=False):
        self.ensure_one()
        if not lunch:
            return self._get_expected_attendances(start, stop)
        else:
            valid_versions = self.sudo()._get_versions_with_contract_overlap_with_period(start.date(), stop.date())
            if not valid_versions:
                calendar = self.resource_calendar_id or self.company_id.resource_calendar_id
                return calendar._attendance_intervals_batch(start, stop, self.resource_id, lunch=True)[self.resource_id.id]
            employee_tz = timezone(self.tz) if self.tz else None
            duration_data = Intervals()
            for version in valid_versions:
                version_start = datetime.combine(version.date_start, time.min, employee_tz)
                version_end = datetime.combine(version.date_end or date.max, time.max, employee_tz)
                calendar = version.resource_calendar_id or version.company_id.resource_calendar_id
                lunch_intervals = calendar._attendance_intervals_batch(
                    max(start, version_start),
                    min(stop, version_end),
                    resources=self.resource_id,
                    lunch=True)[self.resource_id.id]
                duration_data = duration_data | lunch_intervals
            return duration_data

    def _get_expected_attendances(self, date_from, date_to):
        self.ensure_one()
        valid_versions = self.sudo()._get_versions_with_contract_overlap_with_period(date_from.date(), date_to.date())
        employee_tz = timezone(self.tz) if self.tz else None
        if not valid_versions:
            calendar = self.resource_calendar_id or self.company_id.resource_calendar_id
            calendar_intervals = calendar._work_intervals_batch(
                date_from,
                date_to,
                tz=employee_tz,
                resources=self.resource_id,
                compute_leaves=True,
                domain=[('company_id', 'in', [False, self.company_id.id])])[self.resource_id.id]
            return calendar_intervals
        duration_data = Intervals()
        for version in valid_versions:
            version_start = datetime.combine(version.date_start, time.min, employee_tz)
            version_end = datetime.combine(version.date_end or date.max, time.max, employee_tz)
            calendar = version.resource_calendar_id or version.company_id.resource_calendar_id
            version_intervals = calendar._work_intervals_batch(
                                    max(date_from, version_start),
                                    min(date_to, version_end),
                                    tz=employee_tz,
                                    resources=self.resource_id,
                                    compute_leaves=True)[self.resource_id.id]
            duration_data = duration_data | version_intervals
        return duration_data

    def _get_calendar_attendances(self, date_from, date_to):
        self.ensure_one()
        valid_versions = self.sudo()._get_versions_with_contract_overlap_with_period(date_from.date(), date_to.date())
        employee_tz = timezone(self.tz) if self.tz else None
        if not valid_versions:
            calendar = self.resource_calendar_id or self.company_id.resource_calendar_id
            return calendar.with_context(employee_timezone=employee_tz).get_work_duration_data(
                date_from,
                date_to,
                domain=[('company_id', 'in', [False, self.company_id.id])])
        duration_data = {'days': 0, 'hours': 0}
        for version in valid_versions:
            version_start = datetime.combine(version.date_start, time.min, employee_tz)
            version_end = datetime.combine(version.date_end or date.max, time.max, employee_tz)
            calendar = version.resource_calendar_id or version.company_id.resource_calendar_id
            version_duration_data = calendar\
                .with_context(employee_timezone=employee_tz)\
                .get_work_duration_data(
                    max(date_from, version_start),
                    min(date_to, version_end),
                    domain=[('company_id', 'in', [False, version.company_id.id])])
            duration_data['days'] += version_duration_data['days']
            duration_data['hours'] += version_duration_data['hours']
        return duration_data

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Employees'),
            'template': '/hr/static/xls/hr_employee.xls'
        }]

    def _get_age(self, target_date=None):
        self.ensure_one()
        if target_date is None:
            target_date = fields.Date.context_today(self.env.user)
        return relativedelta(target_date, self.birthday).years if self.birthday else 0

    def _get_departure_date(self):
        # Primarily used in the archive wizard
        # to pick a good default for the departure date
        self.ensure_one()
        if self.date_end and self.date_end < fields.Date.today():
            return self.departure_date
        return False

    def _get_versions_with_contract_overlap_with_period(self, date_from, date_to):
        """
        Returns the versions of the employee between date_from and date_to
        that have at least 1 day in contract during that period
        """
        return self.env['hr.version'].search([
            ('employee_id', 'in', self.ids), ('contract_date_start', '!=', False), ('contract_date_start', '<=', date_to),
            '|', ('contract_date_end', '>=', date_from), ('contract_date_end', '=', False),
        ])

    def get_avatar_card_data(self, fields):
        return self.read(fields)
    # ---------------------------------------------------------
    # Messaging
    # ---------------------------------------------------------

    def _phone_get_number_fields(self):
        return ['mobile_phone']

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['work_contact_id', 'user_partner_id']

    def action_open_versions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.employee_id.name + ' Versions',
            'path': 'versions',
            'res_model': 'hr.version',
            'view_mode': 'list,graph,pivot',
            'views': [(self.env.ref('hr.hr_version_list_view').id, 'list'), (False, 'graph'), (False, 'pivot')],
            'domain': [('employee_id', '=', self.employee_id.id)],
            'search_view_id': self.env.ref('hr.hr_version_search_view').id
        }

    def action_new_contract(self):
        self.ensure_one()
        if not self.contract_date_end:
            raise UserError(self.env._("Before creating a new contract, close the current one by setting an end date."))
        if self.current_date_version <= self.contract_date_end:
            raise UserError(self.env._("Before creating a new contract, create a version that is set after the contract end date"))
        self.write({
            'contract_date_start': False,
            'contract_date_end': False,
        })

    def _get_store_avatar_card_fields(self, target):
        employee_fields = [
            "company_id",
            Store.One("department_id", ["name"]),
            "work_email",
            Store.One("work_location_id", ["location_type", "name"]),
            "work_phone",
        ]
        user = target.get_user(self.env)
        if user.has_group("hr.group_hr_user"):
            # job_title is not a field of hr.employee.public, but it is a field of hr.employee
            employee_fields.append("job_title")
        # HACK: fetch the employee fields from employees to retrieve hr.employee.public fields if no access to hr.employee
        if len(self) > 0:
            self.fetch([
                field.field_name if isinstance(field, Store.Attr) else field
                for field in employee_fields
            ])
        return employee_fields
