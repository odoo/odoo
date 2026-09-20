import re
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from random import choice
from string import digits

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models, tools
from odoo.exceptions import AccessError, RedirectWarning, UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.datetime import localize_standard, timezone
from odoo.libs.numbers import float_is_zero
from odoo.tools import SQL, Query, convert, email_normalize, format_time

from ..tools import debug_log as dbg
from odoo.addons.hr.models.hr_version import (
    format_date_abbr,
    remove_values_from_other_companies,
)
from odoo.addons.mail.tools.discuss import Store

_ALLOW_READ_HR_EMPLOYEE = object()


def _searches_for_absence(operator, value):
    if operator not in ("=", "!=", "in", "not in"):
        return None
    operands = (
        [value]
        if isinstance(value, str) or not hasattr(value, "__iter__")
        else list(value)
    )
    if not operands or any(operands):
        return None
    return operator in ("=", "in")


class HrEmployee(models.Model):
    _name = "hr.employee"
    _description = "Employee"
    _order = "name"
    _inherit = [
        "mixin.mail.thread.main.attachment",
        "mixin.mail.activity",
        "mixin.resource",
    ]
    _mail_post_access = "read"
    _primary_email = "work_email"
    _mail_partner_fields = ("partner_id",)
    _inherits = {"hr.version": "version_id", "res.partner": "partner_id"}

    _PUBLIC_PARTY_X2MANY_FIELDS = ("phone_ids",)

    _DIRTY_HACK_PRIVATE_FIELDS = (
        "activity_calendar_event_id",
        "rating_ids",
        "website_message_ids",
        "message_has_sms_error",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        tracking=True,
    )
    company_country_id = fields.Many2one(
        comodel_name="res.country",
        related="company_id.country_id",
        string="Company Country",
        readonly=True,
        groups="base.group_system,hr.group_hr_user",
    )
    company_country_code = fields.Char(
        related="company_country_id.code",
        string="Company Country Code",
        depends=["company_country_id"],
        readonly=True,
        groups="base.group_system,hr.group_hr_user",
    )
    country_code = fields.Char(
        related="version_id.country_code",
        inherited=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        readonly=True,
        groups="hr.group_hr_user",
    )
    resource_id = fields.Many2one(
        comodel_name="resource.resource",
        required=True,
    )
    name = fields.Char(  # noqa: E8529  identity column of a delegated record: 33 files join hr_employee in raw SQL and read it, and it leads _order and name search
        related="partner_id.name",
        string="Employee Name",
        inherited=True,
        store=True,
        copy=True,
        readonly=False,
        tracking=True,
    )
    active = fields.Boolean(  # noqa: E8529  identity column of a delegated record: every search filters on it, 33 files join hr_employee in raw SQL
        related="resource_id.active",
        string="Active",
        default=True,
        store=True,
        readonly=False,
    )
    user_id = fields.Many2one(  # noqa: E8529  UNIQUE (user_id, company_id) partial
        comodel_name="res.users",
        related="resource_id.user_id",
        string="User",
        precompute=True,
        store=True,
        index="btree_not_null",
        copy=False,
        readonly=False,
        ondelete="restrict",
        check_company=True,
    )
    share = fields.Boolean(related="user_id.share")

    version_id = fields.Many2one(
        comodel_name="hr.version",
        compute="_compute_version_id",
        search="_search_version_id",
        compute_sudo=True,
        store=False,
        required=True,
        ondelete="cascade",
        value_sql="_version_id_sql",
    )
    resource_calendar_id = fields.Many2one(
        related="version_id.resource_calendar_id",
        inherited=True,
        store=False,
        index=False,
        check_company=True,
    )
    work_location_id = fields.Many2one(
        related="version_id.work_location_id",
        inherited=True,
        store=False,
        check_company=True,
    )
    current_version_id = fields.Many2one(
        comodel_name="hr.version",
        compute="_compute_current_version_id",
        compute_sudo=True,
        store=True,
        bypass_search_access=True,
    )
    current_date_version = fields.Date(
        related="current_version_id.date_version",
        string="Current Date Version",
        groups="hr.group_hr_user",
    )
    version_ids = fields.One2many(
        comodel_name="hr.version",
        inverse_name="employee_id",
        string="Employee Versions",
        groups="hr.group_hr_user",
    )
    versions_count = fields.Integer(
        compute="_compute_versions_count",
        groups="hr.group_hr_user",
    )

    hr_presence_state = fields.Selection(
        selection=[
            ("present", "Present"),
            ("absent", "Absent"),
            ("archive", "Archived"),
            ("out_of_working_hour", "Off-Hours"),
        ],
        compute="_compute_hr_presence_state",
        compute_sudo=True,
    )
    last_activity = fields.Date(
        compute="_compute_last_activity_and_time",
        compute_sudo=True,
    )
    last_activity_time = fields.Char(
        compute="_compute_last_activity_and_time",
        compute_sudo=True,
    )
    hr_icon_display = fields.Selection(
        selection=[
            ("presence_present", "Present"),
            ("presence_out_of_working_hour", "Off-Hours"),
            ("presence_absent", "Absent"),
            ("presence_archive", "Archived"),
            ("presence_undetermined", "Undetermined"),
        ],
        compute="_compute_presence_icon",
        compute_sudo=True,
    )
    show_hr_icon_display = fields.Boolean(
        compute="_compute_presence_icon",
        compute_sudo=True,
    )
    newly_hired = fields.Boolean(
        compute="_compute_newly_hired",
        search="_search_newly_hired",
        compute_sudo=True,
    )

    work_email = fields.Char(
        compute="_compute_work_email",
        inverse="_inverse_work_email",
        search="_search_work_email",
        compute_sudo=True,
        readonly=False,
        tracking=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        index=True,
        copy=False,
        required=True,
        ondelete="restrict",
    )
    legal_name = fields.Char(
        compute="_compute_legal_name",
        store=True,
        readonly=False,
        groups="hr.group_hr_user",
    )
    is_user_active = fields.Boolean(
        related="user_id.active",
        string="User's active",
        groups="hr.group_hr_user",
    )
    private_phone_ids = fields.Many2many(
        related="private_address_id.phone_ids",
        string="Private Phone",
        readonly=False,
        groups="hr.group_hr_user",
    )
    private_email = fields.Char(
        related="private_address_id.email",
        string="Private Email",
        readonly=False,
        groups="hr.group_hr_user",
    )
    place_of_birth = fields.Char(
        related="private_address_id.place_of_birth",
        string="Place of Birth",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        related="private_address_id.nationality_id",
        string="Nationality (Country)",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )
    country_of_birth = fields.Many2one(
        comodel_name="res.country",
        related="private_address_id.country_of_birth",
        string="Country of Birth",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )
    birthday = fields.Date(
        related="private_address_id.birthdate",
        string="Birthday",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )
    birthday_public_display = fields.Boolean(
        string="Show to all employees",
        default=False,
        groups="hr.group_hr_user",
    )
    birthday_public_display_string = fields.Char(
        string="Public Date of Birth",
        compute="_compute_birthday_public_display_string",
        compute_sudo=True,
    )
    identification_id = fields.Char(
        string="Identification No",
        compute="_compute_identifiers",
        inverse="_inverse_identifiers",
        search="_search_identification_id",
        compute_sudo=True,
        tracking=True,
        groups="hr.group_hr_user",
        help="Enter the employee's National Identification Number issued by the government (e.g., Aadhaar, SIN, NIN). This is used for official records and statutory compliance.",
    )
    ssnid = fields.Char(
        string="SSN No",
        compute="_compute_identifiers",
        inverse="_inverse_identifiers",
        search="_search_ssnid",
        compute_sudo=True,
        tracking=True,
        groups="hr.group_hr_user",
        help="Social Security Number",
    )
    passport_id = fields.Char(
        string="Passport No",
        compute="_compute_identifiers",
        inverse="_inverse_identifiers",
        search="_search_passport_id",
        compute_sudo=True,
        tracking=True,
        groups="hr.group_hr_user",
    )
    passport_expiration_date = fields.Date(
        compute="_compute_identifiers",
        inverse="_inverse_identifiers",
        search="_search_passport_expiration_date",
        compute_sudo=True,
        tracking=True,
        groups="hr.group_hr_user",
    )
    sex = fields.Selection(
        related="private_address_id.gender",
        string="Gender",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
        help="This is the legal sex recognized by the state.",
    )

    private_address_id = fields.Many2one(
        comodel_name="res.partner",
        compute="_compute_private_address_id",
        store=True,
        index="btree_not_null",
        copy=False,
        groups="hr.group_hr_user",
        help="The employee's home address, held as a private child of their "
        "work contact rather than as columns here.",
    )
    private_street = fields.Char(
        related="private_address_id.street",
        string="Private Street",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )
    private_street2 = fields.Char(
        related="private_address_id.street2",
        string="Private Street2",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )
    private_city = fields.Char(
        related="private_address_id.city",
        string="Private City",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )
    allowed_country_state_ids = fields.Many2many(
        comodel_name="res.country.state",
        compute="_compute_allowed_country_state_ids",
        groups="hr.group_hr_user",
    )
    private_state_id = fields.Many2one(
        comodel_name="res.country.state",
        related="private_address_id.state_id",
        string="Private State",
        readonly=False,
        domain="[('id', 'in', allowed_country_state_ids)]",
        tracking=True,
        groups="hr.group_hr_user",
    )
    private_zip = fields.Char(
        related="private_address_id.zip",
        string="Private Zip",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )
    private_country_id = fields.Many2one(
        comodel_name="res.country",
        related="private_address_id.country_id",
        string="Private Country",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )
    marital = fields.Selection(
        related="private_address_id.marital",
        string="Marital Status",
        readonly=False,
        # No default and not required here: the facet carries the value, it
        # exists only once the employee is saved, and a default on this side
        # would be written onto the facet after every create -- a second
        # employment of the same person would reset the first one's answer.
        # res.partner defaults it to single when the facet is created.
        tracking=True,
        groups="hr.group_hr_user",
    )
    spouse_complete_name = fields.Char(
        related="private_address_id.spouse_complete_name",
        string="Spouse Legal Name",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )
    spouse_birthdate = fields.Date(
        related="private_address_id.spouse_birthdate",
        string="Spouse Birthdate",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )
    children = fields.Integer(
        related="private_address_id.dependent_children",
        string="Dependent Children",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )
    emergency_contact = fields.Char(
        tracking=True,
        groups="hr.group_hr_user",
    )
    emergency_phone_ids = fields.Many2many(
        comodel_name="phone.number",
        relation="hr_employee_emergency_phone_number_rel",
        column1="employee_id",
        column2="phone_number_id",
        groups="hr.group_hr_user",
    )

    distance_home_work = fields.Integer(
        string="Home-Work Distance",
        tracking=True,
        groups="hr.group_hr_user",
    )
    km_home_work = fields.Integer(
        string="Home-Work Distance in Km",
        compute="_compute_km_home_work",
        inverse="_inverse_km_home_work",
        store=True,
        tracking=True,
        groups="hr.group_hr_user",
    )
    distance_home_work_unit = fields.Selection(
        selection=[
            ("kilometers", "km"),
            ("miles", "mi"),
        ],
        string="Home-Work Distance unit",
        default="kilometers",
        required=True,
        tracking=True,
        groups="hr.group_hr_user",
    )
    work_location_name = fields.Char(
        compute="_compute_work_location_name",
        compute_sudo=True,
    )
    work_location_type = fields.Selection(
        selection=[("home", "Home"), ("office", "Office"), ("other", "Other")],
        compute="_compute_work_location_type",
        compute_sudo=True,
        tracking=True,
    )

    bank_account_ids = fields.Many2many(
        comodel_name="res.partner.bank",
        relation="employee_bank_account_rel",
        column1="employee_id",
        column2="bank_account_id",
        string="Bank Accounts",
        domain="[('partner_id', '=', partner_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        tracking=True,
        groups="hr.group_hr_user",
        help="Employee bank accounts to pay salaries",
    )
    is_trusted_bank_account = fields.Boolean(
        compute="_compute_is_trusted_bank_account",
        groups="hr.group_hr_user",
    )
    primary_bank_account_id = fields.Many2one(
        comodel_name="res.partner.bank",
        compute="_compute_primary_bank_account_id",
        groups="hr.group_hr_user",
    )
    has_multiple_bank_accounts = fields.Boolean(
        compute="_compute_has_multiple_bank_accounts",
        groups="hr.group_hr_user",
    )
    salary_distribution = fields.Json(
        compute="_compute_salary_distribution",
        store=True,
        readonly=False,
        groups="hr.group_hr_user",
    )

    visa_no = fields.Char(
        tracking=True,
        groups="hr.group_hr_user",
    )
    visa_expire = fields.Date(
        string="Visa Expiration Date",
        tracking=True,
        groups="hr.group_hr_user",
    )
    permit_no = fields.Char(
        string="Work Permit No",
        tracking=True,
        groups="hr.group_hr_user",
    )
    work_permit_expiration_date = fields.Date(
        tracking=True,
        groups="hr.group_hr_user",
    )
    has_work_permit = fields.Binary(
        string="Work Permit",
        groups="hr.group_hr_user",
    )
    work_permit_name = fields.Char(
        string="work_permit_name",
        compute="_compute_work_permit_name",
        groups="hr.group_hr_user",
    )

    certificate = fields.Selection(
        related="private_address_id.education_certificate",
        string="Certificate Level",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )
    study_field = fields.Char(
        related="private_address_id.study_field",
        string="Field of Study",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )
    study_school = fields.Char(
        related="private_address_id.study_school",
        string="School",
        readonly=False,
        tracking=True,
        groups="hr.group_hr_user",
    )

    driving_license = fields.Binary(groups="hr.group_hr_user")
    private_car_plate = fields.Char(
        groups="hr.group_hr_user",
        help="If you have more than one car, just separate the plates by a space.",
    )

    parent_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Manager",
        index=True,
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]",
        tracking=True,
    )
    child_ids = fields.One2many(
        comodel_name="hr.employee",
        inverse_name="parent_id",
        string="Direct subordinates",
    )
    coach_id = fields.Many2one(
        comodel_name="hr.employee",
        compute="_compute_coach_id",
        store=True,
        readonly=False,
        domain="['|', ('company_id', '=', False), ('company_id', 'in', allowed_company_ids)]",
        help='Select the "Employee" who is the coach of this employee.\n'
        'The "Coach" has no specific rights or responsibilities by default.',
    )

    tag_ids = fields.Many2many(
        comodel_name="res.partner.tag",
        relation="employee_tag_rel",
        column1="employee_id",
        column2="tag_id",
        string="Tags",
        groups="hr.group_hr_user",
    )
    tz = fields.Selection(tracking=True)
    color = fields.Integer(
        string="Color Index",
        default=0,
    )
    is_manager = fields.Boolean(compute="_compute_is_manager")
    is_user = fields.Boolean(compute="_compute_is_user")
    barcode = fields.Char(
        string="Badge ID",
        compute="_compute_identifiers",
        inverse="_inverse_identifiers",
        search="_search_barcode",
        compute_sudo=True,
        groups="hr.group_hr_user",
        help="ID used for employee identification.",
    )
    pin = fields.Char(
        string="PIN",
        copy=False,
        groups="hr.group_hr_user",
        help="PIN used to Check In/Out in the Kiosk Mode of the Attendance application (if enabled in Configuration) and to change the cashier in the Point of Sale application.",
    )
    message_main_attachment_id = fields.Many2one(groups="hr.group_hr_user")
    id_card = fields.Binary(
        string="ID Card Copy",
        groups="hr.group_hr_user",
    )
    related_partners_count = fields.Integer(
        compute="_compute_related_partners_count",
        groups="hr.group_hr_user",
    )
    employee_properties = fields.Properties(
        definition="company_id.employee_properties_definition",
        string="Properties",
        precompute=False,
        groups="hr.group_hr_user",
    )

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

    _BARCODE_DRAW_ATTEMPTS = 32

    _user_uniq = models.UniqueIndex(
        "(user_id, company_id) WHERE user_id IS NOT NULL",
        "A user cannot be linked to multiple employees in the same company.",
    )
    _partner_company_uniq = models.UniqueIndex(
        "(partner_id, company_id)",
        "A person cannot be two employees of the same company.",
    )

    _EXPIRY_REQUIRES_ITS_DOCUMENT = {
        "visa_expire": "visa_no",
        "work_permit_expiration_date": "permit_no",
    }

    @api.constrains(
        "visa_expire", "visa_no", "work_permit_expiration_date", "permit_no"
    )
    def _check_expiry_has_its_document(self):
        for employee in self:
            for expiry, number in self._EXPIRY_REQUIRES_ITS_DOCUMENT.items():
                if employee[expiry] and not employee[number]:
                    raise ValidationError(
                        self.env._(
                            "%(expiry_label)s cannot be set without "
                            "%(number_label)s: an expiry date belongs to a "
                            "document, and there is no document to attach it to.",
                            expiry_label=self._fields[expiry].string,
                            number_label=self._fields[number].string,
                        )
                    )

    @api.constrains("barcode")
    def _check_barcode(self):
        for employee in self:
            if employee.barcode and not (
                re.match(r"^[A-Za-z0-9]+$", employee.barcode)
                and len(employee.barcode) <= 18
            ):
                raise ValidationError(
                    self.env._(
                        "The Badge ID must be alphanumeric without any accents and no longer than 18 characters."
                    )
                )

    @api.constrains("user_id", "partner_id")
    def _check_work_contact_is_the_user_partner(self):
        for employee in self:
            user_partner = employee.user_id.partner_id
            if user_partner and employee.partner_id != user_partner:
                raise ValidationError(
                    self.env._(
                        "%(employee)s is linked to user %(user)s, so their work "
                        "contact must be that user's contact, not %(contact)s.",
                        employee=employee.display_name,
                        user=employee.user_id.display_name,
                        contact=employee.partner_id.display_name,
                    )
                )

    @api.constrains("salary_distribution")
    def _check_salary_distribution(self):
        for employee in self:
            dist = employee.salary_distribution
            if not dist:
                continue

            total = 0
            check_total = False
            for ba_values in dist.values():
                amount = ba_values.get("amount")
                is_percentage = ba_values.get("amount_is_percentage", True)
                if is_percentage and (
                    not isinstance(amount, (float, int)) or not (0 <= amount <= 100)
                ):
                    raise ValidationError(
                        self.env._(
                            "Each amount percentage must be a number between 0 and 100."
                        )
                    )
                if not is_percentage and (
                    isinstance(amount, bool)
                    or not isinstance(amount, (float, int))
                    or amount < 0
                ):
                    raise ValidationError(
                        self.env._(
                            "Each fixed amount must be a number of zero or more."
                        )
                    )
                if is_percentage:
                    check_total = True
                    total += amount

            dbg.logic.debug(
                "[employee:%s] salary distribution: %d accounts, percentage total=%s",
                employee.id,
                len(dist),
                total if check_total else None,
            )
            if check_total and not float_is_zero(total - 100.0, precision_digits=4):
                raise ValidationError(
                    self.env._(
                        "Total salary distribution on bank accounts must be exactly 100%."
                    )
                )

    @api.constrains("pin")
    def _check_pin(self):
        for employee in self:
            if employee.pin and not employee.pin.isdigit():
                raise ValidationError(
                    self.env._("The PIN must be a sequence of digits.")
                )

    @api.model
    def new(self, values=None, origin=None, ref=None):
        if not values:
            values = {}
        new_vals, version_vals = self._split_employee_and_version_vals(values)
        dbg.lifecycle.debug(
            "hr.employee.new: employee keys=%s, version keys=%s, origin=%s",
            dbg.keys(new_vals),
            dbg.keys(version_vals),
            dbg.rec(origin) if origin is not None else None,
        )

        employee = super().new(new_vals, origin, ref)
        version_vals["employee_id"] = employee
        self.env["hr.version"].new(
            {
                f_name: value
                for f_name, value in version_vals.items()
                if self.env["hr.version"]._has_field_access(
                    self.env["hr.version"]._fields[f_name], "read"
                )
            }
        )
        return employee

    @api.model
    def _follow_company_calendar(self, company_id, vals_list):
        default_calendar = self.env.company.resource_calendar_id
        if company_id == self.env.company.id or not default_calendar.company_id:
            dbg.logic.debug(
                "_follow_company_calendar: company %s keeps calendar %s (same "
                "company or calendar is shared)",
                company_id,
                default_calendar.id,
            )
            return
        company = self.env["res.company"].browse(company_id)
        for vals in vals_list:
            if (
                vals.get("resource_calendar_id", default_calendar.id)
                == default_calendar.id
            ):
                vals["resource_calendar_id"] = company.resource_calendar_id.id
                dbg.logic.debug(
                    "_follow_company_calendar: calendar %s -> %s for company %s",
                    default_calendar.id,
                    company.resource_calendar_id.id,
                    company_id,
                )

    @dbg.timed
    @api.model_create_multi
    def create(self, vals_list):
        dbg.lifecycle.debug(
            "hr.employee.create: %d vals, keys=%s, salary_simulation=%s",
            len(vals_list),
            dbg.vals_keys(vals_list),
            bool(self.env.context.get("salary_simulation")),
        )
        vals_per_company = defaultdict(list)
        private_address_vals = {}
        for idx, caller_vals in enumerate(vals_list):
            vals, address_vals = self._split_private_address_vals(caller_vals)
            if address_vals:
                private_address_vals[idx] = address_vals
                dbg.logic.debug(
                    "hr.employee.create[%d]: private address keys=%s split off",
                    idx,
                    dbg.keys(address_vals),
                )
            if vals.get("resource_id"):
                resource = self.env["resource.resource"].browse(vals["resource_id"])
                if "user_id" not in vals and resource.user_id:
                    vals["user_id"] = resource.user_id.id
                if not vals.get("partner_id") and resource.partner_id:
                    vals["partner_id"] = resource.partner_id.id
                if "name" not in vals and not vals.get("partner_id"):
                    vals["name"] = resource.name
                dbg.logic.debug(
                    "hr.employee.create[%d]: resource %s given, user_id=%s name=%r",
                    idx,
                    resource.id,
                    vals.get("user_id"),
                    vals.get("name"),
                )
            if vals.get("user_id"):
                user = self.env["res.users"].browse(vals["user_id"])
                vals.update(self._sync_user(user))
                vals["name"] = vals.get("name", user.name)
                dbg.pipeline.debug(
                    "[user:%s] -> employee vals: partner_id=%s name=%r",
                    user.id,
                    vals.get("partner_id"),
                    vals.get("name"),
                )
            vals_per_company[vals.get("company_id") or self.env.company.id].append(
                (idx, vals)
            )
        index_per_employee = {}
        party_tz = {}
        for company_vals_list in vals_per_company.values():
            for idx, vals in company_vals_list:
                if vals.get("tz"):
                    party_tz[idx] = vals["tz"]
        employees = self.env["hr.employee"]
        dbg.pipeline.debug(
            "hr.employee.create: %d company batch(es): %s",
            len(vals_per_company),
            dbg.lazy(lambda: {c: len(batch) for c, batch in vals_per_company.items()}),
        )
        for company, company_vals_list in vals_per_company.items():
            idxs, company_vals_list = zip(*company_vals_list, strict=True)
            self._update_party_vals(company, company_vals_list)
            self._follow_company_calendar(company, company_vals_list)
            with dbg.timer(
                self.env, "hr.employee.create: super for company %s", company
            ):
                new_employees = super(HrEmployee, self.with_company(company)).create(
                    company_vals_list
                )
            dbg.pipeline.debug(
                "[company:%s] created %s", company, dbg.rec(new_employees)
            )
            index_per_employee.update(dict(zip(new_employees, idxs, strict=True)))
            employees |= new_employees
        employees = employees.sorted(key=lambda employee: index_per_employee[employee])
        employees._bind_resource_to_party()
        for employee in employees:
            idx = index_per_employee[employee]
            if address_vals := private_address_vals.get(idx):
                dbg.pipeline.debug(
                    "[employee:%s] writing private address keys=%s",
                    employee.id,
                    dbg.keys(address_vals),
                )
                employee.write(address_vals)
            tz = party_tz.get(idx)
            if tz and employee.partner_id and not employee.partner_id.tz:
                employee.partner_id.sudo().tz = tz
                dbg.logic.debug(
                    "[employee:%s] party %s took tz %s",
                    employee.id,
                    employee.partner_id.id,
                    tz,
                )
        employees.version_id._check_fields(["employee_id"])
        if self.env.context.get("salary_simulation"):
            dbg.lifecycle.debug(
                "hr.employee.create: salary_simulation, returning %s early",
                dbg.rec(employees),
            )
            return employees
        employees.sudo()._update_missing_avatars()
        employee_departments = employees.department_id
        if employee_departments:
            channels = (
                self.env["discuss.channel"]
                .sudo()
                .search(
                    [("subscription_department_ids", "in", employee_departments.ids)]
                )
            )
            dbg.pipeline.debug(
                "hr.employee.create: departments %s -> resubscribing channels %s",
                dbg.rec(employee_departments),
                dbg.rec(channels),
            )
            channels._subscribe_users_automatically()
        onboarding_notes_bodies = {}
        hr_root_menu = self.env.ref("hr.menu_hr_root")
        for employee in employees:
            url = (
                "/odoo/%s/action-hr.plan_wizard_action?active_model=hr.employee&menu_id=%s"
                % (employee.id, hr_root_menu.id)
            )
            onboarding_notes_bodies[employee.id] = (
                Markup(
                    self.env._(
                        '<b>Congratulations!</b> May I recommend you to setup an <a href="%s">onboarding plan?</a>',
                    )
                )
                % url
            )
        employees._message_log_batch(onboarding_notes_bodies)
        employees.invalidate_recordset()
        dbg.lifecycle.debug("hr.employee.create: done %s", dbg.rec(employees))
        return employees

    @api.model
    def _create(self, data_list):
        version_ids = [vals["stored"].pop("version_id", None) for vals in data_list]
        result = super()._create(data_list)
        pairs = [
            (version_id, employee.id)
            for version_id, employee in zip(version_ids, result, strict=True)
            if version_id
        ]
        if not pairs:
            dbg.pipeline.debug(
                "hr.employee._create: no explicit version_id in %d rows", len(data_list)
            )
            return result
        dbg.pipeline.debug(
            "hr.employee._create: binding %d given version(s) to their employee: %s",
            len(pairs),
            pairs,
        )
        explicit_version_fields = {
            version_id: set(vals["inherited"].get("hr.version", ()))
            for version_id, vals in zip(version_ids, data_list, strict=True)
            if version_id
        }
        versions = self.env["hr.version"].browse([pair[0] for pair in pairs])
        versions.flush_recordset()
        self.env.cr.execute(
            SQL(
                "UPDATE hr_version AS v SET employee_id = p.employee_id,"
                " write_date = %s, write_uid = %s"
                " FROM (VALUES %s) AS p(id, employee_id) WHERE v.id = p.id",
                fields.Datetime.now(),
                self.env.uid,
                SQL(", ").join(
                    SQL("(%s, %s)", version_id, employee_id)
                    for version_id, employee_id in pairs
                ),
            )
        )
        versions.invalidate_recordset(["employee_id", "write_date", "write_uid"])
        versions.modified(["employee_id"])
        for version in versions:
            for fname in explicit_version_fields[version.id]:
                field = version._fields[fname]
                if field.compute and field.store:
                    self.env.remove_to_compute(field, version)
                    dbg.logic.debug(
                        "[version:%s] explicit %s kept over its compute",
                        version.id,
                        fname,
                    )
        return result

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        for vals in vals_list:
            if vals:
                vals.pop("employee_id", None)
        remove_values_from_other_companies(self, vals_list, default)
        dbg.lifecycle.debug(
            "hr.employee.copy_data on %s: keys=%s",
            dbg.rec(self),
            dbg.vals_keys(vals_list),
        )
        return vals_list

    @dbg.timed
    def write(self, vals):
        vals = dict(vals)
        dbg.lifecycle.debug(
            "hr.employee.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        if vals.get("company_id") and "resource_calendar_id" not in vals:
            company = self.env["res.company"].browse(vals["company_id"])
            moving = self.filtered(
                lambda employee: (
                    employee.resource_calendar_id.company_id
                    and employee.resource_calendar_id.company_id != company
                )
            )
            if moving:
                dbg.logic.debug(
                    "hr.employee.write: company -> %s, %s follow the company "
                    "calendar %s, %s keep theirs",
                    company.id,
                    dbg.rec(moving),
                    company.resource_calendar_id.id,
                    dbg.rec(self - moving),
                )
                (self - moving).write(vals)
                moving.write(
                    {**vals, "resource_calendar_id": company.resource_calendar_id.id}
                )
                return True
        if "partner_id" in vals:
            dbg.pipeline.debug(
                "hr.employee.write on %s: party change -> %s, unsubscribing former %s",
                dbg.rec(self),
                vals["partner_id"],
                self.partner_id.ids,
            )
            self.message_unsubscribe(self.partner_id.ids)
        user_to_sync = None
        if "user_id" in vals:
            user_to_sync = self.env["res.users"].browse(vals["user_id"])
            vals.update(self._sync_user(user_to_sync))
            dbg.pipeline.debug(
                "[user:%s] -> employee %s: partner_id=%s",
                user_to_sync.id,
                dbg.rec(self),
                vals.get("partner_id"),
            )
        if vals.get("department_id") or vals.get("user_id"):
            department_ids = (
                [vals["department_id"]]
                if vals.get("department_id")
                else self.department_id.ids
            )
            if department_ids:
                channels = (
                    self.env["discuss.channel"]
                    .sudo()
                    .search([("subscription_department_ids", "in", department_ids)])
                )
                dbg.pipeline.debug(
                    "hr.employee.write: departments %s -> resubscribing channels %s",
                    department_ids,
                    dbg.rec(channels),
                )
                channels._subscribe_users_automatically()
        if vals.get("departure_description"):
            dbg.lifecycle.debug(
                "hr.employee.write on %s: posting departure description",
                dbg.rec(self),
            )
            for employee in self:
                employee.message_post(
                    body=self.env._(
                        "Additional Information: \n %(description)s",
                        description=vals.get("departure_description"),
                    )
                )
        vals, address_vals = self._split_private_address_vals(vals)
        new_vals, version_vals = self._split_employee_and_version_vals(vals)
        dbg.logic.debug(
            "hr.employee.write on %s: split -> employee=%s version=%s address=%s",
            dbg.rec(self),
            dbg.keys(new_vals),
            dbg.keys(version_vals),
            dbg.keys(address_vals),
        )
        former_parties = {employee: employee.partner_id for employee in self}
        own_former_parties = {
            employee: party
            for employee, party in former_parties.items()
            if "partner_id" in vals
            and party.sudo().with_context(active_test=False).employee_ids == employee
        }
        with dbg.timer(self.env, "hr.employee.write: super on %s", dbg.rec(self)):
            res = super().write(new_vals)
        if "partner_id" in vals:
            dbg.pipeline.debug(
                "hr.employee.write on %s: party follow-ups (bank accounts, home, "
                "resource, identifiers, former party) former=%s",
                dbg.rec(self),
                dbg.lazy(lambda: {e.id: p.id for e, p in former_parties.items()}),
            )
            self._update_bank_account_contact(vals["partner_id"])
            self._reparent_private_address()
            self._bind_resource_to_party()
            self._move_identifiers_to_party(own_former_parties)
            self._retire_former_party(own_former_parties)
        if version_vals:
            version_vals["last_modified_date"] = fields.Datetime.now()
            version_vals["last_modified_uid"] = self.env.uid
            dbg.pipeline.debug(
                "hr.employee.write on %s -> version %s: keys=%s",
                dbg.rec(self),
                dbg.rec(self.version_id),
                dbg.keys(version_vals),
            )
            self.version_id.write(version_vals)

            for employee in self:
                employee._track_set_log_message(
                    Markup("<b>Modified on the Version '%s'</b>")
                    % employee.version_id.display_name
                )
        if address_vals:
            self._write_private_address(address_vals)
        return res

    @api.model
    def _selection_installed_langs(self):
        return self.env["res.lang"].get_installed()

    @api.model
    def _is_version_delegate_field(self, fname):
        field = self._fields.get(fname)
        return bool(
            field and field.inherited and field.related_field.model_name == "hr.version"
        )

    @api.model
    def _is_private_address_field(self, fname):
        field = self._fields.get(fname)
        return bool(
            field and field.related and field.related.startswith("private_address_id.")
        )

    @api.model
    def _split_private_address_vals(self, vals):
        employee_vals, address_vals = {}, {}
        for fname, value in vals.items():
            target = (
                address_vals if self._is_private_address_field(fname) else employee_vals
            )
            target[fname] = value
        return employee_vals, address_vals

    def _write_private_address(self, address_vals):
        dbg.pipeline.debug(
            "hr.employee._write_private_address on %s: keys=%s (sudo)",
            dbg.rec(self),
            dbg.keys(address_vals),
        )
        self._write_check_field_access(address_vals)
        # The address is a child partner, which the HR groups may not write. The field
        # groups checked above, as the caller, are the policy; the partner write is not.
        super(HrEmployee, self.sudo()).write(address_vals)

    def _create_parent_records(self, data_list):
        # The party is created or updated with the employee. hr.employee's create access
        # and the field groups create() checked on every value decide it, so an HR officer
        # needs no Contact Creation right of their own, as upstream's work contact did not.
        Party = self.env["res.partner"].sudo()
        party_vals_list = [
            data["inherited"].pop("res.partner", {}) for data in data_list
        ]
        to_create = []
        for data, party_vals in zip(data_list, party_vals_list, strict=True):
            if partner_id := data["stored"].get("partner_id"):
                if party_vals:
                    Party.browse(partner_id).write(party_vals)
            else:
                to_create.append((data, party_vals))
        if to_create:
            parties = Party.create([party_vals for _data, party_vals in to_create])
            for party, (data, _party_vals) in zip(parties, to_create, strict=True):
                data["stored"]["partner_id"] = party.id
            dbg.pipeline.debug(
                "hr.employee._create_parent_records: created parties %s",
                dbg.rec(parties),
            )
        dbg.pipeline.debug(
            "hr.employee._create_parent_records: %d rows, %d new parties, %d given",
            len(data_list),
            len(to_create),
            len(data_list) - len(to_create),
        )
        super()._create_parent_records(data_list)
        for data, party_vals in zip(data_list, party_vals_list, strict=True):
            if party_vals:
                data["inherited"]["res.partner"] = party_vals

    @api.model
    def _split_employee_and_version_vals(self, vals):
        employee_vals, version_vals = {}, {}
        for fname, value in vals.items():
            target = (
                version_vals
                if self._is_version_delegate_field(fname)
                else employee_vals
            )
            target[fname] = value
        return employee_vals, version_vals

    def _prepare_create_values(self, vals_list):
        result = super()._prepare_create_values(vals_list)
        new_vals_list = []
        Version = self.env["hr.version"]
        writable_version_fields = {
            fname
            for fname, field in Version._fields.items()
            if Version._has_field_access(field, "write")
        }
        for vals in result:
            employee_vals, version_vals = self._split_employee_and_version_vals(vals)
            dbg.logic.debug(
                "hr.employee._prepare_create_values: version keys dropped as "
                "unwritable: %s",
                dbg.lazy(
                    lambda version_vals=version_vals: sorted(
                        set(version_vals) - writable_version_fields
                    )
                ),
            )
            new_vals_list.append(
                {
                    **employee_vals,
                    **{
                        k: v
                        for k, v in version_vals.items()
                        if k in writable_version_fields
                    },
                }
            )
        return new_vals_list

    @api.depends(
        "bank_account_ids.allow_out_payment",
        "salary_distribution",
    )
    def _compute_is_trusted_bank_account(self):
        for employee in self:
            employee.is_trusted_bank_account = (
                employee.primary_bank_account_id.allow_out_payment
            )

    @api.depends("bank_account_ids")
    def _compute_has_multiple_bank_accounts(self):
        for employee in self:
            employee.has_multiple_bank_accounts = len(employee.bank_account_ids) > 1

    @api.depends("bank_account_ids")
    def _compute_salary_distribution(self):
        for employee in self:
            current_salary_distribution = employee.salary_distribution or {}
            current_ids = set(map(int, current_salary_distribution.keys()))
            account_ids = set(employee.bank_account_ids.ids)

            added_ids = account_ids - current_ids
            removed_ids = current_ids - account_ids
            unchanged_ids = account_ids & current_ids

            ordered = sorted(
                [
                    (int(i), data)
                    for i, data in current_salary_distribution.items()
                    if int(i) in unchanged_ids
                ],
                key=lambda x: (
                    not x[1].get("amount_is_percentage"),
                    x[1].get("sequence", float("inf")),
                ),
            )

            new_salary_distribution = {str(i): data for i, data in ordered}

            removed_percentage = sum(
                current_salary_distribution[str(i)]["amount"]
                for i in removed_ids
                if str(i) in current_salary_distribution
                and current_salary_distribution[str(i)]["amount_is_percentage"]
            )
            if removed_percentage and ordered:
                first_id = str(ordered[0][0])
                if new_salary_distribution[first_id]["amount_is_percentage"]:
                    new_salary_distribution[first_id]["amount"] = (
                        employee.currency_id.round(
                            new_salary_distribution[first_id]["amount"]
                            + removed_percentage
                        )
                    )
                    dbg.logic.debug(
                        "[employee:%s] salary distribution: %s%% of removed "
                        "accounts folded into account %s",
                        employee.id,
                        removed_percentage,
                        first_id,
                    )

            total_allocated = sum(
                d["amount"]
                for d in new_salary_distribution.values()
                if d["amount_is_percentage"]
            )
            remaining = max(0.0, 100.0 - total_allocated)
            seq = max(
                (d.get("sequence", 0) for d in new_salary_distribution.values()),
                default=0,
            )
            amount = (
                employee.currency_id.round(remaining / len(added_ids))
                if added_ids
                else 0.0
            )
            for i, new_id in enumerate(sorted(added_ids)):
                seq += 1
                if i == len(added_ids) - 1:
                    amount = employee.currency_id.round(remaining)
                new_salary_distribution[str(new_id)] = {
                    "amount": amount,
                    "amount_is_percentage": True,
                    "sequence": seq,
                }
                remaining -= amount

            dbg.logic.debug(
                "[employee:%s] salary distribution: added=%s removed=%s kept=%s -> %s",
                employee.id,
                sorted(added_ids),
                sorted(removed_ids),
                sorted(unchanged_ids),
                new_salary_distribution,
            )
            employee.salary_distribution = new_salary_distribution

    @api.depends("private_country_id")
    def _compute_allowed_country_state_ids(self):
        states = None
        for employee in self:
            if employee.private_country_id:
                employee.allowed_country_state_ids = (
                    employee.private_country_id.state_ids
                )
            else:
                if states is None:
                    states = self.env["res.country.state"].search([])  # noqa: E8507 - computed once, on first need
                employee.allowed_country_state_ids = states

    @api.depends("distance_home_work", "distance_home_work_unit")
    def _compute_km_home_work(self):
        for employee in self:
            employee.km_home_work = (
                employee.distance_home_work * 1.609
                if employee.distance_home_work_unit == "miles"
                else employee.distance_home_work
            )

    @api.depends(lambda self: [self._get_new_hire_field_name()])
    def _compute_newly_hired(self):
        new_hire_field = self._get_new_hire_field_name()
        new_hire_date = fields.Datetime.now() - timedelta(days=90)
        for employee in self:
            if not employee[new_hire_field]:
                employee.newly_hired = False
            elif not isinstance(employee[new_hire_field], datetime):
                employee.newly_hired = employee[new_hire_field] > new_hire_date.date()
            else:
                employee.newly_hired = employee[new_hire_field] > new_hire_date

    @api.depends("resource_calendar_id", "hr_presence_state")
    def _compute_presence_icon(self):
        for employee in self:
            employee.hr_icon_display = "presence_" + employee.hr_presence_state
            employee.show_hr_icon_display = bool(employee.user_id)

    @api.depends("name")
    def _compute_legal_name(self):
        for employee in self:
            if not employee.legal_name:
                employee.legal_name = employee.name

    @api.depends("current_version_id")
    @api.depends_context("version_id")
    def _compute_version_id(self):
        context_version_id = self.env.context.get("version_id", False)
        context_version = (
            self.env["hr.version"].browse(context_version_id).exists()
            if context_version_id
            else self.env["hr.version"]
        )

        dbg.logic.debug(
            "hr.employee._compute_version_id on %s: context version_id=%s -> %s",
            dbg.rec(self),
            context_version_id,
            dbg.rec(context_version),
        )
        for employee in self:
            if context_version and context_version.employee_id == employee:
                version = context_version
            else:
                version = employee.current_version_id
            employee.version_id = version

    @api.depends("version_id.work_location_id.name")
    def _compute_work_location_name(self):
        for employee in self:
            employee.work_location_name = (
                employee.version_id.work_location_id.name or None
            )

    @api.depends("version_id.work_location_id.location_type")
    def _compute_work_location_type(self):
        for employee in self:
            employee.work_location_type = (
                employee.version_id.work_location_id.location_type or "other"
            )

    @dbg.timed
    @api.depends("version_ids.date_version", "version_ids.active", "active")
    def _compute_current_version_id(self):
        Version = self.env["hr.version"].with_context(active_test=True)
        today = fields.Date.today()
        latest_version_by_employee = {}
        for version in Version.search(
            [("employee_id", "in", self.ids), ("date_version", "<=", today)],
            order="date_version asc",
        ):
            latest_version_by_employee[version.employee_id.id] = version
        employees_without_past_version = [
            employee.id
            for employee in self
            if employee.id not in latest_version_by_employee
        ]
        earliest_version_by_employee = {}
        if employees_without_past_version:
            for version in Version.search(
                [("employee_id", "in", employees_without_past_version)],
                order="date_version asc",
            ):
                earliest_version_by_employee.setdefault(version.employee_id.id, version)
        no_version = self.env["hr.version"]
        dbg.logic.debug(
            "hr.employee._compute_current_version_id on %s: %d with a past version, "
            "%d falling back to their earliest",
            dbg.rec(self),
            len(latest_version_by_employee),
            len(earliest_version_by_employee),
        )
        for employee in self:
            new_current_version = latest_version_by_employee.get(
                employee.id
            ) or earliest_version_by_employee.get(employee.id, no_version)
            if not new_current_version and not employee.id:
                new_current_version = employee.version_ids[:1]
            if employee.current_version_id != new_current_version:
                dbg.lifecycle.debug(
                    "[employee:%s] current version %s -> %s",
                    employee.id,
                    employee.current_version_id.id,
                    new_current_version.id,
                )
                employee.current_version_id = new_current_version

    @dbg.timed
    @api.depends("partner_id")
    def _compute_private_address_id(self):
        Partner = self.env["res.partner"].sudo()
        unresolved = self.filtered(lambda e: not e.private_address_id)
        existing_by_contact = {}
        for home in Partner.search(
            [
                ("parent_id", "in", unresolved.partner_id.ids),
                ("type", "=", "private"),
            ],
            order="id",
        ):
            existing_by_contact.setdefault(home.parent_id, home)
        to_create = []
        for employee in unresolved:
            contact = employee.partner_id
            if not contact:
                employee.private_address_id = False
            elif contact in existing_by_contact:
                employee.private_address_id = existing_by_contact[contact]
            elif not employee.id:
                employee.private_address_id = employee._origin.private_address_id
            else:
                to_create.append(employee)
        dbg.logic.debug(
            "hr.employee._compute_private_address_id on %s: %d unresolved, %d "
            "existing homes matched, %d to create",
            dbg.rec(self),
            len(unresolved),
            len(existing_by_contact),
            len(to_create),
        )
        if to_create:
            homes = Partner.create(
                [
                    {"parent_id": employee.partner_id.id, "type": "private"}
                    for employee in to_create
                ]
            )
            dbg.pipeline.debug(
                "hr.employee._compute_private_address_id: created homes %s for %s",
                dbg.rec(homes),
                dbg.rec(self.browse(e.id for e in to_create)),
            )
            for employee, home in zip(to_create, homes, strict=True):
                employee.private_address_id = home

    @api.depends("parent_id")
    def _compute_coach_id(self):
        for version in self:
            manager = version.parent_id
            previous_manager = version._origin.parent_id
            if manager and (
                version.coach_id == previous_manager or not version.coach_id
            ):
                dbg.logic.debug(
                    "[employee:%s] coach follows manager: %s -> %s",
                    version.id,
                    version.coach_id.id,
                    manager.id,
                )
                version.coach_id = manager
            elif not version.coach_id:
                version.coach_id = False

    def _has_field_access(self, field, operation):
        if not super()._has_field_access(field, operation):
            return False
        if self.env.su or self.env.user.has_group("hr.group_hr_user"):
            return True
        if field.name in self._DIRTY_HACK_PRIVATE_FIELDS:
            return False
        return not self._is_party_field(field.name) or self._is_public_party_field(
            field.name
        )

    def check_no_existing_contract(self, date):
        if isinstance(date, str):
            date = fields.Date.from_string(date)
        if self._is_in_contract(date):
            raise ValidationError(
                self.env._(
                    "The employee is already in contract on %s. "
                    "Please select a date outside existing contracts",
                    format_date_abbr(self.env, date),
                )
            )

    @api.onchange("contract_template_id")
    def _onchange_contract_template_id(self):
        if self.contract_template_id:
            whitelist = self.env["hr.version"]._get_whitelist_fields_from_template()
            applied = []
            for field in self.contract_template_id._fields:
                if (
                    field in whitelist
                    and not self.env["hr.version"]._fields[field].related
                ):
                    self[field] = self.contract_template_id[field]
                    applied.append(field)
            dbg.logic.debug(
                "[employee:%s] contract template %s applied fields %s",
                self._origin.id,
                self.contract_template_id.id,
                applied,
            )

    @api.onchange("contract_date_start")
    def _onchange_contract_date_start(self):
        if not self.contract_date_start:
            self.contract_date_end = False

    @api.depends("partner_id.email")
    def _compute_work_email(self):
        for employee in self:
            employee.work_email = employee.partner_id.email

    def _search_work_email(self, operator, value):
        return Domain("partner_id.email", operator, value)

    def _inverse_work_email(self):
        # Employee editors may maintain the work contact without Contacts rights.
        for employee in self:
            employee.partner_id.sudo().email = employee.work_email

    def _inverse_km_home_work(self):
        for employee in self:
            employee.distance_home_work = (
                employee.km_home_work / 1.609
                if employee.distance_home_work_unit == "miles"
                else employee.km_home_work
            )

    @api.constrains("ssnid")
    def _check_ssnid(self):
        pass

    @api.onchange("private_state_id")
    def _onchange_private_state_id(self):
        if self.private_state_id:
            self.private_country_id = self.private_state_id.country_id

    def _get_display_name_visible_ids(self) -> set[int]:
        if not self.env.user._is_internal():
            return super()._get_display_name_visible_ids()
        return set(self._ids)

    @api.model
    def _get_new_hire_field_name(self):
        return "create_date"

    def _get_first_versions(self):
        self.check_singleton()
        versions = self.version_ids
        if self.env.context.get("before_date"):
            versions = versions.filtered(
                lambda c: c.date_start <= self.env.context["before_date"]
            )
        return versions

    def _get_first_version_date(self, no_gap=True):
        self.check_singleton()
        if not self.env.su and not self.env.user.has_group("hr.group_hr_user"):
            raise AccessError(
                self.env._(
                    "Only HR users can access first version date on an employee."
                )
            )

        def get_versions_continuous(versions):
            if not versions:
                return self.env["hr.version"]
            if len(versions) == 1:
                return versions
            current_version = versions[0]
            older_versions = versions[1:]
            current_date = current_version.date_start
            for i, other_version in enumerate(older_versions):
                gap = (current_date - (other_version.date_end or date(2100, 1, 1))).days
                current_date = other_version.date_start
                if gap >= 4:
                    dbg.logic.debug(
                        "[employee:%s] version chain breaks before %s: gap %d days",
                        self.id,
                        other_version.id,
                        gap,
                    )
                    return older_versions[0:i] + current_version
            return older_versions + current_version

        versions = self._get_first_versions().sorted("date_start", reverse=True)
        if no_gap:
            versions = get_versions_continuous(versions)
        return min(versions.mapped("date_start")) if versions else False

    @dbg.timed
    def _cron_update_current_version_id(self):
        employees = self.with_context(active_test=False).search([])
        dbg.lifecycle.debug(
            "cron _cron_update_current_version_id: start, %d employees", len(employees)
        )
        employees._apply_pending_version_vals()
        employees._compute_current_version_id()
        dbg.lifecycle.debug("cron _cron_update_current_version_id: done")

    @dbg.timed
    def _apply_pending_version_vals(self):
        due = (
            self.env["hr.version"]
            .sudo()
            .search(
                [
                    ("employee_id", "in", self.ids),
                    ("pending_employee_vals", "!=", False),
                    ("date_version", "<=", fields.Date.today()),
                ],
                order="date_version asc, id asc",
            )
        )
        dbg.pipeline.debug(
            "_apply_pending_version_vals: %d version(s) due: %s", len(due), dbg.rec(due)
        )
        for version in due:
            vals = version.pending_employee_vals
            version.pending_employee_vals = False
            dbg.pipeline.debug(
                "[version:%s] pending vals keys=%s -> employee %s",
                version.id,
                dbg.keys(vals),
                version.employee_id.id,
            )
            version.employee_id.sudo().write(vals)

    def _search_version_id(self, operator, value):
        if operator in ("any", "any!"):
            return Domain("current_version_id", operator, value)
        domain = Domain("id", operator, value)
        return Domain(
            "id", "in", self.env["hr.version"]._search(domain).select("employee_id")
        )

    def _version_id_sql(self, field, alias: str, query: (Query | None) = None) -> SQL:
        # the current version's row: what the compute answers, as a column
        return self._field_to_sql(alias, "current_version_id", query)

    def _get_version(self, date=None):
        date = date or fields.Date.today()
        self.check_singleton()
        versions = self.version_ids.filtered_domain([("date_version", "<=", date)])
        return (
            max(versions, key=lambda v: v.date_version)
            if versions
            else self.version_ids[0]
        )

    @staticmethod
    def _coerce_date(value):
        if isinstance(value, str):
            return fields.Date.to_date(value)
        if isinstance(value, datetime):
            return value.date()
        return value

    def _get_new_version_dates(self, values):
        date = self._coerce_date(values.get("date_version", False))
        if not date:
            raise ValueError("date_version is required")

        date_from, date_to = self.sudo()._get_contract_dates(date)
        contract_date_start = self._coerce_date(
            values.get("contract_date_start", date_from)
        )
        contract_date_end = self._coerce_date(values.get("contract_date_end", date_to))

        if contract_date_end and not contract_date_start:
            raise UserError(
                self.env._("A contract end date requires a contract start date.")
            )
        dbg.logic.debug(
            "[employee:%s] new version dates: date=%s contract=%s..%s (existing "
            "contract on that day: %s..%s)",
            self.id,
            date,
            contract_date_start,
            contract_date_end,
            date_from,
            date_to,
        )
        return date, contract_date_start, contract_date_end, date_from, date_to

    def _update_sibling_contract_end(
        self, employee_id, date_from, date_to, contract_date_start, contract_date_end
    ):
        if not (
            date_from
            and contract_date_start == date_from
            and contract_date_end != date_to
        ):
            dbg.logic.debug(
                "[employee:%s] sibling contract end untouched (date_from=%s "
                "start=%s end=%s..%s)",
                employee_id,
                date_from,
                contract_date_start,
                contract_date_end,
                date_to,
            )
            return
        versions_sudo_to_sync = (
            self.env["hr.version"]
            .with_context(sync_contract_dates=True)
            .sudo()
            .search(
                [
                    ("employee_id", "=", employee_id),
                    ("contract_date_start", "=", date_from),
                ]
            )
        )
        if versions_sudo_to_sync:
            dbg.pipeline.debug(
                "[employee:%s] contract end %s -> %s on siblings %s",
                employee_id,
                date_to,
                contract_date_end,
                dbg.rec(versions_sudo_to_sync),
            )
            versions_sudo_to_sync.write({"contract_date_end": contract_date_end})

    @dbg.timed
    def create_version(self, values):
        self.check_singleton()
        dbg.lifecycle.debug(
            "[employee:%s] create_version: keys=%s", self.id, dbg.keys(values)
        )
        date, contract_date_start, contract_date_end, date_from, date_to = (
            self._get_new_version_dates(values)
        )

        version_to_copy = self._get_version(date)
        if not version_to_copy:
            version_to_copy = self.env["hr.version"].search(
                [("employee_id", "=", self.id)], limit=1
            )
        if version_to_copy.date_version == date:
            dbg.logic.debug(
                "[employee:%s] create_version: version %s already dated %s, reusing",
                self.id,
                version_to_copy.id,
                date,
            )
            return version_to_copy
        dbg.pipeline.debug(
            "[employee:%s] create_version: copying version %s (dated %s) as of %s",
            self.id,
            version_to_copy.id,
            version_to_copy.date_version,
            date,
        )

        employee_id = values.get("employee_id", self.id)
        self._update_sibling_contract_end(
            employee_id, date_from, date_to, contract_date_start, contract_date_end
        )
        self.check_access("write")
        version_to_copy.check_access("write")
        copy_vals = {
            "date_version": date,
            "employee_id": employee_id,
            "contract_date_start": contract_date_start,
            "contract_date_end": contract_date_end,
        }
        if "active" in values:
            copy_vals["active"] = values["active"]
        if calendar_id := values.get("resource_calendar_id"):
            copy_vals["resource_calendar_id"] = calendar_id
        new_version_vals = {
            field_name: field_value
            for field_name, field_value in values.items()
            if field_name not in copy_vals
        }
        version_fields = self.env["hr.version"]._fields
        employee_vals = {
            name: value
            for name, value in new_version_vals.items()
            if name not in version_fields
        }
        if employee_vals:
            # Employee-level values describe the person as of the version's
            # date: a version in effect writes them on the party now, a future
            # one carries them until its date arrives.
            if date <= fields.Date.today():
                dbg.pipeline.debug(
                    "[employee:%s] create_version: employee keys=%s written now",
                    self.id,
                    dbg.keys(employee_vals),
                )
                self.write(employee_vals)
            else:
                dbg.pipeline.debug(
                    "[employee:%s] create_version: employee keys=%s deferred to %s",
                    self.id,
                    dbg.keys(employee_vals),
                    date,
                )
                copy_vals["pending_employee_vals"] = employee_vals
            new_version_vals = {
                name: value
                for name, value in new_version_vals.items()
                if name in version_fields
            }
        copy_vals = {
            k: v
            for k, v in version_to_copy.sudo().copy_data()[0].items()
            if not (
                k in new_version_vals
                and version_fields[k].type in ["one2many", "many2many"]
            )
        } | copy_vals
        new_version = self.env["hr.version"].sudo().create(copy_vals).sudo(False)
        with self.env.protecting(
            [
                f
                for f_name, f in version_fields.items()
                if f_name not in new_version_vals and f.copy
            ],
            new_version,
        ):
            properties_fields_vals = {
                field_name: field_value
                for field_name, field_value in copy_vals.items()
                if version_fields[field_name].type == "properties"
                and field_name not in new_version_vals
            }
            if properties_fields_vals:
                new_version.sudo().write(properties_fields_vals)
            new_version.write(new_version_vals)
        dbg.lifecycle.debug(
            "[employee:%s] create_version: created version %s (keys=%s)",
            self.id,
            new_version.id,
            dbg.keys(new_version_vals),
        )
        return new_version

    def create_contract(self, date):
        self.check_singleton()
        if date and isinstance(date, str):
            date = fields.Date.to_date(date)

        contracts = self._get_contract_versions(date)[self.id]
        future_contract_dates = [d for d in list(contracts.keys()) if d > date]
        new_contract_date_end = (
            min(future_contract_dates) + relativedelta(days=-1)
            if future_contract_dates
            else False
        )

        dbg.logic.debug(
            "[employee:%s] create_contract on %s: %d future contract(s), end=%s",
            self.id,
            date,
            len(future_contract_dates),
            new_contract_date_end,
        )
        if version_same_date := self.version_ids.filtered(
            lambda v: v.date_version == date
        ):
            dbg.pipeline.debug(
                "[employee:%s] create_contract: version %s already dated %s, "
                "writing contract dates on it",
                self.id,
                version_same_date.id,
                date,
            )
            version_same_date.write(
                {
                    "contract_date_start": date,
                    "contract_date_end": new_contract_date_end,
                }
            )
            return version_same_date

        return self.create_version(
            {
                "date_version": date,
                "contract_date_start": date,
                "contract_date_end": new_contract_date_end,
            }
        )

    def _is_in_contract(self, date):
        return self._get_contract_dates(date) != (False, False)

    def _get_contracts(self, date_start=None, date_end=None, domain=None):
        contract_versions_by_employee = self._get_contract_versions(
            date_start, date_end, domain
        )
        contracts_by_employee = defaultdict(lambda: self.env["hr.version"])
        for employee_id, versions_by_contract in contract_versions_by_employee.items():
            for contract_versions in versions_by_contract.values():
                if not date_end:
                    contracts_by_employee[employee_id] |= contract_versions[-1]
                    continue
                effective_versions = contract_versions.filtered(
                    lambda v, date_end=date_end: v.date_version <= date_end
                )
                contracts_by_employee[employee_id] |= (
                    effective_versions[-1]
                    if effective_versions
                    else contract_versions[0]
                )
        return contracts_by_employee

    @dbg.timed
    def _get_contract_versions(self, date_start=None, date_end=None, domain=None):
        version_domain = Domain("contract_date_start", "!=", False)
        if self.ids:
            version_domain &= Domain("employee_id", "in", self.ids)
        elif not any(self._ids):
            version_domain &= Domain("employee_id", "in", self._origin.ids)
        if date_start:
            version_domain &= Domain("contract_date_end", "=", False) | Domain(
                "contract_date_end", ">=", date_start
            )
        if date_end:
            version_domain &= Domain("contract_date_start", "<=", date_end)
        if domain:
            version_domain &= domain
        all_versions = self.env["hr.version"]._read_group(
            domain=version_domain,
            groupby=["employee_id", "date_version:day"],
            aggregates=["id:recordset"],
        )
        contract_versions_by_employee = defaultdict(
            lambda: defaultdict(lambda: self.env["hr.version"])
        )
        for employee, _date_version, version in all_versions:
            first_version = next(iter(version), version)
            contract_versions_by_employee[employee.id][
                first_version.contract_date_start
            ] |= version
        dbg.logic.debug(
            "_get_contract_versions on %s (%s..%s): %d employee(s), %d contract(s)",
            dbg.rec(self),
            date_start,
            date_end,
            len(contract_versions_by_employee),
            sum(len(c) for c in contract_versions_by_employee.values()),
        )
        return contract_versions_by_employee

    def _get_all_contract_dates(self):
        self.check_singleton()
        return self.env["hr.version"]._read_group(
            [("employee_id", "=", self.id), ("contract_date_start", "!=", False)],
            ["contract_date_start:day", "contract_date_end:day"],
        )

    def _get_contract_dates(self, date):
        self.check_singleton()
        is_day_in_period = self.env["hr.version"]._is_day_in_period
        for date_from, date_to in self._get_all_contract_dates():
            if is_day_in_period(date_from, date_to, date):
                return date_from, date_to
        return False, False

    @api.depends("version_ids")
    def _compute_versions_count(self):
        version_count_per_employee = dict(
            self.env["hr.version"]._read_group(
                [("employee_id", "in", self.ids)],
                ["employee_id"],
                ["id:count"],
            ),
        )
        for employee in self:
            employee.versions_count = version_count_per_employee.get(employee, 0)

    def _search_newly_hired(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        new_hire_field = self._get_new_hire_field_name()
        threshold = fields.Datetime.now() - timedelta(days=90)
        if operator == "in":
            return Domain(new_hire_field, ">", threshold)
        return Domain(new_hire_field, "<=", threshold) | Domain(
            new_hire_field, "=", False
        )

    @api.model
    def _get_valid_employee_for_user(self):
        user = self.env.user
        employee = user.employee_id
        if not employee:
            user_employees = self.sudo().search([("user_id", "=", user.id)])
            employee = (
                user_employees.filtered(lambda r: r.company_id == user.company_id)
                or user_employees[:1]
            )
            dbg.logic.debug(
                "[user:%s] no employee in company %s, fallback among %s -> %s",
                user.id,
                self.env.company.id,
                dbg.rec(user_employees),
                dbg.rec(employee),
            )
        return employee

    @api.model
    def _search_member_of_department_domain(self, operator):
        if operator != "in":
            return NotImplemented
        department = self._get_valid_employee_for_user().department_id
        if not department:
            return Domain.FALSE
        return Domain("department_id", "child_of", department.ids)

    @api.model
    def _get_employee_ids_working_now(self):
        start_dt = fields.Datetime.now().replace(tzinfo=UTC)
        stop_dt = start_dt + timedelta(hours=1)
        employees_by_schedule = defaultdict(lambda: self.env["hr.employee"])
        for employee in self.sudo():
            employees_by_schedule[
                (employee.tz or "UTC", employee.resource_calendar_id)
            ] += employee
        working_now = []
        for (tz, calendar), employees in employees_by_schedule.items():
            if not calendar:
                dbg.logic.debug(
                    "_get_employee_ids_working_now: %s have no calendar (tz %s), "
                    "never working",
                    dbg.rec(employees),
                    tz,
                )
                continue
            zone = timezone(tz)
            work_intervals = calendar._work_intervals_batch(
                start_dt.astimezone(zone), stop_dt.astimezone(zone)
            )[False]
            if work_intervals:
                working_now += employees.ids
        dbg.logic.debug(
            "_get_employee_ids_working_now on %s: %d schedule group(s), %d working",
            dbg.rec(self),
            len(employees_by_schedule),
            len(working_now),
        )
        return working_now

    @dbg.timed
    @api.depends("user_id.im_status", "active")
    def _compute_hr_presence_state(self):
        employee_to_check_working = self.filtered(
            lambda e: (
                e.company_id.sudo().hr_presence_control_login
                and (e.user_id.sudo().presence_ids.status or "offline") == "offline"
            )
        )
        working_now_list = employee_to_check_working._get_employee_ids_working_now()
        dbg.logic.debug(
            "_compute_hr_presence_state on %s: %d offline under login control, "
            "%d of them in working hours",
            dbg.rec(self),
            len(employee_to_check_working),
            len(working_now_list),
        )
        for employee in self:
            state = "out_of_working_hour"
            if employee.company_id.sudo().hr_presence_control_login:
                presence_status = (
                    employee.user_id.sudo().presence_ids.status or "offline"
                )
                if presence_status == "online":
                    state = "present"
                elif presence_status == "offline" and employee.id in working_now_list:
                    state = "absent"
            if not employee.active:
                state = "archive"
            employee.hr_presence_state = state

    @api.depends("user_id")
    def _compute_last_activity_and_time(self):
        for employee in self:
            tz = employee.tz
            if last_presence := employee.user_id.sudo().presence_ids.last_presence:
                last_activity_datetime = (
                    last_presence.replace(tzinfo=UTC)
                    .astimezone(timezone(tz or "UTC"))
                    .replace(tzinfo=None)
                )
                employee.last_activity = last_activity_datetime.date()
                if employee.last_activity == fields.Date.today():
                    employee.last_activity_time = format_time(
                        self.env, last_presence, time_format="short"
                    )
                else:
                    employee.last_activity_time = False
            else:
                employee.last_activity = False
                employee.last_activity_time = False

    @api.depends("birthday", "birthday_public_display")
    def _compute_birthday_public_display_string(self):
        for employee in self:
            if employee.birthday and employee.birthday_public_display:
                employee.birthday_public_display_string = datetime.strftime(
                    employee.birthday, "%d %B"
                )
            else:
                employee.birthday_public_display_string = "hidden"

    @api.depends("name", "permit_no")
    def _compute_work_permit_name(self):
        for employee in self:
            name = employee.name.replace(" ", "_") + "_" if employee.name else ""
            permit_no = "_" + employee.permit_no if employee.permit_no else ""
            employee.work_permit_name = "%swork_permit%s" % (name, permit_no)

    def _get_partner_count_depends(self):
        return ["user_id", "partner_id"]

    @api.depends(lambda self: self._get_partner_count_depends())
    def _compute_related_partners_count(self):
        for employee in self:
            employee.related_partners_count = len(employee._get_related_partners())

    def _get_related_partners(self):
        return self.partner_id | self.user_id.partner_id

    def action_view_related_contacts(self):
        related_partners = self._get_related_partners()
        action = {
            "name": self.env._("Related Contacts"),
            "type": "ir.actions.act_window",
            "res_model": "res.partner",
            "view_mode": "form",
        }
        if len(related_partners) > 1:
            action["view_mode"] = "kanban,list,form"
            action["domain"] = [("id", "in", related_partners.ids)]
            return action
        if not related_partners:
            raise UserError(self.env._("%s has no related contact.", self.display_name))
        action["res_id"] = related_partners.id
        return action

    def action_create_user(self):
        self.check_singleton()
        if self.user_id:
            raise ValidationError(self.env._("This employee already has an user."))
        return {
            "name": self.env._("Create User"),
            "type": "ir.actions.act_window",
            "res_model": "res.users",
            "view_mode": "form",
            "view_id": self.env.ref("hr.view_users_simple_form").id,
            "target": "new",
            "context": {
                **self.env.context,
                "default_create_employee_id": self.id,
                "default_name": self.name,
                "default_login": self.work_email,
                "default_partner_id": self.partner_id.id,
            },
        }

    def action_create_users_confirmation(self):
        raise RedirectWarning(
            message=self.env._(
                "You're about to invite new users. %s users will be created with the default user template's rights. "
                "Adding new users may increase your subscription cost. Do you wish to continue?",
                len(self.ids),
            ),
            action=self.env.ref("hr.action_hr_employee_create_users").id,
            button_text=self.env._("Confirm"),
            additional_context={
                "selected_ids": self.ids,
            },
        )

    def _prepare_action_user_creation_notification(
        self, message, message_type, next_action
    ):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("User Creation Notification"),
                "type": message_type,
                "message": message,
                "next": next_action,
            },
        }

    def _prepare_user_vals_and_blocked_names(self):
        employee_emails = [
            normalized_email
            for employee in self
            for normalized_email in tools.mail.email_normalize_all(employee.work_email)
        ]
        conflicting_users = self.env["res.users"]
        if employee_emails:
            conflicting_users = self.env["res.users"].search(
                [
                    "|",
                    ("email_normalized", "in", employee_emails),
                    ("login", "in", employee_emails),
                ]
            )
        taken_addresses = set(conflicting_users.mapped("email_normalized")) | set(
            conflicting_users.mapped("login")
        )
        create_vals = []
        blocked = defaultdict(list)
        for employee in self:
            if employee.user_id:
                blocked["has_user"].append(employee.name)
                continue
            if not employee.work_email:
                blocked["no_email"].append(employee.name)
                continue
            login = email_normalize(employee.work_email)
            if not login:
                blocked["invalid_email"].append(employee.name)
                continue
            if login in taken_addresses:
                blocked["address_taken"].append(employee.name)
                continue
            create_vals.append(
                {
                    "create_employee_id": employee.id,
                    "name": employee.name,
                    "login": login,
                    "partner_id": employee.partner_id.id,
                }
            )
        dbg.logic.debug(
            "_prepare_user_vals_and_blocked_names on %s: %d creatable, %d taken "
            "addresses, blocked=%s",
            dbg.rec(self),
            len(create_vals),
            len(taken_addresses),
            dbg.lazy(lambda: {k: len(v) for k, v in blocked.items()}),
        )
        return create_vals, blocked

    def action_create_users(self):
        create_vals, blocked = self._prepare_user_vals_and_blocked_names()

        next_action = {"type": "ir.actions.act_window_close"}
        if create_vals:
            dbg.pipeline.debug(
                "action_create_users on %s: creating %d user(s) for employees %s",
                dbg.rec(self),
                len(create_vals),
                [vals["create_employee_id"] for vals in create_vals],
            )
            self.env["res.users"].create(create_vals)
            next_action = self._prepare_action_user_creation_notification(
                self.env._(
                    "Users %s creation successful",
                    ", ".join(vals["name"] for vals in create_vals),
                ),
                "success",
                {
                    "type": "ir.actions.client",
                    "tag": "soft_reload",
                    "params": {"next": next_action},
                },
            )

        for names, message_type, message in (
            (
                blocked["has_user"],
                "warning",
                self.env._(
                    "User already exists for Those Employees %s",
                    ", ".join(blocked["has_user"]),
                ),
            ),
            (
                blocked["no_email"],
                "danger",
                self.env._(
                    "You need to set the work email address for %s",
                    ", ".join(blocked["no_email"]),
                ),
            ),
            (
                blocked["invalid_email"],
                "danger",
                self.env._(
                    "You need to set a valid work email address for %s",
                    ", ".join(blocked["invalid_email"]),
                ),
            ),
            (
                blocked["address_taken"],
                "warning",
                self.env._(
                    "User already exists with the same email for Employees %s",
                    ", ".join(blocked["address_taken"]),
                ),
            ),
        ):
            if names:
                next_action = self._prepare_action_user_creation_notification(
                    message, message_type, next_action
                )
        return next_action

    def _is_party_field(self, fname):
        field = self._fields[fname]
        return bool(
            field.inherited and field.inherited_field.model_name == "res.partner"
        )

    def _is_public_party_field(self, fname):
        """A party field a public-profile reader may read through the employee:
        one the partner stores as a column, which the reader could read on the
        partner itself, plus the work channels every internal user reads off a
        colleague. Other computed and x2many party fields reach into models the
        reader has no claim on and stay behind the profile."""
        field = self._fields[fname]
        return self._is_party_field(fname) and (
            fname.startswith(("image_", "avatar_"))
            or fname in self._PUBLIC_PARTY_X2MANY_FIELDS
            or (
                field.inherited_field.store
                and field.inherited_field.type not in ("one2many", "many2many")
            )
        )

    @dbg.timed
    @api.model
    def notify_expiring_contract_work_permit(self):
        dbg.lifecycle.debug("cron notify_expiring_contract_work_permit: start")
        companies = self.env["res.company"].search([])
        employees_contract_expiring = self.env["hr.employee"]
        employees_work_permit_expiring = self.env["hr.employee"]

        today = fields.Date.today()
        companies_by_contract_period = defaultdict(lambda: self.env["res.company"])
        companies_by_permit_period = defaultdict(lambda: self.env["res.company"])
        for company in companies:
            companies_by_contract_period[company.contract_expiration_notice_period] += (
                company
            )
            companies_by_permit_period[
                company.work_permit_expiration_notice_period
            ] += company

        for notice_period, period_companies in companies_by_contract_period.items():
            employees_contract_expiring += self.env["hr.employee"].search(  # noqa: E8507 - one query per distinct notice period; companies sharing one were merged above
                [
                    ("company_id", "in", period_companies.ids),
                    ("contract_date_start", "!=", False),
                    ("contract_date_start", "<=", today),
                    ("contract_date_end", ">=", today),
                    (
                        "contract_date_end",
                        "<=",
                        today + relativedelta(days=notice_period),
                    ),
                ]
            )
        for notice_period, period_companies in companies_by_permit_period.items():
            employees_work_permit_expiring += self.env["hr.employee"].search(  # noqa: E8507 - one query per distinct notice period; companies sharing one were merged above
                [
                    ("company_id", "in", period_companies.ids),
                    ("work_permit_expiration_date", ">=", today),
                    (
                        "work_permit_expiration_date",
                        "<=",
                        today + relativedelta(days=notice_period),
                    ),
                ]
            )

        dbg.logic.debug(
            "notify_expiring_contract_work_permit: %d companies in %d contract "
            "period(s) and %d permit period(s); contracts expiring %s, permits "
            "expiring %s",
            len(companies),
            len(companies_by_contract_period),
            len(companies_by_permit_period),
            dbg.rec(employees_contract_expiring),
            dbg.rec(employees_work_permit_expiring),
        )
        for employee in employees_contract_expiring:
            employee._schedule_expiry_activity(
                employee.contract_date_end,
                self.env._("The contract of %s is about to expire.", employee.name),
            )

        for employee in employees_work_permit_expiring:
            employee._schedule_expiry_activity(
                employee.work_permit_expiration_date,
                self.env._("The work permit of %s is about to expire.", employee.name),
            )

        dbg.lifecycle.debug("cron notify_expiring_contract_work_permit: done")
        return True

    def _schedule_expiry_activity(self, date_deadline, summary):
        self.check_singleton()
        already_scheduled = (
            self.env["mail.activity"]
            .sudo()
            .search_count(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", self.id),
                    ("date_deadline", "=", date_deadline),
                    ("summary", "=", summary),
                ],
                limit=1,
            )
        )
        if already_scheduled:
            dbg.logic.debug(
                "[employee:%s] expiry activity for %s already scheduled, skipped",
                self.id,
                date_deadline,
            )
            return
        dbg.pipeline.debug(
            "[employee:%s] scheduling expiry activity for %s to user %s",
            self.id,
            date_deadline,
            self.hr_responsible_id.id or self.env.uid,
        )
        self.with_context(mail_activity_quick_update=True).activity_schedule(
            "mail.mail_activity_data_todo",
            date_deadline,
            summary,
            user_id=self.hr_responsible_id.id or self.env.uid,
        )

    def _load_demo_data(self):
        self.sudo()._load_scenario()
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    @api.onchange("user_id")
    def _onchange_user(self):
        self.update(self._sync_user(self.user_id))
        if not self.name:
            self.name = self.user_id.name

    @api.onchange("resource_calendar_id")
    def _onchange_timezone(self):
        if self.resource_calendar_id and not self.tz:
            self.tz = self.resource_calendar_id.tz

    @dbg.timed
    def unlink(self):
        resources = self.mapped("resource_id")
        dbg.lifecycle.debug(
            "hr.employee.unlink %s, then resources %s",
            dbg.rec(self),
            dbg.rec(resources),
        )
        result = super().unlink()
        resources.unlink()
        return result

    @api.onchange("company_id")
    def _onchange_company_id(self):
        if self._origin:
            return {
                "warning": {
                    "title": self.env._("Warning"),
                    "message": self.env._(
                        "To avoid multi company issues (losing the access to your previous contracts, leaves, ...), you should create another employee in the new company instead."
                    ),
                }
            }
        return None

    def _load_scenario(self):
        demo_tag = self.env.ref("hr.employee_category_demo", raise_if_not_found=False)
        if demo_tag:
            return
        convert.convert_file(
            self.env, "hr", "data/scenarios/hr_scenario.xml", None, mode="init"
        )

    @api.depends("bank_account_ids", "salary_distribution")
    def _compute_primary_bank_account_id(self):
        for employee in self:
            if employee.bank_account_ids:
                distribution = employee.salary_distribution or {}
                primary_account = min(
                    employee.bank_account_ids,
                    key=lambda acc: distribution.get(str(acc.id), {}).get(
                        "sequence", float("inf")
                    ),
                )
                employee.primary_bank_account_id = primary_account
            else:
                employee.primary_bank_account_id = False

    def action_unarchive(self):
        dbg.lifecycle.debug(
            "hr.employee.action_unarchive %s: clearing departure fields", dbg.rec(self)
        )
        res = super().action_unarchive()
        self.write(
            {
                "departure_reason_id": False,
                "departure_description": False,
                "departure_date": False,
            }
        )
        return res

    @dbg.timed
    def action_archive(self):
        archived_employees = self.filtered("active")
        dbg.lifecycle.debug(
            "hr.employee.action_archive %s: %s were active, no_wizard=%s",
            dbg.rec(self),
            dbg.rec(archived_employees),
            bool(self.env.context.get("no_wizard")),
        )
        res = super().action_archive()
        if archived_employees:
            employee_fields_to_empty = (
                self._get_employee_field_names_to_empty_on_archive()
            )
            user_fields_to_empty = self._get_user_field_names_to_empty_on_archive()
            employee_domain = Domain.OR(
                Domain(field, "in", archived_employees.ids)
                for field in employee_fields_to_empty
            )
            user_domain = Domain.OR(
                Domain(field, "in", archived_employees.user_id.ids)
                for field in user_fields_to_empty
            )
            employees = self.env["hr.employee"].search(employee_domain | user_domain)
            dbg.pipeline.debug(
                "hr.employee.action_archive: emptying %s / %s on %s",
                employee_fields_to_empty,
                user_fields_to_empty,
                dbg.rec(employees),
            )
            for field in employee_fields_to_empty:
                employees.filtered(lambda e, f=field: e[f] in archived_employees).write(
                    {field: False}
                )
            for field in user_fields_to_empty:
                employees.filtered(
                    lambda e, f=field: e[f] in archived_employees.user_id
                ).write({field: False})

            if len(archived_employees) == 1 and not self.env.context.get(
                "no_wizard", False
            ):
                dbg.logic.debug(
                    "[employee:%s] single archive -> departure wizard",
                    archived_employees.id,
                )
                return {
                    "type": "ir.actions.act_window",
                    "name": self.env._("Register Departure"),
                    "res_model": "hr.departure.wizard",
                    "view_mode": "form",
                    "target": "new",
                    "context": {"active_id": archived_employees.id},
                    "views": [[False, "form"]],
                }
        return res

    def action_toggle_primary_bank_account_trust(self):
        self.check_singleton()
        current_val = self.primary_bank_account_id.allow_out_payment
        self.primary_bank_account_id.allow_out_payment = not current_val

    def action_view_allocation_wizard(self):
        self.check_singleton()
        wizard = self.env["hr.bank.account.allocation.wizard"].create(
            {
                "employee_id": self.id,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Bank Account Allocation"),
            "res_model": "hr.bank.account.allocation.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_view_versions(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.name + self.env._(" Records"),
            "path": "versions",
            "res_model": "hr.version",
            "view_mode": "list,graph,pivot",
            "views": [
                (self.env.ref("hr.hr_version_list_view").id, "list"),
                (False, "graph"),
                (False, "pivot"),
            ],
            "domain": [("employee_id", "=", self.id)],
            "search_view_id": self.env.ref("hr.hr_version_search_view").id,
        }

    def action_generate_random_barcode(self):
        Employee = self.env["hr.employee"].sudo().with_context(active_test=False)
        minted = set()
        for employee in self:
            for _attempt in range(self._BARCODE_DRAW_ATTEMPTS):
                barcode = "041" + "".join(choice(digits) for _ in range(9))
                if barcode in minted:
                    continue
                if not Employee.search_count([("barcode", "=", barcode)], limit=1):  # noqa: E8507 - draws a random barcode until a free one turns up
                    break
            else:
                raise UserError(
                    self.env._(
                        "Could not generate a unique Badge ID after %(attempts)s"
                        " attempts. Please set one manually.",
                        attempts=self._BARCODE_DRAW_ATTEMPTS,
                    )
                )
            minted.add(barcode)
            dbg.logic.debug(
                "[employee:%s] badge minted after %d draw(s)", employee.id, _attempt + 1
            )
            employee.barcode = barcode

    def _get_schedule_tz(self):
        self.check_singleton()
        return (
            self.tz
            or self.resource_calendar_id.tz
            or self.company_id.resource_calendar_id.tz
            or "UTC"
        )

    def _get_schedule_tz_batch(self, dt=None):
        employees_by_id = self.grouped("id")

        def get_timezones_by_employee_id(employees, date_at=None):
            return {
                emp_id: employees_by_id[emp_id].tz or calendar.sudo().tz
                for emp_id, calendar in employees._get_calendars(date_at).items()
            }

        if not dt:
            return get_timezones_by_employee_id(self)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        employee_timezones = {}
        for tz, employees in self.grouped(lambda emp: emp._get_schedule_tz()).items():
            employee_timezones |= get_timezones_by_employee_id(
                employees, dt.astimezone(timezone(tz)).date()
            )
        return employee_timezones

    def _get_calendars(self, date_from=None):
        res = super()._get_calendars(date_from=date_from)
        if not date_from:
            return res

        date_from = fields.Date.to_date(date_from)
        for employee in self:
            employee_versions_sudo = employee.sudo().version_ids.filtered(
                lambda v: v._is_in_contract(date_from)
            )
            version_sudo = employee_versions_sudo[:1] or employee.sudo()._get_version(
                date_from
            )
            if version_sudo:
                res[employee.id] = version_sudo.resource_calendar_id.sudo(False)
                dbg.logic.debug(
                    "[employee:%s] calendar at %s from version %s (%s): %s",
                    employee.id,
                    date_from,
                    version_sudo.id,
                    "in contract" if employee_versions_sudo else "nearest",
                    version_sudo.resource_calendar_id.id,
                )
        return res

    @staticmethod
    def _combine_tz(day, moment, tz):
        naive = datetime.combine(day, moment)
        return localize_standard(naive, tz) if tz else naive

    @dbg.timed
    def _get_version_periods(self, start, stop, field_name=None, check_contract=False):
        if field_name and field_name not in self.env["hr.version"]._fields:
            raise UserError(
                self.env._(
                    "This field %(field_name)s doesn't exist on this model (hr.version).",
                    field_name=field_name,
                )
            )
        version_periods_by_employee = defaultdict(list)
        if check_contract:
            versions = self._get_versions_with_contract_overlap_with_period(
                start.date(), stop.date()
            )
        else:
            start_date, stop_date = start.date(), stop.date()
            versions = self.version_ids.filtered(
                lambda version: (
                    version.date_start
                    and version.date_start <= stop_date
                    and (not version.date_end or version.date_end >= start_date)
                )
            )
        dbg.logic.debug(
            "_get_version_periods on %s (%s..%s, field=%s, check_contract=%s): %s",
            dbg.rec(self),
            start,
            stop,
            field_name,
            check_contract,
            dbg.rec(versions),
        )
        for version in versions:
            calendar_tz = timezone(version.employee_id.resource_id.tz)
            date_start = self._combine_tz(
                version.date_start, time.min, calendar_tz
            ).astimezone(UTC)
            end_date = version.date_end
            if end_date:
                date_end = self._combine_tz(
                    end_date + relativedelta(days=1), time.min, calendar_tz
                ).astimezone(UTC)
            else:
                date_end = stop
            version_periods_by_employee[version.employee_id].append(
                (
                    max(date_start, start),
                    min(date_end, stop),
                    version[field_name] if field_name else version,
                )
            )
        return version_periods_by_employee

    def _get_calendar_periods(self, start, stop, check_contract=True):
        return self.sudo()._get_version_periods(
            start, stop, "resource_calendar_id", check_contract
        )

    @api.model
    def _get_all_versions_with_contract_overlap_with_period(self, date_from, date_to):
        all_employees = self.search(
            ["|", ("active", "=", True), ("active", "=", False)]
        )
        return all_employees._get_versions_with_contract_overlap_with_period(
            date_from, date_to
        )

    def _get_unusual_days(self, date_from, date_to=None):
        """Use the employee's schedule, or the current company for an empty recordset."""
        if self:
            self.check_singleton()
        date_from_date = datetime.strptime(date_from, "%Y-%m-%d %H:%M:%S").date()
        date_to_date = (
            datetime.strptime(date_to, "%Y-%m-%d %H:%M:%S").date()
            if date_to
            else date_from_date
        )
        if not self:
            dbg.logic.debug(
                "_get_unusual_days: no employee, company %s calendar %s",
                self.env.company.id,
                self.env.company.resource_calendar_id.id,
            )
            return self.env.company.resource_calendar_id._get_unusual_days(
                datetime.combine(date_from_date, time.min, tzinfo=UTC),
                datetime.combine(date_to_date, time.max, tzinfo=UTC),
                self.env.company,
            )
        employee_versions = (
            self.env["hr.version"]
            .sudo()
            .search([("employee_id", "=", self.id)])
            .filtered(lambda v: v._has_contract_overlap(date_from_date, date_to_date))
        )
        if not employee_versions:
            dbg.logic.debug(
                "[employee:%s] _get_unusual_days %s..%s: no contract version, "
                "using calendar %s",
                self.id,
                date_from_date,
                date_to_date,
                (self.resource_calendar_id or self.env.company.resource_calendar_id).id,
            )
            return (
                self.resource_calendar_id or self.env.company.resource_calendar_id
            )._get_unusual_days(
                datetime.combine(date_from_date, time.min).replace(tzinfo=UTC),
                datetime.combine(date_to_date, time.max).replace(tzinfo=UTC),
                self.company_id,
            )
        dbg.logic.debug(
            "[employee:%s] _get_unusual_days %s..%s: over versions %s",
            self.id,
            date_from_date,
            date_to_date,
            dbg.rec(employee_versions),
        )
        unusual_days = {}
        for version in employee_versions:
            tmp_date_from = max(date_from_date, version.date_start)
            tmp_date_to = (
                min(date_to_date, version.date_end)
                if version.date_end
                else date_to_date
            )
            unusual_days.update(
                version.resource_calendar_id.sudo(False)._get_unusual_days(
                    datetime.combine(
                        fields.Date.from_string(tmp_date_from), time.min
                    ).replace(tzinfo=UTC),
                    datetime.combine(
                        fields.Date.from_string(tmp_date_to), time.max
                    ).replace(tzinfo=UTC),
                    self.company_id,
                )
            )
        return unusual_days

    def _get_employee_field_names_to_empty_on_archive(self):
        return ["parent_id", "coach_id"]

    def _get_user_field_names_to_empty_on_archive(self):
        return []

    def _get_employee_tz(self):
        self.check_singleton()
        return timezone(self.tz) if self.tz else None

    def _get_fallback_calendar(self):
        self.check_singleton()
        return self.resource_calendar_id or self.company_id.resource_calendar_id

    def _get_version_windows(self, start, stop, tz=None):
        self.check_singleton()
        versions = self.sudo()._get_versions_with_contract_overlap_with_period(
            start.date(), stop.date()
        )
        for version in versions:
            window_start = self._combine_tz(version.date_start, time.min, tz)
            window_stop = (
                self._combine_tz(version.date_end, time.max, tz)
                if version.date_end
                else stop
            )
            calendar = (
                version.resource_calendar_id or version.company_id.resource_calendar_id
            )
            yield version, max(start, window_start), min(stop, window_stop), calendar

    def _get_fields_store_avatar_card(self, target):
        employee_fields = [
            "company_id",
            Store.One("department_id", ["name"]),
            "work_email",
            Store.One("work_location_id", ["location_type", "name"]),
            Store.Attr("work_phone", lambda e: e.phone_ids._primary().number),
        ]
        user = target.get_user(self.env)
        if user.has_group("hr.group_hr_user"):
            employee_fields.append("job_title")
        if len(self) > 0:
            self.fetch(
                [
                    field.field_name if isinstance(field, Store.Attr) else field
                    for field in employee_fields
                ]
            )
        return employee_fields

    def get_bank_account_salary_allocation(self, account_id):
        ba_info = (self.salary_distribution or {}).get(str(account_id), {})
        return ba_info.get("amount", 0), ba_info.get("amount_is_percentage", True)

    def get_remaining_percentage(self):
        self.check_singleton()
        distribution = self.salary_distribution or {}
        allocated = 0.0

        for vals in distribution.values():
            if vals.get("amount_is_percentage"):
                allocated += vals.get("amount", 0.0)

        remaining = 100.0 - allocated
        return max(0.0, remaining)

    def _get_accounts_with_fixed_allocations(self):
        self.check_singleton()
        distribution = self.salary_distribution or {}
        return self.bank_account_ids.filtered(
            lambda a: (
                not distribution.get(str(a.id), {}).get("amount_is_percentage", True)
            )
        )

    def _fold_version_windows(self, start, stop, fallback, per_window, combine):
        self.check_singleton()
        employee_tz = self._get_employee_tz()
        windows = list(self._get_version_windows(start, stop, employee_tz))
        if not windows:
            dbg.logic.debug(
                "[employee:%s] no version window in %s..%s, fallback calendar %s",
                self.id,
                start,
                stop,
                self._get_fallback_calendar().id,
            )
            return fallback(self._get_fallback_calendar(), employee_tz)
        dbg.logic.debug(
            "[employee:%s] folding %d version window(s) in %s..%s",
            self.id,
            len(windows),
            start,
            stop,
        )
        result = None
        for index, window in enumerate(windows):
            part = per_window(index, window, employee_tz)
            result = part if result is None else combine(result, part)
        return result

    def _get_attendance_intervals(self, start, stop, lunch=False):
        self.check_singleton()
        if not lunch:
            return self._get_expected_attendances(start, stop)
        resource = self.resource_id

        def fallback(calendar, _tz):
            return calendar._attendance_intervals_batch(
                start, stop, resource, lunch=True
            )[resource.id]

        def per_window(_index, window, _tz):
            _version, window_start, window_stop, calendar = window
            return calendar._attendance_intervals_batch(
                window_start, window_stop, resources=resource, lunch=True
            )[resource.id]

        return self._fold_version_windows(
            start, stop, fallback, per_window, lambda a, b: a | b
        )

    def _get_expected_attendances(self, date_from, date_to):
        self.check_singleton()
        resource = self.resource_id
        company_domain = [("company_id", "in", [False, self.company_id.id])]

        def fallback(calendar, tz):
            return calendar._work_intervals_batch(
                date_from,
                date_to,
                tz=tz,
                resources=resource,
                compute_leaves=True,
                domain=company_domain,
            )[resource.id]

        def per_window(index, window, tz):
            version, window_start, window_stop, calendar = window
            if index == 0:
                window_start = max(
                    date_from,
                    self._combine_tz(version.contract_date_start, time.min, tz),
                )
            return calendar._work_intervals_batch(
                window_start,
                window_stop,
                tz=tz,
                resources=resource,
                compute_leaves=True,
                domain=[*company_domain, ("time_type_id.is_work", "=", False)],
            )[resource.id]

        return self._fold_version_windows(
            date_from, date_to, fallback, per_window, lambda a, b: a | b
        )

    def _get_calendar_attendances(self, date_from, date_to):
        self.check_singleton()

        def fallback(calendar, tz):
            return calendar.with_context(employee_timezone=tz).get_work_duration_data(
                date_from,
                date_to,
                domain=[("company_id", "in", [False, self.company_id.id])],
            )

        def per_window(_index, window, tz):
            version, window_start, window_stop, calendar = window
            return calendar.with_context(employee_timezone=tz).get_work_duration_data(
                window_start,
                window_stop,
                domain=[("company_id", "in", [False, version.company_id.id])],
            )

        def combine(total, part):
            return {
                "days": total["days"] + part["days"],
                "hours": total["hours"] + part["hours"],
            }

        return self._fold_version_windows(
            date_from, date_to, fallback, per_window, combine
        )

    @api.model
    def get_import_templates(self):
        return [
            {
                "label": self.env._("Import Template for Employees"),
                "template": "/hr/static/xls/hr_employee.xls",
            }
        ]

    def _get_age(self, target_date=None):
        self.check_singleton()
        if target_date is None:
            target_date = fields.Date.context_today(self.env.user)
        return relativedelta(target_date, self.birthday).years if self.birthday else 0

    def _get_departure_date(self):
        self.check_singleton()
        if self.date_end and self.date_end < fields.Date.today():
            return self.departure_date
        return False

    def _get_versions_with_contract_overlap_with_period(self, date_from, date_to):
        return self.version_ids.filtered_domain(
            [
                ("contract_date_start", "!=", False),
                ("contract_date_start", "<=", date_to),
                "|",
                ("contract_date_end", ">=", date_from),
                ("contract_date_end", "=", False),
            ]
        )

    def get_avatar_card_data(self, field_names):
        stored = [fname for fname in field_names if fname != "work_phone"]
        data = self.read(stored)
        if "work_phone" in field_names:
            for employee, values in zip(self, data, strict=True):
                values["work_phone"] = employee.phone_ids._primary().number
        return data

    def _update_missing_avatars(self):
        if not self.env["ir.ui.view"].sudo(False).has_access("write"):
            dbg.logic.debug(
                "_update_missing_avatars on %s: no ir.ui.view write access, skipped",
                dbg.rec(self),
            )
            return
        for partner in self.partner_id:
            if partner.image_1920 or not (partner.name or "").strip():
                continue
            dbg.pipeline.debug("[party:%s] generating avatar svg", partner.id)
            partner.image_1920 = partner._prepare_avatar_svg()

    def _sync_user(self, user):
        vals = {"user_id": user.id}
        if user:
            vals["partner_id"] = user.partner_id.id
        return vals

    def _bind_resource_to_party(self):
        for employee in self:
            if employee.resource_id.partner_id != employee.partner_id:
                dbg.pipeline.debug(
                    "[employee:%s] resource %s party %s -> %s",
                    employee.id,
                    employee.resource_id.id,
                    employee.resource_id.partner_id.id,
                    employee.partner_id.id,
                )
                employee.resource_id.partner_id = employee.partner_id

    def _update_party_vals(self, company_id, vals_list):
        unbound = [
            vals
            for vals in vals_list
            if not vals.get("resource_id") and not vals.get("partner_id")
        ]
        parties = (
            self.env["res.partner"]
            .sudo()
            .create(
                [
                    {"name": vals.get("name"), "tz": vals.get("tz") or False}
                    for vals in unbound
                ]
            )
        )
        for vals, party in zip(unbound, parties, strict=True):
            vals["partner_id"] = party.id
        pending = [vals for vals in vals_list if not vals.get("resource_id")]
        resource_by_party = {
            resource.partner_id.id: resource
            for resource in self.env["res.partner"]
            .browse([vals["partner_id"] for vals in pending])
            ._get_resources(self.env["res.company"].browse(company_id))
        }
        for vals in pending:
            if resource := resource_by_party.get(vals["partner_id"]):
                dbg.pipeline.debug(
                    "[party:%s] employee takes existing resource %s",
                    vals["partner_id"],
                    resource.id,
                )
                vals["resource_id"] = resource.id

    def _prepare_resource_values(self, vals, tz):
        resource_vals = super()._prepare_resource_values(vals, tz)
        resource_vals["partner_id"] = vals.get("partner_id")
        user_id = vals.pop("user_id", None)
        if user_id:
            resource_vals["user_id"] = user_id
        active_status = vals.get("active")
        if active_status is not None:
            resource_vals["active"] = active_status
        return resource_vals

    _IDENTIFIER_TYPES = {
        "identification_id": "NATIONAL_ID",
        "ssnid": "SSN",
        "passport_id": "PASSPORT",
        "barcode": "BADGE",
    }
    _IDENTIFIER_EXPIRY = {
        "PASSPORT": "passport_expiration_date",
    }

    @api.depends(
        "partner_id.identifier_ids.type_id",
        "partner_id.identifier_ids.value",
        "partner_id.identifier_ids.valid_until",
    )
    def _compute_identifiers(self):
        for employee in self:
            by_code = {
                identifier.type_id.code: identifier
                for identifier in employee.partner_id.identifier_ids
            }
            for fname, code in self._IDENTIFIER_TYPES.items():
                employee[fname] = by_code[code].value if code in by_code else False
            for code, fname in self._IDENTIFIER_EXPIRY.items():
                row = by_code.get(code)
                employee[fname] = row.valid_until if row else False

    def _inverse_identifiers(self):
        Type = self.env["res.partner.identifier.type"].sudo()
        types = {
            identifier_type.code: identifier_type
            for identifier_type in Type.search(
                [("code", "in", list(self._IDENTIFIER_TYPES.values()))]
            )
        }
        for employee in self:
            partner = employee.partner_id.sudo()
            by_code = {
                identifier.type_id.code: identifier
                for identifier in partner.identifier_ids
            }
            for fname, code in self._IDENTIFIER_TYPES.items():
                value = employee[fname]
                row = by_code.get(code)
                vals = {"value": value}
                expiry = self._IDENTIFIER_EXPIRY.get(code)
                if expiry:
                    vals["valid_until"] = employee[expiry]
                if not value:
                    if expiry and employee[expiry]:
                        raise ValidationError(
                            self.env._(
                                "%(expiry_label)s cannot be set without "
                                "%(number_label)s: an expiry date belongs to a "
                                "document, and there is no document to attach "
                                "it to.",
                                expiry_label=self._fields[expiry].string,
                                number_label=self._fields[fname].string,
                            )
                        )
                    if row:
                        dbg.lifecycle.debug(
                            "[employee:%s] identifier %s cleared, row %s unlinked",
                            employee.id,
                            code,
                            row.id,
                        )
                        row.unlink()
                    continue
                if row:
                    changed = {k: v for k, v in vals.items() if row[k] != v}
                    if changed:
                        dbg.lifecycle.debug(
                            "[employee:%s] identifier %s row %s: %s changed",
                            employee.id,
                            code,
                            row.id,
                            dbg.keys(changed),
                        )
                        row.write(changed)
                else:
                    dbg.lifecycle.debug(
                        "[employee:%s] identifier %s created on party %s",
                        employee.id,
                        code,
                        partner.id,
                    )
                    partner.identifier_ids.create(
                        {"partner_id": partner.id, "type_id": types[code].id, **vals}
                    )

    @api.model
    def _search_identifier(self, code, operator, value):
        absent = _searches_for_absence(operator, value)
        if absent is not None:
            return [
                (
                    "partner_id.identifier_ids",
                    "not any" if absent else "any",
                    [("type_id.code", "=", code)],
                )
            ]
        return [
            (
                "partner_id.identifier_ids",
                "any",
                [("type_id.code", "=", code), ("value", operator, value)],
            )
        ]

    def _search_identification_id(self, operator, value):
        return self._search_identifier("NATIONAL_ID", operator, value)

    def _search_ssnid(self, operator, value):
        return self._search_identifier("SSN", operator, value)

    def _search_passport_id(self, operator, value):
        return self._search_identifier("PASSPORT", operator, value)

    def _search_barcode(self, operator, value):
        return self._search_identifier("BADGE", operator, value)

    def _search_passport_expiration_date(self, operator, value):
        absent = _searches_for_absence(operator, value)
        if absent is not None:
            dated = [("type_id.code", "=", "PASSPORT"), ("valid_until", "!=", False)]
            has = "not any" if absent else "any"
            return [("partner_id.identifier_ids", has, dated)]
        return [
            (
                "partner_id.identifier_ids",
                "any",
                [("type_id.code", "=", "PASSPORT"), ("valid_until", operator, value)],
            )
        ]

    def _reparent_private_address(self):
        employees = self.sudo()
        other_residents = dict(
            employees.with_context(active_test=False)._read_group(
                [
                    ("private_address_id", "in", employees.private_address_id.ids),
                    ("id", "not in", employees.ids),
                ],
                ["private_address_id"],
                ["__count"],
            )
        )
        for employee in employees:
            home = employee.private_address_id
            contact = employee.partner_id
            if (
                home
                and contact
                and home.parent_id != contact
                and home not in other_residents
            ):
                dbg.pipeline.debug(
                    "[employee:%s] home %s reparented %s -> %s",
                    employee.id,
                    home.id,
                    home.parent_id.id,
                    contact.id,
                )
                home.parent_id = contact

    def _move_identifiers_to_party(self, former_parties):
        codes = set(self._IDENTIFIER_TYPES.values())
        for employee in self:
            former = former_parties.get(employee)
            party = employee.partner_id
            if not former or not party or former == party:
                continue
            held = {
                identifier.type_id.code for identifier in party.sudo().identifier_ids
            }
            wanted = codes - held
            to_move = former.sudo().identifier_ids.filtered(
                lambda identifier, wanted=wanted: identifier.type_id.code in wanted
            )
            if to_move:
                dbg.pipeline.debug(
                    "[employee:%s] identifiers %s move party %s -> %s (held: %s)",
                    employee.id,
                    dbg.rec(to_move),
                    former.id,
                    party.id,
                    sorted(held),
                )
                to_move.partner_id = party.id

    def _check_access(self, operation):
        if (
            operation == "read"
            and self.env.context.get("_allow_read_hr_employee")
            is _ALLOW_READ_HR_EMPLOYEE
        ):
            return None
        return super()._check_access(operation)

    @api.depends_context("uid")
    @api.depends("parent_id")
    def _compute_is_manager(self):
        user_employee = self.env.user.employee_id
        if not user_employee:
            self.is_manager = False
            return
        all_reports = set(
            self.env["hr.employee"]
            .sudo()
            .search([("id", "child_of", user_employee.id)])
            .ids
        )
        for employee in self:
            employee.is_manager = employee.id in all_reports

    @api.depends_context("uid")
    def _compute_is_user(self):
        user_employee_id = self.env.user.employee_id.id
        for employee in self:
            employee.is_user = employee.id == user_employee_id

    def _retire_former_party(self, former_parties):
        for employee in self:
            former = former_parties.get(employee)
            party = employee.partner_id
            if not former or not party or former == party:
                continue
            former = former.sudo()
            if (
                former.user_ids
                or former.employee_ids
                or former.is_company
                or former.parent_id
                or former.child_ids
            ):
                dbg.logic.debug(
                    "[employee:%s] former party %s kept: still referenced",
                    employee.id,
                    former.id,
                )
                continue
            if former.tag_ids:
                party.sudo().tag_ids = [(4, tag.id) for tag in former.tag_ids]
            dbg.lifecycle.debug(
                "[employee:%s] former party %s archived, %d tag(s) carried to %s",
                employee.id,
                former.id,
                len(former.tag_ids),
                party.id,
            )
            former.active = False

    def _update_bank_account_contact(self, partner_id):
        accounts_sudo = (
            self.env["res.partner.bank"].sudo().browse(self.bank_account_ids.ids)
        )
        to_move = accounts_sudo.filtered(
            lambda account: account.partner_id.id != partner_id
        )
        if not to_move:
            return
        trusted = to_move.filtered("allow_out_payment")
        dbg.pipeline.debug(
            "hr.employee._update_bank_account_contact on %s: accounts %s -> party "
            "%s, %s lose trust",
            dbg.rec(self),
            dbg.rec(to_move),
            partner_id,
            dbg.rec(trusted),
        )
        if trusted:
            trusted.allow_out_payment = False
        if partner_id:
            to_move.partner_id = partner_id
