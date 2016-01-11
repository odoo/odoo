# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from dateutil.relativedelta import relativedelta
from operator import itemgetter

from odoo import api, fields, models, tools, _
from odoo.tools import email_re, email_split
from odoo.exceptions import UserError, AccessError

from odoo.addons.base.res.res_partner import format_address
import crm_stage


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

    def _get_default_probability(self):
        """ Gives default probability """
        stage_id = self._get_default_stage_id()
        if stage_id:
            return self.env['crm.stage'].browse(stage_id).probability
        return 10

    def _get_default_stage_id(self):
        """ Gives default stage_id """
        team = self.env['crm.team'].sudo()._get_default_team_id(user_id=self.env.uid)
        return self.stage_find(team.id, [('fold', '=', False)])

    partner_id = fields.Many2one('res.partner', string='Partner', track_visibility='onchange',
            index=True, help="Linked partner (optional). Usually created when converting the lead.")

    name = fields.Char(string='Opportunity', required=True, index=True)
    active = fields.Boolean(default=True)
    date_action_last = fields.Datetime(string='Last Action', readonly=True)
    date_action_next = fields.Datetime(string='Next Action', readonly=True)
    email_from = fields.Char(string='Email', size=128, help="Email address of the contact", index=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id', default=lambda self: self.env['crm.team'].sudo()._get_default_team_id(user_id=self.env.uid),
                        index=True, track_visibility='onchange', help='When sending mails, the default email address is taken from the sales team.')
    kanban_state = fields.Selection(compute='_compute_kanban_state', string='Activity State',
            selection=[('grey', 'Normal'), ('red', 'Blocked'), ('green', 'Ready for next stage')])
    email_cc = fields.Text(string='Global CC', help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma")
    description = fields.Text(string='Notes')
    tag_ids = fields.Many2many('crm.lead.tag', 'crm_lead_tag_rel', 'lead_id', 'tag_id', string='Tags', help="Classify and analyze your lead/opportunity categories like: Training, Service")
    contact_name = fields.Char(string='Contact Name')
    partner_name = fields.Char(string="Customer Name", help='The name of the future partner company that will be created while converting the lead into opportunity', index=True)
    opt_out = fields.Boolean(string='Opt-Out', oldname='optout',
            help="If opt-out is checked, this contact has refused to receive emails for mass mailing and marketing campaign. "
                    "Filter 'Available for Mass Mailing' allows users to filter the leads when performing mass mailing.")
    type = fields.Selection(
            [('lead', 'Lead'), ('opportunity', 'Opportunity')],
            string='Type', index=True, required=True, default=lambda self: 'lead' if self.env['res.users'].has_group('crm.group_use_lead') else 'opportunity',
            help="Type is used to separate Leads and Opportunities")
    priority = fields.Selection(crm_stage.AVAILABLE_PRIORITIES, string='Rating', index=True, default=lambda *a: crm_stage.AVAILABLE_PRIORITIES[0][0])
    date_closed = fields.Datetime(string='Closed', readonly=True, copy=False)
    stage_id = fields.Many2one('crm.stage', string='Stage', track_visibility='onchange', index=True,
                        domain="['|', ('team_id', '=', False), ('team_id', '=', team_id)]", default=lambda self: self._get_default_stage_id())
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    referred = fields.Char(string='Referred By')
    date_open = fields.Datetime(string='Assigned', readonly=True)
    day_open = fields.Float(compute='_compute_day', string='Days to Assign', store=True)
    day_close = fields.Float(compute='_compute_day', string='Days to Close', store=True)
    date_last_stage_update = fields.Datetime(string='Last Stage Update', index=True, default=fields.Datetime.now)
    date_conversion = fields.Datetime(string='Conversion Date', readonly=True)

    # Messaging and marketing
    message_bounce = fields.Integer('Bounce', help="Counter of the number of bounced emails for this contact")
    # Only used for type opportunity
    probability = fields.Float(group_operator="avg", default=lambda self: self._get_default_probability())
    planned_revenue = fields.Float(string='Expected Revenue', track_visibility='always')
    date_deadline = fields.Date(string='Expected Closing', help="Estimate of the date on which the opportunity will be won.")
    # CRM Actions
    next_activity_id = fields.Many2one("crm.activity", string="Next Activity", index=True)
    date_action = fields.Date(string='Next Activity Date', index=True)
    title_action = fields.Char(string='Next Activity Summary')

    color = fields.Integer(string='Color Index', default=0)
    partner_address_name = fields.Char(related='partner_id.name', string='Partner Contact Name', readonly=True)
    partner_address_email = fields.Char(related='partner_id.email', string='Partner Contact Email', readonly=True)
    company_currency = fields.Many2one(related='company_id.currency_id', string='Currency', readonly=True, relation="res.currency")
    user_email = fields.Char(related='user_id.email', string='User Email', readonly=True)
    user_login = fields.Char(related='user_id.login', string='User Login', readonly=True)

    # Fields for address, due to separation from crm and res.partner
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True, size=24)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State')
    country_id = fields.Many2one('res.country', string='Country')
    phone = fields.Char()
    fax = fields.Char()
    mobile = fields.Char()
    function = fields.Char()
    title = fields.Many2one('res.partner.title')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id.id)
    meeting_count = fields.Integer(compute='_compute_meeting_count', string='# Meetings')
    lost_reason = fields.Many2one('crm.lost.reason', string='Lost Reason', index=True, track_visibility='onchange')

    _sql_constraints = [
        ('check_probability', 'check(probability >= 0 and probability <= 100)', 'The probability of closing the deal should be between 0% and 100%!')
    ]

    @api.depends('kanban_state')
    def _compute_kanban_state(self):
        """ Very interesting kanban state color. This makes complete sense. Or
        not. """
        today = fields.Date.from_string(fields.Date.today())
        for lead in self:
            lead.kanban_state = 'grey'
            if lead.date_action:
                lead_date = fields.Date.from_string(lead.date_action)
                if lead_date > today:
                    lead.kanban_state = 'green'
                elif lead_date < today:
                    lead.kanban_state = 'red'

    @api.depends('date_open', 'date_closed')
    def _compute_day(self):
        """
        Compute difference between current date and log date
        """
        for lead in self:
            if lead.date_open:
                date_create = fields.Datetime.from_string(lead.create_date)
                date_open = fields.Datetime.from_string(lead.date_open)
                ans = date_open - date_create
                lead.day_open = abs(int(ans.days))

            if lead.date_closed:
                date_create = fields.Datetime.from_string(lead.create_date)
                date_close = fields.Datetime.from_string(lead.date_closed)
                ans = date_close - date_create
                lead.day_close = abs(int(ans.days))

    def _compute_meeting_count(self):
        self.meeting_count = self.env['calendar.event'].search_count([('opportunity_id', 'in', self.ids)])

    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        value = self._onchange_stage_id_internal(self.stage_id.id)
        if value.get('probability'):
            self.probability = value['probability']

    def _onchange_stage_id_internal(self, stage_id=False):
        if not stage_id:
            return {}
        stage = self.env['crm.stage'].browse(stage_id)
        if not stage.on_change:
            return {}
        return {'probability': stage.probability}

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        partner = self.partner_id
        self.partner_name = partner.parent_id.name or partner.is_company and partner.name
        self.contact_name = (not partner.is_company and partner.name) or False
        self.title = partner.title
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
    def _onchange_user_id(self):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of. """
        CrmTeam = self.env['crm.team']
        if self.user_id and self.env.context.get('team_id'):
            team = CrmTeam.browse(self.env.context['team_id'])
            if self.user_id in team.member_ids:
                return
        self.team_id = CrmTeam._get_default_team_id(user_id=self.user_id.id or None)

    @api.onchange('next_activity_id')
    def _onchange_next_activity_id(self):
        activity = self.next_activity_id
        date_action = False
        if activity.days:
            date_action = fields.Datetime.to_string(fields.Datetime.from_string(fields.Datetime.now()) + timedelta(days=activity.days))
        self.title_action = activity.description
        self.date_action = date_action

    @api.onchange('state_id')
    def _onchange_state(self):
        self.country_id = self.state_id.country_id.id

    @api.model
    def create(self, vals):
        ctx = dict(self.env.context)
        if vals.get('type') and not ctx.get('default_type'):
            ctx['default_type'] = vals.get('type')
        if vals.get('team_id') and not ctx.get('default_team_id'):
            ctx['default_team_id'] = vals.get('team_id')
        if vals.get('user_id') and 'date_open' not in vals:
            vals['date_open'] = fields.Datetime.now()

        # context: no_log, because subtype already handle this
        ctx['mail_create_nolog'] = True
        return super(CrmLead, self.with_context(ctx)).create(vals)

    @api.multi
    def write(self, vals):
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.Datetime.now()
        if vals.get('user_id') and 'date_open' not in vals:
            vals['date_open'] = fields.Datetime.now()
        # stage change with new stage: update probability and date_closed
        if vals.get('stage_id') and 'probability' not in vals:
            vals.update(self._onchange_stage_id_internal(vals.get('stage_id')))
        if vals.get('probability') >= 100 or not vals.get('active', True):
            vals['date_closed'] = fields.Datetime.now()
        return super(CrmLead, self).write(vals)

    @api.multi
    def copy(self, default=None):
        self.ensure_one()
        default['date_open'] = False
        if self.type == 'opportunity':
            default['date_open'] = fields.Datetime.now()
        return super(CrmLead, self.with_context(default_type=self.type, default_team_id=self.team_id.id)).copy(default=default)

    @api.multi
    def stage_find(self, team_id, domain=None, order='sequence'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - team_id: if set, stages must belong to this team or
              be a default stage; if not set, stages must be default
              stages
        """
        # collect all team_ids
        team_ids = set()
        if team_id:
            team_ids.add(team_id)
        for lead in self:
            if lead.team_id:
                team_ids.add(lead.team_id.id)
        # OR all team_ids
        if team_ids:
            search_domain = ['|', ('team_id', '=', False), ('team_id', 'in', list(team_ids))]
        else:
            search_domain = [('team_id', '=', False)]
        # AND with the domain in parameter
        if domain:
            search_domain = ['&'] + list(domain) + search_domain
        # perform search, return the first found
        stage = self.env['crm.stage'].search(search_domain, order=order, limit=1)
        return stage.id

    @api.multi
    def action_set_lost(self):
        """ Lost semantic: probability = 0, active = False """
        return self.write({'probability': 0, 'active': False})
    # Backward compatibility
    case_mark_lost = action_set_lost

    @api.multi
    def action_set_active(self):
        return self.write({'active': True})

    @api.multi
    def action_set_unactive(self):
        return self.write({'active': False})

    @api.multi
    def action_set_won(self):
        """ Won semantic: probability = 100 (active untouched) """
        for lead in self:
            stage_id = lead.stage_find(lead.team_id.id, [('probability', '=', 100.0), ('on_change', '=', True)])
            return lead.write({'probability': 100, 'stage_id': stage_id})

    # Backward compatibility
    case_mark_won = action_set_won

    def _merge_get_result_type(self):
        """
        Define the type of the result of the merge.  If at least one of the
        element to merge is an opp, the resulting new element will be an opp.
        Otherwise it will be a lead.
        We'll directly use a list of browse records instead of a list of ids
        for performances' sake: it will spare a second browse of the
        leads/opps.
        :param list opps: list of browse records containing the leads/opps to process
        :return string type: the type of the final element
        """
        for opp in self.filtered(lambda o: o.type == 'opportunity'):
            return 'opportunity'

        return 'lead'

    @api.multi
    def _merge_data(self, oldest, fields):
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
                if callable(field.selection):
                    key = field.selection()
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
                        'res_id': opportunity.id,
                        'subject' : _("From %s : %s") % (opportunity.name, history.subject)
                })

        return True

    def _merge_opportunity_attachments(self, opportunities):

        self.ensure_one()
        # return attachments of opportunity
        def _get_attachments(opportunity_id):
            return self.env['ir.attachment'].search([('res_model', '=', self._name), ('res_id', '=', opportunity_id)])

        first_attachments = _get_attachments(self.id)
        #counter of all attachments to move. Used to make sure the name is different for all attachments
        count = 1
        for opportunity in opportunities:
            attachments = _get_attachments(opportunity.id)
            for attachment in attachments:
                values = {'res_id': self.id,}
                for attachment_in_first in first_attachments:
                    if attachment.name == attachment_in_first.name:
                        values['name'] = "%s (%s)" % (attachment.name, count,),
                count+=1
                attachment.write(values)
        return True

    def _get_duplicated_leads_by_emails(self, partner_id, email, include_lost=False):
        """
        Search for opportunities that have   the same partner and that arent done or cancelled
        """
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
            domain += ['&', ('active', '=', True), ('probability', '<', 100)]
        return self.search(domain)

    def merge_dependences(self, opportunities):
        self._merge_notify(opportunities)
        self._merge_opportunity_history(opportunities)
        self._merge_opportunity_attachments(opportunities)

    @api.multi
    def merge_opportunity(self, user_id=False, team_id=False):
        """
        Different cases of merge:
        - merge leads together = 1 new lead
        - merge at least 1 opp with anything else (lead or opp) = 1 new opp
        :param list ids: leads/opportunities ids to merge
        :return int id: id of the resulting lead/opp
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
        opportunities = self.browse(map(itemgetter(1), sequenced_opps))
        highest = opportunities[0]
        opportunities_rest = opportunities[1:]

        tail_opportunities = opportunities_rest

        fields = list(CRM_LEAD_FIELDS_TO_MERGE)
        merged_data = opportunities._merge_data(highest, fields)

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
            stages = self.env['crm.stage'].search([('team_id', '=', merged_data['team_id'])], order='sequence')
            if merged_data.get('stage_id') not in stages.ids:
                merged_data['stage_id'] = stages and stages[0].id
        # Write merged data into first opportunity
        highest.write(merged_data)
        # Delete tail opportunities 
        # We use the SUPERUSER to avoid access rights issues because as the user had the rights to see the records it should be safe to do so
        tail_opportunities.sudo().unlink()

        return highest

    def _convert_opportunity_data(self, customer, team_id=False):
        self.ensure_one()
        if not team_id:
            team_id = self.team_id.id
        val = {
            'planned_revenue': self.planned_revenue,
            'probability': self.probability,
            'name': self.name,
            'partner_id': customer.id,
            'type': 'opportunity',
            'date_open': fields.Datetime.now(),
            'email_from': customer and customer.email or self.email_from,
            'phone': customer and customer.phone or self.phone,
            'date_conversion': fields.Datetime.now(),
        }
        if not self.stage_id:
            val['stage_id'] = self.stage_find(team_id, [])
        return val

    @api.multi
    def convert_opportunity(self, partner_id, user_ids=False, team_id=False):
        for lead in self.filtered(lambda l: l.active or l.probability < 100):
            vals = lead._convert_opportunity_data(partner_id, team_id)
            lead.write(vals)

        if user_ids or team_id:
            self.allocate_salesman(user_ids, team_id)

        return True

    def _lead_create_contact(self, name, is_company, parent=False):
        self.ensure_one()
        vals = {'name': name,
            'user_id': self.user_id.id,
            'comment': self.description,
            'team_id': self.team_id.id,
            'parent_id': parent and parent.id,
            'phone': self.phone,
            'mobile': self.mobile,
            'email': tools.email_split(self.email_from) and tools.email_split(self.email_from)[0] or False,
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
        return self.env['res.partner'].create(vals)

    def _create_lead_partner(self):
        self.ensure_one()
        contact_name = self.contact_name or self.email_from and self.env['res.partner']._parse_partner_name(self.email_from)[0]
        if self.partner_name:
            partner_company = self._lead_create_contact(self.partner_name, True)
        elif self.partner_id:
            partner_company = self.partner_id
        else:
            partner_company = False

        contacts = self._lead_create_contact(contact_name, False, partner_company) if contact_name else False

        return contacts or partner_company or self._lead_create_contact(self.name, False)

    @api.multi
    def handle_partner_assignation(self, action='create', partner=False):
        """
        Handle partner assignation during a lead conversion.
        if action is 'create', create new partner with contact and assign lead to new partner_id.
        otherwise assign lead to the specified partner_id
        :param string action: what has to be done regarding partners (create it, assign an existing one, or nothing)
        :param int partner_id: partner to assign if any
        :return dict: dictionary organized as followed: {lead_id: partner_assigned_id}
        """
        partners = {}
        for lead in self:
            # If the action is set to 'create' and no partner_id is set, create a new one
            if lead.partner_id:
                partners[lead.id] = lead.partner_id.id
            if action == 'create':
                partner = lead._create_lead_partner()
                partner.write({'team_id': lead.team_id.id})
            if partner:
                lead.write({'partner_id': partner.id})
            partners[lead.id] = partner
        return partners

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
            'views': [(form_view.id or False, 'form'),
                      (tree_view.id or False, 'tree'), (False, 'kanban'),
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
            'views': [(form_view.id or False, 'form'),
                      (tree_view.id or False, 'tree'),
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
        partner_ids = self.env.user.partner_id.ids
        if self.partner_id:
            partner_ids.append(self.partner_id.id)
        res['context'] = {
            'search_default_opportunity_id': self.type == 'opportunity' and self.id or False,
            'default_opportunity_id': self.type == 'opportunity' and self.id or False,
            'default_partner_id': self.partner_id.id,
            'default_partner_ids': partner_ids,
            'default_team_id': self.team_id.id,
            'default_name': self.name,
        }
        return res

    @api.model
    def get_empty_list_help(self, help):
        ctx = dict(self.env.context)
        ctx['empty_list_help_model'] = 'crm.team'
        ctx['empty_list_help_id'] = ctx.get('default_team_id', None)
        ctx['empty_list_help_document_name'] = _("opportunities")
        if help:
            alias = self.env.ref("crm.mail_alias_lead_info")
            if alias and alias.alias_domain and alias.alias_name:
                dynamic_help = '<p>%s</p>' % _("""All email incoming to %(link)s  will automatically create new opportunity.
Update your business card, phone book, social media,... Send an email right now and see it here.""") % {
                    'link': "<a href='mailto:%s'>%s</a>" % (alias.alias_name, alias.alias_domain)
                }
                return '<p class="oe_view_nocontent_create">%s</p>%s%s' % (
                    _('Click to add a new opportunity'),
                    help,
                    dynamic_help)
        return super(CrmLead, self.with_context(ctx)).get_empty_list_help(help)

    # ----------------------------------------
    # Mail Gateway
    # ----------------------------------------

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage_id' in init_values and self.probability == 100 and self.stage_id.on_change:
            return 'crm.mt_lead_won'
        elif 'active' in init_values and self.probability == 0 and not self.active:
            return 'crm.mt_lead_lost'
        elif 'stage_id' in init_values and self.stage_id and self.stage_id.sequence <= 1:
            return 'crm.mt_lead_create'
        elif 'stage_id' in init_values:
            return 'crm.mt_lead_stage'
        return super(CrmLead, self)._track_subtype(init_values)

    @api.multi
    def _notification_group_recipients(self, message, recipients, done_ids, group_data):
        """ Override the mail.thread method to handle salesman recipients.
        Indeed those will have specific action in their notification emails. """
        group_sale_salesman = self.env.ref('base.group_sale_salesman')
        for recipient in recipients.filtered(lambda r: r.id not in done_ids):
            if recipient.user_ids and group_sale_salesman.id in recipient.user_ids.mapped('groups_id').ids:
                group_data['group_sale_salesman'] |= recipient
                done_ids.add(recipient.id)
        return super(CrmLead, self)._notification_group_recipients(message, recipients, done_ids, group_data)

    @api.multi
    def _notification_get_recipient_groups(self, message, recipients):
        self.ensure_one()
        res = super(CrmLead, self)._notification_get_recipient_groups(message, recipients)

        won_action = self._notification_link_helper('method', method='case_mark_won')
        lost_action = self._notification_link_helper('method', method='case_mark_lost')
        convert_action = self._notification_link_helper('method', method='convert_opportunity')

        if self.type == 'lead':
            res['group_sale_salesman'] = {
                'actions': [{'url': convert_action, 'title': 'Convert to opportunity'}]
            }
        else:
            res['group_sale_salesman'] = {
                'actions': [
                    {'url': won_action, 'title': 'Won'},
                    {'url': lost_action, 'title': 'Lost'}]
            }
        return res

    @api.model
    def message_get_reply_to(self, ids, default=None):
        """ Override to get the reply_to of the parent project. """
        leads = self.sudo().browse(ids)
        team_ids = set([lead.team_id.id for lead in leads if lead.team_id])
        aliases = self.env['crm.team'].message_get_reply_to(list(team_ids), default=default)
        return dict((lead.id, aliases.get(lead.team_id and lead.team_id.id or 0, False)) for lead in leads)

    @api.multi
    def get_formview_id(self):
        self.ensure_one()
        if self.type == 'opportunity':
            view_id = self.env.ref('crm.crm_case_form_view_oppor').id
        else:
            view_id = super(CrmLead, self).get_formview_id()
        return view_id

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(CrmLead, self).message_get_suggested_recipients()
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
        if priority in dict(crm_stage.AVAILABLE_PRIORITIES):
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
        if update_vals is None:
            update_vals = {}
        if priority in dict(crm_stage.AVAILABLE_PRIORITIES):
            update_vals['priority'] = priority
        maps = {
            'revenue': 'planned_revenue',
            'probability': 'probability',
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
        if not duration:
            duration = _('unknown')
        else:
            duration = str(duration)
        meet_date = fields.Datetime.from_string(meeting_date)
        meeting_usertime = fields.Datetime.to_string(fields.Datetime.context_timestamp(self, meet_date))
        html_time = "<time datetime='%s+00:00'>%s</time>" % (meeting_date, meeting_usertime)
        message = _("Meeting scheduled at '%s'<br> Subject: %s <br> Duration: %s hour(s)") % (html_time, meeting_subject, duration)
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
    def retrieve_sales_dashboard(self):

        res = {
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

        opportunities = self.search_read(
            [('type', '=', 'opportunity'), ('user_id', '=', self.env.uid)],
            ['date_deadline', 'next_activity_id', 'date_action', 'date_closed', 'planned_revenue'])

        current_date = fields.Date.from_string(fields.Date.today())
        for opp in opportunities:

            # Expected closing
            if opp['date_deadline']:
                date_deadline = fields.Date.from_string(opp['date_deadline'])

                if date_deadline == current_date:
                    res['closing']['today'] += 1
                if date_deadline >= current_date and date_deadline <= current_date + timedelta(days=7):
                    res['closing']['next_7_days'] += 1
                if date_deadline < current_date:
                    res['closing']['overdue'] += 1

            # Next activities
            if opp['next_activity_id'] and opp['date_action']:
                date_action = fields.Date.from_string(opp['date_action'])

                if date_action == current_date:
                    res['activity']['today'] += 1
                if date_action >= current_date and date_action <= current_date + timedelta(days=7):
                    res['activity']['next_7_days'] += 1
                if date_action < current_date:
                    res['activity']['overdue'] += 1

            # Won in Opportunities
            if opp['date_closed']:
                date_closed = fields.Date.from_string(opp['date_closed'])

                if date_closed <= current_date and date_closed >= current_date.replace(day=1):
                    if opp['planned_revenue']:
                        res['won']['this_month'] += opp['planned_revenue']
                elif date_closed < current_date.replace(day=1) and date_closed >= current_date.replace(day=1) - relativedelta(months=+1):
                    if opp['planned_revenue']:
                        res['won']['last_month'] += opp['planned_revenue']

        # crm.activity is a very messy model so we need to do that in order to retrieve the actions done.
        self.env.cr.execute("""
            SELECT
                m.id,
                m.subtype_id,
                m.date,
                l.user_id,
                l.type
            FROM
                "mail_message" m
            LEFT JOIN
                "crm_lead" l
            ON
                (m.res_id = l.id)
            INNER JOIN
                "crm_activity" a
            ON
                (m.subtype_id = a.subtype_id)
            WHERE
                (m.model = 'crm.lead') AND (l.user_id = %s) AND (l.type = 'opportunity')
        """, (self.env.uid,))
        activites_done = self.env.cr.dictfetchall()

        for act in activites_done:
            if act['date']:
                date_act = fields.Date.from_string(act['date'])
                if date_act <= current_date and date_act >= current_date.replace(day=1):
                    res['done']['this_month'] += 1
                elif date_act < current_date.replace(day=1) and date_act >= current_date.replace(day=1) - relativedelta(months=+1):
                    res['done']['last_month'] += 1

        # Meetings
        min_date = fields.Datetime.now()
        max_date = fields.Datetime.to_string(fields.Datetime.from_string(fields.Datetime.now()) + timedelta(days=8))
        meetings_domain = [
            ('start', '>=', min_date),
            ('start', '<=', max_date)
        ]
        # We need to add 'mymeetings' in the context for the search to be correct.
        meetings = self.env['calendar.event'].with_context(mymeetings=1).search(meetings_domain)
        for meeting in meetings:
            if meeting['start']:
                start = fields.Date.from_string(meeting.start)

                if start == current_date:
                    res['meeting']['today'] += 1
                if start >= current_date and start <= current_date + timedelta(days=7):
                    res['meeting']['next_7_days'] += 1

        res['nb_opportunities'] = len(opportunities)

        res['done']['target'] = self.env.user.target_sales_done
        res['won']['target'] = self.env.user.target_sales_won

        res['currency_id'] = self.env.user.company_id.currency_id.id

        return res

    @api.model
    def modify_target_sales_dashboard(self, target_name, target_value):

        if target_name in ['won', 'done', 'invoiced']:
            # bypass rights (with superuser_id)
            self.env.user.sudo().write({'target_sales_' + target_name: target_value})
        else:
            raise UserError(_('This target does not exist.'))

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
        # - OR ('fold', '=', False): add default columns that are not folded
        # - OR ('team_ids', '=', team_id), ('fold', '=', False) if team_id: add team columns that are not folded
        team_id = self.env.context.get('default_team_id', False)
        if team_id:
            search_domain = ['|', ('id', 'in', self.ids), '|', ('team_id', '=', False), ('team_id', '=', team_id)]
        else:
            search_domain = ['|', ('id', 'in', self.ids), ('team_id', '=', False)]
        # perform search
        stage_ids = CrmStage._search(search_domain, order=order, access_rights_uid=access_rights_uid)
        stages = CrmStage.sudo(access_rights_uid).browse(stage_ids)
        result = stages.name_get()
        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stages:
            fold[stage.id] = stage.fold or False
        return result, fold

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        opportunity_id = self.env.context.get('opportunity_id')
        if opportunity_id:
            action = self._get_formview_action(opportunity_id)
            if action.get('views') and any(view_id for view_id in action['views'] if view_id[1] == view_type):
                view_id = next(view_id[0] for view_id in action['views'] if view_id[1] == view_type)
        res = super(CrmLead, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            res['arch'] = self.fields_view_get_address(res['arch'])
        return res

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }


class CrmLeadTag(models.Model):
    _name = "crm.lead.tag"
    _description = "Category of lead"

    name = fields.Char(required=True)
    color = fields.Integer(string='Color Index')
    team_id = fields.Many2one('crm.team', string='Sales Team')

    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class CrmLostReason(models.Model):
    _name = "crm.lost.reason"
    _description = 'Reason for loosing leads'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
