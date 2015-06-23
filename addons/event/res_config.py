# -*- coding: utf-8 -*-

from openerp.osv import fields, osv

class event_config_settings(osv.TransientModel):
    _name='event.config.settings'
    _inherit='res.config.settings'
    _columns = {
        'module_event_sale': fields.boolean(
            'Sell events tickets',
            help='Install the event_sale module'),
        'module_website_event_track': fields.boolean(
            'Organize few days event with track, full agenda, own menu in website',
            help='Install the module website_event_track'),
        'module_website_event_questions': fields.boolean(
            'Ask questions to online subscribers',
            help='Install the website_event_questions module'),
        'auto_confirmation': fields.boolean(
            'Automate events and subscription confirmation', help='Unselect this option to manually manage draft event and draft subscription'),
        'group_email_scheduling': fields.boolean(
            'Schedule emails to attendees and subscribers', 
            help='You will be able to configure emails, and to schedule them to be automatically sent to the attendees on subscription and/or attendance',
            implied_group='event.group_email_scheduling'),            
    }

    def set_default_auto_confirmation(self, cr, uid, ids, context=None):
        config_value = self.browse(cr, uid, ids, context=context).auto_confirmation
        self.pool.get('ir.values').set_default(cr, uid, 'marketing.config.settings', 'auto_confirmation', config_value)
