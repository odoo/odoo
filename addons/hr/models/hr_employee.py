# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from random import choice
from string import digits
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, DAILY
from markupsafe import Markup

from odoo import api, Command, fields, models, tools
from odoo.exceptions import AccessError, RedirectWarning, UserError, ValidationError
from odoo.fields import Domain
from odoo.models import Query
from odoo.tools import SQL, convert, format_date, format_time
from odoo.tools.float_utils import float_is_zero
from odoo.tools.intervals import Intervals
from odoo.tools.misc import SENTINEL

from odoo.addons.hr.models.hr_version import format_date_abbr
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.resource.models.utils import extract_comodel_domain, filter_map_domain


from .hr_employee_location import DAYS

# This sentinel object, when in the context, provides read access to the
# model 'hr.employee' in certain situations, like when setting a many2many
# field for users that don't have access to `hr.employee`.
_ALLOW_READ_HR_EMPLOYEE = object()


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
    _order = 'name, id'
    _inherit = ['mail.thread.main.attachment', 'mail.thread.phone', 'mail.activity.mixin', 'resource.mixin', 'avatar.mixin']
    _mail_post_access = 'read'
    _mailing_enabled = True
    _primary_email = 'work_email'
    _inherits = {'hr.version': 'version_id'}
    _check_inherits_access = False

    # versions
    version_id = fields.Many2one(
        'hr.version',
        string="Employee Record",
        compute='_compute_version_id',
        search='_search_version_id',
        compute_sql='_compute_sql_version_id',
        ondelete='cascade',  # FIXME: cascade but not store to avoid Error => "Field definition for _inherits ..."
        required=True,
        store=False,
        compute_sudo=True,
    )
    current_version_id = fields.Many2one(
        'hr.version',
        string="Current Employee Record",
        compute='_compute_current_version_id',
        store=True,
        index=True,
        bypass_search_access=True,
    )
    current_date_version = fields.Date(
        string="Current Date Employee Record",
        related="current_version_id.date_version",
        groups="hr.group_hr_user"
    )
    version_ids = fields.One2many(
        'hr.version',
        'employee_id',
        string='Employee Records',
        groups="hr.group_hr_user",
        required=True
    )
    versions_count = fields.Integer(string="Employee Records Count", compute='_compute_versions_count', groups="hr.group_hr_user")
    version_revision = fields.Char(compute="_compute_version_revision", groups="hr.group_hr_user")

    contract_template_id = fields.Many2one(
        'hr.version',
        groups="hr.group_hr_user",
    )

    def _get_hr_responsible_domain(self):
        return "[('share', '=', False), ('company_ids', 'in', company_id), ('all_group_ids', 'in', %s)]" % self.env.ref('hr.group_hr_user').id

    hr_responsible_id = fields.Many2one(related='version_id.hr_responsible_id', readonly=False, inherited=True, domain=lambda self: self.env['hr.version']._get_hr_responsible_domain(), groups="hr.group_hr_user")

    @api.model
    def _lang_get(self):
        return self.env['res.lang'].get_installed()

    # resource and user
    # required on the resource, make sure required="True" set in the view
    name = fields.Char(string="Employee Name", related='resource_id.name', store=True, readonly=False, tracking=True)
    resource_id = fields.Many2one('resource.resource', required=True)
    # required because the mixin already creates it so it is not related to the version_id
    resource_calendar_id = fields.Many2one(
        related='version_id.resource_calendar_id',
        inherited=True,
        index=False,
        store=False,
        domain="['|', ('company_id', '=', False), ('company_id.id', 'parent_of', company_id)]")
    user_id = fields.Many2one(
        'res.users', 'User',
        related='resource_id.user_id',
        store=True,
        readonly=False,
        check_company=True,
        precompute=True,
        index='btree_not_null',
        ondelete='restrict',
        copy=False
    )
    user_partner_id = fields.Many2one(related="user_id.partner_id", related_sudo=False, string="User's partner")
    share = fields.Boolean(related="user_id.share")
    phone = fields.Char(related="user_id.phone")
    email = fields.Char(related="user_id.email")
    hr_presence_state = fields.Selection([
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('out_of_working_hour', 'Off-Hours')], compute='_compute_presence_state', compute_sql='_compute_sql_presence_state', compute_sudo=False, default='out_of_working_hour')
    is_off_hours = fields.Boolean(compute='_compute_is_off_hours')
    last_activity = fields.Date(compute="_compute_last_activity")
    last_activity_time = fields.Char(compute="_compute_last_activity")
    hr_icon_display = fields.Selection([
        ('presence_present', 'Present'),
        ('presence_out_of_working_hour', 'Off-Hours'),
        ('presence_absent', 'Absent'),
        ('presence_home', 'At Home'),
        ('presence_office', 'At Office'),
        ('presence_other', 'At Other'),
        ('presence_undetermined', 'Undetermined')], compute='_compute_presence_icon')
    show_hr_icon_display = fields.Boolean(compute='_compute_presence_icon')
    newly_hired = fields.Boolean('Newly Hired', compute='_compute_newly_hired', search='_search_newly_hired')

    active = fields.Boolean('Active', related='resource_id.active', default=True, store=True, readonly=False)
    company_id = fields.Many2one('res.company', required=True, tracking=True)
    company_country_id = fields.Many2one('res.country', 'Company Country', related='company_id.country_id', readonly=True, groups="base.group_system,hr.group_hr_user")
    company_country_code = fields.Char(related='company_country_id.code', depends=['company_country_id'], readonly=True, groups="base.group_system,hr.group_hr_user", string='Company Country Code')
    parent_company_id = fields.Many2one(related="company_id.parent_id", groups="hr.group_hr_user", readonly=True)
    work_phone = fields.Char('Work Phone', store=True, readonly=False, tracking=True, compute="_compute_work_contact_details", inverse='_inverse_work_contact_details')
    mobile_phone = fields.Char('Work Mobile')
    work_phone_sanitized = fields.Char(compute='_compute_phone_companion_fields', store=False, export_string_translation=False)
    work_phone_formatted = fields.Char(compute='_compute_phone_companion_fields', store=False, export_string_translation=False)
    mobile_phone_sanitized = fields.Char(compute='_compute_phone_companion_fields', store=False, export_string_translation=False)
    mobile_phone_formatted = fields.Char(compute='_compute_phone_companion_fields', store=False, export_string_translation=False)
    # Restrict the `mail.thread.phone` mixin's non-stored helpers to HR users.
    # On hr.employee, anything readable by a regular internal user must also
    # be on hr.employee.public; tightening the access here keeps that
    # invariant intact without special-casing these fields elsewhere.
    phone_blacklisted = fields.Boolean(groups='hr.group_hr_user')
    phone_sanitized_blacklisted = fields.Boolean(groups='hr.group_hr_user')
    phone_mobile_search = fields.Char(groups='hr.group_hr_user')
    work_email = fields.Char('Work Email', compute="_compute_work_contact_details", store=True, inverse='_inverse_work_contact_details')
    work_contact_id = fields.Many2one('res.partner', 'Work Contact', copy=False, index='btree_not_null')
    # private info
    legal_name = fields.Char(compute='_compute_legal_name', store=True, readonly=False, groups="hr.group_hr_user", help="The employee's official name as per government-issued or legal documents.")
    split_legal_name = fields.Boolean(compute='_compute_split_legal_name', groups="hr.group_hr_user", help="Indicates whether the legal name is split into first and last name fields based on the employee's country.")
    private_phone = fields.Char(string="Private Phone", groups="hr.group_hr_user")
    private_phone_sanitized = fields.Char(compute='_compute_restricted_phone_companion_fields', store=False, export_string_translation=False, groups='hr.group_hr_user')
    private_phone_formatted = fields.Char(compute='_compute_restricted_phone_companion_fields', store=False, export_string_translation=False, groups='hr.group_hr_user')
    private_email = fields.Char(string="Private Email", groups="hr.group_hr_user")
    lang = fields.Selection(selection=_lang_get, string="Lang", groups="hr.group_hr_user")
    place_of_birth = fields.Char('Place of Birth', groups="hr.group_hr_user", tracking=True)
    country_of_birth = fields.Many2one('res.country', string="Country of Birth", groups="hr.group_hr_user", tracking=True)
    birthday = fields.Date('Birthday', groups="hr.group_hr_user", tracking=True)
    birthday_public_display = fields.Boolean('Show Birthday To Employees', groups="hr.group_hr_user", default=False)
    birthday_public_display_string = fields.Char("Public Date of Birth", compute="_compute_birthday_public_display_string", default="hidden")
    age = fields.Integer('Age', groups='hr.group_hr_user', compute='_compute_age')

    # For birthday group by month
    birthday_month = fields.Selection(
        selection=[
            ('0', "Not specified"),  # key named '0' to make the "Not specified" column appear first to the left in grouped kanban view
            ('1', "January"),
            ('2', "February"),
            ('3', "March"),
            ('4', "April"),
            ('5', "May"),
            ('6', "June"),
            ('7', "July"),
            ('8', "August"),
            ('9', "September"),
            ('10', "October"),
            ('11', "November"),
            ('12', "December"),
        ],
        string="Birthday Month",
        store=True,
        compute='_compute_birthday_month',
        groups="hr.group_hr_user"
    )

    bank_account_ids = fields.Many2many(
        'res.partner.bank',
        relation='employee_bank_account_rel',
        column1='employee_id',
        column2='bank_account_id',
        domain="[('partner_id', '=', work_contact_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        groups="hr.group_hr_user",
        copy=False,
        tracking=True,
        string='Bank Accounts',
        help='Employee bank accounts to pay salaries')
    is_trusted_bank_account = fields.Boolean(compute="_compute_is_trusted_bank_account", groups="hr.group_hr_user")
    primary_bank_account_id = fields.Many2one('res.partner.bank', compute="_compute_primary_bank_account_id", groups="hr.group_hr_user")
    has_multiple_bank_accounts = fields.Boolean(compute="_compute_has_multiple_bank_accounts", default=False, groups="hr.group_hr_user")
    salary_distribution = fields.Json(string="Salary Distribution", compute='_sync_salary_distribution', groups='hr.group_hr_user', store=True, readonly=False)
    """
    {
    `bank_account_id`: {
        'sequence': int,
        'amount': float,
        'amount_is_percentage': boolean,
        }
    }
    """

    permit_no = fields.Char('Work Permit No', groups="hr.group_hr_user", tracking=True)
    visa_no = fields.Char('Visa No', groups="hr.group_hr_user", tracking=True)
    visa_expire = fields.Date('Visa Expiration Date', groups="hr.group_hr_user", tracking=True)
    work_permit_expiration_date = fields.Date('Work Permit Expiration Date', groups="hr.group_hr_user", tracking=True)
    has_work_permit = fields.Binary(string="Work Permit", groups="hr.group_hr_user")
    work_permit_scheduled_activity = fields.Boolean(default=False, groups="hr.group_hr_user")
    work_permit_name = fields.Char('work_permit_name', compute='_compute_work_permit_name', groups="hr.group_hr_user")
    certificate = fields.Selection(selection='_get_certificate_selection', string='Certificate Level', groups="hr.group_hr_user", tracking=True)
    study_field = fields.Char("Field of Study", groups="hr.group_hr_user", tracking=True)
    emergency_contact = fields.Char(groups="hr.group_hr_user", tracking=True)
    emergency_phone = fields.Char(groups="hr.group_hr_user", tracking=True)
    # HR-only companions for the phone widget; computed apart from work/mobile
    # (see _compute_restricted_phone_companion_fields) to keep the group invariant.
    emergency_phone_sanitized = fields.Char(compute='_compute_restricted_phone_companion_fields', store=False, export_string_translation=False, groups='hr.group_hr_user')
    emergency_phone_formatted = fields.Char(compute='_compute_restricted_phone_companion_fields', store=False, export_string_translation=False, groups='hr.group_hr_user')
    additional_note = fields.Text(string='Additional Note', groups="hr.group_hr_user", tracking=True)
    work_location_name = fields.Char("Work Location Name", compute="_compute_work_location_name")
    work_location_type = fields.Selection([
        ("home", "Home"),
        ("office", "Office"),
        ("other", "Other")], compute="_compute_work_location_type", tracking=True)

    # Since groups don't naturally propagate to related fields (see _add_inherited_fields in model_classes.py),
    # we explicitly redefine some version fields on the employee model to enforce access rights.
    #
    # However, redefining them bypasses the standard _inherits mapping.
    # This causes the ORM to update them via inverse methods after creation, which breaks database constraints.
    # Adding inherited=True solves this by simulating the standard _inherits behavior.
    # It ensures these fields are injected directly into the version's create dictionary (vals),
    # so constraints pass right away without having to hack the employee methods.
    #
    # This change did cause a side effect: an AccessError.
    # When fetching missing default values for the version,
    # the ORM blindly included these restricted fields without checking user groups.
    # The extra fix just strips those restricted fields out of the vals before the create method crashes,
    # keeping everything safe and working.
    first_contract_date = fields.Date(compute='_compute_first_contract_date', groups="hr.group_hr_user", store=True,
                                    help="The date of the first contract of the employee in the company.")
    contract_date_start = fields.Date(readonly=False, related="version_id.contract_date_start", inherited=True, groups="hr.group_hr_user")
    contract_date_end = fields.Date(readonly=False, related="version_id.contract_date_end", inherited=True, groups="hr.group_hr_user")
    fixed_term = fields.Boolean(readonly=False, related="version_id.fixed_term", inherited=True, groups="hr.group_hr_user")
    trial_date_end = fields.Date(readonly=False, related="version_id.trial_date_end", inherited=True, groups="hr.group_hr_user")
    date_start = fields.Date(related='version_id.date_start', inherited=True, groups="hr.group_hr_user")
    date_end = fields.Date(related='version_id.date_end', inherited=True, groups="hr.group_hr_user")
    is_current = fields.Boolean(related='version_id.is_current', inherited=True, groups="hr.group_hr_user")
    is_past = fields.Boolean(related='version_id.is_past', inherited=True, groups="hr.group_hr_user")
    is_future = fields.Boolean(related='version_id.is_future', inherited=True, groups="hr.group_hr_user")
    is_in_contract = fields.Boolean(related='version_id.is_in_contract', inherited=True, groups="hr.group_hr_user")
    structure_type_id = fields.Many2one(readonly=False, related='version_id.structure_type_id', inherited=True, groups="hr.group_hr_manager")
    employee_type_id = fields.Many2one(readonly=False, related='version_id.employee_type_id', inherited=True, groups="hr.group_hr_manager")
    hourly_cost = fields.Monetary('Hourly Cost', groups="hr.group_hr_user", tracking=True)
    nationality_country_code = fields.Char(
        string='Nationality',
        related='version_id.country_id.code',
        groups="hr.group_hr_user"
    )
    # Direct subordinates
    parent_id = fields.Many2one('hr.employee', 'Manager', tracking=True, index=True,
                                domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]")
    child_ids = fields.One2many('hr.employee', 'parent_id', string='Direct subordinates', domain=[('active', '=', True)])
    child_count = fields.Integer('Direct Subordinates Count', compute='_compute_child_count',
        recursive=True, compute_sudo=True)

    # Indirect subordinates
    subordinate_ids = fields.One2many('hr.employee', string='Subordinates', compute='_compute_subordinates',
        help="Direct and indirect subordinates", compute_sudo=True)
    is_subordinate = fields.Boolean(compute="_compute_is_subordinate", search="_search_is_subordinate")
    child_all_count = fields.Integer('Indirect Subordinates Count', compute='_compute_subordinates', recursive=True,
        store=False, compute_sudo=True)
    department_color = fields.Integer("Department Color", related="department_id.color")

    coach_id = fields.Many2one(
        'hr.employee', 'Coach', compute='_compute_coach', store=True, readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]",
        help='Select the "Employee" who is the coach of this employee.\n'
             'The "Coach" has no specific rights or responsibilities by default.')
    category_ids = fields.Many2many(
        'hr.employee.category', 'employee_category_rel',
        'employee_id', 'category_id', groups="hr.group_hr_user",
        string='Tags')
    tz = fields.Selection(readonly=False, related="version_id.tz", inherited=True, tracking=True)
    # misc
    color = fields.Integer('Color Index', default=0)
    barcode = fields.Char(string="Badge ID", help="ID used for employee identification.", groups="hr.group_hr_user", copy=False)
    pin = fields.Char(string="PIN", groups="hr.group_hr_user", copy=False,
        help="PIN used to Check In/Out in the Kiosk Mode of the Attendance application (if enabled in Configuration) and to change the cashier in the Point of Sale application.")
    message_main_attachment_id = fields.Many2one(groups="hr.group_hr_user")
    id_card = fields.Binary(string="ID Card Copy", groups="hr.group_hr_user")
    driving_license = fields.Binary(string="Driving License", groups="hr.group_hr_user")
    id_card_name = fields.Char(groups="hr.group_hr_user")
    driving_license_name = fields.Char(groups="hr.group_hr_user")
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True, groups="hr.group_hr_user")
    related_partners_count = fields.Integer(compute="_compute_related_partners_count", groups="hr.group_hr_user")
    # properties
    employee_properties = fields.Properties('Properties', definition='company_id.employee_properties_definition', precompute=False, groups="hr.group_hr_user")

    # departure
    departure_id = fields.Many2one(related='version_id.departure_id', inherited=True,
        readonly=False, groups="hr.group_hr_user")
    departure_reason_id = fields.Many2one(related='version_id.departure_reason_id', inherited=True,
        readonly=False, groups="hr.group_hr_user")
    departure_description = fields.Html(related='version_id.departure_description', inherited=True,
        readonly=False, groups="hr.group_hr_user")
    dismissal_date = fields.Date(related='version_id.dismissal_date', inherited=True,
        readonly=False, groups="hr.group_hr_user")
    departure_date = fields.Date(related='version_id.departure_date', inherited=True,
        readonly=False, groups="hr.group_hr_user")
    departure_action_date = fields.Date(related='version_id.departure_action_date', inherited=True,
        readonly=False, groups="hr.group_hr_user")
    departure_apply_immediately = fields.Boolean(related='version_id.departure_apply_immediately', inherited=True,
        groups="hr.group_hr_user")
    departure_apply_date = fields.Date(related='version_id.departure_apply_date', inherited=True,
        groups="hr.group_hr_user")

    # mail.activity.mixin
    activity_ids = fields.One2many(groups="hr.group_hr_user")
    activity_state = fields.Selection(groups="hr.group_hr_user")
    activity_user_id = fields.Many2one(groups="hr.group_hr_user")
    activity_type_id = fields.Many2one(groups="hr.group_hr_user")
    activity_type_icon = fields.Char(groups="hr.group_hr_user")
    activity_plans_ids = fields.Many2many(groups="hr.group_hr_user")
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

    monday_location_id = fields.Many2one('hr.work.location', string='Monday')
    tuesday_location_id = fields.Many2one('hr.work.location', string='Tuesday')
    wednesday_location_id = fields.Many2one('hr.work.location', string='Wednesday')
    thursday_location_id = fields.Many2one('hr.work.location', string='Thursday')
    friday_location_id = fields.Many2one('hr.work.location', string='Friday')
    saturday_location_id = fields.Many2one('hr.work.location', string='Saturday')
    sunday_location_id = fields.Many2one('hr.work.location', string='Sunday')
    exceptional_location_id = fields.Many2one(
        'hr.work.location', string='Current',
        compute='_compute_exceptional_location_id',
        help='This is the exceptional, non-weekly, location set for today.', groups="hr.group_hr_user")
    today_location_name = fields.Char()

    # Display-only mirror of the linked user's invitation/activation status.
    # Read-only: the status is driven by user actions (see action_* below), not
    # by writing the computed res.users.state directly.
    user_state = fields.Selection(related='user_id.state', string="User Status", groups="hr.group_hr_user")

    # skills and resume
    resume_line_ids = fields.One2many('hr.resume.line', 'employee_id', string="Resume lines")
    employee_skill_ids = fields.One2many('hr.employee.skill', 'employee_id', string="Skills",
        domain=[('skill_type_id.active', '=', True)])
    current_employee_skill_ids = fields.One2many('hr.employee.skill',
        compute='_compute_current_employee_skill_ids', readonly=False)
    skill_ids = fields.Many2many('hr.skill', compute='_compute_skill_ids', store=True, groups="hr.group_hr_user")
    certification_ids = fields.One2many('hr.employee.skill', compute='_compute_certification_ids', readonly=False)
    display_certification_page = fields.Boolean(compute="_compute_display_certification_page")

    _barcode_uniq = models.Constraint(
        'unique (barcode)',
        'The Badge ID must be unique, this one is already assigned to another employee.',
    )
    _user_uniq = models.Constraint(
        'unique (user_id, company_id)',
        'A user cannot be linked to multiple employees in the same company.',
    )

    @api.model
    def _get_current_day_location_field(self):
        """Return the name of today's weekly work location field, e.g. ``'monday_location_id'``.

        "Today" is evaluated in the user's timezone (``fields.Date.context_today``).

        :rtype: str
        """
        return DAYS[fields.Date.context_today(self).weekday()]

    def _prepare_create_values(self, vals_list):
        """Drop the values of inherited ``hr.version`` fields the current user cannot write.

        Default values of version fields restricted to other groups (e.g. ``wage``
        for non-managers) would otherwise make the creation of the delegated
        version raise an ``AccessError``. Values of employee fields are kept as is.
        """
        result = super()._prepare_create_values(vals_list)
        new_vals_list = []
        Version = self.env['hr.version']
        version_fields = [fname for fname, field in Version._fields.items() if Version.has_field_access(field, 'write')]
        for vals in result:
            employee_vals = {}
            version_vals = {}
            for fname, value in vals.items():
                employee_field = self._fields.get(fname)
                if not (employee_field and employee_field.inherited and employee_field.related_field.model_name == 'hr.version'):
                    employee_vals[fname] = value
                else:
                    version_vals[fname] = value
            new_vals_list.append({
                **employee_vals,
                **{k: v for k, v in version_vals.items() if k in version_fields},
            })
        return new_vals_list

    @api.depends('employee_skill_ids')
    def _compute_current_employee_skill_ids(self):
        current_employee_skill_by_employee = self.employee_skill_ids.get_current_skills_by_employee()
        for employee in self:
            employee.current_employee_skill_ids = current_employee_skill_by_employee[employee.id]

    @api.depends('employee_skill_ids.skill_id')
    def _compute_skill_ids(self):
        for employee in self:
            employee.skill_ids = employee.employee_skill_ids.skill_id

    @api.depends('employee_skill_ids')
    def _compute_certification_ids(self):
        for employee in self:
            employee.certification_ids = employee.employee_skill_ids.filtered('is_certification')

    def _compute_display_certification_page(self):
        self.display_certification_page = bool(self.env['hr.skill.type'].search_count([('is_certification', '=', True)], limit=1))

    @api.depends('bank_account_ids.allow_out_payment')
    def _compute_is_trusted_bank_account(self):
        for employee in self:
            employee.is_trusted_bank_account = employee.primary_bank_account_id.allow_out_payment

    @api.depends('bank_account_ids')
    def _compute_has_multiple_bank_accounts(self):
        for employee in self:
            if employee.bank_account_ids and len(employee.bank_account_ids) > 1:
                employee.has_multiple_bank_accounts = True
            else:
                employee.has_multiple_bank_accounts = False

    @api.depends('bank_account_ids.active')
    def _sync_salary_distribution(self):
        for employee in self:
            current_salary_distribution = employee.salary_distribution or {}
            current_ids = set(map(int, current_salary_distribution.keys()))
            account_ids = set(employee.bank_account_ids.ids)

            added_ids = account_ids - current_ids
            removed_ids = current_ids - account_ids
            unchanged_ids = account_ids & current_ids

            # Preserve existing data and order
            ordered = sorted([
                (int(i), data) for i, data in current_salary_distribution.items()
                if int(i) in unchanged_ids
            ], key=lambda x: (not x[1].get('amount_is_percentage'), x[1].get('sequence', float('inf'))))

            new_salary_distribution = {str(i): data for i, data in ordered}

            # Redistribute removed % to first item
            removed_percentage = sum(current_salary_distribution[str(i)]['amount']
                for i in removed_ids if str(i) in current_salary_distribution and current_salary_distribution[str(i)]['amount_is_percentage'])
            if removed_percentage and ordered:
                first_id = str(ordered[0][0])
                if new_salary_distribution[first_id]['amount_is_percentage']:
                    new_salary_distribution[first_id]['amount'] += removed_percentage

            # Add new entries with remaining %
            total_allocated = sum(d['amount'] for d in new_salary_distribution.values() if d['amount_is_percentage'])
            remaining = max(0.0, 100.0 - total_allocated)
            seq = max((d.get('sequence', 0) for d in new_salary_distribution.values()), default=0)
            amount = employee.currency_id.round(remaining / len(added_ids)) if added_ids else 0.0
            for i, new_id in enumerate(added_ids):
                seq += 1
                if i == len(added_ids) - 1:
                    amount = remaining
                new_salary_distribution[str(new_id)] = {
                    'amount': amount,
                    'amount_is_percentage': True,
                    'sequence': seq,
                }
                remaining -= amount

            employee.salary_distribution = new_salary_distribution

    @api.constrains('salary_distribution')
    def _check_salary_distribution(self):
        for employee in self:
            dist = employee.salary_distribution
            if not dist:
                continue

            total = 0
            check_total = False
            for ba_values in dist.values():
                amount = ba_values.get('amount')
                is_percentage = ba_values.get('amount_is_percentage', True)
                if is_percentage and (not isinstance(amount, (float, int)) or not (0 <= amount <= 100)):
                    raise ValidationError(self.env._("Each amount percentage must be a number between 0 and 100."))
                if is_percentage:
                    check_total = True
                    total += amount

            if check_total and not float_is_zero(total - 100.0, precision_digits=4):
                raise ValidationError(self.env._("Total salary distribution on bank accounts must be exactly 100%."))

    @api.model
    def _create(self, data_list):
        """Insert the employees, then link the version created by ``_inherits`` back to them.

        The ORM creates the delegated ``hr.version`` before the employee, so its
        ``employee_id`` can only be set (together with the inherited values) once
        the employee row exists.
        """
        versions = [vals['stored'].pop('version_id', None) for vals in data_list]
        result = super()._create(data_list)
        for (employee, version_id, vals) in zip(result, versions, data_list):
            version = self.env['hr.version'].browse(version_id)
            version.employee_id = employee.id
            version.write({**vals.get('inherited', {})['hr.version'], 'employee_id': employee.id})
        return result

    def _has_field_access(self, field, operation):
        # DISCLAIMER: Dirty hack to avoid having to create a bridge module to override only a
        # groups on a field which is not prefetched (because not stored) but would crash anyway
        # if we try to read them directly (very uncommon use case). Don't add your field on this
        # list if you can specify the group on the field directly (as all the other fields).
        return super()._has_field_access(field, operation) and (
            self.env.su
            or self.env.user.has_group("hr.group_hr_user")
            or field.name not in ('activity_calendar_event_id', 'rating_ids', 'message_has_sms_error')
        )

    def check_no_existing_contract(self, date):
        """Raise if the employee is already in contract on ``date``.

        Call it before :meth:`create_contract`. Single employee only.

        :param date: the date to check
        :type date: datetime.date or str
        :raise ValidationError: if a contract (of any active version) covers ``date``
        """
        if isinstance(date, str):
            date = fields.Date.from_string(date)
        if self._is_in_contract(date):
            raise ValidationError(self.env._("The employee is already in contract on %s. "
                                             "Please select a date outside existing contracts",
                                             format_date_abbr(self.env, date)))

    @api.onchange('contract_template_id')
    def _onchange_contract_template_id(self):
        if self.contract_template_id:
            template_company = self.contract_template_id.company_id
            whitelist = self.contract_template_id.with_company(template_company)._get_whitelist_fields_from_template()
            for field in self.contract_template_id._fields:
                if field in whitelist and not self.env['hr.version']._fields[field].related:
                    self[field] = self.contract_template_id[field]

    @api.onchange('contract_date_start')
    def _onchange_contract_date_start(self):
        if not self.contract_date_start:
            self.contract_date_end = False

    @api.onchange('contract_date_end')
    def _onchange_contract_date_end(self):
        for version in self:
            if not version.contract_date_end:
                version.fixed_term = False
            elif (
                version._origin.contract_date_start != version.contract_date_start
                and version._origin.contract_date_end != version.contract_date_end
            ):
                version.fixed_term = True

    @api.onchange("private_state_id")
    def _onchange_private_state_id(self):
        if self.private_state_id:
            self.private_country_id = self.private_state_id.country_id

    @api.model
    def _get_new_hire_field(self):
        """Return the name of the date(time) field used to compute ``newly_hired``.

        An employee is newly hired when this field is less than 90 days old.
        Override to use another field (default: ``'create_date'``).

        :rtype: str
        """
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

    @api.depends(*DAYS, 'exceptional_location_id', 'resource_calendar_id', 'hr_presence_state')
    def _compute_presence_icon(self):
        """Compute ``hr_icon_display`` and ``show_hr_icon_display`` (presence icon of kanban/avatar cards).

        Today's work location (exceptional location, else the weekday location)
        wins and gives ``presence_home``/``presence_office``/``presence_other``;
        otherwise the icon is ``'presence_' + hr_presence_state``, shown only for
        employees linked to a user. Overridden by e.g. ``hr_holidays`` and
        ``hr_attendance`` to add time off / attendance based icons.
        """
        dayfield = self._get_current_day_location_field()
        for employee in self:
            today_employee_location_id = employee.sudo().exceptional_location_id or employee[dayfield]
            if not today_employee_location_id:
                employee.hr_icon_display = 'presence_' + employee.hr_presence_state
                employee.show_hr_icon_display = bool(employee.user_id)
            else:
                employee.hr_icon_display = f'presence_{today_employee_location_id.location_type}'
                employee.show_hr_icon_display = True

    @api.depends('birthday')
    def _compute_birthday_month(self):
        for employee in self:
            employee.birthday_month = str(employee.birthday.month) if employee.birthday else '0'

    @api.depends('birthday')
    def _compute_age(self):
        for employee in self:
            employee.age = employee._get_age()

    @api.model
    def _get_certificate_selection(self):
        return [
            ('graduate', self.env._('Graduate')),
            ('bachelor', self.env._('Bachelor')),
            ('master', self.env._('Master')),
            ('doctor', self.env._('Doctor')),
            ('other', self.env._('Other')),
        ]

    @api.depends('version_ids.contract_date_start')
    def _compute_first_contract_date(self):
        for employee in self:
            employee.first_contract_date = employee._get_first_contract_date()

    def _get_first_versions(self, date_limit=date.max):
        """Return the active versions of the employee starting on or before ``date_limit``.

        :param datetime.date date_limit: upper bound on the versions ``date_start``
        :return: versions ordered by ``date_version``
        :rtype: hr.version
        """
        self.ensure_one()
        return self.version_ids.filtered(lambda c: c.date_start <= date_limit)

    def _get_last_consecutive_versions(self, date_limit=date.max):
        """Return the last uninterrupted block of versions starting on or before ``date_limit``.

        Starting from the latest version, earlier versions are included as long
        as there are no working hours (according to the earlier version's
        calendar) between the end of a version and the start of the next one
        (see :meth:`hr.version._has_work_hours_between_versions`). A gap of
        non-working days only (e.g. a weekend) does not break the block.

        Example: with versions 01/01-31/07 (3 versions, consecutive), then a
        working-days gap, then 01/09-20/11 (2 versions), only the last 2 are
        returned.

        Restricted to HR officers (or superuser). Single employee only.

        :param datetime.date date_limit: upper bound on the versions ``date_start``
        :return: versions ordered by ``date_start``
        :rtype: hr.version
        :raise AccessError: if the user is not an HR officer
        """
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group("hr.group_hr_user"):
            raise AccessError(self.env._("Only HR users can access first version date on an employee."))

        versions = self._get_first_versions(date_limit).sorted('date_start')
        # index of the earliest consecutive version
        first_version_index = len(versions) - 1

        while first_version_index > 0:
            if versions[first_version_index - 1]._has_work_hours_between_versions(versions[first_version_index]):
                break  # version_before is not consecutive with first_version
            first_version_index -= 1
        return versions[first_version_index:]

    def _get_first_version_date(self, date_limit=date.max):
        """Return the start date of the last uninterrupted block of versions.

        See :meth:`_get_last_consecutive_versions`.

        :param datetime.date date_limit: only consider versions starting on or before this date
        :return: the smallest ``date_start`` of the block, or ``False`` if no version
        :rtype: datetime.date or bool
        """
        versions = self._get_last_consecutive_versions(date_limit)
        return min(versions.mapped('date_start')) if versions else False

    def _get_first_contract_date(self, date_limit=date.max):
        """Return the first contract start date of the last uninterrupted block of versions.

        This is the value of the stored ``first_contract_date`` field (computed
        with the default ``date_limit``): the seniority start date, ignoring
        older contracts separated from the current ones by a gap with working
        days. See :meth:`_get_last_consecutive_versions`.

        :param datetime.date date_limit: only consider versions starting on or before this date
        :return: the smallest ``contract_date_start`` of the block, or ``False``
        :rtype: datetime.date or bool
        """
        versions = self._get_last_consecutive_versions(date_limit).filtered(lambda x: x.contract_date_start)
        return min(versions.mapped('contract_date_start')) if versions else False

    @api.depends('name')
    def _compute_legal_name(self):
        for employee in self:
            if not employee.legal_name:
                employee.legal_name = employee.name

    @api.model
    def _get_splitting_legal_name_countries(self):
        """Return the company country codes for which the legal name is split into first/last name.

        Hook for localizations (e.g. ``l10n_be_hr_payroll``); drives ``split_legal_name``.

        :rtype: list[str]
        """
        return []

    def _compute_split_legal_name(self):
        splitting_country_codes = self._get_splitting_legal_name_countries()
        for employee in self:
            employee.split_legal_name = employee.company_country_code in splitting_country_codes

    @api.depends('current_version_id')
    @api.depends_context('version_id')
    def _compute_version_id(self):
        """Compute ``version_id``, the version that the inherited (``_inherits``) fields read and write.

        It is ``current_version_id``, unless the context key ``version_id``
        holds the id of a version of the employee: the employee then reads and
        writes that version (this is how the form view displays and edits a
        past or future version)::

            employee.with_context(version_id=old_version.id).wage
        """
        context_version_id = self.env.context.get('version_id', False)
        context_version = self.env['hr.version'].browse(context_version_id).exists() if context_version_id else self.env['hr.version']

        for employee in self:
            if context_version.employee_id == employee:
                version = context_version
            else:
                version = employee.current_version_id
            employee.version_id = version

    def _compute_child_count(self):
        employee_read_group = self._read_group(
            [('parent_id', 'in', self.ids)],
            ['parent_id'],
            ['id:count'],
        )
        child_count_per_parent_id = dict(employee_read_group)
        for employee in self:
            employee.child_count = child_count_per_parent_id.get(employee._origin, 0)

    @api.depends_context('uid', 'company')
    @api.depends('parent_id')
    def _compute_is_subordinate(self):
        subordinates = self.env.user.employee_id.subordinate_ids
        if not subordinates:
            self.is_subordinate = False
        else:
            for employee in self:
                employee.is_subordinate = employee in subordinates

    def _search_is_subordinate(self, operator, value):
        if operator != 'in':
            return NotImplemented
        subordinates = self.env.user.employee_id.subordinate_ids
        return [('id', 'in', subordinates.ids)]

    def _get_subordinates(self, parents=None):
        """Return all direct and indirect subordinates (via ``child_ids``) of the employees in ``self``.

        Cycles in the hierarchy are supported (e.g. the CEO manages the CTO who
        manages the R&D department the CEO belongs to): employees already in
        ``parents`` or ``self`` are never returned. Only active subordinates are
        followed (``child_ids`` domain).

        :param parents: employees already visited, used by the recursion
        :type parents: hr.employee or None
        :rtype: hr.employee
        """
        if not parents:
            parents = self.env[self._name]

        indirect_subordinates = self.env[self._name]
        parents |= self
        direct_subordinates = self.child_ids - parents
        child_subordinates = direct_subordinates._get_subordinates(parents=parents) if direct_subordinates else self.browse()
        indirect_subordinates |= child_subordinates
        return indirect_subordinates | direct_subordinates

    @api.depends('child_ids', 'child_ids.child_all_count')
    def _compute_subordinates(self):
        for employee in self:
            employee.subordinate_ids = employee._get_subordinates()
            employee.child_all_count = len(employee.subordinate_ids)

    @api.depends(*DAYS, "exceptional_location_id", "version_id.work_location_id.name")
    def _compute_work_location_name(self):
        dayfield = self.env['hr.employee']._get_current_day_location_field()
        for employee in self:
            current_location = employee.exceptional_location_id or employee[dayfield]
            employee.work_location_name = current_location.name

    @api.depends(*DAYS, "exceptional_location_id", "version_id.work_location_id.location_type")
    def _compute_work_location_type(self):
        dayfield = self.env['hr.employee']._get_current_day_location_field()
        for employee in self:
            current_location = employee.exceptional_location_id or employee[dayfield]
            employee.work_location_type = current_location.location_type

    @api.depends('version_ids.date_version', 'version_ids.active')
    def _compute_current_version_id(self):
        """Compute the stored ``current_version_id``.

        The current version is the active version with the latest
        ``date_version`` on or before today (user's timezone); if all versions
        are in the future, the first one. Contract dates are not considered:
        the current version may be out of contract. Since "today" changes, the
        value is refreshed daily by :meth:`_cron_update_current_version_id`.
        """
        today = fields.Date.context_today(self)
        current_version_per_employee = {}
        for version in self.env['hr.version'].search_fetch(
            [
                ('employee_id', 'in', self.ids),
                ('date_version', '<=', today),
                ('active', '=', True),
            ],
            ['employee_id'],
            order='employee_id, date_version desc',
        ):
            current_version_per_employee.setdefault(version.employee_id.id, version)
        for employee in self:
            new_current_version = False
            if version := current_version_per_employee.get(employee.id):
                new_current_version = version
            elif employee.version_ids:
                new_current_version = employee.version_ids[0]
            # To not trigger computed properties if still the same version
            if employee.current_version_id != new_current_version:
                employee.current_version_id = new_current_version

    def _cron_update_current_version_id(self):
        """Recompute ``current_version_id`` of all active employees (daily cron).

        Needed because the current version depends on today's date: a future
        version only becomes current when this cron runs on or after its
        ``date_version``. The calendar and timezone of the employee's
        ``resource_id`` follow the new current version (computed fields).
        """
        self.search([])._compute_current_version_id()

    def _search_version_id(self, operator, value):
        if operator in ('any', 'any!'):
            return Domain('current_version_id', operator, value)
        domain = Domain('id', operator, value)
        return Domain('id', 'in', self.env['hr.version']._search(domain).select(SQL('employee_id')))

    def _compute_sql_version_id(self, table):
        # HACK required to make inherits work on a computed field
        # (could be a CASE WHEN with the version_id from the content for the current user)
        return table.current_version_id

    def _get_version(self, date=None):
        """Return the version in effect on ``date``.

        This is the active version with the latest ``date_version`` on or before
        ``date``. If ``date`` is before all versions, the first version is
        returned. Archived versions are only used when the employee has no
        active version. Contract dates are ignored: the result may be out of
        contract (check ``version._is_in_contract(date)`` if needed).
        Single employee only.

        :param date: the reference date, today (user's timezone) by default
        :type date: datetime.date or None
        :return: a single version, or an empty recordset if the employee has none
        :rtype: hr.version
        """
        self.ensure_one()
        if date is None:
            date = fields.Date.context_today(self)
        versions = self.version_ids.filtered(lambda v: v.active) or self.with_context(active_test=False).version_ids
        if not versions:
            return self.env['hr.version']
        filtered_versions = versions.filtered_domain([('date_version', '<=', date)])
        return max(filtered_versions, key=lambda v: v.date_version) if filtered_versions else versions[0]

    def create_version(self, values):
        """Create a new version of the employee, effective from ``values['date_version']``.

        The new version is a copy of the version in effect on that date (see
        :meth:`_get_version`) on which ``values`` are written. If ``values``
        does not specify them, the contract dates are those of the contract
        running on that date (``(False, False)`` if none). If a
        ``contract_date_end`` different from the running contract's end is
        given (with the same start), the end date is propagated to all versions
        of that contract. A ``contract_template_id`` in ``values`` is applied
        on the new version. Single employee only.

        Pitfall: if a version already exists with exactly this ``date_version``,
        it is returned **unchanged** (``values`` are not written).

        :param dict values: ``hr.version`` values; ``date_version`` (date,
            datetime or string) is mandatory
        :return: the new (or already existing) version
        :rtype: hr.version
        :raise ValueError: if ``date_version`` is missing
        :raise AccessError: if the user cannot write on the employee and the copied version
        """
        self.ensure_one()

        date = values.get('date_version', False)
        if not date:
            raise ValueError("date_version is required")

        if isinstance(date, str):
            date = fields.Date.to_date(date)
        elif isinstance(date, datetime):
            date = date.date()

        version_to_copy = self._get_version(date)
        if not version_to_copy:
            version_to_copy = self.env['hr.version'].search([
                ('employee_id', '=', self.id),
                ('active', '=', True),
            ], limit=1)
        if version_to_copy.date_version == date:
            return version_to_copy

        date_from, date_to = self.sudo()._get_contract_dates(date)
        contract_date_start = values.get('contract_date_start', date_from)
        contract_date_end = values.get('contract_date_end', date_to)
        employee_id = values.get('employee_id', self.id)

        if isinstance(contract_date_start, str):
            contract_date_start = fields.Date.to_date(contract_date_start)
        if isinstance(contract_date_end, str):
            contract_date_end = fields.Date.to_date(contract_date_end)

        if contract_date_start == date_from and contract_date_end != date_to:
            versions_sudo_to_sync = self.env['hr.version'].with_context(sync_contract_dates=True).sudo().search([
                ('employee_id', '=', employee_id),
                ('active', '=', True),
                ('contract_date_start', '=', date_from),
            ])
            if versions_sudo_to_sync:
                versions_sudo_to_sync.write({
                    'contract_date_end': contract_date_end,
                })
        self.check_access('write')
        version_to_copy.check_access('write')
        # to be sure even if the user has no access to certain fields, we can still copy the verison without any issues.
        copy_vals = {
            'date_version': date,
            'employee_id': employee_id,
            'contract_date_start': contract_date_start,
            'contract_date_end': contract_date_end,
            'fixed_term': bool(contract_date_end),
        }
        if 'active' in values:
            copy_vals['active'] = values['active']
        if calendar_id := values.get('resource_calendar_id'):
            copy_vals['resource_calendar_id'] = calendar_id
        # apply the changes on the new versions.
        new_version_vals = {
            field_name: field_value
            for field_name, field_value in values.items()
            if field_name not in copy_vals
        }
        version_fields = self.env['hr.version']._fields
        copy_vals = {
            k: v
            for k, v in version_to_copy.sudo().copy_data()[0].items()
            if not (k in new_version_vals and version_fields[k].type in ['one2many', 'many2many'])
        } | copy_vals
        new_version = self.env['hr.version'].sudo().create(copy_vals).sudo(False)
        with self.env.protecting([f for f_name, f in version_fields.items() if f_name not in new_version_vals and f.copy], new_version):
            new_version.write(new_version_vals)
        # Force recompute of fields possibly left stale by protecting() above (e.g. final_yearly_costs)
        with self.env.protecting([f for f_name, f in version_fields.items() if f_name in new_version_vals and f.compute and not f.readonly], new_version):
            new_version.modified(list(new_version_vals.keys()))
        if template_id := values.get('contract_template_id'):
            template = self.env['hr.version'].browse(template_id)
            template_vals = new_version.get_values_from_contract_template(template)
            if template_vals:
                new_version.write(template_vals)
        return new_version

    def create_contract(self, date):
        """Start a new contract on ``date`` and return the version carrying it.

        The contract starts on ``date`` and ends the day before the next future
        contract, or is open-ended (``contract_date_end = False``) if there is
        none. If a version already exists on ``date``, its contract dates are
        overwritten; otherwise a new version is created with
        :meth:`create_version` (copying the version in effect on ``date``).
        The caller must make sure the employee is not already in contract on
        ``date`` (see :meth:`check_no_existing_contract`). Single employee only.

        :param date: contract start date
        :type date: datetime.date or str
        :rtype: hr.version
        """
        # Here we can assume that there is no existing contract on the date given
        self.ensure_one()
        if date and isinstance(date, str):
            date = fields.Date.to_date(date)

        contracts = self._get_contract_versions(date)[self.id]
        future_contract_dates = [d for d in list(contracts.keys()) if d > date]
        new_contract_date_end = min(future_contract_dates) + relativedelta(days=-1) if future_contract_dates else False

        # There is already a version but with no contract defined on it so we simply write on it the dates
        if version_same_date := self.version_ids.filtered(lambda v: v.date_version == date):
            version_same_date.write({
                'contract_date_start': date,
                'contract_date_end': new_contract_date_end
            })
            return version_same_date

        return self.create_version({
            'date_version': date,
            'contract_date_start': date,
            'contract_date_end': new_contract_date_end
        })

    def _is_in_contract(self, date):
        """Return whether a contract of the employee covers ``date``.

        Based on the contract ranges (:meth:`_get_contract_dates`), not on a
        single version: unlike :meth:`hr.version._is_in_contract`, it answers
        ``True`` whatever the version in effect on ``date``. Single employee only.

        :param datetime.date date: the date to check
        :rtype: bool
        """
        return self._get_contract_dates(date) != (False, False)

    def _is_flexible(self, date=None):
        """Return whether the working schedule in effect on ``date`` is flexible.

        :param date: reference date (today by default), see :meth:`_get_version`
        :type date: datetime.date or None
        :rtype: bool
        """
        calendar = self._get_version(date).resource_calendar_id
        return bool(calendar) and calendar._is_flexible()

    def _is_fully_flexible(self, date=None):
        """Return whether the working schedule in effect on ``date`` is fully flexible.

        :param date: reference date (today by default), see :meth:`_get_version`
        :type date: datetime.date or None
        :rtype: bool
        """
        calendar = self._get_version(date).resource_calendar_id
        return bool(calendar) and calendar._is_fully_flexible()

    def _get_contracts(self, date_start=None, date_end=None, use_latest_version=True, domain=None):
        """Return one representative version per contract overlapping the period, per employee.

        Contracts are found with :meth:`_get_contract_versions`. For each
        contract, a single version is kept: with ``use_latest_version``, the
        version in effect on ``date_end`` (the last version of the contract if
        ``date_end`` is not given); otherwise the version in effect on
        ``date_start`` (the first version if not given). If no version of the
        contract has started yet on that date, its first version is used.

        :param date_start: start of the period (inclusive), unbounded if ``None``
        :type date_start: datetime.date or None
        :param date_end: end of the period (inclusive), unbounded if ``None``
        :type date_end: datetime.date or None
        :param bool use_latest_version: pick the version in effect at the end
            (``True``) or at the start (``False``) of the period
        :param domain: extra ``hr.version`` domain
        :type domain: list or Domain or None
        :return: ``{employee_id: hr.version}`` (one record per contract),
            a ``defaultdict`` returning an empty recordset for unknown ids
        :rtype: dict[int, hr.version]
        """
        contract_versions_by_employee = self._get_contract_versions(date_start, date_end, domain)
        contracts_by_employee = defaultdict(lambda: self.env["hr.version"])
        for employee_id in contract_versions_by_employee:
            for contract_versions in contract_versions_by_employee[employee_id].values():
                effective_date = date_end if use_latest_version else date_start
                if effective_date:
                    correct_versions = contract_versions.filtered(lambda v: v.date_version <= effective_date)
                    contracts_by_employee[employee_id] |= correct_versions[-1] if correct_versions else contract_versions[0]
                else:
                    contracts_by_employee[employee_id] |= contract_versions[-1] if use_latest_version else contract_versions[0]
        return contracts_by_employee

    def _get_contract_versions(self, date_start=None, date_end=None, domain=None):
        """Return the versions of the contracts overlapping the period, grouped by employee and contract.

        A contract is the set of active versions of an employee sharing the same
        ``contract_date_start``. A contract overlaps the period if
        ``contract_date_start <= date_end`` and its ``contract_date_end`` is
        empty or ``>= date_start``; all its versions are returned, even those
        whose own ``date_start``/``date_end`` lie outside the period.

        Pitfall: on an empty recordset, versions of **all** employees are returned.

        :param date_start: start of the period (inclusive), unbounded if ``None``
        :type date_start: datetime.date or None
        :param date_end: end of the period (inclusive), unbounded if ``None``
        :type date_end: datetime.date or None
        :param domain: extra ``hr.version`` domain
        :type domain: list or Domain or None
        :return: ``{employee_id: {contract_date_start: hr.version}}``, versions
            ordered by ``date_version`` (nested ``defaultdict``)
        :rtype: dict[int, dict[datetime.date, hr.version]]
        """
        version_domain = Domain('contract_date_start', '!=', False)
        if self.ids:
            version_domain &= Domain('employee_id', 'in', self.ids)
        elif not any(self._ids) and self._origin.ids:  # onchange
            version_domain &= Domain('employee_id', 'in', self._origin.ids)
        if date_start:
            version_domain &= Domain('contract_date_end', '=', False) | Domain('contract_date_end', '>=', date_start)
        if date_end:
            version_domain &= Domain('contract_date_start', '<=', date_end)
        if domain:
            version_domain &= domain
        all_versions = self.env['hr.version']._read_group(
            domain=version_domain,
            groupby=['employee_id', 'date_version:day'],
            aggregates=['id:recordset'],
        )
        contract_versions_by_employee = defaultdict(lambda: defaultdict(lambda: self.env["hr.version"]))
        for employee, _date_version, version in all_versions:
            first_version = next(iter(version), version)
            contract_versions_by_employee[employee.id][first_version.contract_date_start] |= version
        return contract_versions_by_employee

    def _get_all_contract_dates(self):
        """Return the contract periods of the employee, ordered by start date.

        One tuple per distinct ``(contract_date_start, contract_date_end)`` among
        the active versions. Single employee only.

        :return: ``[(date_from, date_to), ...]`` with inclusive dates;
            ``date_to`` is ``False`` for an open-ended contract
        :rtype: list[tuple[datetime.date, datetime.date | bool]]
        """
        self.ensure_one()
        return self.env['hr.version']._read_group(
            domain=[('employee_id', '=', self.id), ('contract_date_start', '!=', False)],
            groupby=['contract_date_start:day', 'contract_date_end:day'],
            order="contract_date_start:day")

    def _get_contract_dates(self, date):
        """Return the period of the contract covering ``date``.

        Single employee only.

        :param datetime.date date: the date to check
        :return: ``(date_from, date_to)`` (``date_to`` is ``False`` if open-ended),
            or ``(False, False)`` if not in contract on ``date``
        :rtype: tuple
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

    @api.depends('version_ids.write_date')
    def _compute_version_revision(self):
        for employee in self:
            employee.version_revision = ",".join(f"{v.id},{v.write_date!s}" for v in employee.version_ids)

    def _search_newly_hired(self, operator, value):
        if operator not in ('in', 'not in'):
            return NotImplemented
        new_hire_field = self._get_new_hire_field()
        new_hires = self.env['hr.employee'].sudo().search([
            (new_hire_field, '>', fields.Datetime.now() - timedelta(days=90))
        ])
        return [('id', operator, new_hires.ids)]

    def _create_work_contacts(self):
        """Create and link a work contact (``res.partner``) for each employee.

        The partner gets the employee's name, work email/phone, image and company.
        Called on employee creation for employees without ``work_contact_id``.

        :raise UserError: if an employee already has a work contact
        """
        if any(employee.work_contact_id for employee in self):
            raise UserError(self.env._('Some employee already has a work contact'))
        work_contacts = self.env['res.partner'].create([{
            'email': employee.work_email,
            'phone': employee.work_phone,
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
                if len(employee.work_contact_id.employee_ids) <= 1:
                    employee.work_phone = employee.work_contact_id.phone
                    employee.work_email = employee.work_contact_id.email

    def _inverse_work_contact_details(self):
        """Propagate ``work_email``/``work_phone`` to the work contact, creating it if missing.

        The partner is only updated when it is the work contact of this employee
        alone (the same partner can be shared by employees of several companies).
        Conversely, ``_compute_work_contact_details`` reads them from the partner.
        """
        employees_without_work_contact = self.env['hr.employee']
        for employee in self:
            if not employee.work_contact_id:
                employees_without_work_contact += employee
            else:
                if len(employee.work_contact_id.employee_ids) <= 1:
                    partner = employee.work_contact_id
                    if not employee.user_id and not partner.user_ids:
                        partner = partner.sudo()
                    partner.write({
                        'email': employee.work_email or employee.private_email,
                        'phone': employee.work_phone,
                    })
        if employees_without_work_contact:
            employees_without_work_contact.sudo()._create_work_contacts()

    # work_phone needs companion fields for the widget, but is not part of
    # the generic phone fields used for SMS/search/blacklist behavior.
    @api.depends(lambda self: ['work_phone'] + self._phone_get_sanitize_triggers())
    def _compute_phone_companion_fields(self):
        self._phone_update_companion_fields(('work_phone', 'mobile_phone'))

    # emergency_phone and private_phone are HR-only. Computing their companions
    # apart from the (ungrouped) work/mobile ones ensures reading work_phone's
    # companions never forces a read of these restricted fields for non-HR users.
    # Same sanitize triggers as the work/mobile compute so a country change
    # (company or fallback partner) re-formats these numbers too.
    @api.depends(lambda self: ['emergency_phone', 'private_phone'] + self._phone_get_sanitize_triggers())
    def _compute_restricted_phone_companion_fields(self):
        self._phone_update_companion_fields(('emergency_phone', 'private_phone'))

    def _get_employee_working_now(self):
        """Return the ids of the employees of ``self`` expected to work now.

        An employee is "working now" when their current working schedule has
        work intervals within the next hour (in the employee's timezone).
        Intervals are computed per calendar, so only company-wide leaves are
        considered, not the employee's own time off. Employees without
        calendar are never returned.

        :rtype: list[int]
        """
        return self._get_employee_working_at(fields.Datetime.now())

    def _get_employee_working_at(self, dt):
        """Same as :meth:`_get_employee_working_now`, at the naive UTC datetime ``dt``."""
        working_now = []
        # We loop over all the employee tz and the resource calendar_id to detect working hours in batch.
        for tz_info, employee_ids in self.filtered('resource_calendar_id').grouped('tz').items():
            calendar_by_employee = employee_ids.grouped('resource_calendar_id')
            tz = ZoneInfo(tz_info or 'UTC')
            from_datetime = dt.replace(tzinfo=UTC).astimezone(tz)
            to_datetime = from_datetime + timedelta(hours=1)
            for calendar_id, res_employee_ids in calendar_by_employee.items():
                # Getting work interval of the first is working. Functions called on resource_calendar_id
                # are waiting for singleton
                work_interval = calendar_id._work_intervals_batch(from_datetime, to_datetime)[False]
                # Employee that is not supposed to work have empty items.
                if len(work_interval._items) > 0:
                    # The employees should be working now according to their work schedule
                    working_now += res_employee_ids.ids
        return working_now

    def _get_next_working_change(self, after):
        """Return the first moment after ``after`` at which ``_get_employee_working_at`` may
        change for these employees, within a week, or None."""
        after_utc = after.replace(tzinfo=UTC)
        changes = []
        for tz_info, employees in self.filtered("resource_calendar_id").grouped("tz").items():
            from_datetime = after_utc.astimezone(ZoneInfo(tz_info or "UTC"))
            for calendar in employees.resource_calendar_id:
                intervals = calendar._work_intervals_batch(
                    from_datetime, from_datetime + timedelta(days=7)
                )[False]
                for start, stop, _record in intervals:
                    # working means a work interval within the next hour
                    changes += [start - timedelta(hours=1), stop]
        return min(
            (
                change.astimezone(UTC).replace(tzinfo=None)
                for change in changes
                if change > after_utc
            ),
            default=None,
        )

    def _compute_is_off_hours(self):
        working_now = set(self._get_employee_working_now())
        for employee in self:
            employee.is_off_hours = employee.id not in working_now

    @api.depends('user_id.im_status')
    def _compute_presence_state(self):
        """Compute ``hr_presence_state`` (``present``, ``absent`` or ``out_of_working_hour``).

        In ``hr``, only the login-based presence control is implemented (company
        setting ``hr_presence_control_login``): out of contract today gives
        ``out_of_working_hour``; an online user gives ``present``; an offline
        user expected to work now (:meth:`_get_employee_working_now`) gives
        ``absent``. Without the setting, the state is always
        ``out_of_working_hour``. Extended by ``hr_attendance``, ``hr_holidays``, ...
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
                if not employee.sudo().is_in_contract:
                    state = "out_of_working_hour"
                elif presence_status == "online":
                    state = 'present'
                elif presence_status == "offline" and employee.id in working_now_list:
                    state = 'absent'
            employee.hr_presence_state = state

    def _compute_sql_presence_state(self, table):
        # Ugly hack to be able to groupby hr_presence_state: that's not efficient since we will compute
        # the hr_presence_state on every record in the DB to generate this new groupby specification.
        limit_records = self.env['ir.config_parameter'].get_int('hr.employee.hr_presence_state.limit', 1000)
        all_records = self.sudo().with_context(active_test=False).search_fetch([], limit=limit_records + 1, order='id')
        # Protection against too much inefficient code.
        if len(all_records) > limit_records:
            raise UserError(self.env._("Cannot search or group by hr_presence state: too many employees (%s)", len(all_records)))
        states_map = all_records.with_env(self.env).grouped('hr_presence_state')
        if not states_map:  # No record, no result
            return SQL('NULL')

        id_field = SQL.identifier(table._alias, 'id')
        when_cases = SQL('\n').join(
            [
                SQL('WHEN %s IN %s THEN %s', id_field, records._ids, state)
                for state, records in states_map.items()
            ],
        )
        return SQL("CASE %s END", when_cases)

    @api.depends('user_id')
    def _compute_last_activity(self):
        today = fields.Date.context_today(self)
        for employee in self:
            tz = employee.tz
            # sudo: res.users - can access presence of accessible user
            if last_presence := employee.user_id.sudo().presence_ids.last_presence:
                last_activity_datetime = last_presence.replace(tzinfo=UTC).astimezone(ZoneInfo(tz)).replace(tzinfo=None)
                employee.last_activity = last_activity_datetime.date()
                if employee.last_activity == today:
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

    def _compute_exceptional_location_id(self):
        current_employee_locations = self.env['hr.employee.location'].search([
            ('employee_id', 'in', self.ids),
            ('date', '=', 'today'),
        ])
        employee_work_locations = {l.employee_id.id: l.work_location_id for l in current_employee_locations}

        for employee in self:
            employee.exceptional_location_id = employee_work_locations.get(employee.id, False)

    @api.depends('birthday', 'birthday_public_display')
    def _compute_birthday_public_display_string(self):
        for employee in self:
            if employee.birthday and employee.birthday_public_display:
                employee.birthday_public_display_string = format_date(self.env, employee.birthday, date_format="MMMM dd")
            else:
                employee.birthday_public_display_string = "hidden"

    @api.depends('name', 'permit_no')
    def _compute_work_permit_name(self):
        for employee in self:
            name = employee.name.replace(' ', '_') + '_' if employee.name else ''
            permit_no = '_' + employee.permit_no if employee.permit_no else ''
            employee.work_permit_name = "%swork_permit%s" % (name, permit_no)

    def _get_partner_count_depends(self):
        return ['user_id']

    @api.depends(lambda self: self._get_partner_count_depends())
    def _compute_related_partners_count(self):
        self.related_partners_count = len(self._get_related_partners())

    def _get_related_partners(self):
        """Return the partners related to the employees (work contacts and users' partners).

        Hook extended by other modules (e.g. ``hr_recruitment`` adds the
        applicants' partners); used by the "Related Contacts" smart button.

        :rtype: res.partner
        """
        return self.work_contact_id | self.user_id.partner_id

    def action_related_contacts(self):
        related_partners = self._get_related_partners()
        action = {
            'name': self.env._("Related Contacts"),
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

    def action_send_invitation(self):
        """Create a user and send a password-reset (invitation) e-mail to the linked user."""
        self.ensure_one()
        if not self.user_id:
            self.user_id = self._get_or_create_light_user(invite=True)
            # as the action_reset_password is done inside get_or_create, return nofication here.
            # reload also needed here for form action button (not only via user_status JS widget)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Notification',
                    'message': self.env._('A signup link was sent by email'),
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'}
                },
            }
        # called when resending invitation to existing user
        return self.user_id.with_context({'create_user': 1}).action_reset_password()

    def action_reset_password(self):
        """Send a password-reset e-mail to the linked user."""
        self.ensure_one()
        if not self.user_id:
            raise UserError(self.env._("This employee has no user."))
        return self.user_id.action_reset_password()

    def action_copy_invitation_link(self):
        self.ensure_one()
        if not self.user_id:
            raise UserError(self.env._("This employee has no user."))
        self.user_id.check_access('write')
        partner = self.user_id.partner_id
        partner.sudo().signup_prepare()
        return partner.sudo()._get_signup_url_for_action().get(partner.id)

    def action_toggle_user_active(self):
        """Activate / deactivate the linked user from the employee form."""
        self.ensure_one()
        if not self.user_id:
            raise UserError(self.env._("This employee has no user."))
        self.user_id.active = not self.user_id.active

    def action_deactivate_user_and_depart(self):
        self.ensure_one()
        if not self.user_id:
            raise UserError(self.env._("This employee has no user."))
        action = self.action_new_departure()
        self.user_id.active = False
        return action

    def _compute_display_name(self):
        if self.browse().has_access('read'):
            return super()._compute_display_name()
        for employee_private, employee_public in zip(self, self.env['hr.employee.public'].browse(self.ids)):
            employee_private.display_name = employee_public.display_name

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if self.env.context.get('import_file'):
            domain &= Domain('company_id', 'in', self.env.companies.ids)
        return domain

    @api.model
    def search_fetch(self, domain, field_names=None, offset=0, limit=None, order=None):
        """Search and fetch, through ``hr.employee.public`` for users without read access.

        Users without access to ``hr.employee`` (e.g. regular internal users)
        still get an ``hr.employee`` recordset: the search runs on
        ``hr.employee.public`` (conditions on ``version_id``/``current_version_id``
        are mapped or dropped) and the public values are copied into the cache
        of the ``hr.employee`` records.

        :raise AccessError: if ``field_names`` or ``domain`` contain fields not
            available on ``hr.employee.public``
        """
        if self.has_access('read'):
            return super().search_fetch(domain, field_names, offset, limit, order)

        # HACK: retrieve publicly available values from hr.employee.public and
        # copy them to the cache of self; non-public data will be missing from
        # cache, and interpreted as an access error
        if field_names is None:
            field_names = [field.name for field in self._determine_fields_to_fetch()]
        field_names = [f_name for f_name in field_names if f_name not in ['current_version_id', 'version_id']]
        self._check_private_fields(field_names)
        self.flush_model(field_names)

        def map_condition_to_public_employee(condition):
            for field in ('version_id', 'current_version_id'):
                if condition.field_expr == field and condition.operator == 'any!':
                    condition = extract_comodel_domain(self.env['hr.employee'], Domain(condition.field_expr, condition.operator, condition.value), field)
                if condition.field_expr == field:
                    # field has not been explicitly declared in hr.employee.public
                    return None
            return condition

        # fields on hr.employee's current_version_id are explicitly declared
        # on hr.employee.public due to versions being absent on the public
        # employee, we thus need to map it to avoid getting errors
        domain = filter_map_domain(domain, map_condition_to_public_employee)

        try:
            public = self.env['hr.employee.public'].search_fetch(domain, field_names, offset, limit, order)
        except (ValueError, KeyError) as e:
            # the domain uses fields not available on hr.employee.public (as in _search)
            raise AccessError(self.env._('You do not have access to this document.')) from e
        employees = self.browse(public._ids)
        employees._copy_cache_from(public, field_names)
        return employees

    def fetch(self, field_names=None):
        """Fetch fields, reading them from ``hr.employee.public`` for users without read access.

        This is what makes ``employee.name`` work for a regular internal user:
        the public values are copied into the ``hr.employee`` cache; reading a
        non-public field raises an ``AccessError``.

        :raise AccessError: if ``field_names`` contains fields not available on
            ``hr.employee.public``
        """
        if self.browse().has_access('read'):
            return super().fetch(field_names)

        # HACK: retrieve publicly available values from hr.employee.public and
        # copy them to the cache of self; non-public data will be missing from
        # cache, and interpreted as an access error
        if field_names is None:
            field_names = [field.name for field in self._determine_fields_to_fetch()]
        field_names = [f_name for f_name in field_names if f_name not in ['current_version_id', 'version_id']]
        self._check_private_fields(field_names)
        self.flush_recordset(field_names)
        public = self.env['hr.employee.public'].browse(self._ids)
        public.fetch(field_names)
        # make sure all related fields from employee are in cache
        for field_name in field_names:
            public_field = self.env['hr.employee.public']._fields[field_name]
            private_field = self.env['hr.employee']._fields[field_name]
            if (public_field.related and public_field.related_field.model_name == 'hr.employee'
                    or private_field.inherited and private_field.inherited_field.model_name == 'hr.version'):
                public.mapped(field_name)
        self._copy_cache_from(public, field_names)

    def _compute_field_value(self, field):
        """Read the non-stored fields inherited from ``hr.version`` from ``hr.employee.public``
        for users without read access.

        Those fields (e.g. ``job_title``, ``department_id``) are computed from
        ``version_id``, that such users cannot read: like in :meth:`fetch`, their
        public values are copied into the cache (an ``AccessError`` is raised for
        the fields not available on ``hr.employee.public``).
        """
        if field.inherited and all(self._ids) and not self.browse().has_access('read'):
            # HACK: fill the cache of the employee with the values of hr.employee.public
            self.fetch([field.name])
            return
        super()._compute_field_value(field)

    def _access_domain(self, operation):
        """Grant read access to all employees when the ``hr.mixin`` context marker is set.

        Models inheriting ``hr.mixin`` set the private context key
        ``_allow_read_hr_employee`` during ``create``/``write`` so that users
        without access to ``hr.employee`` can still assign many2many fields
        targeting employees.
        """
        # This method override provides read access to 'hr.employee' in some
        # situations, like setting a many2many field to comodel 'hr.employee'.
        # Since Odoo 19, one must have read access to the comodel to modify the
        # relation.
        # HACK with context key
        if operation == 'read' and self.env.context.get('_allow_read_hr_employee') is _ALLOW_READ_HR_EMPLOYEE:
            return Domain.TRUE

        return super()._access_domain(operation)

    def _check_private_fields(self, field_names):
        """Raise if ``field_names`` contains fields not available on ``hr.employee.public``.

        :param list[str] field_names: field names to check
        :raise AccessError: if any field is private
        """
        public_fields = self.env['hr.employee.public']._fields
        private_fields = [fname for fname in field_names if fname not in public_fields]
        if private_fields:
            raise AccessError(self.env._('The fields “%s”, which you are trying to read, are not available for employee public profiles.', ','.join(private_fields)))

    def _copy_cache_from(self, public, field_names):
        """Copy the cached values of ``field_names`` from ``public`` (``hr.employee.public``) to ``self``.

        ``self`` and ``public`` must be aligned (same ids, same order). Values
        missing from the public cache are left missing.
        """
        # HACK: retrieve publicly available values from hr.employee.public and
        # copy them to the cache of self; non-public data will be missing from
        # cache, and interpreted as an access error
        self_raw = self.with_context(prefetch_langs=True)
        for fname in field_names:
            field = self._fields[fname]
            cache = public._fields[fname]._get_cache(self_raw.env)

            for record, recordp in zip(self_raw, public):
                value = cache.get(recordp.id, SENTINEL)
                if value is SENTINEL:
                    continue
                if field.translate:
                    value = None if value is None else value.copy()
                field._update_cache(record, value)

    @api.model
    def notify_expiring_contract_work_permit(self):
        """Schedule "to do" activities for expiring contracts and work permits (daily cron).

        For each company, targets employees whose current ``contract_date_end``
        (resp. ``work_permit_expiration_date``) falls within the company's
        ``contract_expiration_notice_period`` (resp.
        ``work_permit_expiration_notice_period``) days from today. The activity
        is assigned to the HR responsible (or the current user), with the
        expiration date as deadline; existing identical activities are not
        duplicated.

        :return: ``True``
        """
        companies = self.env['res.company'].search([])
        employees_contract_expiring = self.env['hr.employee']
        employees_work_permit_expiring = self.env['hr.employee']
        today = fields.Date.context_today(self)

        for company in companies:
            # Employees with contracts expiring soon
            employees_contract_expiring += self.env['hr.employee'].search([
                ('company_id', '=', company.id),
                ('contract_date_start', '!=', False),
                ('contract_date_start', '<', today),
                ('contract_date_end', '>=', today),
                ('contract_date_end', '<=', today + relativedelta(days=company.contract_expiration_notice_period)),
            ])

            # Employees with work permits expiring soon
            employees_work_permit_expiring += self.env['hr.employee'].search([
                ('company_id', '=', company.id),
                ('work_permit_expiration_date', '!=', False),
                ('work_permit_expiration_date', '>=', today),
                ('work_permit_expiration_date', '<=', today + relativedelta(days=company.work_permit_expiration_notice_period)),
            ])

        todo_type = self.env.ref('mail.mail_activity_data_todo')

        # Existing activities
        existing_activities_contract = employees_contract_expiring.activity_ids.filtered(
            lambda a: a.technical_usage == 'hr_expiring_contract'
        )
        existing_activities_permit = employees_work_permit_expiring.activity_ids.filtered(
            lambda a: a.technical_usage == 'hr_expiring_work_permit'
        )

        existing_activities_index_contract = {
            (a.res_id, a.date_deadline, a.user_id.id): a for a in existing_activities_contract
        }
        existing_activities_index_permit = {
            (a.res_id, a.date_deadline, a.user_id.id): a for a in existing_activities_permit
        }

        # Create contract expiry activities
        for employee in employees_contract_expiring:
            activity_responsible = employee.hr_responsible_id.id or self.env.uid
            key = (employee.id, employee.contract_date_end, activity_responsible)
            if key not in existing_activities_index_contract:
                employee.with_context(mail_activity_quick_update=True).activity_schedule(
                    activity_type_id=todo_type.id,
                    date_deadline=employee.contract_date_end,
                    summary=self.env._("The contract of %(employee_name)s is about to expire.", employee_name=employee.name),
                    user_id=activity_responsible,
                    technical_usage='hr_expiring_contract',
                )

        # Create work permit expiry activities
        for employee in employees_work_permit_expiring:
            activity_responsible = employee.hr_responsible_id.id or self.env.uid
            key = (employee.id, employee.work_permit_expiration_date, activity_responsible)
            if key not in existing_activities_index_permit:
                employee.with_context(mail_activity_quick_update=True).activity_schedule(
                    activity_type_id=todo_type.id,
                    date_deadline=employee.work_permit_expiration_date,
                    summary=self.env._("The work permit of %(employee_name)s is about to expire.", employee_name=employee.name),
                    user_id=activity_responsible,
                    technical_usage='hr_expiring_work_permit',
                )

        return True

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        """Return the ``hr.employee.public`` view for users without read access to ``hr.employee``."""
        if self.browse().has_access('read'):
            return super().get_view(view_id, view_type, **options)
        return self.env['hr.employee.public'].get_view(view_id, view_type, **options)

    @api.model
    def get_views(self, views, options=None):
        """Return the views, replacing the "today's location" placeholders by today's weekday field.

        In the search and list archs, ``today_location_name`` and
        ``work_location_name`` are replaced by e.g. ``monday_location_id`` (see
        :meth:`_get_current_day_location_field`).

        :raise RedirectWarning: for users without read access to ``hr.employee``,
            redirecting them to the public employees action
        """
        if self.browse().has_access('read'):
            res = super().get_views(views, options)
            # hack to allow groupby on today's location. Since there are 7 different fields, we have to use a placeholder
            # in the search view and replace it with the correct field every time the views are fetched.
            dayfield = self._get_current_day_location_field()
            if 'search' in res['views']:
                res['views']['search']['arch'] = res['views']['search']['arch'].replace('today_location_name', dayfield)
            if 'list' in res['views']:
                res['views']['list']['arch'] = res['views']['list']['arch'].replace('work_location_name', dayfield)
            res["models"][self._name]["fields"].update(self.fields_get([dayfield]))
            return res
        # returning public employee data would cause a traceback when building
        # the private employee xml view
        raise RedirectWarning(
            message=self.env._(
            """You are not allowed to access "Employee" (hr.employee) records.
    We can redirect you to the public employee list."""
            ),
            action=self.env.ref('hr.hr_employee_public_action').id,
            button_text=self.env._("Employees profile"),
        )

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, *, bypass_access=False, **kwargs):
        """Search employees, through ``hr.employee.public`` for users without read access.

        ``_search`` is where access rights are checked, so overriding it makes
        ``env['hr.employee'].search(...)`` return an ``hr.employee`` recordset
        even for users without access to the model: the domain is evaluated on
        ``hr.employee.public``, whose ids are the employee ids. Conditions on
        ``current_version_id`` (produced by the optimization of inherited
        fields) are converted to conditions on ``id``.

        :raise AccessError: if the domain uses fields not available on
            ``hr.employee.public``
        """
        if self.browse().has_access('read') or bypass_access:
            return super()._search(domain, offset, limit, order, bypass_access=bypass_access, **kwargs)
        domain = Domain(domain)

        # HACK Some fields are inherited from the `current_version_id` and may have been already
        # optimized, showing current_version_id in the domain, but public employee does not have
        # that field and may have fields directly on the model, just change the condition to `id` in
        # that case.
        def adapt_condition(cond):
            if cond.field_expr != 'current_version_id':
                return cond
            if cond.operator in ('any', 'not any'):
                raise AccessError(self.env._('You do not have access to this document.'))
            if cond.operator in ('any!', 'not any!'):
                if isinstance(cond.value, Query):
                    query = cond.value.subselect(cond.value.table.employee_id)
                else:
                    query = self.env['hr.version'].sudo()._search(Domain('id', 'any!', cond.value), active_test=False)
                return Domain('id', cond.operator, query)
            return Domain('id', cond.operator, cond.value)
        domain = domain.map_conditions(adapt_condition)
        try:
            ids = self.env['hr.employee.public']._search(domain, offset, limit, order, **kwargs)
        except (ValueError, KeyError) as e:
            raise AccessError(self.env._('You do not have access to this document.')) from e
        # the result is expected from this table, so we should link tables
        return super(HrEmployee, self.sudo())._search([('id', 'in', ids)], order=order)

    @api.model
    def is_onboarding(self, company_ids):
        main_company = self.env.ref("base.main_company").id
        return (
            main_company in company_ids
            and not self.env['hr.employee'].search_count([('company_id', 'in', company_ids)], limit=1)
        )

    @api.model
    def load_demo_data(self):
        if not self.has_access('create'):
            raise UserError(self.env._("You do not have the rights to load the Employees sample data."))
        convert.convert_file(env=self.sudo().env, module='hr', filename='data/scenarios/hr_scenario.xml', idref=None, mode='init')

    def get_formview_id(self, access_uid=None):
        """Return the public employee form view for users who are not HR officers.

        Used when opening a many2one to ``hr.employee``.

        :param int access_uid: the user to check instead of the current user
        :rtype: int
        """
        user = self.env.user
        if access_uid:
            user = self.env['res.users'].browse(access_uid).sudo()

        if user.has_group('hr.group_hr_user'):
            return super().get_formview_id(access_uid=access_uid)
        # Hardcode the form view for public employee
        return self.env.ref('hr.hr_employee_public_view_form').id

    def get_record_default_action(self, access_uid=None):
        """Return the default action of the record, on ``hr.employee.public`` when needed.

        The action targets ``hr.employee.public`` if the user is not an HR
        officer or cannot read this employee.

        :param int access_uid: the user to check instead of the current user
        :rtype: dict
        """
        res = super().get_record_default_action(access_uid=access_uid)
        user = self.env.user
        if access_uid:
            user = self.env['res.users'].browse(access_uid).sudo()

        if not user.has_group('hr.group_hr_user') or not self.env['hr.employee'].browse(res['res_id']).has_access('read'):
            res['res_model'] = 'hr.employee.public'

        return res

    @api.constrains('pin')
    def _verify_pin(self):
        for employee in self:
            if employee.pin and not employee.pin.isdigit():
                raise ValidationError(self.env._("The PIN must be a sequence of digits."))

    @api.constrains('barcode')
    def _verify_barcode(self):
        for employee in self:
            if employee.barcode:
                # [!-~] matches every printable ASCII character except the space,
                # which is excluded because leading or trailing spaces are invisible
                if not re.fullmatch(r'[!-~]{1,18}', employee.barcode):
                    raise ValidationError(self.env._("The Badge ID must contain only printable ASCII characters, without spaces, and be no longer than 18 characters."))

    @api.onchange('user_id')
    def _onchange_user(self):
        self.update(self._sync_user(self.user_id, (bool(self.image_1920))))
        if not self.name:
            self.name = self.user_id.name

    @api.onchange('work_email')
    def _onchange_work_email_link_user(self):
        # link the internal (light or regular) user of that email, unless it is already an employee of the company
        emails = tools.mail.email_normalize_all(self.work_email)
        if self.user_id or not emails:
            return
        user = self.env['res.users'].search([
            ('share', '=', False),
            ('company_ids', 'in', self.company_id.ids),
            '|', ('login', '=', emails[0]), ('email_normalized', '=', emails[0]),
        ], limit=1)
        if user and not user.employee_ids.filtered(lambda employee: employee.company_id == self.company_id):
            self.update(self._sync_user(user, bool(self.image_1920)))

    @api.onchange('company_id')
    def _onchange_timezone(self):
        if self.company_id and not self.tz:
            self.tz = self.company_id.tz

    def _remove_work_contact_id(self, user, employee_company):
        """Unlink ``user``'s partner as work contact of other user-less employees of the company.

        Called when ``user`` gets linked to ``self`` (create/write of
        ``user_id``), so that the user's partner remains the work contact of a
        single employee per company.

        :param user: the user being linked
        :type user: res.users
        :param employee_company: company id to consider, ``self.company_id`` by default
        :type employee_company: int or None
        """
        employee_company = employee_company or self.company_id.id
        # For employees with a user_id, the constraint (user can't be linked to multiple employees) is triggered
        old_partner_employee_ids = user.partner_id.employee_ids.filtered(lambda e:
            not e.user_id
            and e.company_id.id == employee_company
            and e != self
        )
        old_partner_employee_ids.work_contact_id = None

    def _sync_user(self, user, employee_has_image=False):
        """Return the employee values to write when linking ``user`` to the employee.

        The user's partner becomes the work contact, and the user's image
        (unless the employee has one) and timezone (if set) are copied. Used
        by :meth:`create`, :meth:`write`, the ``user_id`` onchange and
        ``res.users.action_create_employee``. Does not write anything itself.

        :param user: the user to link (may be empty)
        :type user: res.users
        :param bool employee_has_image: if ``True``, keep the employee's image
        :return: values for ``hr.employee.write``/``create`` (``work_contact_id``,
            ``user_id``, optionally ``image_1920`` and ``tz``)
        :rtype: dict
        """
        vals = dict(
            work_contact_id=user.partner_id.id if user else self.work_contact_id.id,
            user_id=user.id,
        )
        if not employee_has_image:
            vals['image_1920'] = user.image_1920
        if user.tz:
            vals['tz'] = user.tz
        return vals

    def _get_or_create_light_user(self, invite=False):
        """Return a user for the employee, creating a light (less billable) internal user if needed.

        Reuses, in order: the resource's user, the work contact's user, or an
        existing active internal user whose login/email matches the work email.
        Otherwise creates a user restricted to the light groups, in the
        employee's company. Does not link the user: the caller assigns
        ``user_id`` (see :meth:`action_send_invitation`). Single employee only.

        :param bool invite: send the signup/reset password e-mail to the reused
            user; refuses to reuse a user only matched by e-mail
        :rtype: res.users
        :raise ValidationError: if no e-mail is available to build the login
        :raise UserError: if the matching user is archived, a portal user,
            already has an employee in the company, or (with ``invite``) was
            only matched by e-mail
        """
        self.ensure_one()
        ResUsers = self.env['res.users'].sudo()
        if self.resource_id.user_id:
            if invite:
                self.resource_id.user_id.with_context({'create_user': 1}).action_reset_password()
            return self.resource_id.user_id
        company_id = self.company_id.id or self.env.company.id
        # 1. reuse the work contact's user, or an existing user matching the work
        #    email (by login or email address) to avoid creating a duplicate user
        user = self.work_contact_id.user_ids[:1]
        emails = tools.mail.email_normalize_all(self.work_contact_id.email or self.work_email or self.resource_id.email)
        login = emails[0] if emails else False
        if not login:
            raise ValidationError(self.env._('Cannot create light user for an employee without login (email address or related contact).'))
        if user:
            if invite:
                user.with_context({'create_user': 1}).action_reset_password()
            return user
        # Try to search for an existing user.
        if not user and login:
            user = ResUsers.with_context(active_test=False).search(
                ['|', ('login', '=', login), ('email_normalized', '=', login)], limit=1, order='active')
            if user:
                # If archived user or employee of the same company linked to that user...
                if not user.active:
                    raise UserError(self.env._('An inactive user already exist with the following login: %(login)s. '
                                               'User Name: %(user_name)s.', login=login, user_name=user.name))
                existing_employee = user.employee_ids.filtered(lambda e: e.company_id.id == company_id)
                if existing_employee:
                    raise UserError(self.env._('A user with the same login (%(login)s) already has an employee in this company. '
                                               'User Name: %(user_name)s / Employee Name: %(employee)s',
                                               login=login, user_name=user.name, employee=existing_employee.name))
                elif user.share:
                    raise UserError(self.env._('A portal user already exist with the following login: %(login)s. '
                                               'User Name: %(user_name)s. You should set another email address on the employee.',
                                               login=login, user_name=user.name))

                if invite:
                    raise UserError(self.env._('A user already exist with the following login: %(login)s. '
                                               'User Name: %(user_name)s. Please link the user instead before sending invitation.', login=login, user_name=user.name))
                return user
        groups = ResUsers._default_groups()._reduce_to_light_groups()
        return ResUsers.create({
            'name': self.name,
            'login': login,
            'email': login,
            'phone': self.work_phone or self.mobile_phone or self.work_contact_id.phone,
            'partner_id': self.work_contact_id.id or False,
            'company_id': company_id,
            'company_ids': [Command.set([company_id])],
            'group_ids': [Command.set(groups.ids)],
        })

    def _prepare_resource_values(self, vals, tz):
        """Return the values of the ``resource.resource`` created with the employee.

        Extends ``resource.mixin`` with ``user_id`` and ``active``. Pops
        ``name`` and ``user_id`` from ``vals`` (they are related to the
        resource) to avoid a useless write after creation.

        :param dict vals: employee creation values (modified in place)
        :param str tz: timezone of the resource
        :rtype: dict
        """
        resource_vals = super()._prepare_resource_values(vals, tz)
        vals.pop('name', False)  # Already considered by super call but no popped
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
        """Create a new (in-memory) employee along with its in-memory version.

        Inherited ``hr.version`` values are put on a new version linked to the
        new employee, keeping only the fields the user can read.
        """
        if not values:
            values = {}
        new_vals = values.copy()
        version_vals = {val: new_vals.pop(val) for val in values if val in self._fields and self._fields[val].inherited}

        employee = super().new(new_vals, origin, ref)
        version_vals['employee_id'] = employee
        self.env['hr.version'].new({
            f_name: value
            for f_name, value in version_vals.items()
            if self.env['hr.version'].has_field_access(self.env['hr.version']._fields[f_name], 'read')
        })
        return employee

    @api.model
    def cycles_in_hierarchy_read(self, domain):
        """
        Detect cycles in a parent-child hierarchy using Floyd's Tortoise and Hare algorithm.
        The algorithm works iff each child in the hierarchy has at most one parent.

        :param domain: A domain used to search for records in the hierarchy.
        :type domain: list

        :return: List of record IDs that are part of a cycle in a model.
        :rtype: list[int]
        """
        records = self.search_fetch(domain=domain, field_names=['parent_id'])
        parent_map = defaultdict(
            lambda: None,
            {
                record.id: record.parent_id.id if record.parent_id else None
                for record in records
            },
        )
        visited = set()
        in_cycle = set()

        for record in records:
            record_id = record.id
            if record in visited:
                continue

            # Floyd's Tortoise and Hare cycle detection
            parent = record_id
            grand_parent = record_id

            while True:
                parent = parent_map.get(parent)
                grand_parent = parent_map.get(parent_map.get(grand_parent))

                if parent is None or grand_parent is None:
                    break

                if parent == grand_parent or parent in in_cycle or grand_parent in in_cycle:
                    cycle_node = record_id
                    while cycle_node not in in_cycle:
                        in_cycle.add(cycle_node)
                        visited.add(cycle_node)
                        cycle_node = parent_map.get(cycle_node)
                    break

                if parent in visited or grand_parent in visited:
                    break

            # Mark the current traversal as visited
            current = record_id
            while current is not None and current not in visited:
                visited.add(current)
                current = parent_map.get(current)
        return list(in_cycle)

    @api.model
    def _pop_employee_skill_commands(self, vals):
        """ Gather the commands written on any of the skill fields of the employee, as they all target
        `employee_skill_ids` and must go through `hr.employee.skill._get_transformed_commands`. """
        return vals.pop('current_employee_skill_ids', []) + vals.pop('certification_ids', []) \
            + vals.get('employee_skill_ids', [])

    def _get_current_skills_summary(self):
        """ Snapshot of the current skills of the employees, see `_log_skill_changes`. """
        return {
            employee: {
                skill.id: {
                    'skill_id': skill.skill_id.id,
                    'skill_name': skill.skill_id.name,
                    'level_name': skill.skill_level_id.name,
                    'is_certification': skill.is_certification,
                    'label': skill._get_chatter_label(),
                }
                for skill in employee.current_employee_skill_ids
            }
            for employee in self
        }

    def _log_skill_changes(self, previous_skills_summary):
        """ Log in the chatter of the employees the difference between the given summary of their
        previous skills and their current ones. A regular skill whose level changed is logged as
        a single update. """
        # the validity of the skills is not part of the dependencies of the compute
        self.invalidate_recordset(['current_employee_skill_ids'])
        for employee, current_skills in self._get_current_skills_summary().items():
            previous_skills = previous_skills_summary.get(employee, {})
            removed_skills = {
                skill_id: skill for skill_id, skill in previous_skills.items() if skill_id not in current_skills
            }
            removed_regular_skill_id_per_skill = {
                skill['skill_id']: skill_id for skill_id, skill in removed_skills.items() if not skill['is_certification']
            }
            lines = []
            for skill_id, skill in current_skills.items():
                if skill_id in previous_skills:
                    continue
                previous_skill_id = not skill['is_certification'] and removed_regular_skill_id_per_skill.get(skill['skill_id'])
                if previous_skill_id:
                    lines.append(self.env._(
                        "Updated: %(skill)s: %(previous_level)s → %(level)s",
                        skill=skill['skill_name'],
                        previous_level=removed_skills.pop(previous_skill_id)['level_name'],
                        level=skill['level_name'],
                    ))
                else:
                    lines.append(self.env._("Added: %(skill)s", skill=skill['label']))
            lines += [self.env._("Removed: %(skill)s", skill=skill['label']) for skill in removed_skills.values()]
            if lines:
                employee._message_log(body=Markup("%(title)s<ul>%(lines)s</ul>") % {
                    'title': self.env._("Skills updated"),
                    'lines': Markup().join(Markup("<li>%s</li>") % line for line in lines),
                })

    @api.model_create_multi
    def create(self, vals_list):
        """Create employees, each with its resource, first version and work contact.

        Values of inherited ``hr.version`` fields (``date_version``,
        ``contract_date_start``, ``wage``, ``job_id``, ``resource_calendar_id``,
        ...) go to the first version, created through ``_inherits``; creation
        is done per company so that the version gets the right company. The
        values of a ``contract_template_id`` are applied to the first version
        (explicit values have priority). If ``user_id`` is given, the user's partner, image and timezone are used
        (:meth:`_sync_user`). A work contact is created for employees without
        one, an avatar is generated if there is no image, department channels
        are subscribed and an onboarding note is logged.

        Example::

            env['hr.employee'].create({
                'name': 'John Doe',
                'job_id': job.id,
                'date_version': date(2026, 1, 1),
                'contract_date_start': date(2026, 1, 1),
                'wage': 3000,
            })
        """
        vals_per_company = defaultdict(list)
        Version = self.env['hr.version']
        for idx, vals in enumerate(vals_list):
            if vals.get('contract_template_id'):
                # the template is stored on the employee, not on the version: apply it
                # here, explicit values having priority (as in hr.version create)
                template_vals = Version.get_values_from_contract_template(Version.browse(vals['contract_template_id']))
                vals.update({**template_vals, **vals})
            if skill_commands := self._pop_employee_skill_commands(vals):
                vals['employee_skill_ids'] = self.env['hr.employee.skill']._get_transformed_commands(skill_commands, self)
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
        # version_id.resource_calendar_id's own inverse (_inverse_resource_calendar_id) runs
        # while the version's employee_id back-link isn't set yet, so it can't sync the resource's
        # calendar at that point; do it explicitly now that every link is in place
        for employee in employees:
            if employee.resource_id.calendar_id != employee.version_id.resource_calendar_id:
                employee.resource_id.calendar_id = employee.version_id.resource_calendar_id
        # As we do a custom batch by company, we must reorder the records to respect the original order.
        employees = employees.sorted(key=lambda employee: index_per_employee[employee])
        # Sudo in case HR officer doesn't have the Contact Creation group
        employees.filtered(lambda e: not e.work_contact_id).sudo()._create_work_contacts()
        if self.env.context.get('salary_simulation'):
            return employees
        for employee_sudo in employees.sudo():
            # creating 'svg/xml' attachments requires specific rights
            if not employee_sudo.image_1920 and self.env['ir.ui.view'].sudo(False).has_access('write'):
                employee_sudo.image_1920 = employee_sudo._avatar_generate_svg()
                employee_sudo.work_contact_id.image_1920 = employee_sudo.image_1920
        employee_departments = employees.department_id
        if employee_departments:
            self.env['discuss.channel'].sudo().search([
                ('subscription_department_ids', 'in', employee_departments.ids)
            ])._subscribe_users_automatically()
        onboarding_notes_bodies = {}
        hr_root_menu = self.env.ref('hr.menu_hr_root')
        for employee in employees:
            # Launch onboarding plans
            link = Markup('<a href="/odoo/%(employee_id)s/action-hr.plan_wizard_action?active_model=hr.employee&menu_id=%(menu_id)s">%(text)s</a>') % {
                'employee_id': employee.id,
                'menu_id': hr_root_menu.id,
                'text': self.env._('onboarding plan'),
            }
            message = Markup('<b>%(title)s</b> %(text)s %(onboarding_plan_link)s?') % {
                'title': self.env._('Congratulations!'),
                'text': self.env._('May I recommend you to setup an'),
                'onboarding_plan_link': link,
            }
            onboarding_notes_bodies[employee.id] = message
        employees._message_log_batch(onboarding_notes_bodies)
        employees.invalidate_recordset()
        return employees

    def write(self, vals):
        """Write on employees, sending inherited fields to their ``version_id`` in a single write.

        Values of inherited ``hr.version`` fields are written on ``version_id``,
        i.e. the current version, or the version given by the ``version_id``
        context key (see :meth:`_compute_version_id`). To change data from a
        given date on, create a version instead (:meth:`create_version`).
        Writing on versions also sets ``last_modified_date/uid`` and logs an
        "As of <date>" tracking message.

        Side effects: ``user_id`` syncs work contact/image/timezone
        (:meth:`_sync_user`); ``tz`` is propagated to the linked user (same
        company); changing ``work_contact_id`` moves the bank accounts to the new
        partner (and untrusts them); ``resource_calendar_id`` updates the
        resource's calendar when the written version is the current one;
        ``current_version_id`` always copies the new version's calendar onto
        the resource; ``department_id``/``user_id`` subscribe the
        user to the department's auto-subscription channels.
        """
        previous_skills_summary = {}
        if skill_commands := self._pop_employee_skill_commands(vals):
            previous_skills_summary = self._get_current_skills_summary()
            vals['employee_skill_ids'] = self.env['hr.employee.skill']._get_transformed_commands(skill_commands, self)
        if 'work_contact_id' in vals:
            self.message_unsubscribe(self.work_contact_id.ids)
        if 'user_id' in vals:
            # Update the profile pictures with user, except if provided
            user = self.env['res.users'].browse(vals['user_id'])
            vals.update(self._sync_user(user, (bool(all(emp.image_1920 for emp in self)))))
            self._remove_work_contact_id(user, vals.get('company_id'))
        if 'work_permit_expiration_date' in vals:
            vals['work_permit_scheduled_activity'] = False
        if vals.get('tz'):
            users_to_update = self.env['res.users']
            for employee in self:
                if employee.user_id and employee.company_id == employee.user_id.company_id and vals['tz'] != employee.user_id.tz:
                    users_to_update |= employee.user_id
            if users_to_update:
                users_to_update.write({'tz': vals['tz']})
        if vals.get('departure_description'):
            for employee in self:
                employee.message_post(body=self.env._(
                    'Additional Information: \n %(description)s',
                    description=vals.get('departure_description')))
        # Only one write call for all the fields from hr.version
        new_vals = vals.copy()
        version_vals = {val: new_vals.pop(val) for val in vals if val in self._fields and self._fields[val].inherited}
        res = super().write(new_vals)
        if previous_skills_summary:
            self._log_skill_changes(previous_skills_summary)
        if 'work_contact_id' in vals:
            account_ids = self.bank_account_ids.ids
            if account_ids:
                bank_accounts = self.env['res.partner.bank'].sudo().browse(account_ids)
                for bank_account in bank_accounts:
                    if vals['work_contact_id'] != bank_account.partner_id.id:
                        if bank_account.allow_out_payment:
                            bank_account.allow_out_payment = False
                        if vals['work_contact_id']:
                            bank_account.partner_id = vals['work_contact_id']
        if 'current_version_id' in vals:
            new_version = self.env['hr.version'].browse(vals.get('current_version_id'))
            self.resource_id.calendar_id = new_version.resource_calendar_id
        if version_vals:
            version_vals['last_modified_date'] = fields.Datetime.now()
            version_vals['last_modified_uid'] = self.env.uid
            self.version_id.write(version_vals)

            for employee in self:
                multi_update_version_ids = self.env.context.get('multi_update_version_ids')
                if multi_update_version_ids:
                    first_version_sudo = employee.version_ids.filtered(lambda v: v.id == multi_update_version_ids[0]).sudo()
                    last_version_sudo = employee.version_ids.filtered(lambda v: v.id == multi_update_version_ids[-1]).sudo()
                else:
                    first_version_sudo = employee.version_id.sudo()
                    last_version_sudo = first_version_sudo
                start = format_date_abbr(self.env, first_version_sudo.date_start) if first_version_sudo.date_start else False
                end = format_date_abbr(self.env, last_version_sudo.date_end) if last_version_sudo.date_end else False
                if start and end:
                    msg = self.env._("As of %(start)s to %(end)s") % {'start': start, 'end': end}
                elif start:
                    msg = self.env._("As of %s") % (start)
                else:
                    msg = self.env._("As of")
                employee._track_set_log_message(Markup("<b>%s</b>") % msg)
        if vals.get('department_id') or vals.get('user_id'):
            department_id = vals['department_id'] if vals.get('department_id') else self[:1].department_id.id
            # When added to a department or changing user, subscribe to the channels auto-subscribed by department
            self.env['discuss.channel'].sudo().search([
                ('subscription_department_ids', 'in', department_id)
            ])._subscribe_users_automatically()
        if res and 'resource_calendar_id' in vals:
            resources = self.env['resource.resource']
            for employee in self:
                if employee.version_id == employee.current_version_id:
                    resources |= employee.resource_id
            resources.write({'calendar_id': vals.get('resource_calendar_id')})
        return res

    def unlink(self):
        """Delete the employees, their versions and their ``resource.resource``.

        The versions are deleted in cascade (``hr.version.employee_id`` has
        ``ondelete='cascade'``). The ``hr.version`` check that an employee keeps
        at least one version is skipped for the deleted employees, through the
        ``hr_unlink_employee_ids`` context key.
        """
        resources = self.mapped('resource_id')
        super(HrEmployee, self.with_context(hr_unlink_employee_ids=self.ids)).unlink()
        return resources.unlink()

    def _get_employee_m2o_to_empty_on_archived_employees(self):
        """Return the ``hr.employee`` many2one fields (to ``hr.employee``) emptied when the target is archived.

        Hook for :meth:`action_archive`, e.g. a manager or coach who is archived
        is removed from their subordinates.

        :rtype: list[str]
        """
        return ['parent_id', 'coach_id']

    def _get_user_m2o_to_empty_on_archived_employees(self):
        """Return the ``hr.employee`` many2one fields (to ``res.users``) emptied when the target's employee is archived.

        Hook for :meth:`action_archive` (e.g. ``hr_holidays`` adds the time off
        approver ``leave_manager_id``).

        :rtype: list[str]
        """
        return []

    def action_archive(self):
        """Archive the employees and clear the references other employees have to them.

        The fields listed by :meth:`_get_employee_m2o_to_empty_on_archived_employees`
        and :meth:`_get_user_m2o_to_empty_on_archived_employees` are emptied on
        the employees pointing to the archived ones (or their users). Archiving
        an employee also archives its resource (``active`` is related).
        """
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
        return res

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self._origin:
            return {'warning': {
                'title': self.env._("Warning"),
                'message': self.env._("To avoid multi company issues (losing the access to your previous contracts, leaves, ...), you should create another employee in the new company instead.")
            }}
        return None

    def _load_scenario(self):
        demo_tag = self.env.ref('hr.employee_category_demo', raise_if_not_found=False)
        if demo_tag:
            return
        convert.convert_file(self.env, 'hr', 'data/scenarios/hr_scenario.xml', None, mode='init')

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    @api.model
    def _add_certification_activity_to_employees(self):
        today = fields.Date.today()
        three_months_later = today + relativedelta(months=3)
        return_val = self.env["mail.activity"]

        jobs_with_certification = self.env["hr.job"].search([("job_skill_ids.is_certification", "=", True)])
        if not jobs_with_certification:
            return return_val

        job_skill_level_mapping = defaultdict(dict)

        for job in jobs_with_certification:
            for cert in job.job_skill_ids.filtered(lambda s: s.is_certification):
                key = (cert.skill_id, cert.skill_level_id)
                summary = f"{cert.skill_id.name}: {cert.skill_level_id.name}"
                job_skill_level_mapping[job][key] = summary

        if not job_skill_level_mapping:
            return return_val

        employee_domain = Domain.AND(
            [
                Domain("job_id", "in", jobs_with_certification.ids),
                Domain.OR(
                    [
                        Domain("user_id", "!=", False),
                        Domain("parent_id.user_id", "!=", False),
                        Domain("job_id.recruiter_id.user_id", "!=", False),
                    ],
                ),
            ],
        )
        employees = self.env["hr.employee"].search(employee_domain)
        if not employees:
            return return_val

        emp_skills = self.env["hr.employee.skill"].search(
            Domain.AND(
                [Domain("employee_id", "in", employees.ids), Domain("is_certification", "=", True)],
            ),
        )

        employee_cert_data = defaultdict(dict)
        for es in emp_skills:
            key = (es.skill_id, es.skill_level_id)
            employee_cert_data[es.employee_id][key] = es.valid_to

        existing_activities = self.env["mail.activity"].search(
            Domain.AND(
                [
                    Domain("active", "=", True),
                    Domain("activity_category", "=", "upload_file"),
                    Domain("res_model", "=", "hr.employee"),
                    Domain("res_id", "in", employees.ids),
                ],
            ),
        )
        existing_activity_keys = {(act.res_id, act.summary) for act in existing_activities}

        for employee in employees:
            job_id = employee.job_id
            responsible = employee.user_id or employee.parent_id.user_id or job_id.recruiter_id.user_id
            if job_id not in job_skill_level_mapping or not responsible:
                continue

            for skill_level_key, summary in job_skill_level_mapping[job_id].items():
                if (employee.id, summary) in existing_activity_keys:
                    continue

                valid_to_date = employee_cert_data.get(employee, {}).get(skill_level_key)
                if valid_to_date is not None and (valid_to_date is False or valid_to_date > three_months_later):
                    continue

                activity = employee.activity_schedule(
                    act_type_xmlid="mail.mail_activity_data_upload_document",
                    summary=summary or self.env._("Upload a document for a missing certification"),
                    note="Certification missing or expiring soon",
                    date_deadline=valid_to_date or today,
                    user_id=responsible.id,
                )
                return_val += activity

        return return_val

    @api.model
    def get_internal_resume_lines(self, res_id, res_model):
        if not res_id:
            return []
        if res_model == 'res.users':
            res_id = self.env['res.users'].browse(res_id).employee_id.id
        if not self.env['hr.employee.public'].browse(res_id).has_access('read'):
            raise AccessError(self.env._("You cannot access the resume of this employee."))
        res = []
        employee_versions = self.env['hr.employee'].sudo().browse(res_id).version_ids
        if not employee_versions:
            return res
        interval_date_start = False
        for i in range(len(employee_versions) - 1):
            current_version = employee_versions[i]
            next_version = employee_versions[i + 1]
            current_date_start = max(current_version.date_version, current_version.contract_date_start or date.min)
            current_date_end = min(next_version.date_version + relativedelta(days=-1), current_version.contract_date_end or date.max)
            if not current_version.job_title:
                if interval_date_start:
                    previous_version = employee_versions[i - 1]
                    res.append({
                        'id': previous_version.id,
                        'job_title': previous_version.job_title,
                        'date_start': interval_date_start,
                        'date_end': current_date_start + relativedelta(days=-1),
                    })
                    interval_date_start = False
            elif current_version.job_title != next_version.job_title or current_date_end + relativedelta(days=1) != next_version.date_version:
                res.append({
                    'id': current_version.id,
                    'job_title': current_version.job_title,
                    'date_start': interval_date_start or current_date_start,
                    'date_end': current_date_end,
                })
                interval_date_start = False
            else:
                interval_date_start = interval_date_start or current_date_start

        last_version = employee_versions[-1]
        if last_version.job_title:
            current_date_start = max(last_version.date_version, last_version.contract_date_start or date.min)
            res.append({
                'id': last_version.id,
                'job_title': last_version.job_title,
                'date_start': interval_date_start or current_date_start,
                'date_end': last_version.contract_date_end or False,
            })
        elif interval_date_start:
            previous_version = employee_versions[-2]
            res.append({
                'id': previous_version.id,
                'job_title': previous_version.job_title,
                'date_start': interval_date_start,
                'date_end': current_date_start + relativedelta(days=-1),
            })
        return res[::-1]

    def generate_random_barcode(self):
        for employee in self:
            employee.barcode = '041'+"".join(choice(digits) for i in range(9))

    def _get_resources_per_tz(self, date=None):
        """Group the employees' resources by timezone, as expected by ``resource.calendar`` batch methods.

        :param date: reference date for the timezone (see :meth:`_get_tz`)
        :type date: datetime.date or datetime.datetime or None
        :return: ``{ZoneInfo: resource.resource}``
        :rtype: dict
        """
        employee_per_tz = self.grouped(lambda e: ZoneInfo(e._get_tz(date=date)))
        return {
            tz: employees.resource_id
            for tz, employees in employee_per_tz.items()
        }

    def _get_tz(self, date=None):
        """Return the timezone name of the employee, on ``date`` if given.

        The timezone is stored on the version: without ``date``, the one of
        ``version_id`` (current version) is used, otherwise the one of the
        version in effect on ``date``. Falls back on the user's partner
        timezone, the company timezone, then ``'UTC'``. Single employee only.

        :param date: reference date
        :type date: datetime.date or datetime.datetime or str or None
        :rtype: str
        """
        self.ensure_one()
        tz = self.tz
        if date:
            date = fields.Date.to_date(date)
            tz = self.sudo()._get_version(date).tz
        return tz or self.user_partner_id.tz or self.company_id.tz or 'UTC'

    def _get_tz_batch(self, date=None):
        """Return the timezone name of each employee, see :meth:`_get_tz`.

        :return: ``{employee_id: tz_name}``
        :rtype: dict[int, str]
        """
        # Finds the first valid timezone in his tz, his partner tz or UTC
        # Returns a dict {employee_id: tz}
        return {emp.id: emp._get_tz(date=date) for emp in self}

    def _get_first_contract_version_at(self, date):
        """Return, per employee in contract on ``date``, the version of that contract in effect on ``date``.

        Among the versions whose contract covers ``date``: the latest one with
        ``date_version <= date``, or the first one of the contract if none has
        started yet. Employees not in contract on ``date`` are absent from the
        result.

        :param datetime.date date: the reference date
        :return: ``{employee_id: hr.version}`` (sudoed versions)
        :rtype: dict[int, hr.version]
        """
        # called for each day of each work entry generation: no domain to build and optimize
        versions = self.sudo().version_ids.filtered(lambda v: (
            v.contract_date_start and v.contract_date_start <= date
            and (not v.contract_date_end or v.contract_date_end >= date)
        ))
        res = {}
        for employee, employee_versions in versions.grouped('employee_id').items():
            started_versions = employee_versions.filtered(lambda v: v.date_version <= date)
            if started_versions:
                res[employee.id] = max(started_versions, key=lambda v: v.date_version)
            else:
                res[employee.id] = min(employee_versions, key=lambda v: v.date_version)
        return res

    def _get_calendars(self, date_from=None):
        """Return the working schedule of each employee, on ``date_from`` if given.

        Without ``date_from``, the calendar of the current version. With
        ``date_from``, employees in contract on that date get the calendar of
        the version in effect (:meth:`_get_first_contract_version_at`); the
        others keep the current version's calendar.

        :param date_from: reference date (a datetime is truncated to its date)
        :type date_from: datetime.date or datetime.datetime or None
        :return: ``{employee_id: resource.calendar}``
        :rtype: dict[int, resource.calendar]
        """
        res = super()._get_calendars(date_from=date_from)
        if not date_from:
            return res

        date_from = fields.Date.to_date(date_from)
        for employee_id, version in self._get_first_contract_version_at(date_from).items():
            res[employee_id] = version.resource_calendar_id.sudo(self.env.su)
        return res

    def _get_hours_per_week_batch(self, date_from=None):
        """Return the ``hours_per_week`` of each employee's calendar, see :meth:`_get_calendars`.

        :return: ``{employee_id: float}``
        :rtype: dict[int, float]
        """
        res = super()._get_hours_per_week_batch(date_from=date_from)
        if not date_from:
            return res

        date_from = fields.Date.to_date(date_from)
        for employee_id, version in self._get_first_contract_version_at(date_from).items():
            res[employee_id] = version.resource_calendar_id.hours_per_week
        return res

    def _get_hours_per_day_batch(self, date_from=None):
        """Return the ``hours_per_day`` of each employee's calendar, see :meth:`_get_calendars`.

        :return: ``{employee_id: float}``
        :rtype: dict[int, float]
        """
        res = super()._get_hours_per_day_batch(date_from=date_from)
        if not date_from:
            return res

        date_from = fields.Date.to_date(date_from)
        for employee_id, version in self._get_first_contract_version_at(date_from).items():
            res[employee_id] = version.resource_calendar_id.hours_per_day
        return res

    def _get_version_periods(self, start, stop, field=None, check_contract=False):
        """Split ``[start, stop]`` into the periods covered by each version, per employee.

        Each period is the intersection of ``[start, stop]`` with the version's
        ``[date_start, date_end]`` (an open-ended version is clipped at
        ``stop``). Days not covered by any version (e.g. before the first
        version) are simply absent. Works in batch.

        Example::

            employee._get_version_periods(date(2026, 1, 1), date(2026, 12, 31), 'wage')
            # {hr.employee(23,): [(date(2026, 1, 1), date(2026, 5, 31), 3000.0),
            #                     (date(2026, 6, 1), date(2026, 12, 31), 3500.0)]}

        :param datetime.date start: start of the period (inclusive)
        :param datetime.date stop: end of the period (inclusive)
        :param field: ``hr.version`` field name to map on each period, or a list
            of field names (values are then tuples); the version itself if empty
        :type field: str or list[str] or None
        :param bool check_contract: only consider the versions in contract
            during the period (:meth:`_get_versions_with_contract_overlap_with_period`)
        :return: ``{employee record: [(date_from, date_to, value), ...]}`` with
            inclusive dates, ordered by date (``defaultdict(list)``)
        :rtype: dict
        :raise UserError: if a field does not exist
        """
        if isinstance(field, list):
            if any(f not in self for f in field):
                raise UserError(self.env._(
                    "Some of these fields %(field_name)s don't exist on this model (hr.version).",
                    field_name=field,
                ))
        elif field and field not in self:
            raise UserError(self.env._(
                "This field %(field_name)s doesn't exist on this model (hr.version).",
                field_name=field,
            ))
        version_periods_by_employee = defaultdict(list)
        if check_contract:
            versions = self._get_versions_with_contract_overlap_with_period(start, stop)
        else:
            versions = self.version_ids.filtered_domain([
                ('date_start', '<=', stop),
                '|',
                    ('date_end', '=', False),
                    ('date_end', '>=', start),
            ])
        for version in versions:
            date_start = max(version.date_start, start)
            date_end = min(version.date_end or stop, stop)
            if date_end < start or date_start > stop or date_start > date_end:
                # not overlapping, this can happen if we check contract versions
                continue
            if isinstance(field, list):
                version_periods_by_employee[version.employee_id].append(
                    (date_start, date_end, tuple(version[f] for f in field)),
                )
            else:
                version_periods_by_employee[version.employee_id].append(
                    (date_start, date_end, version[field] if field else version),
                )
        return version_periods_by_employee

    def _get_calendar_periods(self, start, stop, check_contract=True):
        """Return the working schedule periods of the employees within ``[start, stop]``.

        Shortcut for ``_get_version_periods(start, stop, 'resource_calendar_id',
        check_contract)`` in sudo; note that ``check_contract`` defaults to
        ``True`` here, so periods out of contract are excluded.

        :param datetime.date start: start of the period (inclusive)
        :param datetime.date stop: end of the period (inclusive)
        :param bool check_contract: only consider the versions in contract
        :return: ``{employee record: [(date_from, date_to, resource.calendar), ...]}``
        :rtype: dict
        """
        return self.sudo()._get_version_periods(start, stop, 'resource_calendar_id', check_contract)

    def _adjust_leaves(self, leave_intervals):
        """Hook to alter the leave intervals subtracted from duration-based work intervals.

        Used by :meth:`_get_employee_unavailable_intervals`; overridden in
        ``hr_holidays``. Returns ``leave_intervals`` unchanged by default.

        :param Intervals leave_intervals: leave intervals of one employee
        :rtype: Intervals
        """
        return leave_intervals

    def _get_employee_unavailable_intervals(self, start, stop):
        """Return the unavailability intervals of each employee within ``[start, stop]`` (Gantt views).

        The available time is computed per version in contract (calendar and
        timezone of each version): work intervals for regular calendars, whole
        attendance days for duration-based calendars, everything but leaves for
        flexible calendars. Unavailability is the complement within
        ``[start, stop]``; an employee without contract in the period is
        unavailable the whole period.

        :param datetime.datetime start: timezone-aware start
        :param datetime.datetime stop: timezone-aware end
        :return: ``{employee_id: [{'start': datetime, 'stop': datetime}, ...]}``
            with UTC-aware datetimes
        :rtype: dict[int, list[dict]]
        """

        unavailability_mapping = defaultdict(list)
        start_dt = start.astimezone(UTC)
        stop_dt = stop.astimezone(UTC)
        full_interval = Intervals([(start_dt, stop_dt, self.env['resource.calendar.attendance'])])
        calendar_tz_periods_per_employee = self.sudo()._get_version_periods(
            (start_dt - relativedelta(days=1)).date(),
            (stop_dt + relativedelta(days=1)).date(),
            ['resource_calendar_id', 'tz'],
            check_contract=True,
        )

        work_resources_per_calendar = defaultdict(lambda: self.env['resource.resource'])
        attendance_resources_per_calendar = defaultdict(lambda: self.env['resource.resource'])
        leave_resources_per_calendar = defaultdict(lambda: self.env['resource.resource'])
        for employee, calendar_periods in calendar_tz_periods_per_employee.items():
            for period_start, period_stop, (calendar, tz) in calendar_periods:
                if calendar._is_flexible():
                    leave_resources_per_calendar[calendar, tz] += employee.resource_id
                elif any(calendar.attendance_ids.mapped('duration_based')):
                    attendance_resources_per_calendar[calendar, tz] += employee.resource_id
                    leave_resources_per_calendar[calendar, tz] += employee.resource_id
                else:
                    work_resources_per_calendar[calendar, tz] += employee.resource_id

        work_intervals_per_calendar = defaultdict()
        attendance_intervals_per_calendar = defaultdict()
        leave_intervals_per_calendar = defaultdict()
        # Standard Calendars
        for (calendar, tz), resources in work_resources_per_calendar.items():
            work_intervals_per_calendar[calendar, tz] = calendar._work_intervals_batch(start_dt, stop_dt, resources_per_tz={ZoneInfo(tz): resources})

        # Duration Based Calendars
        for (calendar, tz), resources in attendance_resources_per_calendar.items():
            attendance_intervals_per_calendar[calendar, tz] = calendar._attendance_intervals_batch(start_dt, stop_dt, resources_per_tz={ZoneInfo(tz): resources})
            for resource_id, work_intervals in attendance_intervals_per_calendar[calendar, tz].items():
                extended_intervals = Intervals([])
                for att_start, att_end, attendance in work_intervals:
                    if not attendance.duration_based:
                        extended_intervals |= Intervals([(att_start, att_end, attendance)])
                        continue
                    extended_start = datetime.combine(att_start.date(), time.min, ZoneInfo(tz))
                    extended_end = datetime.combine(att_end.date() + timedelta(days=1), time.min, ZoneInfo(tz))
                    extended_intervals |= Intervals([(extended_start, extended_end, attendance)])
                attendance_intervals_per_calendar[calendar, tz][resource_id] = extended_intervals

        # Flexible and Fully Flexible Calendars
        for (calendar, tz), resources in leave_resources_per_calendar.items():
            leave_intervals_per_calendar[calendar, tz] = calendar._leave_intervals_batch(start_dt, stop_dt, resources_per_tz={ZoneInfo(tz): resources})

        for employee, calendar_periods in calendar_tz_periods_per_employee.items():
            employee_work_intervals = []
            for period_start, period_stop, (calendar, tz) in calendar_periods:
                period_start_dt = datetime.combine(period_start, time.min).replace(tzinfo=ZoneInfo(tz))
                period_stop_dt = datetime.combine(period_stop + timedelta(days=1), time.min).replace(tzinfo=ZoneInfo(tz))
                period_interval = Intervals([(period_start_dt, period_stop_dt, calendar)])
                current_work_intervals = Intervals([])
                if calendar._is_flexible():
                    current_work_intervals = period_interval - leave_intervals_per_calendar[calendar, tz][employee.resource_id.id]
                elif any(calendar.attendance_ids.mapped('duration_based')):
                    current_work_intervals = period_interval & attendance_intervals_per_calendar[calendar, tz][employee.resource_id.id] \
                                          - employee._adjust_leaves(leave_intervals_per_calendar[calendar, tz][employee.resource_id.id])
                else:
                    current_work_intervals = period_interval & work_intervals_per_calendar[calendar, tz][employee.resource_id.id]
                for interval_start, interval_stop, interval_calendar in current_work_intervals:
                    employee_work_intervals += Intervals([(
                        interval_start.astimezone(ZoneInfo(tz)).replace(tzinfo=self.env.tz),
                        interval_stop.astimezone(ZoneInfo(tz)).replace(tzinfo=self.env.tz),
                        interval_calendar
                    )])
            unavailability_mapping[employee.resource_id.id] = full_interval - employee_work_intervals

        result = {}
        for employee in self:
            if employee not in calendar_tz_periods_per_employee:
                result[employee.id] = [{'start': start_dt, 'stop': stop_dt}]
                continue
            result[employee.id] = [{'start': interval[0].astimezone(UTC), 'stop': interval[1].astimezone(UTC)} for interval in unavailability_mapping.get(employee.resource_id.id, [])]

        return result

    @api.model
    def _get_all_versions_with_contract_overlap_with_period(self, date_from, date_to):
        """Return the versions of all employees in contract during ``[date_from, date_to]``.

        Model-level variant of :meth:`_get_versions_with_contract_overlap_with_period`
        (searches the employees accessible to the user, active ones only).

        :param datetime.date date_from: start of the period (inclusive)
        :param datetime.date date_to: end of the period (inclusive)
        :return: versions ordered by ``date_version``
        :rtype: hr.version
        """
        return self.search([
            ('version_ids', 'any', [
                ('contract_date_start', '!=', False),
                ('contract_date_start', '<=', date_to),
                '|',
                    ('contract_date_end', '=', False),
                    ('contract_date_end', '>=', date_from),
            ]),
        ])._get_versions_with_contract_overlap_with_period(date_from, date_to)

    def _get_unusual_days(self, date_from, date_to=None):
        """Return, for each day of the period, whether it is an "unusual" (non-working) day.

        Used by the calendar widgets to grey out days. Each day covered by a
        version in contract is evaluated with that version's calendar
        (``resource.calendar._get_unusual_days``, including public holidays
        of the company); days between contract periods are unusual. If no
        version is in contract during the period, all days are returned as
        **not** unusual. Single employee (or empty recordset).

        :param str date_from: start, formatted ``'%Y-%m-%d %H:%M:%S'``
        :param str date_to: end, same format; ``None`` means ``date_from``
            (a single day)
        :return: ``{'YYYY-MM-DD': bool}``, ``True`` for unusual days, both bounds included
        :rtype: dict[str, bool]
        """
        def _generate_unusual_days(date_from, date_to, value=True):
            return {
                day.strftime('%Y-%m-%d'): value
                for day in rrule(DAILY, date_from, until=date_to - relativedelta(days=1))
            }

        if self:
            self.ensure_one()
        date_from_date = datetime.strptime(date_from, '%Y-%m-%d %H:%M:%S').date()
        date_to_date = datetime.strptime(date_to, '%Y-%m-%d %H:%M:%S').date() if date_to else date_from_date
        employee_versions = self.env['hr.version'].sudo().search([
            ('employee_id', '=', self.id),
            ('active', '=', True),
        ]).filtered(
            lambda v: v._is_overlapping_period(date_from_date, date_to_date))
        if not employee_versions:
            return _generate_unusual_days(date_from_date, date_to_date + timedelta(days=1), value=False)
        unusual_days = {}
        next_date_to_generate = date_from_date
        for version in employee_versions:
            tmp_date_from = max(date_from_date, version.date_start)
            tmp_date_to = min(date_to_date, version.date_end) if version.date_end else date_to_date
            if tmp_date_from > next_date_to_generate:
                unusual_days.update(_generate_unusual_days(next_date_to_generate, tmp_date_from))
            unusual_days.update(version.resource_calendar_id.sudo(False)._get_unusual_days(
                datetime.combine(tmp_date_from, time.min, tzinfo=UTC),
                datetime.combine(tmp_date_to, time.max, tzinfo=UTC),
                self.company_id,
                self.resource_id,
            ))
            next_date_to_generate = tmp_date_to + timedelta(days=1)

        if date_to_date and next_date_to_generate <= date_to_date:
            unusual_days.update(_generate_unusual_days(next_date_to_generate, date_to_date + timedelta(days=1)))
        return unusual_days

    def formatted_employee_attendance_intervals(self, start, stop):
        """Return the expected attendances between two days, serialized for the web client.

        Whole days from ``start`` to ``stop`` are considered, in the employee's
        timezone. See :meth:`_get_expected_attendances`. Single employee only.

        :param start: first day (string or datetime, only the date part is used)
        :param stop: last day (string or datetime, only the date part is used)
        :return: ``[{'start': datetime, 'stop': datetime, 'attendance': [dict]}, ...]``
            where ``attendance`` is the ``read()`` of the ``resource.calendar.attendance``
        :rtype: list[dict]
        """
        self.ensure_one()
        employee_tz = ZoneInfo(self.tz) if self.tz else UTC
        date_start = datetime.combine(fields.Datetime.to_datetime(start), time.min, employee_tz)
        date_stop = datetime.combine(fields.Datetime.to_datetime(stop), time.max, employee_tz)
        employee_attendance_intervals = self._get_expected_attendances(date_start, date_stop)
        return [{'start': i[0], 'stop': i[1], 'attendance': i[2].read()} for i in employee_attendance_intervals]

    def _get_expected_attendances(self, date_from, date_to):
        """Return the work intervals the employee is expected to attend between two datetimes.

        Computed per version in contract during the period, each with its own
        calendar and timezone, minus the leaves counted as absence. Without any
        version in contract, the current calendar is used for the whole period.
        Single employee only.

        :param datetime.datetime date_from: timezone-aware start
        :param datetime.datetime date_to: timezone-aware end
        :return: intervals of ``(start, stop, resource.calendar.attendance)``
            with aware datetimes
        :rtype: Intervals
        """
        self.ensure_one()
        valid_versions = self.sudo()._get_versions_with_contract_overlap_with_period(date_from.date(), date_to.date())
        employee_tz = ZoneInfo(self.tz) if self.tz else None
        if not valid_versions:
            calendar = self.resource_calendar_id
            resources_per_tz = self._get_resources_per_tz(date_from)
            calendar_intervals = calendar._work_intervals_batch(
                date_from,
                date_to,
                resources_per_tz=resources_per_tz,
                compute_leaves=True,
                domain=[('company_id', 'in', [False, self.company_id.id]), ('count_as', '=', 'absence')])[self.resource_id.id]
            return calendar_intervals
        duration_data = Intervals()
        version_prev = datetime.combine(valid_versions[0].date_start, time.min, employee_tz)
        for version in valid_versions:
            version_start = datetime.combine(version.date_start, time.min, employee_tz)
            contract_start = datetime.combine(version.contract_date_start, time.min, employee_tz)
            version_end = datetime.combine(version.date_end or date.max, time.max, employee_tz)
            calendar = version.resource_calendar_id
            start_date = version_start if version_prev < version_start else contract_start
            resources_per_tz = version._get_resources_per_tz()
            version_intervals = calendar._work_intervals_batch(
                                    max(date_from, start_date),
                                    min(date_to, version_end),
                                    resources_per_tz=resources_per_tz,
                                    compute_leaves=True,
                                    domain=[('company_id', 'in', [False, self.company_id.id]), ('count_as', '=', 'absence')])[self.resource_id.id]
            duration_data = duration_data | version_intervals
        return duration_data

    def _get_calendar_attendances(self, date_from, date_to):
        """Return the working time (days and hours) between two datetimes, per the calendars in contract.

        Sums ``resource.calendar.get_work_duration_data`` over the versions in
        contract during the period (each with its calendar; the leaves counted
        as absence of the version's company or without company are deduced).
        Without any version in contract, the current calendar
        is used for the whole period. Single employee only.

        :param datetime.datetime date_from: start (timezone-aware if the employee has a timezone)
        :param datetime.datetime date_to: end (same remark)
        :return: ``{'days': float, 'hours': float}``
        :rtype: dict
        """
        self.ensure_one()
        valid_versions = self.sudo()._get_versions_with_contract_overlap_with_period(date_from.date(), date_to.date())
        employee_tz = ZoneInfo(self.tz) if self.tz else None
        if not valid_versions:
            calendar = self.resource_calendar_id
            return calendar.get_work_duration_data(
                date_from,
                date_to,
                domain=[('company_id', 'in', [False, self.company_id.id]), ('count_as', '=', 'absence')])
        duration_data = {'days': 0, 'hours': 0}
        for version in valid_versions:
            version_start = datetime.combine(version.date_start, time.min, employee_tz)
            version_end = datetime.combine(version.date_end or date.max, time.max, employee_tz)
            calendar = version.resource_calendar_id
            version_duration_data = calendar\
                .get_work_duration_data(
                    max(date_from, version_start),
                    min(date_to, version_end),
                    domain=[('company_id', 'in', [False, version.company_id.id]), ('count_as', '=', 'absence')])
            duration_data['days'] += version_duration_data['days']
            duration_data['hours'] += version_duration_data['hours']
        return duration_data

    @api.model
    def get_import_templates(self):
        return [{
            'label': self.env._('Template for Employees'),
            'template': '/hr/static/xls/hr_employee.xls'
        }]

    def _get_age(self, target_date=None):
        """Return the age of the employee in full years on ``target_date`` (today by default), 0 without birthday.

        :param target_date: reference date
        :type target_date: datetime.date or None
        :rtype: int
        """
        self.ensure_one()
        if target_date is None:
            target_date = fields.Date.context_today(self.env.user)
        return relativedelta(target_date, self.birthday).years if self.birthday else 0

    def _get_versions_with_contract_overlap_with_period(self, date_from, date_to):
        """Return the versions in effect, and in contract, at least one day of ``[date_from, date_to]``.

        Within a contract, a version is effective from its ``date_version``
        (the first version from the contract start) until the day before the
        next version of the same contract (the last one until the contract
        end). Versions of an overlapping contract that were superseded before
        the period (e.g. replaced on 1 March when asking for April) are
        excluded. Works in batch.

        :param datetime.date date_from: start of the period (inclusive)
        :param datetime.date date_to: end of the period (inclusive)
        :return: versions ordered by ``date_version``
        :rtype: hr.version
        """
        candidate_versions = self.version_ids.filtered_domain([
            ('contract_date_start', '!=', False), ('contract_date_start', '<=', date_to),
            '|', ('contract_date_end', '>=', date_from), ('contract_date_end', '=', False),
        ])
        versions_per_contract = defaultdict(lambda: self.env['hr.version'])
        for version in candidate_versions:
            key = (version.employee_id.id, version.contract_date_start, version.contract_date_end)
            versions_per_contract[key] += version

        result = self.env['hr.version']
        for (employee, contract_start, contract_end), versions in versions_per_contract.items():
            versions = versions.sorted('date_version')
            for index, version in enumerate(versions):
                # effective interval of this version within its contract
                eff_start = contract_start if index == 0 else version.date_version
                if index + 1 < len(versions):
                    eff_end = versions[index + 1].date_version - relativedelta(days=1)
                else:
                    eff_end = contract_end or date.max
                if eff_start <= date_to and eff_end >= date_from:
                    result += version
        return result.sorted('date_version')

    # ---------------------------------------------------------
    # Messaging
    # ---------------------------------------------------------

    def _phone_get_number_fields(self):
        return ['mobile_phone']

    def _phone_get_country_field(self):
        return 'company_country_id'

    def _mail_get_partner_fields(self, introspect_fields=False):
        return ['work_contact_id', 'user_partner_id']

    def action_open_versions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.employee_id.name + self.env._(' Records'),
            'path': 'versions',
            'res_model': 'hr.version',
            'view_mode': 'list,graph,pivot',
            'views': [(self.env.ref('hr.hr_version_list_view').id, 'list'), (False, 'graph'), (False, 'pivot')],
            'domain': [('employee_id', '=', self.employee_id.id)],
            'search_view_id': self.env.ref('hr.hr_version_search_view').id
        }

    def _store_avatar_card_fields(self, res: Store.FieldList):
        res.attr("resource_id", "_store_avatar_card_fields")
        res.one("user_id", "_store_avatar_card_fields")
        res.many("employee_skill_ids", ["color", "display_name"])
        res.extend([
            "active",
            "company_id",
            "hr_icon_display",
            "job_title",
            "name",
            "show_hr_icon_display",
        ])
        res.extend(["work_email", "work_phone"])

    def _store_im_status_fields(self, res: Store.FieldList):
        res.one("user_id", "_store_im_status_fields")
        res.extend([
            "active",
            "company_id",
            "is_off_hours",
            "work_location_type",
        ])

    @api.depends('bank_account_ids')
    def _compute_primary_bank_account_id(self):
        for employee in self:
            if employee.bank_account_ids:
                primary_account = min(
                    employee.bank_account_ids,
                    key=lambda acc: employee.salary_distribution.get(str(acc.id), {}).get("sequence", float("inf")),
                )
                employee.primary_bank_account_id = primary_account
            else:
                employee.primary_bank_account_id = False

    def get_accounts_with_fixed_allocations(self):
        """Return the bank accounts receiving a fixed amount (not a percentage) of the salary.

        Based on ``salary_distribution`` (``{str(bank_account_id): {'sequence',
        'amount', 'amount_is_percentage'}}``); accounts absent from it count as
        percentage-based. Single employee only.

        :rtype: res.partner.bank
        """
        self.ensure_one()
        return self.bank_account_ids.filtered(
            lambda a: not self.salary_distribution.get(str(a.id), {}).get('amount_is_percentage', True)
        )

    def get_bank_account_salary_allocation(self, account_id):
        """Return the salary allocation of a bank account from ``salary_distribution``.

        :param int account_id: ``res.partner.bank`` id
        :return: ``(amount, amount_is_percentage)``; ``(0, None)`` if the account
            has no allocation
        :rtype: tuple
        """
        ba_info = self.salary_distribution.get(str(account_id), {})
        return ba_info.get('amount', 0), ba_info.get('amount_is_percentage')

    def get_remaining_percentage(self):
        """Return the salary percentage not yet allocated to a bank account (never below 0).

        :rtype: float
        """
        self.ensure_one()
        distribution = self.salary_distribution or {}
        allocated = 0.0

        for ba_id, vals in distribution.items():
            if vals.get('amount_is_percentage'):
                allocated += vals.get('amount', 0.0)

        remaining = 100.0 - allocated
        return max(0.0, remaining)

    def action_open_allocation_wizard(self):
        self.ensure_one()
        wizard = self.env['hr.bank.account.allocation.wizard'].create({
            'employee_id': self.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Bank Account Allocation'),
            'res_model': 'hr.bank.account.allocation.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_toggle_primary_bank_account_trust(self):
        self.ensure_one()
        current_val = self.primary_bank_account_id.allow_out_payment
        self.primary_bank_account_id.allow_out_payment = not current_val

    def action_new_departure(self):
        """Open the "End of collaboration" wizard (``hr.employee.departure``) for the employee.

        If a departure is already planned (not applied), returns a client action
        asking to cancel it first.

        :raise UserError: if the employee is not on its latest version, if the contract of that
            version has ended, or if the employee has already departed
        """
        self.ensure_one()
        latest_version = self.employee_id.version_ids.sorted("date_version", reverse=True)[0]
        if self.version_id != latest_version:
            raise UserError(self.env._("You can only end the collaboration from the latest version of the employee."))
        today = fields.Date.context_today(self)
        if latest_version.contract_date_end and latest_version.contract_date_end < today:
            raise UserError(self.env._("You can't end the collaboration of an employee without contract, archive it instead."))
        if self.departure_id:
            if self.departure_id.apply_date:
                raise UserError(self.env._("You can't modify the departure of an employee that has already departed."))
            return {
                "type": "ir.actions.client",
                "tag": "departure_conflict_dialog",
                "params": {
                    "title": self.env._("Departure already configured"),
                    "message": self.env._(
                        "Employee is already configured in a Departure process. \n"
                        "Cancel it before configurating a new End of Collaboration."
                    ),
                    "employee_id": self.id,
                },
            }
        return {
            'name': self.env._('End of collaboration'),
            'res_model': 'hr.employee.departure',
            'type': 'ir.actions.act_window',
            'views': [(self.env.ref('hr.hr_employee_departure_view_form').id, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
            },
        }

    def action_cancel_departure(self):
        """Cancel the employee's departure: unarchive, restore the contract end date and delete the departure.

        The contract end date saved on the departure (``last_contract_date_end``)
        is restored on the contract that was ended. Versions deleted when the
        departure was applied are not restored.
        """
        self.ensure_one()
        self.action_unarchive()
        version = self._get_version(self.departure_id.departure_date)
        version.contract_date_end = self.departure_id.last_contract_date_end
        self.departure_id.unlink()

    def _get_working_periods_by_field(self, start, stop, field_key):
        """Return the contract periods of the employees overlapping ``[start, stop]``, keyed by ``field_key``.

        Used by Gantt views of non-employee models (keyed by e.g. resource or
        user). Each contract overlapping the period gives one entry (not
        clipped to the period); an employee without any contract gets the
        whole ``[start, stop]`` period.

        :param start: start of the period (string or naive UTC datetime)
        :param stop: end of the period (string or naive UTC datetime)
        :param str field_key: many2one field of ``hr.employee`` used as key,
            e.g. ``'resource_id'`` or ``'user_id'``
        :return: ``{field_key id: [{'start': ..., 'end': ...}, ...]}``. For
            contracts, ``start`` is the contract start date as a datetime string
            (midnight, not timezone-converted) and ``end`` is the end of the
            contract's last day in the user's timezone, as a naive UTC datetime
            string, or ``False`` if open-ended. For employees without contract,
            a single entry whose ``start``/``end`` are the given bounds as
            ``datetime`` objects (not strings).
        :rtype: dict[int, list[dict]]
        """

        working_periods = {employee[field_key].id: [] for employee in self}

        if self.ids:
            start, stop = fields.Datetime.from_string(start), fields.Datetime.from_string(stop)

            # Fetch the contracts (one row per contract, not per version) of the employees
            contracts = self.env["hr.version"].sudo()._read_group(
                domain=[
                    ("employee_id", "in", self.ids),
                    ('contract_date_start', '!=', False),
                ],
                groupby=['employee_id', 'contract_date_start:day', 'contract_date_end:day'],
            )

            employees_with_contract = self.env['hr.employee']
            for employee, contract_date_start, contract_date_end in contracts:
                employees_with_contract |= employee
                if contract_date_start > stop.date() or (contract_date_end and contract_date_end < start.date()):
                    continue
                field_key_id = employee[field_key].id
                end_datetime = contract_date_end and contract_date_end + relativedelta(hour=23, minute=59, second=59)
                if end_datetime:
                    end_datetime = end_datetime.replace(tzinfo=self.env.tz).astimezone(UTC).replace(tzinfo=None)
                    end_datetime = fields.Datetime.to_string(end_datetime)
                working_periods[field_key_id].append({
                    "start": fields.Datetime.to_string(contract_date_start),
                    "end": end_datetime,
                })
            for employee in self - employees_with_contract:
                working_periods[employee[field_key].id].append({
                    "start": start,
                    "end": stop,
                })
        return working_periods

    def get_multi_version_changes(self, version_changes):
        """Return a human-readable preview of changes to apply on several versions (web client).

        :param dict version_changes: ``{field_name: new_value}`` (ids for
            relational fields)
        :return: ``{'(Field label)': (old_value, new_value)}`` with values
            formatted as in tracking messages, old values read on ``self``
        :rtype: dict
        """
        version_changes_to_display = {}
        for field_name in version_changes:
            new_value = version_changes[field_name]
            field = self.env['ir.model.fields'].search([('model', '=', 'hr.version'), ('name', '=', field_name)])
            if field['relation']:
                new_value = self.env[field['relation']].search([('id', 'in', new_value)])
            tracking_values = self._create_mail_tracking_values(
                self[field_name], new_value,
                field_name, self._track_get_fields_info([field_name])[field_name],
            )
            display_field_name = '(' + tracking_values['field_label'] + ')'
            version_changes_to_display[display_field_name] = (tracking_values['old_value'], tracking_values['new_value'])
        return version_changes_to_display
