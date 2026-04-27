# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    push_subscription_ids = fields.One2many('website.visitor.push.subscription', 'website_visitor_id',
        string="Push Subscriptions")
    has_push_notifications = fields.Boolean('Push Notifications Enabled')

    def init(self):
        self._cr.execute("""
            CREATE INDEX IF NOT EXISTS website_visitor_has_push_notifications_index
                                    ON website_visitor (id)
                                 WHERE has_push_notifications = TRUE;
        """)

    def action_send_push_notification(self):
        """ Opens social media post form prefilled with selected website.visitor
         and push notification activated."""
        # validate if push notification are allowed for all selected visitors
        if all(visitor.has_push_notifications for visitor in self):
            push_media = self.env['social.media'].search([('media_type', '=', 'push_notifications')])
            action = self.env["ir.actions.actions"]._for_xml_id("social.action_social_post")
            action['views'] = [[False, 'form']]
            action['context'] = {
                'default_visitor_domain': "[('has_push_notifications', '!=', False), ('id', 'in', %s)]" % self.ids,
                'default_account_ids': push_media.account_ids.ids,
            }
            return action
        else:
            raise UserError(_("Some selected visitors do not allow push notifications."))

    def _inactive_visitors_domain(self):
        """ Visitors registered to push subscriptions are considered always active and should not be
        deleted. """
        domain = super()._inactive_visitors_domain()
        return expression.AND([domain, [('has_push_notifications', '=', False)]])

    def _merge_visitor(self, target):
        """ Override linking process to link existing push subscriptions to the final visitor. """
        self.push_subscription_ids.write({'website_visitor_id': target.id})
        self.write({'has_push_notifications': False})
        return super()._merge_visitor(target)

    def _register_push_subscription(self, push_token):
        self.ensure_one()

        # in case we already have this token, delete and re-create
        if push_token:
            self.env['website.visitor.push.subscription'].search(
                [('push_token', '=', push_token)]).unlink()

            return self.env['website.visitor.push.subscription'].create({
                'website_visitor_id': self.id,
                'push_token': push_token
            })
