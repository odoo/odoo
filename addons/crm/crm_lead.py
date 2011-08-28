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
    _inherit = ['mail.thread','res.partner.address']

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
        # Overridden from res.partner.address:
        'partner_id': fields.many2one('res.partner', 'Partner', ondelete='set null',
            select=True, help="Optional linked partner, usually after conversion of the lead"),

        'id': fields.integer('ID'),
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
        'partner_name': fields.char("Customer Name", size=64,help='The name of the future partner that will be created while converting the into opportunity', select=1),
        'optin': fields.boolean('Opt-In', help="If opt-in is checked, this contact has accepted to receive emails."),
        'optout': fields.boolean('Opt-Out', help="If opt-out is checked, this contact has refused to receive emails or unsubscribed to a campaign."),
        'type':fields.selection([ ('lead','Lead'), ('opportunity','Opportunity'), ],'Type', help="Type is used to separate Leads and Opportunities"),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
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
        'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact', domain="[('partner_id','=',partner_id)]"), 
        'probability': fields.float('Probability (%)',group_operator="avg"),
        'planned_revenue': fields.float('Expected Revenue'),
        'ref': fields.reference('Reference', selection=crm._links_get, size=128),
        'ref2': fields.reference('Reference 2', selection=crm._links_get, size=128),
        'phone': fields.char("Phone", size=64),
        'date_deadline': fields.date('Expected Closing'),
        'date_action': fields.date('Next Action Date'),
        'title_action': fields.char('Next Action', size=64),
        'stage_id': fields.many2one('crm.case.stage', 'Stage', domain="[('section_ids', '=', section_id)]"),
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
        #'stage_id': _get_stage_id,
    }

    def onchange_partner_address_id(self, cr, uid, ids, add, email=False):
        """This function returns value of partner email based on Partner Address
        """
        if not add:
            return {'value': {'email_from': False, 'country_id': False}}
        address = self.pool.get('res.partner.address').browse(cr, uid, add)
        return {'value': {'email_from': address.email, 'phone': address.phone, 'country_id': address.country_id.id}}

    def on_change_optin(self, cr, uid, ids, optin):
        return {'value':{'optin':optin,'optout':False}}

    def on_change_optout(self, cr, uid, ids, optout):
        return {'value':{'optout':optout,'optin':False}}

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

    def case_open(self, cr, uid, ids, *args):
        for l in self.browse(cr, uid, ids):
            # When coming from draft override date and stage otherwise just set state
            if l.state == 'draft':
                if l.type == 'lead':
                    message = _("The lead '%s' has been opened.") % l.name
                elif l.type == 'opportunity':
                    message = _("The opportunity '%s' has been opened.") % l.name
                else:
                    message = _("The case '%s' has been opened.") % l.name
                self.log(cr, uid, l.id, message)
                value = {'date_open': time.strftime('%Y-%m-%d %H:%M:%S')}
                self.write(cr, uid, [l.id], value)
                if l.type == 'opportunity' and not l.stage_id:
                    stage_id = self.stage_find(cr, uid, l.section_id.id or False, [('sequence','>',0)])
                    if stage_id:
                        self.stage_set(cr, uid, [l.id], stage_id)
        res = super(crm_lead, self).case_open(cr, uid, ids, *args)
        return res

    def case_close(self, cr, uid, ids, *args):
        res = super(crm_lead, self).case_close(cr, uid, ids, *args)
        self.write(cr, uid, ids, {'date_closed': time.strftime('%Y-%m-%d %H:%M:%S')})
        for case in self.browse(cr, uid, ids):
            if case.type == 'lead':
                message = _("The lead '%s' has been closed.") % case.name
            else:
                message = _("The case '%s' has been closed.") % case.name
            self.log(cr, uid, case.id, message)
        return res

    def case_cancel(self, cr, uid, ids, *args):
        """Overrides cancel for crm_case for setting probability
        """
        res = super(crm_lead, self).case_cancel(cr, uid, ids, args)
        self.write(cr, uid, ids, {'probability' : 0.0})
        return res

    def case_reset(self, cr, uid, ids, *args):
        """Overrides reset as draft in order to set the stage field as empty
        """
        res = super(crm_lead, self).case_reset(cr, uid, ids, *args)
        self.write(cr, uid, ids, {'stage_id': False, 'probability': 0.0})
        return res

    def case_mark_lost(self, cr, uid, ids, *args):
        """Mark the case as lost: state = done and probability = 0%
        """
        res = super(crm_lead, self).case_close(cr, uid, ids, *args)
        self.write(cr, uid, ids, {'probability' : 0.0})
        for l in self.browse(cr, uid, ids):
            stage_id = self.stage_find_lost(cr, uid, l.section_id.id or False)
            if stage_id:
                self.stage_set(cr, uid, [l.id], stage_id)
            message = _("The opportunity '%s' has been marked as lost.") % l.name
            self.log(cr, uid, l.id, message)
        return res

    def case_mark_won(self, cr, uid, ids, *args):
        """Mark the case as lost: state = done and probability = 0%
        """
        res = super(crm_lead, self).case_close(cr, uid, ids, *args)
        self.write(cr, uid, ids, {'probability' : 100.0})
        for l in self.browse(cr, uid, ids):
            stage_id = self.stage_find_won(cr, uid, l.section_id.id or False)
            if stage_id:
                self.stage_set(cr, uid, [l.id], stage_id)
            message = _("The opportunity '%s' has been been won.") % l.name
            self.log(cr, uid, l.id, message)
        return res

    def convert_opportunity(self, cr, uid, ids, context=None):
        """ Precomputation for converting lead to opportunity
        """
        if context is None:
            context = {}
        context.update({'active_ids': ids})

        data_obj = self.pool.get('ir.model.data')
        value = {}


        for case in self.browse(cr, uid, ids, context=context):
            context.update({'active_id': case.id})
            data_id = data_obj._get_id(cr, uid, 'crm', 'view_crm_lead2opportunity_partner')
            view_id1 = False
            if data_id:
                view_id1 = data_obj.browse(cr, uid, data_id, context=context).res_id
            value = {
                    'name': _('Create Partner'),
                    'view_type': 'form',
                    'view_mode': 'form,tree',
                    'res_model': 'crm.lead2opportunity.partner',
                    'view_id': False,
                    'context': context,
                    'views': [(view_id1, 'form')],
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'nodestroy': True
            }
        return value

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
        res_id = self.write(cr, uid, [res_id], vals, context)
        return res_id

    def message_update(self, cr, uid, ids, msg, vals={}, default_act='pending', context=None):
        if isinstance(ids, (str, int, long)):
            ids = [ids]

        super(crm_lead, self).message_update(cr, uid, msg,
                                             custom_values=custom_values,
                                             context=context)

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
                values.update(state=crm.AVAILABLE_STATES[1][0]) #re-open
            res = self.write(cr, uid, [case.id], values, context=context)
        return res

    def msg_send(self, cr, uid, id, *args, **argv):
        """ Send The Message
        @param ids: List of email’s IDs
        """
        return True

    def action_makeMeeting(self, cr, uid, ids, context=None):
        """
        This opens Meeting's calendar view to schedule meeting on current Opportunity
        @return : Dictionary value for created Meeting view
        """
        value = {}
        for opp in self.browse(cr, uid, ids, context=context):
            data_obj = self.pool.get('ir.model.data')

            # Get meeting views
            result = data_obj._get_id(cr, uid, 'crm', 'view_crm_case_meetings_filter')
            res = data_obj.read(cr, uid, result, ['res_id'])
            id1 = data_obj._get_id(cr, uid, 'crm', 'crm_case_calendar_view_meet')
            id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_form_view_meet')
            id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_tree_view_meet')
            if id1:
                id1 = data_obj.browse(cr, uid, id1, context=context).res_id
            if id2:
                id2 = data_obj.browse(cr, uid, id2, context=context).res_id
            if id3:
                id3 = data_obj.browse(cr, uid, id3, context=context).res_id

            context = {
                'default_opportunity_id': opp.id,
                'default_partner_id': opp.partner_id and opp.partner_id.id or False,
                'default_user_id': uid, 
                'default_section_id': opp.section_id and opp.section_id.id or False,
                'default_email_from': opp.email_from,
                'default_state': 'open',  
                'default_name': opp.name
            }
            value = {
                'name': _('Meetings'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'calendar,form,tree',
                'res_model': 'crm.meeting',
                'view_id': False,
                'views': [(id1, 'calendar'), (id2, 'form'), (id3, 'tree')],
                'type': 'ir.actions.act_window',
                'search_view_id': res['res_id'],
                'nodestroy': True
            }
        return value


    def unlink(self, cr, uid, ids, context=None):
        for lead in self.browse(cr, uid, ids, context):
            if (not lead.section_id.allow_unlink) and (lead.state <> 'draft'):
                raise osv.except_osv(_('Warning !'),
                    _('You can not delete this lead. You should better cancel it.'))
        return super(crm_lead, self).unlink(cr, uid, ids, context)


    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}

        if 'date_closed' in vals:
            return super(crm_lead,self).write(cr, uid, ids, vals, context=context)

        if 'stage_id' in vals and vals['stage_id']:
            stage_obj = self.pool.get('crm.case.stage').browse(cr, uid, vals['stage_id'], context=context)
            text = _("Changed Stage to: %s") % stage_obj.name
            self.message_append(cr, uid, ids, text, body_text=text, context=context)
            message=''
            for case in self.browse(cr, uid, ids, context=context):
                if case.type == 'lead' or  context.get('stage_type',False)=='lead':
                    message = _("The stage of lead '%s' has been changed to '%s'.") % (case.name, stage_obj.name)
                elif case.type == 'opportunity':
                    message = _("The stage of opportunity '%s' has been changed to '%s'.") % (case.name, stage_obj.name)
                self.log(cr, uid, case.id, message)
        return super(crm_lead,self).write(cr, uid, ids, vals, context)

crm_lead()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
