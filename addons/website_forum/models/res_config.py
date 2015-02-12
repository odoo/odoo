# -*- coding: utf-8 -*-

from openerp import api, fields, models

class forum_config_settings(models.TransientModel):
    _inherit = 'website.config.settings'

    module_website_forum_chrome = fields.Boolean( 'Chrome extension for forum',
        help='Install the website_forum_chrome module')
