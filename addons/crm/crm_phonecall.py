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
from openerp import models, fields, api, _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _

class crm_phonecall(models.Model):
    """ Model for CRM phonecalls """
    _name = "crm.phonecall"
    _description = "Phonecall"
    _order = "id desc"
    _inherit = ['mail.thread']

    @api.multi
    def _get_default_state(self):
        if self._context.get('default_state'):
            return self._context.get('default_state')
        return 'open'

    date_action_last = fields.Datetime('Last Action', readonly=1)
    date_action_next = fields.Datetime('Next Action', readonly=1)
    create_date = fields.Datetime('Creation Date' , readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', 
                select=True, help='Sales team to which Case belongs to.')
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self._uid)
    partner_id = fields.Many2one('res.partner', 'Contact')
    company_id = fields.Many2one('res.company', 'Company')
    description = fields.Text('Description')
    state = fields.Selection(
        [('open', 'Confirmed'),
         ('cancel', 'Cancelled'),
         ('pending', 'Pending'),
         ('done', 'Held')
         ], string='Status', readonly=True, track_visibility='onchange',
        help='The status is set to Confirmed, when a case is created.\n'
             'When the call is over, the status is set to Held.\n'
             'If the callis not applicable anymore, the status can be set to Cancelled.',
        default=lambda self: self._get_default_state())
    email_from = fields.Char('Email', size=128, help="These people will receive email.")
    date_open = fields.Datetime('Opened', readonly=True)
    # phonecall fields
    name = fields.Char('Call Summary', required=True)
    active = fields.Boolean('Active', required=False, default=1)
    duration = fields.Float('Duration', help='Duration in minutes and seconds.')
    categ_id = fields.Many2one('crm.phonecall.category', 'Category')
    partner_phone = fields.Char('Phone')
    partner_mobile = fields.Char('Mobile')
    priority = fields.Selection([('0','Low'), ('1','Normal'), ('2','High')], 'Priority', default='1')
    date_closed = fields.Datetime('Closed', readonly=True)
    date = fields.Datetime('Date',default=fields.datetime.now())
    opportunity_id = fields.Many2one ('crm.lead', 'Lead/Opportunity')

    @api.multi
    def write(self, values):
        """ Override to add case management: open/close dates """
        if values.get('state'):
            if values.get('state') == 'done':
                values['date_closed'] = fields.datetime.now()
                self.compute_duration()
            elif values.get('state') == 'open':
                values['date_open'] = fields.datetime.now()
                values['duration'] = 0.0
        return super(crm_phonecall, self).write(values)

    @api.multi
    def compute_duration(self):
        for phonecall in self:
            if phonecall.duration <= 0:
                duration = datetime.now() - datetime.strptime(phonecall.date, DEFAULT_SERVER_DATETIME_FORMAT)
                values = {'duration': duration.seconds/float(60)}
                self.write(values)
        return True

    @api.multi
    def schedule_another_phonecall(self, ids, schedule_time, call_summary, user_id=False, team_id=False, categ_id=False, action='schedule'):
        """
        action :('schedule','Schedule a call'), ('log','Log a call')
        """
        model_data = self.env['ir.model.data']
        phonecall_dict = {}
        if not categ_id:
            try:
                res_id = model_data._get_id('crm', 'categ_phone2')
                categ_id = model_data.browse(res_id).res_id
            except ValueError:
                pass
        for call in self.browse(ids):
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
                    'description' : call.description or False,
                    'date' : schedule_time,
                    'team_id' : team_id or False,
                    'partner_id': call.partner_id and call.partner_id.id or False,
                    'partner_phone' : call.partner_phone,
                    'partner_mobile' : call.partner_mobile,
                    'priority': call.priority,
                    'opportunity_id': call.opportunity_id and call.opportunity_id.id or False,
            }
            new_id = self.create(vals)
            if action == 'log':
                new_id.write({'state': 'done'})
            phonecall_dict[call.id] = new_id
        return phonecall_dict

    @api.one
    def _call_create_partner(self, phonecall):
        partner = self.pool.get('res.partner')
        partner_id = self.partner_id.create({
                    'name': phonecall.name,
                    'user_id': phonecall.user_id.id,
                    'comment': phonecall.description,
                    'address': []
                    })
        return partner_id.id

    @api.onchange('partner_id')
    def on_change_partner_id(self):
        self.partner_phone = self.partner_id.phone if self.partner_id.phone else ''
        self.partner_mobile = self.partner_id.mobile if self.partner_id.mobile else ''

    @api.onchange('opportunity_id')
    def on_change_opportunity(self):
        team_id = self.opportunity_id.team_id and self.opportunity_id.team_id.id or False
        partner_phone = self.opportunity_id.phone
        partner_mobile = self.opportunity_id.mobile
        partner_id = self.opportunity_id.partner_id and self.opportunity_id.partner_id.id or False

    @api.multi
    def _call_set_partner(self, partner_id):
        write_res = self.write({'partner_id' : partner_id})
        self._call_set_partner_send_note()
        return write_res

    @api.multi
    def _call_create_partner_address(self, phonecall, partner_id):
        address = self.pool.get('res.partner')
        return self.partner_id.create({
                    'parent_id': partner_id,
                    'name': phonecall.name,
                    'phone': phonecall.partner_phone,
        })

    @api.multi
    def handle_partner_assignation(self, action='create', partner_id=False):
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
        for call in self:
            # If the action is set to 'create' and no partner_id is set, create a new one
            if action == 'create':
                partner_id = force_partner_id or self._call_create_partner(call)
                self._call_create_partner_address(call, partner_id)
            self._call_set_partner([call.id], partner_id)
            partner_ids[call.id] = partner_id
        return partner_ids

    @api.multi
    def redirect_phonecall_view(self, phonecall_id):
        model_data = self.env['ir.model.data']
        # Select the view
        tree_view = model_data.get_object_reference('crm', 'crm_case_phone_tree_view')
        form_view = model_data.get_object_reference('crm', 'crm_case_phone_form_view')
        search_view = model_data.get_object_reference('crm', 'view_crm_case_phonecalls_filter')
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

    @api.multi
    def convert_opportunity(self, opportunity_summary=False, partner_id=False, planned_revenue=0.0, probability=0.0):
        partner = self.env['res.partner']
        opportunity = self.env['crm.lead']
        opportunity_dict = {}
        default_contact = False
        for call in self:
            if not partner_id:
                partner_id = call.partner_id and call.partner_id.id or False
            if partner_id:
                address_id = call.partner_id.address_get([partner_id])['default']
                if address_id:
                    default_contact = call.partner_id.browse(address_id)
            opportunity_id = opportunity.create({
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
                            'email_from': default_contact and default_contact.email})
            vals = {
                'partner_id': partner_id,
                'opportunity_id': opportunity_id.id,
                'state': 'done'
                }
            call.write(vals)
            opportunity_dict[call.id] = opportunity_id
        return opportunity_dict

    @api.multi
    def action_make_meeting(self):
        """
        Open meeting's calendar view to schedule a meeting on current phonecall.
        :return dict: dictionary value for created meeting view
        """
        partner_ids = []
        phonecall = self
        if phonecall.partner_id and phonecall.partner_id.email:
            partner_ids.append(phonecall.partner_id.id)
        res = self.env['ir.actions.act_window'].for_xml_id('calendar', 'action_calendar_event')
        res['context'] = {
            'default_phonecall_id': phonecall.id,
            'default_partner_ids': partner_ids,
            'default_user_id': self._uid,
            'default_email_from': phonecall.email_from,
            'default_name': phonecall.name,
        }
        return res

    @api.multi
    def action_button_convert2opportunity(self):
        """
        Convert a phonecall into an opp and then redirect to the opp view.

        :param list ids: list of calls ids to convert (typically contains a single id)
        :return dict: containing view information
        """
        if len(self) != 1:
            raise Warning(('It\'s only possible to convert one phonecall at a time.'))

        opportunity_dict = self.convert_opportunity()
        return opportunity_dict.values()[0].redirect_opportunity_view()

    # ----------------------------------------
    # OpenChatter
    # ----------------------------------------
    @api.multi
    def _call_set_partner_send_note(self):
        return self.message_post(body=_("Partner has been <b>created</b>."))

class crm_phonecall_category(models.Model):
    _name = "crm.phonecall.category"
    _description = "Category of phonecall"
    name = fields.Char('Name', required=True, translate=True)
    team_id = fields.Many2one('crm.team', 'Sales Team')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: