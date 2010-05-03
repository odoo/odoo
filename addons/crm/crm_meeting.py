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
from datetime import datetime, timedelta
from osv import fields, osv
from tools.translate import _
import time


class crm_phonecall(osv.osv):
    """ CRM Phonecall """
    _name = 'crm.phonecall'
crm_phonecall()


class crm_meeting(osv.osv):
    """ CRM Meeting Cases """

    _name = 'crm.meeting'
    _description = "Meeting Cases"
    _order = "id desc"
    _inherit = ["mailgate.thread", "calendar.event"]

    _columns = {
        # From crm.case
        'name': fields.char('Summary', size=124, required=True), 
        'partner_id': fields.many2one('res.partner', 'Partner'), 
        'partner_address_id': fields.many2one('res.partner.address', 'Partner Contact', \
                                 domain="[('partner_id','=',partner_id)]"), 
        'section_id': fields.many2one('crm.case.section', 'Sales Team', \
                        select=True, help='Sales team to which Case belongs to.\
                             Define Responsible user and Email account for mail gateway.'), 
        'email_from': fields.char('Email', size=128, help="These people will receive email."),
        
        # Meeting fields
        'categ_id': fields.many2one('crm.case.categ', 'Meeting Type', \
                        domain="[('object_id.model', '=', 'crm.meeting')]", \
            ),
        'phonecall_id': fields.many2one ('crm.phonecall', 'Phonecall'),
        'opportunity_id': fields.many2one ('crm.lead', 'Opportunity', domain="[('type', '=', 'opportunity')]"),
        'attendee_ids': fields.many2many('calendar.attendee', 'meeting_attendee_rel',\
                                 'event_id', 'attendee_id', 'Attendees'),
        'date_closed': fields.datetime('Closed', readonly=True),
        'date_deadline': fields.datetime('Deadline'),
        'state': fields.selection([('open', 'Confirmed'),
                                    ('draft', 'Unconfirmed'),
                                    ('cancel', 'Cancelled'),
                                    ('done', 'Done')], 'State', \
                                    size=16, readonly=True)
    }

    _defaults = {
        'state': lambda *a: 'draft',
    }

    def open_meeting(self, cr, uid, ids, context=None):
        """
        Open Crm Meeting Form for Crm Meeting.
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of crm meeting’s IDs
        @param context: A standard dictionary for contextual values
        @return: Dictionary value which open Crm Meeting form.
        """

        if not context:
            context = {}

        data_obj = self.pool.get('ir.model.data')

        value = {}

        id2 = data_obj._get_id(cr, uid, 'crm', 'crm_case_form_view_meet')
        id3 = data_obj._get_id(cr, uid, 'crm', 'crm_case_tree_view_meet')
        id4 = data_obj._get_id(cr, uid, 'crm', 'crm_case_calendar_view_meet')
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id
        if id4:
            id4 = data_obj.browse(cr, uid, id4, context=context).res_id
        for id in ids:
            value = {
                    'name': _('Meeting'),
                    'view_type': 'form',
                    'view_mode': 'form,tree',
                    'res_model': 'crm.meeting',
                    'view_id': False,
                    'views': [(id2, 'form'), (id3, 'tree'), (id4, 'calendar')],
                    'type': 'ir.actions.act_window',
                    'res_id': base_calendar.base_calendar_id2real_id(id),
                    'nodestroy': True
                    }

        return value
    
    # From crm.case
    
    def case_close(self, cr, uid, ids, *args):
        """Closes Case
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self._history(cr, uid, cases, _('Close'))
        self.write(cr, uid, ids, {'state': 'done',
                                  'date_closed': time.strftime('%Y-%m-%d %H:%M:%S'),
                                  })
        #
        # We use the cache of cases to keep the old case state
        #
        self._action(cr, uid, cases, 'done')
        return True

    def case_open(self, cr, uid, ids, *args):
        """Opens Case
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        cases = self.browse(cr, uid, ids)
        self._history(cr, uid, cases, _('Open'))

        for case in cases:
            data = {'state': 'open', 'active': True}
            if not case.user_id:
                data['user_id'] = uid
            self.write(cr, uid, case.id, data)
        self._action(cr, uid, cases, 'open')
        return True

    def case_cancel(self, cr, uid, ids, *args):
        """Cancels Case
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self._history(cr, uid, cases, _('Cancel'))
        self.write(cr, uid, ids, {'state': 'cancel',
                                  'active': True})
        self._action(cr, uid, cases, 'cancel')
        return True

    def case_reset(self, cr, uid, ids, *args):
        """Resets case as draft
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of case Ids
        @param *args: Tuple Value for additional Params
        """
        cases = self.browse(cr, uid, ids)
        cases[0].state # to fill the browse record cache
        self._history(cr, uid, cases, _('Draft'))
        self.write(cr, uid, ids, {'state': 'draft', 'active': True})
        self._action(cr, uid, cases, 'draft')
        return True
    
crm_meeting()

class calendar_attendee(osv.osv):
    """ Calendar Attendee """

    _inherit = 'calendar.attendee'
    _description = 'Calendar Attendee'

    def _compute_data(self, cr, uid, ids, name, arg, context):
       """
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of compute data’s IDs
        @param context: A standard dictionary for contextual values
        """
       name = name[0]
       result = super(calendar_attendee, self)._compute_data(cr, uid, ids, name, arg, context)

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
        'categ_id': fields.function(_compute_data, method=True, \
                        string='Event Type', type="many2one", \
                        relation="crm.case.categ", multi='categ_id'),
    }

calendar_attendee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
