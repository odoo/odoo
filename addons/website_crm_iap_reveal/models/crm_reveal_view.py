# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models

DEFAULT_REVEAL_VIEW_WEEKS_VALID = 5

class CRMRevealView(models.Model):
    _name = 'crm.reveal.view'
    _description = 'CRM Reveal View'
    _order = 'id desc'

    reveal_ip = fields.Char(string='IP Address')
    reveal_rule_id = fields.Many2one('crm.reveal.rule', string='Lead Generation Rule', index='btree_not_null')
    reveal_state = fields.Selection([('to_process', 'To Process'), ('not_found', 'Not Found')], default='to_process', string="State", index=True)
    create_date = fields.Datetime(index=True)

    def init(self):
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('crm_reveal_view_ip_rule_id',))
        if not self._cr.fetchone():
            self._cr.execute('CREATE UNIQUE INDEX crm_reveal_view_ip_rule_id ON crm_reveal_view (reveal_rule_id,reveal_ip)')
        self._cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s', ('crm_reveal_view_state_create_date',))
        if not self._cr.fetchone():
            self._cr.execute('CREATE INDEX crm_reveal_view_state_create_date ON crm_reveal_view (reveal_state,create_date)')


    @api.model
    def _clean_reveal_views(self):
        """ Remove old views (> 1 month) """
        weeks_valid = self.env['ir.config_parameter'].sudo().get_param('reveal.view_weeks_valid', DEFAULT_REVEAL_VIEW_WEEKS_VALID)
        try:
            weeks_valid = int(weeks_valid)
        except ValueError:
            weeks_valid = DEFAULT_REVEAL_VIEW_WEEKS_VALID
        domain = []
        domain.append(('reveal_state', '=', 'not_found'))
        domain.append(('create_date', '<', fields.Datetime.to_string(datetime.date.today() - relativedelta(weeks=weeks_valid))))
        self.search(domain).unlink()

    def _create_reveal_view(self, website_id, url, ip_address, country_code, state_code, rules_excluded):
        # we are avoiding reveal if reveal_view already created for this IP
        rules = self.env['crm.reveal.rule']._match_url(website_id, url, country_code, state_code, rules_excluded)
        if rules:
            query = """
                    INSERT INTO crm_reveal_view (reveal_ip, reveal_rule_id, reveal_state, create_date)
                    VALUES (%s, %s, 'to_process', now() at time zone 'UTC')
                    ON CONFLICT DO NOTHING;
                    """ * len(rules)
            params = []
            for rule in rules:
                params += [ip_address, rule['id']]
                rules_excluded.append(str(rule['id']))
            self.env.cr.execute(query, params)
            return rules_excluded
        return False
