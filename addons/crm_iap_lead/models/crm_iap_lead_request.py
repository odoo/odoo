# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from math import floor, log10

from odoo import api, fields, models, _
from odoo.addons.iap import jsonrpc

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'https://iap-services.odoo.com'
MAX_LEAD = 50
MAX_CONTACT = 5


class CRMLeadMiningRequest(models.Model):
    _name = 'crm.iap.lead.request'
    _description = 'CRM Lead Mining Request'

    name = fields.Char(string='Lead Mining Request Name', required=True, readonly=True, default=lambda self: _('New'))
    state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('done', 'Done')], string='State', default='draft')

    # Request Data
    lead_number = fields.Integer(string='Number of Leads', required=True, default=10)
    search_type = fields.Selection([('companies', 'Companies'), ('people', 'Companies and their Contacts')], string='Look for', required=True, default='companies')

    # Lead / Opportunity Data
    lead_type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity')], string='Type', required=True, default='lead')
    team_id = fields.Many2one('crm.team', string='Sales Channel')
    user_id = fields.Many2one('res.users', string='Salesperson')
    tag_ids = fields.Many2many('crm.lead.tag', string='Tags')
    lead_ids = fields.One2many('crm.lead', 'lead_mining_request_id', string='Generated Lead / Opportunity')
    leads_count = fields.Integer(compute='_compute_leads_count', string='Number of Generated Leads')
    opportunity_count = fields.Integer(compute='_compute_leads_count', string='Number of Generated Opportunity')

    # Company Criteria Filter
    filter_on_size = fields.Boolean(string='Filter on Size', default=False)
    company_size_min = fields.Integer(string='Size', default=0)
    company_size_max = fields.Integer(default=1000)
    country_ids = fields.Many2many('res.country', string='Countries', required=True)
    state_ids = fields.Many2many('res.country.state', string='States')
    industry_ids = fields.Many2many('crm.iap.lead.industry', string='Industries')
    technology_ids = fields.Many2many('crm.iap.lead.technology', string='Technologies')

    # Contact Generation Filter
    contact_number = fields.Integer(string='Contact Number', required=True, default=1)
    contact_filter_type = fields.Selection([('role', 'Role'), ('seniority', 'Seniority')], string='Filter on', default='role')
    preferred_role_id = fields.Many2one('crm.iap.lead.role', string='Preferred Role')
    role_ids = fields.Many2many('crm.iap.lead.role', string='Other Roles')
    seniority_id = fields.Many2one('crm.iap.lead.seniority', string='Seniority')

    # Computed field for the blue tooltip on the form view
    contact_total_credit = fields.Integer(compute='_compute_contact_total_credit')

    _sql_constraints = [
        ('limit_contact_number', 'check(contact_number >= 1 and contact_number <= %d)' % MAX_CONTACT, 'Maximum %d contacts are allowed!' % MAX_CONTACT),
        ('limit_lead_number', 'check(lead_number >= 1 and lead_number <= %d)' % MAX_LEAD, 'Maximum %d leads are allowed!' % MAX_LEAD),
        ('check_company_size', 'check(company_size_min <= company_size_max)', 'The minimum size of the company should be less than or equal to the maximum size.'),
    ]

    @api.depends('contact_number', 'lead_number')
    def _compute_contact_total_credit(self):
        for req in self:
            req.contact_total_credit = req.contact_number * req.lead_number

    def _compute_leads_count(self):
        leads = self.env['crm.lead'].read_group([
            ('lead_mining_request_id', 'in', self.ids)
        ], fields=['lead_mining_request_id', 'type'], groupby=['lead_mining_request_id', 'type'], lazy=False)
        mapping = {(lead['lead_mining_request_id'][0], lead['type']): lead['__count'] for lead in leads}
        for request in self:
            request.leads_count = mapping.get((request.id, 'lead'), 0)
            request.opportunity_count = mapping.get((request.id, 'opportunity'), 0)

    @api.onchange('lead_number')
    def _onchange_lead_number(self):
        if self.lead_number <= 0:
            self.lead_number = 1
    
    @api.onchange('contact_number')
    def _onchange_contact_number(self):
        if self.contact_number <= 0:
            self.contact_number = 1

    @api.onchange('country_ids')
    def _onchange_country_ids(self):
        self.state_ids = []

    @api.model
    def _process_requests(self, autocommit=True):
        """ Cron Job for lead mining request processing"""
        _logger.info('Start Reveal Lead Mining Request Processing')
        requests = self.search([('state', '=', 'pending')])
        for req in requests:
            server_payload = self._prepare_iap_payload(req)
            enough_credit = self._perform_request(req, server_payload)
            if autocommit:
                # auto-commit for batch processing
                self._cr.commit()
            if not enough_credit:
                break       # stops the processing of this request and the following requests
            else:
                req.state = 'done'
        _logger.info('End Reveal Lead Mining Request Processing')

    def _prepare_iap_payload(self, req):
        """
        This will prepare the data to send to the server
        """
        payload = {'req_id': req.id,
                   'lead_number': req.lead_number,
                   'search_type': req.search_type,
                   'countries': req.country_ids.mapped('code')}
        if req.state_ids:
            payload['states'] = req.state_ids.mapped('code')
        if req.filter_on_size:
            payload.update({'company_size_min': req.company_size_min,
                            'company_size_max': req.company_size_max})
        if req.technology_ids:
            payload['technology_tags'] = req.technology_ids.mapped('tech_tag')
        if req.search_type == 'people':
            payload.update({'contact_number': req.contact_number,
                            'contact_filter_type': req.contact_filter_type})
            if req.contact_filter_type == 'role':
                payload.update({'preferred_role': req.preferred_role_id.reveal_id,
                                'other_roles': req.role_ids.mapped('reveal_id')})
            elif req.contact_filter_type == 'seniority':
                payload['seniority'] = req.seniority_id.reveal_id
        return payload

    def _perform_request(self, req, server_payload):
        """
        This will perform the request and create the corresponding leads.
        The user will be notified if he hasn't enough credits.
        """
        reveal_account = self.env['iap.account'].get('reveal')
        endpoint = self.env['ir.config_parameter'].sudo().get_param('reveal.endpoint', DEFAULT_ENDPOINT) + '/iap/clearbit/lead_mining_request'
        params = {
            'account_token': reveal_account.account_token,
            'data': server_payload
        }
        response = jsonrpc(endpoint, params=params, timeout=300)
        if response.get('credit_error'):
            self._notify_no_more_credit()
            return False
        else:
            self.env['ir.config_parameter'].sudo().set_param('reveal.request.already_notified', False)
            self._create_leads_from_response(req, response['data'])
        return True

    def _notify_no_more_credit(self):
        """
        Notify about the number of credit.
        In order to avoid to spam people each hour, an ir.config_parameter is set
        """
        already_notified = self.env['ir.config_parameter'].sudo().get_param('reveal.request.already_notified', False)
        if already_notified:
            return
        mail_template = self.env.ref('crm_iap_lead.lead_generation_no_credits')
        iap_account = self.env['iap.account'].search([('service_name', '=', 'reveal')], limit=1)
        # Get the email address of the creators of the Lead Mining Request
        res = self.env['crm.iap.lead.request'].search_read([], ['create_uid'])
        uids = set(r['create_uid'][0] for r in res if r.get('create_uid'))
        res = self.env['res.users'].search_read([('id', 'in', list(uids))], ['email'])
        emails = set(r['email'] for r in res if r.get('email'))

        mail_values = mail_template.generate_email(iap_account.id)
        mail_values['email_to'] = ','.join(emails)
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()
        self.env['ir.config_parameter'].sudo().set_param('reveal.request.already_notified', True)

    def _create_leads_from_response(self, req, response):
        """ This method will get response from service and create the leads accordingly """
        for data in response:
            company_data = data['company_data']
            if not company_data['clearbit_id']:
                return False
            already_created_lead = self.env['crm.lead'].search([('reveal_id', '=', company_data['clearbit_id'])])
            if already_created_lead:
                _logger.info('Existing lead for this clearbit_id [%s]', company_data['clearbit_id'])
                # Do not create a lead if the reveal_id is already known
            else:
                lead_vals = self._lead_vals_from_response(req, data)
                lead = self.env['crm.lead'].create(lead_vals)
                lead.message_post_with_view(
                    'crm_iap_lead.lead_message_template',
                    values=self._format_data_for_message_post(data),
                    subtype_id=self.env.ref('mail.mt_note').id
                )

    # Methods responsible for format response data into valid odoo lead data
    def _lead_vals_from_response(self, req, data):
        company_data = data.get('company_data')
        people_data = data.get('people_data')
        country_id = self.env['res.country'].search([('code', '=', company_data['country_code'])]).id
        website_url = 'https://www.%s' % company_data['domain'] if company_data['domain'] else False
        lead_vals = {
            # Lead vals from request itself
            'type': req.lead_type,
            'team_id': req.team_id.id,
            'tag_ids': [(6, 0, req.tag_ids.ids)],
            'user_id': req.user_id.id,
            'reveal_id': company_data['clearbit_id'],
            'lead_mining_request_id': req.id,
            # Lead vals from response
            'name': company_data['name'],
            'partner_name': company_data['legal_name'] or company_data['name'],
            'email_from': ",".join(company_data['email'] or []),    # TODO: move this to chatter message ? too long if many email addresses
            'phone': company_data['phone'] or (company_data['phone_numbers'] and company_data['phone_numbers'][0]) or '',
            'website': website_url,
            'street': company_data['location'],
            'city': company_data['city'],
            'zip': company_data['postal_code'],
            'country_id': country_id,
            'state_id': self._find_state_id(company_data['state_code'], country_id),
            'description': self._prepare_lead_description(company_data),
        }

        # If type is people then add first contact in lead data
        if people_data:
            lead_vals.update({
                'contact_name': people_data[0]['full_name'],
                'email_from': people_data[0]['email'],
                'function': people_data[0]['title'],
            })

        return lead_vals

    def _find_state_id(self, state_code, country_id):
        state_id = self.env['res.country.state'].search([('code', '=', state_code), ('country_id', '=', country_id)])
        if state_id:
            return state_id.id
        return False

    def _prepare_lead_description(self, company_data):
        description = ''
        if company_data['sector']:
            description += company_data['sector']
        if company_data['website_title']:
            description += '\n' + company_data['website_title']
        if company_data['twitter_bio']:
            description += '\n' + "Twitter Bio: " + company_data['twitter_bio']
        if company_data['twitter_followers']:
            description += ('\nTwitter %s followers, %s \n') % (company_data['twitter_followers'], company_data['twitter_location'] or '')

        numbers = ['raised', 'market_cap', 'employees', 'estimated_annual_revenue']
        millnames = ['', ' K', ' M', ' B', 'T']

        def millify(n):
            try:
                n = float(n)
                millidx = max(0, min(len(millnames) - 1, int(floor(0 if n == 0 else log10(abs(n)) / 3))))
                return '{:.0f}{}'.format(n / 10**(3 * millidx), millnames[millidx])
            except Exception:
                return n

        for key in numbers:
            if company_data.get(key):
                description += ' %s : %s,' % (key.replace('_', ' ').title(), millify(company_data[key]))
        return description

    def _format_data_for_message_post(self, result):
        company_data = result['company_data']
        people_data = result.get('people_data')
        log_data = {
            'twitter': company_data['twitter'],
            'description': company_data['description'],
            'logo': company_data['logo'],
            'name': company_data['name'],
            'phone_numbers': company_data['phone_numbers'],
            'facebook': company_data['facebook'],
            'linkedin': company_data['linkedin'],
            'crunchbase': company_data['crunchbase'],
            'tech': [t.replace('_', ' ').title() for t in company_data['tech']],
            'people_data': people_data,
        }
        timezone = company_data['timezone']
        if timezone:
            log_data.update({
                'timezone': timezone.replace('_', ' ').title(),
                'timezone_url': company_data['timezone_url'],
            })
        return log_data

    def action_submit(self):
        """
        Called upon clicking on the 'Submit' button.
        Changes the state to 'Pending' and assigns a definitive name to the request.
        """
        self.state = 'pending'
        if self.name == _('New'):
            self.name = self.env['ir.sequence'].next_by_code('crm.iap.lead.request') or _('New')

    def action_get_lead_tree_view(self):
        action = self.env.ref('crm.crm_lead_all_leads').read()[0]
        action['domain'] = [('id', 'in', self.lead_ids.ids), ('type', '=', 'lead')]
        return action

    def action_get_opportunity_tree_view(self):
        action = self.env.ref('crm.crm_lead_opportunities').read()[0]
        action['domain'] = [('id', 'in', self.lead_ids.ids), ('type', '=', 'opportunity')]
        return action
