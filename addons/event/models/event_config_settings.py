# -*- coding: utf-8 -*-

from openerp.osv import fields, osv

class event_config_settings(osv.TransientModel):
    _name='event.config.settings'
    _inherit='res.config.settings'
    _columns = {
        'module_event_sale': fields.selection([
            (0, "All events are free"),
            (1, 'Allow selling tickets')
            ], "Tickets",
            help='Install the event_sale module'),
        'module_website_event_track': fields.selection([
            (0, "No mini website per event"),
            (1, 'Allow tracks, agenda and dedicated menus/website per event')
            ], "Tracks and Agenda",
            help='Install the module website_event_track'),
        'module_website_event_questions': fields.selection([
            (0, "No extra questions on subscriptions"),
            (1, 'Allow adding extra questions on subscriptions')
            ], "Subscription Survey",
            help='Install the website_event_questions module'),
        'auto_confirmation': fields.selection([
            (1, 'No validation step on subscription'),
            (0, "Manually confirm every subscription")
            ], "Auto Confirmation",
            help='Unselect this option to manually manage draft event and draft subscription'),
        'group_email_scheduling': fields.selection([
            (0, "No automated emails"),
            (1, 'Schedule emails to attendees and subscribers')
            ], "Email Scheduling",
            help='You will be able to configure emails, and to schedule them to be automatically sent to the attendees on subscription and/or attendance',
            implied_group='event.group_email_scheduling'),            
    }

    def set_default_auto_confirmation(self, cr, uid, ids, context=None):
        config_value = self.browse(cr, uid, ids, context=context).auto_confirmation
        self.pool.get('ir.values').set_default(cr, uid, 'event.config.settings', 'auto_confirmation', config_value)
