# -*- coding: utf-8 -*-

import base64
import simplejson
import werkzeug

import openerp
from openerp.addons.web import http
from openerp.addons.web.controllers.main import content_disposition
from openerp.addons.web.http import request
from openerp.addons.website.models.website import slug

class WebsiteForum(openerp.addons.website_forum.controllers.main.WebsiteForum):

    def _is_allow_chrome_extension(self, forum):
        return forum.allow_chrome_extension

    def _prepare_forum_values(self, forum=None, **kwargs):
        res = super(WebsiteForum, self)._prepare_forum_values(forum=forum, **kwargs)
        res.update({'is_allow_chrome_extension': self._is_allow_chrome_extension(forum)})
        return res

class WebsiteForumChrome(http.Controller):

    @http.route(['''/forum/<model("forum.forum"):forum>/download_plugin'''], type='http', auth="public", website=True)
    def download_plugin(self, forum, **post):
        filename = "forum_link_extension.zip"
        headers = [
                ('Content-Type', 'application/octet-stream; charset=binary'),
                ('Content-Disposition', content_disposition(filename)),
            ]
        extension_stream = forum.generate_extension()
        response = werkzeug.wrappers.Response(extension_stream, headers=headers, direct_passthrough=True)
        return response

    @http.route(['/forum_chrome/<model("forum.forum"):forum>/new'],
                type='json', auth="public", methods=['POST'], website=True)
    def post_create(self, forum, post_parent=None, post_type=None, **post):
        if not request.session.uid:
            return {'no_session': True}
        new_question = request.env['forum.post'].create({
            'forum_id': forum.id,
            'name': post.get('post_name', ''),
            'content': post.get('content', False),
            'content_link': post.get('content_link', False),
            'post_type': post_parent and post_parent.post_type or post_type,  # tde check in selection field
        })
        return {'question_id': new_question.id}
