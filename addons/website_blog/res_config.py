# -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class website_config_settings(osv.osv_memory):
    _inherit = 'website.config.settings'
    _columns = {
        'group_website_mail_reply': fields.boolean('Visitors can reply on blogs',
        		implied_group='website_mail.group_website_mail_reply'),
    }
