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
    @http.route(['/question/', '/question/page/<int:page>'], type='http', auth="public", website=True, multilang=True)
    def questions(self, page=1, **searches):
        cr, uid, context = request.cr, request.uid, request.context
        forum_obj = request.registry['website.forum.post']
        tag_obj = request.registry['website.forum.tag']
        
        step = 5
        question_count = forum_obj.search(
            request.cr, request.uid, [], count=True,
            context=request.context)
        pager = request.website.pager(url="/question/", total=question_count, page=page, step=step, scope=5)
        
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
    def question_page(self, question, page, **post):
        values = {
            'question': question,
            'main_object': question
        }
        return request.website.render(page, values)

    @http.route(['/question/<model("website.forum.post"):question>'], type='http', auth="public", website=True, multilang=True)
    def question_register(self, question, **post):
        values = {
            'question': question,
            'main_object': question,
            'range': range,
        }
        return request.website.render("website_forum.question_description_full", values)

    @http.route('/question/add_question/', type='http', auth="user", multilang=True, methods=['POST'], website=True)
    def add_question(self, question_name="New question", **kwargs):
        return self._add_question(question_name, request.context, **kwargs)

    def _add_question(self, question_name=None, context={}, **kwargs):
        if not question_name:
            question_name = _("New Question")
        Question = request.registry.get('website.forum.post')
        date_begin = datetime.today() + timedelta(days=(14))
        vals = {
            'topic': question_name,
        }
        question_id = Question.create(request.cr, request.uid, vals, context=context)
        return request.redirect("/question/%s/?enable_editor=1" % question_id)
