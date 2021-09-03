# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import lxml
import requests
import logging
import werkzeug.exceptions
import werkzeug.urls
import werkzeug.wrappers

from datetime import datetime

from odoo import http, tools, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.website_profile.controllers.main import WebsiteProfile
from odoo.addons.portal.controllers.portal import _build_url_w_params

from odoo.http import request

_logger = logging.getLogger(__name__)


class WebsiteForum(WebsiteProfile):
    _post_per_page = 10
    _user_per_page = 30

    def _prepare_user_values(self, **kwargs):
        values = super(WebsiteForum, self)._prepare_user_values(**kwargs)
        values['forum_welcome_message'] = request.httprequest.cookies.get('forum_welcome_message', False)
        values.update({
            'header': kwargs.get('header', dict()),
            'searches': kwargs.get('searches', dict()),
        })
        if kwargs.get('forum'):
            values['forum'] = kwargs.get('forum')
        elif kwargs.get('forum_id'):
            values['forum'] = request.env['forum.forum'].browse(kwargs.pop('forum_id'))
        return values

    # Forum
    # --------------------------------------------------

    @http.route(['/forum'], type='http', auth="public", website=True, sitemap=True)
    def forum(self, **kwargs):
        domain = request.website.website_domain()
        forums = request.env['forum.forum'].search(domain)
        if len(forums) == 1:
            return request.redirect('/forum/%s' % slug(forums[0]), code=302)

        return request.render("website_forum.forum_all", {
            'forums': forums
        })

    @http.route('/forum/new', type='json', auth="user", methods=['POST'], website=True)
    def forum_create(self, forum_name="New Forum", forum_mode="questions", forum_privacy="public", forum_privacy_group=False, add_menu=False):
        forum = {
            'name': forum_name,
            'mode': forum_mode,
            'privacy': forum_privacy,
            'website_id': request.website.id,
        }
        if forum_privacy == 'private' and forum_privacy_group:
            forum['authorized_group_id'] = forum_privacy_group
        forum_id = request.env['forum.forum'].create(forum)
        if add_menu:
            group = [int(forum_privacy_group)] if forum_privacy == 'private' else [request.env.ref('base.group_portal').id, request.env.ref('base.group_user').id]
            menu_id = request.env['website.menu'].create({
                'name': forum_name,
                'url': "/forum/%s" % slug(forum_id),
                'parent_id': request.website.menu_id.id,
                'website_id': request.website.id,
                'group_ids': [(6, 0, group)]
            })
            forum_id.menu_id = menu_id
        return "/forum/%s" % slug(forum_id)

    def sitemap_forum(env, rule, qs):
        Forum = env['forum.forum']
        dom = sitemap_qs2dom(qs, '/forum', Forum._rec_name)
        dom += env['website'].get_current_website().website_domain()
        for f in Forum.search(dom):
            loc = '/forum/%s' % slug(f)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    @http.route(['/forum/<model("forum.forum"):forum>',
                 '/forum/<model("forum.forum"):forum>/page/<int:page>',
                 '''/forum/<model("forum.forum"):forum>/tag/<model("forum.tag"):tag>/questions''',
                 '''/forum/<model("forum.forum"):forum>/tag/<model("forum.tag"):tag>/questions/page/<int:page>''',
                 ], type='http', auth="public", website=True, sitemap=sitemap_forum)
    def questions(self, forum, tag=None, page=1, filters='all', my=None, sorting=None, search='', **post):
        Post = request.env['forum.post']

        if sorting:
            # check that sorting is valid
            # retro-compatibily for V8 and google links
            try:
                Post._generate_order_by(sorting, None)
            except ValueError:
                sorting = False

        if not sorting:
            sorting = forum.default_order

        options = {
            'displayDescription': False,
            'displayDetail': False,
            'displayExtraDetail': False,
            'displayExtraLink': False,
            'displayImage': False,
            'allowFuzzy': not post.get('noFuzzy'),
            'forum': str(forum.id) if forum else None,
            'tag': str(tag.id) if tag else None,
            'filters': filters,
            'my': my,
        }
        question_count, details, fuzzy_search_term = request.website._search_with_fuzzy("forum_posts_only", search,
            limit=page * self._post_per_page, order=sorting, options=options)
        question_ids = details[0].get('results', Post)
        question_ids = question_ids[(page - 1) * self._post_per_page:page * self._post_per_page]

        if tag:
            url = "/forum/%s/tag/%s/questions" % (slug(forum), slug(tag))
        else:
            url = "/forum/%s" % slug(forum)

        url_args = {
            'sorting': sorting
        }
        if search:
            url_args['search'] = search
        if filters:
            url_args['filters'] = filters
        if my:
            url_args['my'] = my
        pager = request.website.pager(url=url, total=question_count, page=page,
                                      step=self._post_per_page, scope=self._post_per_page,
                                      url_args=url_args)

        values = self._prepare_user_values(forum=forum, searches=post, header={'ask_hide': not forum.active})
        values.update({
            'main_object': tag or forum,
            'edit_in_backend': not tag,
            'question_ids': question_ids,
            'question_count': question_count,
            'search_count': question_count,
            'pager': pager,
            'tag': tag,
            'filters': filters,
            'my': my,
            'sorting': sorting,
            'search': fuzzy_search_term or search,
            'original_search': fuzzy_search_term and search,
        })
        return request.render("website_forum.forum_index", values)

    @http.route(['''/forum/<model("forum.forum"):forum>/faq'''], type='http', auth="public", website=True, sitemap=True)
    def forum_faq(self, forum, **post):
        values = self._prepare_user_values(forum=forum, searches=dict(), header={'is_guidelines': True}, **post)
        return request.render("website_forum.faq", values)

    @http.route(['/forum/<model("forum.forum"):forum>/faq/karma'], type='http', auth="public", website=True, sitemap=False)
    def forum_faq_karma(self, forum, **post):
        values = self._prepare_user_values(forum=forum, header={'is_guidelines': True, 'is_karma': True}, **post)
        return request.render("website_forum.faq_karma", values)

    @http.route('/forum/get_tags', type='http', auth="public", methods=['GET'], website=True, sitemap=False)
    def tag_read(self, query='', limit=25, **post):
        data = request.env['forum.tag'].search_read(
            domain=[('name', '=ilike', (query or '') + "%")],
            fields=['id', 'name'],
            limit=int(limit),
        )
        return json.dumps(data)

    @http.route(['/forum/<model("forum.forum"):forum>/tag', '/forum/<model("forum.forum"):forum>/tag/<string:tag_char>'], type='http', auth="public", website=True, sitemap=False)
    def tags(self, forum, tag_char=None, **post):
        # build the list of tag first char, with their value as tag_char param Ex : [('All', 'all'), ('C', 'c'), ('G', 'g'), ('Z', z)]
        first_char_tag = forum.get_tags_first_char()
        first_char_list = [(t, t.lower()) for t in first_char_tag if t.isalnum()]
        first_char_list.insert(0, (_('All'), 'all'))

        active_char_tag = tag_char and tag_char.lower() or 'all'

        # generate domain for searched tags
        domain = [('forum_id', '=', forum.id), ('posts_count', '>', 0)]
        order_by = 'name'
        if active_char_tag and active_char_tag != 'all':
            domain.append(('name', '=ilike', tools.escape_psql(active_char_tag) + '%'))
            order_by = 'posts_count DESC'
        tags = request.env['forum.tag'].search(domain, limit=None, order=order_by)
        # prepare values and render template
        values = self._prepare_user_values(forum=forum, searches={'tags': True}, **post)

        values.update({
            'tags': tags,
            'pager_tag_chars': first_char_list,
            'active_char_tag': active_char_tag,
        })
        return request.render("website_forum.tag", values)

    # Questions
    # --------------------------------------------------

    @http.route('/forum/get_url_title', type='json', auth="user", methods=['POST'], website=True)
    def get_url_title(self, **kwargs):
        try:
            req = requests.get(kwargs.get('url'))
            req.raise_for_status()
            arch = lxml.html.fromstring(req.content)
            return arch.find(".//title").text
        except IOError:
            return False

    @http.route(['''/forum/<model("forum.forum"):forum>/question/<model("forum.post", "[('forum_id','=',forum.id),('parent_id','=',False),('can_view', '=', True)]"):question>'''],
                type='http', auth="public", website=True, sitemap=False)
    def old_question(self, forum, question, **post):
        # Compatibility pre-v14
        return request.redirect(_build_url_w_params("/forum/%s/%s" % (slug(forum), slug(question)), request.params), code=301)

    @http.route(['''/forum/<model("forum.forum"):forum>/<model("forum.post", "[('forum_id','=',forum.id),('parent_id','=',False),('can_view', '=', True)]"):question>'''],
                type='http', auth="public", website=True, sitemap=True)
    def question(self, forum, question, **post):
        if not forum.active:
            return request.render("website_forum.header", {'forum': forum})

        # Hide posts from abusers (negative karma), except for moderators
        if not question.can_view:
            raise werkzeug.exceptions.NotFound()

        # Hide pending posts from non-moderators and non-creator
        user = request.env.user
        if question.state == 'pending' and user.karma < forum.karma_post and question.create_uid != user:
            raise werkzeug.exceptions.NotFound()

        if question.parent_id:
            redirect_url = "/forum/%s/%s" % (slug(forum), slug(question.parent_id))
            return request.redirect(redirect_url, 301)
        filters = 'question'
        values = self._prepare_user_values(forum=forum, searches=post)
        values.update({
            'main_object': question,
            'question': question,
            'can_bump': (question.forum_id.allow_bump and not question.child_count and (datetime.today() - question.write_date).days > 9),
            'header': {'question_data': True},
            'filters': filters,
            'reversed': reversed,
        })
        if (request.httprequest.referrer or "").startswith(request.httprequest.url_root):
            values['back_button_url'] = request.httprequest.referrer

        # increment view counter
        question.sudo()._set_viewed()

        return request.render("website_forum.post_description_full", values)

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/toggle_favourite', type='json', auth="user", methods=['POST'], website=True)
    def question_toggle_favorite(self, forum, question, **post):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        favourite = not question.user_favourite
        question.sudo().favourite_ids = [(favourite and 4 or 3, request.uid)]
        if favourite:
            # Automatically add the user as follower of the posts that he
            # favorites (on unfavorite we chose to keep him as a follower until
            # he decides to not follow anymore).
            question.sudo().message_subscribe(request.env.user.partner_id.ids)
        return favourite

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/ask_for_close', type='http', auth="user", methods=['POST'], website=True)
    def question_ask_for_close(self, forum, question, **post):
        reasons = request.env['forum.post.reason'].search([('reason_type', '=', 'basic')])

        values = self._prepare_user_values(**post)
        values.update({
            'question': question,
            'forum': forum,
            'reasons': reasons,
        })
        return request.render("website_forum.close_post", values)

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/edit_answer', type='http', auth="user", website=True)
    def question_edit_answer(self, forum, question, **kwargs):
        for record in question.child_ids:
            if record.create_uid.id == request.uid:
                answer = record
                break
        return request.redirect("/forum/%s/post/%s/edit" % (slug(forum), slug(answer)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/close', type='http', auth="user", methods=['POST'], website=True)
    def question_close(self, forum, question, **post):
        question.close(reason_id=int(post.get('reason_id', False)))
        return request.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/reopen', type='http', auth="user", methods=['POST'], website=True)
    def question_reopen(self, forum, question, **kwarg):
        question.reopen()
        return request.redirect("/forum/%s/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/delete', type='http', auth="user", methods=['POST'], website=True)
    def question_delete(self, forum, question, **kwarg):
        question.active = False
        return request.redirect("/forum/%s/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/undelete', type='http', auth="user", methods=['POST'], website=True)
    def question_undelete(self, forum, question, **kwarg):
        question.active = True
        return request.redirect("/forum/%s/%s" % (slug(forum), slug(question)))

    # Post
    # --------------------------------------------------
    @http.route(['/forum/<model("forum.forum"):forum>/ask'], type='http', auth="user", website=True)
    def forum_post(self, forum, **post):
        user = request.env.user
        if not user.email or not tools.single_email_re.match(user.email):
            return request.redirect("/forum/%s/user/%s/edit?email_required=1" % (slug(forum), request.session.uid))
        values = self._prepare_user_values(forum=forum, searches={}, header={'ask_hide': True}, new_question=True)
        return request.render("website_forum.new_question", values)

    @http.route(['/forum/<model("forum.forum"):forum>/new',
                 '/forum/<model("forum.forum"):forum>/<model("forum.post"):post_parent>/reply'],
                type='http', auth="user", methods=['POST'], website=True)
    def post_create(self, forum, post_parent=None, **post):
        if post.get('content', '') == '<p><br></p>':
            return request.render('http_routing.http_error', {
                'status_code': _('Bad Request'),
                'status_message': post_parent and _('Reply should not be empty.') or _('Question should not be empty.')
            })

        post_tag_ids = forum._tag_to_write_vals(post.get('post_tags', ''))

        if request.env.user.forum_waiting_posts_count:
            return request.redirect("/forum/%s/ask" % slug(forum))

        new_question = request.env['forum.post'].create({
            'forum_id': forum.id,
            'name': post.get('post_name') or (post_parent and 'Re: %s' % (post_parent.name or '')) or '',
            'content': post.get('content', False),
            'parent_id': post_parent and post_parent.id or False,
            'tag_ids': post_tag_ids
        })
        return request.redirect("/forum/%s/%s" % (slug(forum), post_parent and slug(post_parent) or new_question.id))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/comment', type='http', auth="user", methods=['POST'], website=True)
    def post_comment(self, forum, post, **kwargs):
        question = post.parent_id if post.parent_id else post
        if kwargs.get('comment') and post.forum_id.id == forum.id:
            # TDE FIXME: check that post_id is the question or one of its answers
            body = tools.mail.plaintext2html(kwargs['comment'])
            post.with_context(mail_create_nosubscribe=True).message_post(
                body=body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment')
        return request.redirect("/forum/%s/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/toggle_correct', type='json', auth="public", website=True)
    def post_toggle_correct(self, forum, post, **kwargs):
        if post.parent_id is False:
            return request.redirect('/')
        if not request.session.uid:
            return {'error': 'anonymous_user'}

        # set all answers to False, only one can be accepted
        (post.parent_id.child_ids - post).write(dict(is_correct=False))
        post.is_correct = not post.is_correct
        return post.is_correct

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/delete', type='http', auth="user", methods=['POST'], website=True)
    def post_delete(self, forum, post, **kwargs):
        question = post.parent_id
        post.unlink()
        if question:
            request.redirect("/forum/%s/%s" % (slug(forum), slug(question)))
        return request.redirect("/forum/%s" % slug(forum))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/edit', type='http', auth="user", website=True)
    def post_edit(self, forum, post, **kwargs):
        tags = [dict(id=tag.id, name=tag.name) for tag in post.tag_ids]
        tags = json.dumps(tags)
        values = self._prepare_user_values(forum=forum)
        values.update({
            'tags': tags,
            'post': post,
            'is_edit': True,
            'is_answer': bool(post.parent_id),
            'searches': kwargs,
            'content': post.name,
        })
        return request.render("website_forum.edit_post", values)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/save', type='http', auth="user", methods=['POST'], website=True)
    def post_save(self, forum, post, **kwargs):
        vals = {
            'content': kwargs.get('content'),
        }

        if 'post_name' in kwargs:
            if not kwargs.get('post_name').strip():
                return request.render('http_routing.http_error', {
                    'status_code': _('Bad Request'),
                    'status_message': _('Title should not be empty.')
                })

            vals['name'] = kwargs.get('post_name')
        vals['tag_ids'] = forum._tag_to_write_vals(kwargs.get('post_tags', ''))
        post.write(vals)
        question = post.parent_id if post.parent_id else post
        return request.redirect("/forum/%s/%s" % (slug(forum), slug(question)))

    #  JSON utilities
    # --------------------------------------------------

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/upvote', type='json', auth="public", website=True)
    def post_upvote(self, forum, post, **kwargs):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        if request.uid == post.create_uid.id:
            return {'error': 'own_post'}
        upvote = True if not post.user_vote > 0 else False
        return post.vote(upvote=upvote)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/downvote', type='json', auth="public", website=True)
    def post_downvote(self, forum, post, **kwargs):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        if request.uid == post.create_uid.id:
            return {'error': 'own_post'}
        upvote = True if post.user_vote < 0 else False
        return post.vote(upvote=upvote)

    @http.route('/forum/post/bump', type='json', auth="public", website=True)
    def post_bump(self, post_id, **kwarg):
        post = request.env['forum.post'].browse(int(post_id))
        if not post.exists() or post.parent_id:
            return False
        return post.bump()

    # Moderation Tools
    # --------------------------------------------------

    @http.route('/forum/<model("forum.forum"):forum>/validation_queue', type='http', auth="user", website=True)
    def validation_queue(self, forum, **kwargs):
        user = request.env.user
        if user.karma < forum.karma_moderate:
            raise werkzeug.exceptions.NotFound()

        Post = request.env['forum.post']
        domain = [('forum_id', '=', forum.id), ('state', '=', 'pending')]
        posts_to_validate_ids = Post.search(domain)

        values = self._prepare_user_values(forum=forum)
        values.update({
            'posts_ids': posts_to_validate_ids.sudo(),
            'queue_type': 'validation',
        })

        return request.render("website_forum.moderation_queue", values)

    @http.route('/forum/<model("forum.forum"):forum>/flagged_queue', type='http', auth="user", website=True)
    def flagged_queue(self, forum, **kwargs):
        user = request.env.user
        if user.karma < forum.karma_moderate:
            raise werkzeug.exceptions.NotFound()

        Post = request.env['forum.post']
        domain = [('forum_id', '=', forum.id), ('state', '=', 'flagged')]
        if kwargs.get('spam_post'):
            domain += [('name', 'ilike', kwargs.get('spam_post'))]
        flagged_posts_ids = Post.search(domain, order='write_date DESC')

        values = self._prepare_user_values(forum=forum)
        values.update({
            'posts_ids': flagged_posts_ids.sudo(),
            'queue_type': 'flagged',
            'flagged_queue_active': 1,
        })

        return request.render("website_forum.moderation_queue", values)

    @http.route('/forum/<model("forum.forum"):forum>/offensive_posts', type='http', auth="user", website=True)
    def offensive_posts(self, forum, **kwargs):
        user = request.env.user
        if user.karma < forum.karma_moderate:
            raise werkzeug.exceptions.NotFound()

        Post = request.env['forum.post']
        domain = [('forum_id', '=', forum.id), ('state', '=', 'offensive'), ('active', '=', False)]
        offensive_posts_ids = Post.search(domain, order='write_date DESC')

        values = self._prepare_user_values(forum=forum)
        values.update({
            'posts_ids': offensive_posts_ids.sudo(),
            'queue_type': 'offensive',
        })

        return request.render("website_forum.moderation_queue", values)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/validate', type='http', auth="user", website=True)
    def post_accept(self, forum, post, **kwargs):
        url = "/forum/%s/validation_queue" % (slug(forum))
        if post.state == 'flagged':
            url = "/forum/%s/flagged_queue" % (slug(forum))
        elif post.state == 'offensive':
            url = "/forum/%s/offensive_posts" % (slug(forum))
        post.validate()
        return request.redirect(url)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/refuse', type='http', auth="user", website=True)
    def post_refuse(self, forum, post, **kwargs):
        post.refuse()
        return self.question_ask_for_close(forum, post)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/flag', type='json', auth="public", website=True)
    def post_flag(self, forum, post, **kwargs):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        return post.flag()[0]

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/ask_for_mark_as_offensive', type='http', auth="user", methods=['GET'], website=True)
    def post_ask_for_mark_as_offensive(self, forum, post, **kwargs):
        offensive_reasons = request.env['forum.post.reason'].search([('reason_type', '=', 'offensive')])

        values = self._prepare_user_values(forum=forum)
        values.update({
            'question': post,
            'forum': forum,
            'reasons': offensive_reasons,
            'offensive': True,
        })
        return request.render("website_forum.close_post", values)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/mark_as_offensive', type='http', auth="user", methods=["POST"], website=True)
    def post_mark_as_offensive(self, forum, post, **kwargs):
        post.mark_as_offensive(reason_id=int(kwargs.get('reason_id', False)))
        url = ''
        if post.parent_id:
            url = "/forum/%s/%s/#answer-%s" % (slug(forum), post.parent_id.id, post.id)
        else:
            url = "/forum/%s/%s" % (slug(forum), slug(post))
        return request.redirect(url)

    # User
    # --------------------------------------------------
    @http.route(['/forum/<model("forum.forum"):forum>/partner/<int:partner_id>'], type='http', auth="public", website=True)
    def open_partner(self, forum, partner_id=0, **post):
        if partner_id:
            partner = request.env['res.partner'].sudo().search([('id', '=', partner_id)])
            if partner and partner.user_ids:
                return request.redirect("/forum/%s/user/%d" % (slug(forum), partner.user_ids[0].id))
        return request.redirect("/forum/%s" % slug(forum))

    # Profile
    # -----------------------------------

    @http.route(['/forum/<model("forum.forum"):forum>/user/<int:user_id>'], type='http', auth="public", website=True)
    def view_user_forum_profile(self, forum, user_id, forum_origin, **post):
        return request.redirect('/profile/user/' + str(user_id) + '?forum_id=' + str(forum.id) + '&forum_origin=' + str(forum_origin))

    def _prepare_user_profile_values(self, user, **post):
        values = super(WebsiteForum, self)._prepare_user_profile_values(user, **post)
        if not post.get('no_forum'):
            if post.get('forum'):
                forums = post['forum']
            elif post.get('forum_id'):
                forums = request.env['forum.forum'].browse(int(post['forum_id']))
                values.update({
                    'edit_button_url_param': 'forum_id=%s' % str(post['forum_id']),
                    'forum_filtered': forums.name,
                })
            else:
                forums = request.env['forum.forum'].search([])

            values.update(self._prepare_user_values(forum=forums[0] if len(forums) == 1 else True, **post))
            if forums:
                values.update(self._prepare_open_forum_user(user, forums))
        return values

    def _prepare_open_forum_user(self, user, forums, **kwargs):
        Post = request.env['forum.post']
        Vote = request.env['forum.post.vote']
        Activity = request.env['mail.message']
        Followers = request.env['mail.followers']
        Data = request.env["ir.model.data"]

        # questions and answers by user
        user_question_ids = Post.search([
            ('parent_id', '=', False),
            ('forum_id', 'in', forums.ids), ('create_uid', '=', user.id)],
            order='create_date desc')
        count_user_questions = len(user_question_ids)
        min_karma_unlink = min(forums.mapped('karma_unlink_all'))

        # limit length of visible posts by default for performance reasons, except for the high
        # karma users (not many of them, and they need it to properly moderate the forum)
        post_display_limit = None
        if request.env.user.karma < min_karma_unlink:
            post_display_limit = 20

        user_questions = user_question_ids[:post_display_limit]
        user_answer_ids = Post.search([
            ('parent_id', '!=', False),
            ('forum_id', 'in', forums.ids), ('create_uid', '=', user.id)],
            order='create_date desc')
        count_user_answers = len(user_answer_ids)
        user_answers = user_answer_ids[:post_display_limit]

        # showing questions which user following
        post_ids = [follower.res_id for follower in Followers.sudo().search(
            [('res_model', '=', 'forum.post'), ('partner_id', '=', user.partner_id.id)])]
        followed = Post.search([('id', 'in', post_ids), ('forum_id', 'in', forums.ids), ('parent_id', '=', False)])

        # showing Favourite questions of user.
        favourite = Post.search(
            [('favourite_ids', '=', user.id), ('forum_id', 'in', forums.ids), ('parent_id', '=', False)])

        # votes which given on users questions and answers.
        data = Vote.read_group([('forum_id', 'in', forums.ids), ('recipient_id', '=', user.id)], ["vote"],
                               groupby=["vote"])
        up_votes, down_votes = 0, 0
        for rec in data:
            if rec['vote'] == '1':
                up_votes = rec['vote_count']
            elif rec['vote'] == '-1':
                down_votes = rec['vote_count']

        # Votes which given by users on others questions and answers.
        vote_ids = Vote.search([('user_id', '=', user.id)])

        # activity by user.
        comment = Data._xmlid_lookup('mail.mt_comment')[2]
        activities = Activity.search(
            [('res_id', 'in', (user_question_ids + user_answer_ids).ids), ('model', '=', 'forum.post'),
             ('subtype_id', '!=', comment)],
            order='date DESC', limit=100)

        posts = {}
        for act in activities:
            posts[act.res_id] = True
        posts_ids = Post.search([('id', 'in', list(posts))])
        posts = {x.id: (x.parent_id or x, x.parent_id and x or False) for x in posts_ids}

        # TDE CLEANME MASTER: couldn't it be rewritten using a 'menu' key instead of one key for each menu ?
        if user == request.env.user:
            kwargs['my_profile'] = True
        else:
            kwargs['users'] = True

        values = {
            'uid': request.env.user.id,
            'user': user,
            'main_object': user,
            'searches': kwargs,
            'questions': user_questions,
            'count_questions': count_user_questions,
            'answers': user_answers,
            'count_answers': count_user_answers,
            'followed': followed,
            'favourite': favourite,
            'up_votes': up_votes,
            'down_votes': down_votes,
            'activities': activities,
            'posts': posts,
            'vote_post': vote_ids,
            'is_profile_page': True,
            'badge_category': 'forum',
        }

        return values

    # Messaging
    # --------------------------------------------------

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/comment/<model("mail.message"):comment>/convert_to_answer', type='http', auth="user", methods=['POST'], website=True)
    def convert_comment_to_answer(self, forum, post, comment, **kwarg):
        post = request.env['forum.post'].convert_comment_to_answer(comment.id)
        if not post:
            return request.redirect("/forum/%s" % slug(forum))
        question = post.parent_id if post.parent_id else post
        return request.redirect("/forum/%s/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/convert_to_comment', type='http', auth="user", methods=['POST'], website=True)
    def convert_answer_to_comment(self, forum, post, **kwarg):
        question = post.parent_id
        new_msg = post.convert_answer_to_comment()
        if not new_msg:
            return request.redirect("/forum/%s" % slug(forum))
        return request.redirect("/forum/%s/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/comment/<model("mail.message"):comment>/delete', type='json', auth="user", website=True)
    def delete_comment(self, forum, post, comment, **kwarg):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        return post.unlink_comment(comment.id)[0]
