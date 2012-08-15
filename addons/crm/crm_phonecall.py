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

from base_status.base_state import base_state
import crm
from datetime import datetime
from osv import fields, osv
import time
from tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, DATETIME_FORMATS_MAP
from tools.translate import _

class crm_phonecall(base_state, osv.osv):
    """ Model for CRM phonecalls """
    _name = "crm.phonecall"
    _description = "Phonecall"
    _order = "id desc"
    _inherit = ['mail.thread']
    _columns = {
        # base_state required fields
        'date_action_last': fields.datetime('Last Action', readonly=1),
        'date_action_next': fields.datetime('Next Action', readonly=1),
        'create_date': fields.datetime('Creation Date' , readonly=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team', \
                        select=True, help='Sales team to which Case belongs to.'),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'partner_id': fields.many2one('res.partner', 'Contact'),
        'company_id': fields.many2one('res.company', 'Company'),
        'description': fields.text('Description'),
        'state': fields.selection([ ('draft', 'Draft'),
                                    ('open', 'Confirmed'),
                                    ('pending', 'Not Held'),
                                    ('cancel', 'Cancelled'),
                                    ('done', 'Held'),],
                        string='Status', size=16, readonly=True,
                        help='The state is set to \'Todo\', when a case is created.\
                                If the case is in progress the state is set to \'Open\'.\
                                When the call is over, the state is set to \'Held\'.\
                                If the call needs to be done then the state is set to \'Not Held\'.'),
        'email_from': fields.char('Email', size=128, help="These people will receive email."),
        'date_open': fields.datetime('Opened', readonly=True),
        # phonecall fields
        'name': fields.char('Call Summary', size=64, required=True),
        'active': fields.boolean('Active', required=False),
        'duration': fields.float('Duration', help="Duration in Minutes"),
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
                        domain="['|',('section_id','=',section_id),('section_id','=',False),\
                        ('object_id.model', '=', 'crm.phonecall')]"),
        'partner_phone': fields.char('Phone', size=32),
        'partner_mobile': fields.char('Mobile', size=32),
        'priority': fields.selection(crm.AVAILABLE_PRIORITIES, 'Priority'),
        'date_closed': fields.datetime('Closed', readonly=True),
        'date': fields.datetime('Date'),
        'opportunity_id': fields.many2one ('crm.lead', 'Lead/Opportunity'),
    }

    def _get_default_state(self, cr, uid, context=None):
        if context and context.get('default_state', False):
            return context.get('default_state')
        return 'open'

    _defaults = {
        'date': fields.datetime.now,
        'priority': crm.AVAILABLE_PRIORITIES[2][0],
        'state':  _get_default_state,
        'user_id': lambda self,cr,uid,ctx: uid,
        'active': 1
    }

    def create(self, cr, uid, vals, context=None):
        obj_id = super(crm_phonecall, self).create(cr, uid, vals, context)
        for phonecall in self.browse(cr, uid, [obj_id], context=context):
            if not phonecall.opportunity_id:
                self.case_open_send_note(cr, uid, [obj_id], context=context)
        return obj_id

    def case_close(self, cr, uid, ids, context=None):
        """ Overrides close for crm_case for setting duration """
        res = True
        for phone in self.browse(cr, uid, ids, context=context):
            phone_id = phone.id
            data = {}
            if phone.duration <=0:
                duration = datetime.now() - datetime.strptime(phone.date, DEFAULT_SERVER_DATETIME_FORMAT)
                data['duration'] = duration.seconds/float(60)
            res = super(crm_phonecall, self).case_close(cr, uid, [phone_id], context=context)
            self.write(cr, uid, [phone_id], data, context=context)
        return res

    def case_reset(self, cr, uid, ids, context=None):
        """Resets case as Todo
        """
        res = super(crm_phonecall, self).case_reset(cr, uid, ids, context)
        self.write(cr, uid, ids, {'duration': 0.0, 'state':'open'}, context=context)
        return res

    def schedule_another_phonecall(self, cr, uid, ids, schedule_time, call_summary, \
                    user_id=False, section_id=False, categ_id=False, action='schedule', context=None):
        """
        action :('schedule','Schedule a call'), ('log','Log a call')
        """
        model_data = self.pool.get('ir.model.data')
        phonecall_dict = {}
        if not categ_id:
            res_id = model_data._get_id(cr, uid, 'crm', 'categ_phone2')
            if res_id:
                categ_id = model_data.browse(cr, uid, res_id, context=context).res_id
        for call in self.browse(cr, uid, ids, context=context):
            if not section_id:
                section_id = call.section_id and call.section_id.id or False
            if not user_id:
                user_id = call.user_id and call.user_id.id or False
            vals = {
                    'name' : call_summary,
                    'user_id' : user_id or False,
                    'categ_id' : categ_id or False,
                    'description' : call.description or False,
                    'date' : schedule_time,
                    'section_id' : section_id or False,
                    'partner_id': call.partner_id and call.partner_id.id or False,
                    'partner_phone' : call.partner_phone,
                    'partner_mobile' : call.partner_mobile,
                    'priority': call.priority,
            }
            new_id = self.create(cr, uid, vals, context=context)
            if action == 'log':
                self.case_close(cr, uid, [new_id])
            phonecall_dict[call.id] = new_id
        return phonecall_dict

    def _call_create_partner(self, cr, uid, phonecall, context=None):
        partner = self.pool.get('res.partner')
        partner_id = partner.create(cr, uid, {
                    'name': phonecall.name,
                    'user_id': phonecall.user_id.id,
                    'comment': phonecall.description,
                    'address': []
        })
        return partner_id

    def _call_set_partner(self, cr, uid, ids, partner_id, context=None):
        write_res = self.write(cr, uid, ids, {'partner_id' : partner_id}, context=context)
        self._call_set_partner_send_note(cr, uid, ids, context)
        return write_res

    def _call_create_partner_address(self, cr, uid, phonecall, partner_id, context=None):
        address = self.pool.get('res.partner')
        return address.create(cr, uid, {
                    'parent_id': partner_id,
                    'name': phonecall.name,
                    'phone': phonecall.partner_phone,
        })

    def convert_partner(self, cr, uid, ids, action='create', partner_id=False, context=None):
        """
        This function convert partner based on action.
        if action is 'create', create new partner with contact and assign lead to new partner_id.
        otherwise assign lead to specified partner_id
        """
        if context is None:
            context = {}
        partner_ids = {}
        for call in self.browse(cr, uid, ids, context=context):
            if action == 'create':
               if not partner_id:
                   partner_id = self._call_create_partner(cr, uid, call, context=context)
               self._call_create_partner_address(cr, uid, call, partner_id, context=context)
            self._call_set_partner(cr, uid, [call.id], partner_id, context=context)
            partner_ids[call.id] = partner_id
        return partner_ids


    def redirect_phonecall_view(self, cr, uid, phonecall_id, context=None):
        model_data = self.pool.get('ir.model.data')
        # Select the view
        tree_view = model_data.get_object_reference(cr, uid, 'crm', 'crm_case_phone_tree_view')
        form_view = model_data.get_object_reference(cr, uid, 'crm', 'crm_case_phone_form_view')
        search_view = model_data.get_object_reference(cr, uid, 'crm', 'view_crm_case_phonecalls_filter')
        value = {
                'name': _('Phone Call'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'crm.phonecall',
                'res_id' : int(phonecall_id),
                'views': [(form_view and form_view[1] or False, 'form'), (tree_view and tree_view[1] or False, 'tree'), (False, 'calendar')],
                'type': 'ir.actions.act_window',
                'search_view_id': search_view and search_view[1] or False,
        }
        return value


    def convert_opportunity(self, cr, uid, ids, opportunity_summary=False, partner_id=False, planned_revenue=0.0, probability=0.0, context=None):
        partner = self.pool.get('res.partner')
        opportunity = self.pool.get('crm.lead')
        opportunity_dict = {}
        default_contact = False
        for call in self.browse(cr, uid, ids, context=context):
            if not partner_id:
                partner_id = call.partner_id and call.partner_id.id or False
            if partner_id:
                address_id = partner.address_get(cr, uid, [partner_id])['default']
                if address_id:
                    default_contact = partner.browse(cr, uid, address_id, context=context)
            opportunity_id = opportunity.create(cr, uid, {
                            'name': opportunity_summary or call.name,
                            'planned_revenue': planned_revenue,
                            'probability': probability,
                            'partner_id': partner_id or False,
                            'mobile': default_contact and default_contact.mobile,
                            'section_id': call.section_id and call.section_id.id or False,
                            'description': call.description or False,
                            'priority': call.priority,
                            'type': 'opportunity',
                            'phone': call.partner_phone or False,
                            'email_from': default_contact and default_contact.email,
                        })
            vals = {
                    'partner_id': partner_id,
                    'opportunity_id' : opportunity_id,
            }
            self.write(cr, uid, [call.id], vals)
            self.case_close(cr, uid, [call.id])
            opportunity.case_open(cr, uid, [opportunity_id])
            opportunity_dict[call.id] = opportunity_id
        return opportunity_dict

    def action_make_meeting(self, cr, uid, ids, context=None):
        """ This opens Meeting's calendar view to schedule meeting on current Phonecall
            @return : Dictionary value for created Meeting view
        """
        phonecall = self.browse(cr, uid, ids[0], context)
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'base_calendar', 'action_crm_meeting', context)
        res['context'] = {
            'default_phonecall_id': phonecall.id,
            'default_partner_id': phonecall.partner_id and phonecall.partner_id.id or False,
            'default_user_id': uid,
            'default_email_from': phonecall.email_from,
            'default_state': 'open',
            'default_name': phonecall.name,
        }
        return res
    
    # ----------------------------------------
    # OpenChatter
    # ----------------------------------------

    def case_get_note_msg_prefix(self, cr, uid, id, context=None):
        return 'Phonecall'
    
    def case_reset_send_note(self, cr, uid, ids, context=None):
        message = _('Phonecall has been <b>reset and set as open</b>.')
        return self.message_append_note(cr, uid, ids, body=message, context=context)

    def case_open_send_note(self, cr, uid, ids, context=None):
        lead_obj = self.pool.get('crm.lead')
        for phonecall in self.browse(cr, uid, ids, context=context):
            phonecall.message_subscribe([phonecall.user_id.id], context=context)
            if phonecall.opportunity_id:
                lead = phonecall.opportunity_id
                # convert datetime field to a datetime, using server format, then
                # convert it to the user TZ and re-render it with %Z to add the timezone
                phonecall_datetime = fields.DT.datetime.strptime(phonecall.date, DEFAULT_SERVER_DATETIME_FORMAT)
                phonecall_date_str = fields.datetime.context_timestamp(cr, uid, phonecall_datetime, context=context).strftime(DATETIME_FORMATS_MAP['%+'] + " (%Z)")
                message = _("Phonecall linked to the opportunity <em>%s</em> has been <b>created</b> and <b>scheduled</b> on <em>%s</em>.") % (lead.name, phonecall_date_str)
            else:
                message = _("Phonecall has been <b>created and opened</b>.")
            phonecall.message_append_note(body=message)
        return True

    def _call_set_partner_send_note(self, cr, uid, ids, context=None):
        return self.message_append_note(cr, uid, ids, body=_("Partner has been <b>created</b>."), context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
