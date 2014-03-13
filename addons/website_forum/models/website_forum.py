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

import re

import openerp
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _

from openerp.addons.website.models.website import slug

#TODO: Do we need a forum object like blog object ? Need to check with BE team 
class Forum(osv.Model):
    _name = 'website.forum'
    _description = 'Forums'
    _inherit = ['mail.thread', 'website.seo.metadata']
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'faq': fields.html('Guidelines'),
        'right_column': fields.html('Right Column'),
    }
    def _get_default_faq(self, cr, uid, context={}):
        fname = openerp.modules.get_module_resource('website_forum', 'data', 'forum_default_faq.html')
        with open(fname, 'r') as f:
            return f.read()
        return False

    _defaults = {
        'faq': _get_default_faq,
        'right_column': """<div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title">About This Forum</h3>
                </div>
                <div class="panel-body">
                    This community is for professional and enthusiast about our
                    products and services.<br/>
                    <a t-attf-href="/forum/1/faq" class="fa fa-arrow-right"> Read Guidelines</a>
                </div>
            </div>"""
    }

class Post(osv.Model):
    _name = 'website.forum.post'
    _description = "Question"
    _inherit = ['mail.thread', 'website.seo.metadata']

    def _get_votes(self, cr, uid, ids, field_name, arg, context):
        res = dict.fromkeys(ids, False)
        # TODO: implement this with a read_group call instead of browsing all records
        for post in self.browse(cr, uid, ids, context=context):
            if post.vote_ids:
                for vote in post.vote_ids:
                    if vote.user_id.id == uid:
                        if vote.vote == '1':
                            res[post.id] = 1
                        else:
                            res[post.id] = -1
        return res

    def _get_vote_count(self, cr, uid, ids, field_name, arg, context):
        res = dict.fromkeys(ids, 0)
        for post in self.browse(cr, uid, ids, context=context):
            if post.vote_ids:
                for vote in post.vote_ids:
                    res[post.id] += int(vote.vote)
        return res

    def _get_vote(self, cr, uid, ids, context=None):
        result = {}
        for vote in self.pool.get('website.forum.post.vote').browse(cr, uid, ids, context=context):
            result[vote.post_id.id] = True
        return result.keys()

    def _get_child_count(self, cr, uid, ids, field_name=False, arg={}, context=None):
        res = dict.fromkeys(ids, 0)
        for post in self.browse(cr, uid, ids, context=context):
            if post.parent_id:
                res[post.parent_id.id] = len(post.parent_id.child_ids)
        return res

    def _get_child(self, cr, uid, ids, context=None):
        return ids

    _columns = {
        'name': fields.char('Title', size=128),
        'forum_id': fields.many2one('website.forum', 'Forum', required=True),
        'content': fields.text('Content'),
        'create_date': fields.datetime('Asked on', select=True, readonly=True),
        'create_uid': fields.many2one('res.users', 'Asked by', select=True, readonly=True ),
        'write_date': fields.datetime('Update on', select=True, readonly=True ),
        'write_uid': fields.many2one('res.users', 'Update by', select=True, readonly=True),

        'tags': fields.many2many('website.forum.tag', 'forum_tag_rel', 'forum_id', 'forum_tag_id', 'Tag'),
        'vote_ids':fields.one2many('website.forum.post.vote', 'post_id', 'Vote'),

        'favourite_ids': fields.many2many('res.users', 'forum_favourite_rel', 'forum_id', 'user_id', 'Favourite'),

        'state': fields.selection([('active', 'Active'),('close', 'Close'),('offensive', 'Offensive')], 'Status'),
        'active': fields.boolean('Active'),
        'views': fields.integer('Page Views'),

        'parent_id': fields.many2one('website.forum.post', 'Question', ondelete='cascade'),
        'child_ids': fields.one2many('website.forum.post', 'parent_id', 'Answers'),
        'child_count':fields.function(_get_child_count, string="Answers", type='integer',
            store={
                'website.forum.post': (_get_child, [], 10),
            }
        ),

        'history_ids': fields.one2many('blog.post.history', 'post_id', 'History', help='Last post modifications'),
        # TODO FIXME: when website_mail/mail_thread.py inheritance work -> this field won't be necessary
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', ('model', '=', self._name), ('type', '=', 'comment')
            ],
            string='Post Messages',
            help="Comments on forum post",
        ),

        'user_vote':fields.function(_get_votes, string="My Vote", type='boolean',
            store={
                'website.forum.post': (lambda self, cr, uid, ids, c={}: ids, ['vote_ids'], 10),
                'website.forum.post.vote': (_get_vote, [], 10),
            }
        ),

        'vote_count':fields.function(_get_vote_count, string="Votes", type='integer',
            store={
                'website.forum.post': (lambda self, cr, uid, ids, c={}: ids, ['vote_ids'], 10),
                'website.forum.post.vote': (_get_vote, [], 10),
            }
        ),
        'correct': fields.boolean('Correct Answer'),
    }
    _defaults = {
        'state': 'active',
        'vote_count': 0,
        'active': True,
    }

    def create_history(self, cr, uid, ids, vals, context=None):
        hist_obj = self.pool['website.forum.post.history']
        for post in self.browse(cr, uid, ids, context=context):
            hist_obj.create(cr, uid, {
                'post_id': post.id,
                'content': post.content,
                'name': post.name,
                'tags': [(6,0, [x.id for x in post.tags])],
                'date': post.write_date or post.create_date,
                'user_id': post.write_uid and post.write_uid.id or post.create_uid.id
            }, context=context)

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        create_context = dict(context, mail_create_nolog=True)
        body, subtype = "Asked a question", "website_forum.mt_question_create"
        if vals.get("parent_id"):
            body, subtype = "Answered a question", "website_forum.mt_answer_create"
            #Note: because of no name it gives error on slug so set name of question in answer
            question = self.browse(cr, uid, vals.get("parent_id"), context=context)
            vals['name'] = question.name
        post_id = super(Post, self).create(cr, uid, vals, context=create_context)
        #Note: just have to pass subtype in message post: gives error on installation time
        self.message_post(cr, uid, [post_id], body=_(body), context=context)
        return post_id

    def write(self, cr, uid, ids, vals, context=None):
        self.create_history(cr, uid, ids, vals, context=context)
        #NOTE: to avoid message post on write of last comment time
        if not vals.get('message_last_post'):
            for post in self.browse(cr, uid, ids, context=context):
                body, subtype = "Edited question", "website_forum.mt_question_edit"
                if post.parent_id:
                    body, subtype = "Edited answer", "website_forum.mt_answer_edit"
                self.message_post(cr, uid, [post.id], body=_(body), subtype=subtype, context=context)
        return super(Post, self).write(cr, uid, ids, vals, context=context)

class Users(osv.Model):
    _inherit = 'res.users'

    def _get_user_badge_level(self, cr, uid, ids, name, args, context=None):
        """Return total badge per level of users"""
        result = dict.fromkeys(ids, False)
        badge_user_obj = self.pool.get('gamification.badge.user')
        for id in ids:
            result[id] = {
                'gold_badge': badge_user_obj.search(cr, uid, [('badge_id.level', '=', 'gold'), ('user_id', '=', id)], context=context, count=True),
                'silver_badge': badge_user_obj.search(cr, uid, [('badge_id.level', '=', 'silver'), ('user_id', '=', id)], context=context, count=True),
                'bronze_badge': badge_user_obj.search(cr, uid, [('badge_id.level', '=', 'bronze'), ('user_id', '=', id)], context=context, count=True),
            }
        return result

    _columns = {
        'create_date': fields.datetime('Create Date', select=True, readonly=True),
        'karma': fields.integer('Karma'), # Use a function field for this
        'forum': fields.boolean('Is Forum Member'),

        'badges': fields.one2many('gamification.badge.user', 'user_id', 'Badges'),
        'gold_badge':fields.function(_get_user_badge_level, string="Number of gold badges", type='integer', multi='badge_level'),
        'silver_badge':fields.function(_get_user_badge_level, string="Number of silver badges", type='integer', multi='badge_level'),
        'bronze_badge':fields.function(_get_user_badge_level, string="Number of bronze badges", type='integer', multi='badge_level'),
    }
    _defaults = {
        'forum': False,
        'karma': 0
    }

class PostHistory(osv.Model):
    _name = 'website.forum.post.history'
    _description = 'Post History'
    _inherit = ['website.seo.metadata']
    _columns = {
        'name': fields.char('Post Title'),
        'post_id': fields.many2one('website.forum.post', 'Post', ondelete='cascade'),
        'date': fields.datetime('Created on', select=True, readonly=True),
        'user_id': fields.many2one('res.users', 'Created by', select=True, readonly=True),
        'content': fields.html('Contents', help='Automatically sanitized HTML contents'),
        'tags': fields.many2many('website.forum.tag', 'forum_tag_rel', 'forum_id', 'forum_tag_id', 'Tag'),
    }

class Vote(osv.Model):
    _name = 'website.forum.post.vote'
    _description = 'Vote'
    _columns = {
        'post_id': fields.many2one('website.forum.post', 'Post', required=True),
        'user_id': fields.many2one('res.users', 'User'),
        'vote': fields.selection([('1', '1'),('-1', '-1'),('0','0')], 'Vote'),
    }
    _defaults = {
        'user_id': lambda self, cr, uid, ctx: uid,
        'vote': lambda *args: 1
    }

    def create(self, cr, uid, vals, context=None):
        vote_id = super(Vote, self).create(cr, uid, vals, context=context)
        Post = self.pool["website.forum.post"]
        record = Post.browse(cr, uid, vals.get('post_id'), context=context)
        body = "voted %s %s" % ('answer' if record.parent_id else 'question','up' if vals.get('vote')==1 else 'down')
        Post.message_post(cr, uid, [record.id], body=_(body), context=context)
        return vote_id

    def vote(self, cr, uid, post_id, vote, context=None):
        assert int(vote) in (1, -1, 0), "vote can be -1 or 1, nothing else"
        Post = self.pool.get('website.forum.post')
        vote_ids = self.search(cr, uid, [('post_id', '=', post_id), ('user_id','=',uid)], context=context)
        if vote_ids:
            #when user will click again on vote it should set it 0.
            record = self.browse(cr,uid, vote_ids[0], context=context)
            new_vote = '0' if record.vote in ['1','-1'] else vote
            self.write(cr, uid, vote_ids, {
                'vote': new_vote
            }, context=context)
        else:
            self.create(cr, uid, {
                'post_id': post_id,
                'vote': vote,
            }, context=context)
        return Post.browse(cr, uid, post_id, context=context).vote_count

class Badge(osv.Model):
    _inherit = 'gamification.badge'
    _columns = {
        'level': fields.selection([('bronze', 'bronze'), ('silver', 'silver'), ('gold', 'gold')], 'Forum Badge Level'),
    }

class Tags(osv.Model):
    _name = "website.forum.tag"
    _description = "Tag"
    _inherit = ['website.seo.metadata']
    def _get_posts_count(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        Post = self.pool['website.forum.post']
        for tag in ids:
            result[tag] = Post.search_count(cr, uid , [('tags', '=', tag)], context=context)
        return result

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'forum_id': fields.many2one('website.forum', 'Forum', required=True),
        'posts_count': fields.function(_get_posts_count, type='integer', string="# of Posts"),
   }
