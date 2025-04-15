# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.addons.http_routing.models.ir_http import url_for


class Website(models.Model):
    _inherit = 'website'

    forum_count = fields.Integer(readonly=True, default=0)

    @api.model_create_multi
    def create(self, vals_list):
        websites = super().create(vals_list)
        websites._update_forum_count()
        return websites

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
        if search_type in ['forums', 'forum_tags_only', 'all']:
            result.append(self.env['forum.tag']._search_get_detail(self, order, options))
        return result

    def _update_forum_count(self):
        """ Update count of forum linked to some websites. This has to be
        done manually as website_id=False on forum model means a shared forum.
        There is therefore no straightforward relationship to be used between
        forum and website.

        This method either runs on self (if not void), either on all existing
        websites (to update globally counters, notably when a new forum is
        created). """
        websites = self if self else self.search([])
        forums_all = self.env['forum.forum'].search([])
        for website in websites:
            website.forum_count = len(forums_all.filtered_domain(website.website_domain()))
