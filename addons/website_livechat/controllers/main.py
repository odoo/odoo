# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _, fields
from odoo.http import request
from odoo.addons.im_livechat.controllers.main import LivechatController
from datetime import datetime, timedelta


class WebsiteLivechat(LivechatController):

    def _get_guest_name(self):
        visitor_sudo = request.env["website.visitor"]._get_visitor_from_request()
        return _('Visitor #%d', visitor_sudo.id) if visitor_sudo else super()._get_guest_name()

    @http.route()
    def get_session(self, channel_id, anonymous_name, previous_operator_id=None, chatbot_script_id=None, persisted=True):
        """ Override to use visitor name instead of 'Visitor' whenever a visitor start a livechat session. """
        visitor_sudo = request.env['website.visitor']._get_visitor_from_request()
        if visitor_sudo:
            anonymous_name = _('Visitor #%s', visitor_sudo.id)
        return super().get_session(channel_id, anonymous_name, previous_operator_id=previous_operator_id, chatbot_script_id=chatbot_script_id, persisted=persisted)

    def _prepare_visitor_data(self, store, channel, visitor_id):
        domain = [
            ("channel_type", "=", "livechat"),
            ("livechat_visitor_id", "=", visitor_id),
            ("create_date", ">=", fields.Datetime.to_string(datetime.now() - timedelta(days=7))),
        ]
        channels = request.env["discuss.channel"].search(domain)
        store.add(channels)
        return super()._prepare_visitor_data(store, channel, visitor_id)
