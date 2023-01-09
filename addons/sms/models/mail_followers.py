# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Followers(models.Model):
    _inherit = ['mail.followers']

    def _get_recipient_data(self, records, message_type, subtype_id, pids=None):
        if message_type != 'sms' or not (pids or records):
            return super(Followers, self)._get_recipient_data(records, message_type, subtype_id, pids=pids)

        if pids is None and records:
            records_pids = dict(
                (record.id, record._sms_get_default_partners().ids)
                for record in records
            )
        elif pids and records:
            records_pids = dict((record.id, pids) for record in records)
        else:
            records_pids = {0: pids if pids else []}
        recipients_data = super(Followers, self)._get_recipient_data(records, message_type, subtype_id, pids=pids)
        for rid, rdata in recipients_data.items():
            sms_pids = records_pids.get(rid) or []
            for pid, pdata in rdata.items():
                if pid in sms_pids:
                    pdata['notif'] = 'sms'
        return recipients_data
