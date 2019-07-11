# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import werkzeug.urls

from odoo import fields, models


class SMSComposer(models.TransientModel):
    _inherit = 'sms.composer'

    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Mass Mailing')
    utm_campaign_id = fields.Many2one('utm.campaign', string='Campaign')

    def _get_unsubscribe_url(self, res_id, number):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = werkzeug.urls.url_join(
            base_url, 'mail/mailing/%(mailing_id)s/unsubscribe?%(params)s' % {
                'mailing_id': self.mass_mailing_id.id,
                'params': werkzeug.urls.url_encode({
                    'db': self.env.cr.dbname,
                    'res_id': res_id,
                    'number': number,
                    'token': self.mass_mailing_id._unsubscribe_token(
                        res_id, number),
                }),
            }
        )
        return url

    def _prepare_mass_sms_values(self, records=None):
        result = super(SMSComposer, self)._prepare_mass_sms_values(records=records)
        if self.composition_mode == 'mass' and self.mass_mailing_id:
            records = records if records is not None else self._get_records()

            number_opt_out_list = self._context.get('mass_sms_number_opt_out_list', [])
            number_done_list = self._context.get('mass_sms_number_done_list', [])

            # for record_id, sms_values in result.items():
            for record in records:  # TDE FIXME: to ensure order BUT not sure !!
                sms_values = result[record.id]
                target_number = sms_values['number']
                statistics_vals = {
                    'res_model': self.res_model,
                    'res_id': record.id,
                    'mass_mailing_id': self.mass_mailing_id.id,
                    'sms_number': target_number,
                }

                if target_number in number_opt_out_list:
                    sms_values['state'] = 'canceled'
                elif target_number in number_done_list:
                    sms_values['state'] = 'canceled'
                number_done_list.append(target_number)

                if sms_values['state'] == 'error':
                    statistics_vals['exception'] = fields.Datetime.now()
                elif sms_values['state'] == 'canceled':
                    statistics_vals['ignored'] = fields.Datetime.now()
                else:
                    pass
                    # sms_values['body'] = (sms_values['body'] or '') + self._get_unsubscribe_url(record.id, target_number)

                sms_values.update({
                    'mass_mailing_id': self.mass_mailing_id.id,
                    'statistics_ids': [(0, 0, statistics_vals)],
                })
        return result

    def _action_send_sms_mass(self, records=None):
        sms_all = super(SMSComposer, self)._action_send_sms_mass()
        if self.mass_mailing_id:
            for sms in sms_all:
                body = sms._update_body_short_links()[sms.id]
                sms.body = body
        return sms_all
