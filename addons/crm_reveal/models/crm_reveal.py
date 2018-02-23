# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re
from math import floor, log10

from odoo import api, fields, models, tools
from odoo.addons.iap import jsonrpc
from odoo.addons.crm.models import crm_stage

_logger = logging.getLogger(__name__)

# TODO: replace it with our server's url
DEFAULT_ENDPOINT = 'http://localhost:8069/reveal'


class CRMLeadRule(models.Model):

    _name = 'crm.reveal.rule'
    _description = 'CRM Reveal Lead Rules'

    name = fields.Char(string='Rule Name', required=True)
    active = fields.Boolean(default=True)

    # Website Traffic Filter
    country_ids = fields.Many2many('res.country', string='Countries')
    regex_url = fields.Char(string='URL Regex')

    # Company Criteria Filter
    industry_tag_ids = fields.Many2many('crm.reveal.industry', string="Industry Tags")
    company_size_min = fields.Integer(string='Company Size Min', help="fill 0 if you don't want this filter to check")
    company_size_max = fields.Integer(string='Company Size Max', help="fill 0 if you don't want this filter to check")

    # Contact Generation Filter
    preferred_role_id = fields.Many2one('crm.reveal.role', string="Preferred Role")
    other_role_ids = fields.Many2many('crm.reveal.role', string="Other Roles")
    seniority_id = fields.Many2one('crm.reveal.seniority', string="Seniority")
    extra_contacts = fields.Integer(string="Extra Contacts")

    calculate_credits = fields.Integer(compute='_compute_credit_count', string="Credit Used", readonly=True)

    # Lead / Opportunity Data
    lead_for = fields.Selection([('companies', 'Companies'), ('people', 'Companies + People')], string='Generate Leads For', required=True, default="people")
    lead_type = fields.Selection([('lead', 'Lead'), ('opportunity', 'Opportunity')], string='Type', required=True, default="opportunity")
    suffix = fields.Char(string='Suffix')
    team_id = fields.Many2one('crm.team', string='Sales Channel')
    stage_id = fields.Many2one('crm.stage', string='Stage')
    tag_ids = fields.Many2many('crm.lead.tag', string='Tags')
    user_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
    priority = fields.Selection(crm_stage.AVAILABLE_PRIORITIES, string='Priority')
    lead_ids = fields.One2many('crm.lead', 'reveal_rule_id', string="Generated Lead / Opportunity")
    leads_count = fields.Integer(compute='_compute_leads_count', string="Number of Generated Leads")

    _sql_constraints = [
        ('limit_extra_contacts', 'check(extra_contacts >= 0 and extra_contacts <= 5)', "Maximum 5 extra contacts are allowed!"),
    ]

    @api.multi
    def _compute_leads_count(self):
        leads = self.env['crm.lead'].read_group([
            ('reveal_rule_id', 'in', self.ids)
        ], fields=['reveal_rule_id'], groupby=['reveal_rule_id'])
        mapping = dict([(lead['reveal_rule_id'][0], lead['reveal_rule_id_count']) for lead in leads])
        for rule in self:
            rule.leads_count = mapping.get(rule.id, 0)

    @api.depends('extra_contacts', 'lead_for')
    def _compute_credit_count(self):
        credit = 1
        if self.lead_for == 'people':
            credit += 1
            if self.extra_contacts:
                credit += self.extra_contacts
        self.calculate_credits = credit

    @api.model
    def create(self, vals):
        self.clear_caches()
        return super(CRMLeadRule, self).create(vals)

    @api.multi
    def write(self, vals):
        self.clear_caches()
        return super(CRMLeadRule, self).write(vals)

    @api.multi
    def unlink(self):
        self.clear_caches()
        return super(CRMLeadRule, self).unlink()

    @api.multi
    def action_get_lead_tree_view(self):
        action = self.env.ref('crm.crm_lead_all_leads').read()[0]
        action['domain'] = [('id', 'in', self.lead_ids.ids)]
        return action

    @api.model
    @tools.ormcache()
    def get_regex(self):
        return self.search([]).mapped('regex_url')

    def match_url(self, url):
        if re.findall('|'.join([rg for rg in self.get_regex() if rg]), url):
            return True
        return False

    @api.model
    def process_lead_generation(self):
        http_session_records = self.env['http.session'].search([])
        for session in http_session_records:
            page_views = session.pageview_ids.search([('crm_reveal_scanned', '=', False), ('session_id', '=', session.id)])
            if page_views:
                self.process_reveal_request(session,page_views.mapped('url'), session.ip_address)
                for pv in page_views:
                    pv.crm_reveal_scanned = True

    @api.model
    def process_reveal_request(self, session_record, paths, ip):
        """Entry point form http dispatch"""
        lead_exist = self.env['crm.lead'].with_context(active_test=False).search_count([('reveal_ip', '=', ip)])
        if not lead_exist:
            rules = self._get_matching_rules(paths)
            if rules:
                rules._perform_reveal_service(session_record, ip)

    def _get_matching_rules(self, paths):
        active_rules = self.search([])
        rules = self.env['crm.reveal.rule']
        for rule in active_rules:
            try:
                if rule.regex_url:
                    if list(filter(lambda p: re.match(rule.regex_url, p, re.I | re.M), paths)):
                        rules += rule
                else:
                    rules += rule
            except Exception as e:
                _logger.error("CRM Reveal Service: matching regex %s" % (e,))
        return rules

    def _get_request_payload(self):
        rule_data = []
        company_country = self.env.user.company_id.country_id
        for rule in self:
            data = {
                'rule_id': rule.id,
                'lead_for': rule.lead_for,
                'countries': rule.country_ids.mapped('code'),
                'company_size_min': rule.company_size_min,
                'company_size_max': rule.company_size_max,
                'industry_tags': rule.industry_tag_ids.mapped('name'),
                'user_country': company_country and company_country.code or False
            }
            if rule.lead_for == 'people':
                data.update({
                    'preferred_role': rule.preferred_role_id and rule.preferred_role_id.name or '',
                    'other_roles': rule.other_role_ids.mapped('name'),
                    'seniority': rule.seniority_id and rule.seniority_id.name or '',
                    'extra_contacts': rule.extra_contacts
                })
            rule_data.append(data)
        return rule_data

    def _perform_reveal_service(self,session_record, ip):
        result = False
        account_token = self.env['iap.account'].get('reveal')
        endpoint = self.env['ir.config_parameter'].sudo().get_param('reveal.endpoint', DEFAULT_ENDPOINT)

        params = {
            'account_token': account_token.account_token,
            'ip': ip,
            'rules': self._get_request_payload()
        }

        result = jsonrpc(endpoint, params=params)
        if result:
            lead = self._process_response(result, ip)
            if lead:
                session_record.lead_id = lead.id

    def _process_response(self, result, ip):
        """This method will get response from service and create the lead accordingly"""
        rule = self.search([('id', '=', result['rule_id'])])
        # default values for lead based on rule
        lead_vals = {
            'type': rule.lead_type,
            'team_id': rule.team_id.id,
            'tag_ids': [(6, 0, rule.tag_ids.ids)],
            'priority': rule.priority,
            'user_id': rule.user_id.id,
            'stage_id': rule.stage_id.id,
            'reveal_ip': ip,
            'reveal_rule_id': rule.id,
            'referred': 'Website Visitor'
        }
        lead_vals.update(self._lead_vals_from_response(result))  # Update lead values based on service response
        if rule.suffix:
            lead_vals['name'] = lead_vals['name'] + ' - ' + rule.suffix
        lead = self.env['crm.lead'].create(lead_vals)
        msg_post_data = self._format_data_for_message_post(result)
        lead.message_post_with_view('crm_reveal.lead_message_template', values=msg_post_data, subtype_id=self.env.ref('mail.mt_note').id)
        return lead

    # Methods responsible for format response data in to valid odoo lead data
    def _lead_vals_from_response(self, result):
        reveal_data = result['reveal_data']
        people_data = result.get('people_data')
        country_id = self.env['res.country'].search([('code', '=', reveal_data['country_code'])]).id
        data = {
            'name': reveal_data['name'],
            'iap_credits': result['credit'],
            'partner_name': reveal_data['legal_name'] or reveal_data['name'],
            'phone': reveal_data['phone'],
            'website': reveal_data['domain'],
            'street': reveal_data['location'],
            'city': reveal_data['city'],
            'zip': reveal_data['postal_code'],
            'country_id': country_id,
            'state_id': self._find_state_id(reveal_data['state_name'], reveal_data['state_code'], country_id),
            'description': self._prepare_lead_description(reveal_data),
        }
        if people_data:
            # Save first contact in lead data
            data.update({
                'contact_name': people_data[0]['full_name'],
                'email_from': people_data[0]['email'],
                'function': people_data[0]['role'],
            })

        return data

    def _find_state_id(self, state_code, state_name, country_id):
        state_id = self.env['res.country.state'].search([('code', '=', state_code), ('country_id', '=', country_id)])
        if state_id:
            return state_id.id
        else:
            return self.env['res.country.state'].create({
                'country_id': country_id,
                'code': state_code,
                'name': state_name
            }).id

    def _prepare_lead_description(self, reveal_data):

        description = ""
        if reveal_data['sector']:
            description += reveal_data['sector']

        if reveal_data['website_title']:
            description += "\n" + reveal_data['website_title']

        if reveal_data['twitter_bio']:
            description += "\n" + "Twitter Bio: " + reveal_data['twitter_bio']

        if reveal_data['twitter_followers']:
            description += ("\nTwitter %s followers, %s \n") % (reveal_data['twitter_followers'], reveal_data['twitter_location'] or '')

        numbers = ['raised', 'market_cap', 'employees', 'estimated_annual_revenue']
        millnames = ['', ' K', ' M', ' B', 'T']

        def millify(n):
            try:
                n = float(n)
                millidx = max(0, min(len(millnames) - 1, int(floor(0 if n == 0 else log10(abs(n)) / 3))))
                return '{:.0f}{}'.format(n / 10**(3 * millidx), millnames[millidx])
            except Exception as e:
                return n

        for key in numbers:
            if reveal_data.get(key):
                description += "%s : %s, " % (key.replace('_', ' ').title(), millify(reveal_data[key]))

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
                'timezone_link': timezone.lower().replace('_', '-'),
            })

        return log_data

    # TODO: remove this method just for test
    @api.multi
    def test_rule(self):
        return {
            'name': 'action_test_rule',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'reveal.test.rule',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


class IndustryTag(models.Model):
    """ Industry Tags of Acquisition Rules """
    _name = 'crm.reveal.industry'
    _description = 'Industry Tag'

    name = fields.Char(string='Tag Name', required=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]


class PeopleRole(models.Model):
    """ CRM Reveal People Roles for People """
    _name = 'crm.reveal.role'
    _description = 'People Role'

    name = fields.Char(string='Role Name', required=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Role name already exists!"),
    ]

    @api.multi
    @api.depends('name')
    def name_get(self):
        result = []
        for role in self:
            name = role.name.replace('_', ' ').title()
            result.append((role.id, name))
        return result


class PeopleSeniority(models.Model):
    """ Seniority for People Rules """
    _name = 'crm.reveal.seniority'
    _description = 'People Seniority'

    name = fields.Char(string='Name', required=True, translate=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Name already exists!"),
    ]

    @api.multi
    @api.depends('name')
    def name_get(self):
        result = []
        for seniority in self:
            name = seniority.name.replace('_', ' ').title()
            result.append((seniority.id, name))
        return result
