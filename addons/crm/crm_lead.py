# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging
from operator import itemgetter

from openerp import SUPERUSER_ID
from openerp import tools, api, fields as newfields
from openerp.addons.base.res.res_partner import format_address
from openerp.addons.crm import crm_stage
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import email_re, email_split
from openerp.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

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


class crm_lead(format_address, osv.osv):
    """ CRM Lead Case """
    _name = "crm.lead"
    _description = "Lead/Opportunity"
    _order = "priority desc,date_action,id desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin', 'utm.mixin']
    _mail_mass_mailing = _('Leads / Opportunities')

    def _get_default_probability(self, cr, uid, context=None):
        """ Gives default probability """
        stage_id = self._get_default_stage_id(cr, uid, context=context)
        if stage_id:
            return self.pool['crm.stage'].browse(cr, uid, stage_id, context=context).probability
        else:
            return 10

    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        team_id = self.pool['crm.team']._get_default_team_id(cr, SUPERUSER_ID, context=context, user_id=uid)
        return self.stage_find(cr, uid, [], team_id, [('fold', '=', False)], context=context)

    def _resolve_type_from_context(self, cr, uid, context=None):
        """ Returns the type (lead or opportunity) from the type context
            key. Returns None if it cannot be resolved.
        """
        if context is None:
            context = {}
        return context.get('default_type')

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        access_rights_uid = access_rights_uid or uid
        stage_obj = self.pool.get('crm.stage')
        order = stage_obj._order
        # lame hack to allow reverting search, should just work in the trivial case
        if read_group_order == 'stage_id desc':
            order = "%s desc" % order
        # retrieve team_id from the context and write the domain
        # - ('id', 'in', 'ids'): add columns that should be present
        # - OR ('fold', '=', False): add default columns that are not folded
        # - OR ('team_ids', '=', team_id), ('fold', '=', False) if team_id: add team columns that are not folded
        search_domain = []
        team_id = context and context.get('default_team_id') or False
        if team_id:
            search_domain += ['|', ('team_ids', '=', team_id)]
            search_domain += [('id', 'in', ids)]
        else:
            search_domain += [('id', 'in', ids)]
        # retrieve type from the context (if set: choose 'type' or 'both')
        type = self._resolve_type_from_context(cr, uid, context=context)
        if type:
            search_domain += ['|', ('type', '=', type), ('type', '=', 'both')]
        # perform search
        stage_ids = stage_obj._search(cr, uid, search_domain, order=order, access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x, y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stage_obj.browse(cr, access_rights_uid, stage_ids, context=context):
            fold[stage.id] = stage.fold or False
        return result, fold

    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        if context and context.get('opportunity_id'):
            action = self.get_formview_action(cr, user, context['opportunity_id'], context=context)
            if action.get('views') and any(view_id for view_id in action['views'] if view_id[1] == view_type):
                view_id = next(view_id[0] for view_id in action['views'] if view_id[1] == view_type)
        res = super(crm_lead, self).fields_view_get(cr, user, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            res['arch'] = self.fields_view_get_address(cr, user, res['arch'], context=context)
        return res

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    def _compute_day(self, cr, uid, ids, fields, args, context=None):
        """
        :return dict: difference between current date and log date
        """
        res = {}
        for lead in self.browse(cr, uid, ids, context=context):
            for field in fields:
                res[lead.id] = {}
                duration = 0
                ans = False
                if field == 'day_open':
                    if lead.date_open:
                        date_create = datetime.strptime(lead.create_date, "%Y-%m-%d %H:%M:%S")
                        date_open = datetime.strptime(lead.date_open, "%Y-%m-%d %H:%M:%S")
                        ans = date_open - date_create
                elif field == 'day_close':
                    if lead.date_closed:
                        date_create = datetime.strptime(lead.create_date, "%Y-%m-%d %H:%M:%S")
                        date_close = datetime.strptime(lead.date_closed, "%Y-%m-%d %H:%M:%S")
                        ans = date_close - date_create
                if ans:
                    duration = abs(int(ans.days))
                res[lead.id][field] = duration
        return res
    def _meeting_count(self, cr, uid, ids, field_name, arg, context=None):
        Event = self.pool['calendar.event']
        return {
            opp_id: Event.search_count(cr,uid, [('opportunity_id', '=', opp_id)], context=context)
            for opp_id in ids
        }

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner', ondelete='set null', track_visibility='onchange',
            select=True, help="Linked partner (optional). Usually created when converting the lead."),

        'id': fields.integer('ID', readonly=True),
        'name': fields.char('Opportunity', required=True, select=1),
        'active': fields.boolean('Active', required=False),
        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),
        'email_from': fields.char('Email', size=128, help="Email address of the contact", select=1),
        'team_id': fields.many2one('crm.team', 'Sales Team', oldname='section_id',
                        select=True, track_visibility='onchange', help='When sending mails, the default email address is taken from the sales team.'),
        'create_date': fields.datetime('Creation Date', readonly=True),
        'email_cc': fields.text('Global CC', help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'description': fields.text('Notes'),
        'write_date': fields.datetime('Update Date', readonly=True),
        'tag_ids': fields.many2many('crm.lead.tag', 'crm_lead_tag_rel', 'lead_id', 'tag_id', 'Tags', help="Classify and analyze your lead/opportunity categories like: Training, Service"),
        'contact_name': fields.char('Contact Name', size=64),
        'partner_name': fields.char("Customer Name", size=64,help='The name of the future partner company that will be created while converting the lead into opportunity', select=1),
        'opt_out': fields.boolean('Opt-Out', oldname='optout',
            help="If opt-out is checked, this contact has refused to receive emails for mass mailing and marketing campaign. "
                    "Filter 'Available for Mass Mailing' allows users to filter the leads when performing mass mailing."),
        'type': fields.selection(
            [('lead', 'Lead'), ('opportunity', 'Opportunity')],
            string='Type', select=True, required=True,
            help="Type is used to separate Leads and Opportunities"),
        'priority': fields.selection(crm_stage.AVAILABLE_PRIORITIES, 'Rating', select=True),
        'date_closed': fields.datetime('Closed', readonly=True, copy=False),
        'stage_id': fields.many2one('crm.stage', 'Stage', track_visibility='onchange', select=True,
                        domain="['&', ('team_ids', '=', team_id), '|', ('type', '=', type), ('type', '=', 'both')]"),
        'user_id': fields.many2one('res.users', 'Salesperson', select=True, track_visibility='onchange'),
        'referred': fields.char('Referred By'),
        'date_open': fields.datetime('Assigned', readonly=True),
        'day_open': fields.function(_compute_day, string='Days to Assign',
                                    multi='day_open', type="float",
                                    store={'crm.lead': (lambda self, cr, uid, ids, c={}: ids, ['date_open'], 10)}),
        'day_close': fields.function(_compute_day, string='Days to Close',
                                     multi='day_open', type="float",
                                     store={'crm.lead': (lambda self, cr, uid, ids, c={}: ids, ['date_closed'], 10)}),
        'date_last_stage_update': fields.datetime('Last Stage Update', select=True),
        'date_conversion': fields.datetime('Conversion Date', readonly=1),

        # Messaging and marketing
        'message_bounce': fields.integer('Bounce', help="Counter of the number of bounced emails for this contact"),
        # Only used for type opportunity
        'probability': fields.float('Probability', group_operator="avg"),
        'planned_revenue': fields.float('Expected Revenue', track_visibility='always'),
        'date_deadline': fields.date('Expected Closing', help="Estimate of the date on which the opportunity will be won."),
        # CRM Actions
        'last_activity_id': fields.many2one("crm.activity", "Last Activity", select=True),
        'next_activity_id': fields.many2one("crm.activity", "Next Activity", select=True),
        'next_activity_1': fields.related("last_activity_id", "activity_1_id", "name", type="char", string="Next Activity 1"),
        'next_activity_2': fields.related("last_activity_id", "activity_2_id", "name", type="char", string="Next Activity 2"),
        'next_activity_3': fields.related("last_activity_id", "activity_3_id", "name", type="char", string="Next Activity 3"),
        'date_action': fields.date('Next Activity Date', select=True),
        'title_action': fields.char('Next Activity Summary'),

        'color': fields.integer('Color Index'),
        'partner_address_name': fields.related('partner_id', 'name', type='char', string='Partner Contact Name', readonly=True),
        'partner_address_email': fields.related('partner_id', 'email', type='char', string='Partner Contact Email', readonly=True),
        'company_currency': fields.related('company_id', 'currency_id', type='many2one', string='Currency', readonly=True, relation="res.currency"),
        'user_email': fields.related('user_id', 'email', type='char', string='User Email', readonly=True),
        'user_login': fields.related('user_id', 'login', type='char', string='User Login', readonly=True),

        # Fields for address, due to separation from crm and res.partner
        'street': fields.char('Street'),
        'street2': fields.char('Street2'),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City'),
        'state_id': fields.many2one("res.country.state", 'State'),
        'country_id': fields.many2one('res.country', 'Country'),
        'phone': fields.char('Phone'),
        'fax': fields.char('Fax'),
        'mobile': fields.char('Mobile'),
        'function': fields.char('Function'),
        'title': fields.many2one('res.partner.title', 'Title'),
        'company_id': fields.many2one('res.company', 'Company', select=1),
        'meeting_count': fields.function(_meeting_count, string='# Meetings', type='integer'),
        'lost_reason': fields.many2one('crm.lost.reason', 'Lost Reason', select=True, track_visibility='onchange'),
    }

    _defaults = {
        'active': 1,
        'type': lambda s, cr, uid, c: 'lead' if s.pool['res.users'].has_group(cr, uid, 'crm.group_use_lead') else 'opportunity',
        'user_id': lambda s, cr, uid, c: uid,
        'stage_id': lambda s, cr, uid, c: s._get_default_stage_id(cr, uid, c),
        'team_id': lambda s, cr, uid, c: s.pool['crm.team']._get_default_team_id(cr, SUPERUSER_ID, context=c, user_id=uid),
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.lead', context=c),
        'priority': lambda *a: crm_stage.AVAILABLE_PRIORITIES[0][0],
        'probability': lambda s, cr, uid, c: s._get_default_probability(cr, uid, c),
        'color': 0,
        'date_last_stage_update': fields.datetime.now,
    }

    _sql_constraints = [
        ('check_probability', 'check(probability >= 0 and probability <= 100)', 'The probability of closing the deal should be between 0% and 100%!')
    ]

    def onchange_stage_id(self, cr, uid, ids, stage_id, context=None):
        if not stage_id:
            return {'value': {}}
        stage = self.pool['crm.stage'].browse(cr, uid, stage_id, context=context)
        if not stage.on_change:
            return {'value': {}}
        return {'value': {'probability': stage.probability}}

    def on_change_partner_id(self, cr, uid, ids, partner_id, context=None):
        values = {}
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            partner_name = (partner.parent_id and partner.parent_id.name) or (partner.is_company and partner.name) or False
            values = {
                'partner_name': partner_name,
                'contact_name': (not partner.is_company and partner.name) or False,
                'title': partner.title and partner.title.id or False,
                'street': partner.street,
                'street2': partner.street2,
                'city': partner.city,
                'state_id': partner.state_id and partner.state_id.id or False,
                'country_id': partner.country_id and partner.country_id.id or False,
                'email_from': partner.email,
                'phone': partner.phone,
                'mobile': partner.mobile,
                'fax': partner.fax,
                'zip': partner.zip,
                'function': partner.function,
            }
        return {'value': values}

    def on_change_user(self, cr, uid, ids, user_id, context=None):
        """ When changing the user, also set a team_id or restrict team id
            to the ones user_id is member of. """
        if not context:
            context = {}
        if user_id and context.get('team_id'):
            team = self.pool['crm.team'].browse(cr, uid, context['team_id'], context=context)
            if user_id in team.member_ids.ids:
                return {}
        team_id = self.pool['crm.team']._get_default_team_id(cr, uid, context=context, user_id=user_id)
        return {'value': {'team_id': team_id}}

    def stage_find(self, cr, uid, cases, team_id, domain=None, order='sequence', context=None):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - type: stage type must be the same or 'both'
            - team_id: if set, stages must belong to this team or
              be a default stage; if not set, stages must be default
              stages
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cr, uid, cases, context=context)
        if context is None:
            context = {}
        # check whether we should try to add a condition on type
        avoid_add_type_term = any([term for term in domain if len(term) == 3 if term[0] == 'type'])
        # collect all team_ids
        team_ids = set()
        types = ['both']
        if not cases and context.get('default_type'):
            ctx_type = context.get('default_type')
            types += [ctx_type]
        if team_id:
            team_ids.add(team_id)
        for lead in cases:
            if lead.team_id:
                team_ids.add(lead.team_id.id)
            if lead.type not in types:
                types.append(lead.type)
        # OR all team_ids
        search_domain = []
        if team_ids:
            search_domain += [('|')] * (len(team_ids) - 1)
            for team_id in team_ids:
                search_domain.append(('team_ids', '=', team_id))
        # AND with cases types
        if not avoid_add_type_term:
            search_domain.append(('type', 'in', types))
        # AND with the domain in parameter
        search_domain += list(domain)
        # perform search, return the first found
        stage_ids = self.pool.get('crm.stage').search(cr, uid, search_domain, order=order, limit=1, context=context)
        if stage_ids:
            return stage_ids[0]
        return False

    def action_set_lost(self, cr, uid, ids, context=None):
        """ Lost semantic: probability = 0, active = False """
        return self.write(cr, uid, ids, {'probability': 0, 'active': False}, context=context)
    # Backward compatibility
    case_mark_lost = action_set_lost

    def action_set_active(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'active': True}, context=context)

    def action_set_unactive(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'active': False}, context=context)

    def action_set_won(self, cr, uid, ids, context=None):
        """ Won semantic: probability = 100 (active untouched) """
        stages_leads = {}
        for lead in self.browse(cr, uid, ids, context=context):
            stage_id = self.stage_find(cr, uid, [lead], lead.team_id.id or False, [('probability', '=', 100.0), ('on_change', '=', True)], context=context)
            if stage_id:
                if stages_leads.get(stage_id):
                    stages_leads[stage_id].append(lead.id)
                else:
                    stages_leads[stage_id] = [lead.id]
        for stage_id, lead_ids in stages_leads.items():
            self.write(cr, uid, lead_ids, {'stage_id': stage_id}, context=context)
        return self.write(cr, uid, ids, {'probability': 100}, context=context)
    # Backward compatibility
    case_mark_won = action_set_won

    def log_next_activity_1(self, cr, uid, ids, context=None):
        return self.set_next_activity(cr, uid, ids, next_activity_name='activity_1_id', context=context)

    def log_next_activity_2(self, cr, uid, ids, context=None):
        return self.set_next_activity(cr, uid, ids, next_activity_name='activity_2_id', context=context)

    def log_next_activity_3(self, cr, uid, ids, context=None):
        return self.set_next_activity(cr, uid, ids, next_activity_name='activity_3_id', context=context)

    def set_next_activity(self, cr, uid, ids, next_activity_name, context=None):
        for lead in self.browse(cr, uid, ids, context=context):
            if not lead.last_activity_id:
                continue
            next_activity = next_activity_name and getattr(lead.last_activity_id, next_activity_name, False) or False
            if next_activity:
                date_action = False
                if next_activity.days:
                    date_action = (datetime.now() + timedelta(days=next_activity.days)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),
                lead.write({
                    'next_activity_id': next_activity.id,
                    'date_action': date_action,
                    'title_action': next_activity.description,
                })
        return True

    def log_next_activity_done(self, cr, uid, ids, context=None, next_activity_name=False):
        to_clear_ids = []
        for lead in self.browse(cr, uid, ids, context=context):
            if not lead.next_activity_id:
                continue
            body_html = """<div><b>${object.next_activity_id.name}</b></div>
%if object.title_action:
<div>${object.title_action}</div>
%endif"""
            body_html = self.pool['mail.template'].render_template(cr, uid, body_html, 'crm.lead', lead.id, context=context)
            msg_id = lead.message_post(body_html, subtype_id=lead.next_activity_id.subtype_id.id)
            to_clear_ids.append(lead.id)
            self.write(cr, uid, [lead.id], {'last_activity_id': lead.next_activity_id.id}, context=context)

        if to_clear_ids:
            self.cancel_next_activity(cr, uid, to_clear_ids, context=context)
        return True

    def cancel_next_activity(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids,  {
            'next_activity_id': False,
            'date_action': False,
            'title_action': False,
        }, context=context)

    def onchange_next_activity_id(self, cr, uid, ids, next_activity_id, context=None):
        if not next_activity_id:
            return {'value': {
                'next_action1': False,
                'next_action2': False,
                'next_action3': False,
                'title_action': False,
                'date_action': False,
            }}
        activity = self.pool['crm.activity'].browse(cr, uid, next_activity_id, context=context)
        date_action = False
        if activity.days:
            date_action = (datetime.now() + timedelta(days=activity.days)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        return {'value': {
            'next_activity_1': activity.activity_1_id and activity.activity_1_id.name or False,
            'next_activity_2': activity.activity_2_id and activity.activity_2_id.name or False,
            'next_activity_3': activity.activity_3_id and activity.activity_3_id.name or False,
            'title_action': activity.description,
            'date_action': date_action,
            'last_activity_id': False,
        }}

    def _merge_get_result_type(self, cr, uid, opps, context=None):
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
        for opp in opps:
            if (opp.type == 'opportunity'):
                return 'opportunity'

        return 'lead'

    def _merge_data(self, cr, uid, ids, oldest, fields, context=None):
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
        opportunities = self.browse(cr, uid, ids, context=context)

        def _get_first_not_null(attr):
            for opp in opportunities:
                if hasattr(opp, attr) and bool(getattr(opp, attr)):
                    return getattr(opp, attr)
            return False

        def _get_first_not_null_id(attr):
            res = _get_first_not_null(attr)
            return res and res.id or False

        def _concat_all(attr):
            return '\n\n'.join(filter(lambda x: x, [getattr(opp, attr) or '' for opp in opportunities if hasattr(opp, attr)]))

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
        data['type'] = self._merge_get_result_type(cr, uid, opportunities, context)
        return data

    def _mail_body(self, cr, uid, lead, fields, title=False, context=None):
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
                    key = field.selection(self, cr, uid, context=context)
                else:
                    key = field.selection
                value = dict(key).get(lead[field_name], lead[field_name])
            elif field.type == 'many2one':
                if lead[field_name]:
                    value = lead[field_name].sudo().name_get()[0][1]
            elif field.type == 'many2many':
                if lead[field_name]:
                    for val in lead[field_name]:
                        field_value = val.sudo().name_get()[0][1]
                        value += field_value + ","
            else:
                value = lead[field_name]

            body.append("%s: %s" % (field.string, value or ''))
        return "<br/>".join(body + ['<br/>'])

    def _merge_notify(self, cr, uid, opportunity_id, opportunities, context=None):
        """
        Create a message gathering merged leads/opps information.
        """
        #TOFIX: mail template should be used instead of fix body, subject text
        details = []
        result_type = self._merge_get_result_type(cr, uid, opportunities, context)
        if result_type == 'lead':
            merge_message = _('Merged leads')
        else:
            merge_message = _('Merged opportunities')
        subject = [merge_message]
        for opportunity in opportunities:
            subject.append(opportunity.name)
            title = "%s : %s" % (opportunity.type == 'opportunity' and _('Merged opportunity') or _('Merged lead'), opportunity.name)
            fields = list(CRM_LEAD_FIELDS_TO_MERGE)
            details.append(self._mail_body(cr, uid, opportunity, fields, title=title, context=context))

        # Chatter message's subject
        subject = subject[0] + ": " + ", ".join(subject[1:])
        details = "\n\n".join(details)
        return self.message_post(cr, uid, [opportunity_id], body=details, subject=subject, context=context)

    def _merge_opportunity_history(self, cr, uid, opportunity_id, opportunities, context=None):
        message = self.pool.get('mail.message')
        for opportunity in opportunities:
            for history in opportunity.message_ids:
                message.write(cr, uid, history.id, {
                        'res_id': opportunity_id,
                        'subject' : _("From %s : %s") % (opportunity.name, history.subject)
                }, context=context)

        return True

    def _merge_opportunity_attachments(self, cr, uid, opportunity_id, opportunities, context=None):
        attach_obj = self.pool.get('ir.attachment')

        # return attachments of opportunity
        def _get_attachments(opportunity_id):
            attachment_ids = attach_obj.search(cr, uid, [('res_model', '=', self._name), ('res_id', '=', opportunity_id)], context=context)
            return attach_obj.browse(cr, uid, attachment_ids, context=context)

        first_attachments = _get_attachments(opportunity_id)
        #counter of all attachments to move. Used to make sure the name is different for all attachments
        count = 1
        for opportunity in opportunities:
            attachments = _get_attachments(opportunity.id)
            for attachment in attachments:
                values = {'res_id': opportunity_id,}
                for attachment_in_first in first_attachments:
                    if attachment.name == attachment_in_first.name:
                        values['name'] = "%s (%s)" % (attachment.name, count,),
                count+=1
                attachment.write(values)
        return True

    def get_duplicated_leads(self, cr, uid, ids, partner_id, include_lost=False, context=None):
        """
        Search for opportunities that have the same partner and that arent done or cancelled
        """
        lead = self.browse(cr, uid, ids[0], context=context)
        email = lead.partner_id and lead.partner_id.email or lead.email_from
        return self.pool['crm.lead']._get_duplicated_leads_by_emails(cr, uid, partner_id, email, include_lost=include_lost, context=context)

    def _get_duplicated_leads_by_emails(self, cr, uid, partner_id, email, include_lost=False, context=None):
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
        return self.search(cr, uid, domain, context=context)

    def merge_dependences(self, cr, uid, highest, opportunities, context=None):
        self._merge_notify(cr, uid, highest, opportunities, context=context)
        self._merge_opportunity_history(cr, uid, highest, opportunities, context=context)
        self._merge_opportunity_attachments(cr, uid, highest, opportunities, context=context)

    def merge_opportunity(self, cr, uid, ids, user_id=False, team_id=False, context=None):
        """
        Different cases of merge:
        - merge leads together = 1 new lead
        - merge at least 1 opp with anything else (lead or opp) = 1 new opp

        :param list ids: leads/opportunities ids to merge
        :return int id: id of the resulting lead/opp
        """
        if context is None:
            context = {}

        if len(ids) <= 1:
            raise UserError(_('Please select more than one element (lead or opportunity) from the list view.'))

        opportunities = self.browse(cr, uid, ids, context=context)
        sequenced_opps = []
        # Sorting the leads/opps according to the confidence level of its stage, which relates to the probability of winning it
        # The confidence level increases with the stage sequence, except when the stage probability is 0.0 (Lost cases)
        # An Opportunity always has higher confidence level than a lead, unless its stage probability is 0.0
        for opportunity in opportunities:
            sequence = -1
            if opportunity.stage_id and opportunity.stage_id.on_change:
                sequence = opportunity.stage_id.sequence
            sequenced_opps.append(((int(sequence != -1 and opportunity.type == 'opportunity'), sequence, -opportunity.id), opportunity))

        sequenced_opps.sort(reverse=True)
        opportunities = map(itemgetter(1), sequenced_opps)
        ids = [opportunity.id for opportunity in opportunities]
        highest = opportunities[0]
        opportunities_rest = opportunities[1:]

        tail_opportunities = opportunities_rest

        fields = list(CRM_LEAD_FIELDS_TO_MERGE)
        merged_data = self._merge_data(cr, uid, ids, highest, fields, context=context)

        if user_id:
            merged_data['user_id'] = user_id
        if team_id:
            merged_data['team_id'] = team_id

        # Merge notifications about loss of information
        opportunities = [highest]
        opportunities.extend(opportunities_rest)

        self.merge_dependences(cr, uid, highest.id, tail_opportunities, context=context)

        # Check if the stage is in the stages of the sales team. If not, assign the stage with the lowest sequence
        if merged_data.get('team_id'):
            team_stage_ids = self.pool.get('crm.stage').search(cr, uid, [('team_ids', 'in', merged_data['team_id']), ('type', 'in', [merged_data.get('type'), 'both'])], order='sequence', context=context)
            if merged_data.get('stage_id') not in team_stage_ids:
                merged_data['stage_id'] = team_stage_ids and team_stage_ids[0] or False
        # Write merged data into first opportunity
        self.write(cr, uid, [highest.id], merged_data, context=context)
        # Delete tail opportunities 
        # We use the SUPERUSER to avoid access rights issues because as the user had the rights to see the records it should be safe to do so
        self.unlink(cr, SUPERUSER_ID, [x.id for x in tail_opportunities], context=context)

        return highest.id

    def _convert_opportunity_data(self, cr, uid, lead, customer, team_id=False, context=None):
        crm_stage = self.pool.get('crm.stage')
        contact_id = False
        if customer:
            contact_id = self.pool.get('res.partner').address_get(cr, uid, [customer.id])['contact']
        if not team_id:
            team_id = lead.team_id and lead.team_id.id or False
        val = {
            'planned_revenue': lead.planned_revenue,
            'probability': lead.probability,
            'name': lead.name,
            'partner_id': customer and customer.id or False,
            'type': 'opportunity',
            'date_open': fields.datetime.now(),
            'email_from': customer and customer.email or lead.email_from,
            'phone': customer and customer.phone or lead.phone,
            'date_conversion': fields.datetime.now(),
        }
        if not lead.stage_id or lead.stage_id.type=='lead':
            stage_id = self.stage_find(cr, uid, [lead], team_id, [('type', 'in', ['opportunity', 'both'])], context=context)
            val['stage_id'] = stage_id
            if stage_id:
                val['probability'] = self.pool['crm.stage'].browse(cr, uid, stage_id, context=context).probability
        return val

    def convert_opportunity(self, cr, uid, ids, partner_id, user_ids=False, team_id=False, context=None):
        customer = False
        if partner_id:
            partner = self.pool.get('res.partner')
            customer = partner.browse(cr, uid, partner_id, context=context)
        for lead in self.browse(cr, uid, ids, context=context):
            if not lead.active or lead.probability == 100:
                continue
            vals = self._convert_opportunity_data(cr, uid, lead, customer, team_id, context=context)
            self.write(cr, uid, [lead.id], vals, context=context)

        if user_ids or team_id:
            self.allocate_salesman(cr, uid, ids, user_ids, team_id, context=context)

        return True

    def _lead_create_contact(self, cr, uid, lead, name, is_company, parent_id=False, context=None):
        if context is None:
            context = {}
        partner = self.pool.get('res.partner')
        vals = {'name': name,
            'user_id': context.get('default_user_id') or lead.user_id.id,
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
        partner = partner.create(cr, uid, vals, context=context)
        return partner

    def _create_lead_partner(self, cr, uid, lead, context=None):
        contact_id = False
        contact_name = lead.contact_name or lead.email_from and self.pool.get('res.partner')._parse_partner_name(lead.email_from, context=context)[0] or False
        if lead.partner_name:
            partner_company_id = self._lead_create_contact(cr, uid, lead, lead.partner_name, True, context=context)
        elif lead.partner_id:
            partner_company_id = lead.partner_id.id
        else:
            partner_company_id = False

        if contact_name:
            contact_id = self._lead_create_contact(cr, uid, lead, contact_name, False, partner_company_id, context=context)

        partner_id = contact_id or partner_company_id or self._lead_create_contact(cr, uid, lead, lead.name, False, context=context)
        return partner_id

    def handle_partner_assignation(self, cr, uid, ids, action='create', partner_id=False, context=None):
        """
        Handle partner assignation during a lead conversion.
        if action is 'create', create new partner with contact and assign lead to new partner_id.
        otherwise assign lead to the specified partner_id

        :param list ids: leads/opportunities ids to process
        :param string action: what has to be done regarding partners (create it, assign an existing one, or nothing)
        :param int partner_id: partner to assign if any
        :return dict: dictionary organized as followed: {lead_id: partner_assigned_id}
        """
        partner_ids = {}
        for lead in self.browse(cr, uid, ids, context=context):
            # If the action is set to 'create' and no partner_id is set, create a new one
            if lead.partner_id:
                partner_ids[lead.id] = lead.partner_id.id
            if action == 'create':
                partner_id = self._create_lead_partner(cr, uid, lead, context)
                self.pool['res.partner'].write(cr, uid, partner_id, {'team_id': lead.team_id and lead.team_id.id or False})
            if partner_id:
                lead.write({'partner_id': partner_id})
            partner_ids[lead.id] = partner_id
        return partner_ids

    def allocate_salesman(self, cr, uid, ids, user_ids=None, team_id=False, context=None):
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
                self.write(cr, uid, [lead_id], value, context=context)
        return True

    def redirect_opportunity_view(self, cr, uid, opportunity_id, context=None):
        models_data = self.pool.get('ir.model.data')

        # Get opportunity views
        dummy, form_view = models_data.get_object_reference(cr, uid, 'crm', 'crm_case_form_view_oppor')
        dummy, tree_view = models_data.get_object_reference(cr, uid, 'crm', 'crm_case_tree_view_oppor')
        return {
            'name': _('Opportunity'),
            'view_type': 'form',
            'view_mode': 'tree, form',
            'res_model': 'crm.lead',
            'domain': [('type', '=', 'opportunity')],
            'res_id': int(opportunity_id),
            'view_id': False,
            'views': [(form_view or False, 'form'),
                      (tree_view or False, 'tree'), (False, 'kanban'),
                      (False, 'calendar'), (False, 'graph')],
            'type': 'ir.actions.act_window',
            'context': {'default_type': 'opportunity'}
        }

    def redirect_lead_view(self, cr, uid, lead_id, context=None):
        models_data = self.pool.get('ir.model.data')

        # Get lead views
        dummy, form_view = models_data.get_object_reference(cr, uid, 'crm', 'crm_case_form_view_leads')
        dummy, tree_view = models_data.get_object_reference(cr, uid, 'crm', 'crm_case_tree_view_leads')
        return {
            'name': _('Lead'),
            'view_type': 'form',
            'view_mode': 'tree, form',
            'res_model': 'crm.lead',
            'domain': [('type', '=', 'lead')],
            'res_id': int(lead_id),
            'view_id': False,
            'views': [(form_view or False, 'form'),
                      (tree_view or False, 'tree'),
                      (False, 'calendar'), (False, 'graph')],
            'type': 'ir.actions.act_window',
        }

    def action_schedule_meeting(self, cr, uid, ids, context=None):
        """
        Open meeting's calendar view to schedule meeting on current opportunity.
        :return dict: dictionary value for created Meeting view
        """
        lead = self.browse(cr, uid, ids[0], context)
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'calendar', 'action_calendar_event', context)
        partner_ids = [self.pool['res.users'].browse(cr, uid, uid, context=context).partner_id.id]
        if lead.partner_id:
            partner_ids.append(lead.partner_id.id)
        res['context'] = {
            'search_default_opportunity_id': lead.type == 'opportunity' and lead.id or False,
            'default_opportunity_id': lead.type == 'opportunity' and lead.id or False,
            'default_partner_id': lead.partner_id and lead.partner_id.id or False,
            'default_partner_ids': partner_ids,
            'default_team_id': lead.team_id and lead.team_id.id or False,
            'default_name': lead.name,
        }
        return res

    def create(self, cr, uid, vals, context=None):
        context = dict(context or {})
        if vals.get('type') and not context.get('default_type'):
            context['default_type'] = vals.get('type')
        if vals.get('team_id') and not context.get('default_team_id'):
            context['default_team_id'] = vals.get('team_id')
        if vals.get('user_id') and 'date_open' not in vals:
            vals['date_open'] = fields.datetime.now()
        if context.get('default_partner_id') and not vals.get('email_from'):
            partner_id = self.pool['res.partner'].browse(cr, uid, context.get('default_partner_id'))
            vals['email_from'] = partner_id.email

        # context: no_log, because subtype already handle this
        create_context = dict(context, mail_create_nolog=True)
        return super(crm_lead, self).create(cr, uid, vals, context=create_context)

    def write(self, cr, uid, ids, vals, context=None):
        # stage change: update date_last_stage_update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.datetime.now()
        if vals.get('user_id') and 'date_open' not in vals:
            vals['date_open'] = fields.datetime.now()
        # stage change with new stage: update probability and date_closed
        if vals.get('stage_id') and 'probability' not in vals:
            onchange_stage_values = self.onchange_stage_id(cr, uid, ids, vals.get('stage_id'), context=context)['value']
            vals.update(onchange_stage_values)
        if vals.get('probability') >= 100 or not vals.get('active', True):
            vals['date_closed'] = fields.datetime.now()
        elif 'probability' in vals and vals['probability'] < 100:
            vals['date_closed'] = False
        return super(crm_lead, self).write(cr, uid, ids, vals, context=context)

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        if not context:
            context = {}
        lead = self.browse(cr, uid, id, context=context)
        local_context = dict(context)
        local_context.setdefault('default_type', lead.type)
        local_context.setdefault('default_team_id', lead.team_id.id)
        if lead.type == 'opportunity':
            default['date_open'] = fields.datetime.now()
        else:
            default['date_open'] = False
        return super(crm_lead, self).copy(cr, uid, id, default, context=local_context)

    def get_empty_list_help(self, cr, uid, help, context=None):
        context = dict(context or {})
        context['empty_list_help_model'] = 'crm.team'
        context['empty_list_help_id'] = context.get('default_team_id', None)
        context['empty_list_help_document_name'] = _("opportunities")
        if help:
            alias_record = self.pool['ir.model.data'].xmlid_to_object(cr, uid, "crm.mail_alias_lead_info")
            if alias_record and alias_record.alias_domain and alias_record.alias_name:
                dynamic_help = '<p>%s</p>' % _("""All email incoming to %(link)s  will automatically create new opportunity.
Update your business card, phone book, social media,... Send an email right now and see it here.""") % {
                    'link': "<a href='mailto:%(email)s'>%(email)s</a>" % {'email': '%s@%s' % (alias_record.alias_name, alias_record.alias_domain)}
                }
                return '<p class="oe_view_nocontent_create">%s</p>%s%s' % (
                    _('Click to add a new opportunity'),
                    help,
                    dynamic_help)
        return super(crm_lead, self).get_empty_list_help(cr, uid, help, context=context)

    # ----------------------------------------
    # Mail Gateway
    # ----------------------------------------

    def _track_subtype(self, cr, uid, ids, init_values, context=None):
        record = self.browse(cr, uid, ids[0], context=context)
        if 'stage_id' in init_values and record.probability == 100 and record.stage_id and record.stage_id.on_change:
            return 'crm.mt_lead_won'
        elif 'active' in init_values and record.probability == 0 and not record.active:
            return 'crm.mt_lead_lost'
        elif 'stage_id' in init_values and record.stage_id and record.stage_id.sequence <= 1:
            return 'crm.mt_lead_create'
        elif 'stage_id' in init_values:
            return 'crm.mt_lead_stage'
        return super(crm_lead, self)._track_subtype(cr, uid, ids, init_values, context=context)

    def _notification_group_recipients(self, cr, uid, ids, message, recipients, done_ids, group_data, context=None):
        """ Override the mail.thread method to handle salesman recipients.
        Indeed those will have specific action in their notification emails. """
        group_sale_salesman = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'base.group_sale_salesman')
        for recipient in recipients:
            if recipient.id in done_ids:
                continue
            if recipient.user_ids and group_sale_salesman in recipient.user_ids[0].groups_id.ids:
                group_data['group_sale_salesman'] |= recipient
                done_ids.add(recipient.id)
        return super(crm_lead, self)._notification_group_recipients(cr, uid, ids, message, recipients, done_ids, group_data, context=context)

    def _notification_get_recipient_groups(self, cr, uid, ids, message, recipients, context=None):
        res = super(crm_lead, self)._notification_get_recipient_groups(cr, uid, ids, message, recipients, context=context)

        lead = self.browse(cr, uid, ids[0], context=context)

        won_action = self._notification_link_helper(cr, uid, ids, 'controller', controller='/lead/case_mark_won', context=context)
        lost_action = self._notification_link_helper(cr, uid, ids, 'controller', controller='/lead/case_mark_lost', context=context)
        convert_action = self._notification_link_helper(cr, uid, ids, 'controller', controller='/lead/convert', context=context)

        if lead.type == 'lead':
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

    @api.cr_uid_context
    def message_get_reply_to(self, cr, uid, ids, default=None, context=None):
        """ Override to get the reply_to of the parent project. """
        leads = self.browse(cr, SUPERUSER_ID, ids, context=context)
        team_ids = set([lead.team_id.id for lead in leads if lead.team_id])
        aliases = self.pool['crm.team'].message_get_reply_to(cr, uid, list(team_ids), default=default, context=context)
        return dict((lead.id, aliases.get(lead.team_id and lead.team_id.id or 0, False)) for lead in leads)

    def get_formview_id(self, cr, uid, id, context=None):
        obj = self.browse(cr, uid, id, context=context)
        if obj.type == 'opportunity':
            model, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'crm', 'crm_case_form_view_oppor')
        else:
            view_id = super(crm_lead, self).get_formview_id(cr, uid, id, context=context)
        return view_id

    def message_get_suggested_recipients(self, cr, uid, ids, context=None):
        recipients = super(crm_lead, self).message_get_suggested_recipients(cr, uid, ids, context=context)
        try:
            for lead in self.browse(cr, uid, ids, context=context):
                if lead.partner_id:
                    lead._message_add_suggested_recipient(recipients, partner=lead.partner_id, reason=_('Customer'))
                elif lead.email_from:
                    lead._message_add_suggested_recipient(recipients, email=lead.email_from, reason=_('Customer Email'))
        except AccessError:  # no read access rights -> just ignore suggested recipients because this imply modifying followers
            pass
        return recipients

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        create_context = dict(context or {})
        create_context['default_user_id'] = False
        if custom_values is None:
            custom_values = {}
        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
        }
        if msg.get('author_id'):
            defaults.update(self.on_change_partner_id(cr, uid, None, msg.get('author_id'), context=context)['value'])
        if msg.get('priority') in dict(crm_stage.AVAILABLE_PRIORITIES):
            defaults['priority'] = msg.get('priority')
        defaults.update(custom_values)
        return super(crm_lead, self).message_new(cr, uid, msg, custom_values=defaults, context=create_context)

    def message_update(self, cr, uid, ids, msg, update_vals=None, context=None):
        """ Overrides mail_thread message_update that is called by the mailgateway
            through message_process.
            This method updates the document according to the email.
        """
        if isinstance(ids, (str, int, long)):
            ids = [ids]
        if update_vals is None: update_vals = {}

        if msg.get('priority') in dict(crm_stage.AVAILABLE_PRIORITIES):
            update_vals['priority'] = msg.get('priority')
        maps = {
            'revenue': 'planned_revenue',
            'probability':'probability',
        }
        for line in msg.get('body', '').split('\n'):
            line = line.strip()
            res = tools.command_re.match(line)
            if res and maps.get(res.group(1).lower()):
                key = maps.get(res.group(1).lower())
                update_vals[key] = res.group(2).lower()

        return super(crm_lead, self).message_update(cr, uid, ids, msg, update_vals=update_vals, context=context)

    def log_meeting(self, cr, uid, ids, meeting_subject, meeting_date, duration, context=None):
        if not duration:
            duration = _('unknown')
        else:
            duration = str(duration)
        meet_date = datetime.strptime(meeting_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
        meeting_usertime = fields.datetime.context_timestamp(cr, uid, meet_date, context=context).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        html_time = "<time datetime='%s+00:00'>%s</time>" % (meeting_date, meeting_usertime)
        message = _("Meeting scheduled at '%s'<br> Subject: %s <br> Duration: %s hour(s)") % (html_time, meeting_subject, duration)
        return self.message_post(cr, uid, ids, body=message, context=context)

    def onchange_state(self, cr, uid, ids, state_id, context=None):
        if state_id:
            country_id=self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id
            return {'value':{'country_id':country_id}}
        return {}

    def message_partner_info_from_emails(self, cr, uid, ids, emails, link_mail=False, context=None):
        res = super(crm_lead, self).message_partner_info_from_emails(cr, uid, ids, emails, link_mail=link_mail, context=context)
        lead = self.browse(cr, uid, ids[0], context=context)
        for partner_info in res:
            if not partner_info.get('partner_id') and (lead.partner_name or lead.contact_name):
                emails = email_re.findall(partner_info['full_name'] or '')
                email = emails and emails[0] or ''
                if email and lead.email_from and email.lower() == lead.email_from.lower():
                    partner_info['full_name'] = '%s <%s>' % (lead.partner_name or lead.contact_name, email)
                    break
        return res

    def retrieve_sales_dashboard(self, cr, uid, context=None):
        date_today = newfields.Date.from_string(fields.date.context_today(self, cr, uid, context=context))

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
            cr, uid,
            [('type', '=', 'opportunity'), ('user_id', '=', uid)],
            ['date_deadline', 'next_activity_id', 'date_action', 'date_closed', 'planned_revenue'], context=context)

        for opp in opportunities:

            # Expected closing
            if opp['date_deadline']:
                date_deadline = datetime.strptime(opp['date_deadline'], tools.DEFAULT_SERVER_DATE_FORMAT).date()

                if date_deadline == date_today:
                    res['closing']['today'] += 1
                if date_deadline >= date_today and date_deadline <= date_today + timedelta(days=7):
                    res['closing']['next_7_days'] += 1
                if date_deadline < date_today and not opp['date_closed']:
                    res['closing']['overdue'] += 1

            # Next activities
            if opp['next_activity_id'] and opp['date_action']:
                date_action = datetime.strptime(opp['date_action'], tools.DEFAULT_SERVER_DATE_FORMAT).date()

                if date_action == date_today:
                    res['activity']['today'] += 1
                if date_action >= date_today and date_action <= date_today + timedelta(days=7):
                    res['activity']['next_7_days'] += 1
                if date_action < date_today and not opp['date_closed']:
                    res['activity']['overdue'] += 1

            # Won in Opportunities
            if opp['date_closed']:
                date_closed = datetime.strptime(opp['date_closed'], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()

                if date_closed <= date_today and date_closed >= date_today.replace(day=1):
                    if opp['planned_revenue']:
                        res['won']['this_month'] += opp['planned_revenue']
                elif date_closed < date_today.replace(day=1) and date_closed >= date_today.replace(day=1) - relativedelta(months=+1):
                    if opp['planned_revenue']:
                        res['won']['last_month'] += opp['planned_revenue']

        # crm.activity is a very messy model so we need to do that in order to retrieve the actions done.
        cr.execute("""
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
        """, (uid,))
        activites_done = cr.dictfetchall()

        for act in activites_done:
            if act['date']:
                date_act = datetime.strptime(act['date'], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()
                if date_act <= date_today and date_act >= date_today.replace(day=1):
                        res['done']['this_month'] += 1
                elif date_act < date_today.replace(day=1) and date_act >= date_today.replace(day=1) - relativedelta(months=+1):
                    res['done']['last_month'] += 1

        # Meetings
        min_date = datetime.now().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        max_date = (datetime.now() + timedelta(days=8)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        meetings_domain = [
            ('start', '>=', min_date),
            ('start', '<=', max_date)
        ]
        # We need to add 'mymeetings' in the context for the search to be correct.
        meetings = self.pool.get('calendar.event').search_read(cr, uid, meetings_domain, ['start'], context=context.update({'mymeetings': 1}) if context else {'mymeetings': 1})
        for meeting in meetings:
            if meeting['start']:
                start = datetime.strptime(meeting['start'], tools.DEFAULT_SERVER_DATETIME_FORMAT).date()

                if start == date_today:
                    res['meeting']['today'] += 1
                if start >= date_today and start <= date_today + timedelta(days=7):
                    res['meeting']['next_7_days'] += 1

        res['nb_opportunities'] = len(opportunities)

        user = self.pool('res.users').browse(cr, uid, uid, context=context)
        res['done']['target'] = user.target_sales_done
        res['won']['target'] = user.target_sales_won

        res['currency_id'] = user.company_id.currency_id.id

        return res

    def modify_target_sales_dashboard(self, cr, uid, target_name, target_value, context=None):

        if target_name in ['won', 'done', 'invoiced']:
            # bypass rights (with superuser_id)
            self.pool('res.users').write(cr, SUPERUSER_ID, [uid], {'target_sales_' + target_name: target_value}, context=context)
        else:
            raise UserError(_('This target does not exist.'))


class crm_lead_tag(osv.Model):
    _name = "crm.lead.tag"
    _description = "Category of lead"
    _columns = {
        'name': fields.char('Name', required=True),
        'color': fields.integer('Color Index'),
        'team_id': fields.many2one('crm.team', 'Sales Team'),
    }
    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class crm_lost_reason(osv.Model):
    _name = "crm.lost.reason"
    _description = 'Reason for loosing leads'

    _columns = {
        'name': fields.char('Name', required=True),
        'active': fields.boolean('Active'),
    }

    _defaults = {
        'active': True,
    }
