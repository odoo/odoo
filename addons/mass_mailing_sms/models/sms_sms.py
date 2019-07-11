# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import werkzeug.urls

from odoo import api, fields, models, tools

from odoo.addons.link_tracker.models.link_tracker import URL_REGEX


class SmsSms(models.Model):
    _inherit = ['sms.sms']

    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Mass Mailing')
    statistics_ids = fields.One2many('sms.statistics', 'sms_sms_id', string='Statistics')

    def _update_body_short_links(self):
        """ Override to tweak shortened URLs by adding statistics ids, allowing to
        find customer back once clicked. """
        res = dict.fromkeys(self.ids, False)
        for record in self:
            if not record.mass_mailing_id or not record.body:
                continue
            body = record.body
            for match in re.findall(URL_REGEX, body):
                href = match[0]
                url = match[1]

                parsed = werkzeug.urls.url_parse(url, scheme='http')
                if parsed.scheme.startswith('http') and parsed.path.startswith('/r/'):
                    new_href = href.replace(url, url + '/s/' + str(record.id))
                    body = body.replace(href, new_href)
            res[record.id] = body
        return res

    @api.multi
    def _postprocess_sent_sms(self, iap_results, failure_reason=None, delete_all=False):
        success_sms_ids = [item['res_id'] for item in iap_results if item['state'] == 'success']
        failed_sms_ids = [item['res_id'] for item in iap_results if item['state'] != 'success']
        if any(sms.mass_mailing_id for sms in self):
            if success_sms_ids:
                success_stats = self.env['sms.statistics'].search([
                    ('sms_sms_id_int', 'in', success_sms_ids)
                ])
                if success_stats:
                    success_stats.write({'sent': fields.Datetime.now(), 'exception': False})
            if failed_sms_ids:
                failed_stats = self.env['sms.statistics'].search([
                    ('sms_sms_id_int', 'in', success_sms_ids)
                ])
                if failed_stats:
                    failed_stats.write({'exception': fields.Datetime.now()})
        return super(SmsSms, self)._postprocess_sent_sms(iap_results, failure_reason=failure_reason, delete_all=delete_all)
