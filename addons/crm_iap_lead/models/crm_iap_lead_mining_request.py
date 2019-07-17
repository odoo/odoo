# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.iap import jsonrpc, InsufficientCreditError

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'https://iap-services.odoo.com'

MAX_LEAD = 200
MAX_CONTACT = 5

CREDIT_PER_COMPANY = 1
CREDIT_PER_CONTACT = 1


class CRMLeadMiningRequest(models.Model):
    _name = 'crm.iap.lead.mining.request'
    _description = 'CRM Lead Mining Request'

    def _default_lead_type(self):
        if self.env.user.has_group('crm.group_use_lead'):
            return 'lead'
        else:
            return 'opportunity'

    name = fields.Char(string='Request Number', required=True, readonly=True, default=lambda self: _('New'), copy=False)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Done'), ('error', 'Error')], string='Status', required=True, default='draft')

    # Request Data
    lead_number = fields.Integer(string='Number of Leads', required=True, default=10)
    search_type = fields.Selection([('companies', 'Companies'), ('people', 'Companies and their Contacts')], string='Target', required=True, default='companies')
    error = fields.Text(string='Error', readonly=True)

    # Lead / Opportunity Data
    lead_type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity')], string='Type', required=True, default=_default_lead_type)
    team_id = fields.Many2one('crm.team', string='Sales Team', domain="[('use_opportunities', '=', True)]")
    user_id = fields.Many2one('res.users', string='Salesperson')
    tag_ids = fields.Many2many('crm.lead.tag', string='Tags')
    lead_ids = fields.One2many('crm.lead', 'lead_mining_request_id', string='Generated Lead / Opportunity')
    leads_count = fields.Integer(compute='_compute_leads_count', string='Number of Generated Leads')

    # Company Criteria Filter
    filter_on_size = fields.Boolean(string='Filter on Size', default=False)
    company_size_min = fields.Integer(string='Size', default=1)
    company_size_max = fields.Integer(default=1000)
    country_ids = fields.Many2many('res.country', string='Countries')
    state_ids = fields.Many2many('res.country.state', string='States')
    industry_ids = fields.Many2many('crm.iap.lead.industry', string='Industries')

    # Contact Generation Filter
    contact_number = fields.Integer(string='Number of Contacts', default=1)
    contact_filter_type = fields.Selection([('role', 'Role'), ('seniority', 'Seniority')], string='Filter on', default='role')
    preferred_role_id = fields.Many2one('crm.iap.lead.role', string='Preferred Role')
    role_ids = fields.Many2many('crm.iap.lead.role', string='Other Roles')
    seniority_id = fields.Many2one('crm.iap.lead.seniority', string='Seniority')

    # Fields for the blue tooltip
    lead_credits = fields.Char(compute='_compute_tooltip', readonly=True)
    lead_contacts_credits = fields.Char(compute='_compute_tooltip', readonly=True)

    @api.onchange('lead_number', 'contact_number')
    def _compute_tooltip(self):
        for record in self:
            total_credits = CREDIT_PER_COMPANY * record.lead_number
            contact_credits = CREDIT_PER_CONTACT * record.contact_number
            total_contact_credits = contact_credits * record.lead_number
            message_contact = _("""Up to %d additional credits will be consumed
                                per company to identify its contacts (making a
                                total of %d credits for this request).""")
            record.lead_credits = _('%d credits will be consumed to find %d companies.') % (total_credits, record.lead_number)
            record.lead_contacts_credits = message_contact % (contact_credits, total_contact_credits)

    @api.depends('lead_ids')
    def _compute_leads_count(self):
        for req in self:
            req.leads_count = len(req.lead_ids)

    @api.onchange('lead_number')
    def _onchange_lead_number(self):
        if self.lead_number <= 0:
            self.lead_number = 1
        elif self.lead_number > MAX_LEAD:
            self.lead_number = MAX_LEAD

    @api.onchange('contact_number')
    def _onchange_contact_number(self):
        if self.contact_number <= 0:
            self.contact_number = 1
        elif self.contact_number > MAX_CONTACT:
            self.contact_number = MAX_CONTACT

    @api.onchange('country_ids')
    def _onchange_country_ids(self):
        self.state_ids = []

    @api.onchange('company_size_min')
    def _onchange_company_size_min(self):
        if self.company_size_min <= 0:
            self.company_size_min = 1
        elif self.company_size_min > self.company_size_max:
            self.company_size_min = self.company_size_max

    @api.onchange('company_size_max')
    def _onchange_company_size_max(self):
        if self.company_size_max < self.company_size_min:
            self.company_size_max = self.company_size_min
    
    def _prepare_iap_payload(self):
        """
        This will prepare the data to send to the server
        """
        self.ensure_one()
        payload = {'lead_number': self.lead_number,
                   'search_type': self.search_type,
                   'countries': self.country_ids.mapped('code')}
        if self.state_ids:
            payload['states'] = self.state_ids.mapped('code')
        if self.filter_on_size:
            payload.update({'company_size_min': self.company_size_min,
                            'company_size_max': self.company_size_max})
        if self.industry_ids:
            payload['industry_ids'] = self.industry_ids.mapped('reveal_id')
        if self.search_type == 'people':
            payload.update({'contact_number': self.contact_number,
                            'contact_filter_type': self.contact_filter_type})
            if self.contact_filter_type == 'role':
                payload.update({'preferred_role': self.preferred_role_id.reveal_id,
                                'other_roles': self.role_ids.mapped('reveal_id')})
            elif self.contact_filter_type == 'seniority':
                payload['seniority'] = self.seniority_id.reveal_id
        return payload

    def _perform_request(self):
        """
        This will perform the request and create the corresponding leads.
        The user will be notified if he hasn't enough credits.
        """
        server_payload = self._prepare_iap_payload()
        reveal_account = self.env['iap.account'].get('reveal')
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        endpoint = self.env['ir.config_parameter'].sudo().get_param('reveal.endpoint', DEFAULT_ENDPOINT) + '/iap/clearbit/1/lead_mining_request'
        params = {
            'account_token': reveal_account.account_token,
            'dbuuid': dbuuid,
            'data': server_payload
        }
        try:
            response = jsonrpc(endpoint, params=params, timeout=300)
            return response['data']
        except InsufficientCreditError as e:
            self.error = 'Insufficient credits. Recharge your account and retry.'
            self.state = 'error'
            self._cr.commit()
            raise e

    def _create_leads_from_response(self, result):
        """ This method will get the response from the service and create the leads accordingly """
        self.ensure_one()
        lead_vals = []
        messages_to_post = {}
        for data in result:
            lead_vals.append(self._lead_vals_from_response(data))
            messages_to_post[data['company_data']['clearbit_id']] = self.env['crm.iap.lead.helpers'].format_data_for_message_post(data['company_data'], data.get('people_data'))
        leads = self.env['crm.lead'].create(lead_vals)
        for lead in leads:
            if messages_to_post.get(lead.reveal_id):
                lead.message_post_with_view('crm_iap_lead.lead_message_template', values=messages_to_post[lead.reveal_id], subtype_id=self.env.ref('mail.mt_note').id)

    # Methods responsible for format response data into valid odoo lead data
    @api.model
    def _lead_vals_from_response(self, data):
        self.ensure_one()
        company_data = data.get('company_data')
        people_data = data.get('people_data')
        lead_vals = self.env['crm.iap.lead.helpers'].lead_vals_from_response(self.lead_type, self.team_id.id, self.tag_ids.ids, self.user_id.id, company_data, people_data)
        lead_vals['lead_mining_request_id'] = self.id
        return lead_vals

    @api.model
    def get_empty_list_help(self, help):
        help_title = _('Create a Lead Mining Request')
        sub_title = _('Generate new leads based on their country, industry, size, etc.')
        return '<p class="o_view_nocontent_smiling_face">%s</p><p class="oe_view_nocontent_alias">%s</p>' % (help_title, sub_title)

    def action_draft(self):
        self.ensure_one()
        self.name = _('New')
        self.state = 'draft'

    def action_submit(self):
        self.ensure_one()
        if self.name == _('New'):
            self.name = self.env['ir.sequence'].next_by_code('crm.iap.lead.mining.request') or _('New')
        results = self._perform_request()
        if results:
            self._create_leads_from_response(results)
            self.state = 'done'
        if self.lead_type == 'lead':
            return self.action_get_lead_action()
        elif self.lead_type == 'opportunity':
            return self.action_get_opportunity_action()

    def action_get_lead_action(self):
        self.ensure_one()
        action = self.env.ref('crm.crm_lead_all_leads').read()[0]
        action['domain'] = [('id', 'in', self.lead_ids.ids), ('type', '=', 'lead')]
        action['help'] = _("""<p class="o_view_nocontent_empty_folder">
            No leads found
        </p><p>
            No leads could be generated according to your search criteria
        </p>""")
        return action

    def action_get_opportunity_action(self):
        self.ensure_one()
        action = self.env.ref('crm.crm_lead_opportunities').read()[0]
        action['domain'] = [('id', 'in', self.lead_ids.ids), ('type', '=', 'opportunity')]
        action['help'] = _("""<p class="o_view_nocontent_empty_folder">
            No opportunities found
        </p><p>
            No opportunities could be generated according to your search criteria
        </p>""")
        return action
