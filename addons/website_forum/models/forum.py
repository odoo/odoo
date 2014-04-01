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
from openerp import tools
from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import date, datetime

from openerp.addons.website.models.website import slug

#TODO: Do we need a forum object like blog object ? Need to check with BE team 
class Forum(osv.Model):
    _name = 'website.forum'
    _description = 'Forums'
    _inherit = ['mail.thread', 'website.seo.metadata']

    def _get_right_column(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for forum in self.browse(cr, uid, ids, context=context):
            res[forum.id] = """<div class="panel panel-default">
                <div class="panel-heading">
                    <h3 class="panel-title">About This Forum</h3>
                </div>
                <div class="panel-body">
                    This community is for professionals and enthusiasts of our 
                    products and services.<br/>
                    <a href="/forum/%s/faq" class="fa fa-arrow-right"> Read Guidelines</a>
                </div>
            </div>""" % slug(forum)
        return res

    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'faq': fields.html('Guidelines'),
        'right_column':fields.function(_get_right_column, string="Right Column", type='html', store=True),
    }
    def _get_default_faq(self, cr, uid, context={}):
        fname = openerp.modules.get_module_resource('website_forum', 'data', 'forum_default_faq.html')
        with open(fname, 'r') as f:
            return f.read()
        return False

    _defaults = {
        'faq': _get_default_faq,
    }

class Post(osv.Model):
    _name = 'website.forum.post'
    _description = "Question"
    _inherit = ['mail.thread', 'website.seo.metadata']

    def _get_votes(self, cr, uid, ids, field_name, arg, context):
        res = dict.fromkeys(ids, False)
        # Note: read_group is not returning all fields which we passed in list.when it will work uncomment this code and remove remaining code 
        #Vote = self.pool['website.forum.post.vote']
        #data = Vote.read_group(cr, uid, [('post_id','in', ids), ('user_id', '=', uid)], [ "post_id", "vote"], groupby=["post_id"], context=context)
        #for rec in data:
        #    res[rec[post_id][0]] = rec['vote']
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
        for vote in self.pool['website.forum.post.vote'].browse(cr, uid, ids, context=context):
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

    def _get_view_count(self, cr, uid, ids, field_name=False, arg={}, context=None):
        res = dict.fromkeys(ids, 0)
        for post in self.browse(cr, uid, ids, context=context):
            res[post.id] = post.views + 1
        return res

    def _set_view_count(self, cr, uid, ids, name, value, arg, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        for rec in self.browse(cr, uid, ids, context=context):
            views = rec.views + value
            cr.execute('UPDATE website_forum_post SET views=%s WHERE id=%s;',(views, rec.id))
        return True

    def _get_views(self, cr, uid, ids, context=None):
        result = {}
        for statistic in self.pool['website.forum.post.statistics'].browse(cr, uid, ids, context=context):
            result[statistic.post_id.id] = True
        return result.keys()

    _columns = {
        'name': fields.char('Title', size=128),
        'forum_id': fields.many2one('website.forum', 'Forum', required=True),
        'content': fields.text('Content'),
        'create_date': fields.datetime('Asked on', select=True, readonly=True),
        'user_id': fields.many2one('res.users', 'Asked by', select=True, readonly=True ),
        'write_date': fields.datetime('Update on', select=True, readonly=True ),
        'write_uid': fields.many2one('res.users', 'Update by', select=True, readonly=True),

        'tags': fields.many2many('website.forum.tag', 'forum_tag_rel', 'forum_id', 'forum_tag_id', 'Tag'),
        'vote_ids':fields.one2many('website.forum.post.vote', 'post_id', 'Vote'),

        'favourite_ids': fields.many2many('res.users', 'forum_favourite_rel', 'forum_id', 'user_id', 'Favourite'),

        'state': fields.selection([('active', 'Active'), ('close', 'Close'),('offensive', 'Offensive')], 'Status'),
        'active': fields.boolean('Active'),

        'views_ids': fields.one2many('website.forum.post.statistics', 'post_id', 'Views'),
        'views':fields.function(_get_view_count, string="Views", type='integer',
            store={
                'website.forum.post.statistics': (_get_views, [], 10),
            }
        ),

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

        'correct': fields.boolean('Correct Answer/ Answer on this question accepted.'),
        'reason_id': fields.many2one('website.forum.post.reason', 'Reason'),
        'closed_by': fields.many2one('res.users', 'Closed by'),
        'closed_date': fields.datetime('Closed on', readonly=True),
    }
    _defaults = {
        'state': 'active',
        'vote_count': 0,
        'active': True,
    }

    def create_history(self, cr, uid, ids, context=None):
        hist_obj = self.pool['website.forum.post.history']
        for post in self.browse(cr, uid, ids, context=context):
            history_count = hist_obj.search(cr, uid, [('post_id','=', post.id)], count=True, context=context)
            date = datetime.today().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
            name = "No.%s Revision" %(history_count+1) if history_count else "initial version"
            hist_obj.create(cr, uid, {
                'post_id': post.id,
                'content': post.content,
                'name': '%s - (%s) %s' % (history_count+1, date, name),
                'post_name': post.name,
                'tags': [(6,0, [x.id for x in post.tags])],
                'user_id': post.write_uid and post.write_uid.id or post.user_id.id,
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
            #add 2 karma to user when asks question.
            self.pool['res.users'].write(cr, SUPERUSER_ID, [vals.get('user_id')], {'karma': 2}, context=context)
        post_id = super(Post, self).create(cr, uid, vals, context=create_context)
        self.create_history(cr, uid, [post_id], context=context)
        self.message_post(cr, uid, [post_id], body=_(body), subtype=subtype, context=context)
        return post_id

    def write(self, cr, uid, ids, vals, context=None):
        super(Post, self).write(cr, uid, ids, vals, context=context)
        #NOTE: to avoid message post on write of last comment time
        if not vals.get('message_last_post'):
            user = self.pool['res.users'].browse(cr, uid ,uid, context=context)
            self.create_history(cr, uid, ids, context=context)
            for post in self.browse(cr, uid, ids, context=context):
                body, subtype = "Edited question", "website_forum.mt_question_edit"
                if post.parent_id:
                    body, subtype = "Edited answer", "website_forum.mt_answer_edit"
                self.message_post(cr, uid, [post.id], body=_(body), subtype=subtype, context=context)

                #update karma of related user when any answer accepted.
                value = 0
                if vals.get('correct'):
                    value = 15
                elif vals.get('correct') == False:
                    value = -15 
                self.pool['res.users'].write(cr, SUPERUSER_ID, [post.user_id.id], {'karma': value}, context=context)
        return True

class PostStatistics(osv.Model):
    _name = "website.forum.post.statistics"
    _description = "Post Statistics"
    _columns = {
        'name': fields.char('Post Reason'),
        'post_id': fields.many2one('website.forum.post', 'Post', ondelete='cascade'),
        'user_id': fields.many2one('res.users', 'Created by'),
    }

class PostReason(osv.Model):
    _name = "website.forum.post.reason"
    _description = "Post Reason"
    _columns = {
        'name': fields.char('Post Reason'),
    }

class Users(osv.Model):
    _inherit = 'res.users'

    def _get_user_badge_level(self, cr, uid, ids, name, args, context=None):
        """Return total badge per level of users"""
        result = dict.fromkeys(ids, False)
        badge_user_obj = self.pool['gamification.badge.user']
        for id in ids:
            result[id] = {
                'gold_badge': badge_user_obj.search(cr, uid, [('badge_id.level', '=', 'gold'), ('user_id', '=', id)], context=context, count=True),
                'silver_badge': badge_user_obj.search(cr, uid, [('badge_id.level', '=', 'silver'), ('user_id', '=', id)], context=context, count=True),
                'bronze_badge': badge_user_obj.search(cr, uid, [('badge_id.level', '=', 'bronze'), ('user_id', '=', id)], context=context, count=True),
            }
        return result

    def _set_user_karma(self, cr, uid, ids, name, value, arg, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        for rec in self.browse(cr, uid, ids, context=context):
            karma = rec.karma + value
            cr.execute('UPDATE res_users SET karma=%s WHERE id=%s;',(karma, rec.id))
        return True

    def _get_user_karma(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for user in self.browse(cr, uid, ids, context=context):
            result[user.id] = user.karma
        return result

    _columns = {
        'create_date': fields.datetime('Create Date', select=True, readonly=True),
        'forum': fields.boolean('Is Forum Member'),
        'karma': fields.function(_get_user_karma, fnct_inv=_set_user_karma, type='integer', string="Karma", store=True),

        'badges': fields.one2many('gamification.badge.user', 'user_id', 'Badges'),
        'gold_badge':fields.function(_get_user_badge_level, string="Number of gold badges", type='integer', multi='badge_level'),
        'silver_badge':fields.function(_get_user_badge_level, string="Number of silver badges", type='integer', multi='badge_level'),
        'bronze_badge':fields.function(_get_user_badge_level, string="Number of bronze badges", type='integer', multi='badge_level'),
    }
    _defaults = {
        'forum': False,
        'karma': 1,
    }

class PostHistory(osv.Model):
    _name = 'website.forum.post.history'
    _description = 'Post History'
    _inherit = ['website.seo.metadata']
    _columns = {
        'name': fields.char('History Title'),
        'post_id': fields.many2one('website.forum.post', 'Post', ondelete='cascade'),
        'post_name': fields.char('Post Name'),
        'content': fields.text('Content'),
        'user_id': fields.many2one('res.users', 'Created by', select=True, readonly=True),
        'tags': fields.many2many('website.forum.tag', 'post_tag_rel', 'post_id', 'post_tag_id', 'Tag'),
    }

class Vote(osv.Model):
    _name = 'website.forum.post.vote'
    _description = 'Vote'
    _columns = {
        'post_id': fields.many2one('website.forum.post', 'Post', ondelete='cascade', required=True),
        'user_id': fields.many2one('res.users', 'User'),
        'vote': fields.selection([('1', '1'),('-1', '-1'),('0','0')], 'Vote'),
        'create_date': fields.datetime('Create Date', select=True, readonly=True),
    }
    _defaults = {
        'user_id': lambda self, cr, uid, ctx: uid,
        'vote': lambda *args: 1
    }

    def create(self, cr, uid, vals, context=None):
        vote_id = super(Vote, self).create(cr, uid, vals, context=context)
        Post = self.pool["website.forum.post"]
        record = Post.browse(cr, uid, vals.get('post_id'), context=context)
        #Add 10 karma when user get up vote and subtract 10 karma when gets down vote.
        value = 10 if vals.get('vote') == '1' else -10
        self.pool['res.users'].write(cr, SUPERUSER_ID, [record.user_id.id], {'karma': value}, context=context)
        body = "voted %s %s" % ('answer' if record.parent_id else 'question','up' if vals.get('vote')==1 else 'down')
        Post.message_post(cr, uid, [record.id], body=_(body), context=context)
        return vote_id

    def vote(self, cr, uid, post_id, vote, context=None):
        assert int(vote) in (1, -1, 0), "vote can be -1 or 1, nothing else"
        #user can not vote on own post.
        post = self.pool['website.forum.post'].browse(cr, uid, post_id, context=context)
        if post.user_id.id == uid:
            return {'error': 'own_post'}
        user = self.pool['res.users'].browse(cr, uid, uid, context=None)
        if (vote == '-1') and (user.karma <= 10):
            return {'error': 'lessthen_10_karma'}
        vote_ids = self.search(cr, uid, [('post_id', '=', post_id), ('user_id','=',uid)], context=context)
        if vote_ids:
            #when user will click again on vote it should set it 0.
            record = self.browse(cr,uid, vote_ids[0], context=context)
            new_vote = '0' if record.vote in ['1','-1'] else vote
            #update karma when user changed vote.
            if record.vote == '1' or new_vote == '-1':
                value = -10
            elif record.vote == '-1' or new_vote == '1':
                value = 10
            self.pool['res.users'].write(cr, SUPERUSER_ID, [record.post_id.user_id.id], {'karma': value}, context=context)
            self.write(cr, uid, vote_ids, {
                'vote': new_vote
            }, context=context)
        else:
            self.create(cr, uid, {
                'post_id': post_id,
                'vote': vote,
            }, context=context)
        post.refresh()
        return {'vote_count': post.vote_count}

class MailMessage(osv.Model):
    _inherit = 'mail.message'
    _columns = {
        'create_uid': fields.many2one('res.users', 'Created by', readonly=True ),
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

    def _get_post(self, cr, uid, ids, context=None):
        result = {}
        for post in self.pool['website.forum.post'].browse(cr, uid, ids, context=context):
            for tag in post.tags:
                result[tag.id] = True
        return result.keys()

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'forum_id': fields.many2one('website.forum', 'Forum', required=True),
        'posts_count': fields.function(_get_posts_count, type='integer', string="# of Posts",
            store={
                'website.forum.post': (_get_post, ['tags'], 10),
            }
        ),
   }
