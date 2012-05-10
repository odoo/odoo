# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv
from datetime import datetime
import crm
import time
from tools.translate import _
from crm import crm_case
import binascii
import tools
from mail.mail_message import to_email

CRM_LEAD_PENDING_STATES = (
    crm.AVAILABLE_STATES[2][0], # Cancelled
    crm.AVAILABLE_STATES[3][0], # Done
    crm.AVAILABLE_STATES[4][0], # Pending
)

class crm_lead(crm_case, osv.osv):
    """ CRM Lead Case """
    _name = "crm.lead"
    _description = "Lead/Opportunity"
    _order = "priority,date_action,id desc"
    _inherit = ['ir.needaction_mixin', 'mail.thread','res.partner']

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        access_rights_uid = access_rights_uid or uid
        stage_obj = self.pool.get('crm.case.stage')
        order = stage_obj._order
        if read_group_order == 'stage_id desc':
            # lame hack to allow reverting search, should just work in the trivial case
            order = "%s desc" % order
        stage_ids = stage_obj._search(cr, uid, ['|', ('id','in',ids),('case_default','=',1)], order=order,
                                      access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x,y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))
        return result

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    def _compute_day(self, cr, uid, ids, fields, args, context=None):
        """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Openday’s IDs
        @return: difference between current date and log date
        @param context: A standard dictionary for contextual values
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

    def _get_email_subject(self, cr, uid, ids, fields, args, context=None):
        res = {}
        for obj in self.browse(cr, uid, ids, context=context):
            res[obj.id] = ''
            for msg in obj.message_ids:
                if msg.email_from:
                    res[obj.id] = msg.subject
                    break
        return res

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner', ondelete='set null',
            select=True, help="Optional linked partner, usually after conversion of the lead"),

        'id': fields.integer('ID', readonly=True),
        'name': fields.char('Name', size=64, select=1),
        'active': fields.boolean('Active', required=False),
        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),
        'email_from': fields.char('Email', size=128, help="E-mail address of the contact", select=1),
        'section_id': fields.many2one('crm.case.section', 'Sales Team', \
                        select=True, help='When sending mails, the default email address is taken from the sales team.'),
        'create_date': fields.datetime('Creation Date' , readonly=True),
        'email_cc': fields.text('Global CC', size=252 , help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'description': fields.text('Notes'),
        'write_date': fields.datetime('Update Date' , readonly=True),

        'categ_id': fields.many2one('crm.case.categ', 'Category', \
            domain="['|',('section_id','=',section_id),('section_id','=',False), ('object_id.model', '=', 'crm.lead')]"),
        'type_id': fields.many2one('crm.case.resource.type', 'Campaign', \
            domain="['|',('section_id','=',section_id),('section_id','=',False)]", help="From which campaign (seminar, marketing campaign, mass mailing, ...) did this contact come from?"),
        'channel_id': fields.many2one('crm.case.channel', 'Channel', help="Communication channel (mail, direct, phone, ...)"),
        'contact_name': fields.char('Contact Name', size=64),
        'partner_name': fields.char("Customer Name", size=64,help='The name of the future partner company that will be created while converting the lead into opportunity', select=1),
        'opt_in': fields.boolean('Opt-In', oldname='optin', help="If opt-in is checked, this contact has accepted to receive emails."),
        'opt_out': fields.boolean('Opt-Out', oldname='optout', help="If opt-out is checked, this contact has refused to receive emails or unsubscribed to a campaign."),
        'type':fields.selection([ ('lead','Lead'), ('opportunity','Opportunity'), ],'Type', help="Type is used to separate Leads and Opportunities"),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority', select=True),
        'date_closed': fields.datetime('Closed', readonly=True),
        'stage_id': fields.many2one('crm.case.stage', 'Stage', domain="[('section_ids', '=', section_id)]"),
        'user_id': fields.many2one('res.users', 'Salesman'),
        'referred': fields.char('Referred By', size=64),
        'date_open': fields.datetime('Opened', readonly=True),
        'day_open': fields.function(_compute_day, string='Days to Open', \
                                multi='day_open', type="float", store=True),
        'day_close': fields.function(_compute_day, string='Days to Close', \
                                multi='day_close', type="float", store=True),
        'state': fields.selection(crm.AVAILABLE_STATES, 'State', size=16, readonly=True,
                                  help='The state is set to \'Draft\', when a case is created.\
                                  \nIf the case is in progress the state is set to \'Open\'.\
                                  \nWhen the case is over, the state is set to \'Done\'.\
                                  \nIf the case needs to be reviewed then the state is set to \'Pending\'.'),
        'message_ids': fields.one2many('mail.message', 'res_id', 'Messages', domain=[('model','=',_name)]),
        'subjects': fields.function(_get_email_subject, fnct_search=_history_search, string='Subject of Email', type='char', size=64),

        # Only used for type opportunity
        'probability': fields.float('Probability (%)',group_operator="avg"),
        'planned_revenue': fields.float('Expected Revenue'),
        'ref': fields.reference('Reference', selection=crm._links_get, size=128),
        'ref2': fields.reference('Reference 2', selection=crm._links_get, size=128),
        'phone': fields.char("Phone", size=64),
        'date_deadline': fields.date('Expected Closing'),
        'date_action': fields.date('Next Action Date', select=True),
        'title_action': fields.char('Next Action', size=64),
        'stage_id': fields.many2one('crm.case.stage', 'Stage', domain="[('section_ids', '=', section_id)]"),
        'color': fields.integer('Color Index'),
        'partner_address_name': fields.related('partner_id', 'name', type='char', string='Partner Contact Name', readonly=True),
        'partner_address_email': fields.related('partner_id', 'email', type='char', string='Partner Contact Email', readonly=True),
        'company_currency': fields.related('company_id', 'currency_id', 'symbol', type='char', string='Company Currency', readonly=True),
        'user_email': fields.related('user_id', 'user_email', type='char', string='User Email', readonly=True),
        'user_login': fields.related('user_id', 'login', type='char', string='User Login', readonly=True),

    }

    _defaults = {
        'active': lambda *a: 1,
        'user_id': crm_case._get_default_user,
        'email_from': crm_case._get_default_email,
        'state': lambda *a: 'draft',
        'type': lambda *a: 'lead',
        'section_id': crm_case._get_section,
        'company_id': lambda s, cr, uid, c: s.pool.get('res.company')._company_default_get(cr, uid, 'crm.lead', context=c),
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
        'color': 0,
    }

    def get_needaction_user_ids(self, cr, uid, ids, context=None):
        result = dict.fromkeys(ids, [])
        for obj in self.browse(cr, uid, ids, context=context):
            # salesman must perform an action when in draft mode
            if obj.state == 'draft' and obj.user_id:
                result[obj.id] = [obj.user_id.id]
        return result
    
    def create(self, cr, uid, vals, context=None):
        obj_id = super(crm_lead, self).create(cr, uid, vals, context)
        self.create_send_note(cr, uid, [obj_id], context=context)
        return obj_id
    
    def on_change_opt_in(self, cr, uid, ids, opt_in):
        return {'value':{'opt_in':opt_in,'opt_out':False}}

    def on_change_opt_out(self, cr, uid, ids, opt_out):
        return {'value':{'opt_out':opt_out,'opt_in':False}}

    def onchange_stage_id(self, cr, uid, ids, stage_id, context={}):
        if not stage_id:
            return {'value':{}}
        stage = self.pool.get('crm.case.stage').browse(cr, uid, stage_id, context)
        if not stage.on_change:
            return {'value':{}}
        return {'value':{'probability': stage.probability}}

    def stage_find_percent(self, cr, uid, percent, section_id):
        """ Return the first stage with a probability == percent
        """
        stage_pool = self.pool.get('crm.case.stage')
        if section_id :
            ids = stage_pool.search(cr, uid, [("probability", '=', percent), ("section_ids", 'in', [section_id])])
        else :
            ids = stage_pool.search(cr, uid, [("probability", '=', percent)])

        if ids:
            return ids[0]
        return False

    def stage_find_lost(self, cr, uid, section_id):
        return self.stage_find_percent(cr, uid, 0.0, section_id)

    def stage_find_won(self, cr, uid, section_id):
        return self.stage_find_percent(cr, uid, 100.0, section_id)

    def case_open(self, cr, uid, ids, context=None):
        for lead in self.browse(cr, uid, ids, context=context):
            if lead.state == 'draft':
                value = {'date_open': time.strftime('%Y-%m-%d %H:%M:%S')}
                self.write(cr, uid, [lead.id], value)
                if lead.type == 'opportunity' and not lead.stage_id:
                    stage_id = self.stage_find(cr, uid, lead.section_id.id or False, [('sequence','>',0)])
                    if stage_id:
                        self.stage_set(cr, uid, [lead.id], stage_id)
        res = super(crm_lead, self).case_open(cr, uid, ids, context)
        return res

    def case_close(self, cr, uid, ids, context=None):
        res = super(crm_lead, self).case_close(cr, uid, ids, context)
        self.write(cr, uid, ids, {'date_closed': time.strftime('%Y-%m-%d %H:%M:%S')})
        return res

    def case_cancel(self, cr, uid, ids, context=None):
        """Overrides cancel for crm_case for setting probability
        """
        res = super(crm_lead, self).case_cancel(cr, uid, ids, context)
        self.write(cr, uid, ids, {'probability' : 0.0})
        return res

    def case_reset(self, cr, uid, ids, context=None):
        """Overrides reset as draft in order to set the stage field as empty
        """
        res = super(crm_lead, self).case_reset(cr, uid, ids, context)
        self.write(cr, uid, ids, {'stage_id': False, 'probability': 0.0})
        return res

    def case_mark_lost(self, cr, uid, ids, context=None):
        """Mark the case as lost: state = done and probability = 0%
        """
        res = super(crm_lead, self).case_close(cr, uid, ids, context)
        self.write(cr, uid, ids, {'probability' : 0.0})
        for lead in self.browse(cr, uid, ids):
            stage_id = self.stage_find_lost(cr, uid, lead.section_id.id or False)
            if stage_id:
                self.stage_set(cr, uid, [lead.id], stage_id)
        return res

    def case_mark_won(self, cr, uid, ids, context=None):
        """Mark the case as lost: state = done and probability = 0%
        """
        res = super(crm_lead, self).case_close(cr, uid, ids, context=None)
        self.write(cr, uid, ids, {'probability' : 100.0})
        for lead in self.browse(cr, uid, ids):
            stage_id = self.stage_find_won(cr, uid, lead.section_id.id or False)
            if stage_id:
                self.stage_set(cr, uid, [lead.id], stage_id)
            self.case_mark_won_send_note(cr, uid, [lead.id], context=context)
        return res

    def set_priority(self, cr, uid, ids, priority):
        """Set lead priority
        """
        return self.write(cr, uid, ids, {'priority' : priority})

    def set_high_priority(self, cr, uid, ids, context=None):
        """Set lead priority to high
        """
        return self.set_priority(cr, uid, ids, '1')

    def set_normal_priority(self, cr, uid, ids, context=None):
        """Set lead priority to normal
        """
        return self.set_priority(cr, uid, ids, '3')


    def _merge_data(self, cr, uid, ids, oldest, fields, context=None):
        # prepare opportunity data into dictionary for merging
        opportunities = self.browse(cr, uid, ids, context=context)
        def _get_first_not_null(attr):
            if hasattr(oldest, attr):
                return getattr(oldest, attr)
            for opportunity in opportunities:
                if hasattr(opportunity, attr):
                    return getattr(opportunity, attr)
            return False

        def _get_first_not_null_id(attr):
            res = _get_first_not_null(attr)
            return res and res.id or False

        def _concat_all(attr):
            return ', '.join(filter(lambda x: x, [getattr(opportunity, attr) or '' for opportunity in opportunities if hasattr(opportunity, attr)]))

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
        return data

    def _merge_find_oldest(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        #TOCHECK: where pass 'convert' in context ?
        if context.get('convert'):
            ids = list(set(ids) - set(context.get('lead_ids', False)) )

        #search opportunities order by create date
        opportunity_ids = self.search(cr, uid, [('id', 'in', ids)], order='create_date' , context=context)
        oldest_id = opportunity_ids[0]
        return self.browse(cr, uid, oldest_id, context=context)

    def _mail_body_text(self, cr, uid, lead, fields, title=False, context=None):
        body = []
        if title:
            body.append("%s\n" % (title))
        for field_name in fields:
            field_info = self._all_columns.get(field_name)
            if field_info is None:
                continue
            field = field_info.column
            value = None

            if field._type == 'selection':
                if hasattr(field.selection, '__call__'):
                    key = field.selection(self, cr, uid, context=context)
                else:
                    key = field.selection
                value = dict(key).get(lead[field_name], lead[field_name])
            elif field._type == 'many2one':
                if lead[field_name]:
                    value = lead[field_name].name_get()[0][1]
            else:
                value = lead[field_name]

            body.append("%s: %s" % (field.string, value or ''))
        return "\n".join(body + ['---'])

    def _merge_notification(self, cr, uid, opportunity_id, opportunities, context=None):
        #TOFIX: mail template should be used instead of fix body, subject text
        details = []
        merge_message = _('Merged opportunities')
        subject = [merge_message]
        fields = ['name', 'partner_id', 'stage_id', 'section_id', 'user_id', 'categ_id', 'channel_id', 'company_id', 'contact_name',
                  'email_from', 'phone', 'fax', 'mobile', 'state_id', 'description', 'probability', 'planned_revenue',
                  'country_id', 'city', 'street', 'street2', 'zip']
        for opportunity in opportunities:
            subject.append(opportunity.name)
            title = "%s : %s" % (merge_message, opportunity.name)
            details.append(self._mail_body_text(cr, uid, opportunity, fields, title=title, context=context))

        subject = subject[0] + ", ".join(subject[1:])
        details = "\n\n".join(details)
        return self.message_append_note(cr, uid, [opportunity_id], subject=subject, body=details)

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
        attachment = self.pool.get('ir.attachment')

        # return attachments of opportunity
        def _get_attachments(opportunity_id):
            attachment_ids = attachment.search(cr, uid, [('res_model', '=', self._name), ('res_id', '=', opportunity_id)], context=context)
            return attachment.browse(cr, uid, attachment_ids, context=context)

        count = 1
        first_attachments = _get_attachments(opportunity_id)
        for opportunity in opportunities:
            attachments = _get_attachments(opportunity.id)
            for first in first_attachments:
                for attachment in attachments:
                    if attachment.name == first.name:
                        values = dict(
                            name = "%s (%s)" % (attachment.name, count,),
                            res_id = opportunity_id,
                        )
                        attachment.write(values)
                        count+=1

        return True

    def merge_opportunity(self, cr, uid, ids, context=None):
        """
        To merge opportunities
            :param ids: list of opportunities ids to merge
        """
        if context is None: context = {}

        #TOCHECK: where pass lead_ids in context?
        lead_ids = context and context.get('lead_ids', []) or []

        if len(ids) <= 1:
            raise osv.except_osv(_('Warning !'),_('Please select more than one opportunity from the list view.'))

        ctx_opportunities = self.browse(cr, uid, lead_ids, context=context)
        opportunities = self.browse(cr, uid, ids, context=context)
        opportunities_list = list(set(opportunities) - set(ctx_opportunities))
        oldest = self._merge_find_oldest(cr, uid, ids, context=context)
        if ctx_opportunities :
            first_opportunity = ctx_opportunities[0]
            tail_opportunities = opportunities_list
        else:
            first_opportunity = opportunities_list[0]
            tail_opportunities = opportunities_list[1:]

        fields = ['partner_id', 'title', 'name', 'categ_id', 'channel_id', 'city', 'company_id', 'contact_name', 'country_id', 'type_id', 'user_id', 'section_id', 'state_id', 'description', 'email', 'fax', 'mobile',
            'partner_name', 'phone', 'probability', 'planned_revenue', 'street', 'street2', 'zip', 'create_date', 'date_action_last',
            'date_action_next', 'email_from', 'email_cc', 'partner_name']

        data = self._merge_data(cr, uid, ids, oldest, fields, context=context)

        # merge data into first opportunity
        self.write(cr, uid, [first_opportunity.id], data, context=context)

        #copy message and attachements into the first opportunity
        self._merge_opportunity_history(cr, uid, first_opportunity.id, tail_opportunities, context=context)
        self._merge_opportunity_attachments(cr, uid, first_opportunity.id, tail_opportunities, context=context)

        #Notification about loss of information
        self._merge_notification(cr, uid, first_opportunity, opportunities, context=context)
        #delete tail opportunities
        self.unlink(cr, uid, [x.id for x in tail_opportunities], context=context)

        #open first opportunity
        self.case_open(cr, uid, [first_opportunity.id])
        return first_opportunity.id

    def _convert_opportunity_data(self, cr, uid, lead, customer, section_id=False, context=None):
        crm_stage = self.pool.get('crm.case.stage')
        contact_id = False
        if customer:
            contact_id = self.pool.get('res.partner').address_get(cr, uid, [customer.id])['default']
        if not section_id:
            section_id = lead.section_id and lead.section_id.id or False
        if section_id:
            stage_ids = crm_stage.search(cr, uid, [('sequence','>=',1), ('section_ids','=', section_id)])
        else:
            stage_ids = crm_stage.search(cr, uid, [('sequence','>=',1)])
        stage_id = stage_ids and stage_ids[0] or False
        return {
                'planned_revenue': lead.planned_revenue,
                'probability': lead.probability,
                'name': lead.name,
                'partner_id': customer and customer.id or False,
                'user_id': (lead.user_id and lead.user_id.id),
                'type': 'opportunity',
                'stage_id': stage_id or False,
                'date_action': time.strftime('%Y-%m-%d %H:%M:%S'),
                'date_open': time.strftime('%Y-%m-%d %H:%M:%S'),
        }

    def convert_opportunity(self, cr, uid, ids, partner_id, user_ids=False, section_id=False, context=None):
        partner = self.pool.get('res.partner')
        mail_message = self.pool.get('mail.message')
        customer = False
        if partner_id:
            customer = partner.browse(cr, uid, partner_id, context=context)
        for lead in self.browse(cr, uid, ids, context=context):
            if lead.state in ('done', 'cancel'):
                continue
            if user_ids or section_id:
                self.allocate_salesman(cr, uid, [lead.id], user_ids, section_id, context=context)

            vals = self._convert_opportunity_data(cr, uid, lead, customer, section_id, context=context)
            self.write(cr, uid, [lead.id], vals, context=context)

            self.convert_opportunity_send_note(cr, uid, lead, context=context)
            #TOCHECK: why need to change partner details in all messages of lead ?
            if lead.partner_id:
                msg_ids = [ x.id for x in lead.message_ids]
                mail_message.write(cr, uid, msg_ids, {
                        'partner_id': lead.partner_id.id
                    }, context=context)
        return True

    def _lead_create_contact(self, cr, uid, lead, name, is_company, parent_id=False, context=None):
        partner = self.pool.get('res.partner')
        vals = { 'name': name,
            'user_id': lead.user_id.id,
            'comment': lead.description,
            'section_id': lead.section_id.id or False,
            'parent_id': parent_id,
            'phone': lead.phone,
            'mobile': lead.mobile,
            'email': lead.email_from and to_email(lead.email_from)[0],
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
        partner = partner.create(cr, uid,vals, context)
        return partner

    def _create_lead_partner(self, cr, uid, lead, context=None):
        partner_id =  False
        if lead.partner_name and lead.contact_name:
            partner_id = self._lead_create_contact(cr, uid, lead, lead.partner_name, True, context=context)
            self._lead_create_contact(cr, uid, lead, lead.contact_name, False, partner_id, context=context)
        elif lead.partner_name and not lead.contact_name:
            partner_id = self._lead_create_contact(cr, uid, lead, lead.partner_name, True, context=context)
        elif not lead.partner_name and lead.contact_name:
            partner_id = self._lead_create_contact(cr, uid, lead, lead.contact_name, False, context=context)
        else:
            partner_id = self._lead_create_contact(cr, uid, lead, lead.name, False, context=context)
        return partner_id

    def _lead_set_partner(self, cr, uid, lead, partner_id, context=None):
        res = False
        res_partner = self.pool.get('res.partner')
        if partner_id:
            res_partner.write(cr, uid, partner_id, {'section_id': lead.section_id.id or False})
            contact_id = res_partner.address_get(cr, uid, [partner_id])['default']
            res = lead.write({'partner_id' : partner_id, }, context=context)
            self._lead_set_partner_send_note(cr, uid, [lead.id], context)
        return res

    def convert_partner(self, cr, uid, ids, action='create', partner_id=False, context=None):
        """
        This function convert partner based on action.
        if action is 'create', create new partner with contact and assign lead to new partner_id.
        otherwise assign lead to specified partner_id
        """
        if context is None:
            context = {}
        partner_ids = {}
        for lead in self.browse(cr, uid, ids, context=context):
            if action == 'create':
                if not partner_id:
                    partner_id = self._create_lead_partner(cr, uid, lead, context)
            self._lead_set_partner(cr, uid, lead, partner_id, context=context)
            partner_ids[lead.id] = partner_id
        return partner_ids

    def _send_mail_to_salesman(self, cr, uid, lead, context=None):
        """
        Send mail to salesman with updated Lead details.
        @ lead: browse record of 'crm.lead' object.
        """
        #TOFIX: mail template should be used here instead of fix subject, body text.
        message = self.pool.get('mail.message')
        email_to = lead.user_id and lead.user_id.user_email
        if not email_to:
            return False

        email_from = lead.section_id and lead.section_id.user_id and lead.section_id.user_id.user_email or email_to
        partner = lead.partner_id and lead.partner_id.name or lead.partner_name
        subject = "lead %s converted into opportunity" % lead.name
        body = "Info \n Id : %s \n Subject: %s \n Partner: %s \n Description : %s " % (lead.id, lead.name, lead.partner_id.name, lead.description)
        return message.schedule_with_attach(cr, uid, email_from, [email_to], subject, body)


    def allocate_salesman(self, cr, uid, ids, user_ids, team_id=False, context=None):
        index = 0
        for lead_id in ids:
            value = {}
            if team_id:
                value['section_id'] = team_id
            if index < len(user_ids):
                value['user_id'] = user_ids[index]
                index += 1
            if value:
                self.write(cr, uid, [lead_id], value, context=context)
        return True

    def schedule_phonecall(self, cr, uid, ids, schedule_time, call_summary, desc, phone, contact_name, user_id=False, section_id=False, categ_id=False, action='schedule', context=None):
        """
        action :('schedule','Schedule a call'), ('log','Log a call')
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
                    'name' : call_summary,
                    'opportunity_id' : lead.id,
                    'user_id' : user_id or False,
                    'categ_id' : categ_id or False,
                    'description' : desc or '',
                    'date' : schedule_time,
                    'section_id' : section_id or False,
                    'partner_id': lead.partner_id and lead.partner_id.id or False,
                    'partner_phone' : phone or lead.phone or (lead.partner_id and lead.partner_id.phone or False),
                    'partner_mobile' : lead.partner_id and lead.partner_id.mobile or False,
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

        # Get Opportunity views
        form_view = models_data.get_object_reference(cr, uid, 'crm', 'crm_case_form_view_oppor')
        tree_view = models_data.get_object_reference(cr, uid, 'crm', 'crm_case_tree_view_oppor')
        return {
                'name': _('Opportunity'),
                'view_type': 'form',
                'view_mode': 'tree, form',
                'res_model': 'crm.lead',
                'domain': [('type', '=', 'opportunity')],
                'res_id': int(opportunity_id),
                'view_id': False,
                'views': [(form_view and form_view[1] or False, 'form'),
                          (tree_view and tree_view[1] or False, 'tree'),
                          (False, 'calendar'), (False, 'graph')],
                'type': 'ir.actions.act_window',
        }


    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """Automatically calls when new email message arrives"""
        res_id = super(crm_lead, self).message_new(cr, uid, msg, custom_values=custom_values, context=context)
        subject = msg.get('subject')  or _("No Subject")
        body = msg.get('body_text')

        msg_from = msg.get('from')
        priority = msg.get('priority')
        vals = {
            'name': subject,
            'email_from': msg_from,
            'email_cc': msg.get('cc'),
            'description': body,
            'user_id': False,
        }
        if priority:
            vals['priority'] = priority
        vals.update(self.message_partner_by_email(cr, uid, msg.get('from', False)))
        self.write(cr, uid, [res_id], vals, context)
        return res_id

    def message_update(self, cr, uid, ids, msg, vals=None, default_act='pending', context=None):
        if isinstance(ids, (str, int, long)):
            ids = [ids]
        if vals == None:
            vals = {}
        super(crm_lead, self).message_update(cr, uid, ids, msg, context=context)

        if msg.get('priority') in dict(crm.AVAILABLE_PRIORITIES):
            vals['priority'] = msg.get('priority')
        maps = {
            'cost':'planned_cost',
            'revenue': 'planned_revenue',
            'probability':'probability'
        }
        vls = {}
        for line in msg['body_text'].split('\n'):
            line = line.strip()
            res = tools.misc.command_re.match(line)
            if res and maps.get(res.group(1).lower()):
                key = maps.get(res.group(1).lower())
                vls[key] = res.group(2).lower()
        vals.update(vls)

        # Unfortunately the API is based on lists
        # but we want to update the state based on the
        # previous state, so we have to loop:
        for case in self.browse(cr, uid, ids, context=context):
            values = dict(vals)
            if case.state in CRM_LEAD_PENDING_STATES:
                #re-open
                values.update(state=crm.AVAILABLE_STATES[1][0])
                if not case.date_open:
                    values['date_open'] = time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
            res = self.write(cr, uid, [case.id], values, context=context)
        return res

    def action_makeMeeting(self, cr, uid, ids, context=None):
        """
        This opens Meeting's calendar view to schedule meeting on current Opportunity
        @return : Dictionary value for created Meeting view
        """
        if context is None:
            context = {}
        value = {}
        data_obj = self.pool.get('ir.model.data')
        for opp in self.browse(cr, uid, ids, context=context):
            # Get meeting views
            tree_view = data_obj.get_object_reference(cr, uid, 'crm', 'crm_case_tree_view_meet')
            form_view = data_obj.get_object_reference(cr, uid, 'crm', 'crm_case_form_view_meet')
            calander_view = data_obj.get_object_reference(cr, uid, 'crm', 'crm_case_calendar_view_meet')
            search_view = data_obj.get_object_reference(cr, uid, 'crm', 'view_crm_case_meetings_filter')
            context.update({
                'default_opportunity_id': opp.id,
                'default_partner_id': opp.partner_id and opp.partner_id.id or False,
                'default_user_id': uid,
                'default_section_id': opp.section_id and opp.section_id.id or False,
                'default_email_from': opp.email_from,
                'default_state': 'open',
                'default_name': opp.name
            })
            value = {
                'name': _('Meetings'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'calendar,form,tree',
                'res_model': 'crm.meeting',
                'view_id': False,
                'views': [(calander_view and calander_view[1] or False, 'calendar'), (form_view and form_view[1] or False, 'form'), (tree_view and tree_view[1] or False, 'tree')],
                'type': 'ir.actions.act_window',
                'search_view_id': search_view and search_view[1] or False,
                'nodestroy': True
            }
        return value


    def unlink(self, cr, uid, ids, context=None):
        for lead in self.browse(cr, uid, ids, context):
            if (not lead.section_id.allow_unlink) and (lead.state != 'draft'):
                raise osv.except_osv(_('Error'),
                    _("You cannot delete lead '%s'; it must be in state 'Draft' to be deleted. " \
                      "You should better cancel it, instead of deleting it.") % lead.name)
        return super(crm_lead, self).unlink(cr, uid, ids, context)


    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}

        if 'date_closed' in vals:
            return super(crm_lead,self).write(cr, uid, ids, vals, context=context)

        if vals.get('stage_id'):
            stage = self.pool.get('crm.case.stage').browse(cr, uid, vals['stage_id'], context=context)
            # change probability of lead(s) if required by stage
            if not vals.get('probability') and stage.on_change:
                vals['probability'] = stage.probability
            for case in self.browse(cr, uid, ids, context=context):
                message = _("Stage changed to <b>%s</b>.") % (stage.name)
                case.message_append_note(body=message)
        return super(crm_lead,self).write(cr, uid, ids, vals, context)
    
    # ----------------------------------------
    # OpenChatter methods and notifications
    # ----------------------------------------

    def message_get_subscribers(self, cr, uid, ids, context=None):
        sub_ids = self.message_get_subscribers_ids(cr, uid, ids, context=context)
        # add salesman to the subscribers
        for obj in self.browse(cr, uid, ids, context=context):
            if obj.user_id:
                sub_ids.append(obj.user_id.id)
        return self.pool.get('res.users').read(cr, uid, sub_ids, context=context)
    
    def case_get_note_msg_prefix(self, cr, uid, lead, context=None):
        if isinstance(lead, (int, long)):
            lead = self.browse(cr, uid, [lead], context=context)[0]
        return ('Opportunity' if lead.type == 'opportunity' else 'Lead')
    
    def create_send_note(self, cr, uid, ids, context=None):
        for id in ids:
            message = _("%s has been <b>created</b>.")% (self.case_get_note_msg_prefix(cr, uid, id, context=context))
            self.message_append_note(cr, uid, [id], body=message, context=context)
        return True

    def case_mark_lost_send_note(self, cr, uid, ids, context=None):
        message = _("Opportunity has been <b>lost</b>.")
        return self.message_append_note(cr, uid, ids, body=message, context=context)

    def case_mark_won_send_note(self, cr, uid, ids, context=None):
        message = _("Opportunity has been <b>won</b>.")
        return self.message_append_note(cr, uid, ids, body=message, context=context)

    def schedule_phonecall_send_note(self, cr, uid, ids, phonecall_id, action, context=None):
        phonecall = self.pool.get('crm.phonecall').browse(cr, uid, [phonecall_id], context=context)[0]
        if action == 'log': prefix = 'Logged'
        else: prefix = 'Scheduled'
        message = _("<b>%s a call</b> for the <em>%s</em>.") % (prefix, phonecall.date)
        return self. message_append_note(cr, uid, ids, body=message, context=context)

    def _lead_set_partner_send_note(self, cr, uid, ids, context=None):
        for lead in self.browse(cr, uid, ids, context=context):
            message = _("%s <b>partner</b> is now set to <em>%s</em>." % (self.case_get_note_msg_prefix(cr, uid, lead, context=context), lead.partner_id.name))
            lead.message_append_note(body=message)
        return True
    
    def convert_opportunity_send_note(self, cr, uid, lead, context=None):
        message = _("Lead has been <b>converted to an opportunity</b>.")
        lead.message_append_note(body=message)
        return True

crm_lead()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
