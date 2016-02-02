# -*- coding: utf-8 -*-

from datetime import datetime
import itertools
import logging
import math
import re
import uuid
from werkzeug.exceptions import Forbidden

from openerp import _
from openerp import api, fields, models
from openerp import http
from openerp import modules
from openerp import tools
from openerp import SUPERUSER_ID
from openerp.addons.website.models.website import slug
from openerp.exceptions import UserError

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
    description = fields.Text(
        'Description',
        translate=True,
        default='This community is for professionals and enthusiasts of our products and services. '
                'Share and discuss the best content and new marketing ideas, '
                'build your professional profile and become a better marketer together.')
    welcome_message = fields.Html(
        'Welcome Message',
        default = """<section class="bg-info" style="height: 168px;"><div class="container">
                        <div class="row">
                            <div class="col-md-12">
                                <h1 class="text-center" style="text-align: left;">Welcome!</h1>
                                <p class="text-muted text-center" style="text-align: left;">This community is for professionals and enthusiasts of our products and services. Share and discuss the best content and new marketing ideas, build your professional profile and become a better marketer together.</p>
                            </div>
                            <div class="col-md-12">
                                <a href="#" class="js_close_intro">Hide Intro</a>    <a class="btn btn-primary forum_register_url" href="/web/login">Register</a> </div>
                            </div>
                        </div>
                    </section>""")
    default_order = fields.Selection([
        ('create_date desc', 'Newest'),
        ('write_date desc', 'Last Updated'),
        ('vote_count desc', 'Most Voted'),
        ('relevancy desc', 'Relevance'),
        ('child_count desc', 'Answered')],
        string='Default Order', required=True, default='write_date desc')
    relevancy_post_vote = fields.Float('First Relevance Parameter', default=0.8, help="This formula is used in order to sort by relevance. The variable 'votes' represents number of votes for a post, and 'days' is number of days since the post creation")
    relevancy_time_decay = fields.Float('Second Relevance Parameter', default=1.8)
    default_post_type = fields.Selection([
        ('question', 'Question'),
        ('discussion', 'Discussion'),
        ('link', 'Link')],
        string='Default Post', required=True, default='question')
    allow_question = fields.Boolean('Questions', help="Users can answer only once per question. Contributors can edit answers and mark the right ones.", default=True)
    allow_discussion = fields.Boolean('Discussions', default=True)
    allow_link = fields.Boolean('Links', help="When clicking on the post, it redirects to an external link", default=True)
    allow_bump = fields.Boolean('Allow Bump', default=True,
                                help='Check this box to display a popup for posts older than 10 days '
                                     'without any given answer. The popup will offer to share it on social '
                                     'networks. When shared, a question is bumped at the top of the forum.')
    allow_share = fields.Boolean('Sharing Options', default=True,
                                 help='After posting the user will be proposed to share its question '
                                      'or answer on social networks, enabling social network propagation '
                                      'of the forum content.')
    count_posts_waiting_validation = fields.Integer(string="Number of posts waiting for validation", compute='_compute_count_posts_waiting_validation')
    count_flagged_posts = fields.Integer(string='Number of flagged posts', compute='_compute_count_flagged_posts')
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
    karma_ask = fields.Integer(string='Ask questions', default=3)
    karma_answer = fields.Integer(string='Answer questions', default=3)
    karma_edit_own = fields.Integer(string='Edit own posts', default=1)
    karma_edit_all = fields.Integer(string='Edit all posts', default=300)
    karma_close_own = fields.Integer(string='Close own posts', default=100)
    karma_close_all = fields.Integer(string='Close all posts', default=500)
    karma_unlink_own = fields.Integer(string='Delete own posts', default=500)
    karma_unlink_all = fields.Integer(string='Delete all posts', default=1000)
    karma_upvote = fields.Integer(string='Upvote', default=5)
    karma_downvote = fields.Integer(string='Downvote', default=50)
    karma_answer_accept_own = fields.Integer(string='Accept an answer on own questions', default=20)
    karma_answer_accept_all = fields.Integer(string='Accept an answer to all questions', default=500)
    karma_comment_own = fields.Integer(string='Comment own posts', default=1)
    karma_comment_all = fields.Integer(string='Comment all posts', default=1)
    karma_comment_convert_own = fields.Integer(string='Convert own answers to comments and vice versa', default=50)
    karma_comment_convert_all = fields.Integer(string='Convert all answers to comments and vice versa', default=500)
    karma_comment_unlink_own = fields.Integer(string='Unlink own comments', default=50)
    karma_comment_unlink_all = fields.Integer(string='Unlink all comments', default=500)
    karma_retag = fields.Integer(string='Change question tags', default=75)
    karma_flag = fields.Integer(string='Flag a post as offensive', default=500)
    karma_dofollow = fields.Integer(string='Nofollow links', help='If the author has not enough karma, a nofollow attribute is added to links', default=500)
    karma_editor = fields.Integer(string='Editor Features: image and links',
                                  default=30, oldname='karma_editor_link_files')
    karma_user_bio = fields.Integer(string='Display detailed user biography', default=750)
    karma_post = fields.Integer(string='Ask questions without validation', default=100)
    karma_moderate = fields.Integer(string='Moderate posts', default=1000)

    @api.one
    @api.constrains('allow_question', 'allow_discussion', 'allow_link', 'default_post_type')
    def _check_default_post_type(self):
        if (self.default_post_type == 'question' and not self.allow_question) \
                or (self.default_post_type == 'discussion' and not self.allow_discussion) \
                or (self.default_post_type == 'link' and not self.allow_link):
            raise UserError(_('You cannot choose %s as default post since the forum does not allow it.') % self.default_post_type)

    @api.one
    def _compute_count_posts_waiting_validation(self):
        domain = [('forum_id', '=', self.id), ('state', '=', 'pending')]
        self.count_posts_waiting_validation = self.env['forum.post'].search_count(domain)

    @api.one
    def _compute_count_flagged_posts(self):
        domain = [('forum_id', '=', self.id), ('state', '=', 'flagged')]
        self.count_flagged_posts = self.env['forum.post'].search_count(domain)

    @api.model
    def create(self, values):
        return super(Forum, self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True)).create(values)

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
                    if user.exists() and user.karma >= self.karma_retag and len(tag) and len(tag[1:].strip()):
                        post_tags.append((0, 0, {'name': tag[1:], 'forum_id': self.id}))
            else:
                existing_keep.append(int(tag))
        post_tags.insert(0, [6, 0, existing_keep])
        return post_tags

    def get_tags_first_char(self):
        """ get set of first letter of forum tags """
        tags = self.env['forum.tag'].search([('forum_id', '=', self.id), ('posts_count', '>', 0)])
        return sorted(set([tag.name[0].upper() for tag in tags if len(tag.name)]))


class Post(models.Model):

    _name = 'forum.post'
    _description = 'Forum Post'
    _inherit = ['mail.thread', 'website.seo.metadata']
    _order = "is_correct DESC, vote_count DESC, write_date DESC"

    name = fields.Char('Title')
    forum_id = fields.Many2one('forum.forum', string='Forum', required=True)
    content = fields.Html('Content', strip_style=True)
    plain_content = fields.Text('Plain Content', compute='_get_plain_content', store=True)
    content_link = fields.Char('URL', help="URL of Link Articles")
    tag_ids = fields.Many2many('forum.tag', 'forum_tag_rel', 'forum_id', 'forum_tag_id', string='Tags')
    state = fields.Selection([('active', 'Active'), ('pending', 'Waiting Validation'), ('close', 'Close'), ('offensive', 'Offensive'), ('flagged', 'Flagged')], string='Status', default='active')
    views = fields.Integer('Number of Views', default=0)
    active = fields.Boolean('Active', default=True)
    post_type = fields.Selection([
        ('question', 'Question'),
        ('link', 'Article'),
        ('discussion', 'Discussion')],
        string='Type', default='question', required=True)
    website_message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: ['&', ('model', '=', self._name), ('message_type', 'in', ['email', 'comment'])],
        string='Post Messages', help="Comments on forum post",
    )

    # history
    create_date = fields.Datetime('Asked on', select=True, readonly=True)
    create_uid = fields.Many2one('res.users', string='Created by', select=True, readonly=True)
    write_date = fields.Datetime('Update on', select=True, readonly=True)
    bump_date = fields.Datetime('Bumped on', readonly=True,
                                help="Technical field allowing to bump a question. Writing on this field will trigger "
                                     "a write on write_date and therefore bump the post. Directly writing on write_date "
                                     "is currently not supported and this field is a workaround.")
    write_uid = fields.Many2one('res.users', string='Updated by', select=True, readonly=True)
    relevancy = fields.Float('Relevance', compute="_compute_relevancy", store=True)

    # vote
    vote_ids = fields.One2many('forum.post.vote', 'post_id', string='Votes')
    user_vote = fields.Integer('My Vote', compute='_get_user_vote')
    vote_count = fields.Integer('Votes', compute='_get_vote_count', store=True)

    # favorite
    favourite_ids = fields.Many2many('res.users', string='Favourite')
    user_favourite = fields.Boolean('Is Favourite', compute='_get_user_favourite')
    favourite_count = fields.Integer('Favorite Count', compute='_get_favorite_count', store=True)

    # hierarchy
    is_correct = fields.Boolean('Correct', help='Correct answer or answer accepted')
    parent_id = fields.Many2one('forum.post', string='Question', ondelete='cascade')
    self_reply = fields.Boolean('Reply to own question', compute='_is_self_reply', store=True)
    child_ids = fields.One2many('forum.post', 'parent_id', string='Answers')
    child_count = fields.Integer('Number of answers', compute='_get_child_count', store=True)
    uid_has_answered = fields.Boolean('Has Answered', compute='_get_uid_has_answered')
    has_validated_answer = fields.Boolean('Is answered', compute='_get_has_validated_answer', store=True)

    # offensive moderation tools
    flag_user_id = fields.Many2one('res.users', string='Flagged by')
    moderator_id = fields.Many2one('res.users', string='Reviewed by', readonly=True)

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
    karma_flag = fields.Integer('Flag a post as offensive', compute='_get_post_karma_rights')
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
    can_view = fields.Boolean('Can View', compute='_get_post_karma_rights', search='_search_can_view')
    can_display_biography = fields.Boolean("Is the author's biography visible from his post", compute='_get_post_karma_rights')
    can_post = fields.Boolean('Can Automatically be Validated', compute='_get_post_karma_rights')
    can_flag = fields.Boolean('Can Flag', compute='_get_post_karma_rights')
    can_moderate = fields.Boolean('Can Moderate', compute='_get_post_karma_rights')

    def _search_can_view(self, operator, value):
        if operator not in ('=', '!=', '<>'):
            raise ValueError('Invalid operator: %s' % (operator,))

        if not value:
            operator = operator == "=" and '!=' or '='
            value = True

        if self._uid == SUPERUSER_ID:
            return [(1, '=', 1)]

        user = self.env['res.users'].browse(self._uid)
        req = """
            SELECT p.id
            FROM forum_post p
                   LEFT JOIN res_users u ON p.create_uid = u.id
                   LEFT JOIN forum_forum f ON p.forum_id = f.id
            WHERE
                u.karma > 0
                or (p.create_uid = %s and f.karma_close_own <= %s)
                or (p.create_uid != %s and f.karma_close_all <= %s)
        """

        op = operator == "=" and "inselect" or "not inselect"

        # don't use param named because orm will add other param (test_active, ...)
        return [('id', op, (req, (user.id, user.karma, user.id, user.karma)))]

    @api.one
    @api.depends('content')
    def _get_plain_content(self):
        self.plain_content = tools.html2plaintext(self.content)[0:500] if self.content else False

    @api.one
    @api.depends('vote_count', 'forum_id.relevancy_post_vote', 'forum_id.relevancy_time_decay')
    def _compute_relevancy(self):
        if self.create_date:
            days = (datetime.today() - datetime.strptime(self.create_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)).days
            self.relevancy = math.copysign(1, self.vote_count) * (abs(self.vote_count - 1) ** self.forum_id.relevancy_post_vote / (days + 2) ** self.forum_id.relevancy_time_decay)
        else:
            self.relevancy = 0

    @api.multi
    def _get_user_vote(self):
        votes = self.env['forum.post.vote'].search_read([('post_id', 'in', self._ids), ('user_id', '=', self._uid)], ['vote', 'post_id'])
        mapped_vote = dict([(v['post_id'][0], v['vote']) for v in votes])
        for vote in self:
            vote.user_vote = mapped_vote.get(vote.id, 0)

    @api.multi
    @api.depends('vote_ids.vote')
    def _get_vote_count(self):
        read_group_res = self.env['forum.post.vote'].read_group([('post_id', 'in', self._ids)], ['post_id', 'vote'], ['post_id', 'vote'], lazy=False)
        result = dict.fromkeys(self._ids, 0)
        for data in read_group_res:
            result[data['post_id'][0]] += data['__count'] * int(data['vote'])
        for post in self:
            post.vote_count = result[post.id]

    @api.one
    def _get_user_favourite(self):
        self.user_favourite = self._uid in self.favourite_ids.ids

    @api.one
    @api.depends('favourite_ids')
    def _get_favorite_count(self):
        self.favourite_count = len(self.favourite_ids)

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


    @api.multi
    def _get_post_karma_rights(self):
        user = self.env.user
        is_admin = user.id == SUPERUSER_ID
        # sudoed recordset instead of individual posts so values can be
        # prefetched in bulk
        for post, post_sudo in itertools.izip(self, self.sudo()):
            is_creator = post.create_uid == user

            post.karma_accept = post.forum_id.karma_answer_accept_own if post.parent_id.create_uid == user else post.forum_id.karma_answer_accept_all
            post.karma_edit = post.forum_id.karma_edit_own if is_creator else post.forum_id.karma_edit_all
            post.karma_close = post.forum_id.karma_close_own if is_creator else post.forum_id.karma_close_all
            post.karma_unlink = post.forum_id.karma_unlink_own if is_creator else post.forum_id.karma_unlink_all
            post.karma_comment = post.forum_id.karma_comment_own if is_creator else post.forum_id.karma_comment_all
            post.karma_comment_convert = post.forum_id.karma_comment_convert_own if is_creator else post.forum_id.karma_comment_convert_all

            post.can_ask = is_admin or user.karma >= post.forum_id.karma_ask
            post.can_answer = is_admin or user.karma >= post.forum_id.karma_answer
            post.can_accept = is_admin or user.karma >= post.karma_accept
            post.can_edit = is_admin or user.karma >= post.karma_edit
            post.can_close = is_admin or user.karma >= post.karma_close
            post.can_unlink = is_admin or user.karma >= post.karma_unlink
            post.can_upvote = is_admin or user.karma >= post.forum_id.karma_upvote
            post.can_downvote = is_admin or user.karma >= post.forum_id.karma_downvote
            post.can_comment = is_admin or user.karma >= post.karma_comment
            post.can_comment_convert = is_admin or user.karma >= post.karma_comment_convert
            post.can_view = is_admin or user.karma >= post.karma_close or post_sudo.create_uid.karma > 0
            post.can_display_biography = is_admin or post_sudo.create_uid.karma >= post.forum_id.karma_user_bio
            post.can_post = is_admin or user.karma >= post.forum_id.karma_post
            post.can_flag = is_admin or user.karma >= post.forum_id.karma_flag
            post.can_moderate = is_admin or user.karma >= post.forum_id.karma_moderate

    @api.one
    @api.constrains('post_type', 'forum_id')
    def _check_post_type(self):
        if (self.post_type == 'question' and not self.forum_id.allow_question) \
                or (self.post_type == 'discussion' and not self.forum_id.allow_discussion) \
                or (self.post_type == 'link' and not self.forum_id.allow_link):
            raise UserError(_('This forum does not allow %s') % self.post_type)

    def _update_content(self, content, forum_id):
        forum = self.env['forum.forum'].browse(forum_id)
        if content and self.env.user.karma < forum.karma_dofollow:
            for match in re.findall(r'<a\s.*href=".*?">', content):
                match = re.escape(match)  # replace parenthesis or special char in regex
                content = re.sub(match, match[:3] + 'rel="nofollow" ' + match[3:], content)

        if self.env.user.karma <= forum.karma_editor:
            filter_regexp = r'(<img.*?>)|(<a[^>]*?href[^>]*?>)|(<[a-z|A-Z]+[^>]*style\s*=\s*[\'"][^\'"]*\s*background[^:]*:[^url;]*url)'
            content_match = re.search(filter_regexp, content, re.I)
            if content_match:
                raise KarmaError('User karma not sufficient to post an image or link.')
        return content

    @api.model
    def create(self, vals):
        if 'content' in vals and vals.get('forum_id'):
            vals['content'] = self._update_content(vals['content'], vals['forum_id'])

        post = super(Post, self.with_context(mail_create_nolog=True)).create(vals)
        # deleted or closed questions
        if post.parent_id and (post.parent_id.state == 'close' or post.parent_id.active is False):
            raise UserError(_('Posting answer on a [Deleted] or [Closed] question is not possible'))
        # karma-based access
        if not post.parent_id and not post.can_ask:
            raise KarmaError('Not enough karma to create a new question')
        elif post.parent_id and not post.can_answer:
            raise KarmaError('Not enough karma to answer to a question')
        if not post.parent_id and not post.can_post:
            post.state = 'pending'

        # add karma for posting new questions
        if not post.parent_id and post.state == 'active':
            self.env.user.sudo().add_karma(post.forum_id.karma_gen_question_new)

        post.post_notification()
        return post

    @api.model
    def check_mail_message_access(self, res_ids, operation, model_name=None):
        if operation in ('write', 'unlink') and (not model_name or model_name == 'forum.post'):
            # Make sure only author or moderator can edit/delete messages
            if any(not post.can_edit for post in self.browse(res_ids)):
                raise KarmaError('Not enough karma to edit a post.')
        return super(Post, self).check_mail_message_access(res_ids, operation, model_name=model_name)

    @api.multi
    @api.depends('name', 'post_type')
    def name_get(self):
        result = []
        for post in self:
            if post.post_type == 'discussion' and post.parent_id and not post.name:
                result.append((post.id, '%s (%s)' % (post.parent_id.name, post.id)))
            else:
                result.append((post.id, '%s' % (post.name)))
        return result

    @api.multi
    def write(self, vals):
        if 'content' in vals:
            vals['content'] = self._update_content(vals['content'], self.forum_id.id)
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
    def post_notification(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for post in self:
            if post.state == 'active' and post.parent_id:
                body = _('<p>A new answer for <i>%s</i> has been posted. <a href="%s/forum/%s/question/%s">Click here to access the post.</a></p>') % \
                        (post.parent_id.name, base_url, slug(post.parent_id.forum_id), slug(post.parent_id))
                post.parent_id.message_post(subject=_('Re: %s') % post.parent_id.name, body=body, subtype='website_forum.mt_answer_new')
            elif post.state == 'active' and not post.parent_id:
                body = _('<p>A new question <i>%s</i> has been asked on %s. <a href="%s/forum/%s/question/%s">Click here to access the question.</a></p>') % \
                        (post.name, post.forum_id.name, base_url, slug(post.forum_id), slug(post))
                post.message_post(subject=post.name, body=body, subtype='website_forum.mt_question_new')
            elif post.state == 'pending' and not post.parent_id:
                # TDE FIXME: in master, you should probably use a subtype;
                # however here we remove subtype but set partner_ids
                partners = post.sudo().message_partner_ids.filtered(lambda partner: partner.user_ids and any(user.karma >= post.forum_id.karma_moderate for user in partner.user_ids))
                note_subtype = self.sudo().env.ref('mail.mt_note')
                body = _('<p>A new question <i>%s</i> has been asked on %s and require your validation. <a href="%s/forum/%s/question/%s">Click here to access the question.</a></p>') % \
                        (post.name, post.forum_id.name, base_url, slug(post.forum_id), slug(post))
                post.message_post(subject=post.name, body=body, subtype_id=note_subtype.id, partner_ids=partners.ids)
        return True

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
                post.create_uid.sudo().add_karma(post.forum_id.karma_gen_answer_flagged * -1)

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
                post.create_uid.sudo().add_karma(post.forum_id.karma_gen_answer_flagged)

        self.write({
            'state': 'close',
            'closed_uid': self._uid,
            'closed_date': datetime.today().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),
            'closed_reason_id': reason_id,
        })
        return True

    @api.one
    def validate(self):
        if not self.can_moderate:
            raise KarmaError('Not enough karma to validate a post')

        # if state == pending, no karma previously added for the new question
        if self.state == 'pending':
            self.create_uid.sudo().add_karma(self.forum_id.karma_gen_question_new)

        self.write({
            'state': 'active',
            'active': True,
            'moderator_id': self.env.user.id,
        })
        self.post_notification()
        return True

    @api.one
    def refuse(self):
        if not self.can_moderate:
            raise KarmaError('Not enough karma to refuse a post')

        self.moderator_id = self.env.user
        return True

    @api.one
    def flag(self):
        if not self.can_flag:
            raise KarmaError('Not enough karma to flag a post')

        if(self.state == 'flagged'):
            return {'error': 'post_already_flagged'}
        elif(self.state == 'active'):
            self.write({
                'state': 'flagged',
                'flag_user_id': self.env.user.id,
            })
            return self.can_moderate and {'success': 'post_flagged_moderator'} or {'success': 'post_flagged_non_moderator'}
        else:
            return {'error': 'post_non_flaggable'}

    @api.one
    def mark_as_offensive(self, reason_id):
        if not self.can_moderate:
            raise KarmaError('Not enough karma to mark a post as offensive')

        # remove some karma
        _logger.info('Downvoting user <%s> for posting spam/offensive contents', self.create_uid)
        self.create_uid.sudo().add_karma(self.forum_id.karma_gen_answer_flagged)

        self.write({
            'state': 'offensive',
            'moderator_id': self.env.user.id,
            'closed_date': datetime.today().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),
            'closed_reason_id': reason_id,
            'active': False,
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
    def bump(self):
        """ Bump a question: trigger a write_date by writing on a dummy bump_date
        field. One cannot bump a question more than once every 10 days. """
        self.ensure_one()
        if self.forum_id.allow_bump and not self.child_ids and (datetime.today() - datetime.strptime(self.write_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)).days > 9:
            # write through super to bypass karma; sudo to allow public user to bump any post
            return self.sudo().write({'bump_date': fields.Datetime.now()})
        return False

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
            'author_id': self.sudo().create_uid.partner_id.id,  # use sudo here because of access to res.users model
            'body': tools.html_sanitize(self.content, strict=True, strip_style=True, strip_classes=True),
            'message_type': 'comment',
            'subtype': 'mail.mt_comment',
            'date': self.create_date,
        }
        new_message = self.browse(question.id).with_context(mail_create_nosubscribe=True).message_post(**values)

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

    @api.multi
    def get_access_action(self):
        """ Override method that generated the link to access the document. Instead
        of the classic form view, redirect to the post on the website directly """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/forum/%s/question/%s' % (self.forum_id.id, self.id),
            'target': 'self',
            'res_id': self.id,
        }

    @api.multi
    def _notification_get_recipient_groups(self, message, recipients):
        """ Override to set the access button: everyone can see an access button
        on their notification email. It will lead on the website view of the
        post. """
        res = super(Post, self)._notification_get_recipient_groups(message, recipients)
        access_action = self._notification_link_helper('view', model=message.model, res_id=message.res_id)
        for category, data in res.iteritems():
            res[category]['button_access'] = {'url': access_action, 'title': '%s %s' % (_('View'), self.post_type)}
        return res

    @api.cr_uid_ids_context
    def message_post(self, cr, uid, thread_id, message_type='notification', subtype=None, context=None, **kwargs):
        if thread_id and message_type == 'comment':  # user comments have a restriction on karma
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
        return super(Post, self).message_post(cr, uid, thread_id, message_type=message_type, subtype=subtype, context=context, **kwargs)


class PostReason(models.Model):
    _name = "forum.post.reason"
    _description = "Post Closing Reason"
    _order = 'name'

    name = fields.Char(string='Closing Reason', required=True, translate=True)
    reason_type = fields.Char(string='Reason Type')


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
            raise UserError(_('Not allowed to vote for its own post'))
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
                    raise UserError(_('Not allowed to vote for its own post'))
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

    _sql_constraints = [
        ('name_uniq', 'unique (name, forum_id)', "Tag name already exists !"),
    ]

    @api.multi
    @api.depends("post_ids.tag_ids")
    def _get_posts_count(self):
        for tag in self:
            tag.posts_count = len(tag.post_ids)
