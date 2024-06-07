# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _, api
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import url_for

class Website(models.Model):
    _inherit = "website"

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Events'), url_for('/event'), 'website_event'))
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

    @api.model
    def new_page(self, name=False, add_menu=False, template='website.default_page', ispage=True, namespace=None, page_values=None, menu_values=None, sections_arch=None):
        is_event = False
        if template.startswith('website_event.') and template != 'website_event.template_location':
            add_menu = False
            ispage = False
            is_event = True
        event_page = super().new_page(name=name, add_menu=add_menu, template=template, ispage=ispage, namespace=namespace, page_values=page_values, menu_values=menu_values, sections_arch=sections_arch)
        if is_event and request:
            event_page['url'] = f"/event/{request.params.get('event_id')}/page" + event_page['url']
        return event_page
