# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ImLivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    def _get_mail_channel(self, anonymous_name, previous_operator_id=None, user_id=None, country_id=None, extra_info={}):
        """ Override to add the identified website.visitor to the mail_channel.
        this makes the mail_channel enter in 'livechat session' active mode."""
        Visitor = self.env['website.visitor']
        visitor_id = Visitor._decode()
        if visitor_id:
            extra_info.update({
                'livechat_visitor_id': visitor_id,
                'livechat_active': True,
            })
            visitor_sudo = Visitor.browse(visitor_id).sudo()
            anonymous_name = visitor_sudo.name + (' (%s)' % visitor_sudo.country_id.name if visitor_sudo.country_id else '')
        return super(ImLivechatChannel, self)._get_mail_channel(
                anonymous_name, previous_operator_id=previous_operator_id, user_id=user_id,
                country_id=country_id, extra_info=extra_info)
