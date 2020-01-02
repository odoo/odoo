# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, SUPERUSER_ID


class ImLivechatChannel(models.Model):
    _inherit = 'im_livechat.channel'

    def get_livechat_info(self):
        res = super(ImLivechatChannel, self).get_livechat_info()
        res['options']['generate_lead'] = self.with_user(SUPERUSER_ID).env['res.users'].has_group('crm_livechat.group_generate_lead')
        return res
