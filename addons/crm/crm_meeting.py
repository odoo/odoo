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

from base_calendar import base_calendar
from crm import crm_base, crm_case
from osv import fields, osv
from tools.translate import _
import logging

class crm_lead(crm_case, osv.osv):
    """ CRM Leads """
    _name = 'crm.lead'
crm_lead()

class crm_phonecall(crm_case, osv.osv):
    """ CRM Phonecall """
    _name = 'crm.phonecall'
crm_phonecall()


class crm_meeting(crm_base, osv.osv):
    """ CRM Meeting Cases """

    _name = 'crm.meeting'
    _description = "Meeting"
    _order = "id desc"
    _inherit = "calendar.event"
    _columns = {
        # From crm.case
        'name': fields.char('Summary', size=124, required=True, states={'done': [('readonly', True)]}),
        'partner_id': fields.many2one('res.partner', 'Partner', states={'done': [('readonly', True)]}),
        'section_id': fields.many2one('crm.case.section', 'Sales Team', states={'done': [('readonly', True)]}, \
                        select=True, help='Sales team to which Case belongs to.'),
        'email_from': fields.char('Email', size=128, states={'done': [('readonly', True)]}, help="These people will receive email."),
        'id': fields.integer('ID', readonly=True),
        'create_date': fields.datetime('Creation Date' , readonly=True),
        'write_date': fields.datetime('Write Date' , readonly=True),
        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),
        # Meeting fields
        'categ_id': fields.many2one('crm.case.categ', 'Meeting Type', \
                        domain="[('object_id.model', '=', 'crm.meeting')]", \
            ),
        'phonecall_id': fields.many2one ('crm.phonecall', 'Phonecall'),
        'opportunity_id': fields.many2one ('crm.lead', 'Opportunity', domain="[('type', '=', 'opportunity')]"),
        'attendee_ids': fields.many2many('calendar.attendee', 'meeting_attendee_rel',\
                                 'event_id', 'attendee_id', 'Attendees', states={'done': [('readonly', True)]}),
        'date_closed': fields.datetime('Closed', readonly=True),
        'date_deadline': fields.datetime('Deadline', states={'done': [('readonly', True)]}),
        'message_ids': fields.one2many('mail.message', 'res_id', 'Messages', domain=[('model','=',_name)]),
        'state': fields.selection([('open', 'Confirmed'),
                                    ('draft', 'Unconfirmed'),
                                    ('cancel', 'Cancelled'),
                                    ('done', 'Done')], 'State', \
                                    size=16, readonly=True),
    }
    _defaults = {
        'state': 'draft',
        'active': 1,
        'user_id': lambda self, cr, uid, ctx: uid,
    }

    def case_open(self, cr, uid, ids, *args):
        """Confirms meeting
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Meeting Ids
        @param *args: Tuple Value for additional Params
        """
        res = super(crm_meeting, self).case_open(cr, uid, ids, args)
        for (id, name) in self.name_get(cr, uid, ids):
            message = _("The meeting '%s' has been confirmed.") % name
            id=base_calendar.base_calendar_id2real_id(id)
            self.log(cr, uid, id, message)
        return res

crm_meeting()

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

calendar_attendee()

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
                logging.getLogger('orm').debug('Skipped meetings shortcut for user "%s"', data.get('name','<new'))
        return user_id

res_users()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
