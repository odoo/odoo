# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls

from odoo import fields, models, _


class SMSComposer(models.TransientModel):
    _inherit = 'sms.composer'

    # mass mode with mass sms
    mass_sms_allow_unsubscribe = fields.Boolean('Include opt-out link', default=True)
    mailing_id = fields.Many2one('mailing.mailing', string='Mailing')
    utm_campaign_id = fields.Many2one('utm.campaign', string='Campaign')

    # ------------------------------------------------------------
    # Mass mode specific
    # ------------------------------------------------------------

    def _get_unsubscribe_url(self, res_id, trace_code, number):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return werkzeug.urls.url_join(
            base_url,
            '/sms/%s/%s' % (self.mailing_id.id, trace_code)
        )

    def _prepare_mass_sms_trace_values(self, record, sms_values):
        trace_code = self.env['mailing.trace']._get_random_code()
        trace_values = {
            'model': self.res_model,
            'res_id': record.id,
            'trace_type': 'sms',
            'mass_mailing_id': self.mailing_id.id,
            'sms_number': sms_values['number'],
            'sms_code': trace_code,
        }
        if sms_values['state'] == 'error':
            if sms_values['error_code'] == 'sms_number_format':
                trace_values['sent'] = fields.Datetime.now()
                trace_values['bounced'] = fields.Datetime.now()
            else:
                trace_values['exception'] = fields.Datetime.now()
        elif sms_values['state'] == 'canceled':
            trace_values['canceled'] = fields.Datetime.now()
        else:
            if self.mass_sms_allow_unsubscribe:
                sms_values['body'] = '%s\n%s' % (sms_values['body'] or '', _('STOP SMS : %s') % self._get_unsubscribe_url(record.id, trace_code, sms_values['number']))
        return trace_values

    def _get_blacklist_record_ids(self, records, recipients_info):
        """ Consider opt-outed contact as being blacklisted for that specific
        mailing. """
        res = super(SMSComposer, self)._get_blacklist_record_ids(records, recipients_info)
        if self.mailing_id:
            optout_res_ids = self.mailing_id._get_opt_out_list_sms()
            res += optout_res_ids
        return res

    def _get_done_record_ids(self, records, recipients_info):
        """ A/B testing could lead to records having been already mailed. """
        res = super(SMSComposer, self)._get_done_record_ids(records, recipients_info)
        if self.mailing_id:
            seen_ids, seen_list = self.mailing_id._get_seen_list_sms()
            res += seen_ids
        return res

    def _prepare_body_values(self, records):
        all_bodies = super(SMSComposer, self)._prepare_body_values(records)
        if self.mailing_id:
            tracker_values = self.mailing_id._get_link_tracker_values()
            for sms_id, body in all_bodies.items():
                body = self.env['link.tracker'].sudo()._convert_links_text(body, tracker_values)
                all_bodies[sms_id] = body
        return all_bodies

    def _prepare_mass_sms_values(self, records):
        result = super(SMSComposer, self)._prepare_mass_sms_values(records)
        if self.composition_mode == 'mass' and self.mailing_id:
            for record in records:
                sms_values = result[record.id]

                trace_values = self._prepare_mass_sms_trace_values(record, sms_values)
                sms_values.update({
                    'mailing_id': self.mailing_id.id,
                    'mailing_trace_ids': [(0, 0, trace_values)],
                })
        return result

    def _prepare_mass_sms(self, records, sms_record_values):
        sms_all = super(SMSComposer, self)._prepare_mass_sms(records, sms_record_values)
        if self.mailing_id:
            updated_bodies = sms_all._update_body_short_links()
            for sms in sms_all:
                sms.body = updated_bodies[sms.id]
        return sms_all
