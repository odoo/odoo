# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import itertools
import logging
import re
from dateutil.relativedelta import relativedelta
from math import floor, log10

import odoo
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
    regex_url = fields.Char(string='URL Expression', help='Regex to track website pages. Leave empty to track the entire website, or / to target the homepage. Example: /page* to track all the pages which begin with /page')
    sequence = fields.Integer(help='Used to order the rules with same URL and countries. '
                                   'Rules with a lower sequence number will be processed first.')

    # Company Criteria Filter
    industry_tag_ids = fields.Many2many('crm.reveal.industry', string='Industry Tags', help='Leave empty to always match. Odoo will not create lead if no match')
    company_size_min = fields.Integer(string='Min Company Size', help="Leave it as 0 if you don't want to use this filter.")
    company_size_max = fields.Integer(string='Max Company Size', help="Leave it as 0 if you don't want to use this filter.")

    # Contact Generation Filter
    preferred_role_id = fields.Many2one('crm.reveal.role', string='Preferred Role')
    other_role_ids = fields.Many2many('crm.reveal.role', string='Other Roles')
    seniority_id = fields.Many2one('crm.reveal.seniority', string='Seniority')
    extra_contacts = fields.Integer(string='Extra Contacts', help='This is the number of extra contacts to track if their role and seniority match your criteria.Their details will show up in the history thread of generated leads/opportunities. One credit is consumed per tracked contact.')

    calculate_credits = fields.Integer(compute='_compute_credit_count', string='Credit Used', readonly=True)

    # Lead / Opportunity Data
    lead_for = fields.Selection([('companies', 'Companies'), ('people', 'Companies + Contacts')], string='Data Tracking', required=True, default='companies', help='If you track company data, one credit will be consumed per lead/opportunity created. If you track company and contacts data, two credits will be consumed. Such data will be visible in the lead/opportunity.')
    lead_type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity')], string='Type', required=True, default='opportunity')
    suffix = fields.Char(string='Suffix', help='This will be appended in name of generated lead so you can identify lead/opportunity is generated with this rule')
    team_id = fields.Many2one('crm.team', string='Sales Channel')
    tag_ids = fields.Many2many('crm.lead.tag', string='Tags')
    user_id = fields.Many2one('res.users', string='Salesperson')
    priority = fields.Selection(crm_stage.AVAILABLE_PRIORITIES, string='Priority')
    lead_ids = fields.One2many('crm.lead', 'reveal_rule_id', string='Generated Lead / Opportunity')
    leads_count = fields.Integer(compute='_compute_leads_count', string='Number of Generated Leads')
    opportunity_count = fields.Integer(compute='_compute_leads_count', string='Number of Generated Opportunity')

    # This limits the number of extra contact.
    # Even if more than 5 extra contacts provided service will return only 5 contacts (see service module for more)
    _sql_constraints = [
        ('limit_extra_contacts', 'check(extra_contacts >= 0 and extra_contacts <= 5)', 'Maximum 5 extra contacts are allowed!'),
    ]

    @api.constrains('regex_url')
    def _check_regex_url(self):
        try:
            if self.regex_url:
                re.compile(self.regex_url)
        except Exception:
            raise ValidationError(_('Enter Valid Regex.'))

    @api.model
    def _assert_geoip(self):
        if not odoo._geoip_resolver:
            message = _('Lead Generation requires a GeoIP resolver which could not be found on your system. Please consult https://pypi.org/project/GeoIP/.')
            self.env['bus.bus'].sendone(
                (self._cr.dbname, 'res.partner', self.env.user.partner_id.id),
                {'type': 'simple_notification', 'title': _('Missing Library'), 'message': message, 'sticky': True, 'warning': True})

    @api.model
    def create(self, vals):
        self.clear_caches() # Clear the cache in order to recompute _get_active_rules
        self._assert_geoip()
        return super(CRMRevealRule, self).create(vals)

    def write(self, vals):
        fields_set = {
            'country_ids', 'regex_url', 'active'
        }
        if set(vals.keys()) & fields_set:
            self.clear_caches() # Clear the cache in order to recompute _get_active_rules
        self._assert_geoip()
        return super(CRMRevealRule, self).write(vals)

    def unlink(self):
        self.clear_caches() # Clear the cache in order to recompute _get_active_rules
        return super(CRMRevealRule, self).unlink()

    @api.depends('extra_contacts', 'lead_for')
    def _compute_credit_count(self):
        """ Computes maximum IAP credit can be consumed per lead """
        credit = 1
        if self.lead_for == 'people':
            credit += 1
            if self.extra_contacts:
                credit += self.extra_contacts
        self.calculate_credits = credit

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
                'country_codes': ['BE', 'US']
            },
            {
                'id': 1,
                'url': ***,
                'country_codes': ['BE']
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
            rules.append({
                'id': rule.id,
                'regex': regex_url,
                'country_codes': countries
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

    def _match_url(self, url, country_code, rules_excluded):
        """
        Return the matching rule based on the country and URL.
        """
        all_rules = self._get_active_rules()
        rules_id = all_rules['country_rules'].get(country_code, [])
        rules_matched = []
        for rule_index in rules_id:
            rule = all_rules['rules'][rule_index]
            if str(rule['id']) not in rules_excluded and re.search(rule['regex'], url):
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
                'company_size_min': rule.company_size_min,
                'company_size_max': rule.company_size_max,
                'industry_tags': rule.industry_tag_ids.mapped('reveal_id'),
                'user_country': company_country and company_country.code or False
            }
            if rule.lead_for == 'people':
                data.update({
                    'preferred_role': rule.preferred_role_id.reveal_id or '',
                    'other_roles': rule.other_role_ids.mapped('reveal_id'),
                    'seniority': rule.seniority_id.reveal_id or '',
                    'extra_contacts': rule.extra_contacts
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
            self._notify_no_more_credit()
            return False
        else:
            self.env['ir.config_parameter'].sudo().set_param('reveal.already_notified', False)
        return True

    def _notify_no_more_credit(self):
        """
        Notify about the number of credit.
        In order to avoid to spam people each hour, an ir.config_parameter is set
        """
        already_notified = self.env['ir.config_parameter'].sudo().get_param('reveal.already_notified', False)
        if already_notified:
            return
        mail_template = self.env.ref('crm_reveal.reveal_no_credits')
        iap_account = self.env['iap.account'].search([('service_name', '=', 'reveal')], limit=1)
        # Get the email address of the creators of the Lead Generation Rules
        res = self.env['crm.reveal.rule'].search_read([], ['create_uid'])
        uids = set(r['create_uid'][0] for r in res if r.get('create_uid'))
        res = self.env['res.users'].search_read([('id', 'in', list(uids))], ['email'])
        emails = set(r['email'] for r in res if r.get('email'))

        mail_values = mail_template.generate_email(iap_account.id)
        mail_values['email_to'] = ','.join(emails)
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()
        self.env['ir.config_parameter'].sudo().set_param('reveal.already_notified', True)


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
            'crm_reveal.lead_message_template',
            values=self._format_data_for_message_post(result),
            subtype_id=self.env.ref('mail.mt_note').id
        )
        return lead

    # Methods responsible for format response data in to valid odoo lead data
    def _lead_vals_from_response(self, result):
        self.ensure_one()
        reveal_data = result['reveal_data']
        people_data = result.get('people_data')
        country_id = self.env['res.country'].search([('code', '=', reveal_data['country_code'])]).id
        website_url = 'https://www.%s' % reveal_data['domain'] if reveal_data['domain'] else False
        lead_vals = {
            # Lead vals from rule itself
            'type': self.lead_type,
            'team_id': self.team_id.id,
            'tag_ids': [(6, 0, self.tag_ids.ids)],
            'priority': self.priority,
            'user_id': self.user_id.id,
            'reveal_ip': result['ip'],
            'reveal_rule_id': self.id,
            'reveal_id': result['clearbit_id'],
            'referred': 'Website Visitor',
            # Lead vals from response
            'name': reveal_data['name'],
            'reveal_iap_credits': result['credit'],
            'partner_name': reveal_data['legal_name'] or reveal_data['name'],
            'email_from': ",".join(reveal_data['email'] or []),
            'phone': reveal_data['phone'] or (reveal_data['phone_numbers'] and reveal_data['phone_numbers'][0]) or '',
            'website': website_url,
            'street': reveal_data['location'],
            'city': reveal_data['city'],
            'zip': reveal_data['postal_code'],
            'country_id': country_id,
            'state_id': self._find_state_id(reveal_data['state_name'], reveal_data['state_code'], country_id),
            'description': self._prepare_lead_description(reveal_data),
        }

        if self.suffix:
            lead_vals['name'] = '%s - %s' % (lead_vals['name'], self.suffix)

        # If type is people then add first contact in lead data
        if people_data:
            lead_vals.update({
                'contact_name': people_data[0]['full_name'],
                'email_from': people_data[0]['email'],
                'function': people_data[0]['title'],
            })
        return lead_vals

    def _find_state_id(self, state_code, state_name, country_id):
        state_id = self.env['res.country.state'].search([('code', '=', state_code), ('country_id', '=', country_id)])
        if state_id:
            return state_id.id
        return False

    def _prepare_lead_description(self, reveal_data):
        description = ''
        if reveal_data['sector']:
            description += reveal_data['sector']
        if reveal_data['website_title']:
            description += '\n' + reveal_data['website_title']
        if reveal_data['twitter_bio']:
            description += '\n' + "Twitter Bio: " + reveal_data['twitter_bio']
        if reveal_data['twitter_followers']:
            description += ('\nTwitter %s followers, %s \n') % (reveal_data['twitter_followers'], reveal_data['twitter_location'] or '')

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
            if reveal_data.get(key):
                description += ' %s : %s,' % (key.replace('_', ' ').title(), millify(reveal_data[key]))
        return description

    def _format_data_for_message_post(self, result):
        reveal_data = result['reveal_data']
        people_data = result.get('people_data')
        log_data = {
            'twitter': reveal_data['twitter'],
            'description': reveal_data['description'],
            'logo': reveal_data['logo'],
            'name': reveal_data['name'],
            'phone_numbers': reveal_data['phone_numbers'],
            'facebook': reveal_data['facebook'],
            'linkedin': reveal_data['linkedin'],
            'crunchbase': reveal_data['crunchbase'],
            'tech': [t.replace('_', ' ').title() for t in reveal_data['tech']],
            'people_data': people_data,
        }
        timezone = result['ip_time_zone'] or reveal_data['timezone']
        if timezone:
            log_data.update({
                'timezone': timezone.replace('_', ' ').title(),
                'timezone_url': reveal_data['timezone_url'],
            })
        return log_data


class IndustryTag(models.Model):
    """ Industry Tags of Acquisition Rules """
    _name = 'crm.reveal.industry'
    _description = 'Industry Tag'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    reveal_id = fields.Char(required=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Tag name already exists!'),
    ]


class PeopleRole(models.Model):
    """ CRM Reveal People Roles for People """
    _name = 'crm.reveal.role'
    _description = 'People Role'

    name = fields.Char(string='Role Name', required=True, translate=True)
    reveal_id = fields.Char(required=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Role name already exists!'),
    ]

    @api.depends('name')
    def name_get(self):
        return [(role.id, role.name.replace('_', ' ').title()) for role in self]


class PeopleSeniority(models.Model):
    """ Seniority for People Rules """
    _name = 'crm.reveal.seniority'
    _description = 'People Seniority'

    name = fields.Char(string='Name', required=True, translate=True)
    reveal_id = fields.Char(required=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Name already exists!'),
    ]

    @api.depends('name')
    def name_get(self):
        return [(seniority.id, seniority.name.replace('_', ' ').title()) for seniority in self]
