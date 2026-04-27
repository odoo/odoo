# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import AccessError


class EventSocial(models.Model):
    _inherit = "event.event"

    firebase_enable_push_notifications = fields.Boolean('Enable Web Push Notifications',
        compute='_compute_firebase_enable_push_notifications')

    def _compute_firebase_enable_push_notifications(self):
        current_website = self.env['website'].get_current_website()
        for event in self:
            website = event.website_id or current_website
            event.firebase_enable_push_notifications = website.firebase_enable_push_notifications

    def action_send_push(self):
        self.ensure_one()

        if not self.env.user.has_group('social.group_social_user'):
            raise AccessError(_('You do not have access to this action.'))

        action = self.env['ir.actions.act_window']._for_xml_id('social.action_social_post')
        action['views'] = [[False, 'form']]
        current_website = self.env['website'].get_current_website()
        social_account = self.env['social.account'].search([(
            'website_id', '=', (self.website_id or current_website).id
        )])
        action['context'] = dict(self.env.context, **{
            'default_account_ids': [social_account.id] if social_account else False,
            'default_use_visitor_timezone': False,
            'default_visitor_domain': str([
                '&',
                ['has_push_notifications', '=', True],
                ['event_registered_ids', 'in', self.ids],
            ])
        })
        return action

    def action_send_push_reminders(self):
        # TODO awa: remove me in master and keep implementation in website_event_track_social module
        if not self.env.user.has_group('social.group_social_user'):
            raise AccessError(_('You do not have access to this action.'))
