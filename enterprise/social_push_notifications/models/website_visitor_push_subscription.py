# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class WebsiteVisitorPushSubscription(models.Model):
    """ Contains the char push_token of a website.visitor's push subscription.
    Push subscriptions are created when a visitor accepts to receive 'Web Push Notifications' on its
    browser.
    This token is used by the firebase service to send notifications to that browser.

    A visitor can have multiple push subscriptions if they use several devices / browsers.
    (push_subscriptions are 'merged' onto the main visitor, see website.visitor#_merge_visitor for
    more information.) """

    _name = 'website.visitor.push.subscription'
    _description = 'Push Subscription for a Website Visitor'
    _log_access = False
    _rec_name = 'website_visitor_id'

    website_visitor_id = fields.Many2one('website.visitor', string="Website Visitor",
        required=True, readonly=True, index=True, ondelete='cascade')
    push_token = fields.Char("Push Subscription", required=True, readonly=True)

    _sql_constraints = [
        ('push_token_uniq', 'unique (push_token)', "Push token can't be duplicated!"),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        """ Ensure the push_token is unique by first deleting existing copies.
        Will also mark related website.visitors as having push notifications enabled."""

        subscriptions = super().create(vals_list)
        subscriptions.website_visitor_id.write({
            'has_push_notifications': True
        })
        return subscriptions

    def unlink(self):
        """ When unlinking, check if it's the last subscription for the related visitor and mark
        them as not having subscriptions if it's the case. """

        website_visitor_ids = self.website_visitor_id
        result = super().unlink()

        remaining_subscriptions = self.search([('website_visitor_id', 'in', website_visitor_ids.ids)])
        (website_visitor_ids - remaining_subscriptions.mapped('website_visitor_id')).write({
            'has_push_notifications': False
        })

        return result
