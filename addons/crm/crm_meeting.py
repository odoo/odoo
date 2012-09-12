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

from osv import fields, osv
import tools
from tools.translate import _
import logging
_logger = logging.getLogger(__name__)

#
# crm.meeting is defined in module base_calendar
#
class crm_meeting(osv.Model):
    """ Model for CRM meetings """
    _inherit = 'crm.meeting'
    _columns = {
        'phonecall_id': fields.many2one ('crm.phonecall', 'Phonecall'),
        'opportunity_id': fields.many2one ('crm.lead', 'Opportunity', domain="[('type', '=', 'opportunity')]"),
    }

    def create(self, cr, uid, vals, context=None):
        obj_id = super(crm_meeting, self).create(cr, uid, vals, context=context)
        self.create_send_note(cr, uid, [obj_id], context=context)
        return obj_id

    def create_send_note(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # update context: if come from phonecall, default state values can make the message_post crash
        context.pop('default_state', False)
        for meeting in self.browse(cr, uid, ids, context=context):
            # in the message, transpose meeting.date to the timezone of the current user
            meeting_date = fields.DT.datetime.strptime(meeting.date, tools.DEFAULT_SERVER_DATETIME_FORMAT)
            meeting_date_tz = fields.datetime.context_timestamp(cr, uid, meeting_date, context=context).strftime(tools.DATETIME_FORMATS_MAP['%+'] + " (%Z)")
            if meeting.opportunity_id: # meeting can be create from phonecalls or opportunities, therefore checking for the parent
                lead = meeting.opportunity_id
                message = _("Meeting linked to the opportunity <em>%s</em> has been <b>created</b> and <b>scheduled</b> on <em>%s</em>.") % (lead.name, meeting_date_tz)
                lead.message_post(body=message)
            elif meeting.phonecall_id:
                phonecall = meeting.phonecall_id
                message = _("Meeting linked to the phonecall <em>%s</em> has been <b>created</b> and <b>scheduled</b> on <em>%s</em>.") % (phonecall.name, meeting_date_tz)
                phonecall.message_post(body=message)
            else:
                message = _("A meeting has been <b>scheduled</b> on <em>%s</em>.") % (meeting_date_tz)
            meeting.message_post(body=message)
        return True

class calendar_attendee(osv.osv):
    """ Calendar Attendee """

    _inherit = 'calendar.attendee'
    _description = 'Calendar Attendee'

    def _compute_data(self, cr, uid, ids, name, arg, context=None):
       """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of compute data’s IDs
        @param context: A standard dictionary for contextual values
        """
       name = name[0]
       result = super(calendar_attendee, self)._compute_data(cr, uid, ids, name, arg, context=context)

       for attdata in self.browse(cr, uid, ids, context=context):
            id = attdata.id
            result[id] = {}
            if name == 'categ_id':
                if attdata.ref and 'categ_id' in attdata.ref._columns:
                    result[id][name] = (attdata.ref.categ_id.id, attdata.ref.categ_id.name,)
                else:
                    result[id][name] = False
       return result

    _columns = {
        'categ_id': fields.function(_compute_data, \
                        string='Event Type', type="many2one", \
                        relation="crm.case.categ", multi='categ_id'),
    }

class res_users(osv.osv):
    _name = 'res.users'
    _inherit = 'res.users'

    def create(self, cr, uid, data, context=None):
        user_id = super(res_users, self).create(cr, uid, data, context=context)

        # add shortcut unless 'noshortcut' is True in context
        if not(context and context.get('noshortcut', False)):
            data_obj = self.pool.get('ir.model.data')
            try:
                data_id = data_obj._get_id(cr, uid, 'crm', 'ir_ui_view_sc_calendar0')
                view_id  = data_obj.browse(cr, uid, data_id, context=context).res_id
                self.pool.get('ir.ui.view_sc').copy(cr, uid, view_id, default = {
                                            'user_id': user_id}, context=context)
            except:
                # Tolerate a missing shortcut. See product/product.py for similar code.
                _logger.debug('Skipped meetings shortcut for user "%s".', data.get('name','<new'))
        return user_id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
