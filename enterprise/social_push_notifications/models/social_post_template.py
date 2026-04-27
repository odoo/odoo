# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from binascii import Error as binascii_error

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SocialPostTemplate(models.Model):
    _inherit = 'social.post.template'

    push_notification_message = fields.Text(
        'Push Notifications Message', compute='_compute_message_by_media',
        store=True, readonly=False)

    push_notification_title = fields.Char('Push Notification Title')
    push_notification_target_url = fields.Char('Push Target URL')
    push_notification_image = fields.Binary("Push Icon Image", help="This icon will be displayed in the browser notification")
    # Preview
    has_push_notifications_account = fields.Boolean('Has Push Notifications Account', compute='_compute_has_push_notifications_account')
    display_push_notifications_preview = fields.Boolean('Display Push Notifications Preview', compute='_compute_display_push_notifications_preview')
    push_notifications_preview = fields.Html('Push Notifications Preview', compute='_compute_push_notifications_preview')
    # Visitor
    use_visitor_timezone = fields.Boolean("Send at Visitors' Timezone",
        help="e.g: If you post at 15:00 your time, all visitors will receive the post at 15:00 their time.")
    visitor_domain = fields.Char(string="Visitor Domain", default=[['has_push_notifications', '!=', False]], help="Domain to send push notifications to visitors.")

    @api.constrains('push_notification_message')
    def _check_has_push_notification_message(self):
        for post in self:
            if post.has_push_notifications_account and not post.push_notification_message:
                raise UserError(_("Please specify a Notification Message."))

    @api.depends('account_ids.media_id.media_type')
    def _compute_has_push_notifications_account(self):
        for post in self:
            post.has_push_notifications_account = 'push_notifications' in post.account_ids.media_id.mapped('media_type')

    @api.depends('push_notification_message', 'has_push_notifications_account')
    def _compute_display_push_notifications_preview(self):
        for post in self:
            post.display_push_notifications_preview = post.push_notification_message and post.has_push_notifications_account

    @api.depends('push_notification_message', 'push_notification_title', 'push_notification_image', 'display_push_notifications_preview')
    def _compute_push_notifications_preview(self):
        for post in self:
            if not post.display_push_notifications_preview:
                post.push_notifications_preview = False
                continue
            icon = False
            icon_url = False
            if post.push_notification_image:
                try:
                    base64.b64decode(post.push_notification_image, validate=True)
                    icon = post.push_notification_image
                except binascii_error:
                    if post.id or (post._origin and post._origin.id):
                        icon_url = '/web/image/social.post/%s/push_notification_image' % (post.id if post.id else post._origin.id)
            post.push_notifications_preview = self.env['ir.qweb']._render('social_push_notifications.push_notifications_preview', {
                'title': post.push_notification_title or _('New Message'),
                'icon': icon,
                'icon_url': icon_url,
                'message': post.push_notification_message,
                'host_name': post.get_base_url() or 'https://myapp.com'
            })

    @api.model_create_multi
    def create(self, vals_list):
        """ Assign a default push_notification_target_url is none specified and we can extract one from the message """
        for index, values in enumerate(vals_list):
            if not values.get('push_notification_target_url') and values.get('message'):
                message = self._prepare_post_content(
                    values['message'],
                    'push_notifications',
                    **{field: values[field] for field in set(self._get_post_message_modifying_fields()) & values.keys()})
                extracted_url = self._extract_url_from_message(message)
                if extracted_url:
                    vals_list[index]['push_notification_target_url'] = extracted_url
        return super(SocialPostTemplate, self).create(vals_list)

    def write(self, vals):
        """ Assign a default push_notification_target_url is none specified and we can extract one from the message """
        if not any(post.push_notification_target_url for post in self) and vals.get('message'):
            message = self._prepare_post_content(
                    vals['message'],
                    'push_notifications',
                    **{field: vals[field] for field in set(self._get_post_message_modifying_fields()) & vals.keys()})
            extracted_url = self._extract_url_from_message(message)
            if extracted_url:
                vals['push_notification_target_url'] = extracted_url
        return super(SocialPostTemplate, self).write(vals)

    def _prepare_social_post_values(self):
        """Return the values to generate a social post from the social post template."""
        values = super(SocialPostTemplate, self)._prepare_social_post_values()
        values.update({
            'push_notification_title': self.push_notification_title,
            'push_notification_image': self.push_notification_image,
            'push_notification_target_url': self.push_notification_target_url,
            'use_visitor_timezone': self.use_visitor_timezone,
            'visitor_domain': self.visitor_domain,
        })
        return values

    @api.model
    def _message_fields(self):
        """Return the message field per media."""
        return {**super()._message_fields(), 'push_notifications': 'push_notification_message'}
