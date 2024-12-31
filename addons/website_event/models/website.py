# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from lxml import etree, html

from odoo import api, models, _


class Website(models.Model):
    _inherit = "website"

    @api.model
    def new_page(self, name=False, add_menu=False, template='website.default_page', ispage=True, namespace=None, page_values=None, menu_values=None, sections_arch=None, page_title=None):
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

         Finally, we also manually adapt the content of the generated page so that it's suited for
         the website editor generation.
         This includes removing false attributes and making sure the content is contained within a
         single oe_structure element (which cannot be 'wrap' as wrap contains the event menu).

         See: website.menu#save override """

        website_event_menu = False
        if template == 'website.default_page' and name and name.startswith('event/'):
            website_event_menu = self.env["website.event.menu"].sudo().search([
                ('menu_id.url', '=', '/' + name)
            ], limit=1)
            if website_event_menu:
                template = "website_event.layout"

        new_page = super().new_page(name, add_menu, template, ispage, namespace, page_values, menu_values, sections_arch, page_title)

        if website_event_menu and new_page.get('view_id'):
            website_event_menu.view_id = new_page['view_id']
            website_event_menu.view_id.key = f'website_event.{website_event_menu.event_id.name}-{name.split("/")[-1]}'

            arch = website_event_menu.view_id.arch
            if arch:
                tree = html.fromstring(arch)
                content_container = tree.xpath('//div[@id="oe_structure_website_event_layout_1"]')
                if content_container:
                    # remove ID and editor sub-message for custom pages as it doesn't apply
                    wrap = tree.xpath('//div[@id="wrap"]')[0]
                    content_container = content_container[0]
                    content_container.attrib.pop('t-att-data-editor-sub-message', None)
                    content_container.attrib.pop('data-editor-sub-message.translate', None)
                    content_container.attrib.pop('id', None)

                    if sections_arch:
                        for section in wrap.xpath('//section'):
                            # to be properly editable, the content needs to be contained within a
                            # single empty oe_structure, unlike 'wrap' that has the event menu inside
                            wrap.remove(section)
                            content_container.append(section)

                    website_event_menu.view_id.arch = etree.tostring(tree, encoding="unicode")

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
