# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pytz
import threading
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from markupsafe import Markup

from odoo import api, fields, models, tools
from odoo.addons.iap.tools import iap_tools
from odoo.addons.mail.tools import mail_validation
from odoo.addons.phone_validation.tools import phone_validation
from odoo.exceptions import UserError, AccessError
from odoo.osv import expression
from odoo.tools.translate import _
from odoo.tools import date_utils, email_normalize_all, is_html_empty, groupby, parse_contact_from_email, SQL
from odoo.tools.misc import get_lang

from . import crm_stage

_logger = logging.getLogger(__name__)


CRM_LEAD_FIELDS_TO_MERGE = [
    # UTM mixin
    'campaign_id',
    'medium_id',
    'source_id',
    # Mail mixin
    'email_cc',
    # description
    'name',
    'user_id',
    'color',
    'company_id',
    'lang_id',
    'team_id',
    'referred',
    # pipeline
    'stage_id',
    # revenues
    'expected_revenue',
    'recurring_plan',
    'recurring_revenue',
    # dates
    'create_date',
    'date_automation_last',
    'date_deadline',
    # partner / contact
    'partner_id',
    'title',
    'partner_name',
    'contact_name',
    'email_from',
    'function',
    'mobile',
    'phone',
    'website',
]

# Subset of partner fields: sync any of those
PARTNER_FIELDS_TO_SYNC = [
    'lang',
    'mobile',
    'function',
    'website',
]

# Subset of partner fields: sync all or none to avoid mixed addresses
PARTNER_ADDRESS_FIELDS_TO_SYNC = [
    'street',
    'street2',
    'city',
    'zip',
    'state_id',
    'country_id',
]

# Those values have been determined based on benchmark to minimise
# computation time, number of transaction and transaction time.
PLS_COMPUTE_BATCH_STEP = 50000  # PREFETCH_MAX = 1000 but larger cluster can speed up global computation
PLS_UPDATE_BATCH_STEP = 5000


class CrmLead(models.Model):
    _name = 'crm.lead'
    _description = "Lead"
    _order = "priority desc, id desc"
    _inherit = ['mail.thread.cc',
                'mail.thread.blacklist',
                'mail.thread.phone',
                'mail.activity.mixin',
                'utm.mixin',
                'format.address.mixin',
                'mail.tracking.duration.mixin',
               ]
    _primary_email = 'email_from'
    _check_company_auto = True
    _track_duration_field = 'stage_id'

    # Description
    name = fields.Char(
        'Opportunity', index='trigram', required=True,
        compute='_compute_name', readonly=False, store=True)
    user_id = fields.Many2one(
        'res.users', string='Salesperson', default=lambda self: self.env.user,
        domain="[('share', '=', False)]",
        check_company=True, index=True, tracking=True)
    user_company_ids = fields.Many2many(
        'res.company', compute='_compute_user_company_ids',
        help='UX: Limit to lead company or all if no company')
    team_id = fields.Many2one(
        'crm.team', string='Sales Team', check_company=True, index=True, tracking=True,
        compute='_compute_team_id', ondelete="set null", readonly=False, store=True, precompute=True)
    lead_properties = fields.Properties(
        'Properties', definition='team_id.lead_properties_definition',
        copy=True)
    company_id = fields.Many2one(
        'res.company', string='Company', index=True,
        compute='_compute_company_id', readonly=False, store=True)
    referred = fields.Char('Referred By')
    description = fields.Html('Notes')
    active = fields.Boolean('Active', default=True, tracking=True)
    type = fields.Selection([
        ('lead', 'Lead'), ('opportunity', 'Opportunity')], required=True, tracking=15, index=True,
        default=lambda self: 'lead' if self.env.user.has_group('crm.group_use_lead') else 'opportunity')
    # Pipeline management
    priority = fields.Selection(
        crm_stage.AVAILABLE_PRIORITIES, string='Priority', index=True,
        default=crm_stage.AVAILABLE_PRIORITIES[0][0])
    stage_id = fields.Many2one(
        'crm.stage', string='Stage', index=True, tracking=True,
        compute='_compute_stage_id', readonly=False, store=True,
        copy=False, group_expand='_read_group_stage_ids', ondelete='restrict',
        domain="['|', ('team_id', '=', False), ('team_id', '=', team_id)]")
    tag_ids = fields.Many2many(
        'crm.tag', 'crm_tag_rel', 'lead_id', 'tag_id', string='Tags',
        help="Classify and analyze your lead/opportunity categories like: Training, Service")
    color = fields.Integer('Color Index', default=0)
    # Revenues
    expected_revenue = fields.Monetary('Expected Revenue', currency_field='company_currency', tracking=True, default=0.0)
    prorated_revenue = fields.Monetary('Prorated Revenue', currency_field='company_currency', store=True, compute="_compute_prorated_revenue")
    recurring_revenue = fields.Monetary('Recurring Revenues', currency_field='company_currency', tracking=True, default=0.0)
    recurring_plan = fields.Many2one('crm.recurring.plan', string="Recurring Plan")
    recurring_revenue_monthly = fields.Monetary('Expected MRR', currency_field='company_currency', store=True,
                                                compute="_compute_recurring_revenue_monthly")
    recurring_revenue_monthly_prorated = fields.Monetary('Prorated MRR', currency_field='company_currency', store=True,
                                                         compute="_compute_recurring_revenue_monthly_prorated")
    recurring_revenue_prorated = fields.Monetary('Prorated Recurring Revenues', currency_field='company_currency',
                                                 compute="_compute_recurring_revenue_prorated", store=True)
    company_currency = fields.Many2one("res.currency", string='Currency', compute="_compute_company_currency", compute_sudo=True)
    # Dates
    date_closed = fields.Datetime('Closed Date', readonly=True, copy=False)
    date_automation_last = fields.Datetime('Last Action', readonly=True)
    date_open = fields.Datetime(
        'Assignment Date', compute='_compute_date_open', readonly=True, store=True)
    day_open = fields.Float('Days to Assign', compute='_compute_day_open', store=True)
    day_close = fields.Float('Days to Close', compute='_compute_day_close', store=True)
    date_last_stage_update = fields.Datetime(
        'Last Stage Update', compute='_compute_date_last_stage_update', index=True, readonly=True, store=True)
    date_conversion = fields.Datetime('Conversion Date', readonly=True)
    date_deadline = fields.Date('Expected Closing', help="Estimate of the date on which the opportunity will be won.")
    # Customer / contact
    partner_id = fields.Many2one(
        'res.partner', string='Customer', check_company=True, index=True, tracking=10,
        help="Linked partner (optional). Usually created when converting the lead. You can find a partner by its Name, TIN, Email or Internal Reference.")
    partner_is_blacklisted = fields.Boolean('Partner is blacklisted', related='partner_id.is_blacklisted', readonly=True)
    contact_name = fields.Char(
        'Contact Name', index='trigram', tracking=30,
        compute='_compute_contact_name', readonly=False, store=True)
    partner_name = fields.Char(
        'Company Name', index='trigram', tracking=20,
        compute='_compute_partner_name', readonly=False, store=True,
        help='The name of the future partner company that will be created while converting the lead into opportunity')
    function = fields.Char('Job Position', compute='_compute_function', readonly=False, store=True)
    email_from = fields.Char(
        'Email', tracking=40, index='trigram',
        compute='_compute_email_from', inverse='_inverse_email_from', readonly=False, store=True)
    email_normalized = fields.Char(index='trigram')  # inherited via mail.thread.blacklist
    email_domain_criterion = fields.Char(
        string='Email Domain Criterion',
        compute="_compute_email_domain_criterion",
        index='btree_not_null',  # used for exact match, void value do not matter
        store=True,
    )
    phone = fields.Char(
        'Phone', tracking=50,
        compute='_compute_phone', inverse='_inverse_phone', readonly=False, store=True)
    mobile = fields.Char('Mobile', compute='_compute_mobile', readonly=False, store=True)
    phone_sanitized = fields.Char(index='btree_not_null')  # inherited via mail.thread.phone
    phone_state = fields.Selection([
        ('correct', 'Correct'),
        ('incorrect', 'Incorrect')], string='Phone Quality', compute="_compute_phone_state", store=True)
    email_state = fields.Selection([
        ('correct', 'Correct'),
        ('incorrect', 'Incorrect')], string='Email Quality', compute="_compute_email_state", store=True)
    website = fields.Char('Website', help="Website of the contact", compute="_compute_website", readonly=False, store=True)
    lang_id = fields.Many2one(
        'res.lang', string='Language',
        compute='_compute_lang_id', readonly=False, store=True)
    lang_code = fields.Char(related='lang_id.code')
    lang_active_count = fields.Integer(compute='_compute_lang_active_count')
    # Address fields
    street = fields.Char('Street', compute='_compute_partner_address_values', readonly=False, store=True)
    street2 = fields.Char('Street2', compute='_compute_partner_address_values', readonly=False, store=True)
    zip = fields.Char('Zip', change_default=True, compute='_compute_partner_address_values', readonly=False, store=True)
    city = fields.Char('City', compute='_compute_partner_address_values', readonly=False, store=True)
    state_id = fields.Many2one(
        "res.country.state", string='State',
        compute='_compute_partner_address_values', readonly=False, store=True,
        domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one(
        'res.country', string='Country',
        compute='_compute_partner_address_values', readonly=False, store=True)
    # Probability (Opportunity only)
    probability = fields.Float(
        'Probability', aggregator="avg", copy=False,
        compute='_compute_probabilities', readonly=False, store=True)
    automated_probability = fields.Float('Automated Probability', compute='_compute_probabilities', readonly=True, store=True)
    is_automated_probability = fields.Boolean('Is automated probability?', compute="_compute_is_automated_probability")
    # Won/Lost
    lost_reason_id = fields.Many2one(
        'crm.lost.reason', string='Lost Reason',
        index=True, ondelete='restrict', tracking=True)
    # Statistics
    calendar_event_ids = fields.One2many('calendar.event', 'opportunity_id', string='Meetings')
    duplicate_lead_ids = fields.Many2many("crm.lead", compute="_compute_potential_lead_duplicates", string="Potential Duplicate Lead", context={"active_test": False})
    duplicate_lead_count = fields.Integer(compute="_compute_potential_lead_duplicates", string="Potential Duplicate Lead Count")
    meeting_display_date = fields.Date(compute="_compute_meeting_display")
    meeting_display_label = fields.Char(compute="_compute_meeting_display")
    # UX
    partner_email_update = fields.Boolean('Partner Email will Update', compute='_compute_partner_email_update')
    partner_phone_update = fields.Boolean('Partner Phone will Update', compute='_compute_partner_phone_update')
    is_partner_visible = fields.Boolean('Is Partner Visible', compute='_compute_is_partner_visible')
    # UTMs - enforcing the fact that we want to 'set null' when relation is unlinked
    campaign_id = fields.Many2one(ondelete='set null')
    medium_id = fields.Many2one(ondelete='set null')
    source_id = fields.Many2one(ondelete='set null')

    _check_probability = models.Constraint(
        'check(probability >= 0 and probability <= 100)',
        'The probability of closing the deal should be between 0% and 100%!',
    )
    _user_id_team_id_type_index = models.Index("(user_id, team_id, type)")
    _create_date_team_id_idx = models.Index("(create_date, team_id)")

    @api.depends('company_id')
    def _compute_user_company_ids(self):
        all_companies = self.env['res.company'].search([])
        for lead in self:
            if not lead.company_id:
                lead.user_company_ids = all_companies
            else:
                lead.user_company_ids = lead.company_id

    @api.depends('company_id')
    def _compute_company_currency(self):
        for lead in self:
            if not lead.company_id:
                lead.company_currency = self.env.company.currency_id
            else:
                lead.company_currency = lead.company_id.currency_id

    @api.depends('user_id', 'type')
    def _compute_team_id(self):
        """ When changing the user, also set a team_id or restrict team id
        to the ones user_id is member of. """
        for lead in self:
            # setting user as void should not trigger a new team computation
            if not lead.user_id:
                continue
            user = lead.user_id
            if lead.team_id and user in (lead.team_id.member_ids | lead.team_id.user_id):
                continue
            team_domain = [('use_leads', '=', True)] if lead.type == 'lead' else [('use_opportunities', '=', True)]
            team = self.env['crm.team']._get_default_team_id(user_id=user.id, domain=team_domain)
            if lead.team_id != team:
                lead.team_id = team.id

    @api.depends('user_id', 'team_id', 'partner_id')
    def _compute_company_id(self):
        """ Compute company_id coherency. """
        for lead in self:
            proposal = lead.company_id

            # invalidate wrong configuration
            if proposal:
                # company not in responsible companies
                if lead.user_id and proposal not in lead.user_id.company_ids:
                    proposal = False
                # inconsistent
                elif lead.team_id.company_id and proposal != lead.team_id.company_id:
                    proposal = False
                # void company on team and no assignee
                elif lead.team_id and not lead.team_id.company_id and not lead.user_id:
                    proposal = False
                # no user and no team -> void company and let assignment do its job
                # unless customer has a company
                elif not lead.team_id and not lead.user_id and \
                        (not lead.partner_id or lead.partner_id.company_id != proposal):
                    proposal = False

            # propose a new company based on team > user (respecting context) > partner
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

    @api.depends('team_id', 'type')
    def _compute_stage_id(self):
        for lead in self:
            if not lead.stage_id:
                lead.stage_id = lead._stage_find(domain=[('fold', '=', False)]).id

    @api.depends('user_id')
    def _compute_date_open(self):
        for lead in self:
            if not lead.date_open and lead.user_id:
                lead.date_open = self.env.cr.now()

    @api.depends('stage_id')
    def _compute_date_last_stage_update(self):
        for lead in self:
            if not lead.date_last_stage_update:
                lead.date_last_stage_update = self.env.cr.now()

    @api.depends('create_date', 'date_open')
    def _compute_day_open(self):
        """ Compute difference between create date and open date """
        leads = self.filtered(lambda l: l.date_open and l.create_date)
        others = self - leads
        others.day_open = None
        for lead in leads:
            date_create = fields.Datetime.from_string(lead.create_date).replace(microsecond=0)
            date_open = fields.Datetime.from_string(lead.date_open)
            lead.day_open = abs((date_open - date_create).days)

    @api.depends('create_date', 'date_closed')
    def _compute_day_close(self):
        """ Compute difference between current date and log date """
        leads = self.filtered(lambda l: l.date_closed and l.create_date)
        others = self - leads
        others.day_close = None
        for lead in leads:
            date_create = fields.Datetime.from_string(lead.create_date)
            date_close = fields.Datetime.from_string(lead.date_closed)
            lead.day_close = abs((date_close - date_create).days)

    @api.depends('partner_id')
    def _compute_name(self):
        for lead in self:
            if not lead.name and lead.partner_id and lead.partner_id.name:
                lead.name = _("%s's opportunity") % lead.partner_id.name

    @api.depends('partner_id')
    def _compute_contact_name(self):
        """ compute the new values when partner_id has changed """
        for lead in self:
            lead.update(lead._prepare_contact_name_from_partner(lead.partner_id))

    @api.depends('partner_id')
    def _compute_partner_name(self):
        """ compute the new values when partner_id has changed """
        for lead in self:
            lead.update(lead._prepare_partner_name_from_partner(lead.partner_id))

    @api.depends('partner_id')
    def _compute_function(self):
        """ compute the new values when partner_id has changed """
        for lead in self:
            if not lead.function or lead.partner_id.function:
                lead.function = lead.partner_id.function

    @api.depends('partner_id')
    def _compute_mobile(self):
        """ compute the new values when partner_id has changed """
        for lead in self:
            if not lead.mobile or lead.partner_id.mobile:
                lead.mobile = lead.partner_id.mobile

    @api.depends('partner_id')
    def _compute_website(self):
        """ compute the new values when partner_id has changed """
        for lead in self:
            if not lead.website or lead.partner_id.website:
                lead.website = lead.partner_id.website

    @api.depends('partner_id')
    def _compute_lang_id(self):
        """ compute the lang based on partner, erase any value to force the partner
        one if set. """
        # prepare cache
        lang_codes = [code for code in self.mapped('partner_id.lang') if code]
        if lang_codes:
            lang_id_by_code = dict(
                (code, self.env['res.lang']._get_data(code=code).id)
                for code in lang_codes
            )
        else:
            lang_id_by_code = {}
        for lead in self.filtered('partner_id'):
            lead.lang_id = lang_id_by_code.get(lead.partner_id.lang, False)

    @api.depends('lang_id')
    def _compute_lang_active_count(self):
        self.lang_active_count = len(self.env['res.lang'].get_installed())

    @api.depends('partner_id')
    def _compute_partner_address_values(self):
        """ Sync all or none of address fields """
        for lead in self:
            lead.update(lead._prepare_address_values_from_partner(lead.partner_id))

    @api.depends('partner_id.email')
    def _compute_email_from(self):
        for lead in self:
            if lead.partner_id.email and lead._get_partner_email_update():
                lead.email_from = lead.partner_id.email

    def _inverse_email_from(self):
        for lead in self:
            if lead._get_partner_email_update(force_void=False):
                lead.partner_id.email = lead.email_from

    @api.depends('email_normalized')
    def _compute_email_domain_criterion(self):
        self.email_domain_criterion = False
        for lead in self.filtered('email_normalized'):
            lead.email_domain_criterion = iap_tools.mail_prepare_for_domain_search(
                lead.email_normalized
            )

    @api.depends('partner_id.phone')
    def _compute_phone(self):
        for lead in self:
            if lead.partner_id.phone and lead._get_partner_phone_update():
                lead.phone = lead.partner_id.phone

    def _inverse_phone(self):
        for lead in self:
            if lead._get_partner_phone_update(force_void=False):
                lead.partner_id.phone = lead.phone

    @api.depends('phone', 'country_id.code')
    def _compute_phone_state(self):
        for lead in self:
            phone_status = False
            if lead.phone:
                country_code = lead.country_id.code if lead.country_id and lead.country_id.code else None
                try:
                    if phone_validation.phone_parse(lead.phone, country_code):  # otherwise library not installed
                        phone_status = 'correct'
                except UserError:
                    phone_status = 'incorrect'
            lead.phone_state = phone_status

    @api.depends('email_from')
    def _compute_email_state(self):
        for lead in self:
            email_state = False
            if lead.email_from:
                email_state = 'incorrect'
                for email in email_normalize_all(lead.email_from):
                    if mail_validation.mail_validate(email):
                        email_state = 'correct'
                        break
            lead.email_state = email_state

    @api.depends('probability', 'automated_probability')
    def _compute_is_automated_probability(self):
        """ If probability and automated_probability are equal probability computation
        is considered as automatic, aka probability is sync with automated_probability """
        for lead in self:
            lead.is_automated_probability = tools.float_compare(lead.probability, lead.automated_probability, 2) == 0

    @api.depends(lambda self: ['stage_id', 'team_id'] + self._pls_get_safe_fields())
    def _compute_probabilities(self):
        lead_probabilities = self._pls_get_naive_bayes_probabilities()
        for lead in self:
            if lead.id in lead_probabilities:
                was_automated = lead.active and lead.is_automated_probability
                lead.automated_probability = lead_probabilities[lead.id]
                if was_automated:
                    lead.probability = lead.automated_probability

    @api.depends('expected_revenue', 'probability')
    def _compute_prorated_revenue(self):
        for lead in self:
            lead.prorated_revenue = round((lead.expected_revenue or 0.0) * (lead.probability or 0) / 100.0, 2)

    @api.depends('recurring_revenue', 'recurring_plan.number_of_months')
    def _compute_recurring_revenue_monthly(self):
        for lead in self:
            lead.recurring_revenue_monthly = (lead.recurring_revenue or 0.0) / (lead.recurring_plan.number_of_months or 1)

    @api.depends('recurring_revenue_monthly', 'probability')
    def _compute_recurring_revenue_monthly_prorated(self):
        for lead in self:
            lead.recurring_revenue_monthly_prorated = (lead.recurring_revenue_monthly or 0.0) * (lead.probability or 0) / 100.0

    @api.depends('recurring_revenue', 'probability')
    def _compute_recurring_revenue_prorated(self):
        for lead in self:
            lead.recurring_revenue_prorated = (lead.recurring_revenue or 0.0) * (lead.probability or 0) / 100.0

    @api.depends('calendar_event_ids', 'calendar_event_ids.start')
    def _compute_meeting_display(self):
        now = fields.Datetime.now()
        meeting_data = self.env['calendar.event'].sudo()._read_group([
            ('opportunity_id', 'in', self.ids),
        ], ['opportunity_id'], ['start:array_agg', 'start:max'])
        mapped_data = {
            lead: {
                'last_meeting_date': last_meeting_date,
                'next_meeting_date': min([dt for dt in meeting_start_dates if dt > now] or [False]),
            } for lead, meeting_start_dates, last_meeting_date in meeting_data
        }
        for lead in self:
            lead_meeting_info = mapped_data.get(lead)
            if not lead_meeting_info:
                lead.meeting_display_date = False
                lead.meeting_display_label = _('No Meeting')
            elif lead_meeting_info['next_meeting_date']:
                lead.meeting_display_date = lead_meeting_info['next_meeting_date']
                lead.meeting_display_label = _('Next Meeting')
            else:
                lead.meeting_display_date = lead_meeting_info['last_meeting_date']
                lead.meeting_display_label = _('Last Meeting')

    @api.depends('email_domain_criterion', 'email_normalized', 'partner_id',
                 'phone_sanitized')
    def _compute_potential_lead_duplicates(self):
        """ Override potential lead duplicates computation to be more efficient
        with high lead volume.
        Criterions:
          * email domain exact match;
          * phone_sanitized exact match;
          * same commercial entity;
        """
        SEARCH_RESULT_LIMIT = 21

        def return_if_relevant(model_name, domain):
            """ Returns the recordset obtained by performing a search on the provided
            model with the provided domain if the cardinality of that recordset is
            below a given threshold (i.e: `SEARCH_RESULT_LIMIT`). Otherwise, returns
            an empty recordset of the provided model as it indicates search term
            was not relevant.
            Note: The function will use the administrator privileges to guarantee
            that a maximum amount of leads will be included in the search results
            and transcend multi-company record rules. It also includes archived
            records. Idea is that counter indicates duplicates are present and
            the lead could be escalated to managers.
            """
            model = self.env[model_name].sudo().with_context(active_test=False)
            res = model.search(domain, limit=SEARCH_RESULT_LIMIT)
            return res if len(res) < SEARCH_RESULT_LIMIT else model

        for lead in self:
            lead_id = lead._origin.id
            common_lead_domain = [
                ('id', '!=', lead_id)
            ]

            duplicate_lead_ids = self.env['crm.lead']

            # check the "company" email domain duplicates
            if lead.email_domain_criterion:
                duplicate_lead_ids |= return_if_relevant('crm.lead', common_lead_domain + [
                    ('email_domain_criterion', '=', lead.email_domain_criterion)
                ])
            # check for "same commercial entity" duplicates
            if lead.partner_id and lead.partner_id.commercial_partner_id:
                duplicate_lead_ids |= lead.with_context(active_test=False).search(common_lead_domain + [
                    ("partner_id", "child_of", lead.partner_id.commercial_partner_id.ids)
                ])
            # check the phone number duplicates, based on phone_sanitized. Only
            # exact matches are found, and the single one stored in phone_sanitized
            # in case phone and mobile are both set.
            if lead.phone_sanitized:
                duplicate_lead_ids |= return_if_relevant('crm.lead', common_lead_domain + [
                    ('phone_sanitized', '=', lead.phone_sanitized)
                ])

            lead.duplicate_lead_ids = duplicate_lead_ids + lead
            lead.duplicate_lead_count = len(duplicate_lead_ids)

    @api.depends('email_from', 'partner_id')
    def _compute_partner_email_update(self):
        for lead in self:
            lead.partner_email_update = lead._get_partner_email_update(force_void=False)

    @api.depends('phone', 'partner_id')
    def _compute_partner_phone_update(self):
        for lead in self:
            lead.partner_phone_update = lead._get_partner_phone_update(force_void=False)

    @api.depends_context('uid')
    @api.depends('partner_id', 'type')
    def _compute_is_partner_visible(self):
        """ When the crm.lead is of type 'lead', we don't want to display the "Customer" field on the form view
        unless it's set (or debug mode).

        Indeed, most of the times leads will not have this information set, since when we assign a Customer we
        usually convert the lead to an opportunity as well.

        This means that on the lead form, we don't want to display this field since it may be misleading for the
        end user.
        When it's set however, we want to display it, mainly because there are a few automatic synchronizations between
        the lead and its partner (phone and email for examples), and this needs to be clear that modifying
        one of those fields will in turn modify the linked partner."""
        is_debug_mode = self.env.user.has_group('base.group_no_one')
        for lead in self:
            lead.is_partner_visible = bool(lead.type == 'opportunity' or lead.partner_id or is_debug_mode)

    @api.onchange('phone', 'country_id', 'company_id')
    def _onchange_phone_validation(self):
        if self.phone:
            self.phone = self._phone_format(fname='phone', force_format='INTERNATIONAL') or self.phone

    @api.onchange('mobile', 'country_id', 'company_id')
    def _onchange_mobile_validation(self):
        if self.mobile:
            self.mobile = self._phone_format(fname='mobile', force_format='INTERNATIONAL') or self.mobile

    def _prepare_values_from_partner(self, partner):
        """ Get a dictionary with values coming from partner information to
        copy on a lead. Non-address fields get the current lead
        values to avoid being reset if partner has no value for them. """

        # Sync all address fields from partner, or none, to avoid mixing them.
        values = self._prepare_address_values_from_partner(partner)

        # For other fields, get the info from the partner, but only if set
        values.update({f: partner[f] or self[f] for f in PARTNER_FIELDS_TO_SYNC if f != 'lang'})
        if partner.lang:
            values['lang_id'] = self.env['res.lang']._get_data(code=partner.lang).id

        # Fields with specific logic
        values.update(self._prepare_contact_name_from_partner(partner))
        values.update(self._prepare_partner_name_from_partner(partner))

        return self._convert_to_write(values)

    def _prepare_address_values_from_partner(self, partner):
        # Sync all address fields from partner, or none, to avoid mixing them.
        if any(partner[f] for f in PARTNER_ADDRESS_FIELDS_TO_SYNC):
            values = {f: partner[f] for f in PARTNER_ADDRESS_FIELDS_TO_SYNC}
        else:
            values = {f: self[f] for f in PARTNER_ADDRESS_FIELDS_TO_SYNC}
        return values

    def _prepare_contact_name_from_partner(self, partner):
        contact_name = False if partner.is_company else partner.name
        return {'contact_name': contact_name or self.contact_name}

    def _prepare_partner_name_from_partner(self, partner):
        """ Company name: name of partner parent (if set) or name of partner
        (if company) or company_name of partner (if not a company). """
        partner_name = partner.parent_id.name
        if not partner_name and partner.is_company:
            partner_name = partner.name
        elif not partner_name and partner.company_name:
            partner_name = partner.company_name
        return {'partner_name': partner_name or self.partner_name}

    def _get_partner_email_update(self, force_void=True):
        """Calculate if we should write the email on the related partner. When
        the email of the lead / partner is an empty string, we force it to False
        to not propagate a False on an empty string.

        Done in a separate method so it can be used in both ribbon and inverse
        and compute of email update methods.

        :param bool force_void: if False, skip when lead has a void email value.
          This is used notably to avoid propagating void lead value to a valid
          partner value.
        """
        self.ensure_one()
        if self.partner_id and (force_void or self.email_from) and self.email_from != self.partner_id.email:
            lead_email_normalized = tools.email_normalize(self.email_from) or self.email_from or False
            partner_email_normalized = tools.email_normalize(self.partner_id.email) or self.partner_id.email or False
            return lead_email_normalized != partner_email_normalized
        return False

    def _get_partner_phone_update(self, force_void=True):
        """Calculate if we should write the phone on the related partner. When
        the phone of the lead / partner is an empty string, we force it to False
        to not propagate a False on an empty string.

        Done in a separate method so it can be used in both ribbon and inverse
        and compute of phone update methods.

        :param bool force_void: if False, skip when lead has a void phone value.
          This is used notably to avoid propagating void lead value to a valid
          partner value.
        """
        self.ensure_one()
        if self.partner_id and (force_void or self.phone) and self.phone != self.partner_id.phone:
            lead_phone_formatted = self._phone_format(fname='phone') or self.phone or False
            partner_phone_formatted = self.partner_id._phone_format(fname='phone') or self.partner_id.phone or False
            return lead_phone_formatted != partner_phone_formatted
        return False

    # ------------------------------------------------------------
    # ORM
    # ------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('website'):
                vals['website'] = self.env['res.partner']._clean_website(vals['website'])
        leads = super().create(vals_list)

        for lead, values in zip(leads, vals_list):
            if any(field in ['active', 'stage_id'] for field in values):
                lead._handle_won_lost(values)

        return leads

    def write(self, vals):
        if vals.get('website'):
            vals['website'] = self.env['res.partner']._clean_website(vals['website'])

        now = self.env.cr.now()
        stage_updated, stage_is_won = False, False
        # stage change (or reset): update date_last_stage_update if at least one
        # lead does not have the same stage
        if 'stage_id' in vals:
            stage_updated = any(lead.stage_id.id != vals['stage_id'] for lead in self)
            if stage_updated:
                vals['date_last_stage_update'] = now
            if stage_updated and vals.get('stage_id'):
                stage = self.env['crm.stage'].browse(vals['stage_id'])
                if stage.is_won:
                    vals.update({'probability': 100, 'automated_probability': 100})
                    stage_is_won = True
        # user change; update date_open if at least one lead does not
        # have the same user
        if 'user_id' in vals and not vals.get('user_id'):
            vals['date_open'] = False
        elif vals.get('user_id'):
            user_updated = any(lead.user_id.id != vals['user_id'] for lead in self)
            if user_updated:
                vals['date_open'] = now

        # stage change with new stage: update probability and date_closed
        if vals.get('probability', 0) >= 100 or not vals.get('active', True):
            vals['date_closed'] = fields.Datetime.now()
        elif vals.get('probability', 0) > 0:
            vals['date_closed'] = False
        elif stage_updated and not stage_is_won and not 'probability' in vals:
            vals['date_closed'] = False

        if any(field in ['active', 'stage_id'] for field in vals):
            self._handle_won_lost(vals)

        if not stage_is_won:
            return super().write(vals)

        # stage change between two won stages: does not change the date_closed
        leads_already_won = self.filtered(lambda lead: lead.stage_id.is_won)
        remaining = self - leads_already_won
        if remaining:
            result = super(CrmLead, remaining).write(vals)
        if leads_already_won:
            vals.pop('date_closed', False)
            result = super(CrmLead, leads_already_won).write(vals)
        return result

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        """ Override to support ordering on my_activity_date_deadline.

        Ordering through web client calls search_read() with an order parameter
        set. Method search_read() then calls search_fetch(). Here we override
        search_fetch() to intercept a search with an order on field
        my_activity_date_deadline. In that case we do the search in two steps.

        First step: fill with deadline-based results

          * Perform a read_group on my activities to get a mapping lead_id / deadline
            Remember date_deadline is required, we always have a value for it. Only
            the earliest deadline per lead is kept.
          * Search leads linked to those activities that also match the asked domain
            and order from the original search request.
          * Results of that search will be at the top of returned results. Use limit
            None because we have to search all leads linked to activities as ordering
            on deadline is done in post processing.
          * Reorder them according to deadline asc or desc depending on original
            search ordering. Finally take only a subset of those leads to fill with
            results matching asked offset / limit.

        Second step: fill with other results. If first step does not gives results
        enough to match offset and limit parameters we fill with a search on other
        leads. We keep the asked domain and ordering while filtering out already
        scanned leads to keep a coherent results.

        All other search and search_read are left untouched by this override to avoid
        side effects. Search_count is not affected by this override.
        """
        if not order or 'my_activity_date_deadline' not in order:
            return super().search_fetch(domain, field_names, offset, limit, order)
        order_items = [order_item.strip().lower() for order_item in (order or self._order).split(',')]

        # Perform a read_group on my activities to get a mapping lead_id / deadline
        # Remember date_deadline is required, we always have a value for it. Only
        # the earliest deadline per lead is kept.
        activity_asc = any('my_activity_date_deadline asc' in item for item in order_items)
        my_lead_activities = self.env['mail.activity']._read_group(
            [('res_model', '=', self._name), ('user_id', '=', self.env.uid)],
            ['res_id'],
            ['date_deadline:min'],
            order='date_deadline:min ASC, res_id',
        )
        my_lead_mapping = dict(my_lead_activities)
        my_lead_ids = list(my_lead_mapping.keys())
        my_lead_domain = expression.AND([[('id', 'in', my_lead_ids)], domain])
        my_lead_order = ', '.join(item for item in order_items if 'my_activity_date_deadline' not in item)

        # Search leads linked to those activities and order them. See docstring
        # of this method for more details.
        search_res = super().search_fetch(my_lead_domain, field_names, order=my_lead_order)
        my_lead_ids_ordered = sorted(search_res.ids, key=lambda lead_id: my_lead_mapping[lead_id], reverse=not activity_asc)
        # keep only requested window (offset + limit, or offset+)
        my_lead_ids_keep = my_lead_ids_ordered[offset:(offset + limit)] if limit else my_lead_ids_ordered[offset:]
        # keep list of already skipped lead ids to exclude them from future search
        my_lead_ids_skip = my_lead_ids_ordered[:(offset + limit)] if limit else my_lead_ids_ordered

        # do not go further if limit is achieved
        if limit and len(my_lead_ids_keep) >= limit:
            return self.browse(my_lead_ids_keep)

        # Fill with remaining leads. If a limit is given, simply remove count of
        # already fetched. Otherwise keep none. If an offset is set we have to
        # reduce it by already fetch results hereabove. Order is updated to exclude
        # my_activity_date_deadline when calling super() .
        lead_limit = (limit - len(my_lead_ids_keep)) if limit else None
        if offset:
            lead_offset = max((offset - len(search_res), 0))
        else:
            lead_offset = 0
        lead_order = ', '.join(item for item in order_items if 'my_activity_date_deadline' not in item)

        other_lead_res = super().search_fetch(
            expression.AND([[('id', 'not in', my_lead_ids_skip)], domain]),
            field_names, lead_offset, lead_limit, lead_order,
        )
        return self.browse(my_lead_ids_keep) + other_lead_res

    def _handle_won_lost(self, vals):
        """ This method handle the state changes :
        - To lost : We need to increment corresponding lost count in scoring frequency table
        - To won : We need to increment corresponding won count in scoring frequency table
        - From lost to Won : We need to decrement corresponding lost count + increment corresponding won count
        in scoring frequency table.
        - From won to lost : We need to decrement corresponding won count + increment corresponding lost count
        in scoring frequency table."""
        CrmLead = self.env['crm.lead']
        leads_reach_won = CrmLead
        leads_leave_won = CrmLead
        leads_reach_lost = CrmLead
        leads_leave_lost = CrmLead
        won_stage_ids = self.env['crm.stage'].search([('is_won', '=', True)]).ids
        for lead in self:
            if 'stage_id' in vals:
                if vals['stage_id'] in won_stage_ids:
                    if lead.probability == 0:
                        leads_leave_lost += lead
                    leads_reach_won += lead
                elif lead.stage_id.id in won_stage_ids and lead.active:  # a lead can be lost at won_stage
                    leads_leave_won += lead
            if 'active' in vals:
                if not vals['active'] and lead.active:  # archive lead
                    if lead.stage_id.id in won_stage_ids and lead not in leads_leave_won:
                        leads_leave_won += lead
                    leads_reach_lost += lead
                elif vals['active'] and not lead.active:  # restore lead
                    leads_leave_lost += lead

        leads_reach_won._pls_increment_frequencies(to_state='won')
        leads_leave_won._pls_increment_frequencies(from_state='won')
        leads_reach_lost._pls_increment_frequencies(to_state='lost')
        leads_leave_lost._pls_increment_frequencies(from_state='lost')

    def copy_data(self, default=None):
        # set default value in context, if not already set (Put stage to 'new' stage)
        # Set date_open to today if it is an opp
        default = dict(default or {})
        if not self.env.user.has_group('crm.group_use_recurring_revenues'):
            default['recurring_revenue'] = 0
            default['recurring_plan'] = False
        vals_list = super().copy_data(default=default)
        now = self.env.cr.now()
        for lead, vals in zip(self, vals_list):
            vals.setdefault('type', lead.type)
            vals.setdefault('team_id', lead.team_id.id)
            vals['date_open'] = now if lead.type == 'opportunity' else False
            if not lead.user_id.active:
                vals['user_id'] = False
        return vals_list

    def unlink(self):
        """ Update meetings when removing opportunities, otherwise you have
        a link to a record that does not lead anywhere. """
        meetings = self.env['calendar.event'].search([
            ('res_id', 'in', self.ids),
            ('res_model', '=', self._name),
        ])
        if meetings:
            meetings.write({
                'res_id': False,
                'res_model_id': False,
            })
        return super().unlink()

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        # retrieve team_id from the context and write the domain
        # - ('id', 'in', stages.ids): add columns that should be present
        # - OR ('fold', '=', False): add default columns that are not folded
        # - OR ('team_ids', '=', team_id), ('fold', '=', False) if team_id: add team columns that are not folded
        team_id = self._context.get('default_team_id')
        if team_id:
            search_domain = ['|', ('id', 'in', stages.ids), '|', ('team_id', '=', False), ('team_id', '=', team_id)]
        else:
            search_domain = ['|', ('id', 'in', stages.ids), ('team_id', '=', False)]

        # perform search
        stage_ids = stages.sudo()._search(search_domain, order=stages._order)
        return stages.browse(stage_ids)

    def _stage_find(self, team_id=False, domain=None, order='sequence, id', limit=1):
        """ Determine the stage of the current lead with its teams, the given domain and the given team_id
            :param team_id
            :param domain : base search domain for stage
            :param order : base search order for stage
            :param limit : base search limit for stage
            :returns crm.stage recordset
        """
        # collect all team_ids by adding given one, and the ones related to the current leads
        team_ids = set()
        if team_id:
            team_ids.add(team_id)
        for lead in self:
            if lead.team_id:
                team_ids.add(lead.team_id.id)
        # generate the domain
        if team_ids:
            search_domain = ['|', ('team_id', '=', False), ('team_id', 'in', list(team_ids))]
        else:
            search_domain = [('team_id', '=', False)]
        # AND with the domain in parameter
        if domain:
            search_domain += list(domain)
        # perform search, return the first found
        return self.env['crm.stage'].search(search_domain, order=order, limit=limit)

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    def action_archive(self):
        """ When archiving: mark probability as 0."""
        res = super().action_archive()
        self.write({'probability': 0, 'automated_probability': 0})
        return res

    def action_unarchive(self):
        """ When re-activating update probability again, for leads and opportunities. """
        activated = self.filtered(lambda rec: not rec.active)
        res = super().action_unarchive()
        if activated:
            activated.write({'lost_reason_id': False})
            activated._compute_probabilities()
        return res

    def action_set_lost(self, **additional_values):
        """ Lost semantic: probability = 0 or active = False """
        res = self.action_archive()
        if additional_values:
            self.write(dict(additional_values))
        return res

    def action_set_won(self):
        """ Won semantic: probability = 100 (active untouched) """
        self.action_unarchive()
        # group the leads by team_id, in order to write once by values couple (each write leads to frequency increment)
        leads_by_won_stage = {}
        for lead in self:
            won_stages = self._stage_find(domain=[('is_won', '=', True)], limit=None)
            # ABD : We could have a mixed pipeline, with "won" stages being separated by "standard"
            # stages. In the future, we may want to prevent any "standard" stage to have a higher
            # sequence than any "won" stage. But while this is not the case, searching
            # for the "won" stage while alterning the sequence order (see below) will correctly
            # handle such a case :
            #       stage sequence : [x] [x (won)] [y] [y (won)] [z] [z (won)]
            #       when in stage [y] and marked as "won", should go to the stage [y (won)],
            #       not in [x (won)] nor [z (won)]
            stage_id = next((stage for stage in won_stages if stage.sequence > lead.stage_id.sequence), None)
            if not stage_id:
                stage_id = next((stage for stage in reversed(won_stages) if stage.sequence <= lead.stage_id.sequence), won_stages)
            if stage_id in leads_by_won_stage:
                leads_by_won_stage[stage_id] += lead
            else:
                leads_by_won_stage[stage_id] = lead
        for won_stage_id, leads in leads_by_won_stage.items():
            leads.write({'stage_id': won_stage_id.id, 'probability': 100})
        return True

    def action_set_automated_probability(self):
        self.write({'probability': self.automated_probability})

    def action_set_won_rainbowman(self):
        self.ensure_one()
        self.action_set_won()

        message = self._get_rainbowman_message()
        if message:
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': message,
                    'img_url': '/web/image/%s/%s/image_1024' % (self.team_id.user_id._name, self.team_id.user_id.id) if self.team_id.user_id.image_1024 else '/web/static/img/smile.svg',
                    'type': 'rainbow_man',
                }
            }
        return True

    def get_rainbowman_message(self):
        self.ensure_one()
        if self.stage_id.is_won:
            return self._get_rainbowman_message()
        return False

    def _get_rainbowman_message(self):
        if not self.user_id or not self.team_id:
            return False
        if not self.expected_revenue:
            # Show rainbow man for the first won lead of a salesman, even if expected revenue is not set. It is not
            # very often that leads without revenues are marked won, so simply get count using ORM instead of query
            today = fields.Datetime.today()
            user_won_leads_count = self.search_count([
                ('type', '=', 'opportunity'),
                ('user_id', '=', self.user_id.id),
                ('probability', '=', 100),
                ('date_closed', '>=', date_utils.start_of(today, 'year')),
                ('date_closed', '<', date_utils.end_of(today, 'year')),
            ])
            if user_won_leads_count == 1:
                return _('Go, go, go! Congrats for your first deal.')
            return False

        self.flush_model()  # flush fields to make sure DB is up to date
        query = """
            SELECT
                SUM(CASE WHEN user_id = %(user_id)s THEN 1 ELSE 0 END) as total_won,
                MAX(CASE WHEN date_closed >= CURRENT_DATE - INTERVAL '30 days' AND user_id = %(user_id)s THEN expected_revenue ELSE 0 END) as max_user_30,
                MAX(CASE WHEN date_closed >= CURRENT_DATE - INTERVAL '7 days' AND user_id = %(user_id)s THEN expected_revenue ELSE 0 END) as max_user_7,
                MAX(CASE WHEN date_closed >= CURRENT_DATE - INTERVAL '30 days' AND team_id = %(team_id)s THEN expected_revenue ELSE 0 END) as max_team_30,
                MAX(CASE WHEN date_closed >= CURRENT_DATE - INTERVAL '7 days' AND team_id = %(team_id)s THEN expected_revenue ELSE 0 END) as max_team_7
            FROM crm_lead
            WHERE
                type = 'opportunity'
            AND
                active = True
            AND
                probability = 100
            AND
                DATE_TRUNC('year', date_closed) = DATE_TRUNC('year', CURRENT_DATE)
            AND
                (user_id = %(user_id)s OR team_id = %(team_id)s)
        """
        self.env.cr.execute(query, {'user_id': self.user_id.id,
                                    'team_id': self.team_id.id})
        query_result = self.env.cr.dictfetchone()

        message = False
        if query_result['total_won'] == 1:
            message = _('Go, go, go! Congrats for your first deal.')
        elif query_result['max_team_30'] == self.expected_revenue:
            message = _('Boom! Team record for the past 30 days.')
        elif query_result['max_team_7'] == self.expected_revenue:
            message = _('Yeah! Deal of the last 7 days for the team.')
        elif query_result['max_user_30'] == self.expected_revenue:
            message = _('You just beat your personal record for the past 30 days.')
        elif query_result['max_user_7'] == self.expected_revenue:
            message = _('You just beat your personal record for the past 7 days.')
        return message

    def action_schedule_meeting(self, smart_calendar=True):
        """ Open meeting's calendar view to schedule meeting on current opportunity.

            :param smart_calendar: boolean, to set to False if the view should not try to choose relevant
              mode and initial date for calendar view, see ``_get_opportunity_meeting_view_parameters``
            :return dict: dictionary value for created Meeting view
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        partner_ids = self.env.user.partner_id.ids
        if self.partner_id:
            partner_ids.append(self.partner_id.id)
        current_opportunity_id = self.id if self.type == 'opportunity' else False
        action['context'] = {
            'search_default_opportunity_id': current_opportunity_id,
            'default_opportunity_id': current_opportunity_id,
            'default_partner_id': self.partner_id.id,
            'default_partner_ids': partner_ids,
            'default_team_id': self.team_id.id,
            'default_name': self.name,
        }

        # 'Smart' calendar view : get the most relevant time period to display to the user.
        if current_opportunity_id and smart_calendar:
            mode, initial_date = self._get_opportunity_meeting_view_parameters()
            action['context'].update({'default_mode': mode, 'initial_date': initial_date})

        return action

    def _get_opportunity_meeting_view_parameters(self):
        """ Return the most relevant parameters for calendar view when viewing meetings linked to an opportunity.
            If there are any meetings that are not finished yet, only consider those meetings,
            since the user would prefer no to see past meetings. Otherwise, consider all meetings.
            Allday events datetimes are used without taking tz into account.
            -If there is no event, return week mode and false (The calendar will target 'now' by default)
            -If there is only one, return week mode and date of the start of the event.
            -If there are several events entirely on the same week, return week mode and start of first event.
            -Else, return month mode and the date of the start of first event as initial date. (If they are
            on the same month, this will display that month and therefore show all of them, which is expected)

            :return tuple(mode, initial_date)
                - mode: selected mode of the calendar view, 'week' or 'month'
                - initial_date: date of the start of the first relevant meeting. The calendar will target that date.
        """
        self.ensure_one()
        meeting_results = self.env["calendar.event"].search_read([('opportunity_id', '=', self.id)], ['start', 'stop', 'allday'])
        if not meeting_results:
            return "week", False

        user_tz = self.env.user.tz or self.env.context.get('tz')
        user_pytz = pytz.timezone(user_tz) if user_tz else pytz.utc

        # meeting_dts will contain one tuple of datetimes per meeting : (Start, Stop)
        # meetings_dts and now_dt are as per user time zone.
        meeting_dts = []
        now_dt = datetime.now().astimezone(user_pytz).replace(tzinfo=None)

        # When creating an allday meeting, whatever the TZ, it will be stored the same e.g. 00.00.00->23.59.59 in utc or
        # 08.00.00->18.00.00. Therefore we must not put it back in the user tz but take it raw.
        for meeting in meeting_results:
            if meeting.get('allday'):
                meeting_dts.append((meeting.get('start'), meeting.get('stop')))
            else:
                meeting_dts.append((meeting.get('start').astimezone(user_pytz).replace(tzinfo=None),
                                   meeting.get('stop').astimezone(user_pytz).replace(tzinfo=None)))

        # If there are meetings that are still ongoing or to come, only take those.
        unfinished_meeting_dts = [meeting_dt for meeting_dt in meeting_dts if meeting_dt[1] >= now_dt]
        relevant_meeting_dts = unfinished_meeting_dts if unfinished_meeting_dts else meeting_dts
        relevant_meeting_count = len(relevant_meeting_dts)

        if relevant_meeting_count == 1:
            return "week", relevant_meeting_dts[0][0].date()
        else:
            # Range of meetings
            earliest_start_dt = min(relevant_meeting_dt[0] for relevant_meeting_dt in relevant_meeting_dts)
            latest_stop_dt = max(relevant_meeting_dt[1] for relevant_meeting_dt in relevant_meeting_dts)

            # The week start day depends on language. We fetch the week_start of user's language. 1 is monday.
            lang_week_start = self.env["res.lang"].search_read([('code', '=', self.env.user.lang)], ['week_start'])
            # We substract one to make week_start_index range 0-6 instead of 1-7
            week_start_index = int(lang_week_start[0].get('week_start', '1')) - 1

            # We compute the weekday of earliest_start_dt according to week_start_index. earliest_start_dt_index will be 0 if we are on the
            # first day of the week and 6 on the last. weekday() returns 0 for monday and 6 for sunday. For instance, Tuesday in UK is the
            # third day of the week, so earliest_start_dt_index is 2, and remaining_days_in_week includes tuesday, so it will be 5.
            # The first term 7 is there to avoid negative left side on the modulo, improving readability.
            earliest_start_dt_weekday = (7 + earliest_start_dt.weekday() - week_start_index) % 7
            remaining_days_in_week = 7 - earliest_start_dt_weekday

            # We compute the start of the week following the one containing the start of the first meeting.
            next_week_start_date = earliest_start_dt.date() + timedelta(days=remaining_days_in_week)

            # Latest_stop_dt must be before the start of following week. Limit is therefore set at midnight of first day, included.
            meetings_in_same_week = latest_stop_dt <= datetime(next_week_start_date.year, next_week_start_date.month, next_week_start_date.day, 0, 0, 0)

            if meetings_in_same_week:
                return "week", earliest_start_dt.date()
            else:
                return "month", earliest_start_dt.date()

    def action_reschedule_meeting(self):
        self.ensure_one()
        action = self.action_schedule_meeting(smart_calendar=False)
        next_activity = self.activity_ids.filtered(lambda activity: activity.user_id == self.env.user)[:1]
        if next_activity.calendar_event_id:
            action['context']['initial_date'] = next_activity.calendar_event_id.start
        return action

    def action_show_potential_duplicates(self):
        """ Open kanban view to display duplicate leads or opportunity.
            :return dict: dictionary value for created kanban view
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("crm.crm_lead_opportunities")
        action['domain'] = [('id', 'in', self.duplicate_lead_ids.ids)]
        action['context'] = {
            'active_test': False,
            'create': False
        }
        return action

    def action_snooze(self):
        self.ensure_one()
        my_next_activity = self.activity_ids.filtered(lambda activity: activity.user_id == self.env.user)[:1]
        my_next_activity.action_snooze()
        return True

    # ------------------------------------------------------------
    # VIEWS
    # ------------------------------------------------------------

    def redirect_lead_opportunity_view(self):
        self.ensure_one()
        return {
            'name': _('Lead or Opportunity'),
            'view_mode': 'form',
            'res_model': 'crm.lead',
            'domain': [('type', '=', self.type)],
            'res_id': self.id,
            'view_id': False,
            'type': 'ir.actions.act_window',
            'context': {'default_type': self.type}
        }

    @api.model
    def get_empty_list_help(self, help_message):
        """ This method returns the action helpers for the leads. If help is already provided
            on the action, the same is returned. Otherwise, we build the help message which
            contains the alias responsible for creating the lead (if available) and return it.
        """
        if not is_html_empty(help_message):
            return help_message

        help_title, sub_title = "", ""
        if self._context.get('default_type') == 'lead':
            help_title = _('Create a new lead')
        else:
            help_title = _('Create an opportunity to start playing with your pipeline.')
        alias_domain = [
            ('company_id', '=', self.env.company.id),
            ('alias_id.alias_name', '!=', False),
            ('alias_id.alias_name', '!=', ''),
            ('alias_id.alias_model_id.model', '=', 'crm.lead'),
        ]
        # sort by use_leads, then by our membership of the team
        alias_records = self.env['crm.team'].search(alias_domain).sorted(
            lambda r: (r.use_leads, self.env.user in r.member_ids), reverse=True
        )
        alias_record = alias_records[0] if alias_records else None
        if alias_record and alias_record.alias_domain and alias_record.alias_name:
            sub_title = Markup(_('Use the <i>New</i> button, or send an email to %(email_link)s to test the email gateway.')) % {
                'email_link': Markup("<b><a href='mailto:%s'>%s</a></b>") % (alias_record.display_name, alias_record.display_name),
            }
        return super().get_empty_list_help(
            f'<p class="o_view_nocontent_smiling_face">{help_title}</p><p class="oe_view_nocontent_alias">{sub_title}</p>'
        )

    # ------------------------------------------------------------
    # BUSINESS
    # ------------------------------------------------------------

    def log_meeting(self, meeting):
        """ Log the meeting info with a link to it in the chatter
        :param record meeting: the meeting we want to log
        """
        if not meeting.duration:
            duration = _('unknown')
        else:
            duration = self.env['ir.qweb.field.duration'].value_to_html(meeting.duration, {'unit': 'hour'})
        meeting_usertime = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, meeting.start))
        meeting_time = Markup("<time datetime='%(meeting_start)s+00:00'>%(meeting_user_time)s</time>") % {
            'meeting_start': meeting.start,
            'meeting_user_time': meeting_usertime,
        }
        message = Markup("<p>%(meeting)s<br/>%(subject_string)s %(subject_link)s<br/>%(duration)s<p>") % {
            'meeting': _("Meeting scheduled at %s", meeting_time),
            'subject_string': _("Subject: "),
            'subject_link': meeting._get_html_link(),
            'duration': _("Duration: %s", duration),
        }
        return self.message_post(body=message)

    # ------------------------------------------------------------
    # MERGE AND CONVERT LEADS / OPPORTUNITIES
    # ------------------------------------------------------------

    def _merge_data(self, fnames=None):
        """ Prepare lead/opp data into a dictionary for merging. Different types
            of fields are processed in different ways:
                - text: all the values are concatenated
                - m2m and o2m: those fields aren't processed
                - m2o: the first not null value prevails (the other are dropped)
                - any other type of field: same as m2o

            :param fields: list of fields to process
            :return dict data: contains the merged values of the new opportunity
        """
        if fnames is None:
            fnames = self._merge_get_fields()
        fcallables = self._merge_get_fields_specific()
        address_values = self._merge_get_fields_address()

        # helpers
        def _get_first_not_null(attr, opportunities):
            value = False
            for opp in opportunities:
                if opp[attr]:
                    value = opp[attr].id if isinstance(opp[attr], models.BaseModel) else opp[attr]
                    break
            return value

        # process the field's values
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
            elif not fcallable and field.type in ('many2many', 'one2many'):
                continue
            else:
                data[field_name] = _get_first_not_null(field_name, self)  # take the first not null

        return data

    def merge_opportunity(self, user_id=False, team_id=False, auto_unlink=True):
        """ Merge opportunities in one. Different cases of merge:
                - merge leads together = 1 new lead
                - merge at least 1 opp with anything else (lead or opp) = 1 new opp
            The resulting lead/opportunity will be the most important one (based on its confidence level)
            updated with values from other opportunities to merge.

        :param user_id : the id of the saleperson. If not given, will be determined by `_merge_data`.
        :param team : the id of the Sales Team. If not given, will be determined by `_merge_data`.

        :return crm.lead record resulting of th merge
        """
        return self._merge_opportunity(user_id=user_id, team_id=team_id, auto_unlink=auto_unlink)

    def _merge_opportunity(self, user_id=False, team_id=False, auto_unlink=True, max_length=5):
        """ Private merging method. This one allows to relax rules on record set
        length allowing to merge more than 5 opportunities at once if requested.
        This should not be called by action buttons.

        See ``merge_opportunity`` for more details. """
        if len(self.ids) <= 1:
            raise UserError(_('Select at least two Leads/Opportunities from the list to merge them.'))

        if max_length and len(self.ids) > max_length and not self.env.is_superuser():
            raise UserError(_("To prevent data loss, Leads and Opportunities can only be merged by groups of %(max_length)s.", max_length=max_length))

        opportunities = self._sort_by_confidence_level(reverse=True)

        # get SORTED recordset of head and tail, and complete list
        opportunities_head = opportunities[0]
        opportunities_tail = opportunities[1:]

        # merge all the sorted opportunity. This means the value of
        # the first (head opp) will be a priority.
        merged_data = opportunities._merge_data(self._merge_get_fields())

        # force value for saleperson and Sales Team
        if user_id:
            merged_data['user_id'] = user_id
        if team_id:
            merged_data['team_id'] = team_id

        merged_followers = opportunities_head._merge_followers(opportunities_tail)

        # log merge message
        opportunities_head._merge_log_summary(merged_followers, opportunities_tail)
        # merge other data (mail.message, attachments, ...) from tail into head
        opportunities_head._merge_dependences(opportunities_tail)

        # check if the stage is in the stages of the Sales Team. If not, assign the stage with the lowest sequence
        if merged_data.get('team_id'):
            team_stage_ids = self.env['crm.stage'].search(['|', ('team_id', '=', merged_data['team_id']), ('team_id', '=', False)], order='sequence, id')
            if merged_data.get('stage_id') not in team_stage_ids.ids:
                merged_data['stage_id'] = team_stage_ids[0].id if team_stage_ids else False

        # write merged data into first opportunity; remove some keys if already
        # set on opp to avoid useless recomputes
        if 'user_id' in merged_data and opportunities_head.user_id.id == merged_data['user_id']:
            merged_data.pop('user_id')
        if 'team_id' in merged_data and opportunities_head.team_id.id == merged_data['team_id']:
            merged_data.pop('team_id')
        opportunities_head.write(merged_data)

        # delete tail opportunities
        # we use the SUPERUSER to avoid access rights issues because as the user had the rights to see the records it should be safe to do so
        if auto_unlink:
            opportunities_tail.sudo().unlink()

        return opportunities_head

    def _merge_get_fields_address(self):
        """The address fields are propagated as a whole.

        The address is taken from the lead with the most non-empty address field
        (sorted by highest rank if multiple lead have the same amount of non-empty
        fields).
        """
        source_lead = max(self, key=lambda lead: len(list(
            lead[field] for field in PARTNER_ADDRESS_FIELDS_TO_SYNC
            if lead[field]
        )))
        return {fname: source_lead[fname] for fname in PARTNER_ADDRESS_FIELDS_TO_SYNC}

    def _merge_get_fields_specific(self):
        return {
            'description': lambda fname, leads: '<br/><br/>'.join(desc for desc in leads.mapped('description') if not is_html_empty(desc)),
            'type': lambda fname, leads: 'opportunity' if any(lead.type == 'opportunity' for lead in leads) else 'lead',
            'priority': lambda fname, leads: max(leads.mapped('priority')) if leads else False,
            'tag_ids': lambda fname, leads: leads.mapped('tag_ids'),
            'lost_reason_id': lambda fname, leads:
                False if leads and leads[0].probability
                else next((lead.lost_reason_id for lead in leads if lead.lost_reason_id), False),
        }

    def _merge_get_fields(self):
        return (
            CRM_LEAD_FIELDS_TO_MERGE
            + list(self._merge_get_fields_specific().keys())
            + PARTNER_ADDRESS_FIELDS_TO_SYNC
        )

    def _merge_dependences(self, opportunities):
        """ Merge dependences (messages, attachments,activities, calendar events,
        ...). These dependences will be transfered to `self` considered as the
        master lead.

        :param opportunities : recordset of opportunities to transfer. Does not
          include `self` which is the target crm.lead being the result of the
          merge;
        """
        self.ensure_one()
        self._merge_dependences_history(opportunities)
        self._merge_dependences_attachments(opportunities)
        self._merge_dependences_calendar_events(opportunities)

    def _merge_dependences_history(self, opportunities):
        """ Move history from the given opportunities to the current one. `self`
        is the crm.lead record destination for message of `opportunities`.

        This method moves
          * messages
          * activities

        :param opportunities: see ``_merge_dependences``
        """
        self.ensure_one()
        # sudo usage: because we want to go through all messages, whatever the real ACLs
        # current user has on them
        for opportunity_su in opportunities.sudo():
            for message_su in opportunity_su.message_ids:
                if message_su.subject:
                    subject = _("From %(source_name)s: %(source_subject)s", source_name=opportunity_su.name, source_subject=message_su.subject)
                else:
                    subject = _("From %(source_name)s", source_name=opportunity_su.name)
                message_su.write({
                    'res_id': self.id,
                    'subject': subject,
                })
        opportunities.activity_ids.write({
            'res_id': self.id,
        })

        return True

    def _merge_dependences_attachments(self, opportunities):
        """ Move attachments of given opportunities to the current one `self`, and rename
            the attachments having same name than native ones.

        :param opportunities: see ``_merge_dependences``
        """
        self.ensure_one()

        all_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', opportunities.ids)
        ])

        for opportunity in opportunities:
            attachments = all_attachments.filtered(lambda attach: attach.res_id == opportunity.id)
            for attachment in attachments:
                attachment.write({
                    'res_id': self.id,
                    'name': _("%(attach_name)s (from %(lead_name)s)",
                              attach_name=attachment.name,
                              lead_name=opportunity.name[:20]
                             )
                })
        return True

    def _merge_dependences_calendar_events(self, opportunities):
        """ Move calender.event from the given opportunities to the current one. `self` is the
            crm.lead record destination for event of `opportunities`.
        :param opportunities: see ``merge_dependences``
        """
        self.ensure_one()
        meetings = self.env['calendar.event'].search([('opportunity_id', 'in', opportunities.ids)])
        return meetings.write({
            'res_id': self.id,
            'opportunity_id': self.id,
        })

    def _merge_followers(self, opportunities):
        """Add the followers into the destination lead if they post a message in the last 30 days.

        :param opportunities : Record<crm.lead> of opportunities to transfer
        :return: {old_lead_id: Record<mail.followers>} Followers which have been added in
            the destination lead grouped by source lead ID.
        """
        self.ensure_one()

        self.env['mail.message'].flush_model()
        self.env['mail.followers'].flush_model()

        # Get the active followers (followers whose partner post a message on the
        # leads in the last 30 days) which should be moved on the destination lead
        self.env.cr.execute(
            '''
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
               AND mf.res_id IN %(lead_ids)s
               AND destf IS NULL
          GROUP BY mf.partner_id
            ''',
            {'lead_ids': tuple(opportunities.ids), 'lead_id': self.id},
        )
        followers_to_update = [r[0] for r in self.env.cr.fetchall()]
        followers_to_update = self.env['mail.followers'].browse(followers_to_update).sudo()
        followers_by_old_lead = dict(groupby(followers_to_update, lambda f: f.res_id))
        followers_to_update.write({'res_id': self.id})
        return followers_by_old_lead

    def _merge_log_summary(self, merged_followers, opportunities_tail):
        """Log the merge message on the lead."""
        self.ensure_one()
        self.message_post_with_source(
            "crm.crm_lead_merge_summary",
            render_values={
                "merged_followers": merged_followers,
                "opportunities": opportunities_tail,
                "is_html_empty": is_html_empty,
            },
            subtype_xmlid='mail.mt_note',
        )

    def _format_properties(self):
        """Format the properties to build the merge message.

        Return a list of dict containing the label, and a value key if there's only
        one value, or a "values" key if we have multiple values (e.g. many2many, tags).

        E.G.
            [{
                'label': 'My Partner',
                'value': 'Alice',
            }, {
                'label': 'My Partners',
                'values': [
                    {'name': 'Alice'},
                    {'name': 'Bob'},
                ],
            }, {
                'label': 'My Tags',
                'values': [
                    {'name': 'A', 'color': 1},
                    {'name': 'C', 'color': 3},
                ],
            }]
        """
        self.ensure_one()
        # read to have the display names already in the value
        properties = self.read(['lead_properties'])[0]['lead_properties']

        formatted = []
        for definition in properties:
            label = definition.get('string')
            value = definition.get('value')
            property_type = definition['type']
            if not value and property_type != 'boolean':
                continue

            property_dict = {'label': label}
            if property_type == 'boolean':
                property_dict['value'] = _('Yes') if value else _('No')
            elif value and property_type == 'many2one':
                property_dict['value'] = value[1]
            elif value and property_type == 'many2many':
                # show many2many in badge
                property_dict['values'] = [{'name': rec[1]} for rec in value]
            elif value and property_type in ['selection', 'tags']:
                # retrieve the option label from the value
                options = {
                    option[0]: option[1:]
                    for option in (definition.get(property_type) or [])
                }
                if property_type == 'selection':
                    value = options.get(value)
                    property_dict['value'] = value[0] if value else None
                else:
                    property_dict['values'] = [{
                        'name': options[tag][0],
                        'color': options[tag][1],
                        } for tag in value if tag in options
                    ]
            else:
                property_dict['value'] = value

            formatted.append(property_dict)

        return formatted

    # CONVERT
    # ----------------------------------------------------------------------

    def _convert_opportunity_data(self, customer, team_id=False):
        """ Extract the data from a lead to create the opportunity
            :param customer : res.partner record
            :param team_id : identifier of the Sales Team to determine the stage
        """
        new_team_id = team_id if team_id else self.team_id.id
        upd_values = {
            'type': 'opportunity',
            'date_conversion': self.env.cr.now(),
        }
        if customer != self.partner_id:
            upd_values['partner_id'] = customer.id if customer else False
        if not self.stage_id:
            stage = self._stage_find(team_id=new_team_id)
            upd_values['stage_id'] = stage.id
        return upd_values

    def convert_opportunity(self, partner, user_ids=False, team_id=False):
        customer = partner if partner else self.env['res.partner']
        for lead in self:
            if not lead.active or lead.probability == 100:
                continue
            vals = lead._convert_opportunity_data(customer, team_id)
            lead.write(vals)

        if user_ids or team_id:
            self._handle_salesmen_assignment(user_ids=user_ids, team_id=team_id)

        return True

    def _handle_partner_assignment(self, force_partner_id=False, create_missing=True):
        """ Update customer (partner_id) of leads. Purpose is to set the same
        partner on most leads; either through a newly created partner either
        through a given partner_id.

        :param int force_partner_id: if set, update all leads to that customer;
        :param create_missing: for leads without customer, create a new one
          based on lead information;
        """
        for lead in self:
            if force_partner_id:
                lead.partner_id = force_partner_id
            if not lead.partner_id and create_missing:
                partner = lead._create_customer()
                lead.partner_id = partner.id

    def _handle_salesmen_assignment(self, user_ids=False, team_id=False):
        """ Assign salesmen and salesteam to a batch of leads.  If there are more
        leads than salesmen, these salesmen will be assigned in round-robin. E.g.
        4 salesmen (S1, S2, S3, S4) for 6 leads (L1, L2, ... L6) will assigned as
        following: L1 - S1, L2 - S2, L3 - S3, L4 - S4, L5 - S1, L6 - S2.

        :param list user_ids: salesmen to assign
        :param int team_id: salesteam to assign
        """
        update_vals = {'team_id': team_id} if team_id else {}
        if not user_ids and team_id:
            self.write(update_vals)
        else:
            lead_ids = self.ids
            steps = len(user_ids)
            # pass 1 : lead_ids[0:6:3] = [L1,L4]
            # pass 2 : lead_ids[1:6:3] = [L2,L5]
            # pass 3 : lead_ids[2:6:3] = [L3,L6]
            # ...
            for idx in range(0, steps):
                subset_ids = lead_ids[idx:len(lead_ids):steps]
                update_vals['user_id'] = user_ids[idx]
                self.env['crm.lead'].browse(subset_ids).write(update_vals)

    # ------------------------------------------------------------
    # MERGE / CONVERT TOOLS
    # ---------------------------------------------------------

    # CLASSIFICATION TOOLS
    # --------------------------------------------------

    def _get_lead_duplicates(self, partner=None, email=None, include_lost=False):
        """ Search for leads that seem duplicated based on partner / email.

        :param partner : optional customer when searching duplicated
        :param email: email (possibly formatted) to search
        :param boolean include_lost: if True, search includes archived opportunities
          (still only active leads are considered). If False, search for active
          and not won leads and opportunities;
        """
        if not email and not partner:
            return self.env['crm.lead']

        domain = []
        normalized_emails = email_normalize_all(email)
        if normalized_emails:
            domain.append(('email_normalized', 'in', normalized_emails))
        if partner:
            domain.append(('partner_id', '=', partner.id))

        if not domain:
            return self.env['crm.lead']

        domain = ['|'] * (len(domain) - 1) + domain
        if include_lost:
            domain += ['|', ('type', '=', 'opportunity'), ('active', '=', True)]
        else:
            domain += ['&', ('active', '=', True), '|', ('stage_id', '=', False), ('stage_id.is_won', '=', False)]

        return self.with_context(active_test=False).search(domain)

    def _sort_by_confidence_level(self, reverse=False):
        """ Sorting the leads/opps according to the confidence level to it
        being won. It is sorted following this incremental heuristics :

          * "not lost" first (inactive leads are lost); normally all leads
            should be active but in case lost one, they are always last.
            Inactive opportunities are considered as valid;
          * opportunity is more reliable than a lead which is a pre-stage
            used mainly for first classification;
          * stage sequence: the higher the better as it indicates we are moving
            towards won stage;
          * probability: the higher the better as it is more likely to be won;
          * ID: the higher the better when all other parameters are equal. We
            consider newer leads to be more reliable;
        """
        def opps_key(opportunity):
            return opportunity.type == 'opportunity' or opportunity.active,  \
                opportunity.type == 'opportunity', \
                opportunity.stage_id.sequence, \
                opportunity.probability, \
                -opportunity._origin.id

        return self.sorted(key=opps_key, reverse=reverse)

    # CUSTOMER TOOLS
    # --------------------------------------------------

    def _find_matching_partner(self, email_only=False):
        """ Try to find a matching partner with available information on the
        lead, using notably customer's name, email, ...

        :param email_only: Only find a matching based on the email. To use
            for automatic process where ilike based on name can be too dangerous
        :return: partner browse record
        """
        self.ensure_one()
        partner = self.partner_id

        if not partner and self.email_from:
            partner = self.env['res.partner'].search([('email', '=', self.email_from)], limit=1)

        if not partner and not email_only:
            # search through the existing partners based on the lead's partner or contact name
            # to be aligned with _create_customer, search on lead's name as last possibility
            for customer_potential_name in [self[field_name] for field_name in ['partner_name', 'contact_name', 'name'] if self[field_name]]:
                partner = self.env['res.partner'].search([('name', 'ilike', customer_potential_name)], limit=1)
                if partner:
                    break

        return partner

    def _create_customer(self):
        """ Create a partner from lead data and link it to the lead.

        :return: newly-created partner browse record
        """
        Partner = self.env['res.partner']
        contact_name = self.contact_name
        if not contact_name:
            contact_name = parse_contact_from_email(self.email_from)[0] if self.email_from else False

        if self.partner_name:
            partner_company = Partner.create(self._prepare_customer_values(self.partner_name, is_company=True))
        elif self.partner_id:
            partner_company = self.partner_id
        else:
            partner_company = None

        if contact_name:
            return Partner.create(self._prepare_customer_values(contact_name, is_company=False, parent_id=partner_company.id if partner_company else False))

        if partner_company:
            return partner_company
        return Partner.create(self._prepare_customer_values(self.name, is_company=False))

    def _get_customer_information(self):
        email_keys_to_values = super()._get_customer_information()

        for lead in self:
            email_key = lead.email_normalized or lead.email_from
            # do not fill Falsy with random data, unless monorecord (= always correct)
            if not email_key and len(self) > 1:
                continue
            values = email_keys_to_values.setdefault(email_key, {})
            contact_name = lead.contact_name or parse_contact_from_email(lead.email_from)[0] or lead.partner_name or lead.email_from
            is_company = bool(lead.partner_name) and contact_name == lead.partner_name
            # Note that we don't attempt to create the parent company even if partner name is set
            values.update({
                key: val for key, val in lead._prepare_customer_values(
                    contact_name, is_company=is_company, parent_id=False
                ).items() if val and key != 'email'  # don't force email used as criterion
            })
            values['is_company'] = is_company
        return email_keys_to_values

    def _prepare_customer_values(self, partner_name, is_company=False, parent_id=False):
        """ Extract data from lead to create a partner.

        :param partner_name : future name of the partner
        :param is_company : True if the partner is a company
        :param parent_id : id of the parent partner (False if no parent)

        :return: dictionary of values to give at res_partner.create()
        """
        email_parts = tools.email_split(self.email_from)
        res = {
            'name': partner_name,
            'user_id': self.env.context.get('default_user_id') or self.user_id.id,
            'comment': self.description,
            'phone': self.phone,
            'mobile': self.mobile,
            'email': email_parts[0] if email_parts else False,
            'function': self.function,
            # address
            'street': self.street,
            'street2': self.street2,
            'zip': self.zip,
            'city': self.city,
            'country_id': self.country_id.id,
            'state_id': self.state_id.id,
            'website': self.website,
            # company / hierarchy
            'parent_id': parent_id,
            'is_company': is_company,
            'company_name': not is_company and not parent_id and self.partner_name,
            'type': 'contact'
        }
        if self.lang_id.active:
            res['lang'] = self.lang_id.code
        return res

    # ------------------------------------------------------------
    # MAILING
    # ------------------------------------------------------------

    def _creation_subtype(self):
        return self.env.ref('crm.mt_lead_create')

    def _creation_message(self):
        self.ensure_one()
        if self.team_id:
            return _('A new lead has been created for the team "%(team_name)s".', team_name=self.team_id.display_name)
        return _('A new lead has been created and is not assigned to any team.')

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage_id' in init_values and self.probability == 100 and self.stage_id:
            return self.env.ref('crm.mt_lead_won')
        elif 'lost_reason_id' in init_values and self.lost_reason_id:
            return self.env.ref('crm.mt_lead_lost')
        elif 'stage_id' in init_values:
            return self.env.ref('crm.mt_lead_stage')
        elif 'active' in init_values and self.active:
            return self.env.ref('crm.mt_lead_restored')
        elif 'active' in init_values and not self.active:
            return self.env.ref('crm.mt_lead_lost')
        return super()._track_subtype(init_values)

    def _notify_by_email_prepare_rendering_context(self, message, msg_vals=False, model_description=False,
                                                   force_email_company=False, force_email_lang=False):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message, msg_vals=msg_vals, model_description=model_description,
            force_email_company=force_email_company, force_email_lang=force_email_lang
        )
        if self.date_deadline:
            render_context['subtitles'].append(
                _('Deadline: %s', self.date_deadline.strftime(get_lang(self.env).date_format)))
        return render_context

    def _notify_get_reply_to(self, default=None):
        # Override to set alias of lead and opportunities to their sales team if any
        aliases = self.mapped('team_id').sudo()._notify_get_reply_to(default=default)
        res = {lead.id: aliases.get(lead.team_id.id) for lead in self}
        leftover = self.filtered(lambda rec: not rec.team_id)
        if leftover:
            res.update(super(CrmLead, leftover)._notify_get_reply_to(default=default))
        return res

    def _message_get_default_recipients(self):
        return {
            r.id: {
                'partner_ids': [],
                'email_to': ','.join(tools.email_normalize_all(r.email_from)) or r.email_from,
                'email_cc': False,
            } for r in self
        }

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set an user as responsible. We prefer that
        # assignment is done automatically (scoring) or manually. Otherwise it
        # would always be root (gateway user). It also allows to exclude portal
        # and public users.
        self = self.with_context(default_user_id=False)

        if custom_values is None:
            custom_values = {}
        defaults = {
            'name':  msg_dict.get('subject') or _("No Subject"),
            'email_from': msg_dict.get('from'),
            'partner_id': msg_dict.get('author_id', False),
        }
        if msg_dict.get('priority') in dict(crm_stage.AVAILABLE_PRIORITIES):
            defaults['priority'] = msg_dict.get('priority')
        defaults.update(custom_values)

        return super().message_new(msg_dict, custom_values=defaults)

    def _message_post_after_hook(self, message, msg_vals):
        if self.email_from and not self.partner_id:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            new_partner = message.partner_ids.filtered(
                lambda partner: partner.email == self.email_from or (self.email_normalized and partner.email_normalized == self.email_normalized)
            )
            if new_partner:
                if new_partner[0].email_normalized:
                    email_domain = ('email_normalized', '=', new_partner[0].email_normalized)
                else:
                    email_domain = ('email_from', '=', new_partner[0].email)
                self.search([
                    ('partner_id', '=', False), email_domain, ('stage_id.fold', '=', False)
                ]).write({'partner_id': new_partner[0].id})
        return super()._message_post_after_hook(message, msg_vals)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Leads & Opportunities'),
            'template': '/crm/static/xls/crm_lead.xls'
        }]

    # ------------------------------------------------------------
    # PLS
    # ------------------------------------------------------------
    # Predictive lead scoring is computing the lead probability, based on won and lost leads from the past
    # Each won/lost lead increments a frequency table, where we store, for each field/value couple, the number of
    # won and lost leads.
    #   E.g. : A won lead from Belgium will increase the won count of the frequency country_id='Belgium' by 1.
    # The frequencies are split by team_id, so each team has its own frequencies environment. (Team A doesn't impact B)
    # There are two main ways to build the frequency table:
    #   - Live Increment: At each Won/lost, we increment directly the frequencies based on the lead values.
    #       Done right BEFORE writing the lead as won or lost.
    #       We consider a lead that will be marked as won or lost.
    #       Used each time a lead is won or lost, to ensure frequency table is always up to date
    #   - One shot Rebuild: empty the frequency table and rebuild it from scratch, based on every already won/lost leads
    #       Done during cron process.
    #       We consider all the leads that have been already won or lost.
    #       Used in one shot, when modifying the criteria to take into account (fields or reference date)

    # ---------------------------------
    # PLS: Probability Computation
    # ---------------------------------
    def _pls_get_naive_bayes_probabilities(self, batch_mode=False):
        """
        In machine learning, naive Bayes classifiers (NBC) are a family of simple "probabilistic classifiers" based on
        applying Bayes theorem with strong (naive) independence assumptions between the variables taken into account.
        E.g: will TDE eat m&m's depending on his sleep status, the amount of work he has and the fullness of his stomach?
        As we use experience to compute the statistics, every day, we will register the variables state + the result.
        As the days pass, we will be able to determine, with more and more precision, if TDE will eat m&m's
        for a specific combination :
            - did sleep very well, a lot of work and stomach full > Will never happen !
            - didn't sleep at all, no work at all and empty stomach > for sure !
        Following Bayes' Theorem: the probability that an event occurs (to win) under certain conditions is proportional
        to the probability to win under each condition separately and the probability to win. We compute a 'Win score'
        -> P(Won | A∩B) ∝ P(A∩B | Won)*P(Won) OR S(Won | A∩B) = P(A∩B | Won)*P(Won)
        To compute a percentage of probability to win, we also compute the 'Lost score' that is proportional to the
        probability to lose under each condition separately and the probability to lose.
        -> Probability =  S(Won | A∩B) / ( S(Won | A∩B) + S(Lost | A∩B) )
        See https://www.youtube.com/watch?v=CPqOCI0ahss can help to get a quick and simple example.
        One issue about NBC is when a event occurence is never observed.
        E.g: if when TDE has an empty stomach, he always eat m&m's, than the "not eating m&m's when empty stomach' event
        will never be observed.
        This is called 'zero frequency' and that leads to division (or at least multiplication) by zero.
        To avoid this, we add 0.1 in each frequency. With few data, the computation is than not really realistic.
        The more we have records to analyse, the more the estimation will be precise.
        :return: probability in percent (and integer rounded) that the lead will be won at the current stage.
        """
        lead_probabilities = {}
        if not self:
            return lead_probabilities

        # Get all leads values, no matter the team_id
        domain = []
        if batch_mode:
            domain = [
                '&',
                    ('active', '=', True), ('id', 'in', self.ids),
                    '|',
                        ('probability', '=', None),
                        '&',
                            ('probability', '<', 100), ('probability', '>', 0)
            ]
        leads_values_dict = self._pls_get_lead_pls_values(domain=domain)

        if not leads_values_dict:
            return lead_probabilities

        # Get unique couples to search in frequency table and won leads.
        leads_fields = set()  # keep unique fields, as a lead can have multiple tag_ids
        won_leads = set()
        won_stage_ids = self.env['crm.stage'].search([('is_won', '=', True)]).ids
        for lead_id, values in leads_values_dict.items():
            for field, value in values['values']:
                if field == 'stage_id' and value in won_stage_ids:
                    won_leads.add(lead_id)
                leads_fields.add(field)
        leads_fields = sorted(leads_fields)
        # get all variable related records from frequency table, no matter the team_id
        frequencies = self.env['crm.lead.scoring.frequency'].search([('variable', 'in', list(leads_fields))], order="team_id asc, id")

        # get all team_ids from frequencies
        frequency_teams = frequencies.mapped('team_id')
        frequency_team_ids = [team.id for team in frequency_teams]

        # 1. Compute each variable value count individually
        # regroup each variable to be able to compute their own probabilities
        # As all the variable does not enter into account (as we reject unset values in the process)
        # each value probability must be computed only with their own variable related total count
        # special case: for lead for which team_id is not in frequency table or lead with no team_id,
        # we consider all the records, independently from team_id (this is why we add a result[-1])
        result = dict((team_id, dict((field, dict(won_total=0, lost_total=0)) for field in leads_fields)) for team_id in frequency_team_ids)
        result[-1] = dict((field, dict(won_total=0, lost_total=0)) for field in leads_fields)
        for frequency in frequencies:
            field = frequency['variable']
            value = frequency['value']

            # To avoid that a tag take too much importance if its subset is too small,
            # we ignore the tag frequencies if we have less than 50 won or lost for this tag.
            if field == 'tag_id' and (frequency['won_count'] + frequency['lost_count']) < 50:
                continue

            if frequency.team_id:
                team_result = result[frequency.team_id.id]
                team_result[field][value] = {'won': frequency['won_count'], 'lost': frequency['lost_count']}
                team_result[field]['won_total'] += frequency['won_count']
                team_result[field]['lost_total'] += frequency['lost_count']

            if value not in result[-1][field]:
                result[-1][field][value] = {'won': 0, 'lost': 0}
            result[-1][field][value]['won'] += frequency['won_count']
            result[-1][field][value]['lost'] += frequency['lost_count']
            result[-1][field]['won_total'] += frequency['won_count']
            result[-1][field]['lost_total'] += frequency['lost_count']

        # Get all won, lost and total count for all records in frequencies per team_id
        for team_id in result:
            result[team_id]['team_won'], \
            result[team_id]['team_lost'], \
            result[team_id]['team_total'] = self._pls_get_won_lost_total_count(result[team_id])

        save_team_id = None
        p_won, p_lost = 1, 1
        for lead_id, lead_values in leads_values_dict.items():
            # if stage_id is null, return 0 and bypass computation
            lead_fields = [value[0] for value in lead_values.get('values', [])]
            if not 'stage_id' in lead_fields:
                lead_probabilities[lead_id] = 0
                continue
            # if lead stage is won, return 100
            elif lead_id in won_leads:
                lead_probabilities[lead_id] = 100
                continue

            # team_id not in frequency Table -> convert to -1
            lead_team_id = lead_values['team_id'] if lead_values['team_id'] in result else -1
            if lead_team_id != save_team_id:
                save_team_id = lead_team_id
                team_won = result[save_team_id]['team_won']
                team_lost = result[save_team_id]['team_lost']
                team_total = result[save_team_id]['team_total']
                # if one count = 0, we cannot compute lead probability
                if not team_won or not team_lost:
                    continue
                p_won = team_won / team_total
                p_lost = team_lost / team_total

            # 2. Compute won and lost score using each variable's individual probability
            s_lead_won, s_lead_lost = p_won, p_lost
            for field, value in lead_values['values']:
                field_result = result.get(save_team_id, {}).get(field)
                value = value.origin if hasattr(value, 'origin') else value
                value_result = field_result.get(str(value)) if field_result else False
                if value_result:
                    total_won = team_won if field == 'stage_id' else field_result['won_total']
                    total_lost = team_lost if field == 'stage_id' else field_result['lost_total']

                    # if one count = 0, we cannot compute lead probability
                    if not total_won or not total_lost:
                        continue
                    s_lead_won *= value_result['won'] / total_won
                    s_lead_lost *= value_result['lost'] / total_lost

            # 3. Compute Probability to win
            probability = s_lead_won / (s_lead_won + s_lead_lost)
            lead_probabilities[lead_id] = min(max(round(100 * probability, 2), 0.01), 99.99)
        return lead_probabilities

    # ---------------------------------
    # PLS: Live Increment
    # ---------------------------------
    def _pls_increment_frequencies(self, from_state=None, to_state=None):
        """
        When losing or winning a lead, this method is called to increment each PLS parameter related to the lead
        in won_count (if won) or in lost_count (if lost).

        This method is also used when reactivating a mistakenly lost lead (using the decrement argument).
        In this case, the lost count should be de-increment by 1 for each PLS parameter linked to the lead.

        Live increment must be done before writing the new values because we need to know the state change (from and to).
        This would not be an issue for the reach won or reach lost as we just need to increment the frequencies with the
        final state of the lead.
        This issue is when the lead leaves a closed state because once the new values have been writen, we do not know
        what was the previous state that we need to decrement.
        This is why 'is_won' and 'decrement' parameters are used to describe the from / to change of its state.
        """
        new_frequencies_by_team, existing_frequencies_by_team = self._pls_prepare_update_frequency_table(target_state=from_state or to_state)

        # update frequency table
        self._pls_update_frequency_table(new_frequencies_by_team, 1 if to_state else -1,
                                         existing_frequencies_by_team=existing_frequencies_by_team)

    # ---------------------------------
    # PLS: One shot rebuild
    # ---------------------------------
    def _cron_update_automated_probabilities(self):
        """ This cron will :
          - rebuild the lead scoring frequency table
          - recompute all the automated_probability and align probability if both were aligned
        """
        cron_start_date = datetime.now()
        self._rebuild_pls_frequency_table()
        self._update_automated_probabilities()
        _logger.info("Predictive Lead Scoring : Cron duration = %d seconds" % ((datetime.now() - cron_start_date).total_seconds()))

    def _rebuild_pls_frequency_table(self):
        # Clear the frequencies table (in sql to speed up the cron)
        try:
            self.browse().check_access('unlink')
        except AccessError:
            raise UserError(_("You don't have the access needed to run this cron."))
        else:
            self._cr.execute('TRUNCATE TABLE crm_lead_scoring_frequency')

        new_frequencies_by_team, unused = self._pls_prepare_update_frequency_table(rebuild=True)
        # update frequency table
        self._pls_update_frequency_table(new_frequencies_by_team, 1)

        _logger.info("Predictive Lead Scoring : crm.lead.scoring.frequency table rebuilt")

    def _update_automated_probabilities(self):
        """ Recompute all the automated_probability (and align probability if both were aligned) for all the leads
        that are active (not won, nor lost).

        For performance matter, as there can be a huge amount of leads to recompute, this cron proceed by batch.
        Each batch is performed into its own transaction, in order to minimise the lock time on the lead table
        (and to avoid complete lock if there was only 1 transaction that would last for too long -> several minutes).
        If a concurrent update occurs, it will simply be put in the queue to get the lock.
        """
        pls_start_date = self._pls_get_safe_start_date()
        if not pls_start_date:
            return

        # 1. Get all the leads to recompute created after pls_start_date that are nor won nor lost
        # (Won : probability = 100 | Lost : probability = 0 or inactive. Here, inactive won't be returned anyway)
        # Get also all the lead without probability --> These are the new leads. Activate auto probability on them.
        pending_lead_domain = [
            '&',
                '&',
                    ('stage_id', '!=', False), ('create_date', '>=', pls_start_date),
                '|',
                    ('probability', '=', False),
                    '&',
                        ('probability', '<', 100), ('probability', '>', 0)
        ]
        leads_to_update = self.env['crm.lead'].search(pending_lead_domain)
        leads_to_update_count = len(leads_to_update)

        # 2. Compute by batch to avoid memory error
        lead_probabilities = {}
        for i in range(0, leads_to_update_count, PLS_COMPUTE_BATCH_STEP):
            leads_to_update_part = leads_to_update[i:i + PLS_COMPUTE_BATCH_STEP]
            lead_probabilities.update(leads_to_update_part._pls_get_naive_bayes_probabilities(batch_mode=True))
        _logger.info("Predictive Lead Scoring : New automated probabilities computed")

        # 3. Group by new probability to reduce server roundtrips when executing the update
        probability_leads = defaultdict(list)
        for lead_id, probability in sorted(lead_probabilities.items()):
            probability_leads[probability].append(lead_id)

        # 4. Update automated_probability (+ probability if both were equal)
        update_sql = """UPDATE crm_lead
                        SET automated_probability = %s,
                            probability = CASE WHEN (probability = automated_probability OR probability is null)
                                               THEN (%s)
                                               ELSE (probability)
                                          END
                        WHERE id in %s"""

        # Update by a maximum number of leads at the same time, one batch by transaction :
        # - avoid memory errors
        # - avoid blocking the table for too long with a too big transaction
        transactions_count, transactions_failed_count = 0, 0
        cron_update_lead_start_date = datetime.now()
        auto_commit = not getattr(threading.current_thread(), 'testing', False)
        self.flush_model()
        for probability, probability_lead_ids in probability_leads.items():
            for lead_ids_current in tools.split_every(PLS_UPDATE_BATCH_STEP, probability_lead_ids):
                transactions_count += 1
                try:
                    self.env.cr.execute(update_sql, (probability, probability, tuple(lead_ids_current)))
                    # auto-commit except in testing mode
                    if auto_commit:
                        self.env.cr.commit()
                except Exception as e:
                    _logger.warning("Predictive Lead Scoring : update transaction failed. Error: %s" % e)
                    transactions_failed_count += 1
        self.invalidate_model()

        _logger.info(
            "Predictive Lead Scoring : All automated probabilities updated (%d leads / %d transactions (%d failed) / %d seconds)" % (
                leads_to_update_count,
                transactions_count,
                transactions_failed_count,
                (datetime.now() - cron_update_lead_start_date).total_seconds(),
            )
        )

    # ---------------------------------
    # PLS: Common parts for both mode
    # ---------------------------------
    def _pls_prepare_update_frequency_table(self, rebuild=False, target_state=False):
        """
        This method is common to Live Increment or Full Rebuild mode, as it shares the main steps.
        This method will prepare the frequency dict needed to update the frequency table:
            - New frequencies: frequencies that we need to add in the frequency table.
            - Existing frequencies: frequencies that are already in the frequency table.
        In rebuild mode, only the new frequencies are needed as existing frequencies are truncated.
        For each team, each dict contains the frequency in won and lost for each field/value couple
        of the target leads.
        Target leads are :
            - in Live increment mode : given ongoing leads (self)
            - in Full rebuild mode : all the closed (won and lost) leads in the DB.
        During the frequencies update, with both new and existing frequencies, we can split frequencies to update
        and frequencies to add. If a field/value couple already exists in the frequency table, we just update it.
        Otherwise, we need to insert a new one.
        """
        # Keep eligible leads
        pls_start_date = self._pls_get_safe_start_date()
        if not pls_start_date:
            return {}, {}

        if rebuild:  # rebuild will treat every closed lead in DB, increment will treat current ongoing leads
            pls_leads = self
        else:
            # Only treat leads created after the PLS start Date
            pls_leads = self.filtered(
                lambda lead: fields.Date.to_date(pls_start_date) <= fields.Date.to_date(lead.create_date))
            if not pls_leads:
                return {}, {}

        # Extract target leads values
        if rebuild:  # rebuild is ok
            domain = [
                '&',
                    ('create_date', '>=', pls_start_date),
                    '|',
                        ('probability', '=', 100),
                        '&',
                            ('probability', '=', 0), ('active', '=', False)
              ]
            team_ids = self.env['crm.team'].with_context(active_test=False).search([]).ids + [0]  # If team_id is unset, consider it as team 0
        else:  # increment
            domain = [('id', 'in', pls_leads.ids)]
            team_ids = pls_leads.mapped('team_id').ids + [0]

        leads_values_dict = pls_leads._pls_get_lead_pls_values(domain=domain)

        # split leads values by team_id
        # get current frequencies related to the target leads
        leads_frequency_values_by_team = dict((team_id, []) for team_id in team_ids)
        leads_pls_fields = set()  # ensure to keep each field unique (can have multiple tag_id leads_values_dict)
        for values in leads_values_dict.values():
            team_id = values.get('team_id', 0)  # If team_id is unset, consider it as team 0
            lead_frequency_values = {'count': 1}
            for field, value in values['values']:
                if field != "probability":  # was added to lead values in batch mode to know won/lost state, but is not a pls fields.
                    leads_pls_fields.add(field)
                else:  # extract lead probability - needed to increment tag_id frequency. (proba always before tag_id)
                    lead_probability = value
                if field == 'tag_id':  # handle tag_id separatelly (as in One Shot rebuild mode)
                    leads_frequency_values_by_team[team_id].append({field: value, 'count': 1, 'probability': lead_probability})
                else:
                    lead_frequency_values[field] = value
            leads_frequency_values_by_team[team_id].append(lead_frequency_values)
        leads_pls_fields = sorted(leads_pls_fields)

        # get new frequencies
        new_frequencies_by_team = {}
        for team_id in team_ids:
            # prepare fields and tag values for leads by team
            new_frequencies_by_team[team_id] = self._pls_prepare_frequencies(
                leads_frequency_values_by_team[team_id], leads_pls_fields, target_state=target_state)

        # get existing frequencies
        existing_frequencies_by_team = {}
        if not rebuild:  # there is no existing frequency in rebuild mode as they were all deleted.
            # read all fields to get everything in memory in one query (instead of having query + prefetch)
            existing_frequencies = self.env['crm.lead.scoring.frequency'].search_read(
                ['&', ('variable', 'in', leads_pls_fields),
                      '|', ('team_id', 'in', pls_leads.mapped('team_id').ids), ('team_id', '=', False)])
            for frequency in existing_frequencies:
                team_id = frequency['team_id'][0] if frequency.get('team_id') else 0
                if team_id not in existing_frequencies_by_team:
                    existing_frequencies_by_team[team_id] = dict((field, {}) for field in leads_pls_fields)

                existing_frequencies_by_team[team_id][frequency['variable']][frequency['value']] = {
                    'frequency_id': frequency['id'],
                    'won': frequency['won_count'],
                    'lost': frequency['lost_count']
                }

        return new_frequencies_by_team, existing_frequencies_by_team

    def _pls_update_frequency_table(self, new_frequencies_by_team, step, existing_frequencies_by_team=None):
        """ Create / update the frequency table in a cross company way, per team_id"""
        values_to_update = {}
        values_to_create = []
        if not existing_frequencies_by_team:
            existing_frequencies_by_team = {}
        # build the create multi + frequencies to update
        for team_id, new_frequencies in new_frequencies_by_team.items():
            for field, value in new_frequencies.items():
                # frequency already present ?
                current_frequencies = existing_frequencies_by_team.get(team_id, {})
                for param, result in value.items():
                    current_frequency_for_couple = current_frequencies.get(field, {}).get(param, {})
                    # If frequency already present : UPDATE IT
                    if current_frequency_for_couple:
                        new_won = current_frequency_for_couple['won'] + (result['won'] * step)
                        new_lost = current_frequency_for_couple['lost'] + (result['lost'] * step)
                        # ensure to have always positive frequencies
                        values_to_update[current_frequency_for_couple['frequency_id']] = {
                            'won_count': new_won if new_won > 0 else 0.1,
                            'lost_count': new_lost if new_lost > 0 else 0.1
                        }
                        continue

                    # Else, CREATE a new frequency record.
                    # We add + 0.1 in won and lost counts to avoid zero frequency issues
                    # should be +1 but it weights too much on small recordset.
                    values_to_create.append({
                        'variable': field,
                        'value': param,
                        'won_count': result['won'] + 0.1,
                        'lost_count': result['lost'] + 0.1,
                        'team_id': team_id if team_id else None  # team_id = 0 means no team_id
                    })

        LeadScoringFrequency = self.env['crm.lead.scoring.frequency'].sudo()
        for frequency_id, values in values_to_update.items():
            LeadScoringFrequency.browse(frequency_id).write(values)

        if values_to_create:
            LeadScoringFrequency.create(values_to_create)

    # ---------------------------------
    # Utility Tools for PLS
    # ---------------------------------

    # PLS:  Config Parameters
    # ---------------------
    def _pls_get_safe_start_date(self):
        """ As config_parameters does not accept Date field,
            we get directly the date formated string stored into the Char config field,
            as we directly use this string in the sql queries.
            To avoid sql injections when using this config param,
            we ensure the date string can be effectively a date."""
        str_date = self.env['ir.config_parameter'].sudo().get_param('crm.pls_start_date')
        if not fields.Date.to_date(str_date):
            return False
        return str_date

    def _pls_get_safe_fields(self):
        """ As config_parameters does not accept M2M field,
            we the fields from the formated string stored into the Char config field.
            To avoid sql injections when using that list, we return only the fields
            that are defined on the model. """
        pls_fields_config = self.env['ir.config_parameter'].sudo().get_param('crm.pls_fields')
        pls_fields = pls_fields_config.split(',') if pls_fields_config else []
        pls_safe_fields = [field for field in pls_fields if field in self._fields.keys()]
        return pls_safe_fields

    # Compute Automated Probability Tools
    # -----------------------------------
    def _pls_get_won_lost_total_count(self, team_results):
        """ Get all won and all lost + total :
               first stage can be used to know how many lost and won there is
               as won count are equals for all stage
               and first stage is always incremented in lost_count
        :param frequencies: lead_scoring_frequencies
        :return: won count, lost count and total count for all records in frequencies
        """
        # TODO : check if we need to handle specific team_id stages [for lost count] (if first stage in sequence is team_specific)
        first_stage_id = self.env['crm.stage'].search([('team_id', '=', False)], order='sequence, id', limit=1)
        if str(first_stage_id.id) not in team_results.get('stage_id', []):
            return 0, 0, 0
        stage_result = team_results['stage_id'][str(first_stage_id.id)]
        return stage_result['won'], stage_result['lost'], stage_result['won'] + stage_result['lost']

    # PLS: Rebuild Frequency Table Tools
    # ----------------------------------
    def _pls_prepare_frequencies(self, lead_values, leads_pls_fields, target_state=None):
        """new state is used when getting frequencies for leads that are changing to lost or won.
        Stays none if we are checking frequencies for leads already won or lost."""
        pls_fields = leads_pls_fields.copy()
        frequencies = dict((field, {}) for field in pls_fields)

        stage_ids = self.env['crm.stage'].search_read([], ['sequence', 'name', 'id'], order='sequence, id')
        stage_sequences = {stage['id']: stage['sequence'] for stage in stage_ids}

        # Increment won / lost frequencies by criteria (field / value couple)
        for values in lead_values:
            if target_state:  # ignore probability values if target state (as probability is the old value)
                won_count = values['count'] if target_state == 'won' else 0
                lost_count = values['count'] if target_state == 'lost' else 0
            else:
                won_count = values['count'] if values.get('probability', 0) == 100 else 0
                lost_count = values['count'] if values.get('probability', 1) == 0  else 0

            if 'tag_id' in values:
                frequencies = self._pls_increment_frequency_dict(frequencies, 'tag_id', values['tag_id'], won_count, lost_count)
                continue

            # Else, treat other fields
            if 'tag_id' in pls_fields:  # tag_id already treated here above.
                pls_fields.remove('tag_id')
            for field in pls_fields:
                if field not in values:
                    continue
                value = values[field]
                if value or field in ('email_state', 'phone_state'):
                    if field == 'stage_id':
                        if won_count:  # increment all stages if won
                            stages_to_increment = [stage['id'] for stage in stage_ids]
                        else:  # increment only current + previous stages if lost
                            current_stage_sequence = stage_sequences[value]
                            stages_to_increment = [stage['id'] for stage in stage_ids if stage['sequence'] <= current_stage_sequence]
                        for stage_id in stages_to_increment:
                            frequencies = self._pls_increment_frequency_dict(frequencies, field, stage_id, won_count, lost_count)
                    else:
                        frequencies = self._pls_increment_frequency_dict(frequencies, field, value, won_count, lost_count)

        return frequencies

    def _pls_increment_frequency_dict(self, frequencies, field, value, won, lost):
        value = str(value)  # Ensure we will always compare strings.
        if value not in frequencies[field]:
            frequencies[field][value] = {'won': won, 'lost': lost}
        else:
            frequencies[field][value]['won'] += won
            frequencies[field][value]['lost'] += lost
        return frequencies

    # Common PLS Tools
    # ----------------
    def _pls_get_lead_pls_values(self, domain=[]):
        """
        This methods builds a dict where, for each lead in self or matching the given domain,
        we will get a list of field/value couple.
        Due to onchange and create, we don't always have the id of the lead to recompute.
        When we update few records (one, typically) with onchanges, we build the lead_values (= couple field/value)
        using the ORM.
        To speed up the computation and avoid making too much DB read inside loops,
        we can give a domain to make sql queries to bypass the ORM.
        This domain will be used in sql queries to get the values for every lead matching the domain.
        :param domain: If set, we get all the leads values via unique sql queries (one for tags, one for other fields),
                            using the given domain on leads.
                       If not set, get lead values lead by lead using the ORM.
        :return: {lead_id: [(field1: value1), (field2: value2), ...], ...}
        """
        leads_values_dict = OrderedDict()
        pls_fields = ["stage_id", "team_id"] + self._pls_get_safe_fields()

        # Check if tag_ids is in the pls_fields and removed it from the list. The tags will be managed separately.
        use_tags = 'tag_ids' in pls_fields
        if use_tags:
            pls_fields.remove('tag_ids')

        if domain:
            # Get leads values
            self.flush_model()
            # active_test = False as domain should take active into 'active' field it self
            query = self.env['crm.lead'].with_context(active_test=False)._where_calc(domain)
            table = query.table
            query.order = SQL("%(table)s.team_id asc, %(table)s.id desc", table=SQL.identifier(table))
            sql_fields = [SQL.identifier(field) for field in pls_fields]
            self._cr.execute(query.select(
                SQL("id"),
                SQL("probability"),
                *sql_fields,
            ))
            lead_results = self._cr.dictfetchall()

            if use_tags:
                # Get tags values
                tag_rel_alias = query.left_join(table, 'id', 'crm_tag_rel', 'lead_id', 'crm_tag_rel')
                tag_alias = query.left_join(tag_rel_alias, 'tag_id', 'crm_tag', 'id', 'crm_tag')
                self._cr.execute(query.select(
                    SQL("%s AS lead_id", SQL.identifier(table, "id")),
                    SQL("%s AS tag_id", SQL.identifier(tag_alias, "id")),
                ))
                tag_results = self._cr.dictfetchall()
            else:
                tag_results = []

            # get all (variable, value) couple for all in self
            for lead in lead_results:
                lead_values = []
                for field in pls_fields + ['probability']:  # add probability as used in _pls_prepare_frequencies (needed in rebuild mode)
                    value = lead[field]
                    if field == 'team_id':  # ignore team_id as stored separately in leads_values_dict[lead_id][team_id]
                        continue
                    if value or field == 'probability':  # 0 is a correct value for probability
                        lead_values.append((field, value))
                    elif field in ('email_state', 'phone_state'):  # As ORM reads 'None' as 'False', do the same here
                        lead_values.append((field, False))
                    leads_values_dict[lead['id']] = {'values': lead_values, 'team_id': lead['team_id'] or 0}

            for tag in tag_results:
                if tag['tag_id']:
                    leads_values_dict[tag['lead_id']]['values'].append(('tag_id', tag['tag_id']))
            return leads_values_dict
        else:
            for lead in self:
                lead_values = []
                for field in pls_fields:
                    if field == 'team_id':  # ignore team_id as stored separately in leads_values_dict[lead_id][team_id]
                        continue
                    value = lead[field].id if isinstance(lead[field], models.BaseModel) else lead[field]
                    if value or field in ('email_state', 'phone_state'):
                        lead_values.append((field, value))
                if use_tags:
                    for tag in lead.tag_ids:
                        lead_values.append(('tag_id', tag.id))
                leads_values_dict[lead.id] = {'values': lead_values, 'team_id': lead['team_id'].id}
            return leads_values_dict
