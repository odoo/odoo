# -*- coding: utf-8 -*-
import werkzeug

from openerp.addons.web import http
from openerp.http import request


class Website_Url(http.Controller):
    @http.route('/website_links/new', type='json', auth='user', methods=['POST'])
    def create_shorten_url(self, **post):
        if 'url' not in post or post['url'] == '':
            return {'error': 'empty_url'}
        return request.env['link.tracker'].create(post).read()

    @http.route('/r', type='http', auth='user', website=True)
    def shorten_url(self, **post):
        return request.website.render("website_links.page_shorten_url", post)

    @http.route('/website_links/add_code', type='json', auth='user')
    def add_code(self, **post):
        link_id = request.env['link.tracker.code'].search([('code', '=', post['init_code'])], limit=1).link_id.id
        new_code = request.env['link.tracker.code'].search_count([('code', '=', post['new_code']), ('link_id', '=', link_id)])
        if new_code > 0:
            return new_code.read()
        else:
            return request.env['link.tracker.code'].create({'code': post['new_code'], 'link_id': link_id})[0].read()

    @http.route('/website_links/recent_links', type='json', auth='user')
    def recent_links(self, **post):
        return request.env['link.tracker'].recent_links(post['filter'], post['limit'])

    @http.route('/r/<string:code>+', type='http', auth="user", website=True)
    def statistics_shorten_url(self, code, **post):
        code = request.env['link.tracker.code'].search([('code', '=', code)], limit=1)

        if code:
            return request.website.render("website_links.graphs", code.link_id.read()[0])
        else:
            return werkzeug.utils.redirect('', 301)
