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

import crm
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from openerp.exceptions import UserError

class crm_phonecall(osv.osv):
    """ Model for CRM phonecalls """
    _name = "crm.phonecall"
    _description = "Phonecall"
    _order = "id desc"
    _inherit = ['mail.thread']
    
    _columns = {
        'create_date': fields.datetime('Creation Date' , readonly=True),
        'team_id': fields.many2one('crm.team', 'Sales Team', oldname='section_id',\
                        select=True, help='Sales team to which Case belongs to.'),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'partner_id': fields.many2one('res.partner', 'Contact',ondelete='cascade', track_visibility='onchange'),
        'company_id': fields.many2one('res.company', 'Company'),
        'description': fields.text('Description'),
        'state': fields.selection(
            [('no_answer', 'Not Held'),
             ('cancel', 'Cancelled'),
             ('to_do', 'To Do'),
             ('done', 'Held')
             ], string='Status', readonly=True, track_visibility='onchange',
            help='The status is set to To Do, when a case is created.\n'
                 'When the call is over, the status is set to Held.\n'
                 'If the call is not applicable anymore, the status can be set to Cancelled.'),
        'email_from': fields.char('Email', size=128, help="These people will receive email."),
        'name': fields.char('Call Summary', required=True),
        'duration': fields.float('Duration', help='Duration in minutes and seconds.'),
        'categ_id': fields.many2one('crm.phonecall.category', 'Category'),
        'partner_phone': fields.char('Phone'),
        'partner_mobile': fields.char('Mobile'),
        'priority': fields.selection([('0','Low'), ('1','Normal'), ('2','High')], 'Priority'),
        'date': fields.datetime('Date'),
        'opportunity_id': fields.many2one ('crm.lead', 'Lead/Opportunity',ondelete='cascade', track_visibility='onchange'),
    }

    _defaults = {
        'date': fields.datetime.now,
        'priority': '1',
        'state':  'to_do',
        'user_id': lambda self, cr, uid, ctx: uid,
        'active': 1
    }

    def on_change_partner_id(self, cr, uid, ids, partner_id, context=None):
        values = {}
        if partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
            values = {
                'partner_phone': partner.phone,
                'partner_mobile': partner.mobile,
            }
        return {'value': values}

    def compute_duration(self, cr, uid, ids, context=None):
        for phonecall in self.browse(cr, uid, ids, context=context):
            if phonecall.duration <= 0:
                duration = datetime.now() - datetime.strptime(phonecall.date, DEFAULT_SERVER_DATETIME_FORMAT)
                values = {'duration': duration.seconds/float(60)}
                self.write(cr, uid, [phonecall.id], values, context=context)
        return True

    def schedule_another_phonecall(self, cr, uid, ids, schedule_time, call_summary, \
                    user_id=False, team_id=False, categ_id=False, context=None):
        model_data = self.pool.get('ir.model.data')
        phonecall_dict = {}
        if not categ_id:
            try:
                res_id = model_data._get_id(cr, uid, 'crm', 'categ_phone2')
                categ_id = model_data.browse(cr, uid, res_id, context=context).res_id
            except ValueError:
                pass
        for call in self.browse(cr, uid, ids, context=context):
            if(call.state != "done"):
                call.state = "cancel"
                call.in_queue = False
            if not team_id:
                team_id = call.team_id and call.team_id.id or False
            if not user_id:
                user_id = call.user_id and call.user_id.id or False
            if not schedule_time:
                schedule_time = call.date
            vals = {
                    'name' : call_summary,
                    'user_id' : user_id or False,
                    'categ_id' : categ_id or False,
                    'description' : False,
                    'date' : schedule_time,
                    'team_id' : team_id or False,
                    'partner_id': call.partner_id and call.partner_id.id or False,
                    'partner_phone' : call.partner_phone,
                    'partner_mobile' : call.partner_mobile,
                    'priority': call.priority,
                    'opportunity_id': call.opportunity_id and call.opportunity_id.id or False,
            }
            new_id = self.create(cr, uid, vals, context=context)
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

    def on_change_opportunity(self, cr, uid, ids, opportunity_id, context=None):
        values = {}
        if opportunity_id:
            opportunity = self.pool.get('crm.lead').browse(cr, uid, opportunity_id, context=context)
            values = {
                'team_id' : opportunity.team_id and opportunity.team_id.id or False,
                'partner_phone' : opportunity.phone,
                'partner_mobile' : opportunity.mobile,
                'partner_id' : opportunity.partner_id and opportunity.partner_id.id or False,
            }
        return {'value' : values}

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

    def handle_partner_assignation(self, cr, uid, ids, action='create', partner_id=False, context=None):
        """
        Handle partner assignation during a lead conversion.
        if action is 'create', create new partner with contact and assign lead to new partner_id.
        otherwise assign lead to specified partner_id

        :param list ids: phonecalls ids to process
        :param string action: what has to be done regarding partners (create it, assign an existing one, or nothing)
        :param int partner_id: partner to assign if any
        :return dict: dictionary organized as followed: {lead_id: partner_assigned_id}
        """
        #TODO this is a duplication of the handle_partner_assignation method of crm_lead
        partner_ids = {}
        # If a partner_id is given, force this partner for all elements
        force_partner_id = partner_id
        for call in self.browse(cr, uid, ids, context=context):
            # If the action is set to 'create' and no partner_id is set, create a new one
            if action == 'create':
                partner_id = force_partner_id or self._call_create_partner(cr, uid, call, context=context)
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
                            'team_id': call.team_id and call.team_id.id or False,
                            'description': call.description or False,
                            'priority': call.priority,
                            'type': 'opportunity',
                            'phone': call.partner_phone or False,
                            'email_from': default_contact and default_contact.email,
                        })
            vals = {
                'partner_id': partner_id,
                'opportunity_id': opportunity_id,
            }
            self.write(cr, uid, [call.id], vals, context=context)
            opportunity_dict[call.id] = opportunity_id
        return opportunity_dict

    def action_make_meeting(self, cr, uid, ids, context=None):
        """
        Open meeting's calendar view to schedule a meeting on current phonecall.
        :return dict: dictionary value for created meeting view
        """
        partner_ids = []
        phonecall = self.browse(cr, uid, ids[0], context)
        if phonecall.partner_id and phonecall.partner_id.email:
            partner_ids.append(phonecall.partner_id.id)
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'calendar', 'action_calendar_event', context)
        res['context'] = {
            'default_phonecall_id': phonecall.id,
            'default_partner_ids': partner_ids,
            'default_user_id': uid,
            'default_email_from': phonecall.email_from,
            'default_name': phonecall.name,
            'default_opportunity_id': phonecall.opportunity_id.id,
        }
        return res

    def action_button_convert2opportunity(self, cr, uid, ids, context=None):
        """
        Convert a phonecall into an opp and then redirect to the opp view.

        :param list ids: list of calls ids to convert (typically contains a single id)
        :return dict: containing view information
        """
        if len(ids) != 1:
            raise UserError(_('It\'s only possible to convert one phonecall at a time.'))

        opportunity_dict = self.convert_opportunity(cr, uid, ids, context=context)
        return self.pool.get('crm.lead').redirect_opportunity_view(cr, uid, opportunity_dict[ids[0]], context)

    # ----------------------------------------
    # OpenChatter
    # ----------------------------------------

    def _call_set_partner_send_note(self, cr, uid, ids, context=None):
        return self.message_post(cr, uid, ids, body=_("Partner has been <b>created</b>."), context=context)

class crm_phonecall_category(osv.Model):
    _name = "crm.phonecall.category"
    _description = "Category of phonecall"
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'team_id': fields.many2one('crm.team', 'Sales Team'),
    }
