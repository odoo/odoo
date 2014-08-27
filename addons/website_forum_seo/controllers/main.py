import openerp
from openerp import tools
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website_forum.controllers.main import WebsiteForum as controllers

class WebsiteForumSEO(controllers):
    
    # Questions
    # --------------------------------------------------
    @http.route('/forum/<model("forum.forum"):forum>/question/new', type='http', auth="user", methods=['POST'], website=True)
    def question_create(self, forum, **post):
        post.update({'content' : request.env['forum.seo'].update_seo_word(post.get('content'))})
        return super(WebsiteForumSEO, self).question_create(forum=forum, **post)
    
    # Post
    # --------------------------------------------------
    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/new', type='http', auth="public", methods=['POST'], website=True)
    def post_new(self, forum, post, **kwargs):
        kwargs.update({'content' : request.env['forum.seo'].update_seo_word(kwargs.get('content'))})
        return super(WebsiteForumSEO, self).post_new(forum=forum, post=post, **kwargs)
    
    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/save', type='http', auth="user", methods=['POST'], website=True)
    def post_save(self, forum, post, **kwargs):
        kwargs.update({'content' : request.env['forum.seo'].update_seo_word(kwargs.get('content'))})
        return super(WebsiteForumSEO, self).post_save(forum=forum, post=post, **kwargs)
