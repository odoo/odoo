# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _has_unsplash_key_rights(self, mode='write'):
        self.ensure_one()
        # Website has no dependency to web_unsplash, we cannot warranty the order of the execution
        # of the overwrite done in 5ef8300.
        # So to avoid to create a new module bridge, with a lot of code, we prefer to make a check
        # here for website's user.
        assert mode in ('read', 'write')
        website_group_required = (mode == 'write') and 'website.group_website_designer' or 'website.group_website_publisher'
        return self.has_group('base.group_erp_manager') or self.has_group(website_group_required)
