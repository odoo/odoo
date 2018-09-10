# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, SUPERUSER_ID
from odoo.tools.translate import _
from odoo.tools import email_re, email_split
from odoo.exceptions import UserError, AccessError

from odoo.addons.base.res.res_partner import FormatAddress

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


class Lead(FormatAddress, models.Model):

    _name = "crm.lead"
    _description = "Lead/Opportunity"
    _order = "priority desc,date_action,id desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin', 'utm.mixin']
    _mail_mass_mailing = _('Leads / Opportunities')

    def _default_probability(self):
        stage_id = self._default_stage_id()
        if stage_id:
            return self.env['crm.stage'].browse(stage_id).probability
        return 10

    def _default_stage_id(self):
        team = self.env['crm.team'].sudo()._get_default_team_id(user_id=self.env.uid)
        return self._stage_find(team_id=team.id, domain=[('fold', '=', False)]).id

    name = fields.Char('Opportunity', required=True, index=True)
    partner_id = fields.Many2one('res.partner', string='Customer', track_visibility='onchange', index=True,
        help="Linked partner (optional). Usually created when converting the lead.")
    active = fields.Boolean('Active', default=True)
    date_action_last = fields.Datetime('Last Action', readonly=True)
    date_action_next = fields.Datetime('Next Action', readonly=True)
    email_from = fields.Char('Email', help="Email address of the contact", index=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id', default=lambda self: self.env['crm.team'].sudo()._get_default_team_id(user_id=self.env.uid),
        index=True, track_visibility='onchange', help='When sending mails, the default email address is taken from the sales team.')
    kanban_state = fields.Selection([('grey', 'No next activity planned'), ('red', 'Next activity late'), ('green', 'Next activity is planned')],
        string='Activity State', compute='_compute_kanban_state')
    email_cc = fields.Text('Global CC', help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma")
    description = fields.Text('Notes')
    create_date = fields.Datetime('Create Date', readonly=True)
    write_date = fields.Datetime('Update Date', readonly=True)
    tag_ids = fields.Many2many('crm.lead.tag', 'crm_lead_tag_rel', 'lead_id', 'tag_id', string='Tags', help="Classify and analyze your lead/opportunity categories like: Training, Service")
    contact_name = fields.Char('Contact Name')
    partner_name = fields.Char("Customer Name", index=True, help='The name of the future partner company that will be created while converting the lead into opportunity')
    opt_out = fields.Boolean(string='Opt-Out', oldname='optout',
        help="If opt-out is checked, this contact has refused to receive emails for mass mailing and marketing campaign. "
             "Filter 'Available for Mass Mailing' allows users to filter the leads when performing mass mailing.")
    type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity')], index=True, required=True,
        default=lambda self: 'lead' if self.env['res.users'].has_group('crm.group_use_lead') else 'opportunity',
        help="Type is used to separate Leads and Opportunities")
    priority = fields.Selection(crm_stage.AVAILABLE_PRIORITIES, string='Rating', index=True, default=crm_stage.AVAILABLE_PRIORITIES[0][0])
    date_closed = fields.Datetime('Closed Date', readonly=True, copy=False)

    stage_id = fields.Many2one('crm.stage', string='Stage', track_visibility='onchange', index=True,
        domain="['|', ('team_id', '=', False), ('team_id', '=', team_id)]",
        group_expand='_read_group_stage_ids', default=lambda self: self._default_stage_id())
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    referred = fields.Char('Referred By')

    date_open = fields.Datetime('Assigned', readonly=True, default=lambda self: fields.Datetime.now())
    day_open = fields.Float(compute='_compute_day_open', string='Days to Assign', store=True)
    day_close = fields.Float(compute='_compute_day_close', string='Days to Close', store=True)
    date_last_stage_update = fields.Datetime(string='Last Stage Update', index=True, default=fields.Datetime.now)
    date_conversion = fields.Datetime('Conversion Date', readonly=True)

    # Messaging and marketing
    message_bounce = fields.Integer('Bounce', help="Counter of the number of bounced emails for this contact")

    # Only used for type opportunity
    probability = fields.Float('Probability', group_operator="avg", default=lambda self: self._default_probability())
    planned_revenue = fields.Float('Expected Revenue', track_visibility='always')
    date_deadline = fields.Date('Expected Closing', help="Estimate of the date on which the opportunity will be won.")

    # CRM Actions
    next_activity_id = fields.Many2one("crm.activity", string="Next Activity", index=True)
    date_action = fields.Date('Next Activity Date', index=True)
    title_action = fields.Char('Next Activity Summary')

    color = fields.Integer('Color Index', default=0)
    partner_address_name = fields.Char('Partner Contact Name', related='partner_id.name', readonly=True)
    partner_address_email = fields.Char('Partner Contact Email', related='partner_id.email', readonly=True)
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
    phone = fields.Char('Phone')
    fax = fields.Char('Fax')
    mobile = fields.Char('Mobile')
    function = fields.Char('Job Position')
    title = fields.Many2one('res.partner.title')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.user.company_id.id)
    meeting_count = fields.Integer('# Meetings', compute='_compute_meeting_count')
    lost_reason = fields.Many2one('crm.lost.reason', string='Lost Reason', index=True, track_visibility='onchange')

    _sql_constraints = [
        ('check_probability', 'check(probability >= 0 and probability <= 100)', 'The probability of closing the deal should be between 0% and 100%!')
    ]

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

    @api.multi
    def _compute_kanban_state(self):
        today = date.today()
        for lead in self:
            kanban_state = 'grey'
            if lead.date_action:
                lead_date = fields.Date.from_string(lead.date_action)
                if lead_date >= today:
                    kanban_state = 'green'
                else:
                    kanban_state = 'red'
            lead.kanban_state = kanban_state

    @api.depends('date_open')
    def _compute_day_open(self):
        """ Compute difference between create date and open date """
        for lead in self.filtered(lambda l: l.date_open):
            date_create = fields.Datetime.from_string(lead.create_date)
            date_open = fields.Datetime.from_string(lead.date_open)
            lead.day_open = abs((date_open - date_create).days)

    @api.depends('date_closed')
    def _compute_day_close(self):
        """ Compute difference between current date and log date """
        for lead in self.filtered(lambda l: l.date_closed):
            date_create = fields.Datetime.from_string(lead.create_date)
            date_close = fields.Datetime.from_string(lead.date_closed)
            lead.day_close = abs((date_close - date_create).days)

    @api.multi
    def _compute_meeting_count(self):
        meeting_data = self.env['calendar.event'].read_group([('opportunity_id', 'in', self.ids)], ['opportunity_id'], ['opportunity_id'])
        mapped_data = {m['opportunity_id'][0]: m['opportunity_id_count'] for m in meeting_data}
        for lead in self:
            lead.meeting_count = mapped_data.get(lead.id, 0)

    @api.model
    def _onchange_stage_id_values(self, stage_id):
        """ returns the new values when stage_id has changed """
        if not stage_id:
            return {}
        stage = self.env['crm.stage'].browse(stage_id)
        if stage.on_change:
            return {'probability': stage.probability}
        return {}

    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        values = self._onchange_stage_id_values(self.stage_id.id)
        self.update(values)

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
                'fax': partner.fax,
                'zip': partner.zip,
                'function': partner.function,
            }
        return {}

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        values = self._onchange_partner_id_values(self.partner_id.id if self.partner_id else False)
        self.update(values)

    @api.model
    def _onchange_user_values(self, user_id):
        """ returns new values when user_id has changed """
        if user_id and self._context.get('team_id'):
            team = self.env['crm.team'].browse(self._context['team_id'])
            if user_id in team.member_ids.ids:
                return {}
        team_id = self.env['crm.team']._get_default_team_id(user_id=user_id)
        return {'team_id': team_id}

    @api.onchange('user_id')
    def _onchange_user_id(self):
        """ When changing the user, also set a team_id or restrict team id to the ones user_id is member of. """
        values = self._onchange_user_values(self.user_id.id)
        self.update(values)

    @api.onchange('state_id')
    def _onchange_state(self):
        if self.state_id:
            self.country_id = self.state_id.country_id.id

    @api.onchange('next_activity_id')
    def _onchange_next_activity_id(self):
        values = {
            'title_action': False,
            'date_action': False,
        }
        if self.next_activity_id:
            values['title_action'] = self.next_activity_id.description
            if self.next_activity_id.days:
                values['date_action'] = fields.Datetime.to_string(datetime.now() + timedelta(days=self.next_activity_id.days))
        self.update(values)

    # ----------------------------------------
    # ORM override (CRUD, fields_view_get, ...)
    # ----------------------------------------

    @api.model
    def name_create(self, name):
        res = super(Lead, self).name_create(name)
        
        # update the probability of the lead if the stage is set to update it automatically
        self.browse(res[0])._onchange_stage_id()
        return res

    @api.model
    def create(self, vals):
        # set up context used to find the lead's sales team which is needed
        # to correctly set the default stage_id
        context = dict(self._context or {})
        if vals.get('type') and not self._context.get('default_type'):
            context['default_type'] = vals.get('type')
        if vals.get('team_id') and not self._context.get('default_team_id'):
            context['default_team_id'] = vals.get('team_id')

        if vals.get('user_id') and 'date_open' not in vals:
            vals['date_open'] = fields.Datetime.now()

        if context.get('default_partner_id') and not vals.get('email_from'):
            partner = self.env['res.partner'].browse(context['default_partner_id'])
            vals['email_from'] = partner.email

        # context: no_log, because subtype already handle this
        return super(Lead, self.with_context(context, mail_create_nolog=True)).create(vals)

    @api.multi
    def write(self, vals):
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.Datetime.now()
        if vals.get('user_id') and 'date_open' not in vals:
            vals['date_open'] = fields.Datetime.now()
        # stage change with new stage: update probability and date_closed
        if vals.get('stage_id') and 'probability' not in vals:
            vals.update(self._onchange_stage_id_values(vals.get('stage_id')))
        if vals.get('probability') >= 100 or not vals.get('active', True):
            vals['date_closed'] = fields.Datetime.now()
        elif 'probability' in vals and vals['probability'] < 100:
            vals['date_closed'] = False
        return super(Lead, self).write(vals)

    @api.multi
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
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if self._context.get('opportunity_id'):
            opportunity = self.browse(self._context['opportunity_id'])
            action = opportunity.get_formview_action()
            if action.get('views') and any(view_id for view_id in action['views'] if view_id[1] == view_type):
                view_id = next(view_id[0] for view_id in action['views'] if view_id[1] == view_type)
        res = super(Lead, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            res['arch'] = self.fields_view_get_address(res['arch'])
        return res

    # ----------------------------------------
    # Actions Methods
    # ----------------------------------------

    @api.multi
    def action_set_lost(self):
        """ Lost semantic: probability = 0, active = False """
        return self.write({'probability': 0, 'active': False})

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
            stage_id = lead._stage_find(domain=[('probability', '=', 100.0), ('on_change', '=', True)])
            lead.write({'stage_id': stage_id.id, 'probability': 100})
        return True

    @api.multi
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
            'search_default_opportunity_id': self.id if self.type == 'opportunity' else False,
            'default_opportunity_id': self.id if self.type == 'opportunity' else False,
            'default_partner_id': self.partner_id.id,
            'default_partner_ids': partner_ids,
            'default_team_id': self.team_id.id,
            'default_name': self.name,
        }
        return action

    @api.multi
    def close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}

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

    @api.multi
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

    @api.multi
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

        def _concat_all(attr, opportunities):
            return '\n\n'.join(filter(None, (opp[attr] for opp in opportunities)))

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
                data[field_name] = _concat_all(field_name, self)  # contact field of all opportunities
            else:
                data[field_name] = _get_first_not_null(field_name, self)

        # define the resulting type ('lead' or 'opportunity')
        data['type'] = self._merge_get_result_type()
        return data

    @api.one
    def _mail_body(self, fields):
        """ generate the message body with the changed values
            :param fields : list of fields to track
            :returns the body of the message for the current crm.lead
        """
        title = "%s : %s\n" % (_('Merged opportunity') if self.type == 'opportunity' else _('Merged lead'), self.name)
        body = [title]
        fields = self.env['ir.model.fields'].search([('name', 'in', fields or []), ('model_id.model', '=', self._name)])
        for field in fields:
            value = getattr(self, field.name, False)
            if field.ttype == 'selection':
                selections = self.fields_get()[field.name]['selection']
                value = next((v[1] for v in selections if v[0] == value), value)
            elif field.ttype == 'many2one':
                if value:
                    value = value.sudo().name_get()[0][1]
            elif field.ttype == 'many2many':
                if value:
                    value = ','.join(
                        val.name_get()[0][1]
                        for val in value.sudo()
                    )
            body.append("%s: %s" % (field.field_description, value or ''))
        return "<br/>".join(body + ['<br/>'])

    @api.multi
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

    @api.multi
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

    @api.multi
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

    @api.multi
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

    @api.multi
    def merge_opportunity(self, user_id=False, team_id=False):
        """ Merge opportunities in one. Different cases of merge:
                - merge leads together = 1 new lead
                - merge at least 1 opp with anything else (lead or opp) = 1 new opp
            The resulting lead/opportunity will be the most important one (based on its confidence level)
            updated with values from other opportunities to merge.
            :param user_id : the id of the saleperson. If not given, will be determined by `_merge_data`.
            :param team : the id of the sales team. If not given, will be determined by `_merge_data`.
            :return crm.lead record resulting of th merge
        """
        if len(self.ids) <= 1:
            raise UserError(_('Please select more than one element (lead or opportunity) from the list view.'))

        # Sorting the leads/opps according to the confidence level of its stage, which relates to the probability of winning it
        # The confidence level increases with the stage sequence, except when the stage probability is 0.0 (Lost cases)
        # An Opportunity always has higher confidence level than a lead, unless its stage probability is 0.0
        def opps_key(opportunity):
            sequence = -1
            if opportunity.stage_id.on_change:
                sequence = opportunity.stage_id.sequence
            return (sequence != -1 and opportunity.type == 'opportunity'), sequence, -opportunity.id
        opportunities = self.sorted(key=opps_key, reverse=True)

        # get SORTED recordset of head and tail, and complete list
        opportunities_head = opportunities[0]
        opportunities_tail = opportunities[1:]

        # merge all the sorted opportunity. This means the value of
        # the first (head opp) will be a priority.
        merged_data = opportunities._merge_data(list(CRM_LEAD_FIELDS_TO_MERGE))

        # force value for saleperson and sales team
        if user_id:
            merged_data['user_id'] = user_id
        if team_id:
            merged_data['team_id'] = team_id

        # merge other data (mail.message, attachments, ...) from tail into head
        opportunities_head.merge_dependences(opportunities_tail)

        # check if the stage is in the stages of the sales team. If not, assign the stage with the lowest sequence
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

    @api.multi
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
        partner_match_domain = ['|'] * (len(partner_match_domain) - 1) + partner_match_domain
        if not partner_match_domain:
            return self.env['crm.lead']
        domain = partner_match_domain
        if not include_lost:
            domain += ['&', ('active', '=', True), ('probability', '<', 100)]
        return self.search(domain)

    @api.multi
    def _convert_opportunity_data(self, customer, team_id=False):
        """ Extract the data from a lead to create the opportunity
            :param customer : res.partner record
            :param team_id : identifier of the sales team to determine the stage
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
            if stage:
                value['probability'] = stage.probability
        return value

    @api.multi
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

    @api.multi
    def _lead_create_contact(self, name, is_company, parent_id=False):
        """ extract data from lead to create a partner
            :param name : furtur name of the partner
            :param is_company : True if the partner is a company
            :param parent_id : id of the parent partner (False if no parent)
            :returns res.partner record
        """
        email_split = tools.email_split(self.email_from)
        values = {
            'name': name,
            'user_id': self.env.context.get('default_user_id') or self.user_id.id,
            'comment': self.description,
            'team_id': self.team_id.id,
            'parent_id': parent_id,
            'phone': self.phone,
            'mobile': self.mobile,
            'email': email_split[0] if email_split else False,
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
        return self.env['res.partner'].create(values)

    @api.multi
    def _create_lead_partner(self):
        """ Create a partner from lead data
            :returns res.partner record
        """
        contact_name = self.contact_name
        if not contact_name:
            contact_name = self.env['res.partner']._parse_partner_name(self.email_from)[0] if self.email_from else False

        if self.partner_name:
            partner_company = self._lead_create_contact(self.partner_name, True)
        elif self.partner_id:
            partner_company = self.partner_id
        else:
            partner_company = None

        if contact_name:
            return self._lead_create_contact(contact_name, False, partner_company.id if partner_company else False)

        if partner_company:
            return partner_company
        return self._lead_create_contact(self.name, False)

    @api.multi
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
            if lead.partner_id:
                partner_ids[lead.id] = lead.partner_id.id
                continue
            if action == 'create':
                partner = lead._create_lead_partner()
                partner_id = partner.id
                partner.team_id = lead.team_id
            if partner_id:
                lead.partner_id = partner_id
            partner_ids[lead.id] = partner_id
        return partner_ids

    @api.multi
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

    @api.multi
    def redirect_opportunity_view(self):
        self.ensure_one()
        # Get opportunity views
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
            'views': [
                (form_view.id, 'form'),
                (tree_view.id, 'tree'),
                (False, 'kanban'),
                (False, 'calendar'),
                (False, 'graph')
            ],
            'type': 'ir.actions.act_window',
            'context': {'default_type': 'opportunity'}
        }

    @api.multi
    def redirect_lead_view(self):
        self.ensure_one()
        # Get lead views
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
            'views': [
                (form_view.id, 'form'),
                (tree_view.id, 'tree'),
                (False, 'calendar'),
                (False, 'graph')
            ],
            'type': 'ir.actions.act_window',
        }

    @api.model
    def get_empty_list_help(self, help):
        if help:
            alias_record = self.env.ref("crm.mail_alias_lead_info", raise_if_not_found=False)
            if alias_record and alias_record.alias_domain and alias_record.alias_name:
                email = '%s@%s' % (alias_record.alias_name, alias_record.alias_domain)
                email_link = "<a href='mailto:%s'>%s</a>" % (email, email)
                dynamic_help = _("""All email incoming to %s will automatically
                    create new opportunity. Update your business card, phone book, social media,...
                    Send an email right now and see it here.""") % (email_link,)
                return '<p class="oe_view_nocontent_create">%s</p>%s<p>%s</p>' % (_('Click to add a new opportunity'), help, dynamic_help)
        return super(Lead, self.with_context(
            empty_list_help_model='crm.team',
            empty_list_help_id=self._context.get('default_team_id', False),
            empty_list_help_document_name=_("opportunities"),
        )).get_empty_list_help(help)

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
            if opp.date_deadline:
                date_deadline = fields.Date.from_string(opp.date_deadline)
                if date_deadline == today:
                    result['closing']['today'] += 1
                if today <= date_deadline <= today + timedelta(days=7):
                    result['closing']['next_7_days'] += 1
                if date_deadline < today and not opp.date_closed:
                    result['closing']['overdue'] += 1
            # Next activities
            if opp.next_activity_id and opp.date_action:
                date_action = fields.Date.from_string(opp.date_action)
                if date_action == today:
                    result['activity']['today'] += 1
                if today <= date_action <= today + timedelta(days=7):
                    result['activity']['next_7_days'] += 1
                if date_action < today and not opp.date_closed:
                    result['activity']['overdue'] += 1
            # Won in Opportunities
            if opp.date_closed:
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
                m.id,
                m.subtype_id,
                m.date,
                l.user_id,
                l.type
            FROM mail_message M
                LEFT JOIN crm_lead L ON (M.res_id = L.id)
                INNER JOIN crm_activity A ON (M.subtype_id = A.subtype_id)
            WHERE
                (M.model = 'crm.lead') AND (L.user_id = %s) AND (L.type = 'opportunity')
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
                start = datetime.strptime(meeting['start'], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
                if start == today:
                    result['meeting']['today'] += 1
                if today <= start <= today + timedelta(days=7):
                    result['meeting']['next_7_days'] += 1

        result['done']['target'] = self.env.user.target_sales_done
        result['won']['target'] = self.env.user.target_sales_won
        result['currency_id'] = self.env.user.company_id.currency_id.id

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

    @api.multi
    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage_id' in init_values and self.probability == 100 and self.stage_id and self.stage_id.on_change:
            return 'crm.mt_lead_won'
        elif 'active' in init_values and self.probability == 0 and not self.active:
            return 'crm.mt_lead_lost'
        elif 'stage_id' in init_values and self.stage_id and self.stage_id.sequence <= 1:
            return 'crm.mt_lead_create'
        elif 'stage_id' in init_values:
            return 'crm.mt_lead_stage'
        return super(Lead, self)._track_subtype(init_values)

    @api.multi
    def _notification_recipients(self, message, groups):
        """ Handle salesman recipients that can convert leads into opportunities
        and set opportunities as won / lost. """
        groups = super(Lead, self)._notification_recipients(message, groups)

        self.ensure_one()
        if self.type == 'lead':
            convert_action = self._notification_link_helper('controller', controller='/lead/convert')
            salesman_actions = [{'url': convert_action, 'title': _('Convert to opportunity')}]
        else:
            won_action = self._notification_link_helper('controller', controller='/lead/case_mark_won')
            lost_action = self._notification_link_helper('controller', controller='/lead/case_mark_lost')
            salesman_actions = [
                {'url': won_action, 'title': _('Won')},
                {'url': lost_action, 'title': _('Lost')}]

        new_group = (
            'group_sale_salesman', lambda partner: bool(partner.user_ids) and any(user.has_group('sales_team.group_sale_salesman') for user in partner.user_ids), {
                'actions': salesman_actions,
            })

        return [new_group] + groups

    @api.model
    def message_get_reply_to(self, res_ids, default=None):
        leads = self.sudo().browse(res_ids)
        aliases = self.env['crm.team'].message_get_reply_to(leads.mapped('team_id').ids, default=default)
        return {lead.id: aliases.get(lead.team_id.id or 0, False) for lead in leads}

    @api.multi
    def get_formview_id(self):
        if self.type == 'opportunity':
            view_id = self.env.ref('crm.crm_case_form_view_oppor').id
        else:
            view_id = super(Lead, self).get_formview_id()
        return view_id

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(Lead, self).message_get_suggested_recipients()
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
        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        self = self.with_context(default_user_id=False)

        if custom_values is None:
            custom_values = {}
        defaults = {
            'name':  msg_dict.get('subject') or _("No Subject"),
            'email_from': msg_dict.get('from'),
            'email_cc': msg_dict.get('cc'),
            'partner_id': msg_dict.get('author_id', False),
        }
        if msg_dict.get('author_id'):
            defaults.update(self._onchange_partner_id_values(msg_dict.get('author_id')))
        if msg_dict.get('priority') in dict(crm_stage.AVAILABLE_PRIORITIES):
            defaults['priority'] = msg_dict.get('priority')
        defaults.update(custom_values)
        return super(Lead, self).message_new(msg_dict, custom_values=defaults)

    @api.multi
    def message_update(self, msg_dict, update_vals=None):
        """ Overrides mail_thread message_update that is called by the mailgateway
            through message_process.
            This method updates the document according to the email.
        """
        if update_vals is None:
            update_vals = {}
        if msg_dict.get('priority') in dict(crm_stage.AVAILABLE_PRIORITIES):
            update_vals['priority'] = msg_dict.get('priority')
        maps = {
            'revenue': 'planned_revenue',
            'probability': 'probability',
        }
        for line in msg_dict.get('body', '').split('\n'):
            line = line.strip()
            res = tools.command_re.match(line)
            if res and maps.get(res.group(1).lower()):
                key = maps.get(res.group(1).lower())
                update_vals[key] = res.group(2).lower()
        return super(Lead, self).message_update(msg_dict, update_vals=update_vals)

    @api.multi
    def message_partner_info_from_emails(self, emails, link_mail=False):
        result = super(Lead, self).message_partner_info_from_emails(emails, link_mail=link_mail)
        for partner_info in result:
            if not partner_info.get('partner_id') and (self.partner_name or self.contact_name):
                emails = email_re.findall(partner_info['full_name'] or '')
                email = emails and emails[0] or ''
                if email and self.email_from and email.lower() == self.email_from.lower():
                    partner_info['full_name'] = '%s <%s>' % (self.partner_name or self.contact_name, email)
                    break
        return result


class Tag(models.Model):

    _name = "crm.lead.tag"
    _description = "Category of lead"

    name = fields.Char('Name', required=True, translate=True)
    color = fields.Integer('Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class LostReason(models.Model):
    _name = "crm.lost.reason"
    _description = 'Reason for loosing leads'

    name = fields.Char('Name', required=True, translate=True)
    active = fields.Boolean('Active', default=True)
