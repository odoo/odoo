# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import werkzeug.urls

from openerp import tools
from openerp import SUPERUSER_ID
from openerp.addons.web import http

from openerp.tools.translate import _
from datetime import datetime, timedelta
from openerp.addons.web.http import request

from dateutil.relativedelta import relativedelta
from openerp.addons.website.controllers.main import Website as controllers
from openerp.addons.website.models.website import slug

controllers = controllers()

class website_forum(http.Controller):

    @http.route(['/forum/'], type='http', auth="public", website=True, multilang=True)
    def forum(self, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        Forum = request.registry['website.forum']
        obj_ids = Forum.search(cr, uid, [], context=context)
        forums = Forum.browse(cr, uid, obj_ids, context=context)
        values = { 'forums': forums }
        return request.website.render("website_forum.forum_index", values)

    @http.route('/forum/add_forum/', type='http', auth="user", multilang=True, website=True)
    def add_forum(self, forum_name="New Forum", **kwargs):
        forum_id = request.registry['website.forum'].create(request.cr, request.uid, {
            'name': forum_name,
        }, context=request.context)
        return request.redirect("/forum/%s" % forum_id)

    def _get_notifications(self, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        Message = request.registry['mail.message']
        BadgeUser = request.registry['gamification.badge.user']
        #notification to user.
        badgeuser_ids = BadgeUser.search(cr, uid, [('user_id', '=', uid)], context=context)
        notification_ids = Message.search(cr, uid, [('res_id', 'in', badgeuser_ids), ('model', '=', 'gamification.badge.user'), ('to_read', '=', True)], context=context)
        return Message.browse(cr, uid, notification_ids, context=context)

    @http.route(['/forum/<model("website.forum"):forum>', '/forum/<model("website.forum"):forum>/page/<int:page>'], type='http', auth="public", website=True, multilang=True)
    def questions(self, forum, page=1, filters='', sorting='', **searches):
        cr, uid, context = request.cr, request.uid, request.context
        Forum = request.registry['website.forum.post']
        domain = [('forum_id', '=', forum.id), ('parent_id', '=', False)]
        order = "id desc"

        search = searches.get('search',False)
        if search:
            domain += ['|',
                ('name', 'ilike', search),
                ('content', 'ilike', search)]

        if not filters:
            filters = 'all'
        if filters == 'unanswered':
            domain += [ ('child_ids', '=', False) ]
        #TODO: update domain to show followed questions of user
        if filters == 'followed':
            domain += [ ('user_id', '=', uid) ]

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
        pager = request.website.pager(url="/forum/%s/" % slug(forum), total=question_count, page=page, step=step, scope=10)

        obj_ids = Forum.search(cr, uid, domain, limit=step, offset=pager['offset'], order=order, context=context)
        question_ids = Forum.browse(cr, uid, obj_ids, context=context)

        values = {
            'uid': uid,
            'total_questions': question_count,
            'question_ids': question_ids,
            'notifications': self._get_notifications(),
            'forum': forum,
            'pager': pager,
            'filters': filters,
            'sorting': sorting,
            'searches': searches,
        }

        return request.website.render("website_forum.index", values)

    @http.route('/forum/notification_read/', type='json', auth="user", multilang=True, methods=['POST'], website=True)
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

    @http.route(['/forum/<model("website.forum"):forum>/ask'], type='http', auth="public", website=True, multilang=True)
    def question_ask(self, forum, **post):
        values = {
            'searches': {},
            'forum': forum,
            'notifications': self._get_notifications(),
        }
        return request.website.render("website_forum.ask_question", values)

    @http.route(['/forum/<model("website.forum"):forum>/question/<model("website.forum.post"):question>'], type='http', auth="public", website=True, multilang=True)
    def question(self, forum, question, **post):
        answer_done = False
        for answer in question.child_ids:
            if answer.user_id.id == request.uid:
                answer_done = True
        filters = 'question'
        values = {
            'question': question,
            'notifications': self._get_notifications(),
            'searches': post,
            'filters': filters,
            'answer_done': answer_done,
            'reversed': reversed,
            'forum': forum,
        }
        return request.website.render("website_forum.post_description_full", values)

    @http.route(['/forum/<model("website.forum"):forum>/comment'], type='http', auth="public", methods=['POST'], website=True)
    def post_comment(self, forum, post_id, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        if kwargs.get('comment'):
            user = request.registry['res.users'].browse(cr, SUPERUSER_ID, uid, context=context)
            group_ids = user.groups_id
            group_id = request.registry["ir.model.data"].get_object_reference(cr, uid, 'website_mail', 'group_comment')[1]
            if group_id in [group.id for group in group_ids]:
                Post = request.registry['website.forum.post']
                Post.check_access_rights(cr, uid, 'read')
                Post.message_post(
                    cr, SUPERUSER_ID, int(post_id),
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
        Data = request.registry["ir.model.data"]

        #questions asked by user.
        question_ids = Post.search(cr, uid, [('forum_id', '=', forum.id), ('user_id', '=', user.id), ('parent_id', '=', False)], context=context)
        user_questions = Post.browse(cr, uid, question_ids, context=context)

        #showing questions in which user answered
        obj_ids = Post.search(cr, uid, [('forum_id', '=', forum.id), ('user_id', '=', user.id), ('parent_id', '!=', False)], context=context)
        user_answers = Post.browse(cr, uid, obj_ids, context=context)
        answers = [answer.parent_id for answer in user_answers]

        #votes which given on users questions and answers.
        total_votes = Vote.search(cr, uid, [('post_id.forum_id', '=', forum.id), ('post_id.user_id', '=', user.id)], count=True, context=context)
        up_votes = Vote.search(cr, uid, [('post_id.forum_id', '=', forum.id), ('post_id.user_id', '=', user.id), ('vote', '=', '1')], count=True, context=context)
        down_votes = Vote.search(cr, uid, [('post_id.forum_id', '=', forum.id), ('post_id.user_id', '=', user.id), ('vote', '=', '-1')], count=True, context=context)

        #Votes which given by users on others questions and answers.
        post_votes = Vote.search(cr, uid, [('user_id', '=', user.id)], context=context)
        vote_ids = Vote.browse(cr, uid, post_votes, context=context)

        #activity by user.
        user_post_ids = question_ids + obj_ids
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
            'answers': answers,
            'total_votes': total_votes,
            'up_votes': up_votes,
            'down_votes': down_votes,
            'activities': activities,
            'posts': posts,
            'vote_post': vote_ids,
            'notifications': self._get_notifications(),
        }
        return request.website.render("website_forum.user_detail_full", values)

    @http.route('/forum/<model("website.forum"):forum>/question/ask/', type='http', auth="user", multilang=True, methods=['POST'], website=True)
    def register_question(self, forum, **question):
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context)
        new_question_id = request.registry['website.forum.post'].create(
            request.cr, request.uid, {
                'user_id': uid,
                'forum_id': forum.id,
                'name': question.get('question_name'),
                'content': question.get('question_content'),
                #'tags' : question.get('question_tags'),
                'state': 'active',
                'active': True,
            }, context=create_context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),new_question_id))

    @http.route('/forum/<model("website.forum"):forum>/question/postanswer/', type='http', auth="user", multilang=True, methods=['POST'], website=True)
    def post_answer(self, forum ,post_id, **question):
        cr, uid, context = request.cr, request.uid, request.context
        request.registry['res.users'].write(cr, uid, uid, {'forum': True}, context=context)

        create_context = dict(context)
        new_question_id = request.registry['website.forum.post'].create(
            request.cr, request.uid, {
                'forum_id': forum.id,
                'parent_id': post_id,
                'content': question.get('answer_content'),
                'state': 'active',
                'active': True,
            }, context=create_context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),post_id))

    @http.route(['/forum/<model("website.forum"):forum>/question/<model("website.forum.post"):post>/editanswer'], type='http', auth="user", website=True, multilang=True)
    def edit_answer(self, forum, post, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        request.registry['res.users'].write(cr, uid, uid, {'forum': True}, context=context)
        for answer in post.child_ids:
            if answer.user_id.id == request.uid:
                post_answer = answer
        values = {
            'post': post,
            'post_answer': post_answer,
            'notifications': self._get_notifications(),
            'forum': forum,
            'searches': kwargs
        }
        return request.website.render("website_forum.edit_answer", values)

    @http.route('/forum/<model("website.forum"):forum>/question/saveanswer/', type='http', auth="user", multilang=True, methods=['POST'], website=True)
    def save_edited_answer(self, forum, **post):
        cr, uid, context = request.cr, request.uid, request.context
        request.registry['res.users'].write(cr, uid, uid, {'forum': True}, context=context)
        answer_id = int(post.get('answer_id'))
        new_question_id = request.registry['website.forum.post'].write( cr, uid, [answer_id], {
                'content': post.get('answer_content'),
            }, context=context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),post.get('post_id')))

    @http.route(['/forum/<model("website.forum"):forum>/tag/<model("website.forum.tag"):tag>'], type='http', auth="public", website=True, multilang=True)
    def tag_questions(self, forum, tag, page=1, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        Post = request.registry['website.forum.post']
        obj_ids = Post.search(cr, uid, [('forum_id', '=', forum.id), ('tags', '=', tag.id)], context=context)
        question_ids = Post.browse(cr, uid, obj_ids, context=context)
        pager = request.website.pager(url="/forum/%s/tag" % slug(forum), total=len(obj_ids), page=page, step=10, scope=10)
        kwargs['tags'] = 'True'

        values = {
            'question_ids': question_ids,
            'notifications': self._get_notifications(),
            'pager': pager,
            'forum': forum,
            'searches': kwargs
        }
        return request.website.render("website_forum.index", values)

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
            'notifications': [],
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
            'notifications': [],
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
        tag_count = User.search(cr, uid, [('forum','=',True)], count=True, context=context)
        pager = request.website.pager(url="/forum/users/", total=tag_count, page=page, step=step, scope=30)

        obj_ids = User.search(cr, uid, [('forum','=',True)], limit=step, offset=pager['offset'], context=context)
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

    @http.route('/forum/post_vote/', type='json', auth="user", multilang=True, methods=['POST'], website=True)
    def post_vote(self, **post):
        cr, uid, context, post_id = request.cr, request.uid, request.context, int(post.get('post_id'))
        Vote = request.registry['website.forum.post.vote']
        return Vote.vote(cr, uid, post_id, post.get('vote'), context)

    @http.route('/forum/post_delete/', type='json', auth="user", multilang=True, methods=['POST'], website=True)
    def delete_answer(self, **kwarg):
        request.registry['website.forum.post'].unlink(request.cr, request.uid, [int(kwarg.get('post_id'))], context=request.context)
        return True

    @http.route('/forum/<model("website.forum"):forum>/delete/question/<model("website.forum.post"):post>', type='http', auth="user", multilang=True, website=True)
    def delete_question(self, forum, post, **kwarg):
        request.registry['website.forum.post'].unlink(request.cr, request.uid, [post.id], context=request.context)
        return werkzeug.utils.redirect("/forum/%s/" % (slug(forum)))

    @http.route('/forum/message_delete/', type='json', auth="user", multilang=True, methods=['POST'], website=True)
    def delete_comment(self, **kwarg):
        request.registry['mail.message'].unlink(request.cr, request.uid, [int(kwarg.get('message_id'))], context=request.context)
        return True

    @http.route('/forum/<model("website.forum"):forum>/edit/question/<model("website.forum.post"):post>', type='http', auth="user", multilang=True, website=True)
    def edit_question(self, forum, post, **kwarg):
        values = {
            'post': post,
            'forum': forum,
            'searches': kwarg,
            'notifications': self._get_notifications(),
        }
        return request.website.render("website_forum.edit_question", values)

    @http.route('/forum/<model("website.forum"):forum>/question/savequestion/', type='http', auth="user", multilang=True, methods=['POST'], website=True)
    def save_edited_question(self, forum, **post):
        request.registry['website.forum.post'].write( request.cr, request.uid, [int(post.get('post_id'))], {
            'content': post.get('answer_content'),
            'name': post.get('question_name'),
        }, context=request.context)
        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),post.get('post_id')))

    @http.route('/forum/<model("website.forum"):forum>/answer/<model("website.forum.post"):post>/edit/<model("website.forum.post"):answer>', type='http', auth="user", multilang=True, website=True)
    def edit_ans(self, forum, post, answer, **kwarg):
        values = {
            'post': post,
            'post_answer': answer,
            'forum': forum,
            'searches': kwarg,
            'notifications': self._get_notifications(),
        }
        return request.website.render("website_forum.edit_answer", values)

    @http.route('/forum/correct_answer/', type='json', auth="user", multilang=True, methods=['POST'], website=True)
    def correct_answer(self, **kwarg):
        cr, uid, context = request.cr, request.uid, request.context
        Post = request.registry['website.forum.post']
        post = Post.browse(cr, uid, int(kwarg.get('post_id')), context=context)
        if post.user_id.id == uid:
            correct = False if post.correct else True
            #Note: only one answer can be right.
            for child in post.parent_id.child_ids:
                if child.correct:
                    Post.write( cr, uid, [child.id], {
                        'correct': False,
                    }, context=context)
            Post.write( cr, uid, [int(kwarg.get('post_id'))], {
                'correct': correct,
            }, context=context)
        return correct

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

    @http.route('/forum/<model("website.forum"):forum>/save/profile/', type='http', auth="user", multilang=True, website=True)
    def save_edited_profile(self, forum, **post):
        cr, uid, context = request.cr, request.uid, request.context
        request.registry['res.users'].write( cr, uid, [int(post.get('user_id'))], {
            'name': post.get('name'),
        }, context=context)
        record_id = request.registry['res.users'].browse(cr, uid, int(post.get('user_id')),context=context).partner_id.id
        request.registry['res.partner'].write( cr, uid, [record_id], {
            'website': post.get('website'),
            'city': post.get('city'),
            'country_id':post.get('country'),
            'birthdate':post.get('dob'),
            'website_description': post.get('description'), 
        }, context=context)
        return werkzeug.utils.redirect("/forum/%s/user/%s" % (slug(forum),post.get('user_id')))
