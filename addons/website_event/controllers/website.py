# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.addons.website.controllers import main
from odoo.http import request


class Website(main.Website):

    @http.route()
    def pagenew(self, path="", add_menu=False, template=False, redirect=False, **kwargs):
        """ Override the page creation in the context of events.
         When creating a page for an event, the page needs to be embedded inside the
         'website_event.layout' template, otherwise it is not visually contained within that event.

         Note that to create an event page, one has to first create a menu entry in that event.

         To determine if this page is an event page:
         - Check that the path starts with 'event/', this should avoid extra requests in other contexts
         - Fetch a website.menu linked to this path
         - Check if we have a website.event.menu linked to that website.menu.

         See: website.menu#save override """

        if not template and path and path.startswith('event/'):
            website_menu = request.env["website.menu"].sudo().search([('url', '=', '/' + path)], limit=1)
            has_event_menu = request.env["website.event.menu"].search_count([
                ('menu_id', '=', website_menu.id)
            ], limit=1)
            if has_event_menu:
                template = "website_event.layout"

        return super().pagenew(path, add_menu, template, redirect, **kwargs)
