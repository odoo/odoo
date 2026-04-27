# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    marketing_activity_id = fields.Many2one('marketing.activity', string='Marketing Activity')

    def _prepare_mail_values_mailing_traces(self, mail_values_all):
        """ Override method to link mail automation activity with mail statistics"""
        trace_values_all = super()._prepare_mail_values_mailing_traces(mail_values_all)

        # skip update if no marketing activity is linked to the mailing
        if not self.marketing_activity_id:
            return trace_values_all
        if self.composition_mode == 'mass_mail' and (self.mass_mailing_name or self.mass_mailing_id) and self.marketing_activity_id:
            # retrieve trace linked to recipient
            traces = self.env['marketing.trace'].search(
                [
                    ('activity_id', '=', self.marketing_activity_id.id),
                    ('res_id', 'in', list(trace_values_all)),
                ],
                # if somehow multiple traces exist, last one is going to override old ones in mapping below
                # so that we keep last trace reference only
                order='id ASC',
            )
            traces_mapping = {trace.res_id: trace.id for trace in traces}

        # update statistics creation done in mass_mailing to include link between stat and trace
        for res_id, trace_values in trace_values_all.items():
            trace_values['marketing_trace_id'] = traces_mapping[res_id]

        return trace_values_all
