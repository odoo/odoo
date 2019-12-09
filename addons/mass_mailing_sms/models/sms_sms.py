# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import fields, models

TEXT_URL_REGEX = r'https?://[a-zA-Z0-9@:%._+~#=/-]+'


class SmsSms(models.Model):
    _inherit = ['sms.sms']

    mailing_id = fields.Many2one('mailing.mailing', string='Mass Mailing')
    mailing_trace_ids = fields.One2many('mailing.trace', 'sms_sms_id', string='Statistics')

    def _update_body_short_links(self):
        """ Override to tweak shortened URLs by adding statistics ids, allowing to
        find customer back once clicked. """
        shortened_schema = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/r/'
        res = dict.fromkeys(self.ids, False)
        for sms in self:
            if not sms.mailing_id or not sms.body:
                res[sms.id] = sms.body
                continue

            body = sms.body
            for url in re.findall(TEXT_URL_REGEX, body):
                if url.startswith(shortened_schema):
                    body = body.replace(url, url + '/s/%s' % sms.id)
            res[sms.id] = body
        return res

    def _postprocess_iap_sent_sms(self, iap_results, failure_reason=None, delete_all=False):
        all_sms_ids = [item['res_id'] for item in iap_results]
        if any(sms.mailing_id for sms in self.env['sms.sms'].sudo().browse(all_sms_ids)):
            for state in self.IAP_TO_SMS_STATE.keys():
                sms_ids = [item['res_id'] for item in iap_results if item['state'] == state]
                traces = self.env['mailing.trace'].sudo().search([
                    ('sms_sms_id_int', 'in', sms_ids)
                ])
                if traces and state == 'success':
                    traces.write({'sent': fields.Datetime.now(), 'exception': False})
                elif traces:
                    traces.set_failed(failure_type=self.IAP_TO_SMS_STATE[state])
        return super(SmsSms, self)._postprocess_iap_sent_sms(iap_results, failure_reason=failure_reason, delete_all=delete_all)
