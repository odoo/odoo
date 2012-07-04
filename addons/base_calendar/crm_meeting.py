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

from osv import osv, fields
import tools
from tools.translate import _

import base_calendar
from base_status.base_state import base_state

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

class crm_meeting(base_state, osv.Model):
    """ Model for CRM meetings """
    _name = 'crm.meeting'
    _description = "Meeting"
    _order = "id desc"
    _inherit = ["calendar.event", 'ir.needaction_mixin', "mail.thread"]
    _columns = {
        # base_state required fields
        'create_date': fields.datetime('Creation Date', readonly=True),
        'write_date': fields.datetime('Write Date', readonly=True),
        'date_open': fields.datetime('Confirmed', readonly=True),
        'date_closed': fields.datetime('Closed', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', states={'done': [('readonly', True)]}),
        'email_from': fields.char('Email', size=128, states={'done': [('readonly', True)]},
                        help="These people will receive email."),
        'state': fields.selection(
                    [('draft', 'Unconfirmed'), ('open', 'Confirmed'), ('cancel', 'Cancelled'), ('done', 'Done')],
                    string='Status', size=16, readonly=True),
        # Meeting fields
        'name': fields.char('Summary', size=128, required=True, states={'done': [('readonly', True)]}),
        'categ_id': fields.many2one('crm.meeting.type', 'Meeting Type'),
        'attendee_ids': fields.many2many('calendar.attendee', 'meeting_attendee_rel',\
                            'event_id', 'attendee_id', 'Attendees', states={'done': [('readonly', True)]}),
    }
    _defaults = {
        'state': 'draft',
    }

    def create(self, cr, uid, vals, context=None):
        obj_id = super(crm_meeting, self).create(cr, uid, vals, context=context)
        self.create_send_note(cr, uid, [obj_id], context=context)
        return obj_id

    # ----------------------------------------
    # OpenChatter
    # ----------------------------------------

    def case_get_note_msg_prefix(self, cr, uid, id, context=None):
        return 'Meeting'

    def create_send_note(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # update context: if come from phonecall, default state values can make the message_append_note crash
        context.pop('default_state', False)
        for meeting in self.browse(cr, uid, ids, context=context):
            # convert datetime field to a datetime, using server format, then
            # convert it to the user TZ and re-render it with %Z to add the timezone
            meeting_datetime = fields.DT.datetime.strptime(meeting.date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            meeting_date_str = fields.datetime.context_timestamp(cr, uid, meeting_datetime, context=context).strftime(tools.DATETIME_FORMATS_MAP['%+'] + " (%Z)")
            message = _("A meeting has been <b>scheduled</b> on <em>%s</em>.") % (meeting_date_str)
            if meeting.opportunity_id: # meeting can be create from phonecalls or opportunities, therefore checking for the parent
                lead = meeting.opportunity_id
                parent_message = _("Meeting linked to the opportunity <em>%s</em> has been <b>created</b> and <b>cscheduled</b> on <em>%s</em>.") % (lead.name, meeting.date)
                lead.message_append_note(_('System Notification'), message)
            elif meeting.phonecall_id:
                phonecall = meeting.phonecall_id
                parent_message = _("Meeting linked to the phonecall <em>%s</em> has been <b>created</b> and <b>cscheduled</b> on <em>%s</em>.") % (phonecall.name, meeting.date)
                phonecall.message_append_note(body=message)
            else:
                parent_message = message
            if parent_message:
                meeting.message_append_note(body=parent_message)
        return True

    def case_open_send_note(self, cr, uid, ids, context=None):
        return self.message_append_note(cr, uid, ids, body=_("Meeting has been <b>confirmed</b>."), context=context)

    def case_close_send_note(self, cr, uid, ids, context=None):
        return self.message_append_note(cr, uid, ids, body=_("Meeting has been <b>done</b>."), context=context)


