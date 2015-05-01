# -*- coding: utf-8 -*-

from openerp import http
from openerp.http import request


class WebsiteDoc(http.Controller):
    @http.route(['/forum/how-to', '/forum/how-to/<model("forum.documentation.toc"):toc>'], type='http', auth="public", website=True)
    def toc(self, toc=None, **kwargs):
        if toc:
            sections = toc.child_ids
            forum = toc.forum_id
        else:
            sections = request.env['forum.documentation.toc'].search([('parent_id', '=', False)])
            forum = sections and sections[0].forum_id or False
        value = {
            'toc': toc,
            'main_object': toc or forum,
            'forum': forum,
            'sections': sections,
        }
        return request.website.render("website_forum_doc.documentation", value)

    @http.route(['''/forum/how-to/<model("forum.documentation.toc"):toc>/<model("forum.post", "[('documentation_toc_id','=',toc[0])]"):post>'''], type='http', auth="public", website=True)
    def post(self, toc, post, **kwargs):
        # TODO: implement a redirect instead of crash
        assert post.documentation_toc_id.id == toc.id, "Wrong post!"
        value = {
            'toc': toc,
            'post': post,
            'main_object': post,
            'forum': post.forum_id
        }
        return request.website.render("website_forum_doc.documentation_post", value)

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):post>/promote', type='http', auth="user", website=True)
    def post_toc(self, forum, post, **kwargs):
        assert request.env.user.karma >= 200, 'You need 200 karma to promote a post to the documentation'
        tocs = request.env['forum.documentation.toc'].search([]).filtered(lambda toc: not toc.child_ids)
        value = {
            'post': post,
            'forum': post.forum_id,
            'chapters': tocs
        }
        return request.website.render("website_forum_doc.promote_question", value)

    @http.route('/forum/<model("forum.forum"):forum>/promote_ok', type='http', auth="user", website=True)
    def post_toc_ok(self, forum, post_id, toc_id, **kwargs):
        assert request.env.user.karma >= 200, 'Not enough karma, you need 200 to promote a documentation.'
        request.env['forum.post'].browse(int(post_id)).write({
            'documentation_toc_id': toc_id and int(toc_id) or False,
            'documentation_stage_id': request.env['forum.documentation.toc'].search([], limit=1).id
        })
        return request.redirect('/forum/'+str(forum.id)+'/question/'+str(post_id))
