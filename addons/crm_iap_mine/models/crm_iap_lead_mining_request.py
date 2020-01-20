# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, _
from odoo.addons.iap.tools import iap_tools
from odoo.exceptions import UserError

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

    def _default_country_ids(self):
        return self.env.user.company_id.country_id

    name = fields.Char(string='Request Number', required=True, readonly=True, default=lambda self: _('New'), copy=False)
    state = fields.Selection([('draft', 'Draft'), ('error', 'Error'), ('done', 'Done')], string='Status', required=True, default='draft')

    # Request Data
    lead_number = fields.Integer(string='Number of Leads', required=True, default=3)
    search_type = fields.Selection([('companies', 'Companies'), ('people', 'Companies and their Contacts')], string='Target', required=True, default='companies')
    error_type = fields.Selection([
        ('credits', 'Insufficient Credits'),
        ('no_result', 'No Result'),
    ], string='Error Type', copy=False, readonly=True)

    # Lead / Opportunity Data

    lead_type = fields.Selection([('lead', 'Leads'), ('opportunity', 'Opportunities')], string='Type', required=True, default=_default_lead_type)
    display_lead_label = fields.Char(compute='_compute_display_lead_label')
    team_id = fields.Many2one(
        'crm.team', string='Sales Team', ondelete="set null",
        domain="[('use_opportunities', '=', True)]", readonly=False, compute='_compute_team_id', store=True)
    user_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
    tag_ids = fields.Many2many('crm.tag', string='Tags')
    lead_ids = fields.One2many('crm.lead', 'lead_mining_request_id', string='Generated Lead / Opportunity')
    lead_count = fields.Integer(compute='_compute_lead_count', string='Number of Generated Leads')

    # Company Criteria Filter
    filter_on_size = fields.Boolean(string='Filter on Size', default=False)
    company_size_min = fields.Integer(string='Size', default=1)
    company_size_max = fields.Integer(default=1000)
    country_ids = fields.Many2many('res.country', string='Countries', default=_default_country_ids)
    state_ids = fields.Many2many('res.country.state', string='States')
    available_state_ids = fields.One2many('res.country.state', compute='_compute_available_state_ids',
        help="List of available states based on selected countries")
    industry_ids = fields.Many2many('crm.iap.lead.industry', string='Industries')

    # Contact Generation Filter
    contact_number = fields.Integer(string='Number of Contacts', default=10)
    contact_filter_type = fields.Selection([('role', 'Role'), ('seniority', 'Seniority')], string='Filter on', default='role')
    preferred_role_id = fields.Many2one('crm.iap.lead.role', string='Preferred Role')
    role_ids = fields.Many2many('crm.iap.lead.role', string='Other Roles')
    seniority_id = fields.Many2one('crm.iap.lead.seniority', string='Seniority')

    # Fields for the blue tooltip
    lead_credits = fields.Char(compute='_compute_tooltip', readonly=True)
    lead_contacts_credits = fields.Char(compute='_compute_tooltip', readonly=True)
    lead_total_credits = fields.Char(compute='_compute_tooltip', readonly=True)

    @api.depends('lead_type', 'lead_number')
    def _compute_display_lead_label(self):
        selection_description_values = {
            e[0]: e[1] for e in self._fields['lead_type']._description_selection(self.env)}
        for request in self:
            lead_type = selection_description_values[request.lead_type]
            request.display_lead_label = '%s %s' % (request.lead_number, lead_type)


    @api.onchange('lead_number', 'contact_number')
    def _compute_tooltip(self):
        for record in self:
            company_credits = CREDIT_PER_COMPANY * record.lead_number
            contact_credits = CREDIT_PER_CONTACT * record.contact_number
            total_contact_credits = contact_credits * record.lead_number
            record.lead_contacts_credits = _("Up to %d additional credits will be consumed to identify %d contacts per company.") % (contact_credits*company_credits, record.contact_number)
            record.lead_credits = _('%d credits will be consumed to find %d companies.') % (company_credits, record.lead_number)
            record.lead_total_credits = _("This makes a total of %d credits for this request.") % (total_contact_credits + company_credits)

    @api.depends('lead_ids.lead_mining_request_id')
    def _compute_lead_count(self):
        if self.ids:
            leads_data = self.env['crm.lead']._read_group(
                [('lead_mining_request_id', 'in', self.ids)],
                ['lead_mining_request_id'], ['lead_mining_request_id'])
        else:
            leads_data = []
        mapped_data = dict(
            (m['lead_mining_request_id'][0], m['lead_mining_request_id_count'])
            for m in leads_data)
        for request in self:
            request.lead_count = mapped_data.get(request.id, 0)

    @api.depends('user_id', 'lead_type')
    def _compute_team_id(self):
        """ When changing the user, also set a team_id or restrict team id
        to the ones user_id is member of. """
        for mining in self:
            # setting user as void should not trigger a new team computation
            if not mining.user_id:
                continue
            user = mining.user_id
            if mining.team_id and user in mining.team_id.member_ids | mining.team_id.user_id:
                continue
            team_domain = [('use_leads', '=', True)] if mining.lead_type == 'lead' else [('use_opportunities', '=', True)]
            team = self.env['crm.team']._get_default_team_id(user_id=user.id, domain=team_domain)
            mining.team_id = team.id

    @api.depends('country_ids')
    def _compute_available_state_ids(self):
        """ States for some specific countries should not be offered as filtering options because
        they drastically reduce the amount of IAP reveal results.

        For example, in Belgium, only 11% of companies have a defined state within the
        reveal service while the rest of them have no state defined at all.

        Meaning specifying states for that country will yield a lot less results than what you could
        expect, which is not the desired behavior.
        Obviously all companies are active within a state, it's just a lack of data in the reveal
        service side.

        To help users create meaningful iap searches, we only keep the states filtering for several
        whitelisted countries (based on their country code).
        The complete list and reasons for this change can be found on task-2471703. """

        for lead_mining_request in self:
            countries = lead_mining_request.country_ids.filtered(lambda country:
                country.code in iap_tools._STATES_FILTER_COUNTRIES_WHITELIST)
            lead_mining_request.available_state_ids = self.env['res.country.state'].search([
                ('country_id', 'in', countries.ids)
            ])

    @api.onchange('available_state_ids')
    def _onchange_available_state_ids(self):
        self.state_ids -= self.state_ids.filtered(
            lambda state: (state._origin.id or state.id) not in self.available_state_ids.ids
        )

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

    @api.model
    def get_empty_list_help(self, help_string):
        help_title = _('Create a Lead Mining Request')
        sub_title = _('Generate new leads based on their country, industry, size, etc.')
        return '<p class="o_view_nocontent_smiling_face">%s</p><p class="oe_view_nocontent_alias">%s</p>' % (help_title, sub_title)

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
            # accumulate all reveal_ids (separated by ',') into one list
            # eg: 3 records with values: "175,176", "177" and "190,191"
            # will become ['175','176','177','190','191']
            all_industry_ids = [
                reveal_id.strip()
                for reveal_ids in self.mapped('industry_ids.reveal_ids')
                for reveal_id in reveal_ids.split(',')
            ]
            payload['industry_ids'] = all_industry_ids
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
        self.error_type = False
        server_payload = self._prepare_iap_payload()
        reveal_account = self.env['iap.account'].get('reveal')
        dbuuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        params = {
            'account_token': reveal_account.account_token,
            'dbuuid': dbuuid,
            'data': server_payload
        }
        try:
            response = self._iap_contact_mining(params, timeout=300)
            if not response.get('data'):
                self.error_type = 'no_result'
                return False

            return response['data']
        except iap_tools.InsufficientCreditError as e:
            self.error_type = 'credits'
            self.state = 'error'
            return False
        except Exception as e:
            raise UserError(_("Your request could not be executed: %s", e))

    def _iap_contact_mining(self, params, timeout=300):
        endpoint = self.env['ir.config_parameter'].sudo().get_param('reveal.endpoint', DEFAULT_ENDPOINT) + '/iap/clearbit/1/lead_mining_request'
        return iap_tools.iap_jsonrpc(endpoint, params=params, timeout=timeout)

    def _create_leads_from_response(self, result):
        """ This method will get the response from the service and create the leads accordingly """
        self.ensure_one()
        lead_vals_list = []
        messages_to_post = {}
        for data in result:
            lead_vals_list.append(self._lead_vals_from_response(data))

            template_values = data['company_data']
            template_values.update({
                'flavor_text': _("Opportunity created by Odoo Lead Generation"),
                'people_data': data.get('people_data'),
            })
            messages_to_post[data['company_data']['clearbit_id']] = template_values
        leads = self.env['crm.lead'].create(lead_vals_list)
        for lead in leads:
            if messages_to_post.get(lead.reveal_id):
                lead.message_post_with_view('iap_mail.enrich_company', values=messages_to_post[lead.reveal_id], subtype_id=self.env.ref('mail.mt_note').id)

    # Methods responsible for format response data into valid odoo lead data
    @api.model
    def _lead_vals_from_response(self, data):
        self.ensure_one()
        company_data = data.get('company_data')
        people_data = data.get('people_data')
        lead_vals = self.env['crm.iap.lead.helpers'].lead_vals_from_response(self.lead_type, self.team_id.id, self.tag_ids.ids, self.user_id.id, company_data, people_data)
        lead_vals['lead_mining_request_id'] = self.id
        return lead_vals

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
        elif self.env.context.get('is_modal'):
            # when we are inside a modal already, we re-open the same record
            # that way, the form view is updated and the correct error message appears
            # (sadly, there is no way to simply 'reload' a form view within a modal)
            return {
                'name': _('Generate Leads'),
                'res_model': 'crm.iap.lead.mining.request',
                'views': [[False, 'form']],
                'target': 'new',
                'type': 'ir.actions.act_window',
                'res_id': self.id,
                'context': dict(self.env.context, edit=True, form_view_initial_mode='edit')
            }
        else:
            # will reload the form view and show the error message on top
            return False

    def action_get_lead_action(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("crm.crm_lead_all_leads")
        action['domain'] = [('id', 'in', self.lead_ids.ids), ('type', '=', 'lead')]
        return action

    def action_get_opportunity_action(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("crm.crm_lead_opportunities")
        action['domain'] = [('id', 'in', self.lead_ids.ids), ('type', '=', 'opportunity')]
        return action

    def action_buy_credits(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.env['iap.account'].get_credits_url(service_name='reveal'),
        }
