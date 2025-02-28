# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class Website(models.Model):
    _inherit = "website"

    @api.model
    def new_page(self, name=False, add_menu=False, template='website.default_page', ispage=True, namespace=None, page_values=None, menu_values=None, sections_arch=None):
        """ Override the page creation in the context of events.

         When creating a page for an event, the page needs to be embedded inside the
         'website_event.layout' template, otherwise it is not visually contained within that event.
         Note that to create an event page, one has to first create a menu entry in that event.

         To determine if this page is an event page:
         - Check that the path starts with 'event/', this should avoid extra requests in other contexts
         - Fetch a website.menu linked to this path
         - Check if we have a website.event.menu linked to that website.menu.

         In addition, we attach the created view to the website.event.menu and adapt they view key
         to make it unique in the context of our event, which makes it possible to find the view in
         the event pages controller.

         See: website.menu#save override """

        website_event_menu = False
        if template == 'website.default_page' and name and name.startswith('event/'):
            website_menu = self.env["website.menu"].sudo().search([('url', '=', '/' + name)], limit=1)
            website_event_menu = self.env["website.event.menu"].sudo().search([
                ('menu_id', '=', website_menu.id)
            ], limit=1)
            if website_event_menu:
                template = "website_event.layout"

        new_page = super().new_page(name, add_menu, template, ispage, namespace, page_values, menu_values, sections_arch)

        if website_event_menu and new_page.get('view_id'):
            website_event_menu.view_id = new_page['view_id']
            website_event_menu.view_id.key = f'website_event.{website_event_menu.event_id.name}-{name.split("/")[-1]}'

        return new_page

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Events'), self.env['ir.http']._url_for('/event'), 'website_event'))
        return suggested_controllers

    def get_cta_data(self, website_purpose, website_type):
        cta_data = super(Website, self).get_cta_data(website_purpose, website_type)
        if website_purpose == 'sell_more' and website_type == 'event':
            cta_btn_text = _('Next Events')
            return {'cta_btn_text': cta_btn_text, 'cta_btn_href': '/event'}
        return cta_data

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if search_type in ['events', 'all']:
            result.append(self.env['event.event']._search_get_detail(self, order, options))
        return result
