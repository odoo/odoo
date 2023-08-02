# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.api import depends
from odoo.tools.misc import groupby

class MailMessage(models.Model):
    _inherit = "mail.message"

    @depends('sms_id')
    def _compute_mailing_trace_ids(self):
        super()._compute_mailing_trace_ids()

    def _get_message_trace_mapping(self):
        results = super()._get_message_trace_mapping()
        # need sudo to read sms.sms
        message_to_trace = groupby(self.sudo().sms_id.mailing_trace_ids.sudo(False),
                                   lambda trace: trace.sudo().sms_sms_id.mail_message_id.sudo(False))

        for message_id, traces in message_to_trace:
            results[message_id] = results.get(message_id, []) + traces

        return results
