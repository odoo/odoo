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
from tools.translate import _
import crm
import time

class crm_phonecall(osv.osv):
    """ Phonecall Cases """

    _name = "crm.phonecall"
    _description = "Phonecall Cases"
    _order = "id desc"
    _inherit = 'mailgate.thread'

    _columns = {
        # From crm.case
        'section_id': fields.many2one('crm.case.section', 'Sales Team', \
                        select=True, help='Sales team to which Case belongs to.\
                             Define Responsible user and Email account for mail gateway.'), 
        'user_id': fields.many2one('res.users', 'Responsible'), 
        'partner_id': fields.many2one('res.partner', 'Partner'), 
        
        # phonecall fields
        'duration': fields.float('Duration'),
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
                        domain="[('section_id','=',section_id),\
                        ('object_id.model', '=', 'crm.phonecall')]"),
        'partner_phone': fields.char('Phone', size=32),
        'partner_contact': fields.related('partner_address_id', 'name',\
                                 type="char", string="Contact", size=128),
        'partner_mobile': fields.char('Mobile', size=32),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'canal_id': fields.many2one('res.partner.canal', 'Channel',\
                        help="The channels represent the different communication\
                         modes available with the customer." \
                        " With each commercial opportunity, you can indicate\
                         the canall which is this opportunity source."),
        'date_closed': fields.datetime('Closed', readonly=True),
        'date': fields.datetime('Date'),
        'opportunity_id': fields.many2one ('crm.lead', 'Opportunity'),
    }

    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'priority': lambda *a: crm.AVAILABLE_PRIORITIES[2][0],
    }

    def action_make_meeting(self, cr, uid, ids, context=None):
        """
        This opens Meeting's calendar view to schedule meeting on current Phonecall
        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Phonecall to Meeting IDs
        @param context: A standard dictionary for contextual values

        @return : Dictionary value for created Meeting view
        """
        value = {}
        for phonecall in self.browse(cr, uid, ids):
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
                        'default_phonecall_id': phonecall.id,
                        'default_partner_id': phonecall.partner_id and phonecall.partner_id.id or False,
                        'default_email': phonecall.email_from ,
                        'default_name': phonecall.name
                    }

            value = {
                'name': _('Meetings'),
                'domain' : "[('user_id','=',%s)]" % (uid),
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

    def onchange_partner_address_id(self, cr, uid, ids, add, email=False):
        res = super(crm_phonecall, self).onchange_partner_address_id(cr, uid, ids, add, email)
        res.setdefault('value', {})
        if add:
            address = self.pool.get('res.partner.address').browse(cr, uid, add)
            res['value']['partner_phone'] = address.mobile
            res['value']['partner_mobile'] = address.phone
        return res
crm_phonecall()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
