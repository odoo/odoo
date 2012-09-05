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
        'partner_ids': fields.many2many('res.partner', 'crm_meeting_partner_rel', 'meeting_id','partner_id',
            string='Attendees', states={'done': [('readonly', True)]}),
        'state': fields.selection(
                    [('draft', 'Unconfirmed'), ('open', 'Confirmed'), ('cancel', 'Cancelled'), ('done', 'Done')],
                    string='Status', size=16, readonly=True),
        # Meeting fields
        'name': fields.char('Meeting Subject', size=128, required=True, states={'done': [('readonly', True)]}),
        'categ_ids': fields.many2many('crm.meeting.type', 'meeting_category_rel',
            'event_id', 'type_id', 'Tags'),
        'attendee_ids': fields.many2many('calendar.attendee', 'meeting_attendee_rel',\
                            'event_id', 'attendee_id', 'Attendees', states={'done': [('readonly', True)]}),
    }
    _defaults = {
        'state': 'open',
    }

    # ----------------------------------------
    # OpenChatter
    # ----------------------------------------

    def case_get_note_msg_prefix(self, cr, uid, id, context=None):
        return 'Meeting'

    def case_open_send_note(self, cr, uid, ids, context=None):
        return self.message_append_note(cr, uid, ids, body=_("Meeting has been <b>confirmed</b>."), context=context)

    def case_close_send_note(self, cr, uid, ids, context=None):
        return self.message_append_note(cr, uid, ids, body=_("Meeting has been <b>done</b>."), context=context)


