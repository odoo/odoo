# -*- coding: utf-8 -*-


from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models.website import slug


# from openerp.addons.website.controllers.main import Website as controllers
# import werkzeug.urls
# from datetime import datetime
# import simplejson
# from openerp import tools
# from openerp import SUPERUSER_ID
# from openerp.addons.web.controllers.main import login_redirect
# from openerp.addons.website_forum.controllers.main import WebsiteForum
# 
# controllers = controllers()

class WebsiteDoc(http.Controller):
    @http.route(['/forum/how-to', '/forum/how-to/<model("documentation.toc"):toc>'], type='http', auth="public", website=True, multilang=True)
    def toc(self, toc=None, **kwargs):
        cr, uid, context, toc_id = request.cr, request.uid, request.context, False
        if toc:
            toc = [toc]
        else:
            toc_obj = request.registry['forum.documentation.toc']
            obj_ids = toc_obj.search(cr, uid, [('parent_id', '=', False)], context=context)
            toc = toc_obj.browse(cr, uid, obj_ids, context=context)
        value = {
            'sections': toc,
        }
        return request.website.render("website_forum_doc.documentation", value)

    @http.route(['/forum/how-to/<model("documentation.toc"):toc>/<model("forum.post"):post>'], type='http', auth="public", website=True, multilang=True)
    def how_to(self, toc, post, **kwargs):
        assert post.documentation_toc_id.id == toc.id, "Wrong post, should implement a redirect here"
        value = {
            'section': toc,
            'post': post
        }
        return request.website.render("website_forum_doc.documentation.post", value)


#---------------------
# Forum Posts
# --------------------
# 
# class WebsiteForum(WebsiteForum):
# 
#     def prepare_question_values(self, forum, **kwargs):
#         cr, uid, context = request.cr, request.uid, request.context
#         TOC = request.registry['documentation.toc']
#         obj_ids = TOC.search(cr, uid, [('child_ids', '=', False)], context=context)
#         toc = TOC.browse(cr, uid, obj_ids, context=context)
#         values = super(WebsiteForum, self).prepare_question_values(forum=forum, kwargs=kwargs)
#         values.update({'documentaion_toc': toc})
#         return values
# 
#     @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):post>/toc', type='http', auth="user", multilang=True, website=True)
#     def post_toc(self, forum, post, **kwargs):
#         toc_id = int(kwargs.get('content')) if kwargs.get('content') else False
#         request.registry['forum.post'].write(request.cr, request.uid, [post.id], {'toc_id': toc_id}, context=request.context)
#         return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(post)))
