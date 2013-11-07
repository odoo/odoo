#  -*- coding: utf-8 -*-
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

import time

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from base_calendar import get_real_ids, base_calendar_id2real_id
from datetime import datetime, timedelta, date
import pytz
from openerp import tools
import openerp

#
# crm.meeting is defined here so that it may be used by modules other than crm,
# without forcing the installation of crm.
#

class crm_meeting_type(osv.Model):
    _name = 'crm.meeting.type'
    _description = 'Meeting Type'
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
    }

class crm_meeting(osv.Model):
    """ Model for CRM meetings """
    _name = 'crm.meeting'
    _description = "Meeting"
    _order = "id desc"
    _inherit = ["calendar.event", "mail.thread", "ir.needaction_mixin"]
    
    def _find_user_attendee(self, cr, uid, meeting_ids, context=None):
        attendee_pool = self.pool.get('calendar.attendee')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        for meeting_id in meeting_ids:
            for attendee in self.browse(cr,uid,meeting_id,context).attendee_ids:
                if user.partner_id.id == attendee.partner_id.id:
                    return attendee
        return False

    def _compute(self, cr, uid, ids, fields, arg, context=None):
        res = {}
        for meeting_id in ids:
            res[meeting_id] = {}
            attendee = self._find_user_attendee(cr, uid, [meeting_id], context)
            for field in fields:
                if field == 'is_attendee':
                    res[meeting_id][field] = True if attendee else False
                elif field == 'attendee_status':
                    res[meeting_id][field] = attendee.state if attendee else 'needs-action'
                elif field == 'event_time':
                    res[meeting_id][field] = self._compute_time(cr, uid, meeting_id, context=context)
        return res
            

    def _compute_time(self, cr, uid, meeting_id, context=None):
        """
            Return date and time (from to from) based on duration with timezone in string :
            eg.
            1) if user add duration for 2 hours, return : August-23-2013 at ( 04-30 To 06-30) (Europe/Brussels)
            2) if event all day ,return : AllDay, July-31-2013
        """
        if context is None:
            context = {}
        tz = context.get('tz', pytz.timezone('UTC'))
        meeting = self.browse(cr, uid, meeting_id, context=context)
        date = fields.datetime.context_timestamp(cr, uid, datetime.strptime(meeting.date, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context)
        date_deadline = fields.datetime.context_timestamp(cr, uid, datetime.strptime(meeting.date_deadline, tools.DEFAULT_SERVER_DATETIME_FORMAT), context=context)
        event_date = date.strftime('%B-%d-%Y')
        event_time = date.strftime('%H-%M')
        if meeting.allday:
            time =  _("AllDay , %s") % (event_date)
        elif meeting.duration < 24:
            duration =  date + timedelta(hours= meeting.duration)
            time = ("%s at ( %s To %s) (%s)") % (event_date, event_time, duration.strftime('%H-%M'), tz)
        else :
            time = ("%s at %s To\n %s at %s (%s)") % (event_date, event_time, date_deadline.strftime('%B-%d-%Y'), date_deadline.strftime('%H-%M'), tz)
        return time

    _columns = {
        'create_date': fields.datetime('Creation Date', readonly=True),
        'write_date': fields.datetime('Write Date', readonly=True),
        'date_open': fields.datetime('Confirmed', readonly=True),
        'date_closed': fields.datetime('Closed', readonly=True),
        'partner_ids': fields.many2many('res.partner', 'crm_meeting_partner_rel', 'meeting_id', 'partner_id',
            string='Attendees', states={'done': [('readonly', True)]}),
        'state': fields.selection(
                    [('draft', 'Unconfirmed'), ('open', 'Confirmed')],
                    string='Status', size=16, readonly=True, track_visibility='onchange'),
        # Meeting fields
        'name': fields.char('Meeting Subject', size=128, required=True, states={'done': [('readonly', True)]}),
        'categ_ids': fields.many2many('crm.meeting.type', 'meeting_category_rel',
            'event_id', 'type_id', 'Tags'),
        'attendee_ids': fields.many2many('calendar.attendee', 'meeting_attendee_rel',\
                            'event_id', 'attendee_id', 'Invited People', states={'done': [('readonly', True)]}),
        'is_attendee': fields.function(_compute, string='Attendee', \
                            type="boolean", multi='attendee'),
        'attendee_status': fields.function(_compute, string='Attendee Status', \
                            type="selection", multi='attendee'),
        'event_time': fields.function(_compute, string='Event Time', type="char", multi='attendee'),
    }
    _defaults = {
        'state': 'open',
    }
    
    def search(self, cr, uid, args, offset=0, limit=0, order=None, context=None, count=False):
        if context is None:
            context={}
        if context.get('mymeetings',False):
            partner_id = self.pool.get('res.users').browse(cr, uid, uid, context).partner_id.id
            args += ['|', ('partner_ids', 'in', [partner_id]), ('user_id', '=', uid)]
        return super(crm_meeting, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)

    def message_get_subscription_data(self, cr, uid, ids, user_pid=None, context=None):
        res = {}
        for virtual_id in ids:
            real_id = base_calendar_id2real_id(virtual_id)
            result = super(crm_meeting, self).message_get_subscription_data(cr, uid, [real_id], user_pid=None, context=context)
            res[virtual_id] = result[real_id]
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        default = default or {}
        default['attendee_ids'] = False
        return super(crm_meeting, self).copy(cr, uid, id, default, context)

    def write(self, cr, uid, ids, values, context=None):
        """ Override to add case management: open/close dates """
        if values.get('state')and values.get('state') == 'open':
            values['date_open'] = fields.datetime.now()
        return super(crm_meeting, self).write(cr, uid, ids, values, context=context)

    def onchange_partner_ids(self, cr, uid, ids, value, context=None):
        """ The basic purpose of this method is to check that destination partners
            effectively have email addresses. Otherwise a warning is thrown.
            :param value: value format: [[6, 0, [3, 4]]]
        """
        res = {'value': {}}
        if not value or not value[0] or not value[0][0] == 6:
            return
        res.update(self.check_partners_email(cr, uid, value[0][2], context=context))
        return res

    def check_partners_email(self, cr, uid, partner_ids, context=None):
        """ Verify that selected partner_ids have an email_address defined.
            Otherwise throw a warning. """
        partner_wo_email_lst = []
        for partner in self.pool.get('res.partner').browse(cr, uid, partner_ids, context=context):
            if not partner.email:
                partner_wo_email_lst.append(partner)
        if not partner_wo_email_lst:
            return {}
        warning_msg = _('The following contacts have no email address :')
        for partner in partner_wo_email_lst:
            warning_msg += '\n- %s' % (partner.name)
        return {'warning': {
                    'title': _('Email addresses not found'),
                    'message': warning_msg,
                    }
                }
    # ----------------------------------------
    # OpenChatter
    # ----------------------------------------

    # shows events of the day for this user
    def _needaction_domain_get(self, cr, uid, context=None):
        return [('date', '<=', time.strftime(DEFAULT_SERVER_DATE_FORMAT + ' 23:59:59')), ('date_deadline', '>=', time.strftime(DEFAULT_SERVER_DATE_FORMAT + ' 23:59:59')), ('user_id', '=', uid)]

    def message_post(self, cr, uid, thread_id, body='', subject=None, type='notification',
                        subtype=None, parent_id=False, attachments=None, context=None, **kwargs):
        if isinstance(thread_id, str):
            thread_id = get_real_ids(thread_id)
        if context.get('default_date'):
            del context['default_date']
        return super(crm_meeting, self).message_post(cr, uid, thread_id, body=body, subject=subject, type=type, subtype=subtype, parent_id=parent_id, attachments=attachments, context=context, **kwargs)

    def do_decline(self, cr, uid, ids, context=None):
         attendee_pool = self.pool.get('calendar.attendee')
         attendee = self._find_user_attendee(cr, uid, ids, context)
         return attendee_pool.do_decline(cr, uid, [attendee.id], context=context)

    def do_accept(self, cr, uid, ids, context=None):
        attendee_pool = self.pool.get('calendar.attendee')
        attendee = self._find_user_attendee(cr, uid, ids, context)
        return attendee_pool.do_accept(cr, uid, [attendee.id], context=context)

    def get_attendee(self, cr, uid, meeting_id, context=None):
        invitation = {'meeting':{}, 'attendee': [], 'logo': ''}
        attendee_pool = self.pool.get('calendar.attendee')
        company_logo = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.logo
        meeting = self.browse(cr, uid, int(meeting_id), context)
        invitation['meeting'] = {
                'event':meeting.name,
                'organizer': meeting.organizer,
                'where': meeting.location,
                'when':meeting.event_time
        }
        invitation['logo'] = company_logo.replace('\n','\\n') if company_logo else ''
        for attendee in meeting.attendee_ids:
            invitation['attendee'].append({'name':attendee.cn,'status': attendee.state})
        return invitation

    def get_interval(self, cr, uid, ids, date, interval, context=None):
        date = datetime.strptime(date, DEFAULT_SERVER_DATETIME_FORMAT)
        if interval == 'day':
            res = str(date.day)
        elif interval == 'month':
            res = date.strftime('%B') + " " + str(date.year)
        elif interval == 'dayname':
            res = date.strftime('%A')
        elif interval == 'time':
            res = date.strftime('%I:%M %p')
        return res

class mail_message(osv.osv):
    _inherit = "mail.message"

    def search(self, cr, uid, args, offset=0, limit=0, order=None, context=None, count=False):
        '''
        convert the search on real ids in the case it was asked on virtual ids, then call super()
        '''
        for index in range(len(args)):
            if args[index][0] == "res_id" and isinstance(args[index][2], str):
                args[index][2] = get_real_ids(args[index][2])
        return super(mail_message, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)

    def _find_allowed_model_wise(self, cr, uid, doc_model, doc_dict, context=None):
        if doc_model == 'crm.meeting':
            for virtual_id in self.pool[doc_model].get_recurrent_ids(cr, uid, doc_dict.keys(), [], context=context):
                doc_dict.setdefault(virtual_id, doc_dict[get_real_ids(virtual_id)])
        return super(mail_message, self)._find_allowed_model_wise(cr, uid, doc_model, doc_dict, context=context)

class ir_attachment(osv.osv):
    _inherit = "ir.attachment"

    def search(self, cr, uid, args, offset=0, limit=0, order=None, context=None, count=False):
        '''
        convert the search on real ids in the case it was asked on virtual ids, then call super()
        '''
        for index in range(len(args)):
            if args[index][0] == "res_id" and isinstance(args[index][2], str):
                args[index][2] = get_real_ids(args[index][2])
        return super(ir_attachment, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)

    def write(self, cr, uid, ids, vals, context=None):
        '''
        when posting an attachment (new or not), convert the virtual ids in real ids.
        '''
        if isinstance(vals.get('res_id'), str):
            vals['res_id'] = get_real_ids(vals.get('res_id'))
        return super(ir_attachment, self).write(cr, uid, ids, vals, context=context)

class invite_wizard(osv.osv_memory):
    _inherit = 'mail.wizard.invite'

    def default_get(self, cr, uid, fields, context=None):
        '''
        in case someone clicked on 'invite others' wizard in the followers widget, transform virtual ids in real ids
        '''
        result = super(invite_wizard, self).default_get(cr, uid, fields, context=context)
        if 'res_id' in result:
            result['res_id'] = get_real_ids(result['res_id'])
        return result
