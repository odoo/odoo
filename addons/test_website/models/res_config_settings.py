# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import website, web_unsplash


class ResConfigSettings(web_unsplash.ResConfigSettings, website.ResConfigSettings):

    def action_website_test_setting(self):
        return self.env['website'].get_client_action('/')
