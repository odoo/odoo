# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, Command, fields, models, tools


class SmsComposer(models.TransientModel):
    _inherit = 'sms.composer'

    # mass mode with mass sms
    mass_sms_allow_unsubscribe = fields.Boolean('Include opt-out link', default=True)
    mailing_id = fields.Many2one('mailing.mailing', string='Mailing')
    utm_campaign_id = fields.Many2one('utm.campaign', string='Campaign', ondelete='set null')

    # ------------------------------------------------------------
    # Mass mode specific
    # ------------------------------------------------------------

    def _get_unsubscribe_url(self, mailing_id, trace_code):
        return tools.urls.urljoin(
            self.get_base_url(),
            '/sms/%s/%s' % (mailing_id, trace_code)
        )

    @api.model
    def _get_unsubscribe_info(self, url):
        return _('STOP SMS: %(unsubscribe_url)s', unsubscribe_url=url)

    def _prepare_mass_sms_trace_values(self, record, sms_values):
        trace_code = self.env['mailing.trace']._get_random_code()
        trace_values = {
            'mass_mailing_id': self.mailing_id.id,
            'model': self.res_model,
            'res_id': record.id,
            'sms_code': trace_code,
            'sms_number': sms_values['number'],
            'sms_tracker_ids': [Command.create({'sms_uuid': sms_values['uuid']})],
            'trace_type': 'sms',
        }
        if sms_values['state'] == 'error':
            trace_values['failure_type'] = sms_values['failure_type']
            trace_values['trace_status'] = 'error'
        elif sms_values['state'] == 'canceled':
            trace_values['failure_type'] = sms_values['failure_type']
            trace_values['trace_status'] = 'cancel'
        else:
            if self.mass_sms_allow_unsubscribe:
                stop_sms = self._get_unsubscribe_info(self._get_unsubscribe_url(self.mailing_id.id, trace_code))
                sms_values['body'] = '%s\n%s' % (sms_values['body'] or '', stop_sms)
        return trace_values

    def _get_optout_record_ids(self, records, recipients_info):
        """ Fetch opt-out records based on mailing. """
        res = super()._get_optout_record_ids(records, recipients_info)
        if self.mailing_id:
            optout_res_ids = self.mailing_id._get_opt_out_list_sms()
            res += optout_res_ids
        return res

    def _get_done_record_ids(self, records, recipients_info):
        """ A/B testing could lead to records having been already mailed. """
        res = super()._get_done_record_ids(records, recipients_info)
        if self.mailing_id:
            seen_ids, seen_list = self.mailing_id._get_seen_list_sms()
            res += seen_ids
        return res

    def _prepare_body_values(self, records):
        all_bodies = super()._prepare_body_values(records)
        if self.mailing_id:
            tracker_values = self.mailing_id._get_link_tracker_values()
            for sms_id, body in all_bodies.items():
                body = self.env['mail.render.mixin'].sudo()._shorten_links_text(body, tracker_values)
                all_bodies[sms_id] = body
        return all_bodies

    def _prepare_mass_sms_values(self, records):
        # In mass mailing only, add 'mailing.trace' values directly in the o2m field
        result = super()._prepare_mass_sms_values(records)
        if not self._is_mass_sms():
            return result

        for record in records:
            sms_values = result[record.id]

            trace_values = self._prepare_mass_sms_trace_values(record, sms_values)
            sms_values.update({
                'mailing_id': self.mailing_id.id,
                'mailing_trace_ids': [(0, 0, trace_values)],
            })
        return result

    def _prepare_mass_sms(self, records, sms_record_values):
        sms_all = super()._prepare_mass_sms(records, sms_record_values)
        if self.mailing_id:
            updated_bodies = sms_all._update_body_short_links()
            for sms in sms_all:
                sms.body = updated_bodies[sms.id]
        return sms_all

    def _is_mass_sms(self):
        return self.composition_mode == 'mass' and self.mailing_id

    def _filter_out_and_handle_revoked_sms_values(self, sms_values_all):
        # Filter out canceled sms of mass mailing and create traces for canceled ones.
        results = super()._filter_out_and_handle_revoked_sms_values(sms_values_all)
        if not self._is_mass_sms():
            return results
        self.env['mailing.trace'].sudo().create([
            trace_commands[0][2]
            for mail_values in results.values()
            if mail_values.get('state') == 'canceled' and mail_values['mailing_trace_ids']
            for trace_commands in (mail_values['mailing_trace_ids'],)
            # Ensure it is a create command
            if len(trace_commands) == 1 and len(trace_commands[0]) == 3 and trace_commands[0][0] == 0
        ])
        return {
            res_id: sms_values
            for res_id, sms_values in results.items()
            if sms_values.get('state') != 'canceled'
        }
