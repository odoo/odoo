# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import itertools
import logging
import re
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _
from odoo.addons.iap import jsonrpc
from odoo.addons.crm.models import crm_stage
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'https://iap-services.odoo.com'
DEFAULT_REVEAL_BATCH_LIMIT = 25
DEFAULT_REVEAL_MONTH_VALID = 6

class CRMRevealRule(models.Model):
    _name = 'crm.reveal.rule'
    _description = 'CRM Lead Generation Rules'
    _order = 'sequence'

    name = fields.Char(string='Rule Name', required=True)
    active = fields.Boolean(default=True)

    # Website Traffic Filter
    country_ids = fields.Many2many('res.country', string='Countries', help='Only visitors of following countries will be converted into leads/opportunities (using GeoIP).')
    state_ids = fields.Many2many('res.country.state', string='States', help='Only visitors of following states will be converted into leads/opportunities.')
    regex_url = fields.Char(string='URL Expression', help='Regex to track website pages. Leave empty to track the entire website, or / to target the homepage. Example: /page* to track all the pages which begin with /page')
    sequence = fields.Integer(help='Used to order the rules with same URL and countries. '
                                   'Rules with a lower sequence number will be processed first.')

    # Company Criteria Filter
    industry_tag_ids = fields.Many2many('crm.iap.lead.industry', string='Industries', help='Leave empty to always match. Odoo will not create lead if no match')
    filter_on_size = fields.Boolean(string="Filter on Size", default=True, help="Filter companies based on their size.")
    company_size_min = fields.Integer(string='Company Size', default=0)
    company_size_max = fields.Integer(default=1000)

    # Contact Generation Filter
    contact_filter_type = fields.Selection([('role', 'Role'), ('seniority', 'Seniority')], string="Filter On", required=True, default='role')
    preferred_role_id = fields.Many2one('crm.iap.lead.role', string='Preferred Role')
    other_role_ids = fields.Many2many('crm.iap.lead.role', string='Other Roles')
    seniority_id = fields.Many2one('crm.iap.lead.seniority', string='Seniority')
    extra_contacts = fields.Integer(string='Number of Contacts', help='This is the number of contacts to track if their role/seniority match your criteria. Their details will show up in the history thread of generated leads/opportunities. One credit is consumed per tracked contact.', default=1)

    # Lead / Opportunity Data
    lead_for = fields.Selection([('companies', 'Companies'), ('people', 'Companies and their Contacts')], string='Data Tracking', required=True, default='companies', help='Choose whether to track companies only or companies and their contacts')
    lead_type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity')], string='Type', required=True, default='opportunity')
    suffix = fields.Char(string='Suffix', help='This will be appended in name of generated lead so you can identify lead/opportunity is generated with this rule')
    team_id = fields.Many2one('crm.team', string='Sales Team')
    tag_ids = fields.Many2many('crm.lead.tag', string='Tags')
    user_id = fields.Many2one('res.users', string='Salesperson')
    priority = fields.Selection(crm_stage.AVAILABLE_PRIORITIES, string='Priority')
    lead_ids = fields.One2many('crm.lead', 'reveal_rule_id', string='Generated Lead / Opportunity')
    leads_count = fields.Integer(compute='_compute_leads_count', string='Number of Generated Leads')
    opportunity_count = fields.Integer(compute='_compute_leads_count', string='Number of Generated Opportunity')

    # This limits the number of extra contact.
    # Even if more than 5 extra contacts provided service will return only 5 contacts (see service module for more)
    _sql_constraints = [
        ('limit_extra_contacts', 'check(extra_contacts >= 1 and extra_contacts <= 5)', 'Maximum 5 contacts are allowed!'),
    ]

    @api.constrains('regex_url')
    def _check_regex_url(self):
        try:
            if self.regex_url:
                re.compile(self.regex_url)
        except Exception:
            raise ValidationError(_('Enter Valid Regex.'))

    @api.model
    def create(self, vals):
        self.clear_caches() # Clear the cache in order to recompute _get_active_rules
        return super(CRMRevealRule, self).create(vals)

    def write(self, vals):
        fields_set = {
            'country_ids', 'regex_url', 'active'
        }
        if set(vals.keys()) & fields_set:
            self.clear_caches() # Clear the cache in order to recompute _get_active_rules
        return super(CRMRevealRule, self).write(vals)

    def unlink(self):
        self.clear_caches() # Clear the cache in order to recompute _get_active_rules
        return super(CRMRevealRule, self).unlink()

    def _compute_leads_count(self):
        leads = self.env['crm.lead'].read_group([
            ('reveal_rule_id', 'in', self.ids)
        ], fields=['reveal_rule_id', 'type'], groupby=['reveal_rule_id', 'type'], lazy=False)
        mapping = {(lead['reveal_rule_id'][0], lead['type']): lead['__count'] for lead in leads}
        for rule in self:
            rule.leads_count = mapping.get((rule.id, 'lead'), 0)
            rule.opportunity_count = mapping.get((rule.id, 'opportunity'), 0)

    def action_get_lead_tree_view(self):
        action = self.env.ref('crm.crm_lead_all_leads').read()[0]
        action['domain'] = [('id', 'in', self.lead_ids.ids), ('type', '=', 'lead')]
        return action

    def action_get_opportunity_tree_view(self):
        action = self.env.ref('crm.crm_lead_opportunities').read()[0]
        action['domain'] = [('id', 'in', self.lead_ids.ids), ('type', '=', 'opportunity')]
        return action

    @api.model
    @tools.ormcache()
    def _get_active_rules(self):
        """
        Returns informations about the all rules.
        The return is in the form :
        {
            'country_rules': {
                'BE': [0, 1],
                'US': [0]
            },
            'rules': [
            {
                'id': 0,
                'url': ***,
                'country_codes': ['BE', 'US'],
                'state_codes': [('BE', False), ('US', 'NY'), ('US', 'CA')]
            },
            {
                'id': 1,
                'url': ***,
                'country_codes': ['BE'],
                'state_codes': [('BE', False)]
            }
            ]
        }
        """
        country_rules = {}
        rules_records = self.search([])
        rules = []
        # Fixes for special cases
        for rule in rules_records:
            regex_url = rule['regex_url']
            if not regex_url:
                regex_url = '.*'    # for all pages if url not given
            elif regex_url == '/':
                regex_url = '.*/$'  # for home
            countries = rule.country_ids.mapped('code')

            # First apply rules for any state in countries
            states = [(country_id.code, False) for country_id in rule.country_ids]
            if rule.state_ids:
                for state_id in rule.state_ids:
                    if (state_id.country_id.code, False) in states:
                        # Remove country because rule doesn't apply to any state
                        states.remove((state_id.country_id.code, False))
                    states += [(state_id.country_id.code, state_id.code)]
                
            rules.append({
                'id': rule.id,
                'regex': regex_url,
                'country_codes': countries,
                'state_codes': states
            })
            for country in countries:
                country_rules = self._add_to_country(country_rules, country, len(rules) - 1)
        return {
            'country_rules': country_rules,
            'rules': rules,
        }

    def _add_to_country(self, country_rules, country, rule_index):
        """
        Add the rule index to the country code in the country_rules
        """
        if country not in country_rules:
            country_rules[country] = []
        country_rules[country].append(rule_index)
        return country_rules

    def _match_url(self, url, country_code, state_code, rules_excluded):
        """
        Return the matching rule based on the country and URL.
        """
        all_rules = self._get_active_rules()
        rules_id = all_rules['country_rules'].get(country_code, [])

        rules_matched = []
        for rule_index in rules_id:
            rule = all_rules['rules'][rule_index]
            if ((country_code, state_code) in rule['state_codes'] or (country_code, False) in rule['state_codes'])\
                and str(rule['id']) not in rules_excluded\
                and re.search(rule['regex'], url):
                rules_matched.append(rule)
        return rules_matched

    @api.model
    def _process_lead_generation(self, autocommit=True):
        """ Cron Job for lead generation from page view """
        _logger.info('Start Reveal Lead Generation')
        self.env['crm.reveal.view']._clean_reveal_views()
        self._unlink_unrelevant_reveal_view()
        reveal_views = self._get_reveal_views_to_process()
        view_count = 0
        while reveal_views:
            view_count += len(reveal_views)
            server_payload = self._prepare_iap_payload(dict(reveal_views))
            enough_credit = self._perform_reveal_service(server_payload)
            if autocommit:
                # auto-commit for batch processing
                self._cr.commit()
            if enough_credit:
                reveal_views = self._get_reveal_views_to_process()
            else:
                reveal_views = False
        _logger.info('End Reveal Lead Generation - %s views processed', view_count)

    @api.model
    def _unlink_unrelevant_reveal_view(self):
        """
        We don't want to create the lead if in past (<6 months) we already
        created lead with given IP. So, we unlink crm.reveal.view with same IP
        as a already created lead.
        """
        months_valid = self.env['ir.config_parameter'].sudo().get_param('reveal.lead_month_valid', DEFAULT_REVEAL_MONTH_VALID)
        try:
            months_valid = int(months_valid)
        except ValueError:
            months_valid = DEFAULT_REVEAL_MONTH_VALID
        domain = []
        domain.append(('reveal_ip', '!=', False))
        domain.append(('create_date', '>', fields.Datetime.to_string(datetime.date.today() - relativedelta(months=months_valid))))
        leads = self.env['crm.lead'].with_context(active_test=False).search(domain)
        self.env['crm.reveal.view'].search([('reveal_ip', 'in', [lead.reveal_ip for lead in leads])]).unlink()

    @api.model
    def _get_reveal_views_to_process(self):
        """ Return list of reveal rule ids grouped by IPs """
        batch_limit = DEFAULT_REVEAL_BATCH_LIMIT
        query = """
            SELECT v.reveal_ip, array_agg(v.reveal_rule_id ORDER BY r.sequence)
            FROM crm_reveal_view v
            INNER JOIN crm_reveal_rule r
            ON v.reveal_rule_id = r.id
            WHERE v.reveal_state='to_process'
            GROUP BY v.reveal_ip
            LIMIT %d
            """ % batch_limit

        self.env.cr.execute(query)
        return self.env.cr.fetchall()

    def _prepare_iap_payload(self, pgv):
        """ This will prepare the page view and returns payload
            Payload sample
            {
                ips: {
                    '192.168.1.1': [1,4],
                    '192.168.1.6': [2,4]
                },
                rules: {
                    1: {rule_data},
                    2: {rule_data},
                    4: {rule_data}
                }
            }
        """
        new_list = list(set(itertools.chain.from_iterable(pgv.values())))
        rule_records = self.browse(new_list)
        return {
            'ips': pgv,
            'rules': rule_records._get_rules_payload()
        }

    def _get_rules_payload(self):
        company_country = self.env.user.company_id.country_id
        rule_payload = {}
        for rule in self:
            data = {
                'rule_id': rule.id,
                'lead_for': rule.lead_for,
                'countries': rule.country_ids.mapped('code'),
                'filter_on_size': rule.filter_on_size,
                'company_size_min': rule.company_size_min,
                'company_size_max': rule.company_size_max,
                'industry_tags': rule.industry_tag_ids.mapped('reveal_id'),
                'user_country': company_country and company_country.code or False
            }
            if rule.lead_for == 'people':
                data.update({
                    'contact_filter_type': rule.contact_filter_type,
                    'preferred_role': rule.preferred_role_id.reveal_id or '',
                    'other_roles': rule.other_role_ids.mapped('reveal_id'),
                    'seniority': rule.seniority_id.reveal_id or '',
                    'extra_contacts': rule.extra_contacts - 1
                })
            rule_payload[rule.id] = data
        return rule_payload

    def _perform_reveal_service(self, server_payload):
        result = False
        account_token = self.env['iap.account'].get('reveal')
        endpoint = self.env['ir.config_parameter'].sudo().get_param('reveal.endpoint', DEFAULT_ENDPOINT) + '/iap/clearbit/1/reveal'
        params = {
            'account_token': account_token.account_token,
            'data': server_payload
        }
        result = jsonrpc(endpoint, params=params, timeout=300)
        for res in result.get('reveal_data', []):
            if not res.get('not_found'):
                lead = self._create_lead_from_response(res)
                self.env['crm.reveal.view'].search([('reveal_ip', '=', res['ip'])]).unlink()
            else:
                self.env['crm.reveal.view'].search([('reveal_ip', '=', res['ip'])]).write({
                    'reveal_state': 'not_found'
                })
        if result.get('credit_error'):
            self.env['crm.iap.lead.helpers'].notify_no_more_credit('reveal', self._name, 'reveal.already_notified')
            return False
        else:
            self.env['ir.config_parameter'].sudo().set_param('reveal.already_notified', False)
        return True

    def _create_lead_from_response(self, result):
        """ This method will get response from service and create the lead accordingly """
        if result['rule_id']:
            rule = self.browse(result['rule_id'])
        else:
            # Not create a lead if the information match no rule
            # If there is no match, the service still returns all informations
            # in order to let custom code use it.
            return False
        if not result['clearbit_id']:
            return False
        already_created_lead = self.env['crm.lead'].search([('reveal_id', '=', result['clearbit_id'])])
        if already_created_lead:
            _logger.info('Existing lead for this clearbit_id [%s]', result['clearbit_id'])
            # Does not create a lead if the reveal_id is already known
            return False
        lead_vals = rule._lead_vals_from_response(result)
        lead = self.env['crm.lead'].create(lead_vals)
        lead.message_post_with_view(
            'crm_iap_lead.lead_message_template',
            values=self.env['crm.iap.lead.helpers'].format_data_for_message_post(result['reveal_data'], result.get('people_data')),
            subtype_id=self.env.ref('mail.mt_note').id
        )
        return lead

    # Methods responsible for format response data in to valid odoo lead data
    def _lead_vals_from_response(self, result):
        self.ensure_one()
        company_data = result['reveal_data']
        people_data = result.get('people_data')
        lead_vals = self.env['crm.iap.lead.helpers'].lead_vals_from_response(self.lead_type, self.team_id.id, self.tag_ids.ids, self.user_id.id, company_data, people_data)

        lead_vals.update({
            'priority': self.priority,
            'reveal_ip': result['ip'],
            'reveal_rule_id': self.id,
            'referred': 'Website Visitor',
            'reveal_iap_credits': result['credit'],
        })

        if self.suffix:
            lead_vals['name'] = '%s - %s' % (lead_vals['name'], self.suffix)

        return lead_vals
