# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from operator import itemgetter

from openerp import api, fields, models, SUPERUSER_ID, tools, _
from openerp.tools import email_re, email_split
from openerp.exceptions import UserError, AccessError

import crm
from openerp.addons.base.res.res_partner import format_address
from openerp.addons.base.res.res_request import referencable_models


CRM_LEAD_FIELDS_TO_MERGE = ['name',
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
    'email',
    'fax',
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
    'date_action_next',
    'email_from',
    'email_cc',
    'partner_name']


class CrmLead(format_address, models.Model):
    """ CRM Lead Case """
    _name = "crm.lead"
    _description = "Lead/Opportunity"
    _order = "priority desc,date_action,id desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin', 'utm.mixin']
    _mail_mass_mailing = _('Leads / Opportunities')

    def _default_get_stage_id(self):
        """ Gives default stage_id """
        team_id = self.env['crm.team']._get_default_team_id()
        return self.stage_find(team_id, [('fold', '=', False)])

    partner_id = fields.Many2one('res.partner', string='Partner', ondelete='set null', track_visibility='onchange',
        index=True, help="Linked partner (optional). Usually created when converting the lead.")

    name = fields.Char(string='Opportunity', required=True, index=True)
    active = fields.Boolean(required=False, default=True)
    date_action_last = fields.Datetime(string='Last Action', readonly=True)
    date_action_next = fields.Datetime(string='Next Action', readonly=True)
    email_from = fields.Char(string='Email', size=128, help="Email address of the contact", index=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id',
                    index=True, track_visibility='onchange', help='When sending mails, the default email address is taken from the sales team.', default=lambda self: self.env['crm.team']._get_default_team_id())
    create_date = fields.Datetime(string='Creation Date', readonly=True)
    email_cc = fields.Text(string='Global CC', help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma")
    description = fields.Text(string='Notes')
    write_date = fields.Datetime(string='Update Date', readonly=True)
    tag_ids = fields.Many2many('crm.lead.tag', 'crm_lead_tag_rel', 'lead_id', 'tag_id', string='Tags', help="Classify and analyze your lead/opportunity categories like: Training, Service")
    contact_name = fields.Char()
    partner_name = fields.Char(string="Customer Name", help='The name of the future partner company that will be created while converting the lead into opportunity', index=True)
    opt_out = fields.Boolean(string='Opt-Out', oldname='optout',
        help="If opt-out is checked, this contact has refused to receive emails for mass mailing and marketing campaign. "
                "Filter 'Available for Mass Mailing' allows users to filter the leads when performing mass mailing.")
    type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity')], index=True, help="Type is used to separate Leads and Opportunities", default='lead')
    priority = fields.Selection(crm.AVAILABLE_PRIORITIES, index=True, default=lambda *a: crm.AVAILABLE_PRIORITIES[0][0])
    date_closed = fields.Datetime(string='Closed', readonly=True, copy=False)
    stage_id = fields.Many2one('crm.stage', string='Stage', track_visibility='onchange', index=True,
                    domain="['&', ('team_ids', '=', team_id), '|', ('type', '=', type), ('type', '=', 'both')]", default=lambda self: self._default_get_stage_id())
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    referred = fields.Char(string='Referred By')
    date_open = fields.Datetime(string='Assigned', readonly=True)
    day_open = fields.Float(compute='_compute_day', string='Days to Assign', store=True)
    day_close = fields.Float(compute='_compute_day', string='Days to Close', store=True)
    date_last_stage_update = fields.Datetime(string='Last Stage Update', index=True, default=fields.Datetime.now)
    date_conversion = fields.Datetime(string='Conversion Date', readonly=True)

    # Messaging and marketing
    message_bounce = fields.Integer(string='Bounce', help="Counter of the number of bounced emails for this contact")
    # Only used for type opportunity
    probability = fields.Float(group_operator="avg")
    planned_revenue = fields.Float(string='Expected Revenue', track_visibility='always')
    ref = fields.Reference(string='Reference', selection=lambda self: referencable_models(self, self.env.cr, self.env.uid, self.env.context))
    ref2 = fields.Reference(
        string='Reference 2', selection=lambda self: referencable_models(self, self.env.cr, self.env.uid, self.env.context))
    phone = fields.Char()
    date_deadline = fields.Date(string='Expected Closing', help="Estimate of the date on which the opportunity will be won.")
    date_action = fields.Date(string='Next Action Date', index=True)
    title_action = fields.Char(string='Next Action')
    color = fields.Integer(string='Color Index')
    partner_address_name = fields.Char(related='partner_id.name', string='Partner Contact Name', readonly=True)
    partner_address_email = fields.Char(related='partner_id.email', string='Partner Contact Email', readonly=True)
    company_currency = fields.Many2one(related='company_id.currency_id', string='Currency', readonly=True)
    user_email = fields.Char(related='user_id.email', readonly=True)
    user_login = fields.Char(related='user_id.login', string='User Login', readonly=True)

    # Fields for address, due to separation from crm and res.partner
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')
    phone = fields.Char()
    fax = fields.Char()
    mobile = fields.Char()
    function = fields.Char()
    title = fields.Many2one('res.partner.title')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env['res.company']._company_default_get('crm.lead'))
    planned_cost = fields.Float(string='Planned Costs')
    meeting_count = fields.Integer(compute='_compute_meeting_count', string='# Meetings')
    lost_reason = fields.Many2one('crm.lost.reason', string='Lost Reason', index=True, track_visibility='onchange')
    calls_count = fields.Integer(compute='_compute_calls_count', string='# Phonecalls')

    _sql_constraints = [
        ('check_probability', 'check(probability >= 0 and probability <= 100)', 'The probability of closing the deal should be between 0% and 100%!')
    ]

    @api.depends('date_open', 'date_closed')
    def _compute_day(self):
        """
        :return dict: difference between current date and log date
        """
        for lead in self:
            ans = False
            if lead.date_open:
                date_create = fields.Datetime.from_string(lead.create_date)
                date_open = fields.Datetime.from_string(lead.date_open)
                ans = date_open - date_create
                self.day_open = abs(int(ans.days))

            if lead.date_closed:
                date_create = fields.Datetime.from_string(lead.create_date)
                date_close = fields.Datetime.from_string(lead.date_closed)
                ans = date_close - date_create
                self.day_close = abs(int(ans.days))

    @api.one
    def _compute_meeting_count(self):
        self.meeting_count = self.env['calendar.event'].search_count([('opportunity_id', 'in', self.ids)])

    @api.multi
    def _compute_calls_count(self):
        phonecall_data = self.env['crm.phonecall'].read_group(
            [('opportunity_id', 'in', self.ids)], ['opportunity_id'], ['opportunity_id'])
        mapped_data = dict([(m['opportunity_id'][0], m['opportunity_id_count']) for m in phonecall_data])
        for phonecall in self:
            phonecall.calls_count = mapped_data.get(phonecall.id, 0)

    @api.onchange('partner_id')
    def on_change_partner_id(self):
        partner = self.partner_id
        self.partner_name = partner.parent_id.name if partner.parent_id else partner.name
        self.contact_name = partner.name if partner.parent_id else False
        self.title = partner.title.id
        self.street = partner.street
        self.street2 = partner.street2
        self.city = partner.city
        self.state_id = partner.state_id.id
        self.country_id = partner.country_id.id
        self.email_from = partner.email
        self.phone = partner.phone
        self.mobile = partner.mobile
        self.fax = partner.fax
        self.zip = partner.zip
        self.function = partner.function

    @api.onchange('user_id')
    def on_change_user(self):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of. """
        team_id = self.env['crm.team']._get_default_team_id()
        if self.user_id and not team_id and self.user_id.has_group('base.group_multi_salesteams'):
            team_id = self.env['crm.team'].search(['|', ('user_id', '=', self.user_id.id), \
                                                        ('member_ids', '=', self.user_id.id)], limit=1).id
        self.team_id = team_id

    @api.onchange('state_id')
    def onchange_state(self):
        self.country_id = self.state_id.country_id.id

    @api.multi
    def onchange_stage_id(self, stage_id=False):
        if not stage_id:
            return
        stage = self.env['crm.stage'].browse(stage_id)
        if not stage.on_change:
            return
        for lead in self:
            lead.probability = stage.probability
            if stage.probability >= 100 or (stage.probability == 0 and stage.sequence > 1):
                lead.date_closed = fields.Datetime.now()

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if self.env.context.get('opportunity_id'):
            action = self._get_formview_action(self.env.context['opportunity_id'])
            if action.get('views') and any(view_id for view_id in action['views'] if view_id[1] == view_type):
                view_id = next(view_id[0] for view_id in action['views'] if view_id[1] == view_type)
        res = super(CrmLead, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            res['arch'] = self.fields_view_get_address(res['arch'])
        return res

    @api.model
    def create(self, vals):
        type = vals.get('type')
        ctx = dict(self.env.context)
        if type and not ctx.get('default_type'):
            ctx['default_type'] = type
        if vals.get('team_id') and not ctx.get('default_team_id'):
            ctx['default_team_id'] = vals.get('team_id')
        if vals.get('user_id'):
            vals['date_open'] = fields.Datetime.now()
        ctx['mail_create_nolog'] = True
        return super(CrmLead, self.with_context(ctx)).create(vals)

    @api.multi
    def write(self, vals):
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.Datetime.now()
        if vals.get('user_id'):
            vals['date_open'] = fields.Datetime.now()
        # stage change with new stage: update probability and date_closed
        if vals.get('stage_id') and not vals.get('probability'):
            self.onchange_stage_id(vals.get('stage_id'))
        return super(CrmLead, self).write(vals)

    @api.one
    def copy(self, default=None):
        if default is None: default = {}
        if self.type == 'opportunity':
            default['date_open'] = fields.Datetime.now()
        else:
            default['date_open'] = False
        return super(CrmLead, self.with_context(default_type=self.type, default_team_id=self.team_id.id)).copy(default=default)

    @api.multi
    def redirect_opportunity_view(self):
        # Get opportunity views
        self.ensure_one()
        form_view = self.env.ref('crm.crm_case_form_view_oppor')
        tree_view = self.env.ref('crm.crm_case_tree_view_oppor')
        return {
            'name': _('Opportunity'),
            'view_type': 'form',
            'view_mode': 'tree, form',
            'res_model': 'crm.lead',
            'domain': [('type', '=', 'opportunity')],
            'res_id': self.id,
            'view_id': False,
            'views': [(form_view.id, 'form'),
                      (tree_view.id, 'tree'), (False, 'kanban'),
                      (False, 'calendar'), (False, 'graph')],
            'type': 'ir.actions.act_window',
            'context': {'default_type': 'opportunity'}
        }

    @api.multi
    def redirect_lead_view(self):
        # Get lead views
        self.ensure_one()
        form_view = self.env.ref('crm.crm_case_form_view_leads')
        tree_view = self.env.ref('crm.crm_case_tree_view_leads')
        return {
            'name': _('Lead'),
            'view_type': 'form',
            'view_mode': 'tree, form',
            'res_model': 'crm.lead',
            'domain': [('type', '=', 'lead')],
            'res_id': self.id,
            'view_id': False,
            'views': [(form_view.id, 'form'),
                      (tree_view.id, 'tree'),
                      (False, 'calendar'), (False, 'graph')],
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def action_schedule_meeting(self):
        """
        Open meeting's calendar view to schedule meeting on current opportunity.
        :return dict: dictionary value for created Meeting view
        """
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('calendar', 'action_calendar_event')
        partner_ids = [self.env.user.partner_id.id]
        if self.partner_id:
            partner_ids.append(self.partner_id.id)
        res['context'] = {
            'search_default_opportunity_id': self.type == 'opportunity' and self.id,
            'default_opportunity_id': self.type == 'opportunity' and self.id,
            'default_partner_id': self.partner_id.id,
            'default_partner_ids': partner_ids,
            'default_team_id': self.team_id.id,
            'default_name': self.name,
        }
        return res

    # ----------------------------------------
    # Mail Gateway
    # ----------------------------------------
    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage_id' in init_values and self.probability == 100 and self.stage_id.on_change:
            return 'crm.mt_lead_won'
        elif 'stage_id' in init_values and self.probability == 0 and self.stage_id.on_change and self.stage_id.sequence > 1:
            return 'crm.mt_lead_lost'
        elif 'stage_id' in init_values and self.probability == 0 and self.stage_id.sequence <= 1:
            return 'crm.mt_lead_create'
        elif 'stage_id' in init_values:
            return 'crm.mt_lead_stage'
        return super(CrmLead, self)._track_subtype(init_values)

    @api.model
    def message_get_reply_to(self, res_ids, default=None):
        """ Override to get the reply_to of the parent project. """
        leads = self.sudo().browse(res_ids)
        team_ids = set(leads.mapped('team_id').ids)
        aliases = self.env['crm.team'].message_get_reply_to(list(team_ids), default=default)
        return dict((lead.id, aliases.get(lead.team_id and lead.team_id.id or 0, False)) for lead in leads)

    @api.one
    def get_formview_id(self):
        if self.type == 'opportunity':
            view_id = self.env.ref('crm.crm_case_form_view_oppor').id
        else:
            view_id = super(CrmLead, self).get_formview_id()
        return view_id

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(CrmLead, self).message_get_suggested_recipients()
    #TODO: set proper parameter
        try:
            for lead in self:
                if lead.partner_id:
                    self._message_add_suggested_recipient(recipients, lead, partner=lead.partner_id, reason=_('Customer'))
                elif lead.email_from:
                    self._message_add_suggested_recipient(recipients, lead, email=lead.email_from, reason=_('Customer Email'))
        except AccessError:    # no read access rights -> just ignore suggested recipients because this imply modifying followers
            pass
        return recipients

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        author_id = msg.get('author_id', False)
        priority = msg.get('priority')
        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': author_id,
            'user_id': False,
        }
        if author_id:
            self.partner_id = author_id
            defaults.update(self.on_change_partner_id())

        if priority in dict(crm.AVAILABLE_PRIORITIES):
            defaults['priority'] = priority
        defaults.update(custom_values)
        return super(CrmLead, self).message_new(msg, custom_values=defaults)

    @api.multi
    def message_update(self, msg, update_vals=None):
        """ Overrides mail_thread message_update that is called by the mailgateway
            through message_process.
            This method updates the document according to the email.
        """
        priority = msg.get('priority')
        if update_vals is None: update_vals = {}
        if priority in dict(crm.AVAILABLE_PRIORITIES):
            update_vals['priority'] = priority
        maps = {
            'cost':'planned_cost',
            'revenue': 'planned_revenue',
            'probability':'probability',
        }
        for line in msg.get('body', '').split('\n'):
            line = line.strip()
            res = tools.command_re.match(line)
            if res and maps.get(res.group(1).lower()):
                key = maps.get(res.group(1).lower())
                update_vals[key] = res.group(2).lower()

        return super(CrmLead, self).message_update(msg, update_vals=update_vals)

    @api.multi
    def log_meeting(self, meeting_subject, meeting_date, duration):
        meet_date = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, fields.Datetime.from_string(meeting_date)))
        if not duration:
            duration = _('unknown')
        else:
            duration = str(duration)
        message = _("Meeting scheduled at '%s'<br> Subject: %s <br> Duration: %s hour(s)") % (meet_date, meeting_subject, duration)
        return self.message_post(body=message)

    @api.multi
    def message_partner_info_from_emails(self, emails, link_mail=False):
        self.ensure_one()
        res = super(CrmLead, self).message_partner_info_from_emails(emails, link_mail=link_mail)
        for partner_info in res:
            if not partner_info.get('partner_id') and (self.partner_name or self.contact_name):
                emails = email_re.findall(partner_info['full_name'] or '')
                email = emails and emails[0] or ''
                if email and self.email_from and email.lower() == self.email_from.lower():
                    partner_info['full_name'] = '%s <%s>' % (self.partner_name or self.contact_name, email)
                    break
        return res

    @api.model
    def get_empty_list_help(self, help):
        ctx = dict(self.env.context)
        if ctx.get('default_type') == 'lead':
            ctx['empty_list_help_document_name'] = _("lead")
        else:
            ctx['empty_list_help_document_name'] = _("opportunity")
        ctx['empty_list_help_model'] = 'crm.team'
        ctx['empty_list_help_id'] = ctx.get('default_team_id')
        return super(CrmLead, self.with_context(ctx)).get_empty_list_help(help)

    @api.multi
    def stage_find(self, team_id, domain=None, order='sequence'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - type: stage type must be the same or 'both'
            - team_id: if set, stages must belong to this team or
              be a default stage; if not set, stages must be default
              stages
        """
        avoid_add_type_term = any([term for term in domain if len(term) == 3 if term[0] == 'type'])
        # collect all team_ids
        team_ids = set()
        types = ['both']
        default_type = self.env.context.get('default_type')
        if default_type:
            ctx_type = default_type
            types += [ctx_type]
        if team_id:
            team_ids.add(team_id)
        for lead in self:
            if lead.team_id:
                team_ids.add(lead.team_id.id)
            if lead.type not in types:
                types.append(lead.type)
        # OR all team_ids and OR with case_default
        search_domain = []
        if team_ids:
            search_domain += [('|')] * len(team_ids)
            for team_id in team_ids:
                search_domain.append(('team_ids', '=', team_id))
        search_domain.append(('case_default', '=', True))
        # AND with cases types
        if not avoid_add_type_term:
            search_domain.append(('type', 'in', types))
        # AND with the domain in parameter
        search_domain += list(domain)
        # perform search, return the first found
        stage = self.env['crm.stage'].search(search_domain, order=order, limit=1)
        return stage.id

    @api.multi
    def case_mark_lost(self):
        """ Mark the case as lost: state=cancel and probability=0
        """
        stages_leads = {}
        for lead in self:
            stage_id = lead.stage_find(lead.team_id.id, [('probability', '=', 0.0), ('on_change', '=', True), ('sequence', '>', 1)])
            if stage_id:
                if stages_leads.get(stage_id):
                    stages_leads[stage_id].append(lead.id)
                else:
                    stages_leads[stage_id] = [lead.id]
            else:
                raise UserError(_('To relieve your sales pipe and group all Lost opportunities, configure one of your sales stage as follow:\n'
                                    'probability = 0 %, select "Change Probability Automatically".\n'
                                    'Create a specific stage or edit an existing one by editing columns of your opportunity pipe.'))
        for stage_id, lead_ids in stages_leads.items():
            self.browse(lead_ids).write({'stage_id': stage_id})
        return True

    @api.multi
    def case_mark_won(self):
        """ Mark the case as won: state=done and probability=100
        """
        stages_leads = {}
        for lead in self:
            stage_id = lead.stage_find(lead.team_id.id, domain=[('probability', '=', 100.0), ('on_change', '=', True)])
            if stage_id:
                if stages_leads.get(stage_id):
                    stages_leads[stage_id].append(lead.id)
                else:
                    stages_leads[stage_id] = [lead.id]
            else:
                raise UserError(_('To relieve your sales pipe and group all Won opportunities, configure one of your sales stage as follow:\n'
                                    'probability = 100 % and select "Change Probability Automatically".\n'
                                    'Create a specific stage or edit an existing one by editing columns of your opportunity pipe.'))
        for stage_id, lead_ids in stages_leads.items():
            self.browse(lead_ids).write({'stage_id': stage_id})
        return True

    @api.multi
    def case_escalate(self):
        """ Escalates case to parent level """
        for case in self:
            data = {'active': True}
            if case.team_id.parent_id:
                data['team_id'] = case.team_id.parent_id.id
                if case.team_id.parent_id.change_responsible:
                    if case.team_id.parent_id.user_id:
                        data['user_id'] = case.team_id.parent_id.user_id.id
            else:
                raise UserError(_("You are already at the top level of your sales-team category.\nTherefore you cannot escalate furthermore."))
            case.write(data)
        return True

    def get_duplicated_leads(self, partner_id, include_lost=False):
        """
        Search for opportunities that have the same partner and that arent done or cancelled
        """
        email = self.partner_id.email or self.email_from
        return self._get_duplicated_leads_by_emails(partner_id, email, include_lost=include_lost)

    def merge_dependences(self, opportunities):
        self._merge_notify(opportunities)
        self._merge_opportunity_history(opportunities)
        self._merge_opportunity_attachments(opportunities)
        self._merge_opportunity_phonecalls(opportunities)

    @api.multi
    def merge_opportunity(self, user_id=False, team_id=False):
        """
        Different cases of merge:
        - merge leads together = 1 new lead
        - merge at least 1 opp with anything else (lead or opp) = 1 new opp

        """
        if len(self) <= 1:
            raise UserError(_('Please select more than one element (lead or opportunity) from the list view.'))

        sequenced_opps = []
        # Sorting the leads/opps according to the confidence level of its stage, which relates to the probability of winning it
        # The confidence level increases with the stage sequence, except when the stage probability is 0.0 (Lost cases)
        # An Opportunity always has higher confidence level than a lead, unless its stage probability is 0.0
        for opportunity in self:
            sequence = -1
            if opportunity.stage_id and opportunity.stage_id.on_change:
                sequence = opportunity.stage_id.sequence
            sequenced_opps.append(((int(sequence != -1 and opportunity.type == 'opportunity'), sequence, -opportunity.id), opportunity.id))
        sequenced_opps.sort(reverse=True)
        opportunities = map(itemgetter(1), sequenced_opps)
        opportunities = self.browse(opportunities)
        highest = opportunities[0]
        opportunities_rest = opportunities[1:]
        tail_opportunities = opportunities_rest
        fields = list(CRM_LEAD_FIELDS_TO_MERGE)
        merged_data = opportunities.merge_data(fields)
        if user_id:
            merged_data['user_id'] = user_id
        if team_id:
            merged_data['team_id'] = team_id
        # Merge notifications about loss of information
        opportunities = [highest]
        opportunities.extend(opportunities_rest)
        highest.merge_dependences(tail_opportunities)
        # Check if the stage is in the stages of the sales team. If not, assign the stage with the lowest sequence
        if merged_data.get('team_id'):
            stage = self.env['crm.stage'].search([('team_ids', 'in', merged_data['team_id']), ('type', '=', merged_data.get('type'))], order='sequence')
            if merged_data.get('stage_id') not in stage.ids:
                merged_data['stage_id'] = stage and stage[0].id
        # Write merged data into first opportunity
        highest.write(merged_data)
        # Delete tail_opportunities
        # We use the SUPERUSER to avoid access rights issues because as the user had the rights to see the records it should be safe to do so
        for x in tail_opportunities:
            x.sudo().unlink()
        return highest

    @api.multi
    def convert_opportunity(self, partner_id, user_ids=False, team_id=False):
        customer = False
        if partner_id:
            customer = self.env['res.partner'].browse(partner_id)
        for lead in self:
            # TDE: was if lead.state in ('done', 'cancel'):
            if (lead.probability == 100 or lead.probability == 0) and lead.stage_id.on_change and lead.stage_id.sequence > 1:
                continue
            vals = lead._convert_opportunity_data(customer, team_id)
            lead.write(vals)
        if user_ids or team_id:
            self.allocate_salesman(user_ids, team_id)
        return True

    @api.multi
    def handle_partner_assignation(self, action='create', partner=False):
        """
        Handle partner assignation during a lead conversion.
        if action is 'create', create new partner with contact and assign lead to new partner_id.
        otherwise assign lead to the specified partner_id

        :param string action: what has to be done regarding partners (create it, assign an existing one, or nothing)
        :param tuple partner: partner to assign if any
        :return dict: dictionary organized as followed: {lead_id: partner_assigned_id}
        """
        #TODO this is a duplication of the handle_partner_assignation method of crm_phonecall
        partner_ids = {}
        for lead in self:
            # If the action is set to 'create' and no partner_id is set, create a new one
            if lead.partner_id:
                partner_ids[lead.id] = lead.partner_id.id
            if action == 'create':
                partner = lead._create_lead_partner()
                partner.write({'team_id': lead.team_id.id})
            if partner:
                lead.write({'partner_id': partner.id})
            partner_ids[lead.id] = partner.id
        return partner_ids

    @api.multi
    def allocate_salesman(self, user_ids=None, team_id=False):
        """
        Assign salesmen and salesteam to a batch of leads.  If there are more
        leads than salesmen, these salesmen will be assigned in round-robin.
        E.g.: 4 salesmen (S1, S2, S3, S4) for 6 leads (L1, L2, ... L6).  They
        will be assigned as followed: L1 - S1, L2 - S2, L3 - S3, L4 - S4,
        L5 - S1, L6 - S2.

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

    @api.multi
    def merge_data(self, fields):
        """
        Prepare lead/opp data into a dictionary for merging.  Different types
        of fields are processed in different ways:
        - text: all the values are concatenated
        - m2m and o2m: those fields aren't processed
        - m2o: the first not null value prevails (the other are dropped)
        - any other type of field: same as m2o

        :param list fields: list of leads' fields to process
        :return dict data: contains the merged values
        """
        def _get_first_not_null(attr):
            for opp in self:
                if hasattr(opp, attr) and bool(getattr(opp, attr)):
                    return getattr(opp, attr)
            return False

        def _get_first_not_null_id(attr):
            res = _get_first_not_null(attr)
            return res and res.id or False

        def _concat_all(attr):
            return '\n\n'.join(filter(lambda x: x, [getattr(opp, attr) or '' for opp in self if hasattr(opp, attr)]))
        # Process the fields' values
        data = {}
        for field_name in fields:
            field = self._fields.get(field_name)
            if field is None:
                continue
            if field.type in ('many2many', 'one2many'):
                continue
            elif field.type == 'many2one':
                data[field_name] = _get_first_not_null_id(field_name)  # !!
            elif field.type == 'text':
                data[field_name] = _concat_all(field_name)  #not lost
            else:
                data[field_name] = _get_first_not_null(field_name)  #not lost
        # Define the resulting type ('lead' or 'opportunity')
        data['type'] = self._merge_get_result_type()
        return data

    def _get_duplicated_leads_by_emails(self, partner_id, email, include_lost=False):
        """
        Search for opportunities that have   the same partner and that arent done or cancelled
        """
        final_stage_domain = ['|', '|', ('stage_id.on_change', '=', False), ('stage_id.probability', 'not in', [0, 100]), ('stage_id.sequence', '<=', 1)]
        partner_match_domain = []
        for email in set(email_split(email) + [email]):
            partner_match_domain.append(('email_from', '=ilike', email))
        if partner_id:
            partner_match_domain.append(('partner_id', '=', partner_id))
        partner_match_domain = ['|'] * (len(partner_match_domain) - 1) + partner_match_domain
        if not partner_match_domain:
            return []
        domain = partner_match_domain
        if not include_lost:
            domain += final_stage_domain
        return self.search(domain)

    def _resolve_type_from_context(self):
        """ Returns the type (lead or opportunity) from the type context
            key. Returns None if it cannot be resolved.
        """
        return self.env.context.get('default_type')

    @api.multi
    def _read_group_stage_ids(self, domain, read_group_order=None, access_rights_uid=None):
        access_rights_uid = access_rights_uid or self.env.uid
        CrmStage = self.env['crm.stage']
        order = CrmStage._order
        # lame hack to allow reverting search, should just work in the trivial case
        if read_group_order == 'stage_id desc':
            order = "%s desc" % order
        # retrieve team_id from the context and write the domain
        # - ('id', 'in', 'ids'): add columns that should be present
        # - OR ('case_default', '=', True), ('fold', '=', False): add default columns that are not folded
        # - OR ('team_ids', '=', team_id), ('fold', '=', False) if team_id: add team columns that are not folded
        search_domain = []
        team_id = self.env['crm.team']._resolve_team_id_from_context()
        if team_id:
            search_domain += ['|', ('team_ids', '=', team_id)]
            search_domain += [('id', 'in', self.ids)]
        else:
            search_domain += ['|', ('id', 'in', self.ids), ('case_default', '=', True)]
        # retrieve type from the context (if set: choose 'type' or 'both')
        type = self._resolve_type_from_context()
        if type:
            search_domain += ['|', ('type', '=', type), ('type', '=', 'both')]
        # perform search
        stage_ids = CrmStage._search(search_domain, order=order, access_rights_uid=access_rights_uid)
        stage_rec = CrmStage.browse(stage_ids)
        result = stage_rec.name_get()
        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stage_rec:
            fold[stage.id] = stage.fold
        return result, fold

    _group_by_full = {
       'stage_id': _read_group_stage_ids
   }

    def _merge_get_result_type(self):
        """
        Define the type of the result of the merge.  If at least one of the
        element to merge is an opp, the resulting new element will be an opp.
        Otherwise it will be a lead.

        We'll directly use a list of browse records instead of a list of ids
        for performances' sake: it will spare a second browse of the
        leads/opps.

        :return string type: the type of the final element
        """
        for opp in self:
            if (opp.type == 'opportunity'):
                return 'opportunity'
        return 'lead'


    def _mail_body(self, fields, title=False):
        body = []
        if title:
            body.append("%s\n" % (title))

        for field_name in fields:
            field = self._fields.get(field_name)
            if field is None:
                continue
            value = ''
            if field.type == 'selection':
                if hasattr(field.selection, '__call__'):
                    key = field.selection(self, self.env.cr, self.env.uid, context=self.env.context)
                else:
                    key = field.selection
                value = dict(key).get(self[field_name], self[field_name])
            elif field.type == 'many2one':
                if self[field_name]:
                    value = self[field_name].name_get()[0][1]
            elif field.type == 'many2many':
                if self[field_name]:
                    for val in self[field_name]:
                        field_value = val.name_get()[0][1]
                        value += field_value + ","
            else:
                value = self[field_name]

            body.append("%s: %s" % (field.string, value or ''))
        return "<br/>".join(body + ['<br/>'])

    def _merge_notify(self, opportunities):
        """
        Create a message gathering merged leads/opps information.
        """
        #TOFIX: mail template should be used instead of fix body, subject text
        details = []
        result_type = opportunities._merge_get_result_type()
        if result_type == 'lead':
            merge_message = _('Merged leads')
        else:
            merge_message = _('Merged opportunities')
        subject = [merge_message]
        for opportunity in opportunities:
            subject.append(opportunity.name)
            title = "%s : %s" % (opportunity.type == 'opportunity' and _('Merged opportunity') or _('Merged lead'), opportunity.name)
            fields = list(CRM_LEAD_FIELDS_TO_MERGE)
            details.append(opportunity._mail_body(fields, title=title))

        # Chatter message's subject
        subject = subject[0] + ": " + ", ".join(subject[1:])
        details = "\n\n".join(details)
        return self.message_post(body=details, subject=subject)

    def _merge_opportunity_history(self, opportunities):
        self.ensure_one()
        for opportunity in opportunities:
            for history in opportunity.message_ids:
                history.write({
                        'res_id': self.id,
                        'subject': _("From %s : %s") % (opportunity.name, history.subject)
                })
        return True

    def _merge_opportunity_attachments(self, opportunities):
        # return attachments of opportunity
        self.ensure_one()
        def _get_attachments(opportunity_id):
            attachment_ids = self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', opportunity_id)])
            return attachment_ids
        first_attachments = _get_attachments(self.id)
        #counter of all attachments to move. Used to make sure the name is different for all attachments
        count = 1
        for opportunity in opportunities:
            attachments = _get_attachments(opportunity.id)
            for attachment in attachments:
                values = {'res_id': self.id}
                for attachment_in_first in first_attachments:
                    if attachment.name == attachment_in_first.name:
                        values['name'] = "%s (%s)" % (attachment.name, count),
                count += 1
                attachment.write(values)
        return True

    def _merge_opportunity_phonecalls(self, opportunities):
        self.ensure_one()
        CrmPhonecall = self.env['crm.phonecall']
        for opportunity in opportunities:
            for phonecall in CrmPhonecall.search([('opportunity_id', '=', opportunity.id)]):
                phonecall.write({'opportunity_id': self.id})
        return True

    def _create_lead_partner(self):
        self.ensure_one()
        contact_id = False
        contact_name = self.contact_name or self.email_from and self.env['res.partner']._parse_partner_name(self.email_from)[0]
        if self.partner_name:
            partner_company_id = self._lead_create_contact(self.partner_name, True)
        elif self.partner_id:
            partner_company_id = self.partner_id
        else:
            partner_company_id = False

        if contact_name:
            contact_id = self._lead_create_contact(contact_name, False)

        partner_id = contact_id or partner_company_id or self._lead_create_contact(self.name, False)
        return partner_id

    def _lead_create_contact(self, name, is_company, parent_id=False):
        self.ensure_one()
        email = tools.email_split(self.email_from)
        vals = {'name': name,
            'user_id': self.user_id.id,
            'comment': self.description,
            'team_id': self.team_id.id,
            'parent_id': parent_id,
            'phone': self.phone,
            'mobile': self.mobile,
            'email': email and email[0] or False,
            'fax': self.fax,
            'title': self.title.id,
            'function': self.function,
            'street': self.street,
            'street2': self.street2,
            'zip': self.zip,
            'city': self.city,
            'country_id': self.country_id.id,
            'state_id': self.state_id.id,
            'is_company': is_company,
            'type': 'contact'
                }
        partner = self.env['res.partner'].create(vals)
        return partner

    def _convert_opportunity_data(self, customer, team_id=False):
        self.ensure_one()
        contact_id = False
        if customer:
            customer.address_get()['default']
        if not team_id:
            team_id = self.team_id.id
        val = {
            'planned_revenue': self.planned_revenue,
            'probability': self.probability,
            'name': self.name,
            'partner_id': customer and customer.id or False,
            'type': 'opportunity',
            'date_action': fields.Datetime.now(),
            'date_open': fields.Datetime.now(),
            'email_from': customer and customer.email or self.email_from,
            'phone': customer and customer.phone or self.phone,
            'date_conversion': fields.Datetime.now(),
        }
        if not self.stage_id or self.stage_id.stage_type == 'lead':
            val['stage_id'] = self.stage_find(team_id, domain=[('stage_type', 'in', ('opportunity', 'both'))])
        return val

class CrmLeadTag(models.Model):
    _name = "crm.lead.tag"
    _description = "Category of lead"
    name = fields.Char(required=True, translate=True)
    team_id = fields.Many2one('crm.team', string='Sales Team')


class CrmLostReason(models.Model):
    _name = "crm.lost.reason"
    _description = 'Reason for loosing leads'

    name = fields.Char(required=True)
