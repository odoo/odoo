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

controllers = controllers()

class website_forum(http.Controller):

    @http.route(['/questions/', '/questions/page/<int:page>'], type='http', auth="public", website=True, multilang=True)
    def questions(self, page=1, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        forum_obj = request.registry['website.forum.post']
        tag_obj = request.registry['website.forum.tag']

        step = 10
        question_count = forum_obj.search(
            request.cr, request.uid, [], count=True,
            context=request.context)
        pager = request.website.pager(url="/questions/", total=question_count, page=page, step=step, scope=10)

        obj_ids = forum_obj.search(
            request.cr, request.uid, [], limit=step,
            offset=pager['offset'], context=request.context)
        question_ids = forum_obj.browse(request.cr, request.uid, obj_ids,
                                      context=request.context)
        values = {
            'question_ids': question_ids,
            'pager': pager,
            'searches': searches,
        }

        return request.website.render("website_forum.index", values)

    @http.route(['/question/<model("website.forum.post"):question>/page/<page:page>'], type='http', auth="public", website=True, multilang=True)
    def question(self, question, page, **post):
        values = {
            'question': question,
            'main_object': question
        }
        return request.website.render(page, values)

    @http.route(['/question/<model("website.forum.post"):question>'], type='http', auth="public", website=True, multilang=True)
    def open_question(self, question, **post):
        values = {
            'question': question,
            'main_object': question,
            'range': range,
        }
        return request.website.render("website_forum.post_description_full", values)

    @http.route('/question/postquestion/', type='http', auth="user", multilang=True, website=True)
    def post_question(self, question_name="New question", **kwargs):
        #TODO : reply a page that allows user to post a question
        return self._add_question(question_name, request.context, **kwargs)

    @http.route('/question/new/', type='http', auth="user", multilang=True, methods=['POST'], website=True)
    def register_question(self, forum_id=1, **question):
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context)
        new_question_id = request.registry['blog.post'].create(
            request.cr, request.uid, {
                'forum_id': forum_id,
                'name': question.get('name'),
                'content': question.get('content'),
                'tags' : question.get('tags'),
                'state': 'active',
                'active': True,
            }, context=create_context)
        return werkzeug.utils.redirect("/question/%s" % new_question_id)

    @http.route('/question/new/', type='http', auth="user", multilang=True, methods=['POST'], website=True)
    def post_answer(self, post_id, forum_id=1, **question):
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context)
        new_question_id = request.registry['blog.post'].create(
            request.cr, request.uid, {
                'forum_id': forum_id,
                'parent_id':post_id,
                'name': question.get('name'),
                'content': question.get('content'),
                'tags' : question.get('tags'),
                'state': 'active',
                'active': True,
            }, context=create_context)
        return werkzeug.utils.redirect("/question/%s" % post_id)

    @http.route(['/questions/tag/<model("website.forum.tag"):tag>'], type='http', auth="public", website=True, multilang=True)
    def tag_questions(self, tag, page=1, **kwargs):
        cr, uid, context = request.cr, request.uid, request.context
        step = 10
        pager = request.website.pager(url="/questions/", total=len(tag.post_ids), page=page, step=step, scope=10)

        values = {
            'question_ids': tag.post_ids,
            'pager': pager,
        }

        return request.website.render("website_forum.index", values)
