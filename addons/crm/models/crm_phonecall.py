# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError

class CrmPhoneCall(models.Model):
    """ Model for CRM phonecalls """
    _name = "crm.phonecall"
    _description = "Phonecall"
    _order = "id desc"
    _inherit = ['mail.thread']

    def _default_get_state(self):
        state = self.env.context.get('default_state')
        if state:
            return state
        return 'open'

    date_action_last = fields.Datetime(string='Last Action', readonly=True)
    date_action_next = fields.Datetime(string='Next Action', readonly=True)
    create_date = fields.Datetime(string='Creation Date', readonly=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', oldname='section_id',\
                    index=True, help='Sales team to which Case belongs to.', default=lambda self: self.env['crm.team']._get_default_team_id())
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    partner_id = fields.Many2one('res.partner', string='Contact')
    company_id = fields.Many2one('res.company', string='Company')
    description = fields.Text()
    state = fields.Selection(
        [('open', 'Confirmed'),
         ('cancel', 'Cancelled'),
         ('pending', 'Pending'),
         ('done', 'Held')
         ], string='Status', readonly=True, track_visibility='onchange',
        help='The status is set to Confirmed, when a case is created.\n'
             'When the call is over, the status is set to Held.\n'
             'If the callis not applicable anymore, the status can be set to Cancelled.', default=lambda self: self._default_get_state())
    email_from = fields.Char(string='Email', size=128, help="These people will receive email.")
    date_open = fields.Datetime(string='Opened', readonly=True)
    # phonecall fields
    name = fields.Char(string='Call Summary', required=True)
    active = fields.Boolean(required=False, default=True)
    duration = fields.Float(help='Duration in minutes and seconds.')
    categ_id = fields.Many2one('crm.phonecall.category', string='Category')
    partner_phone = fields.Char('Phone')
    partner_mobile = fields.Char('Mobile')
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High')], default="1")
    date_closed = fields.Datetime('Closed', readonly=True)
    date = fields.Datetime(default=fields.Datetime.now)
    opportunity_id = fields.Many2one('crm.lead', string='Lead/Opportunity')

    @api.onchange('partner_id')
    def on_change_partner_id(self):
        self.partner_phone = self.partner_id.phone
        self.partner_mobile = self.partner_id.mobile

    @api.onchange('opportunity_id')
    def on_change_opportunity(self):
        if self.opportunity_id:
            self.team_id = self.opportunity_id.team_id.id
            self.partner_phone = self.opportunity_id.phone
            self.partner_mobile = self.opportunity_id.mobile
            self.partner_id = self.opportunity_id.partner_id.id

    @api.multi
    def write(self, values):
        """ Override to add case management: open/close dates """
        state = values.get('state')
        if state:
            if state == 'done':
                values['date_closed'] = fields.Datetime.now()
                self._compute_duration()
            elif state == 'open':
                values['date_open'] = fields.Datetime.now()
                values['duration'] = 0.0
        return super(CrmPhoneCall, self).write(values)

    @api.multi
    def redirect_phonecall_view(self):
        # Select the view
        self.ensure_one()
        tree_view_id = self.env.ref('crm.crm_case_phone_tree_view').id
        form_view_id = self.env.ref('crm.crm_case_phone_form_view').id
        search_view_id = self.env.ref('crm.view_crm_case_phonecalls_filter').id
        value = {
            'name': _('Phone Call'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'crm.phonecall',
            'res_id': self.id,
            'views': [(form_view_id, 'form'), (tree_view_id, 'tree'), (False, 'calendar')],
            'type': 'ir.actions.act_window',
            'search_view_id': search_view_id,
        }
        return value

    @api.multi
    def action_make_meeting(self):
        """
        Open meeting's calendar view to schedule a meeting on current phonecall.
        :return dict: dictionary value for created meeting view
        """
        self.ensure_one()
        partner_ids = []
        if self.partner_id.email:
            partner_ids.append(self.partner_id.id)
        result = self.env['ir.actions.act_window'].for_xml_id(
            'calendar', 'action_calendar_event')
        result['context'] = {
            'default_phonecall_id': self.id,
            'default_partner_ids': partner_ids,
            'default_user_id': self.env.uid,
            'default_email_from': self.email_from,
            'default_name': self.name,
            'default_opportunity_id': self.opportunity_id.id,
        }
        return result

    @api.multi
    def action_button_convert2opportunity(self):
        """
        Convert a phonecall into an opp and then redirect to the opp view.

        :return dict: containing view information
        """
        if len(self) != 1:
            raise UserError(_('It\'s only possible to convert one phonecall at a time.'))

        opportunity_dict = self.convert_opportunity()
        return opportunity_dict.values()[0].redirect_opportunity_view()

    @api.multi
    def schedule_another_phonecall(self, schedule_time, call_summary, user_id=False, team_id=False, categ_id=False, action='schedule'):
        """
        action :('schedule','Schedule a call'), ('log','Log a call')
        """
        phonecall_dict = {}
        if not categ_id:
            try:
                categ_id = self.env.ref('crm.categ_phone2').id
            except ValueError:
                pass
        for call in self:
            if not team_id:
                team_id = call.team_id.id
            if not user_id:
                user_id = call.user_id.id
            if not schedule_time:
                schedule_time = call.date
            vals = {
                    'name': call_summary,
                    'user_id': user_id,
                    'categ_id': categ_id,
                    'description': call.description,
                    'date': schedule_time,
                    'team_id': team_id,
                    'partner_id': call.partner_id.id,
                    'partner_phone': call.partner_phone,
                    'partner_mobile': call.partner_mobile,
                    'priority': call.priority,
                    'opportunity_id': call.opportunity_id.id,
            }
            phonecall = self.create(vals)
            if action == 'log':
                phonecall.write({'state': 'done'})
            phonecall_dict[call.id] = phonecall
        return phonecall_dict

    def convert_opportunity(self, opportunity_summary=False, partner_id=False, planned_revenue=0.0, probability=0.0):
        Partner = self.env['res.partner']
        opportunity_dict = {}
        default_contact = False
        for call in self:
            if not partner_id:
                partner_id = call.partner_id.id
            if partner_id:
                address_id = call.partner_id.address_get()['default']
                if address_id:
                    default_contact = Partner.browse(address_id)
            opportunity_id = call.opportunity_id.create({
                            'name': opportunity_summary or call.name,
                            'planned_revenue': planned_revenue,
                            'probability': probability,
                            'partner_id': partner_id,
                            'mobile': default_contact and default_contact.mobile or False,
                            'team_id': call.team_id.id,
                            'description': call.description,
                            'priority': call.priority,
                            'type': 'opportunity',
                            'phone': call.partner_phone,
                            'email_from': default_contact and default_contact.email or False
                            })
            vals = {
                'partner_id': partner_id,
                'opportunity_id': opportunity_id.id,
                'state': 'done'
            }
            call.write(vals)
            opportunity_dict[call.id] = opportunity_id
        return opportunity_dict

    def _compute_duration(self):
        for phonecall in self:
            if phonecall.duration <= 0:
                duration = fields.Datetime.from_string(fields.Datetime.now()) - fields.Datetime.from_string(phonecall.date)
                values = {'duration': duration.seconds / float(60)}
                phonecall.write(values)
        return True

class CrmPhoneCallCategory(models.Model):
    _name = "crm.phonecall.category"
    _description = "Category of phonecall"

    name = fields.Char(required=True, translate=True)
    team_id = fields.Many2one('crm.team', string='Sales Team')
