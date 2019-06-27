# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SMSComposer(models.TransientModel):
    _inherit = 'sms.composer'

    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Mass Mailing')
    utm_campaign_id = fields.Many2one('utm.campaign', string='Campaign')

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

                sms_values.update({
                    'mass_mailing_id': self.mass_mailing_id.id,
                    'statistics_ids': [(0, 0, statistics_vals)],
                })
        return result
