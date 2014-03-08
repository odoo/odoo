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
        forum_ids = Forum.browse(cr, uid, obj_ids, context=context)

        values = {
            'forum_ids': forum_ids,
            'searches': {},
        }
        return request.website.render("website_forum.forum_index", values)

    @http.route(['/forum/<model("website.forum"):forum>/view'], type='http', auth="public", website=True, multilang=True)
    def view_forum(self, forum, **searches):
        return request.website.render("website_forum.forum", {'forum': forum })

    @http.route('/forum/add_forum/', type='http', auth="user", multilang=True, methods=['POST'], website=True)
    def add_forum(self, forum_name="New Forum", **kwargs):
        forum_id = request.registry['website.forum'].create(request.cr, request.uid, {
            'name': forum_name,
            'faq': 'F.A.Q'
        }, context=request.context)
        return request.redirect("/forum/%s/view/?enable_editor=1" % forum_id)

    @http.route(['/forum/<model("website.forum"):forum>/', '/forum/<model("website.forum"):forum>/page/<int:page>'], type='http', auth="public", website=True, multilang=True)
    def questions(self, forum, page=1, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        Forum = request.registry['website.forum.post']
        domain = [('forum_id', '=', forum.id), ('parent_id', '=', False)]

        search = searches.get('search',False)
        if search:
            domain += ['|',
                ('name', 'ilike', search),
                ('content', 'ilike', search)]

        type = searches.get('type',False)
        if not type:
            searches['type'] = 'all'
        if type == 'unanswered':
            domain += [ ('child_ids', '=', False) ]
        #TODO: update domain to show followed questions of user
        if type == 'followed':
            domain += [ ('create_uid', '=', uid) ]

        step = 10
        question_count = Forum.search(cr, uid, domain, count=True, context=context)
        pager = request.website.pager(url="/forum/%s/" % slug(forum), total=question_count, page=page, step=step, scope=10)

        obj_ids = Forum.search(cr, uid, domain, limit=step, offset=pager['offset'], context=context)
        question_ids = Forum.browse(cr, uid, obj_ids, context=context)

        values = {
            'total_questions': question_count,
            'question_ids': question_ids,
            'forum': forum,
            'pager': pager,
            'searches': searches,
        }

        return request.website.render("website_forum.index", values)

    @http.route(['/forum/<model("website.forum"):forum>/faq'], type='http', auth="public", website=True, multilang=True)
    def faq(self, forum, **post):
        values = { 'searches': {}, 'forum':forum }
        return request.website.render("website_forum.faq", values)

    @http.route(['/forum/<model("website.forum"):forum>/ask'], type='http', auth="public", website=True, multilang=True)
    def question_ask(self, forum, **post):
        values = { 'searches': {}, 'forum': forum }
        return request.website.render("website_forum.ask_question", values)

    @http.route(['/forum/<model("website.forum"):forum>/question/<model("website.forum.post"):question>/page/<page:page>'], type='http', auth="public", website=True, multilang=True)
    def question(self, forum, question, page, **post):
        values = {
            'question': question,
            'forum': forum
        }
        return request.website.render(page, values)

    @http.route(['/forum/<model("website.forum"):forum>/question/<model("website.forum.post"):question>'], type='http', auth="public", website=True, multilang=True)
    def open_question(self, forum, question, **post):
        answer_done = False
        for answer in question.child_ids:
            if answer.create_uid.id == request.uid:
                answer_done = True
        values = {
            'question': question,
            'searches': post,
            'answer_done': answer_done,
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
        Activity = request.registry['website.forum.activity']

        question_ids = Post.search(cr, uid, [('create_uid', '=', user.id), ('parent_id', '=', False)], context=context)
        questions = Post.browse(cr, uid, question_ids, context=context)

        #TODO: showing questions in which user answered
        obj_ids = Post.search(cr, uid, [('create_uid', '=', user.id), ('parent_id', '!=', False)], context=context)
        answer_ids = Post.browse(cr, uid, obj_ids, context=context)
        answers = [answer.parent_id for answer in answer_ids]

        total_votes = Vote.search(cr, uid, [('post_id.create_uid', '=', user.id)], count=True, context=context)
        up_votes = Vote.search(cr, uid, [('post_id.create_uid', '=', user.id), ('vote', '=', '1')], count=True, context=context)
        down_votes = Vote.search(cr, uid, [('post_id.create_uid', '=', user.id), ('vote', '=', '-1')], count=True, context=context)

        activity_ids = Activity.search(cr, uid, [('user_id', '=', user.id)], context=context)
        activities = Activity.browse(cr, uid, activity_ids, context=context)

        values = {
            'user': user,
            'main_object': user,
            'searches': post,
            'forum': forum,
            'questions': questions,
            'answers': answers,
            'total_votes': total_votes,
            'up_votes': up_votes,
            'down_votes': down_votes,
            'activities': activities
        }
        return request.website.render("website_forum.user_detail_full", values)

    @http.route('/forum/<model("website.forum"):forum>/question/ask/', type='http', auth="user", multilang=True, methods=['POST'], website=True)
    def register_question(self, forum, **question):
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context)
        new_question_id = request.registry['website.forum.post'].create(
            request.cr, request.uid, {
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
            if answer.create_uid.id == request.uid:
                post_answer = answer
        values = {
            'post': post,
            'post_answer': post_answer,
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
        pager = request.website.pager(url="/forum/%s/tag" % slug(forum), total=len(tag.post_ids), page=page, step=10, scope=10)

        values = {
            'question_ids': tag.post_ids,
            'pager': pager,
            'forum': forum,
            'searches': kwargs
        }
        return request.website.render("website_forum.index", values)

    @http.route(['/forum/<model("website.forum"):forum>/tags'], type='http', auth="public", website=True, multilang=True)
    def tags(self, forum, page=1, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        Tag = request.registry['website.forum.tag']
        obj_ids = Tag.search(cr, uid, [], limit=None, context=context)
        tags = Tag.browse(cr, uid, obj_ids, context=context)
        values = {
            'tags': tags,
            'forum': forum,
            'searches': {'tags': True}
        }
        return request.website.render("website_forum.tag", values)

    @http.route(['/forum/<model("website.forum"):forum>/badges'], type='http', auth="public", website=True, multilang=True)
    def badges(self, forum, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        Badge = request.registry['gamification.badge']
        badge_ids = Badge.search(cr, uid, [('forum', '=', True)], context=context)
        badges = Badge.browse(cr, uid, badge_ids, context=context)
        values = {
            'badges': badges,
            'forum': forum,
            'searches': {'badges': True}
        }
        return request.website.render("website_forum.badge", values)

    @http.route(['/forum/<model("website.forum"):forum>/badge/<model("gamification.badge"):badge>'], type='http', auth="public", website=True, multilang=True)
    def badge_users(self, forum, badge, **kwargs):
        users = [badge_user.user_id for badge_user in badge.owner_ids]

        values = {
            'badge': badge,
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
            'pager': pager,
            'forum': forum,
            'searches': searches,
        }

        return request.website.render("website_forum.users", values)

    @http.route('/forum/<model("website.forum"):forum>/post_vote/', type='http', auth="user", multilang=True, methods=['POST'], website=True)
    def post_vote(self, forum, **post):
        cr, uid, context, post_id = request.cr, request.uid, request.context, int(post.get('post_id'))
        Vote = request.registry['website.forum.post.vote']
        vote_ids = Vote.search(cr, uid, [('post_id', '=', post_id)], context=context)

        if vote_ids:
            Vote.unlink(cr, uid, vote_ids, context=context)
        else:
            Vote.create(cr, uid, {
                'post_id': post_id,
                'user_id': uid,
                'vote': post.get('vote'),
            }, context=context)

        return werkzeug.utils.redirect("/forum/%s/question/%s" % (slug(forum),post.get('question_id')))
