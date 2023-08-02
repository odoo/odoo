# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.api import depends
from odoo.tools.misc import groupby

class MailMessage(models.Model):
    _inherit = "mail.message"
    # ------------------------------------------------------------
    # ADDITIONS
    # ------------------------------------------------------------

    mailing_trace_ids = fields.One2many('mailing.trace', 'mail_message_id', compute='_compute_mailing_trace_ids')

    @depends('mail_ids')
    def _compute_mailing_trace_ids(self):
        message_trace_mapping = self._get_message_trace_mapping()
        # browse flattened ids to do a single query
        for message in self:
            trace_ids = [trace.id for trace in message_trace_mapping.get(message.id, [])]
            message.mailing_trace_ids = self.env['mailing.trace'].browse(trace_ids)

    def _get_message_trace_mapping(self):
        """Allow overrides to the compute method, adding additional results.

        :return dict[int, list[int]]: Dictionary mapping message ids to trace recordsets ids
        """
        # need sudo to be allowed to read mail.mail
        return dict(groupby(self.sudo().mail_ids.mailing_trace_ids.sudo(False),
                            lambda trace_ids: trace_ids.sudo().mail_mail_id.mail_message_id.id))

    # ------------------------------------------------------------
    # OVERRIDES
    # ------------------------------------------------------------
    def _message_format(self, *args, **kwargs):
        vals_list = super()._message_format(*args, **kwargs)

        messages = self.browse(vals['id'] for vals in vals_list)
        # cache all traces at once
        messages.mailing_trace_ids

        for message, vals in zip(messages, vals_list):
            vals.setdefault('traces', [])
            vals['traces'] += message.mailing_trace_ids._trace_format()
        return vals_list

    def _message_notification_format(self):
        results = super()._message_notification_format()
        for result in results:
            message = self.browse(result['id'])
            result['traces'] = message.mailing_trace_ids._filtered_for_web_client()._trace_format()
        return results
