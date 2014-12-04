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
        'auto_confirmation': fields.boolean(
            'Automate events and subscription confirmation', help='Unselect this option to manually manage draft event and draft subscription'),
    }

    def set_default_auto_confirmation(self, cr, uid, ids, context=None):
        config_value = self.browse(cr, uid, ids, context=context).auto_confirmation
        self.pool.get('ir.values').set_default(cr, uid, 'marketing.config.settings', 'auto_confirmation', config_value)

