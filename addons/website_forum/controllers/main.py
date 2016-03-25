# -*- coding: utf-8 -*-
from datetime import datetime
import werkzeug.exceptions
import werkzeug.urls
import werkzeug.wrappers
import json
import lxml
from urllib2 import urlopen, URLError
import base64

import openerp
from openerp import tools, _
from openerp.addons.web import http
from openerp.addons.web.controllers.main import binary_content
from openerp.addons.web.http import request
from openerp.addons.website.models.website import slug


class WebsiteForum(http.Controller):
    _post_per_page = 10
    _user_per_page = 30

    def _get_notifications(self):
        badge_subtype = request.env.ref('gamification.mt_badge_granted')
        if badge_subtype:
            msg = request.env['mail.message'].search([('subtype_id', '=', badge_subtype.id), ('needaction', '=', True)])
        else:
            msg = list()
        return msg

    def _prepare_forum_values(self, forum=None, **kwargs):
        values = {
            'user': request.env.user,
            'is_public_user': request.env.user.id == request.website.user_id.id,
            'notifications': self._get_notifications(),
            'header': kwargs.get('header', dict()),
            'searches': kwargs.get('searches', dict()),
            'forum_welcome_message': request.httprequest.cookies.get('forum_welcome_message', False),
            'validation_email_sent': request.session.get('validation_email_sent', False),
            'validation_email_done': request.session.get('validation_email_done', False),
        }
        if forum:
            values['forum'] = forum
        elif kwargs.get('forum_id'):
            values['forum'] = request.env['forum.forum'].browse(kwargs.pop('forum_id'))
        values.update(kwargs)
        return values

    # User and validation
    # --------------------------------------------------

    @http.route('/forum/send_validation_email', type='json', auth='user', website=True)
    def send_validation_email(self, forum_id=None, **kwargs):
        if request.env.uid != request.website.user_id.id:
            request.env.user.send_forum_validation_email(forum_id=forum_id)
        request.session['validation_email_sent'] = True
        return True

    @http.route('/forum/validate_email', type='http', auth='public', website=True)
    def validate_email(self, token, id, email, forum_id=None, **kwargs):
        if forum_id:
            try:
                forum_id = int(forum_id)
            except ValueError:
                forum_id = None
        done = request.env['res.users'].sudo().browse(int(id)).process_forum_validation_token(token, email, forum_id=forum_id)[0]
        if done:
            request.session['validation_email_done'] = True
        if forum_id:
            return request.redirect("/forum/%s" % int(forum_id))
        return request.redirect('/forum')

    @http.route('/forum/validate_email/close', type='json', auth='public', website=True)
    def validate_email_done(self):
        request.session['validation_email_done'] = False
        return True

    # Forum
    # --------------------------------------------------

    @http.route(['/forum'], type='http', auth="public", website=True)
    def forum(self, **kwargs):
        forums = request.env['forum.forum'].search([])
        return request.website.render("website_forum.forum_all", {'forums': forums})

    @http.route('/forum/new', type='http', auth="user", methods=['POST'], website=True)
    def forum_create(self, forum_name="New Forum", add_menu=False):
        forum_id = request.env['forum.forum'].create({'name': forum_name})
        if add_menu:
            request.env['website.menu'].create({
                'name': forum_name,
                'url': "/forum/%s" % slug(forum_id),
                'parent_id': request.website.menu_id.id,
                'website_id': request.website.id,
            })
        return request.redirect("/forum/%s" % slug(forum_id))

    @http.route('/forum/notification_read', type='json', auth="user", methods=['POST'], website=True)
    def notification_read(self, **kwargs):
        request.env['mail.message'].browse([int(kwargs.get('notification_id'))]).set_message_done()
        return True

    @http.route(['/forum/<model("forum.forum"):forum>',
                 '/forum/<model("forum.forum"):forum>/page/<int:page>',
                 '''/forum/<model("forum.forum"):forum>/tag/<model("forum.tag", "[('forum_id','=',forum[0])]"):tag>/questions''',
                 '''/forum/<model("forum.forum"):forum>/tag/<model("forum.tag", "[('forum_id','=',forum[0])]"):tag>/questions/page/<int:page>''',
                 ], type='http', auth="public", website=True)
    def questions(self, forum, tag=None, page=1, filters='all', sorting=None, search='', post_type=None, **post):
        Post = request.env['forum.post']

        domain = [('forum_id', '=', forum.id), ('parent_id', '=', False), ('state', '=', 'active')]
        if search:
            domain += ['|', ('name', 'ilike', search), ('content', 'ilike', search)]
        if tag:
            domain += [('tag_ids', 'in', tag.id)]
        if filters == 'unanswered':
            domain += [('child_ids', '=', False)]
        elif filters == 'followed':
            domain += [('message_partner_ids', '=', request.env.user.partner_id.id)]
        if post_type:
            domain += [('post_type', '=', post_type)]

        if sorting:
            # check that sorting is valid
            # retro-compatibily for V8 and google links
            try:
                Post._generate_order_by(sorting, None)
            except ValueError:
                sorting = False

        if not sorting:
            sorting = forum.default_order

        question_count = Post.search_count(domain)

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
        pager = request.website.pager(url=url, total=question_count, page=page,
                                      step=self._post_per_page, scope=self._post_per_page,
                                      url_args=url_args)

        question_ids = Post.search(domain, limit=self._post_per_page, offset=pager['offset'], order=sorting)

        values = self._prepare_forum_values(forum=forum, searches=post)
        values.update({
            'main_object': tag or forum,
            'question_ids': question_ids,
            'question_count': question_count,
            'pager': pager,
            'tag': tag,
            'filters': filters,
            'sorting': sorting,
            'search': search,
            'post_type': post_type,
        })
        return request.website.render("website_forum.forum_index", values)

    @http.route(['/forum/<model("forum.forum"):forum>/faq'], type='http', auth="public", website=True)
    def forum_faq(self, forum, **post):
        values = self._prepare_forum_values(forum=forum, searches=dict(), header={'is_guidelines': True}, **post)
        return request.website.render("website_forum.faq", values)

    @http.route('/forum/get_tags', type='http', auth="public", methods=['GET'], website=True)
    def tag_read(self, q='', l=25, **post):
        data = request.env['forum.tag'].search_read(
            domain=[('name', '=ilike', (q or '') + "%")],
            fields=['id', 'name'],
            limit=int(l),
        )
        return json.dumps(data)

    @http.route(['/forum/<model("forum.forum"):forum>/tag', '/forum/<model("forum.forum"):forum>/tag/<string:tag_char>'], type='http', auth="public", website=True)
    def tags(self, forum, tag_char=None, **post):
        # build the list of tag first char, with their value as tag_char param Ex : [('All', 'all'), ('C', 'c'), ('G', 'g'), ('Z', z)]
        first_char_tag = forum.get_tags_first_char()
        first_char_list = [(t, t.lower()) for t in first_char_tag if t.isalnum()]
        first_char_list.insert(0, (_('All'), 'all'))
        # get active first char tag
        active_char_tag = first_char_list[1][1] if len(first_char_list) > 1 else 'all'
        if tag_char:
            active_char_tag = tag_char.lower()
        # generate domain for searched tags
        domain = [('forum_id', '=', forum.id), ('posts_count', '>', 0)]
        order_by = 'name'
        if active_char_tag and active_char_tag != 'all':
            domain.append(('name', '=ilike', tools.escape_psql(active_char_tag)+'%'))
            order_by = 'posts_count DESC'
        tags = request.env['forum.tag'].search(domain, limit=None, order=order_by)
        # prepare values and render template
        values = self._prepare_forum_values(forum=forum, searches={'tags': True}, **post)
        values.update({
            'tags': tags,
            'pager_tag_chars': first_char_list,
            'active_char_tag': active_char_tag,
        })
        return request.website.render("website_forum.tag", values)

    @http.route('/forum/<model("forum.forum"):forum>/edit_welcome_message', auth="user", website=True)
    def edit_welcome_message(self, forum, **kw):
        return request.website.render("website_forum.edit_welcome_message", {'forum': forum})

    # Questions
    # --------------------------------------------------

    @http.route('/forum/get_url_title', type='json', auth="user", methods=['POST'], website=True)
    def get_url_title(self, **kwargs):
        try:
            arch = lxml.html.parse(urlopen(kwargs.get('url')))
            return arch.find(".//title").text
        except URLError:
            return False

    @http.route(['''/forum/<model("forum.forum"):forum>/question/<model("forum.post", "[('forum_id','=',forum[0]),('parent_id','=',False),('can_view', '=', True)]"):question>'''], type='http', auth="public", website=True)
    def question(self, forum, question, **post):
        # Hide posts from abusers (negative karma), except for moderators
        if not question.can_view:
            raise werkzeug.exceptions.NotFound()

        # Hide pending posts from non-moderators and non-creator
        user = request.env.user
        if question.state == 'pending' and user.karma < forum.karma_post and question.create_uid != user:
            raise werkzeug.exceptions.NotFound()

        # increment view counter
        question.sudo().set_viewed()
        if question.parent_id:
            redirect_url = "/forum/%s/question/%s" % (slug(forum), slug(question.parent_id))
            return werkzeug.utils.redirect(redirect_url, 301)
        filters = 'question'
        values = self._prepare_forum_values(forum=forum, searches=post)
        values.update({
            'main_object': question,
            'question': question,
            'can_bump': (question.forum_id.allow_bump and not question.child_ids and (datetime.today() - datetime.strptime(question.write_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)).days > 9),
            'header': {'question_data': True},
            'filters': filters,
            'reversed': reversed,
        })
        return request.website.render("website_forum.post_description_full", values)

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/toggle_favourite', type='json', auth="user", methods=['POST'], website=True)
    def question_toggle_favorite(self, forum, question, **post):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        # TDE: add check for not public
        favourite = False if question.user_favourite else True
        if favourite:
            favourite_ids = [(4, request.uid)]
        else:
            favourite_ids = [(3, request.uid)]
        question.sudo().write({'favourite_ids': favourite_ids})
        return favourite

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/ask_for_close', type='http', auth="user", methods=['POST'], website=True)
    def question_ask_for_close(self, forum, question, **post):
        reasons = request.env['forum.post.reason'].search([('reason_type', '=', 'basic')])

        values = self._prepare_forum_values(**post)
        values.update({
            'question': question,
            'forum': forum,
            'reasons': reasons,
        })
        return request.website.render("website_forum.close_post", values)

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/edit_answer', type='http', auth="user", website=True)
    def question_edit_answer(self, forum, question, **kwargs):
        for record in question.child_ids:
            if record.create_uid.id == request.uid:
                answer = record
                break
        return werkzeug.utils.redirect("/forum/%s/post/%s/edit" % (slug(forum), slug(answer)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/close', type='http', auth="user", methods=['POST'], website=True)
    def question_close(self, forum, question, **post):
        question.close(reason_id=int(post.get('reason_id', False)))
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/reopen', type='http', auth="user", methods=['POST'], website=True)
    def question_reopen(self, forum, question, **kwarg):
        question.reopen()
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/delete', type='http', auth="user", methods=['POST'], website=True)
    def question_delete(self, forum, question, **kwarg):
        question.active = False
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/undelete', type='http', auth="user", methods=['POST'], website=True)
    def question_undelete(self, forum, question, **kwarg):
        question.active = True
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    # Post
    # --------------------------------------------------
    @http.route(['/forum/<model("forum.forum"):forum>/ask'], type='http', auth="user", website=True)
    def forum_post(self, forum, post_type=None, **post):
        user = request.env.user
        if post_type not in ['question', 'link', 'discussion']:  # fixme: make dynamic
            return werkzeug.utils.redirect('/forum/%s' % slug(forum))
        if not user.email or not tools.single_email_re.match(user.email):
            return werkzeug.utils.redirect("/forum/%s/user/%s/edit?email_required=1" % (slug(forum), request.session.uid))
        values = self._prepare_forum_values(forum=forum, searches={}, header={'ask_hide': True})
        return request.website.render("website_forum.new_%s" % post_type, values)

    @http.route(['/forum/<model("forum.forum"):forum>/new',
                 '/forum/<model("forum.forum"):forum>/<model("forum.post"):post_parent>/reply'],
                type='http', auth="user", methods=['POST'], website=True)
    def post_create(self, forum, post_parent=None, post_type=None, **post):
        if post_type == 'question' and not post.get('post_name', '').strip():
            return request.website.render('website.http_error', {'status_code': _('Bad Request'), 'status_message': _('Title should not be empty.')})
        post_tag_ids = forum._tag_to_write_vals(post.get('post_tags', ''))
        new_question = request.env['forum.post'].create({
            'forum_id': forum.id,
            'name': post.get('post_name') or (post_parent and 'Re: %s' % (post_parent.name or '')) or '',
            'content': post.get('content', False),
            'content_link': post.get('content_link', False),
            'parent_id': post_parent and post_parent.id or False,
            'tag_ids': post_tag_ids,
            'post_type': post_parent and post_parent.post_type or post_type,  # tde check in selection field
        })
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), post_parent and slug(post_parent) or new_question.id))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/comment', type='http', auth="user", methods=['POST'], website=True)
    def post_comment(self, forum, post, **kwargs):
        question = post.parent_id if post.parent_id else post
        if kwargs.get('comment') and post.forum_id.id == forum.id:
            # TDE FIXME: check that post_id is the question or one of its answers
            post.with_context(mail_create_nosubscribe=True).message_post(
                body=kwargs.get('comment'),
                message_type='comment',
                subtype='mt_comment')
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

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
            werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))
        return werkzeug.utils.redirect("/forum/%s" % slug(forum))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/edit', type='http', auth="user", website=True)
    def post_edit(self, forum, post, **kwargs):
        tags = [dict(id=tag.id, name=tag.name) for tag in post.tag_ids]
        tags = json.dumps(tags)
        values = self._prepare_forum_values(forum=forum)
        values.update({
            'tags': tags,
            'post': post,
            'is_answer': bool(post.parent_id),
            'searches': kwargs,
            'post_name': post.content_link,
            'content': post.name,
        })
        template = "website_forum.new_link" if post.post_type == 'link' and not post.parent_id else "website_forum.edit_post"
        return request.website.render(template, values)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/save', type='http', auth="user", methods=['POST'], website=True)
    def post_save(self, forum, post, **kwargs):
        if 'post_name' in kwargs and not kwargs.get('post_name').strip():
            return request.website.render('website.http_error', {'status_code': _('Bad Request'), 'status_message': _('Title should not be empty.')})
        post_tags = forum._tag_to_write_vals(kwargs.get('post_tags', ''))
        vals = {
            'tag_ids': post_tags,
            'name': kwargs.get('post_name'),
            'content': kwargs.get('content'),
            'content_link': kwargs.get('content_link'),
        }
        post.write(vals)
        question = post.parent_id if post.parent_id else post
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

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
    def validation_queue(self, forum):
        user = request.env.user
        if user.karma < forum.karma_moderate:
            raise werkzeug.exceptions.NotFound()

        Post = request.env['forum.post']
        domain = [('forum_id', '=', forum.id), ('state', '=', 'pending')]
        posts_to_validate_ids = Post.search(domain)

        values = self._prepare_forum_values(forum=forum)
        values.update({
            'posts_ids': posts_to_validate_ids,
            'queue_type': 'validation',
        })

        return request.website.render("website_forum.moderation_queue", values)

    @http.route('/forum/<model("forum.forum"):forum>/flagged_queue', type='http', auth="user", website=True)
    def flagged_queue(self, forum):
        user = request.env.user
        if user.karma < forum.karma_moderate:
            raise werkzeug.exceptions.NotFound()

        Post = request.env['forum.post']
        domain = [('forum_id', '=', forum.id), ('state', '=', 'flagged')]
        flagged_posts_ids = Post.search(domain, order='write_date DESC')

        values = self._prepare_forum_values(forum=forum)
        values.update({
            'posts_ids': flagged_posts_ids,
            'queue_type': 'flagged',
        })

        return request.website.render("website_forum.moderation_queue", values)

    @http.route('/forum/<model("forum.forum"):forum>/offensive_posts', type='http', auth="user", website=True)
    def offensive_posts(self, forum):
        user = request.env.user
        if user.karma < forum.karma_moderate:
            raise werkzeug.exceptions.NotFound()

        Post = request.env['forum.post']
        domain = [('forum_id', '=', forum.id), ('state', '=', 'offensive'), ('active', '=', False)]
        offensive_posts_ids = Post.search(domain, order='write_date DESC')

        values = self._prepare_forum_values(forum=forum)
        values.update({
            'posts_ids': offensive_posts_ids,
            'queue_type': 'offensive',
        })

        return request.website.render("website_forum.moderation_queue", values)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/validate', type='http', auth="user", website=True)
    def post_accept(self, forum, post):
        url = "/forum/%s/validation_queue" % (slug(forum))
        if post.state == 'flagged':
            url = "/forum/%s/flagged_queue" % (slug(forum))
        elif post.state == 'offensive':
            url = "/forum/%s/offensive_posts" % (slug(forum))
        post.validate()
        return werkzeug.utils.redirect(url)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/refuse', type='http', auth="user", website=True)
    def post_refuse(self, forum, post):
        post.refuse()
        return self.question_ask_for_close(forum, post)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/flag', type='json', auth="public", website=True)
    def post_flag(self, forum, post, **kwargs):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        return post.flag()[0]

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/ask_for_mark_as_offensive', type='http', auth="user", methods=['GET'], website=True)
    def post_ask_for_mark_as_offensive(self, forum, post):
        offensive_reasons = request.env['forum.post.reason'].search([('reason_type', '=', 'offensive')])

        values = self._prepare_forum_values(forum=forum)
        values.update({
            'question': post,
            'forum': forum,
            'reasons': offensive_reasons,
            'offensive': True,
        })
        return request.website.render("website_forum.close_post", values)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/mark_as_offensive', type='http', auth="user", methods=["POST"], website=True)
    def post_mark_as_offensive(self, forum, post, **kwargs):
        post.mark_as_offensive(reason_id=int(kwargs.get('reason_id', False)))
        url = ''
        if post.parent_id:
            url = "/forum/%s/question/%s/#answer-%s" % (slug(forum), post.parent_id.id, post.id)
        else:
            url = "/forum/%s/question/%s" % (slug(forum), slug(post))
        return werkzeug.utils.redirect(url)

    # User
    # --------------------------------------------------

    @http.route(['/forum/<model("forum.forum"):forum>/users',
                 '/forum/<model("forum.forum"):forum>/users/page/<int:page>'],
                type='http', auth="public", website=True)
    def users(self, forum, page=1, **searches):
        User = request.env['res.users']
        step = 30
        tag_count = User.sudo().search_count([('karma', '>', 1), ('website_published', '=', True)])
        pager = request.website.pager(url="/forum/%s/users" % slug(forum), total=tag_count, page=page, step=step, scope=30)
        user_obj = User.sudo().search([('karma', '>', 1), ('website_published', '=', True)], limit=step, offset=pager['offset'], order='karma DESC')
        # put the users in block of 3 to display them as a table
        users = [[] for i in range(len(user_obj) / 3 + 1)]
        for index, user in enumerate(user_obj):
            users[index / 3].append(user)
        searches['users'] = 'True'

        values = self._prepare_forum_values(forum=forum, searches=searches)
        values .update({
            'users': users,
            'main_object': forum,
            'notifications': self._get_notifications(),
            'pager': pager,
        })

        return request.website.render("website_forum.users", values)

    @http.route(['/forum/<model("forum.forum"):forum>/partner/<int:partner_id>'], type='http', auth="public", website=True)
    def open_partner(self, forum, partner_id=0, **post):
        if partner_id:
            partner = request.env['res.partner'].sudo().search([('id', '=', partner_id)])
            if partner and partner.user_ids:
                return werkzeug.utils.redirect("/forum/%s/user/%d" % (slug(forum), partner.user_ids[0].id))
        return werkzeug.utils.redirect("/forum/%s" % slug(forum))

    @http.route(['/forum/user/<int:user_id>/avatar'], type='http', auth="public", website=True)
    def user_avatar(self, user_id=0, **post):
        status, headers, content = binary_content(model='res.users', id=user_id, field='image', default_mimetype='image/png', env=request.env(user=openerp.SUPERUSER_ID))

        if not content:
            img_path = openerp.modules.get_module_resource('web', 'static/src/img', 'placeholder.png')
            with open(img_path, 'rb') as f:
                image = f.read()
            content = image.encode('base64')
        if status == 304:
            return werkzeug.wrappers.Response(status=304)
        image_base64 = base64.b64decode(content)
        headers.append(('Content-Length', len(image_base64)))
        response = request.make_response(image_base64, headers)
        response.status = str(status)
        return response

    @http.route(['/forum/<model("forum.forum"):forum>/user/<int:user_id>'], type='http', auth="public", website=True)
    def open_user(self, forum, user_id=0, **post):
        User = request.env['res.users']
        Post = request.env['forum.post']
        Vote = request.env['forum.post.vote']
        Activity = request.env['mail.message']
        Followers = request.env['mail.followers']
        Data = request.env["ir.model.data"]

        user = User.sudo().search([('id', '=', user_id)])
        current_user = request.env.user.sudo()

        # Users with high karma can see users with karma <= 0 for
        # moderation purposes, IFF they have posted something (see below)
        if (not user or (user.karma < 1 and current_user.karma < forum.karma_unlink_all)):
            return werkzeug.utils.redirect("/forum/%s" % slug(forum))
        values = self._prepare_forum_values(forum=forum, **post)

        # questions and answers by user
        user_question_ids = Post.search([
            ('parent_id', '=', False),
            ('forum_id', '=', forum.id), ('create_uid', '=', user.id)],
            order='create_date desc')
        count_user_questions = len(user_question_ids)

        if (user_id != request.session.uid and not
                (user.website_published or
                    (count_user_questions and current_user.karma > forum.karma_unlink_all))):
            return request.render("website_forum.private_profile", values, status=404)

        # limit length of visible posts by default for performance reasons, except for the high
        # karma users (not many of them, and they need it to properly moderate the forum)
        post_display_limit = None
        if current_user.karma < forum.karma_unlink_all:
            post_display_limit = 20

        user_questions = user_question_ids[:post_display_limit]
        user_answer_ids = Post.search([
            ('parent_id', '!=', False),
            ('forum_id', '=', forum.id), ('create_uid', '=', user.id)],
            order='create_date desc')
        count_user_answers = len(user_answer_ids)
        user_answers = user_answer_ids[:post_display_limit]

        # showing questions which user following
        post_ids = [follower.res_id for follower in Followers.sudo().search([('res_model', '=', 'forum.post'), ('partner_id', '=', user.partner_id.id)])]
        followed = Post.search([('id', 'in', post_ids), ('forum_id', '=', forum.id), ('parent_id', '=', False)])

        # showing Favourite questions of user.
        favourite = Post.search([('favourite_ids', '=', user.id), ('forum_id', '=', forum.id), ('parent_id', '=', False)])

        # votes which given on users questions and answers.
        data = Vote.read_group([('forum_id', '=', forum.id), ('recipient_id', '=', user.id)], ["vote"], groupby=["vote"])
        up_votes, down_votes = 0, 0
        for rec in data:
            if rec['vote'] == '1':
                up_votes = rec['vote_count']
            elif rec['vote'] == '-1':
                down_votes = rec['vote_count']

        # Votes which given by users on others questions and answers.
        vote_ids = Vote.search([('user_id', '=', user.id)])

        # activity by user.
        model, comment = Data.get_object_reference('mail', 'mt_comment')
        activities = Activity.search([('res_id', 'in', (user_question_ids + user_answer_ids).ids), ('model', '=', 'forum.post'), ('subtype_id', '!=', comment)],
                                     order='date DESC', limit=100)

        posts = {}
        for act in activities:
            posts[act.res_id] = True
        posts_ids = Post.search([('id', 'in', posts.keys())])
        posts = dict(map(lambda x: (x.id, (x.parent_id or x, x.parent_id and x or False)), posts_ids))

        # TDE CLEANME MASTER: couldn't it be rewritten using a 'menu' key instead of one key for each menu ?
        if user == request.env.user:
            post['my_profile'] = True
        else:
            post['users'] = True

        values.update({
            'uid': request.env.user.id,
            'user': user,
            'main_object': user,
            'searches': post,
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
        })
        return request.website.render("website_forum.user_detail_full", values)

    @http.route('/forum/<model("forum.forum"):forum>/user/<model("res.users"):user>/edit', type='http', auth="user", website=True)
    def edit_profile(self, forum, user, **kwargs):
        countries = request.env['res.country'].search([])
        values = self._prepare_forum_values(forum=forum, searches=kwargs)
        values.update({
            'email_required': kwargs.get('email_required'),
            'countries': countries,
            'notifications': self._get_notifications(),
        })
        return request.website.render("website_forum.edit_profile", values)

    @http.route('/forum/<model("forum.forum"):forum>/user/<model("res.users"):user>/save', type='http', auth="user", methods=['POST'], website=True)
    def save_edited_profile(self, forum, user, **kwargs):
        values = {
            'name': kwargs.get('name'),
            'website': kwargs.get('website'),
            'email': kwargs.get('email'),
            'city': kwargs.get('city'),
            'country_id': int(kwargs.get('country')) if kwargs.get('country') else False,
            'website_description': kwargs.get('description'),
        }
        if request.uid == user.id:  # the controller allows to edit only its own privacy settings; use partner management for other cases
            values['website_published'] = kwargs.get('website_published') == 'True'
        user.write(values)
        return werkzeug.utils.redirect("/forum/%s/user/%d" % (slug(forum), user.id))

    # Badges
    # --------------------------------------------------

    @http.route('/forum/<model("forum.forum"):forum>/badge', type='http', auth="public", website=True)
    def badges(self, forum, **searches):
        Badge = request.env['gamification.badge']
        badges = Badge.sudo().search([('challenge_ids.category', '=', 'forum')])
        badges = sorted(badges, key=lambda b: b.stat_count_distinct, reverse=True)
        values = self._prepare_forum_values(forum=forum, searches={'badges': True})
        values.update({
            'badges': badges,
        })
        return request.website.render("website_forum.badge", values)

    @http.route(['''/forum/<model("forum.forum"):forum>/badge/<model("gamification.badge"):badge>'''], type='http', auth="public", website=True)
    def badge_users(self, forum, badge, **kwargs):
        users = [badge_user.user_id for badge_user in badge.sudo().owner_ids]
        values = self._prepare_forum_values(forum=forum, searches={'badges': True})
        values.update({
            'badge': badge,
            'users': users,
        })
        return request.website.render("website_forum.badge_user", values)

    # Messaging
    # --------------------------------------------------

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/comment/<model("mail.message"):comment>/convert_to_answer', type='http', auth="user", methods=['POST'], website=True)
    def convert_comment_to_answer(self, forum, post, comment, **kwarg):
        post = request.env['forum.post'].convert_comment_to_answer(comment.id)
        if not post:
            return werkzeug.utils.redirect("/forum/%s" % slug(forum))
        question = post.parent_id if post.parent_id else post
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/convert_to_comment', type='http', auth="user", methods=['POST'], website=True)
    def convert_answer_to_comment(self, forum, post, **kwarg):
        question = post.parent_id
        new_msg_id = post.convert_answer_to_comment()[0]
        if not new_msg_id:
            return werkzeug.utils.redirect("/forum/%s" % slug(forum))
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/comment/<model("mail.message"):comment>/delete', type='json', auth="user", website=True)
    def delete_comment(self, forum, post, comment, **kwarg):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        return post.unlink_comment(comment.id)[0]
