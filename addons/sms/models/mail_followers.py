# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Followers(models.Model):
    _inherit = ['mail.followers']

    def _get_recipient_data(self, records, message_type, subtype_id, pids=None):
        recipients_data = super()._get_recipient_data(records, message_type, subtype_id, pids=pids)
        if message_type != 'sms' or not (pids or records):
            return recipients_data

        if pids is None and records:
            records_pids = dict(
                (rec_id, partners.ids)
                for rec_id, partners in records._mail_get_partners().items()
            )
        elif pids and records:
            records_pids = dict((record.id, pids) for record in records)
        else:
            records_pids = {0: pids if pids else []}
        for rid, rdata in recipients_data.items():
            sms_pids = records_pids.get(rid) or []
            for pid, pdata in rdata.items():
                if pid in sms_pids:
                    pdata['notif'] = 'sms'
        return recipients_data
