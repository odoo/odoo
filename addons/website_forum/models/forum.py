# -*- coding: utf-8 -*-

import openerp
from openerp import SUPERUSER_ID
from openerp.addons.website.models.website import slug
from openerp.osv import osv, fields
from openerp.tools.translate import _


class Forum(osv.Model):
    """TDE TODO: set karma values for actions dynamic for a given forum"""
    _name = 'forum.forum'
    _description = 'Forums'
    _inherit = ['mail.thread', 'website.seo.metadata']
    # karma values
    _karma_upvote = 5  # done
    _karma_downvote = 50  # done
    _karma_answer_accept_own = 20  # done
    _karma_answer_accept_own_now = 50
    _karma_answer_accept_all = 500
    _karma_editor_link_files = 30  # done
    _karma_editor_clickable_link = 50
    _karma_comment = 1
    _karma_modo_retag = 75
    _karma_modo_flag = 100
    _karma_modo_flag_see_all = 300
    _karma_modo_unlink_comment = 750
    _karma_modo_edit_own = 1  # done
    _karma_modo_edit_all = 300  # done
    _karma_modo_close_own = 100  # done
    _karma_modo_close_all = 900  # done
    _karma_modo_unlink_own = 500  # done
    _karma_modo_unlink_all = 1000  # done
    # karma generation
    _karma_gen_quest_new = 2  # done
    _karma_gen_upvote_quest = 5  # done
    _karma_gen_downvote_quest = -2  # done
    _karma_gen_upvote_ans = 10  # done
    _karma_gen_downvote_ans = -2  # done
    _karma_gen_ans_accept = 2  # done
    _karma_gen_ans_accepted = 15  # done
    _karma_gen_ans_flagged = -100

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
    _order = "is_correct DESC, vote_count DESC"

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

    def _get_has_validated_answer(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, False)
        ans_ids = self.search(cr, uid, [('parent_id', 'in', ids), ('is_correct', '=', True)], context=context)
        for answer in self.browse(cr, uid, ans_ids, context=context):
            res[answer.parent_id.id] = True
        return res

    def _is_self_reply(self, cr, uid, ids, field_name, arg, context=None):
        res = dict.fromkeys(ids, False)
        for post in self.browse(cr, uid, ids, context=context):
            res[post.id] = post.parent_id and post.parent_id.create_uid == post.create_uid or False
        return res

    _columns = {
        'name': fields.char('Title'),
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
        'self_reply': fields.function(
            _is_self_reply, 'Reply to own question', type='boolean',
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
        'has_validated_answer': fields.function(
            _get_has_validated_answer, string='Has a Validated Answered', type='boolean',
            store={
                'forum.post': (_get_post_from_hierarchy, ['parent_id', 'child_ids', 'is_correct'], 10),
            }
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
            self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [uid], self.pool['forum.forum']._karma_gen_quest_new, context=context)
        return post_id

    def write(self, cr, uid, ids, vals, context=None):
        Forum = self.pool['forum.forum']
        # update karma when accepting/rejecting answers
        if 'is_correct' in vals:
            mult = 1 if vals['is_correct'] else -1
            for post in self.browse(cr, uid, ids, context=context):
                if vals['is_correct'] != post.is_correct:
                    self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [post.create_uid.id], Forum._karma_gen_ans_accepted * mult, context=context)
                    self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [uid], Forum._karma_gen_ans_accept * mult, context=context)
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
        cr.execute("""UPDATE forum_post SET views = views+1 WHERE id IN %s""", (tuple(ids),))
        return True

    def _get_access_link(self, cr, uid, mail, partner, context=None):
        post = self.pool['forum.post'].browse(cr, uid, mail.res_id, context=context)
        res_id = post.parent_id and "%s#answer-%s" % (post.parent_id.id, post.id) or post.id
        return "/forum/%s/question/%s" % (post.forum_id.id, res_id)


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
        if vals.get('vote', '1') == '1':
            karma = self.pool['forum.forum']._karma_upvote
        elif vals.get('vote', '1') == '-1':
            karma = self.pool['forum.forum']._karma_downvote
        post = self.pool['forum.post'].browse(cr, uid, vals['post_id'], context=context)
        self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [post.create_uid.id], karma, context=context)
        return vote_id

    def write(self, cr, uid, ids, values, context=None):
        def _get_karma_value(old_vote, new_vote, up_karma, down_karma):
            _karma_upd = {
                '-1': {'-1': 0, '0': -1 * down_karma, '1': -1 * down_karma + up_karma},
                '0': {'-1': 1 * down_karma, '0': 0, '1': up_karma},
                '1': {'-1': -1 * up_karma + down_karma, '0': -1 * up_karma, '1': 0}
            }
            return _karma_upd[old_vote][new_vote]
        if 'vote' in values:
            Forum = self.pool['forum.forum']
            for vote in self.browse(cr, uid, ids, context=context):
                if vote.post_id.parent_id:
                    karma_value = _get_karma_value(vote.vote, values['vote'], Forum._karma_gen_upvote_ans, Forum._karma_gen_downvote_ans)
                else:
                    karma_value = _get_karma_value(vote.vote, values['vote'], Forum._karma_gen_upvote_quest, Forum._karma_gen_downvote_quest)
                self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [vote.post_id.create_uid.id], karma_value, context=context)
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
