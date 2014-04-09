# -*- coding: utf-8 -*-

import werkzeug.urls
import simplejson

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.addons.web import http
from openerp.tools import html2plaintext

from openerp.tools.translate import _
from datetime import datetime, timedelta
from openerp.addons.web.http import request

from dateutil.relativedelta import relativedelta
from openerp.addons.website.controllers.main import Website as controllers
from openerp.addons.website.models.website import slug
from openerp.addons.web.controllers.main import login_redirect

controllers = controllers()


class WebsiteForum(http.Controller):

    @http.route(['/forum'], type='http', auth="public", website=True, multilang=True)
    def forum(self, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        Forum = request.registry['website.forum']
        obj_ids = Forum.search(cr, uid, [], context=context)
        forums = Forum.browse(cr, uid, obj_ids, context=context)
        return request.website.render("website_forum.forum_index", {'forums': forums})

    @http.route('/forum/new', type='http', auth="user", multilang=True, website=True)
    def forum_create(self, forum_name="New Forum", **kwargs):
        forum_id = request.registry['website.forum'].create(request.cr, request.uid, {
            'name': forum_name,
        }, context=request.context)
        return request.redirect("/forum/%s" % slug(forum_id))

    @http.route(['/forum/<model("website.forum"):forum>',
                 '/forum/<model("website.forum"):forum>/page/<int:page>',
                 '/forum/<model("website.forum"):forum>/tag/<model("website.forum.tag"):tag>/questions'
                 ], type='http', auth="public", website=True, multilang=True)
    def questions(self, forum, tag='', page=1, filters='', sorting='', search='', **searches):
        cr, uid, context = request.cr, request.uid, request.context
        Forum = request.registry['website.forum.post']
        user = request.registry['res.users'].browse(cr, uid, uid, context=context)

        order = "id desc"

        domain = [('forum_id', '=', forum.id), ('parent_id', '=', False)]
        if search:
            domain += ['|', ('name', 'ilike', search), ('content', 'ilike', search)]

        #filter questions for tag.
        if tag:
            if not filters:
                filters = 'tag'
            domain += [('tag_ids', 'in', tag.id)]

        if not filters:
            filters = 'all'
        if filters == 'unanswered':
            domain += [ ('child_ids', '=', False) ]
        if filters == 'followed':
            domain += [ ('message_follower_ids', '=', user.partner_id.id) ]

        # Note: default sorting should be based on last activity
        if not sorting or sorting == 'date':
            sorting = 'date'
            order = 'write_date desc'
        if sorting == 'answered':
            order = 'child_count desc'
        if sorting == 'vote':
            order = 'vote_count desc'

        step = 10
        question_count = Forum.search(cr, uid, domain, count=True, context=context)
        pager = request.website.pager(url="/forum/%s" % slug(forum), total=question_count, page=page, step=step, scope=10)

        obj_ids = Forum.search(cr, uid, domain, limit=step, offset=pager['offset'], order=order, context=context)
        question_ids = Forum.browse(cr, uid, obj_ids, context=context)

        values = {
            'uid': request.session.uid,
            'total_questions': question_count,
            'question_ids': question_ids,
            'notifications': self._get_notifications(),
            'forum': forum,
            'pager': pager,
            'tag': tag,
            'filters': filters,
            'sorting': sorting,
            'search': search,
            'searches': searches,
        }

        return request.website.render("website_forum.index", values)

    def _get_notifications(self, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        Message = request.registry['mail.message']
        BadgeUser = request.registry['gamification.badge.user']
        #notification to user.
        badgeuser_ids = BadgeUser.search(cr, uid, [('user_id', '=', uid)], context=context)
        notification_ids = Message.search(cr, uid, [('res_id', 'in', badgeuser_ids), ('model', '=', 'gamification.badge.user'), ('to_read', '=', True)], context=context)
        notifications = Message.browse(cr, uid, notification_ids, context=context)
        user = request.registry['res.users'].browse(cr, uid, uid, context=context)
        return {"user": user, "notifications": notifications}

    @http.route('/forum/notification_read', type='json', auth="user", multilang=True, methods=['POST'], website=True)
    def notification_read(self, **kwarg):
        request.registry['mail.message'].set_message_read(request.cr, request.uid, [int(kwarg.get('notification_id'))], read=True, context=request.context)
        return True

    @http.route(['/forum/<model("website.forum"):forum>/faq'], type='http', auth="public", website=True, multilang=True)
    def faq(self, forum, **post):
        values = { 
            'searches': {},
            'forum':forum,
            'notifications': self._get_notifications(),
        }
        return request.website.render("website_forum.faq", values)

    @http.route(['/forum/<model("website.forum"):forum>/question/<model("website.forum.post"):question>'], type='http', auth="public", website=True, multilang=True)
    def question(self, forum, question, **post):
        cr, uid, context = request.cr, request.uid, request.context

        #maintain total views on post.
        # Statistics = request.registry['website.forum.post.statistics']
        # post_obj = request.registry['website.forum.post']
        # if request.session.uid:
        #     view_ids = Statistics.search(cr, uid, [('user_id', '=', request.session.uid), ('post_id', '=', question.id)], context=context)
        #     if not view_ids:
        #         Statistics.create(cr, SUPERUSER_ID, {'user_id': request.session.uid, 'post_id': question.id }, context=context)
        # else:
        #     request.session[request.session_id] = request.session.get(request.session_id, [])
        #     if not (question.id in request.session[request.session_id]):
        #         request.session[request.session_id].append(question.id)
        #         post_obj._set_view_count(cr, SUPERUSER_ID, [question.id], 'views', 1, {}, context=context)

        #Check that user have answered question or not.
        answer_done = False
        for answer in question.child_ids:
            if answer.user_id.id == request.uid:
                answer_done = True

        #Check that user is following question or not
        partner_id = request.registry['res.users'].browse(cr, uid, request.uid, context=context).partner_id.id
        message_follower_ids = [follower.id for follower in question.message_follower_ids]
        following = True if partner_id in message_follower_ids else False

        filters = 'question'
        user = request.registry['res.users'].browse(cr, uid, uid, context=None)
        values = {
            'question': question,
            'question_data': True,
            'notifications': self._get_notifications(),
            'searches': post,
            'filters': filters,
            'following': following,
            'answer_done': answer_done,
            'reversed': reversed,
            'forum': forum,
            'user': user,
        }
        return request.website.render("website_forum.post_description_full", values)

    @http.route(['/forum/<model("website.forum"):forum>/comment'], type='http', auth="public", methods=['POST'], website=True)
    def post_comment(self, forum, post_id, **kwargs):
        if not request.session.uid:
            return login_redirect()
        cr, uid, context = request.cr, request.uid, request.context
        if kwargs.get('comment'):
            user = request.registry['res.users'].browse(cr, SUPERUSER_ID, uid, context=context)
            group_ids = user.groups_id
            group_id = request.registry["ir.model.data"].get_object_reference(cr, uid, 'website_mail', 'group_comment')[1]
            if group_id in [group.id for group in group_ids]:
                Post = request.registry['website.forum.post']
                Post.message_post(
                    cr, uid, int(post_id),
                    body=kwargs.get('comment'),
                    type='comment',
                    subtype='mt_comment',
                    content_subtype='plaintext',
                    author_id=user.partner_id.id,
                    context=dict(context, mail_create_nosubcribe=True))

        post = request.registry['website.forum.post'].browse(cr, uid, int(post_id), context=context)
        question_id = post.parent_id.id if post.parent_id else post.id
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),question_id))

    @http.route(['/forum/<model("website.forum"):forum>/user/<model("res.users"):user>'], type='http', auth="public", website=True, multilang=True)
    def open_user(self, forum, user, **post):
        cr, uid, context = request.cr, request.uid, request.context
        User = request.registry['res.users']
        Post = request.registry['website.forum.post']
        Vote = request.registry['website.forum.post.vote']
        Activity = request.registry['mail.message']
        Followers = request.registry['mail.followers']
        Data = request.registry["ir.model.data"]

        #questions and answers by user.
        user_questions, user_answers = [], []
        user_post_ids = Post.search(cr, uid, [('forum_id', '=', forum.id), ('user_id', '=', user.id),
                                             '|', ('active', '=', False), ('active', '=', True)], context=context)
        user_posts = Post.browse(cr, uid, user_post_ids, context=context)
        for record in user_posts:
            if record.parent_id:
                user_answers.append(record)
            else:
                user_questions.append(record)

        #showing questions which user following
        obj_ids = Followers.search(cr, SUPERUSER_ID, [('res_model', '=', 'website.forum.post'),('partner_id' , '=' , user.partner_id.id)], context=context)
        post_ids = [follower.res_id for follower in Followers.browse(cr, SUPERUSER_ID, obj_ids, context=context)]
        que_ids = Post.search(cr, uid, [('id', 'in', post_ids), ('forum_id', '=', forum.id), ('parent_id', '=', False)], context=context)
        followed = Post.browse(cr, uid, que_ids, context=context)

        #showing Favourite questions of user.
        fav_que_ids = Post.search(cr, uid, [('favourite_ids', '=', user.id), ('forum_id', '=', forum.id), ('parent_id', '=', False)], context=context)
        favourite = Post.browse(cr, uid, fav_que_ids, context=context)

        #votes which given on users questions and answers.
        data = Vote.read_group(cr, uid, [('post_id.forum_id', '=', forum.id), ('post_id.user_id', '=', user.id)], ["vote"], groupby=["vote"], context=context)
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
        activity_ids = Activity.search(cr, uid, [('res_id', 'in', user_post_ids), ('model', '=', 'website.forum.post'), '|', ('subtype_id', '!=', comment), ('subtype_id', '=', False)], context=context)
        activities = Activity.browse(cr, uid, activity_ids, context=context)

        posts = {}
        for act in activities:
            posts[act.res_id] = True
        posts_ids = Post.browse(cr, uid, posts.keys(), context=context)
        posts = dict(map(lambda x: (x.id, (x.parent_id or x, x.parent_id and x or False)), posts_ids))

        post['users'] = 'True'

        values = {
            'uid': uid,
            'user': user,
            'main_object': user,
            'searches': post,
            'forum': forum,
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
            'notifications': self._get_notifications(),
        }
        return request.website.render("website_forum.user_detail_full", values)

    @http.route(['/forum/<model("website.forum"):forum>/ask'], type='http', auth="public", website=True, multilang=True)
    def question_ask(self, forum, **post):
        if not request.session.uid:
            return login_redirect()
        user = request.registry['res.users'].browse(request.cr, request.uid, request.uid, context=request.context)
        values = {
            'searches': {},
            'forum': forum,
            'user': user,
            'ask_question': True,
            'notifications': self._get_notifications(),
        }
        return request.website.render("website_forum.ask_question", values)

    @http.route('/forum/<model("website.forum"):forum>/question/ask', type='http', auth="user", multilang=True, methods=['POST'], website=True)
    def register_question(self, forum, **question):
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context)

        Tag = request.registry['website.forum.tag']
        question_tags = []
        if question.get('question_tags').strip('[]'):
            tags = question.get('question_tags').strip('[]').replace('"','').split(",")
            for tag in tags:
                tag_ids = Tag.search(cr, uid, [('name', '=', tag)], context=context)
                if tag_ids:
                    question_tags.append((4,tag_ids[0]))
                else:
                    question_tags.append((0,0,{'name' : tag,'forum_id' : forum.id}))
    
        new_question_id = request.registry['website.forum.post'].create(
            request.cr, request.uid, {
                'user_id': uid,
                'forum_id': forum.id,
                'name': question.get('question_name'),
                'content': question.get('content'),
                'tag_idss' : question_tags,
                'state': 'active',
                'active': True,
            }, context=create_context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),new_question_id))

    @http.route('/forum/<model("website.forum"):forum>/question/postanswer', type='http', auth="public", multilang=True, methods=['POST'], website=True)
    def post_answer(self, forum , post_id, **question):
        if not request.session.uid:
            return login_redirect()

        cr, uid, context = request.cr, request.uid, request.context
        request.registry['res.users'].write(cr, SUPERUSER_ID, uid, {'forum': True}, context=context)

        create_context = dict(context)
        new_question_id = request.registry['website.forum.post'].create(
            cr, uid, {
                'forum_id': forum.id,
                'user_id': uid,
                'parent_id': post_id,
                'content': question.get('content'),
                'state': 'active',
                'active': True,
            }, context=create_context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),post_id))

    @http.route(['/forum/<model("website.forum"):forum>/question/<model("website.forum.post"):question>/editanswer']
                , type='http', auth="user", website=True, multilang=True)
    def edit_answer(self, forum, question, **kwargs):
        for record in question.child_ids:
            if record.user_id.id == request.uid:
                answer = record
        return werkzeug.utils.redirect("/forum/%s/question/%s/edit/%s" % (slug(forum), question.id, answer.id))
 
    @http.route(['/forum/<model("website.forum"):forum>/edit/question/<model("website.forum.post"):question>',
                 '/forum/<model("website.forum"):forum>/question/<model("website.forum.post"):question>/edit/<model("website.forum.post"):answer>']
                , type='http', auth="user", website=True, multilang=True)
    def edit_post(self, forum, question, answer=None, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context

        history_obj = request.registry['website.forum.post.history']
        User = request.registry['res.users']
        User.write(cr, SUPERUSER_ID, uid, {'forum': True}, context=context)
        user = User.browse(cr, uid, uid, context=context)

        post_id = answer.id if answer else question.id
        history_ids = history_obj.search(cr, uid, [('post_id', '=', post_id)], order = "id desc", context=context)
        post_history = history_obj.browse(cr, uid, history_ids, context=context)

        tags = ""
        for tag_name in question.tags:
            tags += tag_name.name + ","

        values = {
            'question': question,
            'user': user,
            'tags': tags,
            'answer': answer,
            'is_answer': True if answer else False,
            'notifications': self._get_notifications(),
            'forum': forum,
            'post_history': post_history,
            'searches': kwargs
        }
        return request.website.render("website_forum.edit_post", values)

    @http.route('/forum/<model("website.forum"):forum>/post/save', type='http', auth="user", multilang=True, methods=['POST'], website=True)
    def save_edited_post(self, forum, **post):
        cr, uid, context = request.cr, request.uid, request.context
        request.registry['res.users'].write(cr, SUPERUSER_ID, uid, {'forum': True}, context=context)
        vals = {
            'content': post.get('content'),
        }
        question_tags = []
        if post.get('question_tag').strip('[]'):
            Tag = request.registry['website.forum.tag']
            tags = post.get('question_tag').strip('[]').replace('"','').split(",")
            for tag in tags:
                tag_ids = Tag.search(cr, uid, [('name', '=', tag)], context=context)
                if tag_ids:
                    question_tags += tag_ids
                else:
                    new_tag = Tag.create(cr, uid, {'name' : tag,'forum_id' : forum.id}, context=context)
                    question_tags.append(new_tag)
        vals.update({'tag_ids': [(6, 0, question_tags)], 'name': post.get('question_name')})

        post_id = post.get('answer_id') if post.get('answer_id') else post.get('question_id')
        new_question_id = request.registry['website.forum.post'].write( cr, uid, [int(post_id)], vals, context=context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),post.get('question_id')))

    @http.route(['/forum/<model("website.forum"):forum>/tag'], type='http', auth="public", website=True, multilang=True)
    def tags(self, forum, page=1, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        Tag = request.registry['website.forum.tag']
        obj_ids = Tag.search(cr, uid, [('forum_id', '=', forum.id)], limit=None, context=context)
        tags = Tag.browse(cr, uid, obj_ids, context=context)
        values = {
            'tags': tags,
            'notifications': self._get_notifications(),
            'forum': forum,
            'searches': {'tags': True}
        }
        return request.website.render("website_forum.tag", values)

    @http.route(['/forum/<model("website.forum"):forum>/badge'], type='http', auth="public", website=True, multilang=True)
    def badges(self, forum, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        Badge = request.registry['gamification.badge']
        badge_ids = Badge.search(cr, uid, [('level', '!=', False)], context=context)
        badges = Badge.browse(cr, uid, badge_ids, context=context)
        values = {
            'badges': badges,
            'notifications': {},
            'forum': forum,
            'searches': {'badges': True}
        }
        return request.website.render("website_forum.badge", values)

    @http.route(['/forum/<model("website.forum"):forum>/badge/<model("gamification.badge"):badge>'], type='http', auth="public", website=True, multilang=True)
    def badge_users(self, forum, badge, **kwargs):
        users = [badge_user.user_id for badge_user in badge.owner_ids]
        kwargs['badges'] = 'True'

        values = {
            'badge': badge,
            'notifications': {},
            'users': users,
            'forum': forum,
            'searches': kwargs
        }
        return request.website.render("website_forum.badge_user", values)

    @http.route(['/forum/<model("website.forum"):forum>/users', '/forum/users/page/<int:page>'], type='http', auth="public", website=True, multilang=True)
    def users(self, forum, page=1, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        User = request.registry['res.users']

        step = 30
        tag_count = User.search(cr, uid, [('karma', '>', 1)], count=True, context=context)
        pager = request.website.pager(url="/forum/users", total=tag_count, page=page, step=step, scope=30)

        obj_ids = User.search(cr, uid, [('karma', '>', 1)], limit=step, offset=pager['offset'], context=context)
        users = User.browse(cr, uid, obj_ids, context=context)
        searches['users'] = 'True'

        values = {
            'users': users,
            'notifications': self._get_notifications(),
            'pager': pager,
            'forum': forum,
            'searches': searches,
        }

        return request.website.render("website_forum.users", values)

    @http.route('/forum/post_vote', type='json', auth="public", multilang=True, methods=['POST'], website=True)
    def post_vote(self, **post):
        if not request.session.uid:
            return {'error': 'anonymous_user'}
        cr, uid, context, post_id = request.cr, request.uid, request.context, int(post.get('post_id'))
        return request.registry['website.forum.post'].vote(cr, uid, [post_id], post.get('vote'), context)

    @http.route('/forum/post_delete', type='json', auth="user", multilang=True, methods=['POST'], website=True)
    def delete_answer(self, **kwarg):
        request.registry['website.forum.post'].unlink(request.cr, request.uid, [int(kwarg.get('post_id'))], context=request.context)
        return True

    @http.route('/forum/<model("website.forum"):forum>/delete/question/<model("website.forum.post"):post>', type='http', auth="user", multilang=True, website=True)
    def delete_question(self, forum, post, **kwarg):
        #instead of unlink record just change 'active' to false so user can undelete it.
        request.registry['website.forum.post'].write( request.cr, request.uid, [post.id], {
            'active': False,
        }, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),post.id))

    @http.route('/forum/<model("website.forum"):forum>/undelete/question/<model("website.forum.post"):post>', type='http', auth="user", multilang=True, website=True)
    def undelete_question(self, forum, post, **kwarg):
        request.registry['website.forum.post'].write( request.cr, request.uid, [post.id], {
            'active': True,
        }, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),post.id))

    @http.route('/forum/message_delete', type='json', auth="user", multilang=True, methods=['POST'], website=True)
    def delete_comment(self, **kwarg):
        request.registry['mail.message'].unlink(request.cr, SUPERUSER_ID, [int(kwarg.get('message_id'))], context=request.context)
        return True

    @http.route('/forum/selecthistory', type='json', auth="user", multilang=True, methods=['POST'], website=True)
    def post_history(self, **kwarg):
        cr, uid, context = request.cr, request.uid, request.context
        post_history = request.registry['website.forum.post.history'].browse(cr, uid, int(kwarg.get('history_id')), context=context)
        tags = ""
        for tag_name in post_history.tags:
            tags += tag_name.name + ","
        data = {
            'name': post_history.post_name,
            'content': post_history.content,
            'tags': tags,
        }
        return data

    @http.route('/forum/correct_answer', type='json', auth="public", multilang=True, methods=['POST'], website=True)
    def correct_answer(self, **kwarg):
        cr, uid, context = request.cr, request.uid, request.context
        if not request.session.uid:
            return {'error': 'anonymous_user'}

        Post = request.registry['website.forum.post']
        post = Post.browse(cr, uid, int(kwarg.get('post_id')), context=context)
        user = request.registry['res.users'].browse(cr, uid, uid, context=None)

        #if user have not access to accept answer then reise warning
        if not (post.parent_id.user_id.id == uid or user.karma >= 500):
            return {'error': 'user'}

        #Note: only one answer can be right.
        correct = False if post.correct else True
        for child in post.parent_id.child_ids:
            if child.correct and child.id != post.id:
                Post.write( cr, uid, [child.id], { 'correct': False }, context=context)
        Post.write( cr, uid, [post.id, post.parent_id.id], { 'correct': correct }, context=context)
        return correct

    @http.route('/forum/favourite_question', type='json', auth="user", multilang=True, methods=['POST'], website=True)
    def favourite_question(self, **kwarg):
        cr, uid, context = request.cr, request.uid, request.context
        Post = request.registry['website.forum.post']
        post = Post.browse(cr, uid, int(kwarg.get('post_id')), context=context)
        favourite = False if post.user_favourite else True
        favourite_ids = [(4, uid)]
        if post.user_favourite:
            favourite_ids = [(3, uid)]
        Post.write( cr, uid, [post.id], { 'favourite_ids': favourite_ids }, context=context)
        return favourite

    @http.route('/forum/<model("website.forum"):forum>/close/question/<model("website.forum.post"):post>', type='http', auth="user", multilang=True, website=True)
    def close_question(self, forum, post, **kwarg):
        cr, uid, context = request.cr, request.uid, request.context
        Reason = request.registry['website.forum.post.reason']
        reason_ids = Reason.search(cr, uid, [], context=context)
        reasons = Reason.browse(cr, uid, reason_ids, context)

        values = {
            'post': post,
            'forum': forum,
            'searches': kwarg,
            'reasons': reasons,
            'notifications': self._get_notifications(),
        }
        return request.website.render("website_forum.close_question", values)

    @http.route('/forum/<model("website.forum"):forum>/question/close', type='http', auth="user", multilang=True, methods=['POST'], website=True)
    def close(self, forum, **post):
        request.registry['website.forum.post'].write( request.cr, request.uid, [int(post.get('post_id'))], {
            'state': 'close',
            'closed_by': request.uid,
            'closed_date': datetime.today().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),
            'reason_id': post.get('reason'),
        }, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),post.get('post_id')))

    @http.route('/forum/<model("website.forum"):forum>/reopen/question/<model("website.forum.post"):post>', type='http', auth="user", multilang=True, website=True)
    def reopen(self, forum, post, **kwarg):
        request.registry['website.forum.post'].write( request.cr, request.uid, [post.id], {
            'state': 'active',
        }, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),post.id))

    @http.route('/forum/<model("website.forum"):forum>/edit/profile/<model("res.users"):user>', type='http', auth="user", multilang=True, website=True)
    def edit_profile(self, forum, user, **kwarg):
        cr,context = request.cr, request.context
        country = request.registry['res.country']
        country_ids = country.search(cr, SUPERUSER_ID, [], context=context)
        countries = country.browse(cr, SUPERUSER_ID, country_ids, context)
        values = {
            'user': user,
            'forum': forum,
            'searches': kwarg,
            'countries': countries,
            'notifications': self._get_notifications(),
        }
        return request.website.render("website_forum.edit_profile", values)

    @http.route('/forum/<model("website.forum"):forum>/save/profile', type='http', auth="user", multilang=True, website=True)
    def save_edited_profile(self, forum, **post):
        cr, uid, context = request.cr, request.uid, request.context
        user = request.registry['res.users'].browse(cr, uid, int(post.get('user_id')),context=context)
        request.registry['res.partner'].write( cr, uid, [user.partner_id.id], {
            'name': post.get('name'),
            'website': post.get('website'),
            'email': post.get('email'),
            'city': post.get('city'),
            'country_id': post.get('country'),
            'website_description': post.get('description'), 
        }, context=context)
        return werkzeug.utils.redirect("/forum/%s/user/%s" % (slug(forum),post.get('user_id')))

    @http.route('/forum/<model("website.forum"):forum>/post/<model("website.forum.post"):post>/commet/<model("mail.message"):comment>/converttoanswer', type='http', auth="public", multilang=True, website=True)
    def convert_to_answer(self, forum, post, comment, **kwarg):
        values = {
            'content': comment.body,
        }
        request.registry['mail.message'].unlink(request.cr, request.uid, [comment.id], context=request.context)
        return self.post_answer(forum, post.parent_id and post.parent_id.id or post.id, **values)

    @http.route('/forum/<model("website.forum"):forum>/post/<model("website.forum.post"):post>/converttocomment', type='http', auth="user", multilang=True, website=True)
    def convert_to_comment(self, forum, post, **kwarg):
        values = {
            'comment': html2plaintext(post.content),
        }
        question = post.parent_id.id
        request.registry['website.forum.post'].unlink(request.cr, SUPERUSER_ID, [post.id], context=request.context)
        return self.post_comment(forum, question, **values)

    @http.route('/forum/get_tags', type='http', auth="public", multilang=True, methods=['GET'], website=True)
    def tag_read(self, **kwarg):
        tags = request.registry['website.forum.tag'].search_read(request.cr, request.uid, [], ['name'], context=request.context)
        data = [tag['name'] for tag in tags]
        return simplejson.dumps(data)

    @http.route('/forum/<model("website.forum"):forum>/question/<model("website.forum.post"):post>/subscribe', type='http', auth="public", multilang=True, website=True)
    def subscribe(self, forum, post, **kwarg):
        cr, uid, context = request.cr, request.uid, request.context
        if not request.session.uid:
            return login_redirect()
        partner_id = request.registry['res.users'].browse(cr, uid, request.uid, context=context).partner_id.id
        post_ids = [child.id for child in post.child_ids]
        post_ids.append(post.id)
        request.registry['website.forum.post'].message_subscribe( cr, uid, post_ids, [partner_id], context=context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),post.id))

    @http.route('/forum/<model("website.forum"):forum>/question/<model("website.forum.post"):post>/unsubscribe', type='http', auth="user", multilang=True, website=True)
    def unsubscribe(self, forum, post, **kwarg):
        cr, uid, context = request.cr, request.uid, request.context
        partner_id = request.registry['res.users'].browse(cr, uid, request.uid, context=context).partner_id.id
        post_ids = [child.id for child in post.child_ids]
        post_ids.append(post.id)
        request.registry['website.forum.post'].message_unsubscribe( cr, uid, post_ids, [partner_id], context=context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),post.id))
