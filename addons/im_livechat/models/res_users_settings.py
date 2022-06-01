# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResUsersSettings(models.Model):
    _inherit = 'res.users.settings'

    is_discuss_sidebar_category_livechat_open = fields.Boolean("Is category livechat open", default=True)

    def _get_rename_table(self):
        res = super()._get_rename_table()
        res.update({'is_discuss_sidebar_category_livechat_open': 'isDiscussSidebarCategoryLivechatOpen'})
        return res

    def _res_users_settings_format(self):
        res = super()._res_users_settings_format()
        res.update({'isDiscussSidebarCategoryLivechatOpen': self.is_discuss_sidebar_category_livechat_open})
        return res
