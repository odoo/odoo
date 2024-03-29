# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging

import lxml
import requests
import werkzeug.exceptions
import werkzeug.urls
import werkzeug.wrappers

from odoo import _, http, tools
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.website_profile.controllers.main import WebsiteProfile
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.osv import expression

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
            values['forum'] = request.env['forum.forum'].browse(int(kwargs.pop('forum_id')))
        forum = values.get('forum')
        if forum and forum is not True and not request.env.user._is_public():
            def _get_my_other_forums():
                post_domain = expression.OR(
                    [[('create_uid', '=', request.uid)],
                     [('favourite_ids', '=', request.uid)]]
                )
                return request.env['forum.forum'].search(expression.AND([
                    request.website.website_domain(),
                    [('id', '!=', forum.id)],
                    [('post_ids', 'any', post_domain)]
                ]))
            values['my_other_forums'] = tools.lazy(_get_my_other_forums)
        else:
            values['my_other_forums'] = request.env['forum.forum']
        return values

    def _prepare_mark_as_offensive_values(self, post, **kwargs):
        offensive_reasons = request.env['forum.post.reason'].search([('reason_type', '=', 'offensive')])

        values = self._prepare_user_values(**kwargs)
        values.update({
            'question': post,
            'forum': post.forum_id,
            'reasons': offensive_reasons,
            'offensive': True,
        })
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

    def sitemap_forum(env, rule, qs):
        Forum = env['forum.forum']
        dom = sitemap_qs2dom(qs, '/forum', Forum._rec_name)
        dom += env['website'].get_current_website().website_domain()
        for f in Forum.search(dom):
            loc = '/forum/%s' % slug(f)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    def _get_forum_post_search_options(self, forum=None, tag=None, filters=None, my=None, create_uid=False, include_answers=False, **post):
        return {
            'allowFuzzy': not post.get('noFuzzy'),
            'create_uid': create_uid,
            'displayDescription': False,
            'displayDetail': False,
            'displayExtraDetail': False,
            'displayExtraLink': False,
            'displayImage': False,
            'filters': filters,
            'forum': str(forum.id) if forum else None,
            'include_answers': include_answers,
            'my': my,
            'tag': str(tag.id) if tag else None,
        }

    @http.route(['/forum/all',
                 '/forum/all/page/<int:page>',
                 '/forum/<model("forum.forum"):forum>',
                 '/forum/<model("forum.forum"):forum>/page/<int:page>',
                 '''/forum/<model("forum.forum"):forum>/tag/<model("forum.tag"):tag>/questions''',
                 '''/forum/<model("forum.forum"):forum>/tag/<model("forum.tag"):tag>/questions/page/<int:page>''',
                 ], type='http', auth="public", website=True, sitemap=sitemap_forum)
    def questions(self, forum=None, tag=None, page=1, filters='all', my=None, sorting=None, search='', create_uid=False, include_answers=False, **post):
        Post = request.env['forum.post']

        author = request.env['res.users'].browse(int(create_uid))

        if author == request.env.user:
            my = 'mine'
        if sorting:
            # check that sorting is valid
            # retro-compatibility for V8 and google links
            try:
                sorting = werkzeug.urls.url_unquote_plus(sorting)
                Post._order_to_sql(sorting, None)
            except (UserError, ValueError):
                sorting = False

        if not sorting:
            sorting = forum.default_order if forum else 'last_activity_date desc'

        options = self._get_forum_post_search_options(
            forum=forum,
            tag=tag,
            filters=filters,
            my=my,
            create_uid=author.id,
            include_answers=include_answers,
            my_profile=request.env.user == author,
            **post
        )
        question_count, details, fuzzy_search_term = request.website._search_with_fuzzy(
            "forum_posts_only", search, limit=page * self._post_per_page, order=sorting, options=options)
        question_ids = details[0].get('results', Post)
        question_ids = question_ids[(page - 1) * self._post_per_page:page * self._post_per_page]

        if not forum:
            url = '/forum/all'
        else:
            url = f"/forum/{slug(forum)}{f'/tag/{slug(tag)}/questions' if tag else ''}"

        url_args = {'sorting': sorting}

        for name, value in zip(['filters', 'search', 'my'], [filters, search, my]):
            if value:
                url_args[name] = value

        pager = tools.lazy(lambda: request.website.pager(
            url=url, total=question_count, page=page, step=self._post_per_page,
            scope=self._post_per_page, url_args=url_args))

        values = self._prepare_user_values(forum=forum, searches=post)
        values.update({
            'author': author,
            'edit_in_backend': True,
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

        if forum or tag:
            values['main_object'] = tag or forum

        return request.render("website_forum.forum_index", values)

    @http.route(['''/forum/<model("forum.forum"):forum>/faq'''], type='http', auth="public", website=True, sitemap=True)
    def forum_faq(self, forum, **post):
        values = self._prepare_user_values(forum=forum, searches=dict(), header={'is_guidelines': True}, **post)
        return request.render("website_forum.faq", values)

    @http.route(['/forum/<model("forum.forum"):forum>/faq/karma'], type='http', auth="public", website=True, sitemap=False)
    def forum_faq_karma(self, forum, **post):
        values = self._prepare_user_values(forum=forum, header={'is_guidelines': True, 'is_karma': True}, **post)
        return request.render("website_forum.faq_karma", values)

    # Tags
    # --------------------------------------------------

    @http.route('/forum/get_tags', type='http', auth="public", methods=['GET'], website=True, sitemap=False)
    def tag_read(self, forum_id, query='', limit=25, **post):
        data = request.env['forum.tag'].search_read(
            domain=[('forum_id', '=', int(forum_id)), ('name', '=ilike', (query or '') + "%")],
            fields=['id', 'name'],
            limit=int(limit),
        )
        return request.make_response(
            json.dumps(data),
            headers=[("Content-Type", "application/json")]
        )

    @http.route(['/forum/<model("forum.forum"):forum>/tag',
                 '/forum/<model("forum.forum"):forum>/tag/<string:tag_char>',
                 ], type='http', auth="public", website=True, sitemap=False)
    def tags(self, forum, tag_char='', filters='all', search='', **post):
        """Render a list of tags matching filters and search parameters.

        :param forum: Forum
        :param string tag_char: Only tags starting with a single character `tag_char`
        :param filters: One of 'all'|'followed'|'most_used'|'unused'.
          Can be combined with `search` and `tag_char`.
        :param string search: Search query using "forum_tags_only" `search_type`
        :param dict post: additional options passed to `_prepare_user_values`
        """
        if not isinstance(tag_char, str) or len(tag_char) > 1 or (tag_char and not tag_char.isalpha()):
            # So that further development does not miss this. Users shouldn't see it with normal usage.
            raise werkzeug.exceptions.BadRequest(_('Bad "tag_char" value "%(tag_char)s"', tag_char=tag_char))

        domain = [('forum_id', '=', forum.id), ('posts_count', '=' if filters == "unused" else '>', 0)]
        if filters == 'followed' and not request.env.user._is_public():
            domain = expression.AND([domain, [('message_is_follower', '=', True)]])

        # Build tags result without using tag_char to build pager, then return tags matching it
        values = self._prepare_user_values(forum=forum, searches={'tags': True}, **post)
        tags = request.env["forum.tag"]

        order = 'posts_count DESC' if tag_char else 'name'

        if search:
            values.update(search=search)
            search_domain = domain if filters in ('all', 'followed') else None
            __, details, __ = request.website._search_with_fuzzy(
                'forum_tags_only', search, limit=None, order=order, options={'forum': forum, 'domain': search_domain},
            )
            tags = details[0].get('results', tags)

        if filters in ('unused', 'most_used'):
            filter_tags = forum.tag_most_used_ids if filters == 'most_used' else forum.tag_unused_ids
            tags = tags & filter_tags if tags else filter_tags
        elif filters in ('all', 'followed'):
            if not search:
                tags = request.env['forum.tag'].search(domain, limit=None, order=order)
        else:
            raise werkzeug.exceptions.BadRequest(_('Bad "filters" value "%(filters)s".', filters=filters))

        first_char_tag = forum._get_tags_first_char(tags=tags)
        first_char_list = [(t, t.lower()) for t in first_char_tag if t.isalnum()]
        first_char_list.insert(0, (_('All'), ''))
        if tag_char:
            tags = tags.filtered(lambda t: t.name.startswith((tag_char.lower(), tag_char.upper())))

        values.update({
            'active_char_tag': tag_char.lower(),
            'pager_tag_chars': first_char_list,
            'search_count': len(tags) if search else None,
            'tags': tags,
        })
        return request.render("website_forum.forum_index_tags", values)

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
        return request.redirect("/forum/%s/%s" % (slug(forum), slug(question)), code=301)

    def sitemap_forum_post(env, rule, qs):
        ForumPost = env['forum.post']
        dom = expression.AND([
            env['website'].get_current_website().website_domain(),
            [('parent_id', '=', False), ('can_view', '=', True)],
        ])
        for forum_post in ForumPost.search(dom):
            loc = '/forum/%s/%s' % (slug(forum_post.forum_id), slug(forum_post))
            if not qs or qs.lower() in loc:
                yield {'loc': loc, 'lastmod': forum_post.write_date.date()}

    @http.route(['''/forum/<model("forum.forum"):forum>/<model("forum.post"):question>'''],
                type='http', auth="public", website=True, sitemap=sitemap_forum_post)
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
            'edit_in_backend': True,
            'question': question,
            'header': {'question_data': True},
            'filters': filters,
            'reversed': reversed,
        })
        if (request.httprequest.referrer or "").startswith(request.httprequest.url_root):
            values['has_back_button_url'] = True

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
        else:
            raise werkzeug.exceptions.NotFound()
        return request.redirect(f'/forum/{slug(forum)}/post/{slug(answer)}/edit')

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/close', type='http', auth="user", methods=['POST'], website=True)
    def question_close(self, forum, question, **post):
        question.close(reason_id=int(post.get('reason_id', False)))
        return request.redirect("/forum/%s/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/reopen', type='http', auth="user", methods=['POST'], website=True)
    def question_reopen(self, forum, question, **kwarg):
        question.reopen()
        return request.redirect("/forum/%s/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/delete', type='http', auth="user", methods=['POST'], website=True)
    def question_delete(self, forum, question, **kwarg):
        question.active = False
        return request.redirect("/forum/%s" % slug(forum))

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
        values = self._prepare_user_values(forum=forum, searches={}, new_question=True)
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
        if forum.has_pending_post:
            return request.redirect("/forum/%s/ask" % slug(forum))

        new_question = request.env['forum.post'].create({
            'forum_id': forum.id,
            'name': post.get('post_name') or (post_parent and 'Re: %s' % (post_parent.name or '')) or '',
            'content': post.get('content', False),
            'parent_id': post_parent and post_parent.id or False,
            'tag_ids': post_tag_ids
        })
        if post_parent:
            post_parent._update_last_activity()
        return request.redirect(f'/forum/{slug(forum)}/{slug(post_parent) if post_parent else new_question.id}')

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/comment', type='http', auth="user", methods=['POST'], website=True)
    def post_comment(self, forum, post, **kwargs):
        question = post.parent_id or post
        if kwargs.get('comment') and post.forum_id.id == forum.id:
            # TDE FIXME: check that post_id is the question or one of its answers
            body = tools.mail.plaintext2html(kwargs['comment'])
            post.with_context(mail_create_nosubscribe=True).message_post(
                body=body,
                message_type='comment',
                subtype_xmlid='mail.mt_comment')
            question._update_last_activity()
        return request.redirect(f'/forum/{slug(forum)}/{slug(question)}')

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/toggle_correct', type='json', auth="public", website=True)
    def post_toggle_correct(self, forum, post, **kwargs):
        if post.parent_id is False:
            return request.redirect('/')
        if request.uid == post.create_uid.id:
            return {'error': 'own_post'}
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

    @http.route('/forum/<model("forum.forum"):forum>/closed_posts', type='http', auth="user", website=True)
    def closed_posts(self, forum, **kwargs):
        if request.env.user.karma < forum.karma_moderate:
            raise werkzeug.exceptions.NotFound()

        closed_posts_ids = request.env['forum.post'].search(
            [('forum_id', '=', forum.id), ('state', '=', 'close')],
            order='write_date DESC, id DESC',
        )
        values = self._prepare_user_values(forum=forum)
        values.update({
            'posts_ids': closed_posts_ids,
            'queue_type': 'close',
        })

        return request.render("website_forum.moderation_queue", values)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/validate', type='http', auth="user", website=True)
    def post_accept(self, forum, post, **kwargs):
        if post.state == 'flagged':
            url = f'/forum/{slug(forum)}/flagged_queue'
        elif post.state == 'offensive':
            url = f'/forum/{slug(forum)}/offensive_posts'
        elif post.state == 'close':
            url = f'/forum/{slug(forum)}/closed_posts'
        else:
            url = f'/forum/{slug(forum)}/validation_queue'
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

    @http.route('/forum/<model("forum.post"):post>/ask_for_mark_as_offensive', type='json', auth="user", website=True)
    def post_json_ask_for_mark_as_offensive(self, post, **kwargs):
        if not post.can_moderate:
            raise AccessError(_('%d karma required to mark a post as offensive.', post.forum_id.karma_moderate))
        values = self._prepare_mark_as_offensive_values(post, **kwargs)
        return request.env['ir.ui.view']._render_template('website_forum.mark_as_offensive', values)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/ask_for_mark_as_offensive', type='http', auth="user", methods=['GET'], website=True)
    def post_http_ask_for_mark_as_offensive(self, forum, post, **kwargs):
        if not post.can_moderate:
            raise AccessError(_('%d karma required to mark a post as offensive.', forum.karma_moderate))
        values = self._prepare_mark_as_offensive_values(post, **kwargs)
        return request.render("website_forum.close_post", values)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/mark_as_offensive', type='http', auth="user", methods=["POST"], website=True)
    def post_mark_as_offensive(self, forum, post, **kwargs):
        post.mark_as_offensive(reason_id=int(kwargs.get('reason_id', False)))
        if post.parent_id:
            url = f'/forum/{slug(forum)}/{post.parent_id.id}/#answer-{post.id}'
        else:
            url = f'/forum/{slug(forum)}/{slug(post)}'
        return request.redirect(url)

    # User
    # --------------------------------------------------
    @http.route(['/forum/<model("forum.forum"):forum>/partner/<int:partner_id>'], type='http', auth="public", website=True)
    def open_partner(self, forum, partner_id=0, **post):
        if partner_id:
            partner = request.env['res.partner'].sudo().search([('id', '=', partner_id)])
            if partner and partner.user_ids:
                return request.redirect(f'/forum/{slug(forum)}/user/{partner.user_ids[0].id}')
        return request.redirect('/forum/' + slug(forum))

    # Profile
    # -----------------------------------

    @http.route(['/forum/user/<int:user_id>'], type='http', auth="public", website=True)
    def view_user_forum_profile(self, user_id, forum_id='', forum_origin='/forum', **post):
        forum_origin_query = f'?forum_origin={forum_origin}&forum_id={forum_id}' if forum_id else ''
        return request.redirect(f'/profile/user/{user_id}{forum_origin_query}')

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
        data = Vote._read_group(
            [('forum_id', 'in', forums.ids), ('recipient_id', '=', user.id)], ['vote'], aggregates=['__count']
        )
        up_votes, down_votes = 0, 0
        for vote, count in data:
            if vote == '1':
                up_votes = count
            elif vote == '-1':
                down_votes = count

        # Votes which given by users on others questions and answers.
        vote_ids = Vote.search([('user_id', '=', user.id), ('forum_id', 'in', forums.ids)])

        # activity by user.
        comment = Data._xmlid_lookup('mail.mt_comment')[1]
        activities = Activity.search(
            [('res_id', 'in', (user_question_ids + user_answer_ids).ids), ('model', '=', 'forum.post'),
             ('subtype_id', '!=', comment)],
            order='date DESC', limit=100)

        posts = {}
        for act in activities:
            posts[act.res_id] = True
        posts_ids = Post.search([('id', 'in', list(posts))])
        posts = {x.id: (x.parent_id or x, x.parent_id and x or False) for x in posts_ids}

        if user != request.env.user:
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
