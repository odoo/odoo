# -*- coding: utf-8 -*-

from openerp.osv import fields, osv

class event_config_settings(osv.TransientModel):
    _name='marketing.config.settings'
    _inherit='marketing.config.settings'
    _columns = {
        'module_event_sale': fields.boolean(
            'Sale different type of ticket',
            help='Install the event_sale module'),
        'module_website_event_track': fields.boolean(
            'Organize few days event with track,full agenda,own menu in website'),
    }

