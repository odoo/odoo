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

from openerp.addons.base_status.base_stage import base_stage
import crm
from datetime import datetime
from operator import itemgetter
from openerp.osv import fields, osv
import time
from openerp import tools
from openerp.tools.translate import _
from openerp.tools import html2plaintext

from base.res.res_partner import format_address

CRM_LEAD_FIELDS_TO_MERGE = ['name',
    'partner_id',
    'channel_id',
    'company_id',
    'country_id',
    'section_id',
    'state_id',
    'stage_id',
    'type_id',
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
CRM_LEAD_PENDING_STATES = (
    crm.AVAILABLE_STATES[2][0], # Cancelled
    crm.AVAILABLE_STATES[3][0], # Done
    crm.AVAILABLE_STATES[4][0], # Pending
)

class crm_lead(base_stage, format_address, osv.osv):
    """ CRM Lead Case """
    _name = "crm.lead"
    _description = "Lead/Opportunity"
    _order = "priority,date_action,id desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    _track = {
        'state': {
            'crm.mt_lead_create': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'new',
            'crm.mt_lead_won': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'done',
            'crm.mt_lead_lost': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'cancel',
        },
        'stage_id': {
            'crm.mt_lead_stage': lambda self, cr, uid, obj, ctx=None: obj['state'] not in ['new', 'cancel', 'done'],
        },
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        if not vals.get('stage_id'):
            ctx = context.copy()
            if vals.get('section_id'):
                ctx['default_section_id'] = vals['section_id']
            if vals.get('type'):
                ctx['default_type'] = vals['type']
            vals['stage_id'] = self._get_default_stage_id(cr, uid, context=ctx)
        return super(crm_lead, self).create(cr, uid, vals, context=context)

    def _get_default_section_id(self, cr, uid, context=None):
        """ Gives default section by checking if present in the context """
        return self._resolve_section_id_from_context(cr, uid, context=context) or False

    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        section_id = self._get_default_section_id(cr, uid, context=context)
        return self.stage_find(cr, uid, [], section_id, [('state', '=', 'draft')], context=context)

    def _resolve_section_id_from_context(self, cr, uid, context=None):
        """ Returns ID of section based on the value of 'section_id'
            context key, or None if it cannot be resolved to a single
            Sales Team.
        """
        if context is None:
            context = {}
        if type(context.get('default_section_id')) in (int, long):
            return context.get('default_section_id')
        if isinstance(context.get('default_section_id'), basestring):
            section_name = context['default_section_id']
            section_ids = self.pool.get('crm.case.section').name_search(cr, uid, name=section_name, context=context)
            if len(section_ids) == 1:
                return int(section_ids[0][0])
        return None

    def _resolve_type_from_context(self, cr, uid, context=None):
        """ Returns the type (lead or opportunity) from the type context
            key. Returns None if it cannot be resolved.
        """
        if context is None:
            context = {}
        return context.get('default_type')

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        access_rights_uid = access_rights_uid or uid
        stage_obj = self.pool.get('crm.case.stage')
        order = stage_obj._order
        # lame hack to allow reverting search, should just work in the trivial case
        if read_group_order == 'stage_id desc':
            order = "%s desc" % order
        # retrieve section_id from the context and write the domain
        # - ('id', 'in', 'ids'): add columns that should be present
        # - OR ('case_default', '=', True), ('fold', '=', False): add default columns that are not folded
        # - OR ('section_ids', '=', section_id), ('fold', '=', False) if section_id: add section columns that are not folded
        search_domain = []
        section_id = self._resolve_section_id_from_context(cr, uid, context=context)
        if section_id:
            search_domain += ['|', ('section_ids', '=', section_id)]
            search_domain += [('id', 'in', ids)]
        else:
            search_domain += ['|', ('id', 'in', ids), ('case_default', '=', True)]
        # retrieve type from the context (if set: choose 'type' or 'both')
        type = self._resolve_type_from_context(cr, uid, context=context)
        if type:
            search_domain += ['|', ('type', '=', type), ('type', '=', 'both')]
        # perform search
        stage_ids = stage_obj._search(cr, uid, search_domain, order=order, access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x,y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stage_obj.browse(cr, access_rights_uid, stage_ids, context=context):
            fold[stage.id] = stage.fold or False
        return result, fold

    def fields_view_get(self, cr, user, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(crm_lead,self).fields_view_get(cr, user, view_id, view_type, context, toolbar=toolbar, submenu=submenu)
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
        cal_obj = self.pool.get('resource.calendar')
        res_obj = self.pool.get('resource.resource')

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
                        date_until = lead.date_open
                elif field == 'day_close':
                    if lead.date_closed:
                        date_create = datetime.strptime(lead.create_date, "%Y-%m-%d %H:%M:%S")
                        date_close = datetime.strptime(lead.date_closed, "%Y-%m-%d %H:%M:%S")
                        date_until = lead.date_closed
                        ans = date_close - date_create
                if ans:
                    resource_id = False
                    if lead.user_id:
                        resource_ids = res_obj.search(cr, uid, [('user_id','=',lead.user_id.id)])
                        if len(resource_ids):
                            resource_id = resource_ids[0]

                    duration = float(ans.days)
                    if lead.section_id and lead.section_id.resource_calendar_id:
                        duration =  float(ans.days) * 24
                        new_dates = cal_obj.interval_get(cr,
                            uid,
                            lead.section_id.resource_calendar_id and lead.section_id.resource_calendar_id.id or False,
                            datetime.strptime(lead.create_date, '%Y-%m-%d %H:%M:%S'),
                            duration,
                            resource=resource_id
                        )
                        no_days = []
                        date_until = datetime.strptime(date_until, '%Y-%m-%d %H:%M:%S')
                        for in_time, out_time in new_dates:
                            if in_time.date not in no_days:
                                no_days.append(in_time.date)
                            if out_time > date_until:
                                break
                        duration =  len(no_days)
                res[lead.id][field] = abs(int(duration))
        return res

    def _history_search(self, cr, uid, obj, name, args, context=None):
        res = []
        msg_obj = self.pool.get('mail.message')
        message_ids = msg_obj.search(cr, uid, [('email_from','!=',False), ('subject', args[0][1], args[0][2])], context=context)
        lead_ids = self.search(cr, uid, [('message_ids', 'in', message_ids)], context=context)

        if lead_ids:
            return [('id', 'in', lead_ids)]
        else:
            return [('id', '=', '0')]

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner', ondelete='set null', track_visibility='onchange',
            select=True, help="Linked partner (optional). Usually created when converting the lead."),

        'id': fields.integer('ID', readonly=True),
        'name': fields.char('Subject', size=64, required=True, select=1),
        'active': fields.boolean('Active', required=False),
        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),
        'email_from': fields.char('Email', size=128, help="Email address of the contact", select=1),
        'section_id': fields.many2one('crm.case.section', 'Sales Team',
                        select=True, track_visibility='onchange', help='When sending mails, the default email address is taken from the sales team.'),
        'create_date': fields.datetime('Creation Date' , readonly=True),
        'email_cc': fields.text('Global CC', size=252 , help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'description': fields.text('Notes'),
        'write_date': fields.datetime('Update Date' , readonly=True),
        'categ_ids': fields.many2many('crm.case.categ', 'crm_lead_category_rel', 'lead_id', 'category_id', 'Categories', \
            domain="['|',('section_id','=',section_id),('section_id','=',False), ('object_id.model', '=', 'crm.lead')]"),
        'type_id': fields.many2one('crm.case.resource.type', 'Campaign', \
            domain="['|',('section_id','=',section_id),('section_id','=',False)]", help="From which campaign (seminar, marketing campaign, mass mailing, ...) did this contact come from?"),
        'channel_id': fields.many2one('crm.case.channel', 'Channel', help="Communication channel (mail, direct, phone, ...)"),
        'contact_name': fields.char('Contact Name', size=64),
        'partner_name': fields.char("Customer Name", size=64,help='The name of the future partner company that will be created while converting the lead into opportunity', select=1),
        'opt_out': fields.boolean('Opt-Out', oldname='optout',
            help="If opt-out is checked, this contact has refused to receive emails for mass mailing and marketing campaign. "
                    "Filter 'Available for Mass Mailing' allows users to filter the leads when performing mass mailing."),
        'type':fields.selection([ ('lead','Lead'), ('opportunity','Opportunity'), ],'Type', help="Type is used to separate Leads and Opportunities"),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority', select=True),
        'date_closed': fields.datetime('Closed', readonly=True),
        'stage_id': fields.many2one('crm.case.stage', 'Stage', track_visibility='onchange',
                        domain="['&', '&', ('fold', '=', False), ('section_ids', '=', section_id), '|', ('type', '=', type), ('type', '=', 'both')]"),
        'user_id': fields.many2one('res.users', 'Salesperson', select=True, track_visibility='onchange'),
        'referred': fields.char('Referred By', size=64),
        'date_open': fields.datetime('Opened', readonly=True),
        'day_open': fields.function(_compute_day, string='Days to Open', \
                                multi='day_open', type="float", store=True),
        'day_close': fields.function(_compute_day, string='Days to Close', \
                                multi='day_close', type="float", store=True),
        'state': fields.related('stage_id', 'state', type="selection", store=True,
                selection=crm.AVAILABLE_STATES, string="Status", readonly=True,
                help='The Status is set to \'Draft\', when a case is created. If the case is in progress the Status is set to \'Open\'. When the case is over, the Status is set to \'Done\'. If the case needs to be reviewed then the Status is  set to \'Pending\'.'),

        # Only used for type opportunity
        'probability': fields.float('Success Rate (%)',group_operator="avg"),
        'planned_revenue': fields.float('Expected Revenue', track_visibility='always'),
        'ref': fields.reference('Reference', selection=crm._links_get, size=128),
        'ref2': fields.reference('Reference 2', selection=crm._links_get, size=128),
        'phone': fields.char("Phone", size=64),
        'date_deadline': fields.date('Expected Closing', help="Estimate of the date on which the opportunity will be won."),
        'date_action': fields.date('Next Action Date', select=True),
        'title_action': fields.char('Next Action', size=64),
        'color': fields.integer('Color Index'),
        'partner_address_name': fields.related('partner_id', 'name', type='char', string='Partner Contact Name', readonly=True),
        'partner_address_email': fields.related('partner_id', 'email', type='char', string='Partner Contact Email', readonly=True),
        'company_currency': fields.related('company_id', 'currency_id', type='many2one', string='Currency', readonly=True, relation="res.currency"),
        'user_email': fields.related('user_id', 'email', type='char', string='User Email', readonly=True),
        'user_login': fields.related('user_id', 'login', type='char', string='User Login', readonly=True),

        # Fields for address, due to separation from crm and res.partner
        'street': fields.char('Street', size=128),
        'street2': fields.char('Street2', size=128),
        'zip': fields.char('Zip', change_default=True, size=24),
        'city': fields.char('City', size=128),
        'state_id': fields.many2one("res.country.state", 'State'),
        'country_id': fields.many2one('res.country', 'Country'),
        'phone': fields.char('Phone', size=64),
        'fax': fields.char('Fax', size=64),
        'mobile': fields.char('Mobile', size=64),
        'function': fields.char('Function', size=128),
        'title': fields.many2one('res.partner.title', 'Title'),
        'company_id': fields.many2one('res.company', 'Company', select=1),
        'payment_mode': fields.many2one('crm.payment.mode', 'Payment Mode', \
                            domain="[('section_id','=',section_id)]"),
        'planned_cost': fields.float('Planned Costs'),
    }

    _defaults = {
        'active': 1,
        'type': 'lead',
        'user_id': lambda s, cr, uid, c: s._get_default_user(cr, uid, c),
        'email_from': lambda s, cr, uid, c: s._get_default_email(cr, uid, c),
        'stage_id': lambda s, cr, uid, c: s._get_default_stage_id(cr, uid, c),
        'section_id': lambda s, cr, uid, c: s._get_default_section_id(cr, uid, c),
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.lead', context=c),
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
        'color': 0,
    }

    _sql_constraints = [
        ('check_probability', 'check(probability >= 0 and probability <= 100)', 'The probability of closing the deal should be between 0% and 100%!')
    ]

    def onchange_stage_id(self, cr, uid, ids, stage_id, context=None):
        if not stage_id:
            return {'value':{}}
        stage = self.pool.get('crm.case.stage').browse(cr, uid, stage_id, context)
        if not stage.on_change:
            return {'value':{}}
        return {'value':{'probability': stage.probability}}

    def on_change_partner(self, cr, uid, ids, partner_id, context=None):
        result = {}
        values = {}
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            values = {
                'partner_name' : partner.name,
                'street' : partner.street,
                'street2' : partner.street2,
                'city' : partner.city,
                'state_id' : partner.state_id and partner.state_id.id or False,
                'country_id' : partner.country_id and partner.country_id.id or False,
                'email_from' : partner.email,
                'phone' : partner.phone,
                'mobile' : partner.mobile,
                'fax' : partner.fax,
            }
        return {'value' : values}

    def on_change_user(self, cr, uid, ids, user_id, context=None):
        """ When changing the user, also set a section_id or restrict section id
            to the ones user_id is member of. """
        section_id = False
        if user_id:
            section_ids = self.pool.get('crm.case.section').search(cr, uid, ['|', ('user_id', '=', user_id), ('member_ids', '=', user_id)], context=context)
            if section_ids:
                section_id = section_ids[0]
        return {'value': {'section_id': section_id}}

    def _check(self, cr, uid, ids=False, context=None):
        """ Override of the base.stage method.
            Function called by the scheduler to process cases for date actions
            Only works on not done and cancelled cases
        """
        cr.execute('select * from crm_case \
                where (date_action_last<%s or date_action_last is null) \
                and (date_action_next<=%s or date_action_next is null) \
                and state not in (\'cancel\',\'done\')',
                (time.strftime("%Y-%m-%d %H:%M:%S"),
                    time.strftime('%Y-%m-%d %H:%M:%S')))

        ids2 = map(lambda x: x[0], cr.fetchall() or [])
        cases = self.browse(cr, uid, ids2, context=context)
        return self._action(cr, uid, cases, False, context=context)

    def stage_find(self, cr, uid, cases, section_id, domain=None, order='sequence', context=None):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - type: stage type must be the same or 'both'
            - section_id: if set, stages must belong to this section or
              be a default stage; if not set, stages must be default
              stages
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cr, uid, cases, context=context)
        # collect all section_ids
        section_ids = []
        types = ['both']
        if not cases :
            type = context.get('default_type')
            types += [type]
        if section_id:
            section_ids.append(section_id)
        for lead in cases:
            if lead.section_id:
                section_ids.append(lead.section_id.id)
            if lead.type not in types:
                types.append(lead.type)
        # OR all section_ids and OR with case_default
        search_domain = []
        if section_ids:
            search_domain += [('|')] * len(section_ids)
            for section_id in section_ids:
                search_domain.append(('section_ids', '=', section_id))
        else:
            search_domain.append(('case_default', '=', True))
        # AND with cases types
        search_domain.append(('type', 'in', types))
        # AND with the domain in parameter
        search_domain += list(domain)
        # perform search, return the first found
        stage_ids = self.pool.get('crm.case.stage').search(cr, uid, search_domain, order=order, context=context)
        if stage_ids:
            return stage_ids[0]
        return False

    def case_cancel(self, cr, uid, ids, context=None):
        """ Overrides case_cancel from base_stage to set probability """
        res = super(crm_lead, self).case_cancel(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'probability' : 0.0}, context=context)
        return res

    def case_reset(self, cr, uid, ids, context=None):
        """ Overrides case_reset from base_stage to set probability """
        res = super(crm_lead, self).case_reset(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'probability': 0.0}, context=context)
        return res

    def case_mark_lost(self, cr, uid, ids, context=None):
        """ Mark the case as lost: state=cancel and probability=0 """
        for lead in self.browse(cr, uid, ids):
            stage_id = self.stage_find(cr, uid, [lead], lead.section_id.id or False, [('probability', '=', 0.0),('on_change','=',True)], context=context)
            if stage_id:
                self.case_set(cr, uid, [lead.id], values_to_update={'probability': 0.0}, new_stage_id=stage_id, context=context)
        return True

    def case_mark_won(self, cr, uid, ids, context=None):
        """ Mark the case as won: state=done and probability=100 """
        for lead in self.browse(cr, uid, ids):
            stage_id = self.stage_find(cr, uid, [lead], lead.section_id.id or False, [('probability', '=', 100.0),('on_change','=',True)], context=context)
            if stage_id:
                self.case_set(cr, uid, [lead.id], values_to_update={'probability': 100.0}, new_stage_id=stage_id, context=context)
        return True

    def set_priority(self, cr, uid, ids, priority):
        """ Set lead priority
        """
        return self.write(cr, uid, ids, {'priority' : priority})

    def set_high_priority(self, cr, uid, ids, context=None):
        """ Set lead priority to high
        """
        return self.set_priority(cr, uid, ids, '1')

    def set_normal_priority(self, cr, uid, ids, context=None):
        """ Set lead priority to normal
        """
        return self.set_priority(cr, uid, ids, '3')

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
            field_info = self._all_columns.get(field_name)
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

        # Define the resulting type ('lead' or 'opportunity')
        data['type'] = self._merge_get_result_type(cr, uid, opportunities, context)
        return data

    def _mail_body(self, cr, uid, lead, fields, title=False, context=None):
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
                value = dict(key).get(lead[field_name], lead[field_name])
            elif field._type == 'many2one':
                if lead[field_name]:
                    value = lead[field_name].name_get()[0][1]
            elif field._type == 'many2many':
                if lead[field_name]:
                    for val in lead[field_name]:
                        field_value = val.name_get()[0][1]
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
                        name = "%s (%s)" % (attachment.name, count,),
                count+=1
                attachment.write(values)
        return True

    def merge_opportunity(self, cr, uid, ids, context=None):
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
            raise osv.except_osv(_('Warning!'), _('Please select more than one element (lead or opportunity) from the list view.'))

        opportunities = self.browse(cr, uid, ids, context=context)
        sequenced_opps = []
        for opportunity in opportunities:
            sequence = -1
            if opportunity.stage_id and opportunity.stage_id.state != 'cancel':
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

        # Merge messages and attachements into the first opportunity
        self._merge_opportunity_history(cr, uid, highest.id, tail_opportunities, context=context)
        self._merge_opportunity_attachments(cr, uid, highest.id, tail_opportunities, context=context)

        # Merge notifications about loss of information
        opportunities = [highest]
        opportunities.extend(opportunities_rest)
        self._merge_notify(cr, uid, highest, opportunities, context=context)
        # Check if the stage is in the stages of the sales team. If not, assign the stage with the lowest sequence
        if merged_data.get('section_id'):
            section_stage_ids = self.pool.get('crm.case.stage').search(cr, uid, [('section_ids', 'in', merged_data['section_id']), ('type', '=', merged_data.get('type'))], order='sequence', context=context)
            if merged_data.get('stage_id') not in section_stage_ids:
                merged_data['stage_id'] = section_stage_ids and section_stage_ids[0] or False
        # Write merged data into first opportunity
        self.write(cr, uid, [highest.id], merged_data, context=context)
        # Delete tail opportunities
        self.unlink(cr, uid, [x.id for x in tail_opportunities], context=context)

        return highest.id

    def _convert_opportunity_data(self, cr, uid, lead, customer, section_id=False, context=None):
        crm_stage = self.pool.get('crm.case.stage')
        contact_id = False
        if customer:
            contact_id = self.pool.get('res.partner').address_get(cr, uid, [customer.id])['default']
        if not section_id:
            section_id = lead.section_id and lead.section_id.id or False
        val = {
            'planned_revenue': lead.planned_revenue,
            'probability': lead.probability,
            'name': lead.name,
            'partner_id': customer and customer.id or False,
            'user_id': (lead.user_id and lead.user_id.id),
            'type': 'opportunity',
            'date_action': fields.datetime.now(),
            'date_open': fields.datetime.now(),
            'email_from': customer and customer.email or lead.email_from,
            'phone': customer and customer.phone or lead.phone,
        }
        if not lead.stage_id or lead.stage_id.type=='lead':
            val['stage_id'] = self.stage_find(cr, uid, [lead], section_id, [('state', '=', 'draft'),('type', 'in', ('opportunity','both'))], context=context)
        return val

    def convert_opportunity(self, cr, uid, ids, partner_id, user_ids=False, section_id=False, context=None):
        customer = False
        if partner_id:
            partner = self.pool.get('res.partner')
            customer = partner.browse(cr, uid, partner_id, context=context)
        for lead in self.browse(cr, uid, ids, context=context):
            if lead.state in ('done', 'cancel'):
                continue
            vals = self._convert_opportunity_data(cr, uid, lead, customer, section_id, context=context)
            self.write(cr, uid, [lead.id], vals, context=context)
        self.message_post(cr, uid, ids, body=_("Lead <b>converted into an Opportunity</b>"), subtype="crm.mt_lead_convert_to_opportunity", context=context)

        if user_ids or section_id:
            self.allocate_salesman(cr, uid, ids, user_ids, section_id, context=context)

        return True

    def _lead_create_contact(self, cr, uid, lead, name, is_company, parent_id=False, context=None):
        partner = self.pool.get('res.partner')
        vals = {'name': name,
            'user_id': lead.user_id.id,
            'comment': lead.description,
            'section_id': lead.section_id.id or False,
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
        partner_id = False
        if lead.partner_name and lead.contact_name:
            partner_id = self._lead_create_contact(cr, uid, lead, lead.partner_name, True, context=context)
            partner_id = self._lead_create_contact(cr, uid, lead, lead.contact_name, False, partner_id, context=context)
        elif lead.partner_name and not lead.contact_name:
            partner_id = self._lead_create_contact(cr, uid, lead, lead.partner_name, True, context=context)
        elif not lead.partner_name and lead.contact_name:
            partner_id = self._lead_create_contact(cr, uid, lead, lead.contact_name, False, context=context)
        elif lead.email_from and self.pool.get('res.partner')._parse_partner_name(lead.email_from, context=context)[0]:
            contact_name = self.pool.get('res.partner')._parse_partner_name(lead.email_from, context=context)[0]
            partner_id = self._lead_create_contact(cr, uid, lead, contact_name, False, context=context)
        else:
            raise osv.except_osv(
                _('Warning!'),
                _('No customer name defined. Please fill one of the following fields: Company Name, Contact Name or Email ("Name <email@address>")')
            )
        return partner_id

    def _lead_set_partner(self, cr, uid, lead, partner_id, context=None):
        """
        Assign a partner to a lead.

        :param object lead: browse record of the lead to process
        :param int partner_id: identifier of the partner to assign
        :return bool: True if the partner has properly been assigned
        """
        res = False
        res_partner = self.pool.get('res.partner')
        if partner_id:
            res_partner.write(cr, uid, partner_id, {'section_id': lead.section_id and lead.section_id.id or False})
            contact_id = res_partner.address_get(cr, uid, [partner_id])['default']
            res = lead.write({'partner_id': partner_id}, context=context)
            message = _("<b>Partner</b> set to <em>%s</em>." % (lead.partner_id.name))
            self.message_post(cr, uid, [lead.id], body=message, context=context)
        return res

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
        #TODO this is a duplication of the handle_partner_assignation method of crm_phonecall
        partner_ids = {}
        # If a partner_id is given, force this partner for all elements
        force_partner_id = partner_id
        for lead in self.browse(cr, uid, ids, context=context):
            # If the action is set to 'create' and no partner_id is set, create a new one
            if action == 'create':
                partner_id = force_partner_id or self._create_lead_partner(cr, uid, lead, context)
            self._lead_set_partner(cr, uid, lead, partner_id, context=context)
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
                value['section_id'] = team_id
            if user_ids:
                value['user_id'] = user_ids[index]
                # Cycle through user_ids
                index = (index + 1) % len(user_ids)
            if value:
                self.write(cr, uid, [lead_id], value, context=context)
        return True

    def schedule_phonecall(self, cr, uid, ids, schedule_time, call_summary, desc, phone, contact_name, user_id=False, section_id=False, categ_id=False, action='schedule', context=None):
        """
        :param string action: ('schedule','Schedule a call'), ('log','Log a call')
        """
        phonecall = self.pool.get('crm.phonecall')
        model_data = self.pool.get('ir.model.data')
        phonecall_dict = {}
        if not categ_id:
            res_id = model_data._get_id(cr, uid, 'crm', 'categ_phone2')
            if res_id:
                categ_id = model_data.browse(cr, uid, res_id, context=context).res_id
        for lead in self.browse(cr, uid, ids, context=context):
            if not section_id:
                section_id = lead.section_id and lead.section_id.id or False
            if not user_id:
                user_id = lead.user_id and lead.user_id.id or False
            vals = {
                'name': call_summary,
                'opportunity_id': lead.id,
                'user_id': user_id or False,
                'categ_id': categ_id or False,
                'description': desc or '',
                'date': schedule_time,
                'section_id': section_id or False,
                'partner_id': lead.partner_id and lead.partner_id.id or False,
                'partner_phone': phone or lead.phone or (lead.partner_id and lead.partner_id.phone or False),
                'partner_mobile': lead.partner_id and lead.partner_id.mobile or False,
                'priority': lead.priority,
            }
            new_id = phonecall.create(cr, uid, vals, context=context)
            phonecall.case_open(cr, uid, [new_id], context=context)
            if action == 'log':
                phonecall.case_close(cr, uid, [new_id], context=context)
            phonecall_dict[lead.id] = new_id
            self.schedule_phonecall_send_note(cr, uid, [lead.id], new_id, action, context=context)
        return phonecall_dict

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
                    (tree_view or False, 'tree'),
                    (False, 'calendar'), (False, 'graph')],
            'type': 'ir.actions.act_window',
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

    def action_makeMeeting(self, cr, uid, ids, context=None):
        """
        Open meeting's calendar view to schedule meeting on current opportunity.
        :return dict: dictionary value for created Meeting view
        """
        opportunity = self.browse(cr, uid, ids[0], context)
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'base_calendar', 'action_crm_meeting', context)
        res['context'] = {
            'default_opportunity_id': opportunity.id,
            'default_partner_id': opportunity.partner_id and opportunity.partner_id.id or False,
            'default_partner_ids' : opportunity.partner_id and [opportunity.partner_id.id] or False,
            'default_user_id': uid,
            'default_section_id': opportunity.section_id and opportunity.section_id.id or False,
            'default_email_from': opportunity.email_from,
            'default_name': opportunity.name,
        }
        return res

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('stage_id') and not vals.get('probability'):
            # change probability of lead(s) if required by stage
            stage = self.pool.get('crm.case.stage').browse(cr, uid, vals['stage_id'], context=context)
            if stage.on_change:
                vals['probability'] = stage.probability
        return super(crm_lead, self).write(cr, uid, ids, vals, context=context)

    def new_mail_send(self, cr, uid, ids, context=None):
        '''
        This function opens a window to compose an email, with the edi sale template message loaded by default
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time.'
        ir_model_data = self.pool.get('ir.model.data')
        try:
            template_id = ir_model_data.get_object_reference(cr, uid, 'crm', 'email_template_opportunity_mail')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference(cr, uid, 'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        if context is None:
            context = {}
        ctx = context.copy()
        ctx.update({
            'default_model': 'crm.lead',
            'default_res_id': ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    # ----------------------------------------
    # Mail Gateway
    # ----------------------------------------

    def message_get_reply_to(self, cr, uid, ids, context=None):
        """ Override to get the reply_to of the parent project. """
        return [lead.section_id.message_get_reply_to()[0] if lead.section_id else False
                    for lead in self.browse(cr, uid, ids, context=context)]

    def message_get_suggested_recipients(self, cr, uid, ids, context=None):
        recipients = super(crm_lead, self).message_get_suggested_recipients(cr, uid, ids, context=context)
        for lead in self.browse(cr, uid, ids, context=context):
            if lead.partner_id:
                self._message_add_suggested_recipient(cr, uid, recipients, lead, partner=lead.partner_id, reason=_('Customer'))
            elif lead.email_from:
                self._message_add_suggested_recipient(cr, uid, recipients, lead, email=lead.email_from, reason=_('Customer Email'))
        return recipients

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        desc = html2plaintext(msg.get('body')) if msg.get('body') else ''
        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'description': desc,
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
            'user_id': False,
        }
        if msg.get('author_id'):
            defaults.update(self.on_change_partner(cr, uid, None, msg.get('author_id'), context=context)['value'])
        if msg.get('priority') in dict(crm.AVAILABLE_PRIORITIES):
            defaults['priority'] = msg.get('priority')
        defaults.update(custom_values)
        return super(crm_lead, self).message_new(cr, uid, msg, custom_values=defaults, context=context)

    def message_update(self, cr, uid, ids, msg, update_vals=None, context=None):
        """ Overrides mail_thread message_update that is called by the mailgateway
            through message_process.
            This method updates the document according to the email.
        """
        if isinstance(ids, (str, int, long)):
            ids = [ids]
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

        return super(crm_lead, self).message_update(cr, uid, ids, msg, update_vals=update_vals, context=context)

    # ----------------------------------------
    # OpenChatter methods and notifications
    # ----------------------------------------

    def schedule_phonecall_send_note(self, cr, uid, ids, phonecall_id, action, context=None):
        phonecall = self.pool.get('crm.phonecall').browse(cr, uid, [phonecall_id], context=context)[0]
        if action == 'log':
            prefix = 'Logged'
        else:
            prefix = 'Scheduled'
        suffix = ' %s' % phonecall.description
        message = _("%s a call for %s.%s") % (prefix, phonecall.date, suffix)
        return self.message_post(cr, uid, ids, body=message, context=context)

    def onchange_state(self, cr, uid, ids, state_id, context=None):
        if state_id:
            country_id=self.pool.get('res.country.state').browse(cr, uid, state_id, context).country_id.id
            return {'value':{'country_id':country_id}}
        return {}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
