# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import threading
from psycopg2 import sql
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, SUPERUSER_ID
from odoo.tools.translate import _
from odoo.tools import email_re, email_split
from odoo.exceptions import UserError, AccessError
from odoo.addons.phone_validation.tools import phone_validation
from collections import OrderedDict, defaultdict

from . import crm_stage

_logger = logging.getLogger(__name__)

CRM_LEAD_FIELDS_TO_MERGE = [
    'name',
    'partner_id',
    'campaign_id',
    'company_id',
    'country_id',
    'team_id',
    'state_id',
    'stage_id',
    'medium_id',
    'source_id',
    'user_id',
    'title',
    'city',
    'contact_name',
    'description',
    'mobile',
    'partner_name',
    'phone',
    'probability',
    'planned_revenue',
    'street',
    'street2',
    'zip',
    'create_date',
    'date_action_last',
    'email_from',
    'email_cc',
    'website',
    'partner_name']

# Those values have been determined based on benchmark to minimise
# computation time, number of transaction and transaction time.
PLS_COMPUTE_BATCH_STEP = 50000  # odoo.models.PREFETCH_MAX = 1000 but larger cluster can speed up global computation
PLS_UPDATE_BATCH_STEP = 5000


class Lead(models.Model):
    _name = "crm.lead"
    _description = "Lead/Opportunity"
    _order = "priority desc, id desc"
    _inherit = ['mail.thread.cc', 'mail.thread.blacklist', 'mail.activity.mixin',
                'utm.mixin', 'format.address.mixin', 'phone.validation.mixin']
    _primary_email = 'email_from'

    def _auto_init(self):
        res = super(Lead, self)._auto_init()
        tools.create_index(self._cr, 'crm_lead_create_date_team_id_idx',
                           self._table, ['create_date', 'team_id'])
        return res

    def _default_team_id(self, user_id):
        domain = [('use_leads', '=', True)] if self._context.get('default_type') == "lead" or self.type == 'lead' else [('use_opportunities', '=', True)]
        return self.env['crm.team']._get_default_team_id(user_id=user_id, domain=domain)

    def _default_stage_id(self):
        team = self._default_team_id(user_id=self.env.uid)
        return self._stage_find(team_id=team.id, domain=[('fold', '=', False)]).id

    name = fields.Char('Opportunity', required=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=10, index=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="Linked partner (optional). Usually created when converting the lead. You can find a partner by its Name, TIN, Email or Internal Reference.")
    active = fields.Boolean('Active', default=True, tracking=True)
    date_action_last = fields.Datetime('Last Action', readonly=True)
    email_from = fields.Char('Email', help="Email address of the contact", tracking=40, index=True)
    website = fields.Char('Website', index=True, help="Website of the contact")
    team_id = fields.Many2one('crm.team', string='Sales Team', default=lambda self: self._default_team_id(self.env.uid),
        index=True, tracking=True, help='When sending mails, the default email address is taken from the Sales Team.')
    kanban_state = fields.Selection([('grey', 'No next activity planned'), ('red', 'Next activity late'), ('green', 'Next activity is planned')],
        string='Kanban State', compute='_compute_kanban_state')
    description = fields.Text('Notes')
    tag_ids = fields.Many2many('crm.lead.tag', 'crm_lead_tag_rel', 'lead_id', 'tag_id', string='Tags', help="Classify and analyze your lead/opportunity categories like: Training, Service")
    contact_name = fields.Char('Contact Name', tracking=30)
    partner_name = fields.Char("Company Name", tracking=20, index=True, help='The name of the future partner company that will be created while converting the lead into opportunity')
    type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity')], index=True, required=True, tracking=15,
        default=lambda self: 'lead' if self.env['res.users'].has_group('crm.group_use_lead') else 'opportunity',
        help="Type is used to separate Leads and Opportunities")
    priority = fields.Selection(crm_stage.AVAILABLE_PRIORITIES, string='Priority', index=True, default=crm_stage.AVAILABLE_PRIORITIES[0][0])
    date_closed = fields.Datetime('Closed Date', readonly=True, copy=False)

    stage_id = fields.Many2one('crm.stage', string='Stage', ondelete='restrict', tracking=True, index=True, copy=False,
        domain="['|', ('team_id', '=', False), ('team_id', '=', team_id)]",
        group_expand='_read_group_stage_ids', default=lambda self: self._default_stage_id())
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, tracking=True, default=lambda self: self.env.user)
    referred = fields.Char('Referred By')

    date_open = fields.Datetime('Assignation Date', readonly=True, default=fields.Datetime.now)
    day_open = fields.Float(compute='_compute_day_open', string='Days to Assign', store=True)
    day_close = fields.Float(compute='_compute_day_close', string='Days to Close', store=True)
    date_last_stage_update = fields.Datetime(string='Last Stage Update', index=True, default=fields.Datetime.now)
    date_conversion = fields.Datetime('Conversion Date', readonly=True)

    # Probability - Only used for type opportunity
    probability = fields.Float('Probability', group_operator="avg", copy=False)
    automated_probability = fields.Float('Automated Probability', readonly=True)
    is_automated_probability = fields.Boolean('Is automated probability?', compute="_compute_is_automated_probability")
    phone_state = fields.Selection([
        ('correct', 'Correct'),
        ('incorrect', 'Incorrect')], string='Phone Quality', compute="_compute_phone_state", store=True)
    email_state = fields.Selection([
        ('correct', 'Correct'),
        ('incorrect', 'Incorrect')], string='Email Quality', compute="_compute_email_state", store=True)

    # Only used for type opportunity
    planned_revenue = fields.Monetary('Expected Revenue', currency_field='company_currency', tracking=True)
    expected_revenue = fields.Monetary('Prorated Revenue', currency_field='company_currency', store=True, compute="_compute_expected_revenue")
    date_deadline = fields.Date('Expected Closing', help="Estimate of the date on which the opportunity will be won.")
    color = fields.Integer('Color Index', default=0)
    partner_address_name = fields.Char('Partner Contact Name', related='partner_id.name', readonly=True)
    partner_address_email = fields.Char('Partner Contact Email', related='partner_id.email', readonly=True)
    partner_address_phone = fields.Char('Partner Contact Phone', related='partner_id.phone', readonly=True)
    partner_is_blacklisted = fields.Boolean('Partner is blacklisted', related='partner_id.is_blacklisted', readonly=True)
    company_currency = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True, relation="res.currency")
    user_email = fields.Char('User Email', related='user_id.email', readonly=True)
    user_login = fields.Char('User Login', related='user_id.login', readonly=True)

    # Fields for address, due to separation from crm and res.partner
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    zip = fields.Char('Zip', change_default=True)
    city = fields.Char('City')
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')
    lang_id = fields.Many2one('res.lang', string='Language', help="Language of the lead.")
    phone = fields.Char('Phone', tracking=50)
    mobile = fields.Char('Mobile')
    function = fields.Char('Job Position')
    title = fields.Many2one('res.partner.title')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)
    meeting_count = fields.Integer('# Meetings', compute='_compute_meeting_count')
    lost_reason = fields.Many2one('crm.lost.reason', string='Lost Reason', index=True, tracking=True)

    _sql_constraints = [
        ('check_probability', 'check(probability >= 0 and probability <= 100)', 'The probability of closing the deal should be between 0% and 100%!')
    ]

    def _auto_init(self):
        res = super(Lead, self)._auto_init()
        tools.create_index(self._cr, 'crm_lead_user_id_team_id_type_index',
                           self._table, ['user_id', 'team_id', 'type'])
        return res

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
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
        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    def _compute_kanban_state(self):
        today = date.today()
        for lead in self:
            kanban_state = 'grey'
            if lead.activity_date_deadline:
                lead_date = fields.Date.from_string(lead.activity_date_deadline)
                if lead_date >= today:
                    kanban_state = 'green'
                else:
                    kanban_state = 'red'
            lead.kanban_state = kanban_state

    @api.depends('planned_revenue', 'probability')
    def _compute_expected_revenue(self):
        for lead in self:
            lead.expected_revenue = round((lead.planned_revenue or 0.0) * (lead.probability or 0) / 100.0, 2)

    @api.depends('date_open')
    def _compute_day_open(self):
        """ Compute difference between create date and open date """
        leads = self.filtered(lambda l: l.date_open and l.create_date)
        others = self - leads
        others.day_open = None
        for lead in leads:
            date_create = fields.Datetime.from_string(lead.create_date).replace(microsecond=0)
            date_open = fields.Datetime.from_string(lead.date_open)
            lead.day_open = abs((date_open - date_create).days)

    @api.depends('date_closed')
    def _compute_day_close(self):
        """ Compute difference between current date and log date """
        leads = self.filtered(lambda l: l.date_closed and l.create_date)
        others = self - leads
        others.day_close = None
        for lead in leads:
            date_create = fields.Datetime.from_string(lead.create_date)
            date_close = fields.Datetime.from_string(lead.date_closed)
            lead.day_close = abs((date_close - date_create).days)

    @api.depends('probability', 'automated_probability')
    def _compute_is_automated_probability(self):
        """ If probability and automated_probability are equal, the probability is considered as automatic.
         when the probability is in automatic mode, the field probability will be aligned
         when automated_probability is modified. """
        for lead in self:
            lead.is_automated_probability = tools.float_compare(lead.probability, lead.automated_probability, 2) == 0

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
                for email in email_split(lead.email_from):
                    if tools.email_normalize(email):
                        email_state = 'correct'
                        break
            lead.email_state = email_state

    def _compute_meeting_count(self):
        meeting_data = self.env['calendar.event'].read_group([('opportunity_id', 'in', self.ids)], ['opportunity_id'], ['opportunity_id'])
        mapped_data = {m['opportunity_id'][0]: m['opportunity_id_count'] for m in meeting_data}
        for lead in self:
            lead.meeting_count = mapped_data.get(lead.id, 0)

    def _onchange_partner_id_values(self, partner_id):
        """ returns the new values when partner_id has changed """
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)

            partner_name = partner.parent_id.name
            if not partner_name and partner.is_company:
                partner_name = partner.name

            return {
                'partner_name': partner_name,
                'contact_name': partner.name if not partner.is_company else False,
                'title': partner.title.id,
                'street': partner.street,
                'street2': partner.street2,
                'city': partner.city,
                'state_id': partner.state_id.id,
                'country_id': partner.country_id.id,
                'email_from': partner.email,
                'phone': partner.phone,
                'mobile': partner.mobile,
                'zip': partner.zip,
                'function': partner.function,
                'website': partner.website,
            }
        return {}

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        values = self._onchange_partner_id_values(self.partner_id.id if self.partner_id else False)
        self.update(values)

    @api.model
    def _onchange_user_values(self, user_id):
        """ returns new values when user_id has changed """
        if not user_id:
            return {}
        if user_id and self._context.get('team_id'):
            team = self.env['crm.team'].browse(self._context['team_id'])
            if user_id in team.member_ids.ids or user_id == team.user_id.id:
                return {}
        team_id = self._default_team_id(user_id)
        return {'team_id': team_id}

    @api.onchange('user_id')
    def _onchange_user_id(self):
        """ When changing the user, also set a team_id or restrict team id to the ones user_id is member of. """
        if self.user_id.sale_team_id:
            values = self._onchange_user_values(self.user_id.id)
            self.update(values)

    def _onchange_compute_probability(self, optional_field_name=None):
        """Recompute probability on onchange methods of :
            'stage_id', 'team_id', 'tag_ids'
            'country_id', 'state_id', 'phone_state', 'email_state', 'source_id' """
        if optional_field_name and optional_field_name not in self._pls_get_safe_fields():
            return
        lead_probabilities = self._pls_get_naive_bayes_probabilities()
        self.automated_probability = lead_probabilities.get(self.id, 0)
        if self._origin.is_automated_probability:
            self.probability = self.automated_probability

    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        self._onchange_compute_probability()

    @api.onchange('source_id')
    def _onchange_source_id(self):
        self._onchange_compute_probability(optional_field_name='source_id')

    @api.onchange('automated_probability')
    def _onchange_automated_probability(self):
        """ If was in auto mode before the change, align both fields so that it will stay in auto mode. """
        if self._origin.is_automated_probability:
            self.probability = self.automated_probability

    @api.onchange('team_id')
    def _onchange_team_id(self):
        self._onchange_compute_probability()

    @api.onchange('tag_ids')
    def _onchange_tag_ids(self):
        self._onchange_compute_probability()

    @api.onchange('phone_state')
    def _onchange_phone_state(self):
        self._onchange_compute_probability(optional_field_name='phone_state')

    @api.onchange('email_state')
    def _onchange_email_state(self):
        self._onchange_compute_probability(optional_field_name='email_state')

    @api.constrains('user_id')
    def _valid_team(self):
        for lead in self:
            if lead.user_id:
                values = lead.with_context(team_id=lead.team_id.id)._onchange_user_values(lead.user_id.id)
                if values:
                    lead.update(values)

    @api.onchange('state_id')
    def _onchange_state(self):
        self._onchange_compute_probability(optional_field_name='state_id')
        if self.state_id:
            self.country_id = self.state_id.country_id.id

    @api.onchange('country_id')
    def _onchange_country_id(self):
        self._onchange_compute_probability(optional_field_name='country_id')
        res = {'domain': {'state_id': []}}
        if self.country_id:
            res['domain']['state_id'] = [('country_id', '=', self.country_id.id)]
        return res

    @api.onchange('lang_id')
    def _onchange_lang_id(self):
        self._onchange_compute_probability(optional_field_name='lang_id')

    # Phone Validation
    # ----------------
    @api.onchange('phone', 'country_id', 'company_id')
    def _onchange_phone_validation(self):
        if self.phone:
            self.phone = self.phone_format(self.phone)

    @api.onchange('mobile', 'country_id', 'company_id')
    def _onchange_mobile_validation(self):
        if self.mobile:
            self.mobile = self.phone_format(self.mobile)

    # ----------------------------------------
    # ORM override (CRUD, fields_view_get, ...)
    # ----------------------------------------

    @api.model
    def create(self, vals):
        if vals.get('website'):
            vals['website'] = self.env['res.partner']._clean_website(vals['website'])
        # set up context used to find the lead's sales channel which is needed
        # to correctly set the default stage_id
        context = dict(self._context or {})
        if vals.get('type') and not self._context.get('default_type'):
            context['default_type'] = vals.get('type')
        if vals.get('team_id') and not self._context.get('default_team_id'):
            context['default_team_id'] = vals.get('team_id')

        if vals.get('user_id') and 'date_open' not in vals:
            vals['date_open'] = fields.Datetime.now()

        partner_id = vals.get('partner_id') or context.get('default_partner_id')
        onchange_values = self._onchange_partner_id_values(partner_id)
        onchange_values.update(vals)  # we don't want to overwrite any existing key
        vals = onchange_values

        result = super(Lead, self.with_context(context)).create(vals)
        # Compute new probability for each lead separately
        result._update_probability()
        return result

    def write(self, vals):
        if vals.get('website'):
            vals['website'] = self.env['res.partner']._clean_website(vals['website'])
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.Datetime.now()
            stage_id = self.env['crm.stage'].browse(vals['stage_id'])
            if stage_id.is_won:
                vals.update({'probability': 100})
        # Only write the 'date_open' if no salesperson was assigned.
        if vals.get('user_id') and 'date_open' not in vals and not self.mapped('user_id'):
            vals['date_open'] = fields.Datetime.now()
        # stage change with new stage: update probability and date_closed
        if vals.get('probability', 0) >= 100 or not vals.get('active', True):
            vals['date_closed'] = fields.Datetime.now()
        elif 'probability' in vals:
            vals['date_closed'] = False
        if vals.get('user_id') and 'date_open' not in vals:
            vals['date_open'] = fields.Datetime.now()

        write_result = super(Lead, self).write(vals)
        # Compute new automated_probability (and, eventually, probability) for each lead separately
        if self._should_update_probability(vals):
            self._update_probability()

        return write_result

    def _update_probability(self):
        lead_probabilities = self.sudo()._pls_get_naive_bayes_probabilities()
        for lead in self:
            if lead.id in lead_probabilities:
                lead_proba = lead_probabilities[lead.id]
                proba_vals = {'automated_probability': lead_proba}
                if tools.float_compare(lead.probability, lead.automated_probability, 2) == 0:
                    proba_vals['probability'] = lead_proba
                super(Lead, lead).write(proba_vals)
        return

    def _should_update_probability(self, vals):
        fields_to_check = ['tag_ids', 'stage_id', 'team_id'] + self._pls_get_safe_fields()
        for field, value in vals.items():
            if field in fields_to_check:
                return True
        return False

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        # set default value in context, if not already set (Put stage to 'new' stage)
        context = dict(self._context)
        context.setdefault('default_type', self.type)
        context.setdefault('default_team_id', self.team_id.id)
        # Set date_open to today if it is an opp
        default = default or {}
        default['date_open'] = fields.Datetime.now() if self.type == 'opportunity' else False
        # Do not assign to an archived user
        if not self.user_id.active:
            default['user_id'] = False
        return super(Lead, self.with_context(context)).copy(default=default)

    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if self._context.get('opportunity_id'):
            opportunity = self.browse(self._context['opportunity_id'])
            action = opportunity.get_formview_action()
            if action.get('views') and any(view_id for view_id in action['views'] if view_id[1] == view_type):
                view_id = next(view_id[0] for view_id in action['views'] if view_id[1] == view_type)
        res = super(Lead, self)._fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            res['arch'] = self._fields_view_get_address(res['arch'])
        return res

    # ----------------------------------------
    # Actions Methods
    # ----------------------------------------

    def toggle_active(self):
        res = super(Lead, self).toggle_active()
        self.filtered(lambda lead: lead.active)._update_probability()
        return res

    def _rebuild_pls_frequency_table_threshold(self):
        """ Called by action_set_lost and action_set_won.
         Will run the cron to update the frequency table only if the number of lead is above
         a specified value (from config_parameter) for onboarding purpose.
         Once the threshold is reached, the config_param is set to 0 to avoid re-run the cron
         and, mainly, to avoid making useless search_count in the future."""
        pls_threshold = int(self.env['ir.config_parameter'].sudo().get_param('crm.pls_rebuild_threshold'))
        if pls_threshold:
            lead_count = self.env['crm.lead'].sudo().search_count([])
            if lead_count < pls_threshold:
                self.sudo()._cron_update_automated_probabilities()
            else:
                self.env['ir.config_parameter'].sudo().set_param('crm.pls_rebuild_threshold', 0)

    def action_set_lost(self, **additional_values):
        """ Lost semantic: probability = 0 or active = False """
        result = self.write({'active': False, 'probability': 0, 'automated_probability': 0, **additional_values})
        self._rebuild_pls_frequency_table_threshold()
        return result

    def action_set_won(self):
        """ Won semantic: probability = 100 (active untouched) """
        for lead in self:
            stage_id = lead._stage_find(domain=[('is_won', '=', True)])
            lead.write({'stage_id': stage_id.id, 'probability': 100})
        self._rebuild_pls_frequency_table_threshold()
        return True

    def action_set_automated_probability(self):
        self.write({'probability': self.automated_probability})

    def action_set_won_rainbowman(self):
        self.ensure_one()
        self.action_set_won()

        if self.user_id and self.team_id and self.planned_revenue:
            query = """
                SELECT
                    SUM(CASE WHEN user_id = %(user_id)s THEN 1 ELSE 0 END) as total_won,
                    MAX(CASE WHEN date_closed >= CURRENT_DATE - INTERVAL '30 days' AND user_id = %(user_id)s THEN planned_revenue ELSE 0 END) as max_user_30,
                    MAX(CASE WHEN date_closed >= CURRENT_DATE - INTERVAL '7 days' AND user_id = %(user_id)s THEN planned_revenue ELSE 0 END) as max_user_7,
                    MAX(CASE WHEN date_closed >= CURRENT_DATE - INTERVAL '30 days' AND team_id = %(team_id)s THEN planned_revenue ELSE 0 END) as max_team_30,
                    MAX(CASE WHEN date_closed >= CURRENT_DATE - INTERVAL '7 days' AND team_id = %(team_id)s THEN planned_revenue ELSE 0 END) as max_team_7
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
            elif query_result['max_team_30'] == self.planned_revenue:
                message = _('Boom! Team record for the past 30 days.')
            elif query_result['max_team_7'] == self.planned_revenue:
                message = _('Yeah! Deal of the last 7 days for the team.')
            elif query_result['max_user_30'] == self.planned_revenue:
                message = _('You just beat your personal record for the past 30 days.')
            elif query_result['max_user_7'] == self.planned_revenue:
                message = _('You just beat your personal record for the past 7 days.')

            if message:
                return {
                    'effect': {
                        'fadeout': 'slow',
                        'message': message,
                        'img_url': '/web/image/%s/%s/image_1024' % (self.team_id.user_id._name, self.team_id.user_id.id) if self.team_id.user_id.image_1024 else '/web/static/src/img/smile.svg',
                        'type': 'rainbow_man',
                    }
                }
        return True

    def action_schedule_meeting(self):
        """ Open meeting's calendar view to schedule meeting on current opportunity.
            :return dict: dictionary value for created Meeting view
        """
        self.ensure_one()
        action = self.env.ref('calendar.action_calendar_event').read()[0]
        partner_ids = self.env.user.partner_id.ids
        if self.partner_id:
            partner_ids.append(self.partner_id.id)
        action['context'] = {
            'default_opportunity_id': self.id if self.type == 'opportunity' else False,
            'default_partner_id': self.partner_id.id,
            'default_partner_ids': partner_ids,
            'default_team_id': self.team_id.id,
            'default_name': self.name,
        }
        return action

    # ----------------------------------------
    # Business Methods
    # ----------------------------------------

    def _stage_find(self, team_id=False, domain=None, order='sequence'):
        """ Determine the stage of the current lead with its teams, the given domain and the given team_id
            :param team_id
            :param domain : base search domain for stage
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
        return self.env['crm.stage'].search(search_domain, order=order, limit=1)

    def _merge_get_result_type(self):
        """ Define the type of the result of the merge.  If at least one of the
            element to merge is an opp, the resulting new element will be an opp.
            Otherwise it will be a lead.
            We'll directly use a list of browse records instead of a list of ids
            for performances' sake: it will spare a second browse of the
            leads/opps.

            :param list opps: list of browse records containing the leads/opps to process
            :return string type: the type of the final element
        """
        if any(record.type == 'opportunity' for record in self):
            return 'opportunity'
        return 'lead'

    def _merge_data(self, fields):
        """ Prepare lead/opp data into a dictionary for merging. Different types
            of fields are processed in different ways:
                - text: all the values are concatenated
                - m2m and o2m: those fields aren't processed
                - m2o: the first not null value prevails (the other are dropped)
                - any other type of field: same as m2o

            :param fields: list of fields to process
            :return dict data: contains the merged values of the new opportunity
        """
        # helpers
        def _get_first_not_null(attr, opportunities):
            for opp in opportunities:
                val = opp[attr]
                if val:
                    return val
            return False

        def _get_first_not_null_id(attr, opportunities):
            res = _get_first_not_null(attr, opportunities)
            return res.id if res else False

        # process the fields' values
        data = {}
        for field_name in fields:
            field = self._fields.get(field_name)
            if field is None:
                continue
            if field.type in ('many2many', 'one2many'):
                continue
            elif field.type == 'many2one':
                data[field_name] = _get_first_not_null_id(field_name, self)  # take the first not null
            elif field.type == 'text':
                data[field_name] = '\n\n'.join(it for it in self.mapped(field_name) if it)
            else:
                data[field_name] = _get_first_not_null(field_name, self)

        # define the resulting type ('lead' or 'opportunity')
        data['type'] = self._merge_get_result_type()
        return data

    def _mail_body(self, fields):
        """ generate the message body with the changed values
            :param fields : list of fields to track
            :returns a list of message bodies for the corresponding leads
        """
        bodies = []
        for lead in self:
            title = "%s : %s\n" % (_('Merged opportunity') if lead.type == 'opportunity' else _('Merged lead'), lead.name)
            body = [title]
            _fields = self.env['ir.model.fields'].search([
                    ('name', 'in', fields or []),
                    ('model_id.model', '=', lead._name),
                ])
            for field in _fields:
                value = getattr(lead, field.name, False)
                if field.ttype == 'selection':
                    selections = lead.fields_get()[field.name]['selection']
                    value = next((v[1] for v in selections if v[0] == value), value)
                elif field.ttype == 'many2one':
                    if value:
                        value = value.sudo().display_name
                elif field.ttype == 'many2many':
                    if value:
                        value = ','.join(
                            val.display_name
                            for val in value.sudo()
                        )
                body.append("%s: %s" % (field.field_description, value or ''))
            bodies.append("<br/>".join(body + ['<br/>']))
        return bodies

    def _merge_notify(self, opportunities):
        """ Create a message gathering merged leads/opps informations. Using message_post, send a
            message explaining which fields has been merged and their new value. `self` is the
            resulting merge crm.lead record.
            :param opportunities : recordset of merged crm.lead
            :returns mail.message posted on resulting crm.lead
        """
        # TODO JEM: mail template should be used instead of fix body, subject text
        self.ensure_one()
        # mail message's subject
        result_type = opportunities._merge_get_result_type()
        merge_message = _('Merged leads') if result_type == 'lead' else _('Merged opportunities')
        subject = merge_message + ": " + ", ".join(opportunities.mapped('name'))
        # message bodies
        message_bodies = opportunities._mail_body(list(CRM_LEAD_FIELDS_TO_MERGE))
        message_body = "\n\n".join(message_bodies)
        return self.message_post(body=message_body, subject=subject)

    def _merge_opportunity_history(self, opportunities):
        """ Move mail.message from the given opportunities to the current one. `self` is the
            crm.lead record destination for message of `opportunities`.
            :param opportunities : recordset of crm.lead to move the messages
        """
        self.ensure_one()
        for opportunity in opportunities:
            for message in opportunity.message_ids:
                message.write({
                    'res_id': self.id,
                    'subject': _("From %s : %s") % (opportunity.name, message.subject)
                })
        return True

    def _merge_opportunity_attachments(self, opportunities):
        """ Move attachments of given opportunities to the current one `self`, and rename
            the attachments having same name than native ones.
            :param opportunities : recordset of merged crm.lead
        """
        self.ensure_one()

        # return attachments of opportunity
        def _get_attachments(opportunity_id):
            return self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', opportunity_id)])

        first_attachments = _get_attachments(self.id)
        # counter of all attachments to move. Used to make sure the name is different for all attachments
        count = 1
        for opportunity in opportunities:
            attachments = _get_attachments(opportunity.id)
            for attachment in attachments:
                values = {'res_id': self.id}
                for attachment_in_first in first_attachments:
                    if attachment.name == attachment_in_first.name:
                        values['name'] = "%s (%s)" % (attachment.name, count)
                count += 1
                attachment.write(values)
        return True

    def merge_dependences(self, opportunities):
        """ Merge dependences (messages, attachments, ...). These dependences will be
            transfered to `self`, the most important lead.
            :param opportunities : recordset of opportunities to transfert. Does
                not include `self`.
        """
        self.ensure_one()
        self._merge_notify(opportunities)
        self._merge_opportunity_history(opportunities)
        self._merge_opportunity_attachments(opportunities)

    def merge_opportunity(self, user_id=False, team_id=False):
        """ Merge opportunities in one. Different cases of merge:
                - merge leads together = 1 new lead
                - merge at least 1 opp with anything else (lead or opp) = 1 new opp
            The resulting lead/opportunity will be the most important one (based on its confidence level)
            updated with values from other opportunities to merge.
            :param user_id : the id of the saleperson. If not given, will be determined by `_merge_data`.
            :param team : the id of the Sales Team. If not given, will be determined by `_merge_data`.
            :return crm.lead record resulting of th merge
        """
        if len(self.ids) <= 1:
            raise UserError(_('Please select more than one element (lead or opportunity) from the list view.'))

        if len(self.ids) > 5 and not self.env.is_superuser():
            raise UserError(_("To prevent data loss, Leads and Opportunities can only be merged by groups of 5."))

        opportunities = self._sort_by_confidence_level(reverse=True)

        # get SORTED recordset of head and tail, and complete list
        opportunities_head = opportunities[0]
        opportunities_tail = opportunities[1:]

        # merge all the sorted opportunity. This means the value of
        # the first (head opp) will be a priority.
        merged_data = opportunities._merge_data(list(CRM_LEAD_FIELDS_TO_MERGE))

        # force value for saleperson and Sales Team
        if user_id:
            merged_data['user_id'] = user_id
        if team_id:
            merged_data['team_id'] = team_id

        # merge other data (mail.message, attachments, ...) from tail into head
        opportunities_head.merge_dependences(opportunities_tail)

        # check if the stage is in the stages of the Sales Team. If not, assign the stage with the lowest sequence
        if merged_data.get('team_id'):
            team_stage_ids = self.env['crm.stage'].search(['|', ('team_id', '=', merged_data['team_id']), ('team_id', '=', False)], order='sequence')
            if merged_data.get('stage_id') not in team_stage_ids.ids:
                merged_data['stage_id'] = team_stage_ids[0].id if team_stage_ids else False

        # write merged data into first opportunity
        opportunities_head.write(merged_data)

        # delete tail opportunities
        # we use the SUPERUSER to avoid access rights issues because as the user had the rights to see the records it should be safe to do so
        opportunities_tail.sudo().unlink()

        return opportunities_head

    def _sort_by_confidence_level(self, reverse=False):
        """ Sorting the leads/opps according to the confidence level of its stage, which relates to the probability of winning it
        The confidence level increases with the stage sequence
        An Opportunity always has higher confidence level than a lead
        """
        def opps_key(opportunity):
            return opportunity.type == 'opportunity', opportunity.stage_id.sequence, -opportunity._origin.id

        return self.sorted(key=opps_key, reverse=reverse)

    def get_duplicated_leads(self, partner_id, include_lost=False):
        """ Search for opportunities that have the same partner and that arent done or cancelled
            :param partner_id : partner to search
        """
        self.ensure_one()
        email = self.partner_id.email or self.email_from
        return self._get_duplicated_leads_by_emails(partner_id, email, include_lost=include_lost)

    @api.model
    def _get_duplicated_leads_by_emails(self, partner_id, email, include_lost=False):
        """ Search for opportunities that have the same partner and that arent done or cancelled """
        if not email:
            return self.env['crm.lead']
        partner_match_domain = []
        for email in set(email_split(email) + [email]):
            partner_match_domain.append(('email_from', '=ilike', email))
        if partner_id:
            partner_match_domain.append(('partner_id', '=', partner_id))
        if not partner_match_domain:
            return self.env['crm.lead']

        partner_match_domain = ['|'] * (len(partner_match_domain) - 1) + partner_match_domain
        if not include_lost:
            partner_match_domain += ['&', ('active', '=', True), ('probability', '<', 100)]
        else:
            partner_match_domain += ['|', '&', ('type', '=', 'lead'), ('active', '=', True), ('type', '=', 'opportunity')]
        return self.search(partner_match_domain)

    def _convert_opportunity_data(self, customer, team_id=False):
        """ Extract the data from a lead to create the opportunity
            :param customer : res.partner record
            :param team_id : identifier of the Sales Team to determine the stage
        """
        if not team_id:
            team_id = self.team_id.id if self.team_id else False
        value = {
            'planned_revenue': self.planned_revenue,
            'probability': self.probability,
            'name': self.name,
            'partner_id': customer.id if customer else False,
            'type': 'opportunity',
            'date_open': fields.Datetime.now(),
            'email_from': customer and customer.email or self.email_from,
            'phone': customer and customer.phone or self.phone,
            'date_conversion': fields.Datetime.now(),
        }
        if not self.stage_id:
            stage = self._stage_find(team_id=team_id)
            value['stage_id'] = stage.id
        return value

    def convert_opportunity(self, partner_id, user_ids=False, team_id=False):
        customer = False
        if partner_id:
            customer = self.env['res.partner'].browse(partner_id)
        for lead in self:
            if not lead.active or lead.probability == 100:
                continue
            vals = lead._convert_opportunity_data(customer, team_id)
            lead.write(vals)

        if user_ids or team_id:
            self.allocate_salesman(user_ids, team_id)

        return True

    def _create_lead_partner_data(self, name, is_company, parent_id=False):
        """ extract data from lead to create a partner
            :param name : furtur name of the partner
            :param is_company : True if the partner is a company
            :param parent_id : id of the parent partner (False if no parent)
            :returns res.partner record
        """
        email_split = tools.email_split(self.email_from)
        res = {
            'name': name,
            'user_id': self.env.context.get('default_user_id') or self.user_id.id,
            'comment': self.description,
            'team_id': self.team_id.id,
            'parent_id': parent_id,
            'phone': self.phone,
            'mobile': self.mobile,
            'email': email_split[0] if email_split else False,
            'title': self.title.id,
            'function': self.function,
            'street': self.street,
            'street2': self.street2,
            'zip': self.zip,
            'city': self.city,
            'country_id': self.country_id.id,
            'state_id': self.state_id.id,
            'website': self.website,
            'is_company': is_company,
            'type': 'contact'
        }
        if self.lang_id:
            res['lang'] = self.lang_id.code
        return res

    def _create_lead_partner(self):
        """ Create a partner from lead data
            :returns res.partner record
        """
        Partner = self.env['res.partner']
        contact_name = self.contact_name
        if not contact_name:
            contact_name = Partner._parse_partner_name(self.email_from)[0] if self.email_from else False

        if self.partner_name:
            partner_company = Partner.create(self._create_lead_partner_data(self.partner_name, True))
        elif self.partner_id:
            partner_company = self.partner_id
        else:
            partner_company = None

        if contact_name:
            return Partner.create(self._create_lead_partner_data(contact_name, False, partner_company.id if partner_company else False))

        if partner_company:
            return partner_company
        return Partner.create(self._create_lead_partner_data(self.name, False))

    def handle_partner_assignation(self,  action='create', partner_id=False):
        """ Handle partner assignation during a lead conversion.
            if action is 'create', create new partner with contact and assign lead to new partner_id.
            otherwise assign lead to the specified partner_id

            :param list ids: leads/opportunities ids to process
            :param string action: what has to be done regarding partners (create it, assign an existing one, or nothing)
            :param int partner_id: partner to assign if any
            :return dict: dictionary organized as followed: {lead_id: partner_assigned_id}
        """
        partner_ids = {}
        for lead in self:
            if partner_id:
                lead.partner_id = partner_id
            if lead.partner_id:
                partner_ids[lead.id] = lead.partner_id.id
                continue
            if action == 'create':
                partner = lead._create_lead_partner()
                partner_id = partner.id
                partner.team_id = lead.team_id
            partner_ids[lead.id] = partner_id
        return partner_ids

    def allocate_salesman(self, user_ids=None, team_id=False):
        """ Assign salesmen and salesteam to a batch of leads.  If there are more
            leads than salesmen, these salesmen will be assigned in round-robin.
            E.g.: 4 salesmen (S1, S2, S3, S4) for 6 leads (L1, L2, ... L6).  They
            will be assigned as followed: L1 - S1, L2 - S2, L3 - S3, L4 - S4,
            L5 - S1, L6 - S2.

            :param list ids: leads/opportunities ids to process
            :param list user_ids: salesmen to assign
            :param int team_id: salesteam to assign
            :return bool
        """
        index = 0
        for lead in self:
            value = {}
            if team_id:
                value['team_id'] = team_id
            if user_ids:
                value['user_id'] = user_ids[index]
                # Cycle through user_ids
                index = (index + 1) % len(user_ids)
            if value:
                lead.write(value)
        return True

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
    def get_empty_list_help(self, help):
        help_title, sub_title = "", ""
        if self._context.get('default_type') == 'lead':
            help_title = _('Create a new lead')
        else:
            help_title = _('Create an opportunity in your pipeline')
        alias_record = self.env['mail.alias'].search([
            ('alias_name', '!=', False),
            ('alias_name', '!=', ''),
            ('alias_model_id.model', '=', 'crm.lead'),
            ('alias_parent_model_id.model', '=', 'crm.team'),
            ('alias_force_thread_id', '=', False)
        ], limit=1)
        if alias_record and alias_record.alias_domain and alias_record.alias_name:
            email = '%s@%s' % (alias_record.alias_name, alias_record.alias_domain)
            email_link = "<a href='mailto:%s'>%s</a>" % (email, email)
            sub_title = _('or send an email to %s') % (email_link)
        return '<p class="o_view_nocontent_smiling_face">%s</p><p class="oe_view_nocontent_alias">%s</p>' % (help_title, sub_title)

    def log_meeting(self, meeting_subject, meeting_date, duration):
        if not duration:
            duration = _('unknown')
        else:
            duration = str(duration)
        meet_date = fields.Datetime.from_string(meeting_date)
        meeting_usertime = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, meet_date))
        html_time = "<time datetime='%s+00:00'>%s</time>" % (meeting_date, meeting_usertime)
        message = _("Meeting scheduled at '%s'<br> Subject: %s <br> Duration: %s hours") % (html_time, meeting_subject, duration)
        return self.message_post(body=message)

    # ----------------------------------------
    # Sales Team Dashboard
    # ----------------------------------------

    @api.model
    def retrieve_sales_dashboard(self):
        """ Fetch data to setup Sales Dashboard """
        result = {
            'meeting': {
                'today': 0,
                'next_7_days': 0,
            },
            'activity': {
                'today': 0,
                'overdue': 0,
                'next_7_days': 0,
            },
            'closing': {
                'today': 0,
                'overdue': 0,
                'next_7_days': 0,
            },
            'done': {
                'this_month': 0,
                'last_month': 0,
            },
            'won': {
                'this_month': 0,
                'last_month': 0,
            },
            'nb_opportunities': 0,
        }

        today = fields.Date.from_string(fields.Date.context_today(self))

        opportunities = self.search([('type', '=', 'opportunity'), ('user_id', '=', self._uid)])

        for opp in opportunities:
            # Expected closing
            if opp.activity_date_deadline:
                if opp.date_deadline:
                    date_deadline = fields.Date.from_string(opp.date_deadline)
                    if date_deadline == today:
                        result['closing']['today'] += 1
                    if today <= date_deadline <= today + timedelta(days=7):
                        result['closing']['next_7_days'] += 1
                    if date_deadline < today and not opp.date_closed:
                        result['closing']['overdue'] += 1
                # Next activities
                for activity in opp.activity_ids:
                    date_deadline = fields.Date.from_string(activity.date_deadline)
                    if date_deadline == today:
                        result['activity']['today'] += 1
                    if today <= date_deadline <= today + timedelta(days=7):
                        result['activity']['next_7_days'] += 1
                    if date_deadline < today:
                        result['activity']['overdue'] += 1
            # Won in Opportunities
            if opp.date_closed and opp.stage_id.is_won:
                date_closed = fields.Date.from_string(opp.date_closed)
                if today.replace(day=1) <= date_closed <= today:
                    if opp.planned_revenue:
                        result['won']['this_month'] += opp.planned_revenue
                elif  today + relativedelta(months=-1, day=1) <= date_closed < today.replace(day=1):
                    if opp.planned_revenue:
                        result['won']['last_month'] += opp.planned_revenue

        result['nb_opportunities'] = len(opportunities)

        # crm.activity is a very messy model so we need to do that in order to retrieve the actions done.
        self._cr.execute("""
            SELECT
                mail_message.id,
                mail_message.subtype_id,
                mail_message.mail_activity_type_id,
                mail_message.date,
                crm_lead.user_id,
                crm_lead.type
            FROM mail_message
                LEFT JOIN crm_lead  ON (mail_message.res_id = crm_lead.id)
                INNER JOIN mail_activity_type activity_type ON (mail_message.mail_activity_type_id = activity_type.id)
            WHERE
                (mail_message.model = 'crm.lead') AND (crm_lead.user_id = %s) AND (crm_lead.type = 'opportunity')
        """, (self._uid,))
        activites_done = self._cr.dictfetchall()
        for activity in activites_done:
            if activity['date']:
                date_act = fields.Date.from_string(activity['date'])
                if today.replace(day=1) <= date_act <= today:
                    result['done']['this_month'] += 1
                elif today + relativedelta(months=-1, day=1) <= date_act < today.replace(day=1):
                    result['done']['last_month'] += 1

        # Meetings
        min_date = fields.Datetime.now()
        max_date = fields.Datetime.to_string(datetime.now() + timedelta(days=8))
        meetings_domain = [
            ('start', '>=', min_date),
            ('start', '<=', max_date),
            ('partner_ids', 'in', [self.env.user.partner_id.id])
        ]
        meetings = self.env['calendar.event'].search(meetings_domain)
        for meeting in meetings:
            if meeting['start']:
                start = meeting['start']
                if start == today:
                    result['meeting']['today'] += 1
                if today <= start <= today + timedelta(days=7):
                    result['meeting']['next_7_days'] += 1

        result['done']['target'] = self.env.user.target_sales_done
        result['won']['target'] = self.env.user.target_sales_won
        result['currency_id'] = self.env.company.currency_id.id

        return result

    @api.model
    def modify_target_sales_dashboard(self, target_name, target_value):
        """ Update the user objectives (`target_sales_done`, target_sales_won`
            and `target_sales_invoiced` fields).
            :param target_name : part of the fields name to update
            :param target_value : value of the field to update
        """
        if target_name in ['won', 'done', 'invoiced']:
            # bypass rights, since self.env.user is browsed as SUPERUSER_ID
            self.env.user.write({'target_sales_' + target_name: target_value})
        else:
            raise UserError(_('This target does not exist.'))

    # ----------------------------------------
    # Mail Gateway
    # ----------------------------------------
    def _creation_subtype(self):
        return self.env.ref('crm.mt_lead_create')

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage_id' in init_values and self.probability == 100 and self.stage_id:
            return self.env.ref('crm.mt_lead_won')
        elif 'lost_reason' in init_values:
            return self.env.ref('crm.mt_lead_lost')
        elif 'stage_id' in init_values:
            return self.env.ref('crm.mt_lead_stage')
        elif 'active' in init_values and self.active:
            return self.env.ref('crm.mt_lead_restored')
        return super(Lead, self)._track_subtype(init_values)

    def _notify_get_groups(self):
        """ Handle salesman recipients that can convert leads into opportunities
        and set opportunities as won / lost. """
        groups = super(Lead, self)._notify_get_groups()

        self.ensure_one()
        if self.type == 'lead':
            convert_action = self._notify_get_action_link('controller', controller='/lead/convert')
            salesman_actions = [{'url': convert_action, 'title': _('Convert to opportunity')}]
        else:
            won_action = self._notify_get_action_link('controller', controller='/lead/case_mark_won')
            lost_action = self._notify_get_action_link('controller', controller='/lead/case_mark_lost')
            salesman_actions = [
                {'url': won_action, 'title': _('Won')},
                {'url': lost_action, 'title': _('Lost')}]

        if self.team_id:
            salesman_actions.append({'url': self._notify_get_action_link('view', res_id=self.team_id.id, model=self.team_id._name), 'title': _('Sales Team Settings')})

        salesman_group_id = self.env.ref('sales_team.group_sale_salesman').id
        new_group = (
            'group_sale_salesman', lambda pdata: pdata['type'] == 'user' and salesman_group_id in pdata['groups'], {
                'actions': salesman_actions,
            })

        return [new_group] + groups

    def _notify_get_reply_to(self, default=None, records=None, company=None, doc_names=None):
        """ Override to set alias of lead and opportunities to their sales team if any. """
        aliases = self.mapped('team_id').sudo()._notify_get_reply_to(default=default, records=None, company=company, doc_names=None)
        res = {lead.id: aliases.get(lead.team_id.id) for lead in self}
        leftover = self.filtered(lambda rec: not rec.team_id)
        if leftover:
            res.update(super(Lead, leftover)._notify_get_reply_to(default=default, records=None, company=company, doc_names=doc_names))
        return res

    def _message_get_default_recipients(self):
        return {r.id: {
            'partner_ids': [],
            'email_to': r.email_normalized,
            'email_cc': False}
            for r in self}

    def _message_get_suggested_recipients(self):
        recipients = super(Lead, self)._message_get_suggested_recipients()
        try:
            for lead in self:
                if lead.partner_id:
                    lead._message_add_suggested_recipient(recipients, partner=lead.partner_id, reason=_('Customer'))
                elif lead.email_from:
                    lead._message_add_suggested_recipient(recipients, email=lead.email_from, reason=_('Customer Email'))
        except AccessError:  # no read access rights -> just ignore suggested recipients because this imply modifying followers
            pass
        return recipients

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """

        # remove external users
        if self.env.user.has_group('base.group_portal'):
            self = self.with_context(default_user_id=False)

        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        if self._uid == self.env.ref('base.user_root').id:
            self = self.with_context(default_user_id=False)

        if custom_values is None:
            custom_values = {}
        defaults = {
            'name':  msg_dict.get('subject') or _("No Subject"),
            'email_from': msg_dict.get('from'),
            'partner_id': msg_dict.get('author_id', False),
        }
        if msg_dict.get('author_id'):
            defaults.update(self._onchange_partner_id_values(msg_dict.get('author_id')))
        if msg_dict.get('priority') in dict(crm_stage.AVAILABLE_PRIORITIES):
            defaults['priority'] = msg_dict.get('priority')
        defaults.update(custom_values)

        # assign right company
        if 'company_id' not in defaults and 'team_id' in defaults:
            defaults['company_id'] = self.env['crm.team'].browse(defaults['team_id']).company_id.id
        return super(Lead, self).message_new(msg_dict, custom_values=defaults)

    def _message_post_after_hook(self, message, msg_vals):
        if self.email_from and not self.partner_id:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            new_partner = message.partner_ids.filtered(lambda partner: partner.email == self.email_from)
            if new_partner:
                self.search([
                    ('partner_id', '=', False),
                    ('email_from', '=', new_partner.email),
                    ('stage_id.fold', '=', False)]).write({'partner_id': new_partner.id})
        return super(Lead, self)._message_post_after_hook(message, msg_vals)

    def _message_partner_info_from_emails(self, emails, link_mail=False):
        result = super(Lead, self)._message_partner_info_from_emails(emails, link_mail=link_mail)
        for partner_info in result:
            if not partner_info.get('partner_id') and (self.partner_name or self.contact_name):
                emails = email_re.findall(partner_info['full_name'] or '')
                email = emails and emails[0] or ''
                if email and self.email_from and email.lower() == self.email_from.lower():
                    partner_info['full_name'] = '%s <%s>' % (self.contact_name or self.partner_name, email)
                    break
        return result

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Leads & Opportunities'),
            'template': '/crm/static/xls/crm_lead.xls'
        }]

    # ----------------------------------------
    # Predictive Lead Scoring
    # ----------------------------------------
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
        if len(self) == 0:
            return lead_probabilities

        LeadScoringFrequency = self.env['crm.lead.scoring.frequency']

        # get stages
        first_stage_id = self.env['crm.stage'].search([], order='sequence', limit=1)
        won_stage_ids = self.env['crm.stage'].search([('is_won', '=', True)]).ids

        # Get all leads values, no matter the team_id
        leads_values_dict = self._pls_get_lead_pls_values(batch_mode=batch_mode)
        if not leads_values_dict:
            return lead_probabilities

        # Get unique couples to search in frequency table
        leads_values = set()
        won_leads = set()
        for lead_id, values in leads_values_dict.items():
            for couple in values['values']:
                if couple[0] == 'stage_id' and couple[1] in won_stage_ids:
                    won_leads.add(lead_id)
                leads_values.add(couple)

        # get all variable related records from frequency table, no matter the team_id
        fields = list(set([lead_value[0] for lead_value in leads_values]))
        frequencies = LeadScoringFrequency.search([('variable', 'in', fields)], order="team_id asc")

        # get all team_ids from frequencies
        frequency_teams = frequencies.mapped('team_id')
        frequency_team_ids = [0] + [team.id for team in frequency_teams]

        # 1. Compute each variable value count individually
        # regroup each variable to be able to compute their own probabilities
        # As all the variable does not enter into account (as we reject unset values in the process)
        # each value probability must be computed only with their own variable related total count
        # special case: for lead for which team_id is not in frequency table,
        # we consider all the records, independently from team_id (this is why we add a result[-1])
        result = dict((team_id, dict((field, dict(won_total=0, lost_total=0)) for field in fields)) for team_id in frequency_team_ids)
        result[-1] = dict((field, dict(won_total=0, lost_total=0)) for field in fields)
        for frequency in frequencies:
            team_result = result[frequency.team_id.id if frequency.team_id else 0]

            field = frequency['variable']
            value = frequency['value']

            team_result[field][value] = {'won': frequency['won_count'], 'lost': frequency['lost_count']}
            team_result[field]['won_total'] += frequency['won_count']
            team_result[field]['lost_total'] += frequency['lost_count']

            if value not in result[-1][field]:
                result[-1][field][value] = {'won': 0, 'lost': 0}
            result[-1][field][value]['won'] += frequency['won_count']
            result[-1][field][value]['lost'] += frequency['won_count']
            result[-1][field]['won_total'] += frequency['won_count']
            result[-1][field]['lost_total'] += frequency['won_count']

        # Get all won, lost and total count for all records in frequencies per team_id
        for team_id in result:
            result[team_id]['team_won'], \
            result[team_id]['team_lost'], \
            result[team_id]['team_total'] = self._pls_get_won_lost_total_count(result[team_id], first_stage_id)

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

            lead_team_id = lead_values['team_id'] if lead_values['team_id'] else 0  # team_id = None -> Convert to 0
            lead_team_id = lead_team_id if lead_team_id in result else -1  # team_id not in frequency Table -> convert to -1
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
                value_result = field_result.get(str(value)) if field_result else False
                if value_result:
                    total_won = team_won if field == 'stage_id' else field_result['won_total']
                    total_lost = team_lost if field == 'stage_id' else field_result['lost_total']

                    s_lead_won *= value_result['won'] / total_won
                    s_lead_lost *= value_result['lost'] / total_lost

            # 3. Compute Probability to win
            lead_probabilities[lead_id] = round(100 * s_lead_won / (s_lead_won + s_lead_lost), 2)
        return lead_probabilities

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
            self.check_access_rights('unlink')
        except AccessError:
            raise UserError(_("You don't have the access needed to run this cron."))
        else:
            self._cr.execute('TRUNCATE TABLE crm_lead_scoring_frequency')

        # get stages by sequence
        stage_ids = self.env['crm.stage'].search_read([], ['sequence', 'name', 'id'], order='sequence')
        stage_sequences = {stage['id']: stage['sequence'] for stage in stage_ids}

        values_to_create = []
        # Compute stat individually for each team
        for team in self.env['crm.team'].with_context(active_test=False).search([]):
            values_to_create = self._pls_update_frequency_table(values_to_create, stage_ids, stage_sequences, team_id=team.id)
        values_to_create = self._pls_update_frequency_table(values_to_create, stage_ids, stage_sequences)

        # create all frequencies from all company and team in batch
        self.env['crm.lead.scoring.frequency'].create(values_to_create)
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
                    ('stage_id', '!=', False),
                    ('create_date', '>', pls_start_date),
                '|',
                    ('probability', '=', False),
                    '&',
                        ('probability', '<', 100),
                        ('probability', '>', 0)
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
        auto_commit = not getattr(threading.currentThread(), 'testing', False)
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

        _logger.info(
            "Predictive Lead Scoring : All automated probabilities updated (%d leads / %d transactions (%d failed) / %d seconds)" % (
                leads_to_update_count,
                transactions_count,
                transactions_failed_count,
                (datetime.now() - cron_update_lead_start_date).total_seconds(),
            )
        )

    # ----------------------------
    # Utility Tools for PLS
    # ----------------------------

    # PLS Config Parameters
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

    # Rebuild Frequency Table Tools
    # -----------------------------
    def _pls_update_frequency_table(self, values_to_create, stage_ids, stage_sequences, team_id=None):
        """ Create / update the frequency table in a cross company way, per team_id"""
        pls_start_date = self._pls_get_safe_start_date()
        if not pls_start_date:
            return values_to_create

        fields = ['stage_id', 'team_id'] + self._pls_get_safe_fields()
        frequencies = dict((field, {}) for field in (fields + ['tag_id']))

        frequencies = self._pls_update_frequency_table_fields(frequencies, stage_ids, stage_sequences, fields, team_id, pls_start_date)
        frequencies = self._pls_update_frequency_table_tag(frequencies, team_id, pls_start_date)

        # build the create multi
        for field, value in frequencies.items():
            for param, result in value.items():
                # To avoid that a tag take to much importance if his subset is too small,
                # we include the tag frequencies in the frequency table only if at least 50 won or lost leads had this tag.
                if field != 'tag_id' or (result['won'] + result['lost']) >= 50:
                    # We add + 0.1 in won and lost counts to avoid zero frequency issues
                    # should be +1 but it weights too much on small recordset.
                    values_to_create.append({
                        'variable': field,
                        'value': param,
                        'won_count': result['won'] + 0.1,
                        'lost_count': result['lost'] + 0.1,
                        'team_id': team_id
                    })
        return values_to_create

    def _pls_update_frequency_table_fields(self, frequencies, stage_ids, stage_sequences, fields, team_id, pls_start_date):
        # get all lead fields combination aggregated by won / lost count
        #   Prepare fields injection
        team_condition = 'and l.team_id = %s' if team_id else 'and l.team_id is null'
        str_fields = ", ".join(["{}"] * len(fields))
        args = [sql.Identifier(field) for field in fields] * 2

        #   Build sql query in safe mode
        self.flush(['probability', 'active'])
        query = """select probability, active, %s, count(probability) as count
                    from crm_lead l
                    where (probability = 0 or probability >= 100)
                    and create_date > %%s
                    %s
                    group by probability, active, %s """
        query = sql.SQL(query % (str_fields, team_condition, str_fields)).format(*args)

        query_params = [pls_start_date] + ([int(team_id)] if team_id else [])
        self._cr.execute(query, query_params)
        results = self._cr.dictfetchall()

        # Increment won / lost frequencies by criteria (field / value couple)
        for result in results:
            won = result['count'] if result['probability'] == 100 else 0
            lost = result['count'] if result['probability'] == 0 else 0
            for field in fields:
                value = result[field]
                if value or field in ('email_state', 'phone_state'):
                    if field == 'stage_id':
                        if won:  # increment all stages if won
                            stages_to_increment = [stage['id'] for stage in stage_ids]
                        else:  # increment only current + previous stages if lost
                            current_stage_sequence = stage_sequences[value]
                            stages_to_increment = [stage['id'] for stage in stage_ids if
                                          stage['sequence'] <= current_stage_sequence]
                        for stage in stages_to_increment:
                            frequencies = self._pls_increment_frequency(frequencies, field, stage, won, lost)
                    else:
                        frequencies = self._pls_increment_frequency(frequencies, field, value, won, lost)

        return frequencies

    def _pls_update_frequency_table_tag(self, frequencies, team_id, pls_start_date):
        # get all tag_ids won / lost count
        self.flush(['probability', 'active'])
        query = """select l.probability, l.active, t.id, count(l.probability) as count
                    from crm_lead_tag_rel rel
                    inner join crm_lead_tag t on rel.tag_id = t.id
                    inner join crm_lead l on l.id = rel.lead_id
                    where (l.probability = 0 or l.probability >= 100)
                    and l.create_date > %%s
                    %s
                    group by l.probability, l.active, t.id"""
        team_condition = 'and l.team_id = %s' if team_id else 'and l.team_id is null'
        query_params = [pls_start_date] + ([int(team_id)] if team_id else [])
        self._cr.execute(query % team_condition, query_params)
        tag_results = self._cr.dictfetchall()

        for result in tag_results:
            won = result['count'] if result['probability'] == 100 else 0
            lost = result['count'] if result['probability'] == 0 else 0
            value = result['id']
            frequencies = self._pls_increment_frequency(frequencies, 'tag_id', value, won, lost)

        return frequencies

    def _pls_increment_frequency(self, frequencies, field, value, won, lost):
        if value not in frequencies[field]:
            frequencies[field][value] = {'won': won, 'lost': lost}
        else:
            frequencies[field][value]['won'] += won
            frequencies[field][value]['lost'] += lost
        return frequencies

    # Compute Automated Probability Tools
    # -----------------------------------
    def _pls_get_lead_pls_values(self, batch_mode=False):
        """
        Due to onchange, we don't have always the id of the lead to recompute.
        When we update few records (one, typically) with onchanges, we build the
        lead_values (= couple field/value) using the ORM.
        To speed up the computation and avoid making too much DB read inside loops,
        we can activate the batch_mode, that needs the id of each lead to recompute to be known.
        That batch mode is directly making sql queries to bypass the ORM,
        so we can get everything we need for all leads to recompute in a minimum number of queries.
        This batch mode is currently called when the computation is triggered by
        crm.lead._cron_update_automated_probabilities().
        :param team_id: (int) team_id to search on
        :param batch_mode: (bool) batch mode
        :return: dict of list of tuple of field - value by lead ({lead_id: [(field1: value1), (field2: value2), ...], ...})
        """
        leads_values_dict = OrderedDict()
        fields = ["stage_id", "team_id"] + self._pls_get_safe_fields()
        if batch_mode:
            # get all info on leads
            #   Prepare fields injection
            str_fields = ", ".join(["{}"] * len(fields))
            args = [sql.Identifier(field) for field in fields]
            #   Build sql query in safe mode
            self.flush(['probability'])
            query = """SELECT id, %s
                        FROM crm_lead l
                        WHERE ((probability > 0 AND probability < 100) OR probability is null) AND active = True AND id in %%s order by team_id asc"""
            query = sql.SQL(query % str_fields).format(*args)

            self._cr.execute(query, [tuple(self.ids)])
            lead_results = self._cr.dictfetchall()

            query = """SELECT l.id as lead_id, t.id as tag_id
                        FROM crm_lead l
                        LEFT JOIN crm_lead_tag_rel rel ON l.id = rel.lead_id
                        LEFT JOIN crm_lead_tag t ON rel.tag_id = t.id
                        WHERE ((l.probability > 0 AND l.probability < 100) OR l.probability is null) AND l.active = True AND l.id in %s order by l.team_id asc"""
            self._cr.execute(query, [tuple(self.ids)])
            tag_results = self._cr.dictfetchall()

            # get all (variable, value) couple for all in self
            for lead in lead_results:
                lead_values = []
                for field in fields:
                    if field == 'team_id':  # ignore team_id as stored separately in leads_values_dict[lead_id][team_id]
                        continue
                    value = lead[field]
                    if value or field in ('email_state', 'phone_state'):
                        lead_values.append((field, value))
                leads_values_dict[lead['id']] = {'values': lead_values, 'team_id': lead['team_id']}

            for tag in tag_results:
                if tag['tag_id']:
                    leads_values_dict[tag['lead_id']]['values'].append(('tag_id', tag['tag_id']))
            return leads_values_dict
        else:
            for lead in self:
                lead_values = []
                for field in fields:
                    if field == 'team_id':  # ignore team_id as stored separately in leads_values_dict[lead_id][team_id]
                        continue
                    value = lead[field].id if isinstance(lead[field], models.BaseModel) else lead[field]
                    if value or field in ('email_state', 'phone_state'):
                        lead_values.append((field, value))
                for tag in lead.tag_ids:
                    lead_values.append(('tag_id', tag.id))
                leads_values_dict[lead.id] = {'values': lead_values, 'team_id': lead['team_id'].id}
            return leads_values_dict

    def _pls_get_won_lost_total_count(self, team_results, first_stage_id):
        """ Get all won and all lost + total :
               first stage can be used to know how many lost and won there is
               as won count are equals for all stage
               and first stage is always incremented in lost_count
        :param frequencies: lead_scoring_frequencies
        :param first_stage_id: stage with smallest sequence
        :return: won count, lost count and total count for all records in frequencies
        """
        if str(first_stage_id.id) not in team_results.get('stage_id', []):
            return 0, 0, 0
        stage_result = team_results['stage_id'][str(first_stage_id.id)]
        return stage_result['won'], stage_result['lost'], stage_result['won'] + stage_result['lost']


class Tag(models.Model):

    _name = "crm.lead.tag"
    _description = "Lead Tag"

    name = fields.Char('Tag Name', required=True, translate=True)
    color = fields.Integer('Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class LostReason(models.Model):
    _name = "crm.lost.reason"
    _description = 'Opp. Lost Reason'

    name = fields.Char('Description', required=True, translate=True)
    active = fields.Boolean('Active', default=True)
