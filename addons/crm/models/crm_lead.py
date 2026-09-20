import logging
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from markupsafe import Markup

from odoo import Command, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.datetime import timezone
from odoo.tools import (
    SQL,
    email_normalize_all,
    groupby,
    is_html_empty,
    parse_contact_from_email,
)
from odoo.tools.misc import get_lang
from odoo.tools.translate import _

from . import crm_stage
from odoo.addons.iap.tools import iap_tools
from odoo.addons.mail.tools import mail_validation
from odoo.addons.phone_validation.tools import phone_validation

_logger = logging.getLogger(__name__)


CRM_LEAD_FIELDS_TO_MERGE = [
    "campaign_id",
    "medium_id",
    "source_id",
    "email_cc",
    "name",
    "user_id",
    "color",
    "company_id",
    "lang_id",
    "team_id",
    "referred",
    "stage_id",
    "expected_revenue",
    "recurring_plan",
    "recurring_revenue",
    "create_date",
    "date_automation_last",
    "date_deadline",
    "partner_id",
    "title",
    "partner_name",
    "contact_name",
    "email_from",
    "function",
    "website",
]

PARTNER_FIELDS_TO_SYNC = [
    "lang",
    "phone_ids",
    "function",
    "website",
]

PARTNER_ADDRESS_FIELDS_TO_SYNC = [
    "street",
    "street2",
    "city",
    "zip",
    "state_id",
    "country_id",
]


class CrmLead(models.Model):
    _name = "crm.lead"
    _description = "Lead"
    _order = "priority desc, id desc"
    _inherit = [
        "mixin.mail.thread.cc",
        "mixin.mail.thread.blacklist",
        "mixin.mail.thread.phone",
        "mixin.mail.activity",
        "mixin.utm",
        "mixin.format.address",
        "mixin.mail.tracking.duration",
    ]
    _primary_email = "email_from"
    _check_company_auto = True
    _track_duration_field = "stage_id"

    name = fields.Char(
        string="Opportunity",
        compute="_compute_name",
        store=True,
        index="trigram",
        readonly=False,
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        default=lambda self: self.env.user,
        index=True,
        domain="[('share', '=', False)]",
        check_company=True,
        tracking=True,
    )
    user_company_ids = fields.Many2many(
        comodel_name="res.company",
        compute="_compute_user_company_ids",
        help="UX: Limit to lead company or all if no company",
    )
    team_id = fields.Many2one(
        comodel_name="team.team",
        string="Sales Team",
        compute="_compute_team_id",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
        domain=[("use_sale", "=", True)],
        ondelete="set null",
        check_company=True,
        tracking=True,
    )
    lead_properties = fields.Properties(
        definition="team_id.lead_properties_definition",
        string="Properties",
        copy=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        store=True,
        index=True,
        readonly=False,
    )
    referred = fields.Char(string="Referred By")
    description = fields.Html(string="Notes")
    active = fields.Boolean(
        default=True,
        tracking=72,
    )
    type = fields.Selection(
        selection=[("lead", "Lead"), ("opportunity", "Opportunity")],
        default=lambda self: (
            "lead" if self.env.user.has_group("crm.group_use_lead") else "opportunity"
        ),
        index=True,
        required=True,
        tracking=15,
    )
    priority = fields.Selection(
        selection=crm_stage.AVAILABLE_PRIORITIES,
        default=crm_stage.AVAILABLE_PRIORITIES[0][0],
        index=True,
    )
    stage_id = fields.Many2one(
        comodel_name="crm.stage",
        compute="_compute_stage_id",
        store=True,
        index=True,
        copy=False,
        readonly=False,
        group_expand="_read_group_stage_ids",
        domain="['|', ('team_ids', '=', False), ('team_ids', 'in', team_id)]",
        ondelete="restrict",
        tracking=True,
    )
    stage_id_color = fields.Integer(
        related="stage_id.color",
        string="Stage Color",
        export_string_translation=False,
    )
    tag_ids = fields.Many2many(
        comodel_name="crm.tag",
        relation="crm_tag_rel",
        column1="lead_id",
        column2="tag_id",
        string="Tags",
        help="Classify and analyze your lead/opportunity categories like: Training, Service",
    )
    color = fields.Integer(
        string="Color Index",
        default=0,
    )
    expected_revenue = fields.Monetary(
        currency_field="company_currency",
        default=0.0,
        tracking=True,
    )
    prorated_revenue = fields.Monetary(
        currency_field="company_currency",
        compute="_compute_prorated_revenue",
        store=True,
    )
    recurring_revenue = fields.Monetary(
        string="Recurring Revenues",
        currency_field="company_currency",
        default=0.0,
        tracking=True,
    )
    recurring_plan = fields.Many2one(comodel_name="crm.recurring.plan")
    recurring_revenue_monthly = fields.Monetary(
        string="Expected MRR",
        currency_field="company_currency",
        compute="_compute_recurring_revenue_monthly",
        store=True,
    )
    recurring_revenue_monthly_prorated = fields.Monetary(
        string="Prorated MRR",
        currency_field="company_currency",
        compute="_compute_recurring_revenue_monthly_prorated",
        store=True,
    )
    recurring_revenue_prorated = fields.Monetary(
        string="Prorated Recurring Revenues",
        currency_field="company_currency",
        compute="_compute_recurring_revenue_prorated",
        store=True,
    )
    company_currency = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        compute="_compute_company_currency",
        compute_sudo=True,
        value_sql="_company_currency_sql",
    )
    date_closed = fields.Datetime(
        string="Closed Date",
        copy=False,
        readonly=True,
    )
    date_automation_last = fields.Datetime(
        string="Last Action",
        readonly=True,
    )
    date_open = fields.Datetime(
        string="Assignment Date",
        compute="_compute_date_open",
        store=True,
        readonly=True,
    )
    day_open = fields.Float(
        string="Days to Assign",
        compute="_compute_day_open",
        store=True,
    )
    day_close = fields.Float(
        string="Days to Close",
        compute="_compute_day_close",
        store=True,
    )
    date_last_stage_update = fields.Datetime(
        string="Last Stage Update",
        compute="_compute_date_last_stage_update",
        store=True,
        index=True,
        readonly=True,
    )
    date_conversion = fields.Datetime(
        string="Conversion Date",
        readonly=True,
    )
    date_deadline = fields.Date(
        string="Expected Closing",
        help="Estimate of the date on which the opportunity will be won.",
    )

    commercial_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer Company",
        compute="_compute_commercial_partner_id",
        store=False,
        readonly=False,
        domain="[('is_company', '=', True)]",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
        index=True,
        check_company=True,
        tracking=10,
        help="Linked partner (optional). Usually created when converting the lead. You can find a partner by its Name, TIN, Email or Internal Reference.",
    )
    partner_is_blacklisted = fields.Boolean(
        related="partner_id.is_blacklisted",
        string="Partner is blacklisted",
        readonly=True,
    )
    contact_name = fields.Char(
        compute="_compute_contact_name",
        store=True,
        index="trigram",
        readonly=False,
        tracking=30,
    )
    partner_name = fields.Char(
        string="Company Name",
        compute="_compute_partner_name",
        store=True,
        index="trigram",
        readonly=False,
        tracking=20,
        help="The name of the future partner company that will be created while converting the lead into opportunity",
    )
    function = fields.Char(
        string="Job Position",
        compute="_compute_function",
        store=True,
        readonly=False,
    )
    email_from = fields.Char(
        string="Email",
        compute="_compute_email_from",
        inverse="_inverse_email_from",
        store=True,
        index="trigram",
        readonly=False,
        tracking=40,
    )
    email_normalized = fields.Char(index="trigram")
    email_domain_criterion = fields.Char(
        compute="_compute_email_domain_criterion",
        store=True,
        index="btree_not_null",
    )
    phone_ids = fields.Many2many(
        comodel_name="phone.number",
        relation="crm_lead_phone_number_rel",
        column1="lead_id",
        column2="phone_number_id",
        compute="_compute_phone_ids",
        inverse="_inverse_phone_ids",
        store=True,
        readonly=False,
        tracking=50,
    )
    phone_sanitized = fields.Char(index="btree_not_null")
    phone_state = fields.Selection(
        selection=[("correct", "Correct"), ("incorrect", "Incorrect")],
        string="Phone Quality",
        compute="_compute_phone_state",
        store=True,
    )
    email_state = fields.Selection(
        selection=[("correct", "Correct"), ("incorrect", "Incorrect")],
        string="Email Quality",
        compute="_compute_email_state",
        store=True,
    )
    website = fields.Char(
        compute="_compute_website",
        store=True,
        readonly=False,
        help="Website of the contact",
    )
    lang_id = fields.Many2one(
        comodel_name="res.lang",
        string="Language",
        compute="_compute_lang_id",
        store=True,
        readonly=False,
    )
    lang_code = fields.Char(related="lang_id.code")
    lang_active_count = fields.Integer(compute="_compute_lang_active_count")
    street = fields.Char(
        compute="_compute_partner_address_values",
        store=True,
        readonly=False,
    )
    street2 = fields.Char(
        compute="_compute_partner_address_values",
        store=True,
        readonly=False,
    )
    zip = fields.Char(
        compute="_compute_partner_address_values",
        change_default=True,
        store=True,
        readonly=False,
    )
    city = fields.Char(
        compute="_compute_partner_address_values",
        store=True,
        readonly=False,
    )
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        compute="_compute_partner_address_values",
        store=True,
        readonly=False,
        domain="[('country_id', '=?', country_id)]",
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        compute="_compute_partner_address_values",
        store=True,
        readonly=False,
    )
    probability = fields.Float(
        compute="_compute_probabilities",
        store=True,
        copy=False,
        readonly=False,
        aggregator="avg",
    )
    automated_probability = fields.Float(
        compute="_compute_probabilities",
        store=True,
        readonly=True,
    )
    is_automated_probability = fields.Boolean(
        string="Is automated probability?",
        compute="_compute_is_automated_probability",
    )
    won_status = fields.Selection(
        selection=[
            ("won", "Won"),
            ("lost", "Lost"),
            ("pending", "Pending"),
        ],
        string="Won/Lost",
        compute="_compute_won_status",
        store=True,
        tracking=70,
    )
    lost_reason_id = fields.Many2one(
        comodel_name="crm.lost.reason",
        index=True,
        ondelete="restrict",
        tracking=71,
    )
    calendar_event_ids = fields.One2many(
        comodel_name="calendar.event",
        inverse_name="opportunity_id",
        string="Meetings",
    )
    duplicate_lead_ids = fields.Many2many(
        comodel_name="crm.lead",
        string="Potential Duplicate Lead",
        compute="_compute_potential_lead_duplicates",
        compute_sudo=True,
        context={"active_test": False},
    )
    duplicate_lead_count = fields.Integer(
        string="Potential Duplicate Lead Count",
        compute="_compute_potential_lead_duplicates",
        compute_sudo=True,
    )
    meeting_display_date = fields.Date(compute="_compute_meeting_display")
    meeting_display_label = fields.Char(compute="_compute_meeting_display")
    partner_email_update = fields.Boolean(
        string="Partner Email will Update",
        compute="_compute_partner_email_update",
    )
    partner_phone_update = fields.Boolean(
        string="Partner Phone will Update",
        compute="_compute_partner_phone_update",
    )
    is_partner_visible = fields.Boolean(compute="_compute_is_partner_visible")
    campaign_id = fields.Many2one(ondelete="set null")
    medium_id = fields.Many2one(ondelete="set null")
    source_id = fields.Many2one(ondelete="set null")

    _check_probability = models.Constraint(
        "check(probability >= 0 and probability <= 100)",
        "The probability of closing the deal should be between 0% and 100%!",
    )
    _email_normalized_idx = models.Index(
        "(email_normalized) WHERE email_normalized IS NOT NULL"
    )
    _user_id_team_id_type_index = models.Index("(user_id, team_id, type)")
    _create_date_team_id_idx = models.Index("(create_date, team_id)")
    _default_order_idx = models.Index("(priority DESC, id DESC) WHERE active IS TRUE")

    @api.constrains("probability", "stage_id")
    def _check_won_validity(self):
        for lead in self:
            if lead.stage_id.is_won and lead.probability != 100:
                raise ValidationError(
                    _(
                        "%(lead_name)s is in the won stage %(stage_name)s, which implies a "
                        "100%% probability, but its probability is %(probability)s%%. "
                        "Move it to another stage first.",
                        lead_name=lead.display_name,
                        stage_name=lead.stage_id.display_name,
                        probability=lead.probability,
                    )
                )

    @api.depends("company_id")
    def _compute_user_company_ids(self):
        leads_wo_company = self.filtered(lambda lead: not lead.company_id)
        for lead in self - leads_wo_company:
            lead.user_company_ids = lead.company_id
        if leads_wo_company:
            leads_wo_company.user_company_ids = self.env["res.company"].search([])

    @api.depends("company_id")
    def _compute_company_currency(self):
        for lead in self:
            if not lead.company_id:
                lead.company_currency = self.env.company.currency_id
            else:
                lead.company_currency = lead.company_id.currency_id

    def _company_currency_sql(self, field, alias, query) -> SQL:
        if query is None:
            raise ValueError("company_currency needs a query to hang its join on")
        alias_company = query.get_table_alias(self._table, "company_id")
        company_field_sql = self._field_to_sql(self._table, "company_id", query)
        query.add_join(
            "LEFT JOIN",
            alias_company,
            "res_company",
            SQL(
                "%s = %s",
                company_field_sql,
                SQL.identifier(alias_company, "id"),
            ),
        )
        company_currency_expr = self.env["res.company"]._field_to_sql(
            alias_company, "currency_id", query
        )
        return SQL(
            "(CASE WHEN %s IS NOT NULL THEN %s ELSE %s END)",
            company_field_sql,
            company_currency_expr,
            self.env.company.currency_id.id,
        )

    @api.depends("user_id", "type")
    def _compute_team_id(self):
        Team = self.env["team.team"]
        for lead in self:
            if not lead.user_id:
                continue
            team_domain = (
                [("use_leads", "=", True)]
                if lead.type == "lead"
                else [("use_opportunities", "=", True)]
            )
            team = Team._get_team_for_user(
                lead.user_id, lead.team_id, domain=team_domain
            )
            if lead.team_id != team:
                lead.team_id = team.id

    @api.depends("user_id", "team_id", "partner_id")
    def _compute_company_id(self):
        for lead in self:
            proposal = lead.company_id

            if proposal:
                if (
                    (lead.user_id and proposal not in lead.user_id.company_ids)
                    or (lead.team_id.company_id and proposal != lead.team_id.company_id)
                    or (
                        lead.team_id
                        and not lead.team_id.company_id
                        and not lead.user_id
                    )
                    or (
                        not lead.team_id
                        and not lead.user_id
                        and (
                            not lead.partner_id
                            or lead.partner_id.company_id != proposal
                        )
                    )
                ):
                    proposal = False

            if not proposal:
                if lead.team_id.company_id:
                    lead.company_id = lead.team_id.company_id
                elif lead.user_id:
                    if self.env.company in lead.user_id.company_ids:
                        lead.company_id = self.env.company
                    else:
                        lead.company_id = lead.user_id.company_id & self.env.companies
                elif lead.partner_id:
                    lead.company_id = lead.partner_id.company_id
                else:
                    lead.company_id = False

    @api.depends("team_id", "type")
    def _compute_stage_id(self):
        # one stage lookup per team, not per lead: the search depends on the
        # team and the domain alone, and assigning a batch of leads ran it
        # once per lead (200 identical queries over 200 leads)
        to_place = self.filtered(
            lambda lead: (
                not lead.stage_id
                or (
                    lead.team_id
                    and lead.stage_id.team_ids
                    and lead.team_id not in lead.stage_id.team_ids
                )
            )
        )
        for leads in to_place.grouped("team_id").values():
            leads.stage_id = leads[:1]._stage_find(domain=[("fold", "=", False)]).id

    @api.depends("user_id")
    def _compute_date_open(self):
        for lead in self:
            if not lead.date_open and lead.user_id:
                lead.date_open = self.env.cr.now()

    @api.depends("stage_id")
    def _compute_date_last_stage_update(self):
        for lead in self:
            if not lead.date_last_stage_update:
                lead.date_last_stage_update = self.env.cr.now()

    @api.depends("create_date", "date_open")
    def _compute_day_open(self):
        leads = self.filtered(lambda l: l.date_open and l.create_date)
        others = self - leads
        others.day_open = None
        for lead in leads:
            date_create = fields.Datetime.from_string(lead.create_date).replace(
                microsecond=0
            )
            date_open = fields.Datetime.from_string(lead.date_open)
            lead.day_open = abs((date_open - date_create).days)

    @api.depends("create_date", "date_closed")
    def _compute_day_close(self):
        leads = self.filtered(lambda l: l.date_closed and l.create_date)
        others = self - leads
        others.day_close = None
        for lead in leads:
            # to the second, as `date_closed` is: a lead closed in the second
            # it was created has a negative sub-second interval, whose .days
            # is -1, and abs() reads that as one day
            date_create = fields.Datetime.from_string(lead.create_date).replace(
                microsecond=0
            )
            date_close = fields.Datetime.from_string(lead.date_closed)
            lead.day_close = abs((date_close - date_create).days)

    def _get_rotting_depends_fields(self):
        return super()._get_rotting_depends_fields() + ["won_status", "type"]

    def _get_domain_rotting_records(self):
        return super()._get_domain_rotting_records() & Domain(
            [
                ("won_status", "=", "pending"),
                ("type", "=", "opportunity"),
            ]
        )

    @api.depends("partner_id")
    def _compute_name(self):
        for lead in self:
            if not lead.name and lead.partner_id and lead.partner_id.name:
                lead.name = _("%s's opportunity") % lead.partner_id.name

    @api.depends("partner_id", "partner_name")
    def _compute_commercial_partner_id(self):
        leads_w_partners = self.filtered("partner_id")
        for lead in leads_w_partners:
            commercial_partner = lead.partner_id.commercial_partner_id
            lead.commercial_partner_id = (
                commercial_partner.is_company
                and commercial_partner != lead.partner_id
                and commercial_partner
            )
        remaining_leads_w_pname = (self - leads_w_partners).filtered("partner_name")
        commercial_partner_by_name = self.env["res.partner"]._read_group(
            [
                ("is_company", "=", True),
                ("name", "in", remaining_leads_w_pname.mapped("partner_name")),
            ],
            ["name"],
            ["id:array_agg"],
        )
        remaining_leads_by_name = remaining_leads_w_pname.grouped("partner_name")
        for (
            commercial_partner_name,
            commercial_partner_ids,
        ) in commercial_partner_by_name:
            remaining_leads_by_name[
                commercial_partner_name
            ].commercial_partner_id = commercial_partner_ids[0]

    @api.onchange("commercial_partner_id")
    def _onchange_commercial_partner_id(self):
        for lead in self:
            if (
                lead.partner_id
                and lead.commercial_partner_id
                and lead.commercial_partner_id != lead.partner_id.commercial_partner_id
            ):
                commercial_partner = lead.commercial_partner_id
                lead.update(
                    {
                        "partner_id": False,
                        "email_from": False,
                        "phone_ids": False,
                    }
                )
                lead.commercial_partner_id = commercial_partner
            if not lead.name and lead.commercial_partner_id:
                lead.name = _("%s's opportunity", lead.commercial_partner_id.name)

    @api.depends("partner_id")
    def _compute_contact_name(self):
        to_reset = self.filtered(lambda l: not l.partner_id)
        to_reset.contact_name = False
        for lead in self - to_reset:
            lead.update(lead._prepare_contact_name_from_partner(lead.partner_id))

    @api.depends("partner_id")
    def _compute_partner_name(self):
        to_reset = self.filtered(lambda l: not l.partner_id)
        to_reset.partner_name = False
        for lead in self - to_reset:
            lead.update(lead._prepare_partner_name_from_partner(lead.partner_id))

    @api.depends("partner_id")
    def _compute_function(self):
        for lead in self:
            if not lead.function or lead.partner_id.function:
                lead.function = lead.partner_id.function

    @api.depends("partner_id")
    def _compute_website(self):
        for lead in self:
            if not lead.website or lead.partner_id.website:
                lead.website = lead.partner_id.website

    @api.depends("partner_id")
    def _compute_lang_id(self):
        lang_codes = [code for code in self.mapped("partner_id.lang") if code]
        if lang_codes:
            lang_id_by_code = dict(
                (code, self.env["res.lang"]._get_data(code=code).id)
                for code in lang_codes
            )
        else:
            lang_id_by_code = {}
        for lead in self.filtered("partner_id"):
            lead.lang_id = lang_id_by_code.get(lead.partner_id.lang, False)

    @api.depends("lang_id")
    def _compute_lang_active_count(self):
        self.lang_active_count = len(self.env["res.lang"].get_installed())

    @api.depends("partner_id")
    def _compute_partner_address_values(self):
        for lead in self:
            lead.update(lead._prepare_address_values_from_partner(lead.partner_id))

    @api.depends("partner_id.email")
    def _compute_email_from(self):
        for lead in self:
            if lead.partner_id.email and lead._get_partner_email_update():
                lead.email_from = lead.partner_id.email

    def _inverse_email_from(self):
        for lead in self:
            if lead._get_partner_email_update(force_void=False):
                lead.partner_id.email = lead.email_from

    @api.depends("email_normalized")
    def _compute_email_domain_criterion(self):
        self.email_domain_criterion = False
        for lead in self.filtered("email_normalized"):
            lead.email_domain_criterion = iap_tools.mail_prepare_for_domain_search(
                lead.email_normalized
            )

    @api.depends("partner_id.phone_ids")
    def _compute_phone_ids(self):
        for lead in self:
            if lead.partner_id.phone_ids and lead._get_partner_phone_update():
                lead.phone_ids = lead.partner_id.phone_ids

    def _inverse_phone_ids(self):
        for lead in self:
            if lead._get_partner_phone_update(force_void=False):
                lead.partner_id.phone_ids = lead.phone_ids

    @api.depends(
        "phone_ids.number", "phone_ids.primary", "phone_ids.sequence", "country_id.code"
    )
    def _compute_phone_state(self):
        for lead in self:
            phone_status = False
            number = lead._phone_get_number().number
            if number:
                country_code = lead.country_id.code or None
                try:
                    if phone_validation.phone_parse(number, country_code):
                        phone_status = "correct"
                except UserError:
                    phone_status = "incorrect"
            lead.phone_state = phone_status

    @api.depends("email_from")
    def _compute_email_state(self):
        for lead in self:
            email_state = False
            if lead.email_from:
                email_state = "incorrect"
                for email in email_normalize_all(lead.email_from):
                    if mail_validation.is_valid_email(email):
                        email_state = "correct"
                        break
            lead.email_state = email_state

    @api.depends("probability", "automated_probability")
    def _compute_is_automated_probability(self):
        for lead in self:
            lead.is_automated_probability = (
                tools.float_compare(lead.probability, lead.automated_probability, 2)
                == 0
            )

    @api.depends(lambda self: ["stage_id", "team_id"] + self._pls_get_safe_fields())
    def _compute_probabilities(self):
        lead_probabilities, _unused = self._pls_get_naive_bayes_probabilities()
        for lead in self:
            if lead.id in lead_probabilities:
                was_automated = lead.active and lead.is_automated_probability
                lead.automated_probability = lead_probabilities[lead.id]
                if was_automated:
                    lead.probability = lead.automated_probability

    @api.depends("expected_revenue", "probability")
    def _compute_prorated_revenue(self):
        for lead in self:
            lead.prorated_revenue = round(
                (lead.expected_revenue or 0.0) * (lead.probability or 0) / 100.0, 2
            )

    @api.depends("recurring_revenue", "recurring_plan.number_of_months")
    def _compute_recurring_revenue_monthly(self):
        for lead in self:
            lead.recurring_revenue_monthly = (lead.recurring_revenue or 0.0) / (
                lead.recurring_plan.number_of_months or 1
            )

    @api.depends("recurring_revenue_monthly", "probability")
    def _compute_recurring_revenue_monthly_prorated(self):
        for lead in self:
            lead.recurring_revenue_monthly_prorated = (
                (lead.recurring_revenue_monthly or 0.0)
                * (lead.probability or 0)
                / 100.0
            )

    @api.depends("recurring_revenue", "probability")
    def _compute_recurring_revenue_prorated(self):
        for lead in self:
            lead.recurring_revenue_prorated = (
                (lead.recurring_revenue or 0.0) * (lead.probability or 0) / 100.0
            )

    @api.depends("calendar_event_ids", "calendar_event_ids.start")
    def _compute_meeting_display(self):
        now = fields.Datetime.now()
        meeting_data = (
            self.env["calendar.event"]
            .sudo()
            ._read_group(
                [
                    ("opportunity_id", "in", self.ids),
                ],
                ["opportunity_id"],
                ["start:array_agg", "start:max"],
            )
        )
        mapped_data = {
            lead: {
                "last_meeting_date": last_meeting_date,
                "next_meeting_date": min(
                    [dt for dt in meeting_start_dates if dt > now] or [False]
                ),
            }
            for lead, meeting_start_dates, last_meeting_date in meeting_data
        }
        for lead in self:
            lead_meeting_info = mapped_data.get(lead)
            if not lead_meeting_info:
                lead.meeting_display_date = False
                lead.meeting_display_label = _("No Meeting")
            elif lead_meeting_info["next_meeting_date"]:
                lead.meeting_display_date = lead_meeting_info["next_meeting_date"]
                lead.meeting_display_label = _("Next Meeting")
            else:
                lead.meeting_display_date = lead_meeting_info["last_meeting_date"]
                lead.meeting_display_label = _("Last Meeting")

    @api.depends("active", "probability", "stage_id")
    def _compute_won_status(self):
        for lead in self:
            if lead.probability == 100 and lead.stage_id.is_won:
                lead.won_status = "won"
            elif not lead.active and lead.probability == 0:
                lead.won_status = "lost"
            else:
                lead.won_status = "pending"

    @api.depends(
        "email_domain_criterion", "email_normalized", "partner_id", "phone_sanitized"
    )
    def _compute_potential_lead_duplicates(self):
        SEARCH_RESULT_LIMIT = 21

        def return_if_relevant(model_name, domain):
            model = self.env[model_name].with_context(active_test=False)
            res = model.search(domain, limit=SEARCH_RESULT_LIMIT)
            return res if len(res) < SEARCH_RESULT_LIMIT else model

        for lead in self:
            lead_id = lead._origin.id
            common_lead_domain = [("id", "!=", lead_id)]

            duplicate_lead_ids = self.env["crm.lead"]

            if lead.email_domain_criterion:
                duplicate_lead_ids |= return_if_relevant(
                    "crm.lead",
                    common_lead_domain
                    + [("email_domain_criterion", "=", lead.email_domain_criterion)],
                )
            if lead.partner_id and lead.partner_id.commercial_partner_id:
                duplicate_lead_ids |= lead.with_context(active_test=False).search(  # noqa: E8507 - one probe per lead, on the lead's own commercial partner
                    common_lead_domain
                    + [
                        (
                            "partner_id",
                            "child_of",
                            lead.partner_id.commercial_partner_id.ids,
                        )
                    ]
                )
            if lead.phone_sanitized:
                duplicate_lead_ids |= return_if_relevant(
                    "crm.lead",
                    common_lead_domain
                    + [("phone_sanitized", "=", lead.phone_sanitized)],
                )

            lead.duplicate_lead_ids = duplicate_lead_ids + lead
            lead.duplicate_lead_count = len(duplicate_lead_ids)

    @api.depends("email_from", "partner_id")
    def _compute_partner_email_update(self):
        for lead in self:
            lead.partner_email_update = lead._get_partner_email_update(force_void=False)

    @api.depends("phone_ids.sanitized", "partner_id.phone_ids.sanitized")
    def _compute_partner_phone_update(self):
        for lead in self:
            lead.partner_phone_update = lead._get_partner_phone_update(force_void=False)

    @api.depends_context("uid")
    @api.depends("partner_id", "type")
    def _compute_is_partner_visible(self):
        is_debug_mode = self.env.user.has_group("base.group_no_one")
        for lead in self:
            lead.is_partner_visible = bool(
                lead.type == "opportunity" or lead.partner_id or is_debug_mode
            )

    def _prepare_values_from_partner(self, partner):
        values = self._prepare_address_values_from_partner(partner)

        values.update(
            {f: partner[f] or self[f] for f in PARTNER_FIELDS_TO_SYNC if f != "lang"}
        )
        if partner.lang:
            values["lang_id"] = self.env["res.lang"]._get_data(code=partner.lang).id

        values.update(self._prepare_contact_name_from_partner(partner))
        values.update(self._prepare_partner_name_from_partner(partner))

        return self._convert_to_write(values)

    def _prepare_address_values_from_partner(self, partner):
        if any(partner[f] for f in PARTNER_ADDRESS_FIELDS_TO_SYNC):
            values = {f: partner[f] for f in PARTNER_ADDRESS_FIELDS_TO_SYNC}
        else:
            values = {f: self[f] for f in PARTNER_ADDRESS_FIELDS_TO_SYNC}
        return values

    def _prepare_contact_name_from_partner(self, partner):
        contact_name = False if partner.is_company else partner.name
        return {"contact_name": contact_name or self.contact_name}

    def _prepare_partner_name_from_partner(self, partner):
        partner_name = partner.parent_id.name
        if not partner_name and partner.is_company:
            partner_name = partner.name
        return {"partner_name": partner_name or self.partner_name}

    def _get_partner_email_update(self, force_void=True):
        self.check_singleton()
        if (
            self.partner_id
            and (force_void or self.email_from)
            and self.email_from != self.partner_id.email
        ):
            lead_email_normalized = (
                tools.email_normalize(self.email_from) or self.email_from or False
            )
            partner_email_normalized = (
                tools.email_normalize(self.partner_id.email)
                or self.partner_id.email
                or False
            )
            return lead_email_normalized != partner_email_normalized
        return False

    def _get_partner_phone_update(self, force_void=True):
        self.check_singleton()
        if self.partner_id and (force_void or self.phone_ids):
            return set(self.phone_ids.mapped("sanitized")) != set(
                self.partner_id.phone_ids.mapped("sanitized")
            )
        return False

    @api.model
    def _phone_commands_with_country(self, commands, country_id):
        if not country_id or not isinstance(commands, list):
            return commands
        return [
            (Command.CREATE, 0, {"country_id": country_id, **command[2]})
            if isinstance(command, tuple | list)
            and command[0] == Command.CREATE
            and isinstance(command[2], dict)
            and not command[2].get("country_id")
            else command
            for command in commands
        ]

    def _normalize_written_vals(self, vals):
        if vals.get("website"):
            vals["website"] = self.env["res.partner"]._clean_website(vals["website"])
        if not vals.get("phone_ids"):
            return
        country_id = vals.get("country_id")
        if not country_id and len(self.country_id) == 1:
            country_id = self.country_id.id
        vals["phone_ids"] = self._phone_commands_with_country(
            vals["phone_ids"], country_id
        )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("website"):
                vals["website"] = self.env["res.partner"]._clean_website(
                    vals["website"]
                )
            if vals.get("phone_ids"):
                vals["phone_ids"] = self._phone_commands_with_country(
                    vals["phone_ids"], vals.get("country_id")
                )
        leads = super().create(vals_list)

        won_to_set = leads.filtered(lambda l: not l.date_closed and l.stage_id.is_won)
        won_to_set.write({"date_closed": fields.Datetime.now()})

        if self.default_get(["partner_id"]).get("partner_id") is None:
            commercial_partner_ids = [
                vals["commercial_partner_id"]
                for vals in vals_list
                if vals.get("commercial_partner_id")
            ]
            CommercialPartners = self.env["res.partner"].with_prefetch(
                commercial_partner_ids
            )
            for lead, lead_vals in zip(leads, vals_list, strict=True):
                if not lead_vals.get("partner_id") and lead_vals.get(
                    "commercial_partner_id"
                ):
                    commercial_partner = CommercialPartners.browse(
                        lead_vals["commercial_partner_id"]
                    )
                    if (lead.phone_ids or lead.email_from) and (
                        set(lead.phone_ids.mapped("sanitized"))
                        != set(commercial_partner.phone_ids.mapped("sanitized"))
                        or lead.email_normalized != commercial_partner.email_normalized
                    ):
                        lead.partner_name = lead.partner_name or commercial_partner.name
                        continue
                    lead.partner_id = commercial_partner

        leads._handle_won_lost(
            {},
            {
                lead.id: {
                    "is_lost": lead.won_status == "lost",
                    "is_won": lead.won_status == "won",
                }
                for lead in leads
            },
        )

        return leads

    def web_save(self, vals, specification, next_id=None, **kwargs):
        to_sync = (
            self.filtered("partner_phone_update")
            if self and "phone_ids" not in vals
            else self.browse()
        )
        result = super().web_save(vals, specification, next_id=next_id, **kwargs)
        to_sync._inverse_phone_ids()
        return result

    def write(self, vals):
        self._normalize_written_vals(vals)

        now = self.env.cr.now()
        stage_is_won = False
        stage_movers = user_movers = self.browse()
        if "stage_id" in vals:
            stage_movers = self.filtered(
                lambda lead: lead.stage_id.id != vals["stage_id"]
            )
            if stage_movers and vals.get("stage_id"):
                stage = self.env["crm.stage"].browse(vals["stage_id"])
                if stage.is_won:
                    vals.update(
                        {
                            "active": True,
                            "probability": 100,
                            "automated_probability": 100,
                        }
                    )
                    stage_is_won = True
        if "user_id" in vals and not vals.get("user_id"):
            vals["date_open"] = False
        elif vals.get("user_id"):
            user_movers = self.filtered(lambda lead: lead.user_id.id != vals["user_id"])

        stage_clears_date_closed = False
        if vals.get("probability", 0) >= 100 or not vals.get("active", True):
            vals["date_closed"] = fields.Datetime.now()
        elif vals.get("probability", 0) > 0:
            vals["date_closed"] = False
        elif not stage_is_won and "probability" not in vals:
            stage_clears_date_closed = bool(stage_movers)

        update_frequencies = any(
            field in ["active", "stage_id", "probability"] for field in vals
        )
        old_status_by_lead = (
            {
                lead.id: {
                    "is_lost": lead.won_status == "lost",
                    "is_won": lead.won_status == "won",
                }
                for lead in self
            }
            if update_frequencies
            else {}
        )

        keep_date_closed = (
            self.filtered(lambda lead: lead.stage_id.is_won)
            if stage_is_won
            else self.browse()
        )

        stage_mover_ids, user_mover_ids = set(stage_movers._ids), set(user_movers._ids)
        keep_date_closed_ids = set(keep_date_closed._ids)
        writes = {}
        for lead_id in self._ids:
            extra = {}
            if lead_id in stage_mover_ids:
                extra["date_last_stage_update"] = now
                if stage_clears_date_closed:
                    extra["date_closed"] = False
            if lead_id in user_mover_ids:
                extra["date_open"] = now
            drop_date_closed = lead_id in keep_date_closed_ids
            key = (tuple(sorted(extra)), drop_date_closed)
            writes.setdefault(key, (extra, drop_date_closed, []))[2].append(lead_id)

        result = True
        for extra, drop_date_closed, lead_ids in writes.values():
            lead_vals = {**vals, **extra}
            if drop_date_closed:
                lead_vals.pop("date_closed", None)
            result = super(CrmLead, self.browse(lead_ids)).write(lead_vals)

        if update_frequencies:
            self._handle_won_lost(
                old_status_by_lead,
                {
                    lead.id: {
                        "is_lost": lead.won_status == "lost",
                        "is_won": lead.won_status == "won",
                    }
                    for lead in self
                },
            )

        return result

    def _handle_won_lost(self, old_status_by_lead, new_status_by_lead):
        leads_reach_won_ids = self.env["crm.lead"]
        leads_leave_won_ids = self.env["crm.lead"]
        leads_reach_lost_ids = self.env["crm.lead"]
        leads_leave_lost_ids = self.env["crm.lead"]

        for lead in self:
            new_status = new_status_by_lead.get(
                lead.id, {"is_lost": False, "is_won": False}
            )
            old_status = old_status_by_lead.get(
                lead.id, {"is_lost": False, "is_won": False}
            )
            if new_status["is_lost"] and new_status["is_won"]:
                raise ValidationError(
                    _("The lead %s cannot be won and lost at the same time.", lead)
                )

            if new_status["is_lost"] and not old_status["is_lost"]:
                leads_reach_lost_ids += lead
            elif not new_status["is_lost"] and old_status["is_lost"]:
                leads_leave_lost_ids += lead

            if new_status["is_won"] and not old_status["is_won"]:
                leads_reach_won_ids += lead
            elif not new_status["is_won"] and old_status["is_won"]:
                leads_leave_won_ids += lead

        leads_reach_won_ids._pls_increment_frequencies(to_state="won")
        leads_leave_won_ids._pls_increment_frequencies(from_state="won")
        leads_reach_lost_ids._pls_increment_frequencies(to_state="lost")
        leads_leave_lost_ids._pls_increment_frequencies(from_state="lost")

        return True

    def copy_data(self, default=None):
        default = dict(default or {})
        if not self.env.user.has_group("crm.group_use_recurring_revenues"):
            default["recurring_revenue"] = 0
            default["recurring_plan"] = False
        vals_list = super().copy_data(default=default)
        now = self.env.cr.now()
        for lead, vals in zip(self, vals_list):
            vals.setdefault("type", lead.type)
            vals.setdefault("team_id", lead.team_id.id)
            vals["date_open"] = (
                now if lead.type == "opportunity" and lead.user_id.active else False
            )
            if not lead.user_id.active:
                vals["user_id"] = False
        return vals_list

    def unlink(self):
        meetings = self.env["calendar.event"].search(
            [
                ("res_id", "in", self.ids),
                ("res_model", "=", self._name),
            ]
        )
        if meetings:
            meetings.write(
                {
                    "res_id": False,
                    "res_model_id": False,
                }
            )
        return super().unlink()

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        team_id = self.env.context.get("default_team_id")
        team_ids = (
            self.env.user.sale_team_ids._ids
            if self.env.context.get("show_user_team_stages")
            else ()
        )
        team_ids += (team_id,) if team_id else ()
        search_domain = ["|", ("id", "in", stages.ids), ("team_ids", "=", False)]
        if team_ids:
            search_domain = [
                "|",
                ("id", "in", stages.ids),
                "|",
                ("team_ids", "=", False),
                ("team_ids", "in", team_ids),
            ]

        stage_ids = stages.sudo()._search(search_domain, order=stages._order)
        return stages.browse(stage_ids)

    def _stage_find(self, team_id=False, domain=None, order="sequence, id", limit=1):
        team_ids = set()
        if team_id:
            team_ids.add(team_id)
        for lead in self:
            if lead.team_id:
                team_ids.add(lead.team_id.id)
        if team_ids:
            search_domain = [
                "|",
                ("team_ids", "=", False),
                ("team_ids", "in", list(team_ids)),
            ]
        else:
            search_domain = [("team_ids", "=", False)]
        if domain:
            search_domain += list(domain)
        return self.env["crm.stage"].search(search_domain, order=order, limit=limit)

    def action_unarchive(self):
        activated = self.filtered(lambda rec: not rec.active)
        res = super().action_unarchive()
        if activated:
            activated.write({"lost_reason_id": False})
            activated._compute_probabilities()
        return res

    def action_restore(self):
        self.action_unarchive()
        for lead in self:
            lead.probability = lead.automated_probability

    def action_set_lost(self, **additional_values):
        res = self.action_archive()
        self.write({**additional_values, "probability": 0, "automated_probability": 0})
        return res

    def action_set_won(self):
        self.action_unarchive()
        won_stages_by_team = {
            team: team_leads._stage_find(domain=[("is_won", "=", True)], limit=None)
            for team, team_leads in self.grouped("team_id").items()
        }
        leads_by_won_stage = defaultdict(lambda: self.browse())
        for lead in self:
            won_stages = won_stages_by_team[lead.team_id]
            won_stage = next(
                (
                    stage
                    for stage in won_stages
                    if stage.sequence > lead.stage_id.sequence
                ),
                None,
            )
            if not won_stage:
                won_stage = next(
                    (
                        stage
                        for stage in reversed(won_stages)
                        if stage.sequence <= lead.stage_id.sequence
                    ),
                    won_stages,
                )
            leads_by_won_stage[won_stage] += lead
        for won_stage, leads in leads_by_won_stage.items():
            leads.write({"stage_id": won_stage.id, "probability": 100})
        return True

    def action_set_automated_probability(self):
        self.check_singleton()
        self._compute_probabilities()
        self.write({"probability": self.automated_probability})

    def action_set_won_rainbowman(self):
        self.check_singleton()
        self.action_set_won()

        message = self._get_rainbowman_message()
        if message:
            return {
                "effect": {
                    "fadeout": "slow",
                    "message": message,
                    "img_url": "/web/image/%s/%s/image_1024"
                    % (self.team_id.user_id._name, self.team_id.user_id.id)
                    if self.team_id.user_id.image_1024
                    else "/web/static/img/smile.svg",
                    "type": "rainbow_man",
                }
            }
        return True

    def get_rainbowman_message(self):
        self.check_singleton()
        if self.stage_id.is_won:
            return self._get_rainbowman_message()
        return False

    def _get_rainbowman_message(self):
        self.check_singleton()
        if not self.user_id:
            return False
        self.flush_model()

        if len(self.message_ids) >= 25:
            return _("Phew, that took some effort — but you nailed it. Good job!")

        tz_midnight = (
            fields.Datetime.now()
            .astimezone(timezone(self.env.user.tz or self.user_id.tz or "UTC"))
            .replace(hour=0, minute=0, second=0)
        )
        tz_midnight_in_utc = tz_midnight.astimezone(UTC).replace(tzinfo=None)
        team_condition = (
            SQL("team_id = %s", self.team_id.id)
            if self.team_id
            else SQL("team_id IS NULL")
        )
        source_case = (
            SQL("source_id = %s AND %s", self.source_id.id, team_condition)
            if self.source_id
            else SQL("false")
        )
        country_case = (
            SQL("country_id = %s AND %s", self.country_id.id, team_condition)
            if self.country_id
            else SQL("false")
        )
        user_id, team_id, lead_id = self.env.user.id, self.team_id.id or -1, self.id
        self.env.cr.execute(
            SQL(
                """
        SELECT
            MAX(CASE WHEN team_id = %(team_id)s AND COALESCE(date_closed, create_date) >= %(tz_midnight)s - INTERVAL '31 days' AND id <> %(lead_id)s THEN expected_revenue ELSE 0 END) AS max_team_31,
            MAX(CASE WHEN team_id = %(team_id)s AND COALESCE(date_closed, create_date) >= %(tz_midnight)s - INTERVAL '7 days'  AND id <> %(lead_id)s THEN expected_revenue ELSE 0 END) AS max_team_7,
            MAX(CASE WHEN user_id = %(user_id)s AND COALESCE(date_closed, create_date) >= %(tz_midnight)s - INTERVAL '31 days' AND id <> %(lead_id)s THEN expected_revenue ELSE 0 END) AS max_user_31,
            MAX(CASE WHEN user_id = %(user_id)s AND COALESCE(date_closed, create_date) >= %(tz_midnight)s - INTERVAL '7 days'  AND id <> %(lead_id)s THEN expected_revenue ELSE 0 END) AS max_user_7,
            MIN(CASE WHEN COALESCE(date_closed, create_date) >= %(tz_midnight)s - INTERVAL '31 days' THEN day_close ELSE 31 END) AS min_day_close_31,
            COUNT(CASE WHEN user_id = %(user_id)s THEN 1 ELSE NULL END) AS count_user_closed_year,
            COUNT(CASE WHEN user_id = %(user_id)s AND COALESCE(date_closed, create_date) >= %(tz_midnight)s - INTERVAL '3 days' AND COALESCE(date_closed, create_date) < %(tz_midnight)s - INTERVAL '2 days' THEN 1 ELSE NULL END) AS count_user_closed_minus3day,
            COUNT(CASE WHEN user_id = %(user_id)s AND COALESCE(date_closed, create_date) >= %(tz_midnight)s - INTERVAL '2 days' AND COALESCE(date_closed, create_date) < %(tz_midnight)s - INTERVAL '1 days' THEN 1 ELSE NULL END) AS count_user_closed_minus2day,
            COUNT(CASE WHEN user_id = %(user_id)s AND COALESCE(date_closed, create_date) >= %(tz_midnight)s - INTERVAL '1 days' AND COALESCE(date_closed, create_date) < %(tz_midnight)s THEN 1 ELSE NULL END) AS count_user_closed_yesterday,
            COUNT(CASE WHEN user_id = %(user_id)s AND COALESCE(date_closed, create_date) >= %(tz_midnight)s THEN 1 ELSE NULL END) AS count_user_closed_today,
            COUNT(CASE WHEN %(source_case)s THEN 1 ELSE NULL END) AS count_source_closed_year,
            COUNT(CASE WHEN %(country_case)s THEN 1 ELSE NULL END) AS count_country_closed_year
            FROM crm_lead
            WHERE
                type = 'opportunity'
            AND
                active = True
            AND
                probability = 100
            AND
                DATE_TRUNC('year', COALESCE(date_closed, create_date)) = DATE_TRUNC('year', %(tz_midnight)s)
            AND
                (user_id = %(user_id)s OR team_id = %(team_id)s)
            """,
                country_case=country_case,
                lead_id=lead_id,
                source_case=source_case,
                team_id=team_id,
                tz_midnight=tz_midnight_in_utc,
                user_id=user_id,
            )
        )
        query_result = self.env.cr.dictfetchone()

        if query_result["count_user_closed_year"] == 1:
            return _("Go, go, go! Congrats for your first deal.")
        elif (
            self.expected_revenue
            and query_result["max_team_31"] < self.expected_revenue
        ):
            return _("Boom! Team record for the past 30 days.")
        elif (
            self.expected_revenue and query_result["max_team_7"] < self.expected_revenue
        ):
            return _("Yeah! Best deal out of the last 7 days for the team.")
        elif (
            self.expected_revenue
            and query_result["max_user_31"] < self.expected_revenue
        ):
            return _("You just beat your personal record for the past 30 days.")
        elif (
            self.expected_revenue and query_result["max_user_7"] < self.expected_revenue
        ):
            return _("You just beat your personal record for the past 7 days.")
        elif query_result["count_user_closed_today"] == 5:
            return _("You're on fire! Fifth deal won today 🔥")
        elif (
            query_result["count_user_closed_today"] == 1
            and query_result["count_user_closed_yesterday"]
            and query_result["count_user_closed_minus2day"]
            and not query_result["count_user_closed_minus3day"]
        ):
            return _("You're on a winning streak. 3 deals in 3 days, congrats!")
        elif (
            query_result["min_day_close_31"] == self.day_close
            and self.day_close < 31
            and self.date_closed
            and (self.date_closed - self.create_date).total_seconds() > 60
        ):
            return _("Wow, that was fast. That deal didn’t stand a chance!")
        elif (
            len(
                stage_ids := [
                    int(stage_id)
                    for stage_id, duration in self.duration_tracking.items()
                    if duration >= 60
                ]
            )
            == 1
        ):
            first_stage = self.env["crm.stage"].search(
                [
                    "|",
                    ("team_ids", "in", False),
                    ("team_ids", "in", self.team_id.id),
                ],
                order="sequence ASC",
                limit=1,
            )
            if first_stage.id == stage_ids[0]:
                return _(
                    "No detours, no delays - from %(stage_name)s straight to the win! 🚀",
                    stage_name=first_stage.name,
                )
        if query_result["count_country_closed_year"] == 1 and self.country_id:
            return _(
                "You just expanded the map! First win in %(country)s.",
                country=self.country_id.name,
            )
        elif query_result["count_source_closed_year"] == 1 and self.source_id:
            return _(
                "Yay, your first win from %(utm_source_name)s!",
                utm_source_name=self.source_id.name,
            )
        return False

    def action_schedule_meeting(self, smart_calendar=True):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "calendar.action_calendar_event"
        )
        partner_ids = self.env.user.partner_id.ids
        if self.partner_id:
            partner_ids.append(self.partner_id.id)
        current_opportunity_id = self.id if self.type == "opportunity" else False
        action["context"] = {
            "search_default_opportunity_id": current_opportunity_id,
            "default_opportunity_id": current_opportunity_id,
            "default_partner_id": self.partner_id.id,
            "default_partner_ids": partner_ids,
            "default_team_id": self.team_id.id,
            "default_name": self.name,
        }

        if current_opportunity_id and smart_calendar:
            mode, initial_date = self._get_opportunity_meeting_view_parameters()
            action["context"].update(
                {"default_mode": mode, "initial_date": initial_date}
            )

        return action

    def _get_opportunity_meeting_view_parameters(self):
        self.check_singleton()
        meeting_results = self.env["calendar.event"].search_read(
            [("opportunity_id", "=", self.id)], ["start", "stop", "allday"]
        )
        if not meeting_results:
            return "week", False

        user_tz = self.env.tz

        meeting_dts = []
        now_dt = datetime.now().astimezone(user_tz).replace(tzinfo=None)

        for meeting in meeting_results:
            if meeting.get("allday"):
                meeting_dts.append((meeting.get("start"), meeting.get("stop")))
            else:
                meeting_dts.append(
                    (
                        meeting.get("start").astimezone(user_tz).replace(tzinfo=None),
                        meeting.get("stop").astimezone(user_tz).replace(tzinfo=None),
                    )
                )

        unfinished_meeting_dts = [
            meeting_dt for meeting_dt in meeting_dts if meeting_dt[1] >= now_dt
        ]
        relevant_meeting_dts = unfinished_meeting_dts or meeting_dts
        relevant_meeting_count = len(relevant_meeting_dts)

        if relevant_meeting_count == 1:
            return "week", relevant_meeting_dts[0][0].date()
        else:
            earliest_start_dt = min(
                relevant_meeting_dt[0] for relevant_meeting_dt in relevant_meeting_dts
            )
            latest_stop_dt = max(
                relevant_meeting_dt[1] for relevant_meeting_dt in relevant_meeting_dts
            )

            lang_week_start = self.env["res.lang"].search_read(
                [("code", "=", self.env.user.lang)], ["week_start"]
            )
            week_start_index = int(lang_week_start[0].get("week_start", "1")) - 1

            earliest_start_dt_weekday = (
                7 + earliest_start_dt.weekday() - week_start_index
            ) % 7
            remaining_days_in_week = 7 - earliest_start_dt_weekday

            next_week_start_date = earliest_start_dt.date() + timedelta(
                days=remaining_days_in_week
            )

            meetings_in_same_week = latest_stop_dt <= datetime(
                next_week_start_date.year,
                next_week_start_date.month,
                next_week_start_date.day,
                0,
                0,
                0,
            )

            if meetings_in_same_week:
                return "week", earliest_start_dt.date()
            else:
                return "month", earliest_start_dt.date()

    def action_reschedule_meeting(self):
        self.check_singleton()
        action = self.action_schedule_meeting(smart_calendar=False)
        next_activity = self.activity_ids.filtered(
            lambda activity: activity.user_id == self.env.user
        )[:1]
        if next_activity.calendar_event_id:
            action["context"]["initial_date"] = next_activity.calendar_event_id.start
        return action

    def action_show_potential_duplicates(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "crm.crm_lead_opportunities"
        )
        action["domain"] = [("id", "in", self.duplicate_lead_ids.ids)]
        action["context"] = {"active_test": False, "create": False}
        return action

    def redirect_lead_opportunity_view(self):
        self.check_singleton()
        return {
            "name": _("Lead or Opportunity"),
            "view_mode": "form",
            "res_model": "crm.lead",
            "domain": [("type", "=", self.type)],
            "res_id": self.id,
            "view_id": False,
            "type": "ir.actions.act_window",
            "context": {"default_type": self.type},
        }

    @api.model
    def get_empty_list_help(self, help_message):
        if not is_html_empty(help_message):
            return help_message

        help_title, sub_title = "", ""
        if self.env.context.get("default_type") == "lead":
            help_title = _("Create a new lead")
        else:
            help_title = _("Create an opportunity to start playing with your pipeline.")
        alias_domain = [
            ("company_id", "in", [self.env.company.id, False]),
            ("lead_alias_id.alias_name", "!=", False),
            ("lead_alias_id.alias_name", "!=", ""),
        ]
        alias_records = (
            self.env["team.team"]
            .search(alias_domain)
            .sorted(
                lambda r: (r.use_leads, self.env.user in r.member_ids), reverse=True
            )
        )
        alias_record = alias_records[0] if alias_records else None
        if (
            alias_record
            and alias_record.lead_alias_domain
            and alias_record.lead_alias_name
        ):
            sub_title = Markup(
                _(
                    "Use the <i>New</i> button, or send an email to %(email_link)s to test the email gateway."
                )
            ) % {
                "email_link": Markup("<b><a href='mailto:%s'>%s</a></b>")
                % (alias_record.lead_alias_email, alias_record.lead_alias_email),
            }
        return super().get_empty_list_help(
            f'<p class="o_view_nocontent_smiling_face">{help_title}</p><p class="oe_view_nocontent_alias">{sub_title}</p>'
        )

    def _update_userless_leads_with_team_leader(self, creation_source: str):
        if not self._is_rule_based_assignment_activated() and self.team_id:
            for team_id, leads in (
                self.filtered(lambda lead: not lead.user_id).grouped("team_id").items()
            ):
                if team_id.user_id:
                    leads.user_id = team_id.user_id
                    message = _(
                        "This new lead created by %(creation_source)s was automatically assigned to team leader %(user_name)s",
                        user_name=team_id.user_id.name,
                        creation_source=creation_source,
                    )
                    leads._message_log_batch(
                        bodies={lead.id: message for lead in leads}
                    )

    def log_meeting(self, meeting):
        if not meeting.duration:
            duration = _("unknown")
        else:
            duration = self.env["ir.qweb.field.duration"].value_to_html(
                meeting.duration, {"unit": "hour"}
            )
        meeting_usertime = fields.Datetime.to_string(
            fields.Datetime.context_timestamp(self, meeting.start)
        )
        meeting_time = Markup(
            "<time datetime='%(meeting_start)s+00:00'>%(meeting_user_time)s</time>"
        ) % {
            "meeting_start": meeting.start,
            "meeting_user_time": meeting_usertime,
        }
        message = Markup(
            "<p>%(meeting)s<br/>%(subject_string)s %(subject_link)s<br/>%(duration)s<p>"
        ) % {
            "meeting": _("Meeting scheduled at %s", meeting_time),
            "subject_string": _("Subject: "),
            "subject_link": meeting._get_html_link(),
            "duration": _("Duration: %s", duration),
        }
        return self.message_post(body=message)

    def _merge_data(self, fnames=None):
        if fnames is None:
            fnames = self._merge_get_fields()
        fcallables = self._merge_get_fields_specific()
        address_values = self._merge_get_fields_address()

        def _get_first_not_null(attr, opportunities):
            value = False
            for opp in opportunities:
                if opp[attr]:
                    value = (
                        opp[attr].id
                        if isinstance(opp[attr], models.BaseModel)
                        else opp[attr]
                    )
                    break
            return value

        data = {}
        for field_name in fnames:
            field = self._fields.get(field_name)
            if field is None:
                continue

            fcallable = fcallables.get(field_name)
            if fcallable and callable(fcallable):
                data[field_name] = fcallable(field_name, self)
            elif field_name in address_values:
                data[field_name] = address_values[field_name]
            elif not fcallable and field.type in ("many2many", "one2many"):
                continue
            else:
                data[field_name] = _get_first_not_null(field_name, self)

        return data

    def merge_opportunity(self, user_id=False, team_id=False, auto_unlink=True):
        return self._merge_opportunity(
            user_id=user_id, team_id=team_id, auto_unlink=auto_unlink
        )

    def _merge_opportunity(
        self, user_id=False, team_id=False, auto_unlink=True, max_length=5
    ):
        if len(self.ids) <= 1:
            raise UserError(
                _(
                    "Select at least two Leads/Opportunities from the list to merge them."
                )
            )

        if max_length and len(self.ids) > max_length and not self.env.is_superuser():
            raise UserError(
                _(
                    "To prevent data loss, Leads and Opportunities can only be merged by groups of %(max_length)s.",
                    max_length=max_length,
                )
            )

        opportunities = self._sort_by_confidence_level(reverse=True)

        opportunities_head = opportunities[0]
        opportunities_tail = opportunities[1:].with_prefetch(
            opportunities._prefetch_ids
        )

        merged_data = opportunities._merge_data(self._merge_get_fields())

        if user_id:
            merged_data["user_id"] = user_id
        if team_id:
            merged_data["team_id"] = team_id

        merged_followers = opportunities_head._merge_followers(opportunities_tail)

        opportunities_head._merge_log_summary(merged_followers, opportunities_tail)
        opportunities_head._merge_dependences(opportunities_tail)

        if merged_data.get("team_id"):
            team_stage_ids = self.env["crm.stage"].search(
                [
                    "|",
                    ("team_ids", "in", merged_data["team_id"]),
                    ("team_ids", "=", False),
                ],
                order="sequence, id",
            )
            if merged_data.get("stage_id") not in team_stage_ids.ids:
                merged_data["stage_id"] = (
                    team_stage_ids[0].id if team_stage_ids else False
                )

        if (
            "user_id" in merged_data
            and opportunities_head.user_id.id == merged_data["user_id"]
        ):
            merged_data.pop("user_id")
        if (
            "team_id" in merged_data
            and opportunities_head.team_id.id == merged_data["team_id"]
        ):
            merged_data.pop("team_id")
        opportunities_head.write(merged_data)

        if auto_unlink:
            opportunities_tail.check_access("write")
            opportunities_tail.sudo().unlink()

        return opportunities_head

    def _merge_get_fields_address(self):
        source_lead = max(
            self,
            key=lambda lead: len(
                list(
                    lead[field]
                    for field in PARTNER_ADDRESS_FIELDS_TO_SYNC
                    if lead[field]
                )
            ),
        )
        return {fname: source_lead[fname] for fname in PARTNER_ADDRESS_FIELDS_TO_SYNC}

    def _merge_get_fields_specific(self):
        return {
            "description": lambda fname, leads: "<br/><br/>".join(
                desc for desc in leads.mapped("description") if not is_html_empty(desc)
            ),
            "type": lambda fname, leads: (
                "opportunity"
                if any(lead.type == "opportunity" for lead in leads)
                else "lead"
            ),
            "priority": lambda fname, leads: (
                max(priorities)
                if (priorities := leads.filtered("priority").mapped("priority"))
                else False
            ),
            "tag_ids": lambda fname, leads: leads.mapped("tag_ids"),
            "phone_ids": lambda fname, leads: leads.mapped("phone_ids"),
            "lost_reason_id": lambda fname, leads: (
                False
                if leads and leads[0].probability
                else next(
                    (lead.lost_reason_id for lead in leads if lead.lost_reason_id),
                    False,
                )
            ),
        }

    def _merge_get_fields(self):
        return (
            CRM_LEAD_FIELDS_TO_MERGE
            + list(self._merge_get_fields_specific().keys())
            + PARTNER_ADDRESS_FIELDS_TO_SYNC
        )

    def _merge_dependences(self, opportunities):
        self.check_singleton()
        self._merge_dependences_history(opportunities)
        self._merge_dependences_attachments(opportunities)
        self._merge_dependences_calendar_events(opportunities)

    def _merge_dependences_history(self, opportunities):
        self.check_singleton()
        messages_by_subject = {}
        for opportunity_su in opportunities.sudo():
            for message_su in opportunity_su.message_ids:
                if message_su.subject:
                    subject = _(
                        "From %(source_name)s: %(source_subject)s",
                        source_name=opportunity_su.name,
                        source_subject=message_su.subject,
                    )
                else:
                    subject = _("From %(source_name)s", source_name=opportunity_su.name)
                messages_by_subject[subject] = (
                    messages_by_subject.get(subject, message_su.browse()) + message_su
                )
        for subject, messages_su in messages_by_subject.items():
            messages_su.write({"res_id": self.id, "subject": subject})
        opportunities.activity_ids.write(
            {
                "res_id": self.id,
            }
        )

        return True

    def _merge_dependences_attachments(self, opportunities):
        self.check_singleton()

        all_attachments = self.env["ir.attachment"].search(
            [("res_model", "=", self._name), ("res_id", "in", opportunities.ids)]
        )

        for opportunity in opportunities:
            attachments = all_attachments.filtered(
                lambda attach: attach.res_id == opportunity.id
            )
            for attachment in attachments:
                attachment.write(
                    {
                        "res_id": self.id,
                        "name": _(
                            "%(attach_name)s (from %(lead_name)s)",
                            attach_name=attachment.name,
                            lead_name=opportunity.name[:20],
                        ),
                    }
                )
        return True

    def _merge_dependences_calendar_events(self, opportunities):
        self.check_singleton()
        meetings = self.env["calendar.event"].search(
            [("opportunity_id", "in", opportunities.ids)]
        )
        return meetings.write(
            {
                "res_id": self.id,
                "opportunity_id": self.id,
            }
        )

    def _merge_followers(self, opportunities):
        self.check_singleton()

        self.env["mail.message"].flush_model()
        self.env["mail.followers"].flush_model()

        self.env.cr.execute(
            """
            SELECT MAX(mf.id) AS id
              FROM mail_followers AS mf
              JOIN mail_message AS mm
                ON mm.author_id = mf.partner_id
               AND mm.res_id = mf.res_id
               AND mm.model = 'crm.lead'
               AND mm.date > NOW() - INTERVAL '30 DAY'
                   /* Check if the partner is already
                      following the destination lead */
         LEFT JOIN mail_followers AS destf
                ON destf.res_model = 'crm.lead'
               AND destf.res_id = %(lead_id)s
               AND destf.partner_id = mf.partner_id
                   /* Select only once each partner
                      to not create duplicated followers */
             WHERE mf.res_model = 'crm.lead'
               AND mf.res_id = ANY(%(lead_ids)s)
               AND destf IS NULL
          GROUP BY mf.partner_id
            """,
            {"lead_ids": list(opportunities.ids), "lead_id": self.id},
        )
        followers_to_update = [r[0] for r in self.env.cr.fetchall()]
        followers_to_update = (
            self.env["mail.followers"].browse(followers_to_update).sudo()
        )
        followers_by_old_lead = dict(groupby(followers_to_update, lambda f: f.res_id))
        followers_to_update.write({"res_id": self.id})
        return followers_by_old_lead

    def _merge_log_summary(self, merged_followers, opportunities_tail):
        self.check_singleton()
        self.message_post_with_source(
            "crm.crm_lead_merge_summary",
            render_values={
                "merged_followers": merged_followers,
                "opportunities": opportunities_tail,
                "is_html_empty": is_html_empty,
            },
            subtype_xmlid="mail.mt_note",
        )

    def _format_properties(self):
        self.check_singleton()
        properties = self.read(["lead_properties"])[0]["lead_properties"]

        formatted = []
        for definition in properties:
            label = definition.get("string")
            value = definition.get("value")
            property_type = definition["type"]
            if not value and property_type != "boolean":
                continue

            property_dict = {"label": label}
            if property_type == "boolean":
                property_dict["value"] = _("Yes") if value else _("No")
            elif value and property_type == "many2one":
                property_dict["value"] = value[1]
            elif value and property_type == "many2many":
                property_dict["values"] = [{"name": rec[1]} for rec in value]
            elif value and property_type in ["selection", "tags"]:
                options = {
                    option[0]: option[1:]
                    for option in (definition.get(property_type) or [])
                }
                if property_type == "selection":
                    value = options.get(value)
                    property_dict["value"] = value[0] if value else None
                else:
                    property_dict["values"] = [
                        {
                            "name": options[tag][0],
                            "color": options[tag][1],
                        }
                        for tag in value
                        if tag in options
                    ]
            else:
                property_dict["value"] = value

            formatted.append(property_dict)

        return formatted

    def _convert_opportunity_data(self, customer, team_id=False):
        new_team_id = team_id or self.team_id.id
        upd_values = {
            "type": "opportunity",
            "date_conversion": self.env.cr.now(),
        }
        if customer is not None and customer != self.partner_id:
            upd_values["partner_id"] = customer.id if customer else False
        if not self.stage_id:
            stage = self._stage_find(team_id=new_team_id)
            upd_values["stage_id"] = stage.id
        return upd_values

    def convert_opportunity(self, partner, user_ids=False, team_id=False):
        """Convert the leads; ``partner=None`` keeps each lead's own customer."""
        customer = partner if partner is None else partner or self.env["res.partner"]
        leads_by_vals = {}
        for lead in self:
            if not lead.active or lead.won_status == "won":
                continue
            vals = lead._convert_opportunity_data(customer, team_id)
            key = tuple(sorted(vals.items()))
            leads_by_vals[key] = leads_by_vals.get(key, self.browse()) + lead
        for key, leads in leads_by_vals.items():
            leads.write(dict(key))

        if user_ids or team_id:
            self._handle_salesmen_assignment(user_ids=user_ids, team_id=team_id)

        return True

    def _handle_partner_assignment(
        self, force_partner_id=False, create_missing=True, with_parent=None
    ):
        for lead in self:
            if force_partner_id:
                lead.partner_id = force_partner_id
            if not lead.partner_id and create_missing:
                partner = lead._create_customer(with_parent=with_parent)
                lead.partner_id = partner.id

    def _handle_salesmen_assignment(self, user_ids=False, team_id=False):
        update_vals = {"team_id": team_id} if team_id else {}
        if not user_ids and team_id:
            self.write(update_vals)
        else:
            lead_ids = self.ids
            steps = len(user_ids)
            for idx in range(steps):
                subset_ids = lead_ids[idx : len(lead_ids) : steps]
                update_vals["user_id"] = user_ids[idx]
                self.env["crm.lead"].browse(subset_ids).write(update_vals)

    def _get_lead_duplicates(self, partner=None, email=None, include_lost=False):
        if not email and not partner:
            return self.env["crm.lead"]

        domain = []
        normalized_emails = email_normalize_all(email)
        if normalized_emails:
            domain.append(("email_normalized", "in", normalized_emails))
        if partner:
            domain.append(("partner_id", "=", partner.id))

        if not domain:
            return self.env["crm.lead"]

        domain = ["|"] * (len(domain) - 1) + domain
        if include_lost:
            domain += [
                ("won_status", "!=", "won"),
                "|",
                ("type", "=", "opportunity"),
                ("active", "=", True),
            ]
        else:
            domain += [("won_status", "=", "pending"), ("active", "=", True)]

        return self.with_context(active_test=False).search(domain)

    def _get_lead_duplicates_by_lead(
        self, leads, with_partner=False, include_lost=False
    ):
        emails_by_lead, all_emails = {}, set()
        partners = self.env["res.partner"]
        for lead in leads:
            email = lead.email_from
            if with_partner and lead.partner_id:
                partners |= lead.partner_id
                email = lead.partner_id.email or lead.email_from
            normalized = email_normalize_all(email) if email else []
            emails_by_lead[lead] = normalized
            all_emails.update(normalized)

        empty = self.env["crm.lead"]
        if not all_emails and not partners:
            return dict.fromkeys(leads, empty)

        domain = Domain.FALSE
        if all_emails:
            domain |= Domain("email_normalized", "in", list(all_emails))
        if partners:
            domain |= Domain("partner_id", "in", partners.ids)
        if include_lost:
            domain &= Domain("won_status", "!=", "won") & (
                Domain("type", "=", "opportunity") | Domain("active", "=", True)
            )
        else:
            domain &= Domain("won_status", "=", "pending") & Domain("active", "=", True)
        candidates = self.with_context(active_test=False).search(domain)

        ids_by_email, ids_by_partner = defaultdict(list), defaultdict(list)
        for candidate in candidates:
            ids_by_email[candidate.email_normalized].append(candidate.id)
            if candidate.partner_id:
                ids_by_partner[candidate.partner_id.id].append(candidate.id)
        rank = {candidate.id: index for index, candidate in enumerate(candidates)}

        duplicates_by_lead = {}
        for lead in leads:
            dup_ids = {
                dup_id
                for normalized in emails_by_lead[lead]
                for dup_id in ids_by_email.get(normalized, ())
            }
            if with_partner and lead.partner_id:
                dup_ids.update(ids_by_partner.get(lead.partner_id.id, ()))
            duplicates_by_lead[lead] = candidates.browse(
                sorted(dup_ids, key=rank.__getitem__)
            ).with_prefetch(candidates._prefetch_ids)
        return duplicates_by_lead

    def _sort_by_confidence_level(self, reverse=False):
        def opps_key(opportunity):
            return (
                opportunity.type == "opportunity" or opportunity.active,
                opportunity.type == "opportunity",
                opportunity.stage_id.sequence,
                opportunity.probability,
                -opportunity._origin.id,
            )

        return self.sorted(key=opps_key, reverse=reverse)

    def _find_matching_partner(self):
        self.check_singleton()
        partner = self.partner_id
        if not partner and (self.email_normalized or self.email_from):
            partner = self._partner_get_or_create_from_emails_single(
                [self.email_normalized or self.email_from],
                no_create=True,
            )
        return partner

    def _create_customer(self, with_parent=None):
        Partner = self.env["res.partner"]
        contact_name = self.contact_name
        if not contact_name:
            contact_name = (
                parse_contact_from_email(self.email_from)[0]
                if self.email_from
                else False
            )

        if with_parent:
            partner_company = with_parent
        elif self.partner_name:
            partner_company = Partner.create(
                self._prepare_customer_values(self.partner_name, is_company=True)
            )
        elif self.partner_id:
            partner_company = self.partner_id
        else:
            partner_company = self.env["res.partner"]

        if contact_name:
            return Partner.create(
                self._prepare_customer_values(
                    contact_name, is_company=False, parent_id=partner_company.id
                )
            )

        if partner_company:
            return partner_company
        return Partner.create(
            self._prepare_customer_values(self.name, is_company=False)
        )

    def _mail_get_customer_information(self):
        email_keys_to_values = super()._mail_get_customer_information()

        for lead in self:
            email_key = lead.email_normalized or lead.email_from
            if not email_key and len(self) > 1:
                continue
            values = email_keys_to_values.setdefault(email_key, {})
            contact_name = (
                lead.contact_name
                or parse_contact_from_email(lead.email_from)[0]
                or lead.email_from
            )
            is_company = bool(lead.partner_name) and contact_name == lead.partner_name
            values.update(
                {
                    key: val
                    for key, val in lead._prepare_customer_values(
                        contact_name, is_company=is_company, parent_id=False
                    ).items()
                    if val and key != "email"
                }
            )
            values["is_company"] = is_company
            if not is_company and lead.commercial_partner_id:
                values["parent_id"] = lead.commercial_partner_id.id
        return email_keys_to_values

    def _prepare_customer_values(self, partner_name, is_company=False, parent_id=False):
        email_parts = tools.email_split(self.email_from)
        res = {
            "name": partner_name,
            "user_id": self.env.context.get("default_user_id") or self.user_id.id,
            "comment": self.description,
            "phone_ids": [Command.set(self.phone_ids.ids)] if self.phone_ids else False,
            "email": email_parts[0] if email_parts else False,
            "function": self.function,
            "street": self.street,
            "street2": self.street2,
            "zip": self.zip,
            "city": self.city,
            "country_id": self.country_id.id,
            "state_id": self.state_id.id,
            "website": self.website,
            "parent_id": parent_id,
            "is_company": is_company,
            "type": "contact",
        }
        if self.lang_id.active:
            res["lang"] = self.lang_id.code
        return res

    def _is_rule_based_assignment_activated(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("crm.lead.auto.assignment", False)
        )

    def _creation_subtype(self):
        return self.env.ref("crm.mt_lead_create")

    def _creation_message(self):
        self.check_singleton()
        if self.team_id:
            return _(
                'A new lead has been created for the team "%(team_name)s".',
                team_name=self.team_id.display_name,
            )
        return _("A new lead has been created and is not assigned to any team.")

    def _track_subtype(self, init_values):
        self.check_singleton()
        if "stage_id" in init_values and self.won_status == "won":
            return self.env.ref("crm.mt_lead_won")
        elif "lost_reason_id" in init_values and self.lost_reason_id:
            return self.env.ref("crm.mt_lead_lost")
        elif "stage_id" in init_values:
            return self.env.ref("crm.mt_lead_stage")
        elif "won_status" in init_values and self.won_status != "lost":
            return self.env.ref("crm.mt_lead_restored")
        elif "won_status" in init_values and self.won_status == "lost":
            return self.env.ref("crm.mt_lead_lost")
        return super()._track_subtype(init_values)

    def _notify_by_email_prepare_rendering_context(
        self,
        message,
        msg_vals=False,
        model_description=False,
        force_email_company=False,
        force_email_lang=False,
        force_record_name=False,
        tracking_values=None,
    ):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message,
            msg_vals=msg_vals,
            model_description=model_description,
            force_email_company=force_email_company,
            force_email_lang=force_email_lang,
            force_record_name=force_record_name,
            tracking_values=tracking_values,
        )
        if self.date_deadline:
            render_context["subtitles"].append(
                _(
                    "Deadline: %s",
                    self.date_deadline.strftime(get_lang(self.env).date_format),
                )
            )
        return render_context

    def _notify_get_reply_to_addresses(self):
        addresses = self.team_id.sudo()._notify_get_usage_reply_to_addresses("sale")
        res = {
            lead.id: addresses[lead.team_id.id]
            for lead in self
            if lead.team_id and lead.team_id.id in addresses
        }
        leftover = self.filtered(lambda rec: not rec.team_id)
        if leftover:
            res.update(super(CrmLead, leftover)._notify_get_reply_to_addresses())
        return res

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        self = self.with_context(default_user_id=False)

        if custom_values is None:
            custom_values = {}
        defaults = {
            "name": msg_dict.get("subject") or _("No Subject"),
            "email_from": msg_dict.get("from"),
            "partner_id": msg_dict.get("author_id", False),
        }
        if msg_dict.get("priority") in dict(crm_stage.AVAILABLE_PRIORITIES):
            defaults["priority"] = msg_dict.get("priority")
        defaults.update(custom_values)

        new_lead = super().message_new(msg_dict, custom_values=defaults)
        new_lead._update_userless_leads_with_team_leader(_("incoming email"))
        return new_lead

    def _message_post_after_hook(self, message, msg_vals):
        if self.email_from and not self.partner_id:
            new_partner = message.partner_ids.filtered(
                lambda partner: (
                    partner.email == self.email_from
                    or (
                        self.email_normalized
                        and partner.email_normalized == self.email_normalized
                    )
                )
            )
            if new_partner:
                if new_partner[0].email_normalized:
                    email_domain = (
                        "email_normalized",
                        "=",
                        new_partner[0].email_normalized,
                    )
                else:
                    email_domain = ("email_from", "=", new_partner[0].email)
                self.search(
                    [
                        ("partner_id", "=", False),
                        email_domain,
                        ("stage_id.fold", "=", False),
                    ]
                ).write({"partner_id": new_partner[0].id})
        return super()._message_post_after_hook(message, msg_vals)

    @api.model
    def get_import_templates(self):
        return [
            {
                "label": _("Import Template for Leads & Opportunities"),
                "template": "/crm/static/xls/crm_lead.xls",
            }
        ]
