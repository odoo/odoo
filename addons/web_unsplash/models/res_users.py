# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _can_manage_unsplash_settings(self):
        self.ensure_one()
        # Website has no dependency to web_unsplash, we cannot warranty the order of the execution
        # of the overwrite done in 5ef8300.
        # So to avoid to create a new module bridge, with a lot of code, we prefer to make a check
        # here for website's user.
        return self.has_group('base.group_erp_manager') or self.has_group('website.group_website_restricted_editor')
