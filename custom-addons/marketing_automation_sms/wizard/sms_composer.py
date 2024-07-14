# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SMSComposer(models.TransientModel):
    _inherit = 'sms.composer'

    marketing_activity_id = fields.Many2one('marketing.activity', string='Marketing Activity')

    def _prepare_mass_sms_values(self, records):
        result = super(SMSComposer, self)._prepare_mass_sms_values(records)
        if self.composition_mode == 'mass' and self.mailing_id and self.marketing_activity_id:
            # retrieve traces linked to recipients
            traces = self.env['marketing.trace'].search([('activity_id', '=', self.marketing_activity_id.id), ('res_id', 'in', records.ids)])
            res_id_to_trace_id = dict((trace.res_id, trace.id) for trace in traces)

            # update generated traces
            for record in records:
                sms_values = result[record.id]
                trace_commands = sms_values['mailing_trace_ids']
                if not trace_commands or len(trace_commands) != 1 or len(trace_commands[0]) != 3:
                    continue
                trace_values = trace_commands[0][2]
                trace_values['marketing_trace_id'] = res_id_to_trace_id.get(record.id, False)
        return result
