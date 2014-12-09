# -*- coding: utf-8 -*-

from datetime import datetime
import logging
import math
import uuid
from werkzeug.exceptions import Forbidden

from openerp import _
from openerp import api, fields, models
from openerp import modules
from openerp import tools
from openerp import SUPERUSER_ID
from openerp.addons.website.models.website import slug
from openerp.exceptions import Warning

_logger = logging.getLogger(__name__)


class KarmaError(Forbidden):
    """ Karma-related error, used for forum and posts. """
    pass


class Forum(models.Model):
    _name = 'forum.forum'
    _description = 'Forum'
    _inherit = ['mail.thread', 'website.seo.metadata']

    def init(self, cr):
        """ Add forum uuid for user email validation.

        TDE TODO: move me somewhere else, auto_init ? """
        forum_uuids = self.pool['ir.config_parameter'].search(cr, SUPERUSER_ID, [('key', '=', 'website_forum.uuid')])
        if not forum_uuids:
            self.pool['ir.config_parameter'].set_param(cr, SUPERUSER_ID, 'website_forum.uuid', str(uuid.uuid4()), ['base.group_system'])

    @api.model
    def _get_default_faq(self):
        fname = modules.get_module_resource('website_forum', 'data', 'forum_default_faq.html')
        with open(fname, 'r') as f:
            return f.read()
        return False

    # description and use
    name = fields.Char('Forum Name', required=True, translate=True)
    faq = fields.Html('Guidelines', default=_get_default_faq, translate=True)
    description = fields.Html(
        'Description',
        default='<p> This community is for professionals and enthusiasts of our products and services.'
                'Share and discuss the best content and new marketing ideas,'
                'build your professional profile and become a better marketer together.</p>')
    default_order = fields.Selection([
        ('create_date desc', 'Newest'),
        ('write_date desc', 'Last Updated'),
        ('vote_count desc', 'Most Voted'),
        ('relevancy desc', 'Relevancy'),
        ('child_count desc', 'Answered')],
        string='Default Order', required=True, default='write_date desc')
    relevancy_post_vote = fields.Float('First Relevancy Parameter', default=0.8)
    relevancy_time_decay = fields.Float('Second Relevancy Parameter', default=1.8)
    default_post_type = fields.Selection([
        ('question', 'Question'),
        ('discussion', 'Discussion'),
        ('link', 'Link')],
        string='Default Post', required=True, default='question')
    allow_question = fields.Boolean('Questions', help="Users can answer only once per question. Contributors can edit answers and mark the right ones.", default=True)
    allow_discussion = fields.Boolean('Discussions', default=True)
    allow_link = fields.Boolean('Links', help="When clicking on the post, it redirects to an external link", default=True)
    # karma generation
    karma_gen_question_new = fields.Integer(string='Asking a question', default=2)
    karma_gen_question_upvote = fields.Integer(string='Question upvoted', default=5)
    karma_gen_question_downvote = fields.Integer(string='Question downvoted', default=-2)
    karma_gen_answer_upvote = fields.Integer(string='Answer upvoted', default=10)
    karma_gen_answer_downvote = fields.Integer(string='Answer downvoted', default=-2)
    karma_gen_answer_accept = fields.Integer(string='Accepting an answer', default=2)
    karma_gen_answer_accepted = fields.Integer(string='Answer accepted', default=15)
    karma_gen_answer_flagged = fields.Integer(string='Answer flagged', default=-100)
    # karma-based actions
    karma_ask = fields.Integer(string='Ask a new question', default=3)
    karma_answer = fields.Integer(string='Answer a question', default=3)
    karma_edit_own = fields.Integer(string='Edit its own posts', default=1)
    karma_edit_all = fields.Integer(string='Edit all posts', default=300)
    karma_close_own = fields.Integer(string='Close its own posts', default=100)
    karma_close_all = fields.Integer(string='Close all posts', default=500)
    karma_unlink_own = fields.Integer(string='Delete its own posts', default=500)
    karma_unlink_all = fields.Integer(string='Delete all posts', default=1000)
    karma_upvote = fields.Integer(string='Upvote', default=5)
    karma_downvote = fields.Integer(string='Downvote', default=50)
    karma_answer_accept_own = fields.Integer(string='Accept an answer on its own questions', default=20)
    karma_answer_accept_all = fields.Integer(string='Accept an answers to all questions', default=500)
    karma_editor_link_files = fields.Integer(string='Linking files (Editor)', default=20)
    karma_editor_clickable_link = fields.Integer(string='Add clickable links (Editor)', default=20)
    karma_comment_own = fields.Integer(string='Comment its own posts', default=1)
    karma_comment_all = fields.Integer(string='Comment all posts', default=1)
    karma_comment_convert_own = fields.Integer(string='Convert its own answers to comments and vice versa', default=50)
    karma_comment_convert_all = fields.Integer(string='Convert all answers to answers and vice versa', default=500)
    karma_comment_unlink_own = fields.Integer(string='Unlink its own comments', default=50)
    karma_comment_unlink_all = fields.Integer(string='Unlinnk all comments', default=500)
    karma_retag = fields.Integer(string='Change question tags', default=75)
    karma_flag = fields.Integer(string='Flag a post as offensive', default=500)
    karma_dofollow = fields.Integer(string='Disabled links', help='If the author has not enough karma, a nofollow attribute is added to links', default=500)

    @api.model
    def create(self, values):
        return super(Forum, self.with_context(mail_create_nolog=True)).create(values)

    @api.model
    def _tag_to_write_vals(self, tags=''):
        User = self.env['res.users']
        Tag = self.env['forum.tag']
        post_tags = []
        existing_keep = []
        for tag in filter(None, tags.split(',')):
            if tag.startswith('_'):  # it's a new tag
                # check that not arleady created meanwhile or maybe excluded by the limit on the search
                tag_ids = Tag.search([('name', '=', tag[1:])])
                if tag_ids:
                    existing_keep.append(int(tag_ids[0]))
                else:
                    # check if user have Karma needed to create need tag
                    user = User.sudo().browse(self._uid)
                    if user.exists() and user.karma >= self.karma_retag:
                        post_tags.append((0, 0, {'name': tag[1:], 'forum_id': self.id}))
            else:
                existing_keep.append(int(tag))
        post_tags.insert(0, [6, 0, existing_keep])
        return post_tags


class Post(models.Model):
    _name = 'forum.post'
    _description = 'Forum Post'
    _inherit = ['mail.thread', 'website.seo.metadata']
    _order = "is_correct DESC, vote_count DESC, write_date DESC"

    name = fields.Char('Title')
    forum_id = fields.Many2one('forum.forum', string='Forum', required=True)
    content = fields.Html('Content')
    content_link = fields.Char('URL', help="URL of Link Articles")
    tag_ids = fields.Many2many('forum.tag', 'forum_tag_rel', 'forum_id', 'forum_tag_id', string='Tags')
    state = fields.Selection([('active', 'Active'), ('close', 'Close'), ('offensive', 'Offensive')], string='Status', default='active')
    views = fields.Integer('Number of Views', default=0)
    active = fields.Boolean('Active', default=True)
    post_type = fields.Selection([
        ('question', 'Question'),
        ('link', 'Article'),
        ('discussion', 'Discussion')],
        string='Type', default='question')
    website_message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: ['&', ('model', '=', self._name), ('type', 'in', ['email', 'comment'])],
        string='Post Messages', help="Comments on forum post",
    )
    # history
    create_date = fields.Datetime('Asked on', select=True, readonly=True)
    create_uid = fields.Many2one('res.users', string='Created by', select=True, readonly=True)
    write_date = fields.Datetime('Update on', select=True, readonly=True)
    write_uid = fields.Many2one('res.users', string='Updated by', select=True, readonly=True)
    relevancy = fields.Float('Relevancy', compute="_compute_relevancy", store=True)

    @api.one
    @api.depends('vote_count', 'forum_id.relevancy_post_vote', 'forum_id.relevancy_time_decay')
    def _compute_relevancy(self):
        days = (datetime.today() - datetime.strptime(self.create_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)).days
        self.relevancy = math.copysign(1, self.vote_count) * (abs(self.vote_count - 1) ** self.forum_id.relevancy_post_vote / (days + 2) ** self.forum_id.relevancy_time_decay)

    # vote
    vote_ids = fields.One2many('forum.post.vote', 'post_id', string='Votes')
    user_vote = fields.Integer('My Vote', compute='_get_user_vote')
    vote_count = fields.Integer('Votes', compute='_get_vote_count', store=True)

    @api.multi
    def _get_user_vote(self):
        votes = self.env['forum.post.vote'].search_read([('post_id', 'in', self._ids), ('user_id', '=', self._uid)], ['vote', 'post_id'])
        mapped_vote = dict([(v['post_id'][0], v['vote']) for v in votes])
        for vote in self:
            vote.user_vote = mapped_vote.get(vote.id, 0)

    @api.multi
    @api.depends('vote_ids')
    def _get_vote_count(self):
        read_group_res = self.env['forum.post.vote'].read_group([('post_id', 'in', self._ids)], ['post_id', 'vote'], ['post_id', 'vote'], lazy=False)
        result = dict.fromkeys(self._ids, 0)
        for data in read_group_res:
            result[data['post_id'][0]] += data['__count'] * int(data['vote'])
        for post in self:
            post.vote_count = result[post.id]

    # favorite
    favourite_ids = fields.Many2many('res.users', string='Favourite')
    user_favourite = fields.Boolean('Is Favourite', compute='_get_user_favourite')
    favourite_count = fields.Integer('Favorite Count', compute='_get_favorite_count', store=True)

    @api.one
    def _get_user_favourite(self):
        self.user_favourite = self._uid in self.favourite_ids.ids

    @api.one
    @api.depends('favourite_ids')
    def _get_favorite_count(self):
        self.favourite_count = len(self.favourite_ids)

    # hierarchy
    is_correct = fields.Boolean('Correct', help='Correct answer or answer accepted')
    parent_id = fields.Many2one('forum.post', string='Question', ondelete='cascade')
    self_reply = fields.Boolean('Reply to own question', compute='_is_self_reply', store=True)
    child_ids = fields.One2many('forum.post', 'parent_id', string='Answers')
    child_count = fields.Integer('Number of answers', compute='_get_child_count', store=True)
    uid_has_answered = fields.Boolean('Has Answered', compute='_get_uid_has_answered')
    has_validated_answer = fields.Boolean('Is answered', compute='_get_has_validated_answer', store=True)

    @api.one
    @api.depends('create_uid', 'parent_id')
    def _is_self_reply(self):
        self.self_reply = self.parent_id.create_uid.id == self._uid

    @api.one
    @api.depends('child_ids.create_uid', 'website_message_ids')
    def _get_child_count(self):
        def process(node):
            total = len(node.website_message_ids) + len(node.child_ids)
            for child in node.child_ids:
                total += process(child)
            return total
        self.child_count = process(self)

    @api.one
    def _get_uid_has_answered(self):
        self.uid_has_answered = any(answer.create_uid.id == self._uid for answer in self.child_ids)

    @api.one
    @api.depends('child_ids.is_correct')
    def _get_has_validated_answer(self):
        self.has_validated_answer = any(answer.is_correct for answer in self.child_ids)

    # closing
    closed_reason_id = fields.Many2one('forum.post.reason', string='Reason')
    closed_uid = fields.Many2one('res.users', string='Closed by', select=1)
    closed_date = fields.Datetime('Closed on', readonly=True)
    # karma calculation and access
    karma_accept = fields.Integer('Convert comment to answer', compute='_get_post_karma_rights')
    karma_edit = fields.Integer('Karma to edit', compute='_get_post_karma_rights')
    karma_close = fields.Integer('Karma to close', compute='_get_post_karma_rights')
    karma_unlink = fields.Integer('Karma to unlink', compute='_get_post_karma_rights')
    karma_comment = fields.Integer('Karma to comment', compute='_get_post_karma_rights')
    karma_comment_convert = fields.Integer('Karma to convert comment to answer', compute='_get_post_karma_rights')
    can_ask = fields.Boolean('Can Ask', compute='_get_post_karma_rights')
    can_answer = fields.Boolean('Can Answer', compute='_get_post_karma_rights')
    can_accept = fields.Boolean('Can Accept', compute='_get_post_karma_rights')
    can_edit = fields.Boolean('Can Edit', compute='_get_post_karma_rights')
    can_close = fields.Boolean('Can Close', compute='_get_post_karma_rights')
    can_unlink = fields.Boolean('Can Unlink', compute='_get_post_karma_rights')
    can_upvote = fields.Boolean('Can Upvote', compute='_get_post_karma_rights')
    can_downvote = fields.Boolean('Can Downvote', compute='_get_post_karma_rights')
    can_comment = fields.Boolean('Can Comment', compute='_get_post_karma_rights')
    can_comment_convert = fields.Boolean('Can Convert to Comment', compute='_get_post_karma_rights')

    @api.one
    def _get_post_karma_rights(self):
        user = self.env.user

        self.karma_accept = self.parent_id and self.parent_id.create_uid.id == self._uid and self.forum_id.karma_answer_accept_own or self.forum_id.karma_answer_accept_all
        self.karma_edit = self.create_uid.id == self._uid and self.forum_id.karma_edit_own or self.forum_id.karma_edit_all
        self.karma_close = self.create_uid.id == self._uid and self.forum_id.karma_close_own or self.forum_id.karma_close_all
        self.karma_unlink = self.create_uid.id == self._uid and self.forum_id.karma_unlink_own or self.forum_id.karma_unlink_all
        self.karma_comment = self.create_uid.id == self._uid and self.forum_id.karma_comment_own or self.forum_id.karma_comment_all
        self.karma_comment_convert = self.create_uid.id == self._uid and self.forum_id.karma_comment_convert_own or self.forum_id.karma_comment_convert_all

        self.can_ask = user.karma >= self.forum_id.karma_ask
        self.can_answer = user.karma >= self.forum_id.karma_answer
        self.can_accept = user.karma >= self.karma_accept
        self.can_edit = user.karma >= self.karma_edit
        self.can_close = user.karma >= self.karma_close
        self.can_unlink = user.karma >= self.karma_unlink
        self.can_upvote = user.karma >= self.forum_id.karma_upvote
        self.can_downvote = user.karma >= self.forum_id.karma_downvote
        self.can_comment = user.karma >= self.karma_comment
        self.can_comment_convert = user.karma >= self.karma_comment_convert

    @api.model
    def create(self, vals):
        post = super(Post, self.with_context(mail_create_nolog=True)).create(vals)
        # deleted or closed questions
        if post.parent_id and (post.parent_id.state == 'close' or post.parent_id.active is False):
            raise Warning(_('Posting answer on a [Deleted] or [Closed] question is not possible'))
        # karma-based access
        if not post.parent_id and not post.can_ask:
            raise KarmaError('Not enough karma to create a new question')
        elif post.parent_id and not post.can_answer:
            raise KarmaError('Not enough karma to answer to a question')
        # messaging and chatter
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        if post.parent_id:
            body = _(
                '<p>A new answer for <i>%s</i> has been posted. <a href="%s/forum/%s/question/%s">Click here to access the post.</a></p>' %
                (post.parent_id.name, base_url, slug(post.parent_id.forum_id), slug(post.parent_id))
            )
            post.parent_id.message_post(subject=_('Re: %s') % post.parent_id.name, body=body, subtype='website_forum.mt_answer_new')
        else:
            body = _(
                '<p>A new question <i>%s</i> has been asked on %s. <a href="%s/forum/%s/question/%s">Click here to access the question.</a></p>' %
                (post.name, post.forum_id.name, base_url, slug(post.forum_id), slug(post))
            )
            post.message_post(subject=post.name, body=body, subtype='website_forum.mt_question_new')
            self.env.user.sudo().add_karma(post.forum_id.karma_gen_question_new)
        return post

    @api.multi
    def write(self, vals):
        if 'state' in vals:
            if vals['state'] in ['active', 'close'] and any(not post.can_close for post in self):
                raise KarmaError('Not enough karma to close or reopen a post.')
        if 'active' in vals:
            if any(not post.can_unlink for post in self):
                raise KarmaError('Not enough karma to delete or reactivate a post')
        if 'is_correct' in vals:
            if any(not post.can_accept for post in self):
                raise KarmaError('Not enough karma to accept or refuse an answer')
            # update karma except for self-acceptance
            mult = 1 if vals['is_correct'] else -1
            for post in self:
                if vals['is_correct'] != post.is_correct and post.create_uid.id != self._uid:
                    post.create_uid.sudo().add_karma(post.forum_id.karma_gen_answer_accepted * mult)
                    self.env.user.sudo().add_karma(post.forum_id.karma_gen_answer_accept * mult)
        if any(key not in ['state', 'active', 'is_correct', 'closed_uid', 'closed_date', 'closed_reason_id'] for key in vals.keys()) and any(not post.can_edit for post in self):
            raise KarmaError('Not enough karma to edit a post.')

        res = super(Post, self).write(vals)
        # if post content modify, notify followers
        if 'content' in vals or 'name' in vals:
            for post in self:
                if post.parent_id:
                    body, subtype = _('Answer Edited'), 'website_forum.mt_answer_edit'
                    obj_id = post.parent_id
                else:
                    body, subtype = _('Question Edited'), 'website_forum.mt_question_edit'
                    obj_id = post
                obj_id.message_post(body=body, subtype=subtype)
        return res

    @api.multi
    def reopen(self):
        if any(post.parent_id or post.state != 'close' for post in self):
            return False

        reason_offensive = self.env.ref('website_forum.reason_7')
        reason_spam = self.env.ref('website_forum.reason_8')
        for post in self:
            if post.closed_reason_id in (reason_offensive, reason_spam):
                _logger.info('Upvoting user <%s>, reopening spam/offensive question',
                             post.create_uid)
                # TODO: in master, consider making this a tunable karma parameter
                post.create_uid.sudo().add_karma(post.forum_id.karma_gen_question_downvote * -5)

        self.sudo().write({'state': 'active'})

    @api.multi
    def close(self, reason_id):
        if any(post.parent_id for post in self):
            return False

        reason_offensive = self.env.ref('website_forum.reason_7').id
        reason_spam = self.env.ref('website_forum.reason_8').id
        if reason_id in (reason_offensive, reason_spam):
            for post in self:
                _logger.info('Downvoting user <%s> for posting spam/offensive contents',
                             post.create_uid)
                # TODO: in master, consider making this a tunable karma parameter
                post.create_uid.sudo().add_karma(post.forum_id.karma_gen_question_downvote * 5)

        self.write({
            'state': 'close',
            'closed_uid': self._uid,
            'closed_date': datetime.today().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),
            'closed_reason_id': reason_id,
        })
        return True

    @api.multi
    def unlink(self):
        if any(not post.can_unlink for post in self):
            raise KarmaError('Not enough karma to unlink a post')
        # if unlinking an answer with accepted answer: remove provided karma
        for post in self:
            if post.is_correct:
                post.create_uid.sudo().add_karma(post.forum_id.karma_gen_answer_accepted * -1)
                self.env.user.sudo().add_karma(post.forum_id.karma_gen_answer_accepted * -1)
        return super(Post, self).unlink()

    @api.multi
    def vote(self, upvote=True):
        Vote = self.env['forum.post.vote']
        vote_ids = Vote.search([('post_id', 'in', self._ids), ('user_id', '=', self._uid)])
        new_vote = '1' if upvote else '-1'
        voted_forum_ids = set()
        if vote_ids:
            for vote in vote_ids:
                if upvote:
                    new_vote = '0' if vote.vote == '-1' else '1'
                else:
                    new_vote = '0' if vote.vote == '1' else '-1'
                vote.vote = new_vote
                voted_forum_ids.add(vote.post_id.id)
        for post_id in set(self._ids) - voted_forum_ids:
            for post_id in self._ids:
                Vote.create({'post_id': post_id, 'vote': new_vote})
        return {'vote_count': self.vote_count, 'user_vote': new_vote}

    @api.one
    def convert_answer_to_comment(self):
        """ Tools to convert an answer (forum.post) to a comment (mail.message).
        The original post is unlinked and a new comment is posted on the question
        using the post create_uid as the comment's author. """
        if not self.parent_id:
            return False

        # karma-based action check: use the post field that computed own/all value
        if not self.can_comment_convert:
            raise KarmaError('Not enough karma to convert an answer to a comment')

        # post the message
        question = self.parent_id
        values = {
            'author_id': self.create_uid.partner_id.id,
            'body': tools.html2plaintext(self.content),
            'type': 'comment',
            'subtype': 'mail.mt_comment',
            'date': self.create_date,
        }
        new_message = self.browse(question.id).with_context(mail_create_nosubcribe=True).message_post(**values)

        # unlink the original answer, using SUPERUSER_ID to avoid karma issues
        self.sudo().unlink()

        return new_message

    @api.model
    def convert_comment_to_answer(self, message_id, default=None):
        """ Tool to convert a comment (mail.message) into an answer (forum.post).
        The original comment is unlinked and a new answer from the comment's author
        is created. Nothing is done if the comment's author already answered the
        question. """
        comment = self.env['mail.message'].sudo().browse(message_id)
        post = self.browse(comment.res_id)
        if not comment.author_id or not comment.author_id.user_ids:  # only comment posted by users can be converted
            return False

        # karma-based action check: must check the message's author to know if own / all
        karma_convert = comment.author_id.id == self.env.user.partner_id.id and post.forum_id.karma_comment_convert_own or post.forum_id.karma_comment_convert_all
        can_convert = self.env.user.karma >= karma_convert
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
        new_post = self.sudo(post_create_uid.id).create(post_values)

        # delete comment
        comment.unlink()

        return new_post

    @api.one
    def unlink_comment(self, message_id):
        user = self.env.user
        comment = self.env['mail.message'].sudo().browse(message_id)
        if not comment.model == 'forum.post' or not comment.res_id == self.id:
            return False
        # karma-based action check: must check the message's author to know if own or all
        karma_unlink = comment.author_id.id == user.partner_id.id and self.forum_id.karma_comment_unlink_own or self.forum_id.karma_comment_unlink_all
        can_unlink = user.karma >= karma_unlink
        if not can_unlink:
            raise KarmaError('Not enough karma to unlink a comment')
        return comment.unlink()

    @api.multi
    def set_viewed(self):
        self._cr.execute("""UPDATE forum_post SET views = views+1 WHERE id IN %s""", (self._ids,))
        return True

    @api.model
    def _get_access_link(self, mail, partner):
        post = self.browse(mail.res_id)
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
            # TDE FIXME: trigger browse because otherwise the function field is not compted - check with RCO
            tmp1, tmp2 = post.karma_comment, post.can_comment
            user = self.pool['res.users'].browse(cr, uid, uid)
            tmp3 = user.karma
            # TDE END FIXME
            if not post.can_comment:
                raise KarmaError('Not enough karma to comment')
        return super(Post, self).message_post(cr, uid, thread_id, type=type, subtype=subtype, context=context, **kwargs)


class PostReason(models.Model):
    _name = "forum.post.reason"
    _description = "Post Closing Reason"
    _order = 'name'

    name = fields.Char(string='Closing Reason', required=True, translate=True)


class Vote(models.Model):
    _name = 'forum.post.vote'
    _description = 'Vote'

    post_id = fields.Many2one('forum.post', string='Post', ondelete='cascade', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self._uid)
    vote = fields.Selection([('1', '1'), ('-1', '-1'), ('0', '0')], string='Vote', required=True, default='1')
    create_date = fields.Datetime('Create Date', select=True, readonly=True)
    forum_id = fields.Many2one('forum.forum', string='Forum', related="post_id.forum_id", store=True)
    recipient_id = fields.Many2one('res.users', string='To', related="post_id.create_uid", store=True)

    def _get_karma_value(self, old_vote, new_vote, up_karma, down_karma):
        _karma_upd = {
            '-1': {'-1': 0, '0': -1 * down_karma, '1': -1 * down_karma + up_karma},
            '0': {'-1': 1 * down_karma, '0': 0, '1': up_karma},
            '1': {'-1': -1 * up_karma + down_karma, '0': -1 * up_karma, '1': 0}
        }
        return _karma_upd[old_vote][new_vote]

    @api.model
    def create(self, vals):
        vote = super(Vote, self).create(vals)

        # own post check
        if vote.user_id.id == vote.post_id.create_uid.id:
            raise Warning('Not allowed to vote for its own post')
        # karma check
        if vote.vote == '1' and not vote.post_id.can_upvote:
            raise KarmaError('Not enough karma to upvote.')
        elif vote.vote == '-1' and not vote.post_id.can_downvote:
            raise KarmaError('Not enough karma to downvote.')

        if vote.post_id.parent_id:
            karma_value = self._get_karma_value('0', vote.vote, vote.forum_id.karma_gen_answer_upvote, vote.forum_id.karma_gen_answer_downvote)
        else:
            karma_value = self._get_karma_value('0', vote.vote, vote.forum_id.karma_gen_question_upvote, vote.forum_id.karma_gen_question_downvote)
        vote.recipient_id.sudo().add_karma(karma_value)
        return vote

    @api.multi
    def write(self, values):
        if 'vote' in values:
            for vote in self:
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
                vote.recipient_id.sudo().add_karma(karma_value)
        res = super(Vote, self).write(values)
        return res


class Tags(models.Model):
    _name = "forum.tag"
    _description = "Forum Tag"
    _inherit = ['website.seo.metadata']

    name = fields.Char('Name', required=True)
    create_uid = fields.Many2one('res.users', string='Created by', readonly=True)
    forum_id = fields.Many2one('forum.forum', string='Forum', required=True)
    post_ids = fields.Many2many('forum.post', 'forum_tag_rel', 'forum_tag_id', 'forum_id', string='Posts')
    posts_count = fields.Integer('Number of Posts', compute='_get_posts_count', store=True)

    @api.multi
    @api.depends("post_ids.tag_ids")
    def _get_posts_count(self):
        for tag in self:
            tag.posts_count = len(tag.post_ids)
