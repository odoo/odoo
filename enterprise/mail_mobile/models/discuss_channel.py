# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def _notify_thread_by_ocn(self, message, recipients_data, msg_vals=False, **kwargs):
        """ Specifically handle channel members. """
        icp_sudo = self.env['ir.config_parameter'].sudo()
        # Avoid to send notification if this feature is disabled or if no user use the mobile app.
        if not icp_sudo.get_param('odoo_ocn.project_id') or not icp_sudo.get_param('mail_mobile.enable_ocn'):
            return

        chat_channels = self.filtered(lambda channel: channel.channel_type == 'chat')
        if chat_channels:
            # modify rdata only for calling super. Do not deep copy as we only
            # add data into list but we do not modify item content
            channel_rdata = recipients_data.copy()
            channel_rdata += [
                {'id': partner.id,
                 'share': partner.partner_share,
                 'active': partner.active,
                 'notif': 'ocn',
                 'type': 'customer',
                 'groups': [],
                }
                for partner in chat_channels.mapped("channel_partner_ids")
            ]
        else:
            channel_rdata = recipients_data

        return super()._notify_thread_by_ocn(message, channel_rdata, msg_vals=msg_vals, **kwargs)

    def _notify_by_ocn_prepare_payload(self, message, receiver_ids, msg_vals=False):
        payload = super()._notify_by_ocn_prepare_payload(message, receiver_ids, msg_vals=msg_vals)
        payload['action'] = 'mail.action_discuss'
        record_name = msg_vals.get('record_name') if msg_vals and 'record_name' in msg_vals else message.record_name
        if self.channel_type == 'chat':
            payload['subject'] = payload['author_name']
            payload['type'] = 'chat'
            payload['android_channel_id'] = 'DirectMessage'
        elif self.channel_type == 'channel':
            payload['subject'] = "#%s - %s" % (record_name, payload['author_name'])
            payload['android_channel_id'] = 'ChannelMessage'
        else:
            payload['subject'] = "#%s" % (record_name)
        # FIXME: mobile apps use old "mail.channel" and cannot be changed on iOS
        payload['model'] = 'mail.channel'
        return payload
