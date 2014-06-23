# -*- coding: utf-8 -*-

from datetime import datetime
import werkzeug.urls
import werkzeug.wrappers
import simplejson

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.addons.web.controllers.main import login_redirect
from openerp.addons.web.http import request
from openerp.addons.website.controllers.main import Website as controllers
from openerp.addons.website.models.website import slug
from openerp.tools import html2plaintext

controllers = controllers()


class WebsiteForum(http.Controller):
    _post_per_page = 10
    _user_per_page = 30

    def _get_notifications(self):
        cr, uid, context = request.cr, request.uid, request.context
        Message = request.registry['mail.message']
        badge_st_id = request.registry['ir.model.data'].xmlid_to_res_id(cr, uid, 'gamification.mt_badge_granted')
        if badge_st_id:
            msg_ids = Message.search(cr, uid, [('subtype_id', '=', badge_st_id), ('to_read', '=', True)], context=context)
            msg = Message.browse(cr, uid, msg_ids, context=context)
        else:
            msg = list()
        return msg

    def _prepare_forum_values(self, forum=None, **kwargs):
        Forum = request.registry['forum.forum']
        user = request.registry['res.users'].browse(request.cr, request.uid, request.uid, context=request.context)
        values = {'user': user,
                  'is_public_user': user.id == request.website.user_id.id,
                  'notifications': self._get_notifications(),
                  'header': kwargs.get('header', dict()),
                  'searches': kwargs.get('searches', dict()),
                  'can_edit_own': True,
                  'can_edit_all': user.karma > Forum._karma_modo_edit_all,
                  'can_close_own': user.karma > Forum._karma_modo_close_own,
                  'can_close_all': user.karma > Forum._karma_modo_close_all,
                  'can_unlink_own': user.karma > Forum._karma_modo_unlink_own,
                  'can_unlink_all': user.karma > Forum._karma_modo_unlink_all,
                  'can_unlink_comment': user.karma > Forum._karma_modo_unlink_comment,
                  }
        if forum:
            values['forum'] = forum
        elif kwargs.get('forum_id'):
            values['forum'] = request.registry['forum.forum'].browse(request.cr, request.uid, kwargs.pop('forum_id'), context=request.context)
        values.update(kwargs)
        return values

    def _has_enough_karma(self, karma_name, uid=None):
        Forum = request.registry['forum.forum']
        karma = hasattr(Forum, karma_name) and getattr(Forum, karma_name) or 0
        user = request.registry['res.users'].browse(request.cr, SUPERUSER_ID, uid or request.uid, context=request.context)
        if user.karma < karma:
            return False, {'error': 'not_enough_karma', 'karma': karma}
        return True, {}

    # Forum
    # --------------------------------------------------

    @http.route(['/forum'], type='http', auth="public", website=True)
    def forum(self, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        Forum = request.registry['forum.forum']
        obj_ids = Forum.search(cr, uid, [], context=context)
        forums = Forum.browse(cr, uid, obj_ids, context=context)
        return request.website.render("website_forum.forum_all", {'forums': forums})

    @http.route('/forum/new', type='http', auth="user", methods=['POST'], website=True)
    def forum_create(self, forum_name="New Forum", **kwargs):
        forum_id = request.registry['forum.forum'].create(request.cr, request.uid, {
            'name': forum_name,
        }, context=request.context)
        return request.redirect("/forum/%s" % slug(forum_id))

    @http.route('/forum/notification_read', type='json', auth="user", methods=['POST'], website=True)
    def notification_read(self, **kwargs):
        request.registry['mail.message'].set_message_read(request.cr, request.uid, [int(kwargs.get('notification_id'))], read=True, context=request.context)
        return True

    @http.route(['/forum/<model("forum.forum"):forum>',
                 '/forum/<model("forum.forum"):forum>/page/<int:page>',
                 '''/forum/<model("forum.forum"):forum>/tag/<model("forum.tag", "[('forum_id','=',forum[0])]"):tag>/questions''',
                 '''/forum/<model("forum.forum"):forum>/tag/<model("forum.tag", "[('forum_id','=',forum[0])]"):tag>/questions/page/<int:page>''',
                 ], type='http', auth="public", website=True)
    def questions(self, forum, tag=None, page=1, filters='all', sorting='date', search='', **post):
        cr, uid, context = request.cr, request.uid, request.context
        Post = request.registry['forum.post']
        user = request.registry['res.users'].browse(cr, uid, uid, context=context)

        domain = [('forum_id', '=', forum.id), ('parent_id', '=', False), ('state', '=', 'active')]
        if search:
            domain += ['|', ('name', 'ilike', search), ('content', 'ilike', search)]
        if tag:
            domain += [('tag_ids', 'in', tag.id)]
        if filters == 'unanswered':
            domain += [('child_ids', '=', False)]
        elif filters == 'followed':
            domain += [('message_follower_ids', '=', user.partner_id.id)]
        else:
            filters = 'all'

        if sorting == 'answered':
            order = 'child_count desc'
        elif sorting == 'vote':
            order = 'vote_count desc'
        elif sorting == 'date':
            order = 'write_date desc'
        else:
            sorting = 'creation'
            order = 'create_date desc'

        question_count = Post.search(cr, uid, domain, count=True, context=context)
        if tag:
            url = "/forum/%s/tag/%s/questions" % (slug(forum), slug(tag))
        else:
            url = "/forum/%s" % slug(forum)

        url_args = {}
        if search:
            url_args['search'] = search
        if filters:
            url_args['filters'] = filters
        if sorting:
            url_args['sorting'] = sorting
        pager = request.website.pager(url=url, total=question_count, page=page,
                                      step=self._post_per_page, scope=self._post_per_page,
                                      url_args=url_args)

        obj_ids = Post.search(cr, uid, domain, limit=self._post_per_page, offset=pager['offset'], order=order, context=context)
        question_ids = Post.browse(cr, uid, obj_ids, context=context)

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
        })
        return request.website.render("website_forum.forum_index", values)

    @http.route(['/forum/<model("forum.forum"):forum>/faq'], type='http', auth="public", website=True)
    def forum_faq(self, forum, **post):
        values = self._prepare_forum_values(forum=forum, searches=dict(), header={'is_guidelines': True}, **post)
        return request.website.render("website_forum.faq", values)

    @http.route('/forum/get_tags', type='http', auth="public", methods=['GET'], website=True)
    def tag_read(self, **post):
        tags = request.registry['forum.tag'].search_read(request.cr, request.uid, [], ['name'], context=request.context)
        data = [tag['name'] for tag in tags]
        return simplejson.dumps(data)

    @http.route(['/forum/<model("forum.forum"):forum>/tag'], type='http', auth="public", website=True)
    def tags(self, forum, page=1, **post):
        cr, uid, context = request.cr, request.uid, request.context
        Tag = request.registry['forum.tag']
        obj_ids = Tag.search(cr, uid, [('forum_id', '=', forum.id), ('posts_count', '>', 0)], limit=None, order='posts_count DESC', context=context)
        tags = Tag.browse(cr, uid, obj_ids, context=context)
        values = self._prepare_forum_values(forum=forum, searches={'tags': True}, **post)
        values.update({
            'tags': tags,
            'main_object': forum,
        })
        return request.website.render("website_forum.tag", values)

    # Questions
    # --------------------------------------------------

    @http.route(['/forum/<model("forum.forum"):forum>/ask'], type='http', auth="public", website=True)
    def question_ask(self, forum, **post):
        if not request.session.uid:
            return login_redirect()
        values = self._prepare_forum_values(forum=forum, searches={},  header={'ask_hide': True})
        return request.website.render("website_forum.ask_question", values)

    @http.route('/forum/<model("forum.forum"):forum>/question/new', type='http', auth="user", methods=['POST'], website=True)
    def question_create(self, forum, **post):
        cr, uid, context = request.cr, request.uid, request.context
        Tag = request.registry['forum.tag']
        question_tag_ids = []
        if post.get('question_tags').strip('[]'):
            tags = post.get('question_tags').strip('[]').replace('"', '').split(",")
            for tag in tags:
                tag_ids = Tag.search(cr, uid, [('name', '=', tag)], context=context)
                if tag_ids:
                    question_tag_ids.append((4, tag_ids[0]))
                else:
                    question_tag_ids.append((0, 0, {'name': tag, 'forum_id': forum.id}))

        new_question_id = request.registry['forum.post'].create(
            request.cr, request.uid, {
                'forum_id': forum.id,
                'name': post.get('question_name'),
                'content': post.get('content'),
                'tag_ids': question_tag_ids,
            }, context=context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), new_question_id))

    @http.route(['''/forum/<model("forum.forum"):forum>/question/<model("forum.post", "[('forum_id','=',forum[0])]"):question>'''], type='http', auth="public", website=True)
    def question(self, forum, question, **post):
        cr, uid, context = request.cr, request.uid, request.context
        # increment view counter
        request.registry['forum.post'].set_viewed(cr, SUPERUSER_ID, [question.id], context=context)

        filters = 'question'
        values = self._prepare_forum_values(forum=forum, searches=post)
        values.update({
            'main_object': question,
            'question': question,
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
        request.registry['forum.post'].write(request.cr, request.uid, [question.id], {'favourite_ids': favourite_ids}, context=request.context)
        return favourite

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/ask_for_close', type='http', auth="user", methods=['POST'], website=True)
    def question_ask_for_close(self, forum, question, **post):
        check_res = self._has_enough_karma(question.create_uid.id == request.uid and '_karma_modo_close_own' or '_karma_modo_close_all')
        if not check_res[0]:
            return werkzeug.utils.redirect("/forum/%s" % slug(forum))

        cr, uid, context = request.cr, request.uid, request.context
        Reason = request.registry['forum.post.reason']
        reason_ids = Reason.search(cr, uid, [], context=context)
        reasons = Reason.browse(cr, uid, reason_ids, context)

        values = self._prepare_forum_values(**post)
        values.update({
            'question': question,
            'question': question,
            'forum': forum,
            'reasons': reasons,
        })
        return request.website.render("website_forum.close_question", values)

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/edit_answer', type='http', auth="user", website=True)
    def question_edit_answer(self, forum, question, **kwargs):
        for record in question.child_ids:
            if record.create_uid.id == request.uid:
                answer = record
                break
        return werkzeug.utils.redirect("/forum/%s/post/%s/edit" % (slug(forum), slug(answer)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/close', type='http', auth="user", methods=['POST'], website=True)
    def question_close(self, forum, question, **post):
        check_res = self._has_enough_karma(question.create_uid.id == request.uid and '_karma_modo_close_own' or '_karma_modo_close_all')
        if not check_res[0]:
            return werkzeug.utils.redirect("/forum/%s" % slug(forum))

        request.registry['forum.post'].write(request.cr, request.uid, [question.id], {
            'state': 'close',
            'closed_uid': request.uid,
            'closed_date': datetime.today().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),
            'closed_reason_id': int(post.get('reason_id', False)),
        }, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/reopen', type='http', auth="user", methods=['POST'], website=True)
    def question_reopen(self, forum, question, **kwarg):
        check_res = self._has_enough_karma(question.create_uid.id == request.uid and '_karma_modo_close_own' or '_karma_modo_close_all')
        if not check_res[0]:
            return werkzeug.utils.redirect("/forum/%s" % slug(forum))

        request.registry['forum.post'].write(request.cr, request.uid, [question.id], {'state': 'active'}, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/delete', type='http', auth="user", methods=['POST'], website=True)
    def question_delete(self, forum, question, **kwarg):
        check_res = self._has_enough_karma(question.create_uid.id == request.uid and '_karma_modo_unlink_own' or '_karma_modo_unlink_all')
        if not check_res[0]:
            return werkzeug.utils.redirect("/forum/%s" % slug(forum))

        request.registry['forum.post'].write(request.cr, request.uid, [question.id], {'active': False}, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/question/<model("forum.post"):question>/undelete', type='http', auth="user", methods=['POST'], website=True)
    def question_undelete(self, forum, question, **kwarg):
        check_res = self._has_enough_karma(question.create_uid.id == request.uid and '_karma_modo_unlink_own' or '_karma_modo_unlink_all')
        if not check_res[0]:
            return werkzeug.utils.redirect("/forum/%s" % slug(forum))

        request.registry['forum.post'].write(request.cr, request.uid, [question.id], {'active': True}, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    # Post
    # --------------------------------------------------

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/new', type='http', auth="public", methods=['POST'], website=True)
    def post_new(self, forum, post, **kwargs):
        if not request.session.uid:
            return login_redirect()
        request.registry['forum.post'].create(
            request.cr, request.uid, {
                'forum_id': forum.id,
                'parent_id': post.id,
                'content': kwargs.get('content'),
            }, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(post)))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/comment', type='http', auth="public", methods=['POST'], website=True)
    def post_comment(self, forum, post, **kwargs):
        if not request.session.uid:
            return login_redirect()
        question = post.parent_id if post.parent_id else post
        cr, uid, context = request.cr, request.uid, request.context
        if kwargs.get('comment') and post.forum_id.id == forum.id:
            # TDE FIXME: check that post_id is the question or one of its answers
            request.registry['forum.post'].message_post(
                cr, uid, post.id,
                body=kwargs.get('comment'),
                type='comment',
                subtype='mt_comment',
                context=dict(context, mail_create_nosubcribe=True))
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/toggle_correct', type='json', auth="public", website=True)
    def post_toggle_correct(self, forum, post, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        if post.parent_id is False:
            return request.redirect('/')
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        user = request.registry['res.users'].browse(request.cr, SUPERUSER_ID, request.uid, context=request.context)
        if post.parent_id.create_uid.id != uid and user.karma < request.registry['forum.forum']._karma_answer_accept_all:
            return {'error': 'not_enough_karma', 'karma': request.registry['forum.forum']._karma_answer_accept_all}
        if post.create_uid.id == user.id and user.karma < request.registry['forum.forum']._karma_answer_accept_own:
            return {'error': 'not_enough_karma', 'karma': request.registry['forum.forum']._karma_answer_accept_own}

        # set all answers to False, only one can be accepted
        request.registry['forum.post'].write(cr, uid, [c.id for c in post.parent_id.child_ids], {'is_correct': False}, context=context)
        request.registry['forum.post'].write(cr, uid, [post.id], {'is_correct': not post.is_correct}, context=context)
        return not post.is_correct

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/delete', type='http', auth="user", methods=['POST'], website=True)
    def post_delete(self, forum, post, **kwargs):
        check_res = self._has_enough_karma(post.create_uid.id == request.uid and '_karma_modo_unlink_own' or '_karma_modo_unlink_all')
        if not check_res[0]:
            return werkzeug.utils.redirect("/forum/%s" % slug(forum))

        question = post.parent_id
        request.registry['forum.post'].unlink(request.cr, request.uid, [post.id], context=request.context)
        if question:
            werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))
        return werkzeug.utils.redirect("/forum/%s" % slug(forum))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/edit', type='http', auth="user", website=True)
    def post_edit(self, forum, post, **kwargs):
        check_res = self._has_enough_karma(post.create_uid.id == request.uid and '_karma_modo_edit_own' or '_karma_modo_edit_all')
        if not check_res[0]:
            return werkzeug.utils.redirect("/forum/%s" % slug(forum))

        tags = ""
        for tag_name in post.tag_ids:
            tags += tag_name.name + ","
        values = self._prepare_forum_values(forum=forum)
        values.update({
            'tags': tags,
            'post': post,
            'is_answer': bool(post.parent_id),
            'searches': kwargs
        })
        return request.website.render("website_forum.edit_post", values)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/save', type='http', auth="user", methods=['POST'], website=True)
    def post_save(self, forum, post, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        question_tags = []
        if kwargs.get('question_tag') and kwargs.get('question_tag').strip('[]'):
            Tag = request.registry['forum.tag']
            tags = kwargs.get('question_tag').strip('[]').replace('"', '').split(",")
            for tag in tags:
                tag_ids = Tag.search(cr, uid, [('name', '=', tag)], context=context)
                if tag_ids:
                    question_tags += tag_ids
                else:
                    new_tag = Tag.create(cr, uid, {'name': tag, 'forum_id': forum.id}, context=context)
                    question_tags.append(new_tag)
        vals = {
            'tag_ids': [(6, 0, question_tags)],
            'name': kwargs.get('question_name'),
            'content': kwargs.get('content'),
        }
        request.registry['forum.post'].write(cr, uid, [post.id], vals, context=context)
        question = post.parent_id if post.parent_id else post
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum), slug(question)))

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/upvote', type='json', auth="public", website=True)
    def post_upvote(self, forum, post, **kwargs):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        if request.uid == post.create_uid.id:
            return {'error': 'own_post'}
        check_res = self._has_enough_karma('_karma_upvote')
        if not check_res[0]:
            return check_res[1]
        upvote = True if not post.user_vote > 0 else False
        return request.registry['forum.post'].vote(request.cr, request.uid, [post.id], upvote=upvote, context=request.context)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/downvote', type='json', auth="public", website=True)
    def post_downvote(self, forum, post, **kwargs):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        if request.uid == post.create_uid.id:
            return {'error': 'own_post'}
        check_res = self._has_enough_karma('_karma_downvote')
        if not check_res[0]:
            return check_res[1]
        upvote = True if post.user_vote < 0 else False
        return request.registry['forum.post'].vote(request.cr, request.uid, [post.id], upvote=upvote, context=request.context)

    # User
    # --------------------------------------------------

    @http.route(['/forum/<model("forum.forum"):forum>/users',
                 '/forum/<model("forum.forum"):forum>/users/page/<int:page>'],
                type='http', auth="public", website=True)
    def users(self, forum, page=1, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        User = request.registry['res.users']

        step = 30
        tag_count = User.search(cr, SUPERUSER_ID, [('karma', '>', 1), ('website_published', '=', True)], count=True, context=context)
        pager = request.website.pager(url="/forum/%s/users" % slug(forum), total=tag_count, page=page, step=step, scope=30)

        obj_ids = User.search(cr, SUPERUSER_ID, [('karma', '>', 1), ('website_published', '=', True)], limit=step, offset=pager['offset'], order='karma DESC', context=context)
        # put the users in block of 3 to display them as a table
        users = [[] for i in range(len(obj_ids)/3+1)]
        for index, user in enumerate(User.browse(cr, SUPERUSER_ID, obj_ids, context=context)):
            users[index/3].append(user)
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
        cr, uid, context = request.cr, request.uid, request.context
        pids = request.registry['res.partner'].search(cr, SUPERUSER_ID, [('id', '=', partner_id)], context=context)
        if pids:
            partner = request.registry['res.partner'].browse(cr, SUPERUSER_ID, pids[0], context=context)
            if partner.user_ids:
                return werkzeug.utils.redirect("/forum/%s/user/%d" % (slug(forum), partner.user_ids[0].id))
        return werkzeug.utils.redirect("/forum/%s" % slug(forum))

    @http.route(['/forum/user/<int:user_id>/avatar'], type='http', auth="public", website=True)
    def user_avatar(self, user_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        response = werkzeug.wrappers.Response()
        User = request.registry['res.users']
        Website = request.registry['website']
        user = User.browse(cr, SUPERUSER_ID, user_id, context=context)
        if not user.exists() or (user_id != request.session.uid and user.karma < 1):
            return Website._image_placeholder(response)
        return Website._image(cr, SUPERUSER_ID, 'res.users', user.id, 'image', response)

    @http.route(['/forum/<model("forum.forum"):forum>/user/<int:user_id>'], type='http', auth="public", website=True)
    def open_user(self, forum, user_id=0, **post):
        cr, uid, context = request.cr, request.uid, request.context
        User = request.registry['res.users']
        Post = request.registry['forum.post']
        Vote = request.registry['forum.post.vote']
        Activity = request.registry['mail.message']
        Followers = request.registry['mail.followers']
        Data = request.registry["ir.model.data"]

        user = User.browse(cr, SUPERUSER_ID, user_id, context=context)
        values = self._prepare_forum_values(forum=forum, **post)
        if not user.exists() or (user_id != request.session.uid and (not user.website_published or user.karma < 1)):
            return request.website.render("website_forum.private_profile", values)
        # questions and answers by user
        user_questions, user_answers = [], []
        user_post_ids = Post.search(
            cr, uid, [
                ('forum_id', '=', forum.id), ('create_uid', '=', user.id),
                '|', ('active', '=', False), ('active', '=', True)], context=context)
        user_posts = Post.browse(cr, uid, user_post_ids, context=context)
        for record in user_posts:
            if record.parent_id:
                user_answers.append(record)
            else:
                user_questions.append(record)

        # showing questions which user following
        obj_ids = Followers.search(cr, SUPERUSER_ID, [('res_model', '=', 'forum.post'), ('partner_id', '=', user.partner_id.id)], context=context)
        post_ids = [follower.res_id for follower in Followers.browse(cr, SUPERUSER_ID, obj_ids, context=context)]
        que_ids = Post.search(cr, uid, [('id', 'in', post_ids), ('forum_id', '=', forum.id), ('parent_id', '=', False)], context=context)
        followed = Post.browse(cr, uid, que_ids, context=context)

        #showing Favourite questions of user.
        fav_que_ids = Post.search(cr, uid, [('favourite_ids', '=', user.id), ('forum_id', '=', forum.id), ('parent_id', '=', False)], context=context)
        favourite = Post.browse(cr, uid, fav_que_ids, context=context)

        #votes which given on users questions and answers.
        data = Vote.read_group(cr, uid, [('post_id.forum_id', '=', forum.id), ('post_id.create_uid', '=', user.id)], ["vote"], groupby=["vote"], context=context)
        up_votes, down_votes = 0, 0
        for rec in data:
            if rec['vote'] == '1':
                up_votes = rec['vote_count']
            elif rec['vote'] == '-1':
                down_votes = rec['vote_count']
        total_votes = up_votes + down_votes

        #Votes which given by users on others questions and answers.
        post_votes = Vote.search(cr, uid, [('user_id', '=', user.id)], context=context)
        vote_ids = Vote.browse(cr, uid, post_votes, context=context)

        #activity by user.
        model, comment = Data.get_object_reference(cr, uid, 'mail', 'mt_comment')
        activity_ids = Activity.search(cr, uid, [('res_id', 'in', user_post_ids), ('model', '=', 'forum.post'), ('subtype_id', '!=', comment)], order='date DESC', limit=100, context=context)
        activities = Activity.browse(cr, uid, activity_ids, context=context)

        posts = {}
        for act in activities:
            posts[act.res_id] = True
        posts_ids = Post.browse(cr, uid, posts.keys(), context=context)
        posts = dict(map(lambda x: (x.id, (x.parent_id or x, x.parent_id and x or False)), posts_ids))

        post['users'] = 'True'

        values.update({
            'uid': uid,
            'user': user,
            'main_object': user,
            'searches': post,
            'questions': user_questions,
            'answers': user_answers,
            'followed': followed,
            'favourite': favourite,
            'total_votes': total_votes,
            'up_votes': up_votes,
            'down_votes': down_votes,
            'activities': activities,
            'posts': posts,
            'vote_post': vote_ids,
        })
        return request.website.render("website_forum.user_detail_full", values)

    @http.route('/forum/<model("forum.forum"):forum>/user/<model("res.users"):user>/edit', type='http', auth="user", website=True)
    def edit_profile(self, forum, user, **kwargs):
        country = request.registry['res.country']
        country_ids = country.search(request.cr, SUPERUSER_ID, [], context=request.context)
        countries = country.browse(request.cr, SUPERUSER_ID, country_ids, context=request.context)
        values = self._prepare_forum_values(forum=forum, searches=kwargs)
        values.update({
            'countries': countries,
            'notifications': self._get_notifications(),
        })
        return request.website.render("website_forum.edit_profile", values)

    @http.route('/forum/<model("forum.forum"):forum>/user/<model("res.users"):user>/save', type='http', auth="user", methods=['POST'], website=True)
    def save_edited_profile(self, forum, user, **kwargs):
        request.registry['res.users'].write(request.cr, request.uid, [user.id], {
            'name': kwargs.get('name'),
            'website': kwargs.get('website'),
            'email': kwargs.get('email'),
            'city': kwargs.get('city'),
            'country_id': int(kwargs.get('country')),
            'website_description': kwargs.get('description'),
        }, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/user/%d" % (slug(forum), user.id))

    # Badges
    # --------------------------------------------------

    @http.route('/forum/<model("forum.forum"):forum>/badge', type='http', auth="public", website=True)
    def badges(self, forum, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        Badge = request.registry['gamification.badge']
        badge_ids = Badge.search(cr, SUPERUSER_ID, [('challenge_ids.category', '=', 'forum')], context=context)
        badges = Badge.browse(cr, uid, badge_ids, context=context)
        badges = sorted(badges, key=lambda b: b.stat_count_distinct, reverse=True)
        values = self._prepare_forum_values(forum=forum, searches={'badges': True})
        values.update({
            'badges': badges,
        })
        return request.website.render("website_forum.badge", values)

    @http.route(['''/forum/<model("forum.forum"):forum>/badge/<model("gamification.badge"):badge>'''], type='http', auth="public", website=True)
    def badge_users(self, forum, badge, **kwargs):
        user_ids = [badge_user.user_id.id for badge_user in badge.owner_ids]
        users = request.registry['res.users'].browse(request.cr, SUPERUSER_ID, user_ids, context=request.context)
        values = self._prepare_forum_values(forum=forum, searches={'badges': True})
        values.update({
            'badge': badge,
            'users': users,
        })
        return request.website.render("website_forum.badge_user", values)

    # Messaging
    # --------------------------------------------------

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/comment/<model("mail.message"):comment>/convert_to_answer', type='http', auth="public", methods=['POST'], website=True)
    def convert_comment_to_answer(self, forum, post, comment, **kwarg):
        body = comment.body
        request.registry['mail.message'].unlink(request.cr, request.uid, [comment.id], context=request.context)
        question = post.parent_id if post.parent_id else post
        for answer in question.child_ids:
            if answer.create_uid.id == request.uid:
                return self.post_comment(forum, answer, comment=html2plaintext(body))
        return self.post_new(forum, question, content=body)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/convert_to_comment', type='http', auth="user", methods=['POST'], website=True)
    def convert_answer_to_comment(self, forum, post, **kwarg):
        values = {
            'comment': html2plaintext(post.content),
        }
        question = post.parent_id
        request.registry['forum.post'].unlink(request.cr, SUPERUSER_ID, [post.id], context=request.context)
        return self.post_comment(forum, question, **values)

    @http.route('/forum/<model("forum.forum"):forum>/post/<model("forum.post"):post>/comment/<model("mail.message"):comment>/delete', type='json', auth="user", website=True)
    def delete_comment(self, forum, post, comment, **kwarg):
        request.registry['mail.message'].unlink(request.cr, SUPERUSER_ID, [comment.id], context=request.context)
        return True
