# -*- coding: utf-8 -*-

import openerp

from openerp import SUPERUSER_ID
from openerp.addons.website.models.website import slug
from openerp.osv import osv, fields
from openerp.tools.translate import _


class Forum(osv.Model):
    _name = 'forum.forum'
    _description = 'Forums'
    _inherit = ['website.seo.metadata']

    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'faq': fields.html('Guidelines'),
        'description': fields.html('Description'),
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

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        create_context = dict(context, mail_create_nolog=True)
        return super(Forum, self).create(cr, uid, values, context=create_context)


class Post(osv.Model):
    _name = 'forum.post'
    _description = 'Forum Post'
    _inherit = ['mail.thread', 'website.seo.metadata']

    def _get_user_vote(self, cr, uid, ids, field_name, arg, context):
        res = dict.fromkeys(ids, 0)
        vote_ids = self.pool['forum.post.vote'].search(cr, uid, [('post_id', 'in', ids), ('user_id', '=', uid)], context=context)
        for vote in self.pool['forum.post.vote'].browse(cr, uid, vote_ids, context=context):
            res[vote.post_id.id] = vote.vote
        return res

    def _get_vote_count(self, cr, uid, ids, field_name, arg, context):
        res = dict.fromkeys(ids, 0)
        for post in self.browse(cr, uid, ids, context=context):
            for vote in post.vote_ids:
                res[post.id] += int(vote.vote)
        return res

    def _get_post_from_vote(self, cr, uid, ids, context=None):
        result = {}
        for vote in self.pool['forum.post.vote'].browse(cr, uid, ids, context=context):
            result[vote.post_id.id] = True
        return result.keys()

    def _get_user_favourite(self, cr, uid, ids, field_name, arg, context):
        res = dict.fromkeys(ids, False)
        for post in self.browse(cr, uid, ids, context=context):
            if uid in [f.id for f in post.favourite_ids]:
                res[post.id] = True
        return res

    def _get_favorite_count(self, cr, uid, ids, field_name, arg, context):
        res = dict.fromkeys(ids, 0)
        for post in self.browse(cr, uid, ids, context=context):
            res[post.id] += len(post.favourite_ids)
        return res

    def _get_post_from_hierarchy(self, cr, uid, ids, context=None):
        post_ids = set(ids)
        for post in self.browse(cr, SUPERUSER_ID, ids, context=context):
            if post.parent_id:
                post_ids.add(post.parent_id.id)
        return list(post_ids)

    def _get_child_count(self, cr, uid, ids, field_name=False, arg={}, context=None):
        res = dict.fromkeys(ids, 0)
        for post in self.browse(cr, uid, ids, context=context):
            if post.parent_id:
                res[post.parent_id.id] = len(post.parent_id.child_ids)
            else:
                res[post.id] = len(post.child_ids)
        return res

    def _get_uid_answered(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for post in self.browse(cr, uid, ids, context=context):
            res[post.id] = any(answer.create_uid.id == uid for answer in post.child_ids)
        return res

    def _is_self_reply(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for post in self.browse(cr, uid, ids, context=context):
            res[post.id] = post.parent_id and post.parent_id.create_uid == post.create_uid or False
        return res

    _columns = {
        'name': fields.char('Title', size=128),
        'forum_id': fields.many2one('forum.forum', 'Forum', required=True),
        'content': fields.html('Content'),
        'tag_ids': fields.many2many('forum.tag', 'forum_tag_rel', 'forum_id', 'forum_tag_id', 'Tags'),
        'state': fields.selection([('active', 'Active'), ('close', 'Close'), ('offensive', 'Offensive')], 'Status'),
        'views': fields.integer('Number of Views'),
        'active': fields.boolean('Active'),
        'is_correct': fields.boolean('Valid Answer', help='Correct Answer or Answer on this question accepted.'),
        'website_message_ids': fields.one2many(
            'mail.message', 'res_id',
            domain=lambda self: [
                '&', ('model', '=', self._name), ('type', '=', 'comment')
            ],
            string='Post Messages', help="Comments on forum post",
        ),
        # history
        'create_date': fields.datetime('Asked on', select=True, readonly=True),
        'create_uid': fields.many2one('res.users', 'Created by', select=True, readonly=True),
        'write_date': fields.datetime('Update on', select=True, readonly=True),
        'write_uid': fields.many2one('res.users', 'Updated by', select=True, readonly=True),
        # vote fields
        'vote_ids': fields.one2many('forum.post.vote', 'post_id', 'Votes'),
        'user_vote': fields.function(_get_user_vote, string='My Vote', type='integer'),
        'vote_count': fields.function(
            _get_vote_count, string="Votes", type='integer',
            store={
                'forum.post': (lambda self, cr, uid, ids, c={}: ids, ['vote_ids'], 10),
                'forum.post.vote': (_get_post_from_vote, [], 10),
            }),
        # favorite fields
        'favourite_ids': fields.many2many('res.users', string='Favourite'),
        'user_favourite': fields.function(_get_user_favourite, string="My Favourite", type='boolean'),
        'favourite_count': fields.function(
            _get_favorite_count, string='Favorite Count', type='integer',
            store={
                'forum.post': (lambda self, cr, uid, ids, c={}: ids, ['favourite_ids'], 10),
            }),
        # hierarchy
        'parent_id': fields.many2one('forum.post', 'Question', ondelete='cascade'),
        'self_reply': fields.function(_is_self_reply, 'Reply to own question', type='boolean',
            store={
                'forum.post': (lambda self, cr, uid, ids, c={}: ids, ['parent_id', 'create_uid'], 10),
            }),
        'child_ids': fields.one2many('forum.post', 'parent_id', 'Answers'),
        'child_count': fields.function(
            _get_child_count, string="Answers", type='integer',
            store={
                'forum.post': (_get_post_from_hierarchy, ['parent_id', 'child_ids'], 10),
            }),
        'uid_has_answered': fields.function(
            _get_uid_answered, string='Has Answered', type='boolean',
        ),
        # closing
        'closed_reason_id': fields.many2one('forum.post.reason', 'Reason'),
        'closed_uid': fields.many2one('res.users', 'Closed by', select=1),
        'closed_date': fields.datetime('Closed on', readonly=True),
    }

    _defaults = {
        'state': 'active',
        'views': 0,
        'active': True,
        'vote_ids': list(),
        'favourite_ids': list(),
        'child_ids': list(),
    }

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        create_context = dict(context, mail_create_nolog=True)
        post_id = super(Post, self).create(cr, uid, vals, context=create_context)
        # post message + subtype depending on parent_id
        if vals.get("parent_id"):
            parent = self.browse(cr, SUPERUSER_ID, vals['parent_id'], context=context)
            body = _('<p><a href="forum/%s/question/%s">New Answer Posted</a></p>' % (slug(parent.forum_id), slug(parent)))
            self.message_post(cr, uid, parent.id, subject=_('Re: %s') % parent.name, body=body, subtype='website_forum.mt_answer_new', context=context)
        else:
            self.message_post(cr, uid, post_id, subject=vals.get('name', ''), body=_('New Question Created'), subtype='website_forum.mt_question_new', context=context)
            self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [uid], 2, context=context)
        return post_id

    def write(self, cr, uid, ids, vals, context=None):
        res = super(Post, self).write(cr, uid, ids, vals, context=context)
        # if post content modify, notify followers
        if 'content' in vals or 'name' in vals:
            for post in self.browse(cr, uid, ids, context=context):
                if post.parent_id:
                    body, subtype = _('Answer Edited'), 'website_forum.mt_answer_edit'
                    obj_id = post.parent_id.id
                else:
                    body, subtype = _('Question Edited'), 'website_forum.mt_question_edit'
                    obj_id = post.id
                self.message_post(cr, uid, obj_id, body=_(body), subtype=subtype, context=context)
        # update karma of related user when any answer accepted
        if 'correct' in vals:
            for post in self.browse(cr, uid, ids, context=context):
                karma_value = 15 if vals.get('correct') else -15
                self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [post.create_uid.id], {'karma': karma_value}, context=context)
        return res

    def vote(self, cr, uid, ids, upvote=True, context=None):
        Vote = self.pool['forum.post.vote']
        vote_ids = Vote.search(cr, uid, [('post_id', 'in', ids), ('user_id', '=', uid)], context=context)
        if vote_ids:
            for vote in Vote.browse(cr, uid, vote_ids, context=context):
                if upvote:
                    new_vote = '0' if vote.vote == '-1' else '1'
                else:
                    new_vote = '0' if vote.vote == '1' else '-1'
                Vote.write(cr, uid, vote_ids, {'vote': new_vote}, context=context)
        else:
            for post_id in ids:
                new_vote = '1' if upvote else '-1'
                Vote.create(cr, uid, {'post_id': post_id, 'vote': new_vote}, context=context)
        return {'vote_count': self._get_vote_count(cr, uid, ids, None, None, context=context)[ids[0]]}

    def set_viewed(self, cr, uid, ids, context=None):
        for post in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [post.id], {'views': post.views + 1}, context=context)
        return True


class PostReason(osv.Model):
    _name = "forum.post.reason"
    _description = "Post Closing Reason"
    _order = 'name'
    _columns = {
        'name': fields.char('Post Reason', required=True, translate=True),
    }


class Vote(osv.Model):
    _name = 'forum.post.vote'
    _description = 'Vote'
    _columns = {
        'post_id': fields.many2one('forum.post', 'Post', ondelete='cascade', required=True),
        'user_id': fields.many2one('res.users', 'User', required=True),
        'vote': fields.selection([('1', '1'), ('-1', '-1'), ('0', '0')], 'Vote', required=True),
        'create_date': fields.datetime('Create Date', select=True, readonly=True),
    }
    _defaults = {
        'user_id': lambda self, cr, uid, ctx: uid,
        'vote': lambda *args: '1',
    }

    def create(self, cr, uid, vals, context=None):
        vote_id = super(Vote, self).create(cr, uid, vals, context=context)
        karma_value = int(vals.get('vote', '1')) * 10
        post = self.pool['forum.post'].browse(cr, uid, vals.get('post_id'), context=context)
        self.pool['res.users'].add_karma(cr, SUPERUSER_ID, post.create_uid.id, karma_value, context=context)
        return vote_id

    def write(self, cr, uid, ids, values, context=None):
        if 'vote' in values:
            for vote in self.browse(cr, uid, ids, context=context):
                karma_value = (int(values.get('vote')) - int(vote.vote)) * 10
                self.pool['res.users'].add_karma(cr, SUPERUSER_ID, vote.post_id.create_uid.id, karma_value, context=context)
        res = super(Vote, self).write(cr, uid, ids, values, context=context)
        return res


class Tags(osv.Model):
    _name = "forum.tag"
    _description = "Tag"
    _inherit = ['website.seo.metadata']

    def _get_posts_count(self, cr, uid, ids, field_name, arg, context=None):
        return dict((tag_id, self.pool['forum.post'].search_count(cr, uid, [('tag_ids', 'in', tag_id)], context=context)) for tag_id in ids)

    def _get_tag_from_post(self, cr, uid, ids, context=None):
        return list(set(
            [tag.id for post in self.pool['forum.post'].browse(cr, SUPERUSER_ID, ids, context=context) for tag in post.tag_ids]
        ))

    _columns = {
        'name': fields.char('Name', required=True),
        'forum_id': fields.many2one('forum.forum', 'Forum', required=True),
        'post_ids': fields.many2many('forum.post', 'forum_tag_rel', 'tag_id', 'post_id', 'Posts'),
        'posts_count': fields.function(
            _get_posts_count, type='integer', string="Number of Posts",
            store={
                'forum.post': (_get_tag_from_post, ['tag_ids'], 10),
            }
        ),
        'create_uid': fields.many2one('res.users', 'Created by', readonly=True),
    }
