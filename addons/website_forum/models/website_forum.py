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
    _order = "id desc"

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
                    if vote.vote == '1':
                        res[post.id] += 1
                    else:
                        res[post.id] -= 1
        return res

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

        # TODO: add a store={} on those two fields. Why is it a boolean?
        'user_vote':fields.function(_get_votes, string="My Vote", type='boolean'),

        # TODO: add a store={} on those two fields
        'vote_count':fields.function(_get_vote_count, string="Votes", type='integer'),
    }
    _defaults = {
        'state': 'active',
        'active': True
    }

    def create_history(self, cr, uid, ids, vals, context=None):
        History = self.pool['website.forum.post.history']
        for post in ids:
            if vals.get('content'):
                create_date = vals.get('create_date')
                res = {
                    'name': 'Update %s - %s' % (create_date, vals.get('name')),
                    'content': vals.get('content', ''),
                    'post_id': post
                }
                if vals.get('version'):
                    res.update({'version':vals.get('version')})

                if vals.get('tags'):
                    res.update({'tags':vals.get('tags')})

                History.create(cr, uid, res, context=context)

    def create_activity(self, cr, uid, ids, method, context=None):
        Activity = self.pool['website.forum.activity']
        for post in self.browse(cr, uid, ids, context=context):
            res = {
                'name': post.name,
                'post_id': post.id,
                'user_id': uid,
            }

            if post.parent_id:
                res.update({'type': 'edited_answer'})
                if method == 'create':
                    res.update({'type': 'answered_question'})
                if method == 'unlink':
                    res.update({'type': 'deleted_answer'})
                if method == 'vote':
                    res.update({'type': 'voted_answer'})

            else:
                res.update({'type': 'edited_question'})
                if method == 'create':
                    res.update({'type': 'asked_question'})
                if method == 'unlink':
                    res.update({'type': 'deleted_question'})
                if method == 'vote':
                    res.update({'type': 'voted_question'})

            Activity.create(cr, uid, res, context=context)

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        create_context = dict(context, mail_create_nolog=True)
        post_id = super(Post, self).create(cr, uid, vals, context=create_context)
        self.create_activity(cr, uid, [post_id], method='create', context=context)
        return post_id

    def write(self, cr, uid, ids, vals, context=None):
        self.create_history(cr, uid, ids, vals, context=context)
        result = super(Post, self).write(cr, uid, ids, vals, context=context)
        self.create_activity(cr, uid, ids, method='write', context=context)
        return result

    def unlink(self, cr, uid, ids, context=None):
        self.create_activity(cr, uid, ids, method='unlink', context=context)
        return super(Post, self).unlink(cr, uid, ids, context=context)

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
        'karma': fields.integer('Karma'), # Use Gamification for this
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
        'name': fields.char('Update Notes', size=64, required=True),
        'post_id': fields.many2one('website.forum.post', 'Post', ondelete='cascade'),
        'create_date': fields.datetime('Created on', select=True, readonly=True),
        'create_uid': fields.many2one('res.users', 'Created by', select=True, readonly=True),
        'version': fields.integer('Version'),
        'content': fields.html('Contents', help='Automatically sanitized HTML contents'),
        'tags': fields.many2many('website.forum.tag', 'forum_tag_rel', 'forum_id', 'forum_tag_id', 'Tag'),
    }

class Vote(osv.Model):
    _name = 'website.forum.post.vote'
    _description = 'Vote'
    _columns = {
        'post_id': fields.many2one('website.forum.post', 'Post', required=True),
        'user_id': fields.many2one('res.users', 'User'),
        'vote': fields.selection([('1', '1'),('-1', '-1')], 'rate'),
    }

    def create(self, cr, uid, vals, context=None):
        vote_id = super(Vote, self).create(cr, uid, vals, context=context)
        self.pool['website.forum.post'].create_activity(cr, uid, [int(vals.get('post_id'))], method='vote', context=context)
        return vote_id

class Badge(osv.Model):
    _inherit = 'gamification.badge'
    _columns = {
        'forum': fields.boolean('Is a Forum Badge'),
        'level': fields.selection([('bronze', 'bronze'), ('silver', 'silver'), ('gold', 'gold')], 'Badge Level'),
    }
    _defaults = {
        'forum': False,
        'level': 'bronze'
    }


# TODO:
# remove this object and replace by mail.message of type notes on related post
# type = message types
class ForumActivity(osv.Model):
    _name = "website.forum.activity"
    _description = "Activity"
    _order = "id desc"
    _columns = {
        'name': fields.char('Name', size=64),
        'post_id': fields.many2one('website.forum.post', 'Post'),
        'user_id': fields.many2one('res.users', 'User'),
        'create_date': fields.datetime('Created on', select=True, readonly=True),
        # Use the gamification module instead!
        'badge_id': fields.many2one('res.groups', 'Badge'),
        #NOTE: we can create new ForumActivityType object instead of selection
        'type': fields.selection([('asked_question', 'asked a question'), ('answered_question', 'answered a question'),
                                  ('edited_question', 'edited question'), ('edited_answer', 'edited answer'),
                                  ('commented_question', 'commented question'), ('commented_answer', 'commented answer'),
                                  ('deleted_question', 'deleted question'), ('deleted_answer', 'deleted answer'),
                                  ('voted_question', 'voted question'), ('voted_answer', 'voted answer'),
                                  ('received_badge', 'received badge'),
                                  ], 'Activity Type'),
        # merge these 2 fields into one: karma: fields.integer (that can be positive or negative)
        'karma_add': fields.integer('Added Karma'),
        'karma_sub': fields.integer('Karma Removed')
   }

class Tags(osv.Model):
    _name = "website.forum.tag"
    _description = "Tag"
    _inherit = ['website.seo.metadata']
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'post_ids': fields.many2many('website.forum.post', 'forum_tag_que_rel', 'tag_id', 'forum_id', 'Questions', readonly=True),
        'forum_id': fields.many2one('website.forum', 'Forum', required=True)
   }
