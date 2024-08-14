# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class WebsiteUrl(http.Controller):
    @http.route('/website_links/new', type='json', auth='user', methods=['POST'])
    def create_shorten_url(self, **post):
        if 'url' not in post or post['url'] == '':
            return {'error': 'empty_url'}
        return request.env['link.tracker'].search_or_create(post).read()

    @http.route('/r', type='http', auth='user', website=True)
    def shorten_url(self, **post):
        return request.render("website_links.page_shorten_url", post)

    def _search_link_tracker_code(self, domain):
        return request.env['link.tracker.code'].search(domain, limit=1)

    @http.route('/website_links/add_code', type='json', auth='user')
    def add_code(self, **post):
        link_id = self._search_link_tracker_code([('code', '=', post['init_code'])]).link_id.id
        new_code = self._search_link_tracker_code([('code', '=', post['new_code']), ('link_id', '=', link_id)])
        if new_code:
            return new_code.read()
        else:
            return request.env['link.tracker.code'].create({'code': post['new_code'], 'link_id': link_id})[0].read()

    @http.route('/website_links/recent_links', type='json', auth='user')
    def recent_links(self, **post):
        return request.env['link.tracker'].recent_links(post['filter'], post['limit'])

    @http.route('/r/<string:code>+', type='http', auth="user", website=True)
    def statistics_shorten_url(self, code, **post):
        code = self._search_link_tracker_code([('code', '=', code)])

        if code:
            return request.render("website_links.graphs", code.link_id.read()[0])
        else:
            return request.redirect('/', code=301)
