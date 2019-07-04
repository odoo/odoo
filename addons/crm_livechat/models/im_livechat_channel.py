# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ImLivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    def get_livechat_info(self, username='Visitor'):
        res = super(ImLivechatChannel, self).get_livechat_info(username='Visitor')
        if not res.get('available'):
            res['available'] = True
            res['options'] = self._get_channel_infos()
            res['options']['default_username'] = username
        return res
