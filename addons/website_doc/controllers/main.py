# -*- coding: utf-8 -*-

from datetime import datetime
import werkzeug.urls
import simplejson

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.controllers.main import login_redirect
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import Website as controllers
from openerp.addons.website.models.website import slug
from openerp.addons.website_forum.controllers.main import WebsiteForum

controllers = controllers()

class WebsiteDoc(http.Controller):

    @http.route(['/doc', '/doc/<model("documentation.toc"):toc>'], type='http', auth="public", website=True, multilang=True)
    def documentation(self, toc='', **kwargs):
        cr, uid, context, toc_id = request.cr, request.uid, request.context, False
        TOC = request.registry['documentation.toc']
        obj_ids = TOC.search(cr, uid, [('parent_id', '=', False)], context=context)
        toc_ids = TOC.browse(cr, uid, obj_ids, context=context)
        value = {
            'documentaion_toc': toc_ids,
            'topic': toc or toc_ids[0],
        }
        return request.website.render("website_doc.documentation", value)

    @http.route('/doc/new', type='http', auth="user", multilang=True, website=True)
    def create_table_of_content(self, toc_name="New Table Of Content", **kwargs):
        toc_id = request.registry['documentation.toc'].create(request.cr, request.uid, {
            'name': toc_name,
        }, context=request.context)
        return request.redirect("/doc/%s" % toc_id)

    #---------------------
    # Forum Posts
    # --------------------

class WebsiteForum(WebsiteForum):

    def prepare_question_values(self, forum, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        TOC = request.registry['documentation.toc']
        obj_ids = TOC.search(cr, uid, [('child_ids', '=', False)], context=context)
        toc = TOC.browse(cr, uid, obj_ids, context=context)
        values = super(WebsiteForum, self).prepare_question_values(forum=forum, kwargs=kwargs)
        values.update({'documentaion_toc': toc})
        return values

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):post>/toc', type='http', auth="user", multilang=True, website=True)
    def post_toc(self, forum, post, **kwargs):
        toc_id = int(kwargs.get('content')) if kwargs.get('content') else False
        request.registry['forum.post'].write(request.cr, request.uid, [post.id], {'toc_id': toc_id}, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(post)))