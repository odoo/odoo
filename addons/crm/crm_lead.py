# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import crm
from datetime import datetime
from operator import itemgetter

import openerp
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.addons.base.res.res_partner import format_address
from openerp import models, api, fields, _
from openerp.tools import email_re, email_split


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

class crm_lead(format_address, models.Model):
    """ CRM Lead Case """
    _name = "crm.lead"
    _description = "Lead/Opportunity"
    _order = "priority desc,date_action,id desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin', 'crm.tracking.mixin']

    _track = {
        'stage_id': {
            # this is only an heuristics; depending on your particular stage configuration it may not match all 'new' stages
            'crm.mt_lead_create': lambda self, cr, uid, obj, ctx=None: obj.probability == 0 and obj.stage_id and obj.stage_id.sequence <= 1,
            'crm.mt_lead_stage': lambda self, cr, uid, obj, ctx=None: (obj.stage_id and obj.stage_id.sequence > 1) and obj.probability < 100,
            'crm.mt_lead_won': lambda self, cr, uid, obj, ctx=None: obj.probability == 100 and obj.stage_id and obj.stage_id.fold,
            'crm.mt_lead_lost': lambda self, cr, uid, obj, ctx=None: obj.probability == 0 and obj.stage_id and obj.stage_id.fold and obj.stage_id.sequence > 1,
        },
    }
    _mail_mass_mailing = _('Leads / Opportunities')

    @api.model
    def get_empty_list_help(self, help):
        if self._context.get('default_type') == 'lead':
            self = self.with_context(
                empty_list_help_model='crm.team',
                empty_list_help_id=self._context.get('default_team_id'))
        self = self.with_context(empty_list_help_document_name = _("leads"))
        return super(crm_lead, self).get_empty_list_help(help)

    @api.multi
    def _resolve_team_id_from_context(self):
        """ Returns ID of team based on the value of 'team_id'
            context key, or None if it cannot be resolved to a single
            Sales Team.
        """
        context = self._context or {}
        if type(context.get('default_team_id')) in (int, long):
            return context.get('default_team_id')
        if isinstance(context.get('default_team_id'), basestring):
            team_ids = self.env['crm.team'].name_search(name=context['default_team_id'])
            if len(team_ids) == 1:
                return int(team_ids[0][0])
        return None

    @api.multi
    def _get_default_team_id(self, user_id=False):
        """ Gives default team by checking if present in the context """
        team_id = self._resolve_team_id_from_context() or False
        return team_id

    @api.multi
    def _get_default_stage_id(self):
        """ Gives default stage_id """
        team_id = self._get_default_team_id()
        return self.stage_find([], team_id, [('fold', '=', False)])

    @api.multi
    def _resolve_type_from_context(self):
        """ Returns the type (lead or opportunity) from the type context
            key. Returns None if it cannot be resolved.
        """
        return self._context.get('default_type')

    @api.multi
    def _read_group_stage_ids(self, domain, read_group_order=None, access_rights_uid=None):
        access_rights_uid = access_rights_uid or self._uid
        stage_obj = self.env['crm.stage']
        order = stage_obj._order
        # lame hack to allow reverting search, should just work in the trivial case
        if read_group_order == 'stage_id desc':
            order = "%s desc" % order
        # retrieve team_id from the context and write the domain
        # - ('id', 'in', 'ids'): add columns that should be present
        # - OR ('case_default', '=', True), ('fold', '=', False): add default columns that are not folded
        # - OR ('team_ids', '=', team_id), ('fold', '=', False) if team_id: add team columns that are not folded
        search_domain = []
        team_id = self._resolve_team_id_from_context()
        if team_id:
            search_domain += ['|', ('team_ids', '=', team_id)]
            search_domain += [('id', 'in', self._ids)]
        else:
            search_domain += ['|', ('id', 'in', self._ids), ('case_default', '=', True)]
        # retrieve type from the context (if set: choose 'type' or 'both')
        type = self._resolve_type_from_context()
        if type:
            search_domain += ['|', ('type', '=', type), ('type', '=', 'both')]
        # perform search
        stage_ids = stage_obj._search(search_domain, order=order, access_rights_uid=access_rights_uid)
        stage_rec = stage_obj.browse(stage_ids)
        result = stage_rec.name_get()
        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))
        fold = {}
        for stage in stage_rec:
            fold[stage.id] = stage.fold or False
        return result, fold

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if self._context.get('opportunity_id'):
            action = self._get_formview_action(self._context['opportunity_id'])
            if action.get('views') and any(view_id for view_id in action['views'] if view_id[1] == view_type):
                view_id = next(view_id[0] for view_id in action['views'] if view_id[1] == view_type)
        res = super(crm_lead, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            res['arch'] = self.fields_view_get_address(res['arch'])
        return res

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    @api.one
    @api.depends('day_open')
    def _compute_day_open(self):
        for lead in self:
            lead.day_open=""
            for field in self._fields:
                duration = 0
                day_open_ans = False
                if field == 'day_open':
                    if lead.date_open:
                        date_create = datetime.strptime(lead.create_date, "%Y-%m-%d %H:%M:%S")
                        date_open = datetime.strptime(lead.date_open, "%Y-%m-%d %H:%M:%S")
                        day_open_ans = date_open - date_create
                        duration = abs(int(day_open_ans.days))
                        lead.day_open = duration

    @api.one
    @api.depends('day_close')
    def _compute_day_close(self):
        for lead in self:
            lead.day_close=""
            for field in self._fields:
                duration = 0
                day_close_ans = False
                if field == 'day_close':
                    if lead.date_closed:
                        date_create = datetime.strptime(lead.create_date, "%Y-%m-%d %H:%M:%S")
                        date_close = datetime.strptime(lead.date_closed, "%Y-%m-%d %H:%M:%S")
                        day_close_ans = date_close - date_create
                        duration = abs(int(day_close_ans.days))
                        lead.day_close = duration

    @api.one
    @api.depends('meeting_count')
    def _meeting_count(self):
        event = self.pool['calendar.event']
        self.meeting_count = event.search_count(self._cr, self._uid, [('opportunity_id','=',self._ids)])


    partner_id = fields.Many2one('res.partner', 'Partner', 
        ondelete='set null', track_visibility='onchange',
        select=True, help="Linked partner (optional). Usually created when converting the lead.")
    id = fields.Integer('ID', readonly=True)
    name = fields.Char('Opportunity', required=True, select=1)
    active = fields.Boolean('Active', required=False, default=1)
    email_from = fields.Char('Email', size=128, help="Email address of the contact", select=1)
    team_id = fields.Many2one('crm.team', 'Sales Team',
        select=True, 
        track_visibility='onchange', 
        help='When sending mails, the default email address is taken from the sales team.',
        default=lambda self:self._get_default_team_id())
    email_cc = fields.Text('Global CC', help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma")
    description = fields.Text('Notes')
    write_date = fields.Datetime('Update Date', readonly=True)
    tag_ids = fields.Many2many(comodel_name='crm.lead.tag', relation='crm_lead_tag_rel', 
        column1='lead_id', column2='tag_id', string='Tags',help="Classify and analyze your lead/opportunity categories like: Training, Service")
    contact_name = fields.Char('Contact Name', size=64)
    partner_name = fields.Char("Customer Name", size=64,help='The name of the future partner company that will be created while converting the lead into opportunity', select=1)
    opt_out = fields.Boolean('Opt-Out', oldname='optout',
        help="If opt-out is checked, this contact has refused to receive emails for mass mailing and marketing campaign. "
                "Filter 'Available for Mass Mailing' allows users to filter the leads when performing mass mailing.")
    type = fields.Selection([ ('lead','Lead'), ('opportunity','Opportunity'), ],'Type', select=True, help="Type is used to separate Leads and Opportunities", default='lead')
    priority = fields.Selection(crm.AVAILABLE_PRIORITIES, 'Priority', select=True, 
        default=lambda *a: crm.AVAILABLE_PRIORITIES[0][0])
    stage_id = fields.Many2one('crm.stage', 'Stage', 
      track_visibility='onchange', 
      select=True,
      domain="['&', ('team_ids', '=', team_id), '|', ('type', '=', type), ('type', '=', 'both')]",
      default=lambda s:s._get_default_stage_id())
    user_id = fields.Many2one('res.users', 'Salesperson', select=True, 
        track_visibility='onchange',
        default=lambda self:self._uid)
    referred = fields.Char('Referred By')
    create_date = fields.Datetime('Creation Date', readonly=True)
    date_action_last = fields.Datetime('Last Action', readonly=1)
    date_action_next = fields.Datetime('Next Action', readonly=1)
    date_open = fields.Datetime('Assigned', readonly=True)
    date_closed = fields.Datetime('Closed', readonly=True)#copy=False
    date_last_stage_update = fields.Datetime('Last Stage Update', select=True,
        default=fields.datetime.now())
    day_open = fields.Float(compute='_compute_day_open', string='Days to Assign', store=True)
    day_close = fields.Float(compute='_compute_day_close', string='Days to Close', store=True)

    # Messaging and marketing
    message_bounce = fields.Integer('Bounce')
    # Only used for type opportunity
    probability = fields.Float('Success Rate (%)', group_operator="avg")
    planned_revenue = fields.Float('Expected Revenue', track_visibility='always')
    ref = fields.Reference(string='Reference', selection='referencable_models')
    ref2 = fields.Reference(string='Reference2', selection='referencable_models')
    company_currency = fields.Many2one(comodel_name='res.currency', related='company_id.currency_id', string='Currency', store=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', select=True, default=lambda self: self.env['res.company']._company_default_get('crm.lead'))
    phone = fields.Char("Phone", size=64)
    date_deadline = fields.Date('Expected Closing', help="Estimate of the date on which the opportunity will be won.")
    date_action = fields.Date('Next Action Date', select=True)
    title_action = fields.Char('Next Action')
    color = fields.Integer('Color Index', default=0)
    partner_address_name = fields.Char(related='partner_id.name', string='Partner Contact Name', readonly=True)
    partner_address_email = fields.Char(related='partner_id.email', string='Partner Contact Email', readonly=True)

    user_email = fields.Char(related='user_id.email', string='User Email', readonly=True)
    user_login = fields.Char(related='user_id.login', string='User Login', readonly=True)

    # Fields for address, due to separation from crm and res.partner
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    zip = fields.Char('Zip', change_default=True, size=24)
    city = fields.Char('City')
    state_id = fields.Many2one("res.country.state", 'State')
    country_id = fields.Many2one('res.country', 'Country')
    phone = fields.Char('Phone')
    fax = fields.Char('Fax')
    mobile = fields.Char('Mobile')
    function = fields.Char('Function')
    title = fields.Many2one('res.partner.title', 'Title')
    planned_cost = fields.Float('Planned Costs')
    meeting_count = fields.Integer(compute='_meeting_count', string='# Meetings')

    _sql_constraints = [
        ('check_probability', 'check(probability >= 0 and probability <= 100)', 'The probability of closing the deal should be between 0% and 100%!')
    ]

    @api.model
    def referencable_models(self):
        obj = self.pool['res.request.link']
        res = obj.search_read(self._cr, self._uid, [], context=self._context)
        # res = obj.read(self._cr, self._uid, ids, ['object', 'name'], self._context)
        return [(r['object'], r['name']) for r in res]

    @api.one
    @api.onchange('stage_id')
    def onchange_stage_id(self, stage_id=False):
        if not stage_id:
            return
        stage = self.pool['crm.stage'].browse(self._cr, self._uid, stage_id, context=self._context)
        if not stage.on_change:
            return
        self.probability = stage.probability
        if stage.probability >= 100 or (stage.probability == 0 and stage.sequence > 1):
                self.date_closed = fields.datetime.now()

    @api.onchange('partner_id')
    def on_change_partner_id(self):
        partner = self.partner_id

        self.partner_name = partner.parent_id.name if partner.parent_id else partner.name
        self.contact_name = partner.name if partner.parent_id else False
        self.street = partner.street
        self.street2 = partner.street2
        self.city = partner.city
        self.state_id = partner.state_id and partner.state_id.id or False
        self.country_id = partner.country_id and partner.country_id.id or False
        self.email_from = partner.email
        self.phone = partner.phone
        self.mobile = partner.mobile
        self.fax = partner.fax
        self.zip = partner.zip

    @api.onchange('user_id')
    def on_change_user(self):
        print"*/*/*/*/ on_change_user */*/*/ crm_lead.py"
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of. """
        team_id = self._get_default_team_id()
        if self.user_id and not team_id:
            team_ids = self.env['crm.team'].search(['|', ('user_id', '=', self.user_id.id), ('member_ids', '=', self.user_id.id)])
            if team_ids:
                team_id = team_ids[0].id
        print"--team_id : ",team_id
        self.team_id = team_id
        print"*/*/*/*/ END on_change_user */*/*/ crm_lead.py"

    @api.multi
    def stage_find(self, cases, team_id, domain=None, order='sequence'):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - type: stage type must be the same or 'both'
            - team_id: if set, stages must belong to this team or
              be a default stage; if not set, stages must be default
              stages
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cr, uid, cases, context=context)
        # check whether we should try to add a condition on type
        avoid_add_type_term = any([term for term in domain if len(term) == 3 if term[0] == 'type'])
        # collect all team_ids
        team_ids = set()
        types = ['both']
        if not cases and self._context.get('default_type'):
            ctx_type = self._context.get('default_type')
            types += [ctx_type]
        if team_id:
            team_ids.add(team_id)
        for lead in cases:
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
        stage_ids = self.env['crm.stage'].search(search_domain, order=order, limit=1)
        if stage_ids:
            return stage_ids[0].id
        return False

    @api.multi
    def case_mark_lost(self):
        """ Mark the case as lost: state=cancel and probability=0
        """
        stages_leads = {}
        for lead in self:
            stage_id = self.stage_find([lead], lead.team_id.id or False, [('probability', '=', 0.0), ('fold', '=', True), ('sequence', '>', 1)])
            if stage_id:
                if stages_leads.get(stage_id):
                    stages_leads[stage_id].append(lead.id)
                else:
                    stages_leads[stage_id] = [lead.id]
            else:
                raise Warning(_('To relieve your sales pipe and group all Lost opportunities, configure one of your sales stage as follow:\n'
                        'probability = 0 %, select "Change Probability Automatically".\n'
                        'Create a specific stage or edit an existing one by editing columns of your opportunity pipe.'))
        for stage_id, lead_ids in stages_leads.items():
            self.write({'stage_id': stage_id})
        return True

    @api.multi
    def case_mark_won(self):
        """ Mark the case as won: state=done and probability=100
        """
        stages_leads = {}
        for lead in self:
            stage_id = self.stage_find([lead], lead.team_id.id or False, [('probability', '=', 100.0), ('fold', '=', True)])
            if stage_id:
                if stages_leads.get(stage_id):
                    stages_leads[stage_id].append(lead.id)
                else:
                    stages_leads[stage_id] = [lead.id]
            else:
                raise Warning(_('To relieve your sales pipe and group all Won opportunities, configure one of your sales stage as follow:\n'
                        'probability = 100 % and select "Change Probability Automatically".\n'
                        'Create a specific stage or edit an existing one by editing columns of your opportunity pipe.'))
        for stage_id, lead_ids in stages_leads.items():
            self.write({'stage_id': stage_id})
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
                raise Warning (_("You are already at the top level of your sales-team category.\nTherefore you cannot escalate furthermore."))
            case.write(data)
        return True

    @api.multi
    def _merge_get_result_type(self, opportunities=False):
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
        ###print"*/*/*/*/ in _merge_get_result_type */*/*/"
        ###print"----self : ",self
        ###print"----opportunities : ",opportunities
        for opp in opportunities:
            if (opp.type == 'opportunity'):
                return 'opportunity'
        return 'lead'

    @api.multi
    def _merge_data(self, opportunities, fields):
        """
        Prepare lead/opp data into a dictionary for merging.  Different types
        of fields are processed in different ways:
        - text: all the values are concatenated
        - m2m and o2m: those fields aren't processed
        - m2o: the first not null value prevails (the other are dropped)
        - any other type of field: same as m2o

        :param list ids: list of ids of the leads to process
        :param list fields: list of leads' fields to process
        :return dict data: contains the merged values
        """
        print"*/*/*/*/ in merged_data */*/*/"
        print"----self : ",opportunities
        def _get_first_not_null(attr):
            for opp in opportunities:
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
        print"------------data--------"
        for field_name in fields:
            field_info = self._all_columns.get(field_name)
            print data
            if field_info is None:
                continue
            field = field_info.column
            if field._type in ('many2many', 'one2many'):
                continue
            elif field._type == 'many2one':
                data[field_name] = _get_first_not_null_id(field_name)  # !!
            elif field._type == 'text':
                data[field_name] = _concat_all(field_name)  #not lost
            else:
                data[field_name] = _get_first_not_null(field_name)  #not lost
        print"------------data--------"
        # print data
        # Define the resulting type ('lead' or 'opportunity')
        data['type'] = self._merge_get_result_type(opportunities)
        return data


    @api.multi
    def _mail_body(self, fields, title=False):
        body = []
        if title:
            body.append("%s\n" % (title))

        for field_name in fields:
            field_info = self._all_columns.get(field_name)
            if field_info is None:
                continue
            field = field_info.column
            value = ''
            if field._type == 'selection':
                if hasattr(field.selection, '__call__'):
                    key = field.selection(self, cr, uid, context=context)
                else:
                    key = field.selection
                value = dict(key).get(self[field_name], self[field_name])
            elif field._type == 'many2one':
                if self[field_name]:
                    value = self[field_name].name_get()[0][1]
            elif field._type == 'many2many':
                if self[field_name]:
                    for val in self[field_name]:
                        field_value = val.name_get()[0][1]
                        value += field_value + ","
            else:
                value = self[field_name]

            body.append("%s: %s" % (field.string, value or ''))
        return "<br/>".join(body + ['<br/>'])

    @api.multi
    def _merge_notify(self, opportunities):
        """
        Create a message gathering merged leads/opps information.
        """
        ###print"------- _merge_notify-----------"
        ###print"----opportunity_id : ",self
        ###print"----opportunity : ",opportunities
        #TOFIX: mail template should be used instead of fix body, subject text
        details = []
        result_type = self._merge_get_result_type(opportunities)
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
        data= self.message_post(body=details, subject=subject)
        return data

    @api.multi
    def _merge_opportunity_history(self, opportunities):
        ###print"------ _merge_opportunity_history-----"
        ###print"--opportunity_id : ",self.ids[0]
        ###print"--opportunities : ",opportunities
        message = self.env['mail.message']
        for opportunity in opportunities:
            for history in opportunity.message_ids:
                history.write({
                        'res_id': self._ids[0],
                        'subject' : _("From %s : %s") % (opportunity.name, history.subject)
                })

        return True

    @api.multi
    def _merge_opportunity_attachments(self, opportunities):
        ###print"------ _merge_opportunity_attachments-----"
        ###print"--opportunity_id : ",self
        ###print"--opportunities : ",opportunities
        attach_obj = self.pool['ir.attachment']
        # return attachments of opportunity
        def _get_attachments(opportunity_id):
            attachment_ids = attach_obj.search(self._cr, self._uid, [('res_model', '=', self._name), ('res_id', '=', opportunity_id)])
            return attachment_ids
        first_attachments = _get_attachments(self._ids[0])
        #counter of all attachments to move. Used to make sure the name is different for all attachments
        count = 1
        for opportunity in opportunities:
            attachments = _get_attachments(opportunity.id)
            for attachment in attachments:
                values = {'res_id': self._ids[0],}
                for attachment_in_first in first_attachments:
                    if attachment.name == attachment_in_first.name:
                        values['name'] = "%s (%s)" % (attachment.name, count,),
                count+=1
                attachment.write(values)
        return True

    @api.multi
    def _merge_opportunity_phonecalls(self, opportunities):
        phonecall_obj = self.env['crm.phonecall']
        for opportunity in opportunities:
            for phonecall_id in phonecall_obj.search([('opportunity_id', '=', opportunity.id)]):
                phonecall_id.write({'opportunity_id': self._ids[0]})
        return True

    @api.multi
    def get_duplicated_leads(self, partner_id, include_lost=False):
        """
        Search for opportunities that have the same partner and that arent done or cancelled
        """
        ###print"*/*/*/*/*/*/* need to check what is in lead : ",self
        lead = self[0]
        email = lead.partner_id and lead.partner_id.email or lead.email_from
        return self.env['crm.lead']._get_duplicated_leads_by_emails(partner_id, email, include_lost=include_lost)

    @api.multi
    def _get_duplicated_leads_by_emails(self, partner_id, email, include_lost=False):
        """
        Search for opportunities that have   the same partner and that arent done or cancelled
        """
        #print"***** _get_duplicated_leads_by_emails****cl"
        #print"----partner_id : ",partner_id
        final_stage_domain = [('stage_id.probability', '<', 100), '|', ('stage_id.probability', '>', 0), ('stage_id.sequence', '<=', 1)]
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
        #print"***** _get_duplicated_leads_by_emails****cl"
        return self.search(domain)

    @api.multi
    def merge_dependences(self, opportunities):
        ###print"-----in merge_dependences-----"
        ###print"--highest : ",self
        ###print"--opportunities : ",opportunities
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

        :param list ids: leads/opportunities ids to merge
        :return int id: id of the resulting lead/opp
        """
        print"----user_id : ",user_id
        print"----team_id : ",team_id
        if len(self) <= 1:
            raise Warning(_('Please select more than one element (lead or opportunity) from the list view.'))
        sequenced_opps = []
        ###print"*/*/ids : ",self._ids
        ###print"*/*/opportunities : ",self

        # Sorting the leads/opps according to the confidence level of its stage, which relates to the probability of winning it
        # The confidence level increases with the stage sequence, except when the stage probability is 0.0 (Lost cases)
        # An Opportunity always has higher confidence level than a lead, unless its stage probability is 0.0
        for opportunity in self:
            sequence = -1
            if opportunity.stage_id and not opportunity.stage_id.fold:
                sequence = opportunity.stage_id.sequence
            sequenced_opps.append(((int(sequence != -1 and opportunity.type == 'opportunity'), sequence, -opportunity.id), opportunity))

        sequenced_opps.sort(reverse=True)
        print"----------------sequenced_opps : ",sequenced_opps
        opportunities = map(itemgetter(1), sequenced_opps)
        ###print"opportunities : ",opportunities
        highest = opportunities[0]
        ###print"highest : ",highest
        opportunities_rest = opportunities[1:]
        ###print"opportunities_rest : ",opportunities_rest
        tail_opportunities = opportunities_rest
        ###print"tail_opportunities : ",tail_opportunities
        fields = list(CRM_LEAD_FIELDS_TO_MERGE)
        merged_data = self._merge_data(opportunities, fields)
        ###print"merged_data : ",merged_data
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
            team_stage_ids = self.pool['crm.stage'].search(self._cr, self._uid, 
                [('team_ids', 'in', merged_data['team_id']), 
                 ('type', '=', merged_data.get('type'))
                 ], order='sequence', context=self._context)
            if merged_data.get('stage_id') not in team_stage_ids:
                merged_data['stage_id'] = team_stage_ids and team_stage_ids[0] or False
        # Write merged data into first opportunity
        print"--------------------merged_data"
        print merged_data
        highest.write(merged_data)
        # Delete tail_opportunities 
        # We use the SUPERUSER to avoid access rights issues because as the user had the rights to see the records it should be safe to do so
        for x in tail_opportunities:
            x.unlink()
        # return opportunities[0].id
        return highest

    @api.multi
    def _convert_opportunity_data(self, customer, team_id=False):
        crm_stage = self.env['crm.stage']
        contact_id = False
        if customer:
            contact_id = self.pool['res.partner'].address_get(self._cr, self._uid,[customer.id])['default']
        if not team_id:
            team_id = self.team_id and self.team_id.id or False
        val = {
            'planned_revenue': self.planned_revenue,
            'probability': self.probability,
            'name': self.name,
            'partner_id': customer and customer.id or False,
            'type': 'opportunity',
            'date_action': fields.datetime.now(),
            'date_open': fields.datetime.now(),
            'email_from': customer and customer.email or self.email_from,
            'phone': customer and customer.phone or self.phone,
        }
        if not self.stage_id or self.stage_id.type=='lead':
            val['stage_id'] = self.stage_find([], team_id, [('type', 'in', ('opportunity', 'both'))])
        return val

    @api.multi
    def convert_opportunity(self, partner_id, user_ids=False, team_id=False):
        customer = False
        if partner_id:
            partner = self.pool['res.partner']
            customer = partner.browse(self._cr, self._uid, partner_id)
        for lead in self:
            # TDE: was if lead.state in ('done', 'cancel'):
            if lead.probability == 100 or (lead.probability == 0 and lead.stage_id.fold):
                continue
            vals = lead._convert_opportunity_data(customer, team_id)
            lead.write(vals)
        if user_ids or team_id:
            self.allocate_salesman(ids, user_ids, team_id)
        return True

    @api.multi
    def _lead_create_contact(self, name, is_company, parent_id=False):
        lead = self[0]
        vals = {'name': name,
            'user_id': lead.user_id.id,
            'comment': lead.description,
            'team_id': lead.team_id.id or False,
            'parent_id': parent_id,
            'phone': lead.phone,
            'mobile': lead.mobile,
            'email': tools.email_split(lead.email_from) and tools.email_split(lead.email_from)[0] or False,
            'fax': lead.fax,
            'title': lead.title and lead.title.id or False,
            'function': lead.function,
            'street': lead.street,
            'street2': lead.street2,
            'zip': lead.zip,
            'city': lead.city,
            'country_id': lead.country_id and lead.country_id.id or False,
            'state_id': lead.state_id and lead.state_id.id or False,
            'is_company': is_company,
            'type': 'contact'
        }
        return self.pool['res.partner'].create(self._cr, self._uid, vals, context=self._context)

    @api.multi
    def _create_lead_partner(self):
        lead = self[0]
        partner_id = False
        if lead.partner_name and lead.contact_name:
            partner_id = lead._lead_create_contact(lead.partner_name, True)
            partner_id = lead._lead_create_contact(lead.contact_name, False, partner_id)
        elif lead.partner_name and not lead.contact_name:
            partner_id = lead._lead_create_contact(lead.partner_name, True)
        elif not lead.partner_name and lead.contact_name:
            partner_id = lead._lead_create_contact(lead.contact_name, False)
        elif lead.email_from and self.pool['res.partner']._parse_partner_name(lead.email_from, context=self._context)[0]:
            contact_name = self.pool['res.partner']._parse_partner_name(lead.email_from, context=self._context)[0]
            partner_id = lead._lead_create_contact(contact_name, False)
        else:
            raise Warning(_('No customer name defined. Please fill one of the following fields: Company Name, Contact Name or Email ("Name <email@address>")')
            )
        return partner_id

    @api.multi
    def handle_partner_assignation(self, ids, action='create', partner_id=False):
        """
        Handle partner assignation during a lead conversion.
        if action is 'create', create new partner with contact and assign lead to new partner_id.
        otherwise assign lead to the specified partner_id

        :param list ids: leads/opportunities ids to process
        :param string action: what has to be done regarding partners (create it, assign an existing one, or nothing)
        :param int partner_id: partner to assign if any
        :return dict: dictionary organized as followed: {lead_id: partner_assigned_id}
        """
        #TODO this is a duplication of the handle_partner_assignation method of crm_phonecall
        partner_ids = {}
        for lead in self.browse(ids):
            # If the action is set to 'create' and no partner_id is set, create a new one
            if lead.partner_id:
                partner_ids[lead.id] = lead.partner_id.id
                continue
            if not partner_id and action == 'create':
                partner_id = lead._create_lead_partner()
                self.pool['res.partner'].write(self._cr, self._uid, partner_id, {'team_id': lead.team_id and lead.team_id.id or False})
            if partner_id:
                lead.write({'partner_id': partner_id}, context=self._context)
            partner_ids[lead.id] = partner_id
        return partner_ids

    @api.multi
    def allocate_salesman(self, ids, user_ids=None, team_id=False):
        """
        Assign salesmen and salesteam to a batch of leads.  If there are more
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
        for lead_id in ids:
            value = {}
            if team_id:
                value['team_id'] = team_id
            if user_ids:
                value['user_id'] = user_ids[index]
                # Cycle through user_ids
                index = (index + 1) % len(user_ids)
            if value:
                self.write(value)
        return True

    @api.multi
    def schedule_phonecall(self, schedule_time, call_summary, desc, phone, contact_name, user_id=False, team_id=False, categ_id=False, action='schedule'):
        """
        :param string action: ('schedule','Schedule a call'), ('log','Log a call')
        """
        phonecall = self.env['crm.phonecall']
        model_data = self.pool['ir.model.data']
        phonecall_dict = {}
        if not categ_id:
            try:
                res_id = model_data._get_id('crm', 'categ_phone2')
                categ_id = model_data.browse(res_id).res_id
            except ValueError:
                pass
        for lead in self:
            if not team_id:
                team_id = lead.team_id and lead.team_id.id or False
            if not user_id:
                user_id = lead.user_id and lead.user_id.id or False
            vals = {
                'name': call_summary,
                'opportunity_id': lead.id,
                'user_id': user_id or False,
                'categ_id': categ_id or False,
                'description': desc or '',
                'date': schedule_time,
                'team_id': team_id or False,
                'partner_id': lead.partner_id and lead.partner_id.id or False,
                'partner_phone': phone or lead.phone or (lead.partner_id and lead.partner_id.phone or False),
                'partner_mobile': lead.partner_id and lead.partner_id.mobile or False,
                'priority': lead.priority,
            }
            new_rec = phonecall.create(vals)
            new_rec.write({'state': 'open'})
            if action == 'log':
                new_rec.write({'state': 'done'})
            phonecall_dict[lead.id] = new_rec.id
            self.schedule_phonecall_send_note([lead.id], new_rec.id, action)
        return phonecall_dict


    @api.multi
    def redirect_opportunity_view(self):
        models_data = self.env['ir.model.data']
        print"-****-*-*-*-*-views id  in opp :",self.id
        print"-****-*-*-*-*-views id  in opp :",self._ids
        # Get opportunity views
        dummy, form_view = models_data.get_object_reference('crm', 'crm_case_form_view_oppor')
        dummy, tree_view = models_data.get_object_reference('crm', 'crm_case_tree_view_oppor')
        return {
            'name': _('Opportunity'),
            'view_type': 'form',
            'view_mode': 'tree, form',
            'res_model': 'crm.lead',
            'domain': [('type', '=', 'opportunity')],
            'res_id': int(self.id),
            'view_id': False,
            'views': [(form_view or False, 'form'),
                      (tree_view or False, 'tree'), (False, 'kanban'),
                      (False, 'calendar'), (False, 'graph')],
            'type': 'ir.actions.act_window',
        }

    @api.model
    def create(self, vals):
        print"*****create*****"
        print"values : ",vals
        if vals.get('type') and not self._context.get('default_type'):
            self = self.with_context(default_type=vals.get('type'))
        if vals.get('team_id') and not self._context.get('default_team_id'):
            self = self.with_context(default_team_id=vals.get('team_id'))
        if vals.get('user_id'):
            vals['date_open'] = fields.datetime.now()
        self = self.with_context(mail_create_nolog=True)
        return super(crm_lead, self).create(vals)

    @api.multi
    def write(self, vals):
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.datetime.now()
        if vals.get('user_id'):
            vals['date_open'] = fields.datetime.now()
        # stage change with new stage: update probability and date_closed
        if vals.get('stage_id') and not vals.get('probability'):
            # stage_rec = self.browse(vals.get('stage_id'))
            self.onchange_stage_id(vals.get('stage_id'))
        return super(crm_lead, self).write(vals)

    # @api.model
    # def copy(self, default={}):
    #     self = self.with_context(default_type=self.type,default_team_id=self.team_id)
    #     if self.type == 'opportunity':
    #         default['date_open'] = fields.datetime.now()
    #     else:
    #         default['date_open'] = False
    #     return super(crm_lead, self).copy(default)
    @api.multi
    def copy(self, default={}):
        self = self.with_context(default_type=self.type, default_team_id=self.team_id.id)
        if self.type == 'opportunity':
            default['date_open'] = fields.datetime.now()
        else:
            default['date_open'] = ''
        return super(crm_lead, self).copy(default)

    @api.multi
    def redirect_lead_view(self):
        models_data = self.pool['ir.model.data']
        print"-****-*-*-*-*-views id  in lead :",self.id
        print"-****-*-*-*-*-views id  in lead :",self._ids
        # Get lead views
        dummy, form_view = models_data.get_object_reference(self._cr, self._uid, 'crm', 'crm_case_form_view_leads')
        dummy, tree_view = models_data.get_object_reference(self._cr, self._uid, 'crm', 'crm_case_tree_view_leads')
        return {
            'name': _('Lead'),
            'view_type': 'form',
            'view_mode': 'tree, form',
            'res_model': 'crm.lead',
            'domain': [('type', '=', 'lead')],
            'res_id': int(self.id),
            'view_id': False,
            'views': [(form_view or False, 'form'),
                      (tree_view or False, 'tree'),
                      (False, 'calendar'), (False, 'graph')],
            'type': 'ir.actions.act_window',
        }

    @api.multi
    def action_schedule_meeting(self):
        """
        Open meeting's calendar view to schedule meeting on current opportunity.
        :return dict: dictionary value for created Meeting view
        """
        lead = self[0]
        res = self.pool['ir.actions.act_window'].for_xml_id(self._cr, self._uid, 'calendar', 'action_calendar_event', context=self._context)
        partner_ids = [self.pool['res.users'].browse(self._cr, self._uid, self._uid, context=self._context).partner_id.id]
        if lead.partner_id:
            partner_ids.append(lead.partner_id.id)
        res['context'] = {
            'default_opportunity_id': lead.type == 'opportunity' and lead.id or False,
            'default_partner_id': lead.partner_id and lead.partner_id.id or False,
            'default_partner_ids': partner_ids,
            'default_team_id': lead.team_id and lead.team_id.id or False,
            'default_name': lead.name,
        }
        return res


    @api.model
    def get_empty_list_help(self, help):
        self = self.with_context(empty_list_help_model='crm.team',
            empty_list_help_id=self._context.get('default_team_id', None),
            )
        if self._context.get('default_type') == 'lead':
            self = self.with_context(empty_list_help_document_name = _("lead"))
        else:
            self = self.with_context(empty_list_help_document_name=_("opportunity"))
        return super(crm_lead, self).get_empty_list_help(help)

    # ----------------------------------------
    # Mail Gateway
    # ----------------------------------------

    @api.multi
    def message_get_reply_to(self):
        """ Override to get the reply_to of the parent project. """
        leads = self
        team_ids = set([lead.team_id.id for lead in leads if lead.team_id])
        aliases = self.pool['crm.team'].message_get_reply_to(self._cr, self._uid, list(team_ids), context=self._context)
        return dict((lead.id, aliases.get(lead.team_id and lead.team_id.id or 0, False)) for lead in leads)

    @api.multi
    def get_formview_id(self):
        obj = self
        if obj.type == 'opportunity':
            model, view_id = self.pool['ir.model.data'].get_object_reference('crm', 'crm_case_form_view_oppor')
        else:
            view_id = super(crm_lead, self).get_formview_id()
        return view_id

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(crm_lead, self).message_get_suggested_recipients()
    #TODO: set proper parameter
        try:
            for lead in self:
                if lead.partner_id:
                    self._message_add_suggested_recipient(self._cr, self._uid, recipients, lead ,partner=lead.partner_id, reason=_('Customer'))
                elif lead.email_from:
                    lead._message_add_suggested_recipient(self._cr, self._uid, recipients, lead, email=lead.email_from, reason=_('Customer Email'))
        except (except_orm):
        # no read access rights -> just ignore suggested recipients because this imply modifying followers
            pass
        return recipients

    @api.multi
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
            'user_id': False,
        }
        if msg.get('author_id'):
            partner_rec = self.pool['rec.partner'].browse(self._cr, self._uid, msg.get('author_id'))
            defaults.update(partner_rec.on_change_partner_id()['value'])
        if msg.get('priority') in dict(crm.AVAILABLE_PRIORITIES):
            defaults['priority'] = msg.get('priority')
        defaults.update(custom_values)
        return super(crm_lead, self).message_new(msg, custom_values=defaults)

    @api.multi
    def message_update(self, msg, update_vals=None):
        """ Overrides mail_thread message_update that is called by the mailgateway
            through message_process.
            This method updates the document according to the email.
        """
        if isinstance(self._ids, (str, int, long)):
            ids = [self._ids]
        if update_vals is None: update_vals = {}

        if msg.get('priority') in dict(crm.AVAILABLE_PRIORITIES):
            update_vals['priority'] = msg.get('priority')
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
        
        return super(crm_lead, self).message_update(msg, update_vals=update_vals)

    @api.multi
    def schedule_phonecall_send_note(self, phonecall_id, action):
        phonecall = self.env['crm.phonecall'].browse([phonecall_id])[0]
        if action == 'log':
            message = _('Logged a call for %(date)s. %(description)s')
        else:
            message = _('Scheduled a call for %(date)s. %(description)s')
        phonecall_date = datetime.strptime(phonecall.date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
        phonecall_usertime = fields.datetime.context_timestamp(phonecall_date).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        html_time = "<time datetime='%s+00:00'>%s</time>" % (phonecall.date, phonecall_usertime)
        message = message % dict(date=html_time, description=phonecall.description)
        return self.message_post(body=message)

    @api.multi
    def log_meeting(self, meeting_subject, meeting_date, duration):
        if not duration:
            duration = _('unknown')
        else:
            duration = str(duration)
        message = _("Meeting scheduled at '%s'<br> Subject: %s <br> Duration: %s hour(s)") % (meeting_date, meeting_subject, duration)
        return self.message_post(body=message)

    @api.onchange('state_id')
    def onchange_state(self):
        country_id=self.pool['res.country.state'].browse(self._cr, self._uid, self.state_id.id, context=self._context).country_id.id
        self.country_id =country_id

    @api.multi
    def message_partner_info_from_emails(self, emails, link_mail=False):
        res = super(crm_lead, self).message_partner_info_from_emails(emails, link_mail=link_mail)
        
        lead = self
        for partner_info in res:
            if not partner_info.get('partner_id') and (lead.partner_name or lead.contact_name):
                emails = email_re.findall(partner_info['full_name'] or '')
                email = emails and emails[0] or ''
                if email and lead.email_from and email.lower() == lead.email_from.lower():
                    partner_info['full_name'] = '%s <%s>' % (lead.partner_name or lead.contact_name, email)
                    break
        return res

class crm_lead_tag(models.Model):
    _name = "crm.lead.tag"
    _description = "Category of lead"
    name = fields.Char('Name', required=True, translate=True)
    team_id = fields.Many2one('crm.team', 'Sales Team')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
