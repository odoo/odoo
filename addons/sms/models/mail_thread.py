# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    @api.multi
    def message_post_send_sms(self, body, sms_ids):
        """ Post SMS text message as internal note in the chatter, and link sms_ids
            to the mail.message
            :param body: Note to log in the chatter.
            :param sms_ids: IDs of the sms.sms records
            :return: ID of the mail.message created
        """
        self.ensure_one()
        message_id = self.message_post(body=body, message_type='sms')
        message_id.sms_ids = sms_ids
        return message_id
