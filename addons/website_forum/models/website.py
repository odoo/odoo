# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.addons.http_routing.models.ir_http import url_for


class Website(models.Model):
    _inherit = 'website'

    @api.model
    def get_default_forum_count(self):
        self.forums_count = self.env['forum.forum'].search_count(self.website_domain())

    forums_count = fields.Integer(readonly=True, default=get_default_forum_count)

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Forum'), url_for('/forum'), 'website_forum'))
        return suggested_controllers

    def configurator_get_footer_links(self):
        links = super().configurator_get_footer_links()
        links.append({'text': _("Forum"), 'href': '/forum'})
        return links

    def configurator_set_menu_links(self, menu_company, module_data):
        # Forum menu should only be a footer link, not a menu
        forum_menu = self.env['website.menu'].search([('url', '=', '/forum'), ('website_id', '=', self.id)])
        forum_menu.unlink()
        super().configurator_set_menu_links(menu_company, module_data)

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if search_type in ['forums', 'forums_only', 'all']:
            result.append(self.env['forum.forum']._search_get_detail(self, order, options))
        if search_type in ['forums', 'forum_posts_only', 'all']:
            result.append(self.env['forum.post']._search_get_detail(self, order, options))
        return result
