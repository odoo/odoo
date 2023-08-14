# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.addons.http_routing.models.ir_http import url_for


class Website(models.Model):
    _inherit = "website"

    @api.model
    def page_search_dependencies(self, page_id=False):
        dep = super(Website, self).page_search_dependencies(page_id=page_id)

        page = self.env['website.page'].browse(int(page_id))
        path = page.url

        dom = [
            ('content', 'ilike', path)
        ]
        posts = self.env['blog.post'].search(dom)
        if posts:
            page_key = _('Blog Post')
            if len(posts) > 1:
                page_key = _('Blog Posts')
            dep[page_key] = []
        for p in posts:
            dep[page_key].append({
                'text': _('Blog Post <b>%s</b> seems to have a link to this page !', p.name),
                'item': p.name,
                'link': p.website_url,
            })

        return dep

    @api.model
    def page_search_key_dependencies(self, page_id=False):
        dep = super(Website, self).page_search_key_dependencies(page_id=page_id)

        page = self.env['website.page'].browse(int(page_id))
        key = page.key

        dom = [
            ('content', 'ilike', key)
        ]
        posts = self.env['blog.post'].search(dom)
        if posts:
            page_key = _('Blog Post')
            if len(posts) > 1:
                page_key = _('Blog Posts')
            dep[page_key] = []
        for p in posts:
            dep[page_key].append({
                'text': _('Blog Post <b>%s</b> seems to be calling this file !', p.name),
                'item': p.name,
                'link': p.website_url,
            })

        return dep

    def get_suggested_controllers(self):
        suggested_controllers = super(Website, self).get_suggested_controllers()
        suggested_controllers.append((_('Blog'), url_for('/blog'), 'website_blog'))
        return suggested_controllers
