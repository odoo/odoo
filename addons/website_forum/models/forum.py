# -*- coding: utf-8 -*-

import openerp

from openerp import SUPERUSER_ID
from openerp.osv import osv, fields
from openerp.tools.translate import _


class Forum(osv.Model):
    _name = 'website.forum'
    _description = 'Forums'
    _inherit = ['mail.thread', 'website.seo.metadata']

    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'faq': fields.html('Guidelines'),
        'description': fields.text('Description'),
    }

    def _get_default_faq(self, cr, uid, context=None):
        fname = openerp.modules.get_module_resource('website_forum', 'data', 'forum_default_faq.html')
        with open(fname, 'r') as f:
            return f.read()
        return False

    _defaults = {
        'description': 'This community is for professionals and enthusiasts of our products and services.',
        'faq': _get_default_faq,
    }


class Post(osv.Model):
    _name = 'website.forum.post'
    _description = "Question"
    _inherit = ['mail.thread', 'website.seo.metadata']

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
            else:
                res[post.id] = len(post.child_ids)
        return res

    def _get_user_vote(self, cr, uid, ids, field_name, arg, context):
        res = dict.fromkeys(ids, 0)
        vote_ids = self.pool['website.forum.post.vote'].search(cr, uid, [('post_id', 'in', ids), ('user_id', '=', uid)], context=context)
        for vote in self.pool['website.forum.post.vote'].browse(cr, uid, vote_ids, context=context):
            res[vote.post_id.id] = vote.vote
        return res

    def _get_user_favourite(self, cr, uid, ids, field_name, arg, context):
        res = dict.fromkeys(ids, False)
        user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        for post in self.browse(cr, uid, ids, context=context):
            if user in post.favourite_ids:
                res[post.id] = True
        return res

    _columns = {
        'name': fields.char('Title', size=128),
        'forum_id': fields.many2one('website.forum', 'Forum', required=True),
        'content': fields.text('Content'),
        'create_date': fields.datetime('Asked on', select=True, readonly=True),
        'user_id': fields.many2one('res.users', 'Asked by', select=True, readonly=True),
        'write_date': fields.datetime('Update on', select=True, readonly=True),
        'write_uid': fields.many2one('res.users', 'Update by', select=True, readonly=True),
        'tag_ids': fields.many2many('website.forum.tag', 'forum_tag_rel', 'forum_id', 'forum_tag_id', 'Tag'),
        'vote_ids': fields.one2many('website.forum.post.vote', 'post_id', 'Votes'),
        'user_vote': fields.function(_get_user_vote, string="My Vote", type='integer'),
        'favourite_ids': fields.many2many('res.users', 'forum_favourite_rel', 'forum_id', 'user_id', 'Favourite'),
        'user_favourite': fields.function(_get_user_favourite, string="My Favourite", type='boolean'),
        'state': fields.selection([('active', 'Active'), ('close', 'Close'), ('offensive', 'Offensive')], 'Status'),
        'active': fields.boolean('Active'),
        'views': fields.integer('Number of Views'),
        'parent_id': fields.many2one('website.forum.post', 'Question', ondelete='cascade'),
        'child_ids': fields.one2many('website.forum.post', 'parent_id', 'Answers'),
        'child_count': fields.function(
            _get_child_count, string="Answers", type='integer',
            store={
                'website.forum.post': (lambda self, cr, uid, ids, c={}: ids, ['parent_id', 'child_ids'], 10),
            }
        ),
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', ('model', '=', self._name), ('type', '=', 'comment')
            ],
            string='Post Messages',
            help="Comments on forum post",
        ),
        'vote_count': fields.function(
            _get_vote_count, string="Votes", type='integer',
            store={
                'website.forum.post': (lambda self, cr, uid, ids, c={}: ids, ['vote_ids'], 10),
                'website.forum.post.vote': (_get_vote, [], 10),
            }
        ),
        'is_correct': fields.boolean('Valid Answer', help='Correct Answer/ Answer on this question accepted.'),
        'closed_reason_id': fields.many2one('website.forum.post.reason', 'Reason'),
        'closed_by': fields.many2one('res.users', 'Closed by'),
        'closed_date': fields.datetime('Closed on', readonly=True),
    }

    _defaults = {
        'state': 'active',
        'views': 0,
        'vote_count': 0,
        'active': True,
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        create_context = dict(context, mail_create_nolog=True)
        post_id = super(Post, self).create(cr, uid, vals, context=create_context)
        # post message + subtype depending on parent_id
        if vals.get("parent_id"):
            name, body, subtype = vals.get('name'), 'New Answer', 'website_forum.mt_answer_new'
        else:
            name, body, subtype = vals.get('name'), 'Post Created', 'website_forum.mt_question_new'
            #add 2 karma to user when asks question.
            self.pool['res.users'].write(cr, SUPERUSER_ID, [vals.get('user_id')], {'karma': 2}, context=context)
        self.message_post(cr, uid, [post_id], body=_(body), subtype=subtype, context=context)
        return post_id

    def write(self, cr, uid, ids, vals, context=None):
        res = super(Post, self).write(cr, uid, ids, vals, context=context)
        # if post content modify, notify followers
        if 'content' in vals or 'name' in vals:
            for post in self.browse(cr, uid, ids, context=context):
                if post.parent_id:
                    body, subtype = 'Answer Edited', 'website_forum.mt_answer_edit'
                else:
                    body, subtype = 'Question Edited', 'website_forum.mt_question_edit'
                self.message_post(cr, uid, [post.id], body=_(body), subtype=subtype, context=context)
        # update karma of related user when any answer accepted
        if vals.get('correct'):
            for post in self.browse(cr, uid, ids, context=context):
                value = -15
                if vals.get('correct'):
                    value = 15
                self.pool['res.users'].write(cr, SUPERUSER_ID, [post.user_id.id], {'karma': value}, context=context)
        return res

    def vote(self, cr, uid, ids, vote, context=None):
        print ids, vote
        return True
        # try:
        #     vote = int(vote)
        # except:
        #     return {'error': 'Wrong Vote Value'}

        # if not vote in [-1, 0, 1]:
        #     return {'error': 'Wrong Vote Value'}
        # user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        # # must have at least 10 karma to vote
        # if (vote == '-1') and (user.karma <= 10):
        #     return {'error': 'lessthen_10_karma'}
        # # user can not vote on own post
        # posts = self.pool['website.forum.post'].browse(cr, uid, ids, context=context)
        # if any(post.user_id.id == uid for post in posts):
        #     return {'error': 'own_post'}

        # vote_ids = self.pool['website.forum.post.vote'].search(cr, uid, [('post_id', 'in', post_ids), ('user_id', '=', uid)], context=context)
        # if vote_ids:
        #     self.pool['website.forum.post.vote'].write(cr, uid, vote_ids, {'vote': new_vote}, context=context)
        # else:
        #     self.popol['website.forum.post.vote'].create(cr, uid, {'post_id': post_id, 'vote': vote}, context=context)
        # post.refresh()
        # return {'vote_count': post.vote_count}

    def set_viewed(self, cr, uid, ids, context=None):
        for post in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [post.id], {'views': post.views + 1}, context=context)
        return True


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

    _columns = {
        'create_date': fields.datetime('Create Date', select=True, readonly=True),
        # 'is_forum': fields.boolean('Is Forum Member'),
        'karma': fields.integer('Karma'),
        'badge_ids': fields.one2many('gamification.badge.user', 'user_id', 'Badges'),
        'gold_badge': fields.function(_get_user_badge_level, string="Number of gold badges", type='integer', multi='badge_level'),
        'silver_badge': fields.function(_get_user_badge_level, string="Number of silver badges", type='integer', multi='badge_level'),
        'bronze_badge': fields.function(_get_user_badge_level, string="Number of bronze badges", type='integer', multi='badge_level'),
    }

    _defaults = {
        # 'is_forum': False,
        'karma': 0,
    }

    def add_karma(self, cr, uid, ids, karma, context=None):
        for user in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [user.id], {'karma': user.karma + karma}, context=context)
        return True


class Vote(osv.Model):
    _name = 'website.forum.post.vote'
    _description = 'Vote'
    _columns = {
        'post_id': fields.many2one('website.forum.post', 'Post', ondelete='cascade', required=True),
        'user_id': fields.many2one('res.users', 'User'),
        'vote': fields.selection([('1', '1'), ('-1', '-1'), ('0', '0')], 'Vote', required=True),
        'create_date': fields.datetime('Create Date', select=True, readonly=True),
    }
    _defaults = {
        'user_id': lambda self, cr, uid, ctx: uid,
        'vote': lambda *args: '1',
    }

    def update_karma(self, cr, uid, ids, new_vote='0', old_vote='0', context=None):
        karma_value = (int(new_vote) - int(old_vote)) * 10
        if karma_value:
            for vote in self.browse(cr, uid, ids, context=context):
                self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [vote.post_id.user_id.id], karma_value, context=context)
        return True

    def create(self, cr, uid, vals, context=None):
        vote_id = super(Vote, self).create(cr, uid, vals, context=context)
        self.update_karma(cr, uid, [vote_id], new_vote=vals.get('vote', '1'), context=context)
        # body = "voted %s %s" % ('answer' if record.parent_id else 'question','up' if vals.get('vote')==1 else 'down')
        # Post.message_post(cr, uid, [record.id], body=_(body), context=context)
        return vote_id

    def write(self, cr, uid, ids, values, context=None):
        res = super(Vote, self).write(cr, uid, ids, values, context=context)
        if 'vote' in values:
            for vote in self.browse(cr, uid, ids, context=context):
                self.update_karma(cr, uid, ids, new_vote=values['vote'], old_vote=vote.vote, context=context)
        return res


class Tags(osv.Model):
    _name = "website.forum.tag"
    _description = "Tag"
    _inherit = ['website.seo.metadata']

    def _get_posts_count(self, cr, uid, ids, field_name, arg, context=None):
        return dict((tag_id, self.pool['website.forum.post'].search_count(cr, uid, [('tag_ids', 'in', tag_id)], context=context)) for tag_id in ids)

    def _get_tag_from_post(self, cr, uid, ids, context=None):
        return list(set(
            [tag.id for post in self.pool['website.forum.post'].browse(cr, SUPERUSER_ID, ids, context=context) for tag in post.tag_ids]
        ))

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'forum_id': fields.many2one('website.forum', 'Forum', required=True),
        'posts_count': fields.function(
            _get_posts_count, type='integer', string="# of Posts",
            store={
                'website.forum.post': (_get_tag_from_post, ['tag_ids'], 10),
            }
        ),
    }
