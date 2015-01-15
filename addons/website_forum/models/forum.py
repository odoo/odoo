# -*- coding: utf-8 -*-

from datetime import datetime
import uuid
from werkzeug.exceptions import Forbidden

import logging
import openerp

from openerp import api, tools
from openerp import SUPERUSER_ID
from openerp.addons.website.models.website import slug
from openerp.exceptions import Warning
from openerp.osv import osv, fields
from openerp.tools import html2plaintext
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

class KarmaError(Forbidden):
    """ Karma-related error, used for forum and posts. """
    pass


class Forum(osv.Model):
    """TDE TODO: set karma values for actions dynamic for a given forum"""
    _name = 'forum.forum'
    _description = 'Forums'
    _inherit = ['mail.thread', 'website.seo.metadata']

    def init(self, cr):
        """ Add forum uuid for user email validation. """
        forum_uuids = self.pool['ir.config_parameter'].search(cr, SUPERUSER_ID, [('key', '=', 'website_forum.uuid')])
        if not forum_uuids:
            self.pool['ir.config_parameter'].set_param(cr, SUPERUSER_ID, 'website_forum.uuid', str(uuid.uuid4()), ['base.group_system'])

    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'faq': fields.html('Guidelines'),
        'description': fields.html('Description', translate=True),
        # karma generation
        'karma_gen_question_new': fields.integer('Asking a question'),
        'karma_gen_question_upvote': fields.integer('Question upvoted'),
        'karma_gen_question_downvote': fields.integer('Question downvoted'),
        'karma_gen_answer_upvote': fields.integer('Answer upvoted'),
        'karma_gen_answer_downvote': fields.integer('Answer downvoted'),
        'karma_gen_answer_accept': fields.integer('Accepting an answer'),
        'karma_gen_answer_accepted': fields.integer('Answer accepted'),
        'karma_gen_answer_flagged': fields.integer('Answer flagged'),
        # karma-based actions
        'karma_ask': fields.integer('Ask a question'),
        'karma_answer': fields.integer('Answer a question'),
        'karma_edit_own': fields.integer('Edit its own posts'),
        'karma_edit_all': fields.integer('Edit all posts'),
        'karma_close_own': fields.integer('Close its own posts'),
        'karma_close_all': fields.integer('Close all posts'),
        'karma_unlink_own': fields.integer('Delete its own posts'),
        'karma_unlink_all': fields.integer('Delete all posts'),
        'karma_upvote': fields.integer('Upvote'),
        'karma_downvote': fields.integer('Downvote'),
        'karma_answer_accept_own': fields.integer('Accept an answer on its own questions'),
        'karma_answer_accept_all': fields.integer('Accept an answer to all questions'),
        'karma_editor_link_files': fields.integer('Linking files (Editor)'),
        'karma_editor_clickable_link': fields.integer('Clickable links (Editor)'),
        'karma_comment_own': fields.integer('Comment its own posts'),
        'karma_comment_all': fields.integer('Comment all posts'),
        'karma_comment_convert_own': fields.integer('Convert its own answers to comments and vice versa'),
        'karma_comment_convert_all': fields.integer('Convert all answers to comments and vice versa'),
        'karma_comment_unlink_own': fields.integer('Unlink its own comments'),
        'karma_comment_unlink_all': fields.integer('Unlink all comments'),
        'karma_retag': fields.integer('Change question tags'),
        'karma_flag': fields.integer('Flag a post as offensive'),
    }

    def _get_default_faq(self, cr, uid, context=None):
        fname = openerp.modules.get_module_resource('website_forum', 'data', 'forum_default_faq.html')
        with open(fname, 'r') as f:
            return f.read()
        return False

    _defaults = {
        'description': 'This community is for professionals and enthusiasts of our products and services.',
        'faq': _get_default_faq,
        'karma_gen_question_new': 0,  # set to null for anti spam protection
        'karma_gen_question_upvote': 5,
        'karma_gen_question_downvote': -2,
        'karma_gen_answer_upvote': 10,
        'karma_gen_answer_downvote': -2,
        'karma_gen_answer_accept': 2,
        'karma_gen_answer_accepted': 15,
        'karma_gen_answer_flagged': -100,
        'karma_ask': 3,  # set to not null for anti spam protection
        'karma_answer': 3,  # set to not null for anti spam protection
        'karma_edit_own': 1,
        'karma_edit_all': 300,
        'karma_close_own': 100,
        'karma_close_all': 500,
        'karma_unlink_own': 500,
        'karma_unlink_all': 1000,
        'karma_upvote': 5,
        'karma_downvote': 50,
        'karma_answer_accept_own': 20,
        'karma_answer_accept_all': 500,
        'karma_editor_link_files': 20,
        'karma_editor_clickable_link': 20,
        'karma_comment_own': 3,
        'karma_comment_all': 5,
        'karma_comment_convert_own': 50,
        'karma_comment_convert_all': 500,
        'karma_comment_unlink_own': 50,
        'karma_comment_unlink_all': 500,
        'karma_retag': 75,
        'karma_flag': 500,
    }

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        create_context = dict(context, mail_create_nolog=True)
        return super(Forum, self).create(cr, uid, values, context=create_context)

    def _tag_to_write_vals(self, cr, uid, ids, tags='', context=None):
        User = self.pool['res.users']
        Tag = self.pool['forum.tag']
        result = {}
        for forum in self.browse(cr, uid, ids, context=context):
            post_tags = []
            existing_keep = []
            for tag in filter(None, tags.split(',')):
                if tag.startswith('_'):  # it's a new tag
                    # check that not already created meanwhile or maybe excluded by the limit on the search
                    tag_ids = Tag.search(cr, uid, [('name', '=', tag[1:])], context=context)
                    if tag_ids:
                        existing_keep.append(int(tag_ids[0]))
                    else:
                        # check if user have Karma needed to create need tag
                        user = User.browse(cr, uid, uid, context=context)
                        if user.exists() and user.karma >= forum.karma_retag:
                            post_tags.append((0, 0, {'name': tag[1:], 'forum_id': forum.id}))
                else:
                    existing_keep.append(int(tag))
            post_tags.insert(0, [6, 0, existing_keep])
            result[forum.id] = post_tags

        return result


class Post(osv.Model):
    _name = 'forum.post'
    _description = 'Forum Post'
    _inherit = ['mail.thread', 'website.seo.metadata']
    _order = "is_correct DESC, vote_count DESC, write_date DESC"

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

    def _get_post_karma_rights(self, cr, uid, ids, field_name, arg, context=None):
        user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        res = dict.fromkeys(ids, False)
        for post in self.browse(cr, uid, ids, context=context):
            res[post.id] = {
                'karma_ask': post.forum_id.karma_ask,
                'karma_answer': post.forum_id.karma_answer,
                'karma_accept': post.parent_id and post.parent_id.create_uid.id == uid and post.forum_id.karma_answer_accept_own or post.forum_id.karma_answer_accept_all,
                'karma_edit': post.create_uid.id == uid and post.forum_id.karma_edit_own or post.forum_id.karma_edit_all,
                'karma_close': post.create_uid.id == uid and post.forum_id.karma_close_own or post.forum_id.karma_close_all,
                'karma_unlink': post.create_uid.id == uid and post.forum_id.karma_unlink_own or post.forum_id.karma_unlink_all,
                'karma_upvote': post.forum_id.karma_upvote,
                'karma_downvote': post.forum_id.karma_downvote,
                'karma_comment': post.create_uid.id == uid and post.forum_id.karma_comment_own or post.forum_id.karma_comment_all,
                'karma_comment_convert': post.create_uid.id == uid and post.forum_id.karma_comment_convert_own or post.forum_id.karma_comment_convert_all,
            }
            res[post.id].update({
                'can_ask': uid == SUPERUSER_ID or user.karma >= res[post.id]['karma_ask'],
                'can_answer': uid == SUPERUSER_ID or user.karma >= res[post.id]['karma_answer'],
                'can_accept': uid == SUPERUSER_ID or user.karma >= res[post.id]['karma_accept'],
                'can_edit': uid == SUPERUSER_ID or user.karma >= res[post.id]['karma_edit'],
                'can_close': uid == SUPERUSER_ID or user.karma >= res[post.id]['karma_close'],
                'can_unlink': uid == SUPERUSER_ID or user.karma >= res[post.id]['karma_unlink'],
                'can_upvote': uid == SUPERUSER_ID or user.karma >= res[post.id]['karma_upvote'],
                'can_downvote': uid == SUPERUSER_ID or user.karma >= res[post.id]['karma_downvote'],
                'can_comment': uid == SUPERUSER_ID or user.karma >= res[post.id]['karma_comment'],
                'can_comment_convert': uid == SUPERUSER_ID or user.karma >= res[post.id]['karma_comment_convert'],
            })
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
                '&', ('model', '=', self._name), ('type', 'in', ['email', 'comment'])
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
        # karma
        'karma_ask': fields.function(_get_post_karma_rights, string='Karma to ask', type='integer', multi='_get_post_karma_rights'),
        'karma_answer': fields.function(_get_post_karma_rights, string='Karma to answer', type='integer', multi='_get_post_karma_rights'),
        'karma_accept': fields.function(_get_post_karma_rights, string='Karma to accept this answer', type='integer', multi='_get_post_karma_rights'),
        'karma_edit': fields.function(_get_post_karma_rights, string='Karma to edit', type='integer', multi='_get_post_karma_rights'),
        'karma_close': fields.function(_get_post_karma_rights, string='Karma to close', type='integer', multi='_get_post_karma_rights'),
        'karma_unlink': fields.function(_get_post_karma_rights, string='Karma to unlink', type='integer', multi='_get_post_karma_rights'),
        'karma_upvote': fields.function(_get_post_karma_rights, string='Karma to upvote', type='integer', multi='_get_post_karma_rights'),
        'karma_downvote': fields.function(_get_post_karma_rights, string='Karma to downvote', type='integer', multi='_get_post_karma_rights'),
        'karma_comment': fields.function(_get_post_karma_rights, string='Karma to comment', type='integer', multi='_get_post_karma_rights'),
        'karma_comment_convert': fields.function(_get_post_karma_rights, string='karma to convert as a comment', type='integer', multi='_get_post_karma_rights'),
        # access rights
        'can_ask': fields.function(_get_post_karma_rights, string='Can Ask', type='boolean', multi='_get_post_karma_rights'),
        'can_answer': fields.function(_get_post_karma_rights, string='Can Answer', type='boolean', multi='_get_post_karma_rights'),
        'can_accept': fields.function(_get_post_karma_rights, string='Can Accept', type='boolean', multi='_get_post_karma_rights'),
        'can_edit': fields.function(_get_post_karma_rights, string='Can Edit', type='boolean', multi='_get_post_karma_rights'),
        'can_close': fields.function(_get_post_karma_rights, string='Can Close', type='boolean', multi='_get_post_karma_rights'),
        'can_unlink': fields.function(_get_post_karma_rights, string='Can Unlink', type='boolean', multi='_get_post_karma_rights'),
        'can_upvote': fields.function(_get_post_karma_rights, string='Can Upvote', type='boolean', multi='_get_post_karma_rights'),
        'can_downvote': fields.function(_get_post_karma_rights, string='Can Downvote', type='boolean', multi='_get_post_karma_rights'),
        'can_comment': fields.function(_get_post_karma_rights, string='Can Comment', type='boolean', multi='_get_post_karma_rights'),
        'can_comment_convert': fields.function(_get_post_karma_rights, string='Can Convert to Comment', type='boolean', multi='_get_post_karma_rights'),
    }

    _defaults = {
        'state': 'active',
        'views': 0,
        'active': True,
        'vote_ids': list(),
        'favourite_ids': list(),
        'child_ids': list(),
    }

    def name_get(self, cr, uid, ids, context=None):
        result = []
        for post in self.browse(cr, uid, ids, context=context):
            if post.parent_id and not post.name:
                result.append((post.id, '%s (%s)' % (post.parent_id.name, post.id)))
            else:
                result.append((post.id, '%s' % (post.name)))
        return result

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        create_context = dict(context, mail_create_nolog=True)
        post_id = super(Post, self).create(cr, uid, vals, context=create_context)
        post = self.browse(cr, uid, post_id, context=context)
        # karma-based access
        if not post.parent_id and not post.can_ask:
            raise KarmaError('Not enough karma to create a new question')
        elif post.parent_id and not post.can_answer:
            raise KarmaError('Not enough karma to answer to a question')
        # messaging and chatter
        base_url = self.pool['ir.config_parameter'].get_param(cr, uid, 'web.base.url')
        if post.parent_id:
            body = _(
                '<p>A new answer for <i>%s</i> has been posted. <a href="%s/forum/%s/question/%s">Click here to access the post.</a></p>' %
                (post.parent_id.name, base_url, slug(post.parent_id.forum_id), slug(post.parent_id))
            )
            self.message_post(cr, uid, post.parent_id.id, subject=_('Re: %s') % post.parent_id.name, body=body, subtype='website_forum.mt_answer_new', context=context)
        else:
            body = _(
                '<p>A new question <i>%s</i> has been asked on %s. <a href="%s/forum/%s/question/%s">Click here to access the question.</a></p>' %
                (post.name, post.forum_id.name, base_url, slug(post.forum_id), slug(post))
            )
            self.message_post(cr, uid, post_id, subject=post.name, body=body, subtype='website_forum.mt_question_new', context=context)
            self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [uid], post.forum_id.karma_gen_question_new, context=context)
        return post_id

    def write(self, cr, uid, ids, vals, context=None):
        posts = self.browse(cr, uid, ids, context=context)
        if 'state' in vals:
            if vals['state'] in ['active', 'close'] and any(not post.can_close for post in posts):
                raise KarmaError('Not enough karma to close or reopen a post.')
        if 'active' in vals:
            if any(not post.can_unlink for post in posts):
                raise KarmaError('Not enough karma to delete or reactivate a post')
        if 'is_correct' in vals:
            if any(not post.can_accept for post in posts):
                raise KarmaError('Not enough karma to accept or refuse an answer')
            # update karma except for self-acceptance
            mult = 1 if vals['is_correct'] else -1
            for post in self.browse(cr, uid, ids, context=context):
                if vals['is_correct'] != post.is_correct and post.create_uid.id != uid:
                    self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [post.create_uid.id], post.forum_id.karma_gen_answer_accepted * mult, context=context)
                    self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [uid], post.forum_id.karma_gen_answer_accept * mult, context=context)
        if any(key not in ['state', 'active', 'is_correct', 'closed_uid', 'closed_date', 'closed_reason_id'] for key in vals.keys()) and any(not post.can_edit for post in posts):
            raise KarmaError('Not enough karma to edit a post.')

        res = super(Post, self).write(cr, uid, ids, vals, context=context)
        # if post content modify, notify followers
        if 'content' in vals or 'name' in vals:
            for post in posts:
                if post.parent_id:
                    body, subtype = _('Answer Edited'), 'website_forum.mt_answer_edit'
                    obj_id = post.parent_id.id
                else:
                    body, subtype = _('Question Edited'), 'website_forum.mt_question_edit'
                    obj_id = post.id
                self.message_post(cr, uid, obj_id, body=body, subtype=subtype, context=context)
        return res


    def reopen(self, cr, uid, ids, context=None):
        if any(post.parent_id or post.state != 'close'
                    for post in self.browse(cr, uid, ids, context=context)):
            return False

        reason_offensive = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'website_forum.reason_7')
        reason_spam = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'website_forum.reason_8')
        for post in self.browse(cr, uid, ids, context=context):
            if post.closed_reason_id.id in (reason_offensive, reason_spam):
                _logger.info('Upvoting user <%s>, reopening spam/offensive question',
                             post.create_uid)
                # TODO: in master, consider making this a tunable karma parameter
                self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [post.create_uid.id],
                                                 post.forum_id.karma_gen_question_downvote * -5,
                                                 context=context)
        self.pool['forum.post'].write(cr, SUPERUSER_ID, ids, {'state': 'active'}, context=context)

    def close(self, cr, uid, ids, reason_id, context=None):
        if any(post.parent_id for post in self.browse(cr, uid, ids, context=context)):
            return False

        reason_offensive = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'website_forum.reason_7')
        reason_spam = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'website_forum.reason_8')
        if reason_id in (reason_offensive, reason_spam):
            for post in self.browse(cr, uid, ids, context=context):
                _logger.info('Downvoting user <%s> for posting spam/offensive contents',
                             post.create_uid)
                # TODO: in master, consider making this a tunable karma parameter
                self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [post.create_uid.id],
                                                 post.forum_id.karma_gen_question_downvote * 5,
                                                 context=context)

        self.pool['forum.post'].write(cr, uid, ids, {
            'state': 'close',
            'closed_uid': uid,
            'closed_date': datetime.today().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),
            'closed_reason_id': reason_id,
        }, context=context)

    def unlink(self, cr, uid, ids, context=None):
        posts = self.browse(cr, uid, ids, context=context)
        if any(not post.can_unlink for post in posts):
            raise KarmaError('Not enough karma to unlink a post')
        # if unlinking an answer with accepted answer: remove provided karma
        for post in posts:
            if post.is_correct:
                self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [post.create_uid.id], post.forum_id.karma_gen_answer_accepted * -1, context=context)
                self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [uid], post.forum_id.karma_gen_answer_accept * -1, context=context)
        return super(Post, self).unlink(cr, uid, ids, context=context)

    def vote(self, cr, uid, ids, upvote=True, context=None):
        Vote = self.pool['forum.post.vote']
        vote_ids = Vote.search(cr, uid, [('post_id', 'in', ids), ('user_id', '=', uid)], context=context)
        new_vote = '1' if upvote else '-1'
        voted_forum_ids = set()
        if vote_ids:
            for vote in Vote.browse(cr, uid, vote_ids, context=context):
                if upvote:
                    new_vote = '0' if vote.vote == '-1' else '1'
                else:
                    new_vote = '0' if vote.vote == '1' else '-1'
                Vote.write(cr, uid, vote_ids, {'vote': new_vote}, context=context)
                voted_forum_ids.add(vote.post_id.id)
        for post_id in set(ids) - voted_forum_ids:
            for post_id in ids:
                Vote.create(cr, uid, {'post_id': post_id, 'vote': new_vote}, context=context)
        return {'vote_count': self._get_vote_count(cr, uid, ids, None, None, context=context)[ids[0]], 'user_vote': new_vote}

    def convert_answer_to_comment(self, cr, uid, id, context=None):
        """ Tools to convert an answer (forum.post) to a comment (mail.message).
        The original post is unlinked and a new comment is posted on the question
        using the post create_uid as the comment's author. """
        post = self.browse(cr, SUPERUSER_ID, id, context=context)
        if not post.parent_id:
            return False

        # karma-based action check: use the post field that computed own/all value
        if not post.can_comment_convert:
            raise KarmaError('Not enough karma to convert an answer to a comment')

        # post the message
        question = post.parent_id
        values = {
            'author_id': post.create_uid.partner_id.id,
            'body': html2plaintext(post.content),
            'type': 'comment',
            'subtype': 'mail.mt_comment',
            'date': post.create_date,
        }
        message_id = self.pool['forum.post'].message_post(
            cr, uid, question.id,
            context=dict(context, mail_create_nosubscribe=True),
            **values)

        # unlink the original answer, using SUPERUSER_ID to avoid karma issues
        self.pool['forum.post'].unlink(cr, SUPERUSER_ID, [post.id], context=context)

        return message_id

    def convert_comment_to_answer(self, cr, uid, message_id, default=None, context=None):
        """ Tool to convert a comment (mail.message) into an answer (forum.post).
        The original comment is unlinked and a new answer from the comment's author
        is created. Nothing is done if the comment's author already answered the
        question. """
        comment = self.pool['mail.message'].browse(cr, SUPERUSER_ID, message_id, context=context)
        post = self.pool['forum.post'].browse(cr, uid, comment.res_id, context=context)
        user = self.pool['res.users'].browse(cr, uid, uid, context=context)
        if not comment.author_id or not comment.author_id.user_ids:  # only comment posted by users can be converted
            return False

        # karma-based action check: must check the message's author to know if own / all
        karma_convert = comment.author_id.id == user.partner_id.id and post.forum_id.karma_comment_convert_own or post.forum_id.karma_comment_convert_all
        can_convert = uid == SUPERUSER_ID or user.karma >= karma_convert
        if not can_convert:
            raise KarmaError('Not enough karma to convert a comment to an answer')

        # check the message's author has not already an answer
        question = post.parent_id if post.parent_id else post
        post_create_uid = comment.author_id.user_ids[0]
        if any(answer.create_uid.id == post_create_uid.id for answer in question.child_ids):
            return False

        # create the new post
        post_values = {
            'forum_id': question.forum_id.id,
            'content': comment.body,
            'parent_id': question.id,
        }
        # done with the author user to have create_uid correctly set
        new_post_id = self.pool['forum.post'].create(cr, post_create_uid.id, post_values, context=context)

        # delete comment
        self.pool['mail.message'].unlink(cr, SUPERUSER_ID, [comment.id], context=context)

        return new_post_id

    def unlink_comment(self, cr, uid, id, message_id, context=None):
        comment = self.pool['mail.message'].browse(cr, SUPERUSER_ID, message_id, context=context)
        post = self.pool['forum.post'].browse(cr, uid, id, context=context)
        user = self.pool['res.users'].browse(cr, SUPERUSER_ID, uid, context=context)
        if not comment.model == 'forum.post' or not comment.res_id == id:
            return False

        # karma-based action check: must check the message's author to know if own or all
        karma_unlink = comment.author_id.id == user.partner_id.id and post.forum_id.karma_comment_unlink_own or post.forum_id.karma_comment_unlink_all
        can_unlink = uid == SUPERUSER_ID or user.karma >= karma_unlink
        if not can_unlink:
            raise KarmaError('Not enough karma to unlink a comment')

        return self.pool['mail.message'].unlink(cr, SUPERUSER_ID, [message_id], context=context)

    def set_viewed(self, cr, uid, ids, context=None):
        cr.execute("""UPDATE forum_post SET views = views+1 WHERE id IN %s""", (tuple(ids),))
        return True

    def _get_access_link(self, cr, uid, mail, partner, context=None):
        post = self.pool['forum.post'].browse(cr, uid, mail.res_id, context=context)
        res_id = post.parent_id and "%s#answer-%s" % (post.parent_id.id, post.id) or post.id
        return "/forum/%s/question/%s" % (post.forum_id.id, res_id)

    @api.cr_uid_ids_context
    def message_post(self, cr, uid, thread_id, type='notification', subtype=None, context=None, **kwargs):
        if thread_id and type == 'comment':  # user comments have a restriction on karma
            if isinstance(thread_id, (list, tuple)):
                post_id = thread_id[0]
            else:
                post_id = thread_id
            post = self.browse(cr, uid, post_id, context=context)
            if not post.can_comment:
                raise KarmaError('Not enough karma to comment')
        return super(Post, self).message_post(cr, uid, thread_id, type=type, subtype=subtype, context=context, **kwargs)


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

        # TODO master: store these two
        'forum_id': fields.related('post_id', 'forum_id', type='many2one', relation='forum.forum', string='Forum'),
        'recipient_id': fields.related('post_id', 'create_uid', type='many2one', relation='res.users', string='To', help="The user receiving the vote"),
    }
    _defaults = {
        'user_id': lambda self, cr, uid, ctx: uid,
        'vote': lambda *args: '1',
    }

    def _get_karma_value(self, old_vote, new_vote, up_karma, down_karma):
        _karma_upd = {
            '-1': {'-1': 0, '0': -1 * down_karma, '1': -1 * down_karma + up_karma},
            '0': {'-1': 1 * down_karma, '0': 0, '1': up_karma},
            '1': {'-1': -1 * up_karma + down_karma, '0': -1 * up_karma, '1': 0}
        }
        return _karma_upd[old_vote][new_vote]

    def create(self, cr, uid, vals, context=None):
        vote_id = super(Vote, self).create(cr, uid, vals, context=context)
        vote = self.browse(cr, uid, vote_id, context=context)

        # own post check
        if vote.user_id.id == vote.post_id.create_uid.id:
            raise Warning('Not allowed to vote for its own post')
        # karma check
        if vote.vote == '1' and not vote.post_id.can_upvote:
            raise KarmaError('Not enough karma to upvote.')
        elif vote.vote == '-1' and not vote.post_id.can_downvote:
            raise KarmaError('Not enough karma to downvote.')

        # karma update
        if vote.post_id.parent_id:
            karma_value = self._get_karma_value('0', vote.vote, vote.forum_id.karma_gen_answer_upvote, vote.forum_id.karma_gen_answer_downvote)
        else:
            karma_value = self._get_karma_value('0', vote.vote, vote.forum_id.karma_gen_question_upvote, vote.forum_id.karma_gen_question_downvote)
        self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [vote.recipient_id.id], karma_value, context=context)
        return vote_id

    def write(self, cr, uid, ids, values, context=None):
        if 'vote' in values:
            for vote in self.browse(cr, uid, ids, context=context):
                # own post check
                if vote.user_id.id == vote.post_id.create_uid.id:
                    raise Warning('Not allowed to vote for its own post')
                # karma check
                if (values['vote'] == '1' or vote.vote == '-1' and values['vote'] == '0') and not vote.post_id.can_upvote:
                    raise KarmaError('Not enough karma to upvote.')
                elif (values['vote'] == '-1' or vote.vote == '1' and values['vote'] == '0') and not vote.post_id.can_downvote:
                    raise KarmaError('Not enough karma to downvote.')

                # karma update
                if vote.post_id.parent_id:
                    karma_value = self._get_karma_value(vote.vote, values['vote'], vote.forum_id.karma_gen_answer_upvote, vote.forum_id.karma_gen_answer_downvote)
                else:
                    karma_value = self._get_karma_value(vote.vote, values['vote'], vote.forum_id.karma_gen_question_upvote, vote.forum_id.karma_gen_question_downvote)
                self.pool['res.users'].add_karma(cr, SUPERUSER_ID, [vote.recipient_id.id], karma_value, context=context)
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
