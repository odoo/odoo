# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import math
import re

from datetime import datetime

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.tools import misc, sql
from odoo.tools.translate import html_translate
from odoo.addons.http_routing.models.ir_http import slug, unslug

_logger = logging.getLogger(__name__)


class Forum(models.Model):
    _name = 'forum.forum'
    _description = 'Forum'
    _inherit = [
        'mail.thread',
        'image.mixin',
        'website.seo.metadata',
        'website.multi.mixin',
        'website.searchable.mixin',
    ]
    _order = "sequence"

    # description and use
    name = fields.Char('Forum Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=1)
    mode = fields.Selection([
        ('questions', 'Questions (1 answer)'),
        ('discussions', 'Discussions (multiple answers)')],
        string='Mode', required=True, default='questions',
        help='Questions mode: only one answer allowed\n Discussions mode: multiple answers allowed')
    privacy = fields.Selection([
        ('public', 'Public'),
        ('connected', 'Signed In'),
        ('private', 'Some users')],
        help="Public: Forum is public\nSigned In: Forum is visible for signed in users\nSome users: Forum and their content are hidden for non members of selected group",
        default='public')
    authorized_group_id = fields.Many2one('res.groups', 'Authorized Group')
    menu_id = fields.Many2one('website.menu', 'Menu', copy=False)
    active = fields.Boolean(default=True)
    faq = fields.Html('Guidelines', translate=html_translate, sanitize=True, sanitize_overridable=True)
    description = fields.Text('Description', translate=True)
    teaser = fields.Text('Teaser', compute='_compute_teaser', store=True)
    welcome_message = fields.Html(
        'Welcome Message',
        translate=True,
        default="""<section>
                        <div class="container py-5">
                            <div class="row">
                                <div class="col-lg-12">
                                    <h1 class="text-center">Welcome!</h1>
                                    <p class="text-400 text-center">
                                        This community is for professionals and enthusiasts of our products and services.
                                        <br/>Share and discuss the best content and new marketing ideas, build your professional profile and become a better marketer together.
                                    </p>
                                </div>
                                <div class="col text-center mt-3">
                                    <a href="#" class="js_close_intro btn btn-outline-light mr-2">Hide Intro</a>
                                    <a class="btn btn-light forum_register_url" href="/web/login">Register</a>
                                </div>
                            </div>
                        </div>
                    </section>""",
        sanitize_attributes=False,
        sanitize_form=False)
    default_order = fields.Selection([
        ('create_date desc', 'Newest'),
        ('write_date desc', 'Last Updated'),
        ('vote_count desc', 'Most Voted'),
        ('relevancy desc', 'Relevance'),
        ('child_count desc', 'Answered')],
        string='Default', required=True, default='write_date desc')
    relevancy_post_vote = fields.Float('First Relevance Parameter', default=0.8, help="This formula is used in order to sort by relevance. The variable 'votes' represents number of votes for a post, and 'days' is number of days since the post creation")
    relevancy_time_decay = fields.Float('Second Relevance Parameter', default=1.8)
    allow_bump = fields.Boolean('Allow Bump', default=True,
                                help='Check this box to display a popup for posts older than 10 days '
                                     'without any given answer. The popup will offer to share it on social '
                                     'networks. When shared, a question is bumped at the top of the forum.')
    allow_share = fields.Boolean('Sharing Options', default=True,
                                 help='After posting the user will be proposed to share its question '
                                      'or answer on social networks, enabling social network propagation '
                                      'of the forum content.')
    # posts statistics
    post_ids = fields.One2many('forum.post', 'forum_id', string='Posts')
    last_post_id = fields.Many2one('forum.post', compute='_compute_last_post')
    total_posts = fields.Integer('# Posts', compute='_compute_forum_statistics')
    total_views = fields.Integer('# Views', compute='_compute_forum_statistics')
    total_answers = fields.Integer('# Answers', compute='_compute_forum_statistics')
    total_favorites = fields.Integer('# Favorites', compute='_compute_forum_statistics')
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
    karma_edit_retag = fields.Integer(string='Change question tags', default=75)
    karma_close_own = fields.Integer(string='Close own posts', default=100)
    karma_close_all = fields.Integer(string='Close all posts', default=500)
    karma_unlink_own = fields.Integer(string='Delete own posts', default=500)
    karma_unlink_all = fields.Integer(string='Delete all posts', default=1000)
    karma_tag_create = fields.Integer(string='Create new tags', default=30)
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
    karma_flag = fields.Integer(string='Flag a post as offensive', default=500)
    karma_dofollow = fields.Integer(string='Nofollow links', help='If the author has not enough karma, a nofollow attribute is added to links', default=500)
    karma_editor = fields.Integer(string='Editor Features: image and links',
                                  default=30)
    karma_user_bio = fields.Integer(string='Display detailed user biography', default=750)
    karma_post = fields.Integer(string='Ask questions without validation', default=100)
    karma_moderate = fields.Integer(string='Moderate posts', default=1000)

    @api.depends('post_ids')
    def _compute_last_post(self):
        for forum in self:
            forum.last_post_id = forum.post_ids.search([('forum_id', '=', forum.id), ('parent_id', '=', False), ('state', '=', 'active')], order='create_date desc', limit=1)

    @api.depends('description')
    def _compute_teaser(self):
        for forum in self:
            if forum.description:
                desc = forum.description.replace('\n', ' ')
                if len(forum.description) > 180:
                    forum.teaser = desc[:180] + '...'
                else:
                    forum.teaser = forum.description
            else:
                forum.teaser = ""

    @api.depends('post_ids.state', 'post_ids.views', 'post_ids.child_count', 'post_ids.favourite_count')
    def _compute_forum_statistics(self):
        default_stats = {'total_posts': 0, 'total_views': 0, 'total_answers': 0, 'total_favorites': 0}

        if not self.ids:
            self.update(default_stats)
            return

        result = {cid: dict(default_stats) for cid in self.ids}
        read_group_res = self.env['forum.post']._read_group(
            [('forum_id', 'in', self.ids), ('state', 'in', ('active', 'close')), ('parent_id', '=', False)],
            ['forum_id', 'views', 'child_count', 'favourite_count'],
            groupby=['forum_id'],
            lazy=False)
        for res_group in read_group_res:
            cid = res_group['forum_id'][0]
            result[cid]['total_posts'] += res_group.get('__count', 0)
            result[cid]['total_views'] += res_group.get('views', 0)
            result[cid]['total_answers'] += res_group.get('child_count', 0)
            result[cid]['total_favorites'] += 1 if res_group.get('favourite_count', 0) else 0

        for record in self:
            record.update(result[record.id])

    def _compute_count_posts_waiting_validation(self):
        for forum in self:
            domain = [('forum_id', '=', forum.id), ('state', '=', 'pending')]
            forum.count_posts_waiting_validation = self.env['forum.post'].search_count(domain)

    def _compute_count_flagged_posts(self):
        for forum in self:
            domain = [('forum_id', '=', forum.id), ('state', '=', 'flagged')]
            forum.count_flagged_posts = self.env['forum.post'].search_count(domain)

    def _set_default_faq(self):
        for forum in self:
            forum.faq = self.env['ir.ui.view']._render_template('website_forum.faq_accordion', {"forum": forum})

    @api.model_create_multi
    def create(self, vals_list):
        forums = super(
            Forum,
            self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True)
        ).create(vals_list)
        forums._set_default_faq()  # will trigger a write and call update_website_count
        return forums

    def write(self, vals):
        if 'privacy' in vals:
            if not vals['privacy']:
                # The forum is neither public, neither private, remove menu to avoid conflict
                self.menu_id.unlink()
            elif vals['privacy'] == 'public':
                # The forum is public, the menu must be also public
                vals['authorized_group_id'] = False
            elif vals['privacy'] == 'connected':
                vals['authorized_group_id'] = False

        res = super(Forum, self).write(vals)
        if 'active' in vals:
            # archiving/unarchiving a forum does it on its posts, too
            self.env['forum.post'].with_context(active_test=False).search([('forum_id', 'in', self.ids)]).write({'active': vals['active']})

        if 'active' in vals or 'website_id' in vals:
            self._update_website_count()
        return res

    def unlink(self):
        self._update_website_count()
        return super(Forum, self).unlink()

    def _tag_to_write_vals(self, tags=''):
        Tag = self.env['forum.tag']
        post_tags = []
        existing_keep = []
        user = self.env.user
        for tag in (tag for tag in tags.split(',') if tag):
            if tag.startswith('_'):  # it's a new tag
                # check that not already created meanwhile or maybe excluded by the limit on the search
                tag_ids = Tag.search([('name', '=', tag[1:]), ('forum_id', '=', self.id)])
                if tag_ids:
                    existing_keep.append(int(tag_ids[0]))
                else:
                    # check if user have Karma needed to create need tag
                    if user.exists() and user.karma >= self.karma_tag_create and len(tag) and len(tag[1:].strip()):
                        post_tags.append((0, 0, {'name': tag[1:], 'forum_id': self.id}))
            else:
                existing_keep.append(int(tag))
        post_tags.insert(0, [6, 0, existing_keep])
        return post_tags

    def _compute_website_url(self):
        if not self.id:
            return False
        return '/forum/%s' % (slug(self))

    def get_tags_first_char(self):
        """ get set of first letter of forum tags """
        tags = self.env['forum.tag'].search([('forum_id', '=', self.id), ('posts_count', '>', 0)])
        return sorted(set([tag.name[0].upper() for tag in tags if len(tag.name)]))

    def go_to_website(self):
        self.ensure_one()
        website_url = self._compute_website_url()
        if not website_url:
            return False
        return self.env['website'].get_client_action(website_url)

    @api.model
    def _update_website_count(self):
        for website in self.env['website'].sudo().search([]):
            website.forums_count = self.env['forum.forum'].sudo().search_count(website.website_domain())

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options['displayDescription']
        search_fields = ['name']
        fetch_fields = ['id', 'name']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'website_url', 'type': 'text', 'truncate': False},
        }
        if with_description:
            search_fields.append('description')
            fetch_fields.append('description')
            mapping['description'] = {'name': 'description', 'type': 'text', 'match': True}
        return {
            'model': 'forum.forum',
            'base_domain': [website.website_domain()],
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-comments-o',
            'order': 'name desc, id desc' if 'name desc' in order else 'name asc, id desc',
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)
        for forum, data in zip(self, results_data):
            data['website_url'] = forum._compute_website_url()
        return results_data


class Post(models.Model):

    _name = 'forum.post'
    _description = 'Forum Post'
    _inherit = [
        'mail.thread',
        'website.seo.metadata',
        'website.searchable.mixin',
    ]
    _order = "is_correct DESC, vote_count DESC, write_date DESC"

    name = fields.Char('Title')
    forum_id = fields.Many2one('forum.forum', string='Forum', required=True)
    content = fields.Html('Content', strip_style=True)
    plain_content = fields.Text('Plain Content', compute='_get_plain_content', store=True)
    tag_ids = fields.Many2many('forum.tag', 'forum_tag_rel', 'forum_id', 'forum_tag_id', string='Tags')
    state = fields.Selection([('active', 'Active'), ('pending', 'Waiting Validation'), ('close', 'Closed'), ('offensive', 'Offensive'), ('flagged', 'Flagged')], string='Status', default='active')
    views = fields.Integer('Views', default=0, readonly=True, copy=False)
    active = fields.Boolean('Active', default=True)
    website_message_ids = fields.One2many(domain=lambda self: [('model', '=', self._name), ('message_type', 'in', ['email', 'comment'])])
    website_url = fields.Char('Website URL', compute='_compute_website_url')
    website_id = fields.Many2one(related='forum_id.website_id', readonly=True)

    # history
    create_date = fields.Datetime('Asked on', index=True, readonly=True)
    create_uid = fields.Many2one('res.users', string='Created by', index=True, readonly=True)
    write_date = fields.Datetime('Updated on', index=True, readonly=True)
    bump_date = fields.Datetime('Bumped on', readonly=True,
                                help="Technical field allowing to bump a question. Writing on this field will trigger "
                                     "a write on write_date and therefore bump the post. Directly writing on write_date "
                                     "is currently not supported and this field is a workaround.")
    write_uid = fields.Many2one('res.users', string='Updated by', index=True, readonly=True)
    relevancy = fields.Float('Relevance', compute="_compute_relevancy", store=True)

    # vote
    vote_ids = fields.One2many('forum.post.vote', 'post_id', string='Votes')
    user_vote = fields.Integer('My Vote', compute='_get_user_vote')
    vote_count = fields.Integer('Total Votes', compute='_get_vote_count', store=True)

    # favorite
    favourite_ids = fields.Many2many('res.users', string='Favourite')
    user_favourite = fields.Boolean('Is Favourite', compute='_get_user_favourite')
    favourite_count = fields.Integer('Favorite', compute='_get_favorite_count', store=True)

    # hierarchy
    is_correct = fields.Boolean('Correct', help='Correct answer or answer accepted')
    parent_id = fields.Many2one('forum.post', string='Question', ondelete='cascade', readonly=True, index=True)
    self_reply = fields.Boolean('Reply to own question', compute='_is_self_reply', store=True)
    child_ids = fields.One2many('forum.post', 'parent_id', string='Post Answers', domain=lambda self: [('forum_id', 'in', self.forum_id.ids)])
    child_count = fields.Integer('Answers', compute='_get_child_count', store=True)
    uid_has_answered = fields.Boolean('Has Answered', compute='_get_uid_has_answered')
    has_validated_answer = fields.Boolean('Is answered', compute='_get_has_validated_answer', store=True)

    # offensive moderation tools
    flag_user_id = fields.Many2one('res.users', string='Flagged by')
    moderator_id = fields.Many2one('res.users', string='Reviewed by', readonly=True)

    # closing
    closed_reason_id = fields.Many2one('forum.post.reason', string='Reason', copy=False)
    closed_uid = fields.Many2one('res.users', string='Closed by', readonly=True, copy=False)
    closed_date = fields.Datetime('Closed on', readonly=True, copy=False)

    # karma calculation and access
    karma_accept = fields.Integer('Convert comment to answer', compute='_get_post_karma_rights', compute_sudo=False)
    karma_edit = fields.Integer('Karma to edit', compute='_get_post_karma_rights', compute_sudo=False)
    karma_close = fields.Integer('Karma to close', compute='_get_post_karma_rights', compute_sudo=False)
    karma_unlink = fields.Integer('Karma to unlink', compute='_get_post_karma_rights', compute_sudo=False)
    karma_comment = fields.Integer('Karma to comment', compute='_get_post_karma_rights', compute_sudo=False)
    karma_comment_convert = fields.Integer('Karma to convert comment to answer', compute='_get_post_karma_rights', compute_sudo=False)
    karma_flag = fields.Integer('Flag a post as offensive', compute='_get_post_karma_rights', compute_sudo=False)
    can_ask = fields.Boolean('Can Ask', compute='_get_post_karma_rights', compute_sudo=False)
    can_answer = fields.Boolean('Can Answer', compute='_get_post_karma_rights', compute_sudo=False)
    can_accept = fields.Boolean('Can Accept', compute='_get_post_karma_rights', compute_sudo=False)
    can_edit = fields.Boolean('Can Edit', compute='_get_post_karma_rights', compute_sudo=False)
    can_close = fields.Boolean('Can Close', compute='_get_post_karma_rights', compute_sudo=False)
    can_unlink = fields.Boolean('Can Unlink', compute='_get_post_karma_rights', compute_sudo=False)
    can_upvote = fields.Boolean('Can Upvote', compute='_get_post_karma_rights', compute_sudo=False)
    can_downvote = fields.Boolean('Can Downvote', compute='_get_post_karma_rights', compute_sudo=False)
    can_comment = fields.Boolean('Can Comment', compute='_get_post_karma_rights', compute_sudo=False)
    can_comment_convert = fields.Boolean('Can Convert to Comment', compute='_get_post_karma_rights', compute_sudo=False)
    can_view = fields.Boolean('Can View', compute='_get_post_karma_rights', search='_search_can_view', compute_sudo=False)
    can_display_biography = fields.Boolean("Is the author's biography visible from his post", compute='_get_post_karma_rights', compute_sudo=False)
    can_post = fields.Boolean('Can Automatically be Validated', compute='_get_post_karma_rights', compute_sudo=False)
    can_flag = fields.Boolean('Can Flag', compute='_get_post_karma_rights', compute_sudo=False)
    can_moderate = fields.Boolean('Can Moderate', compute='_get_post_karma_rights', compute_sudo=False)
    can_use_full_editor = fields.Boolean(
        compute='_get_post_karma_rights', compute_sudo=False,
        help="Editor Features: image and links")

    def _search_can_view(self, operator, value):
        if operator not in ('=', '!=', '<>'):
            raise ValueError('Invalid operator: %s' % (operator,))

        if not value:
            operator = operator == "=" and '!=' or '='
            value = True

        user = self.env.user
        # Won't impact sitemap, search() in converter is forced as public user
        if self.env.is_admin():
            return [(1, '=', 1)]

        req = """
            SELECT p.id
            FROM forum_post p
                   LEFT JOIN res_users u ON p.create_uid = u.id
                   LEFT JOIN forum_forum f ON p.forum_id = f.id
            WHERE
                (p.create_uid = %s and f.karma_close_own <= %s)
                or (p.create_uid != %s and f.karma_close_all <= %s)
                or (
                    u.karma > 0
                    and (p.active or p.create_uid = %s)
                )
        """

        op = operator == "=" and "inselect" or "not inselect"

        # don't use param named because orm will add other param (test_active, ...)
        return [('id', op, (req, (user.id, user.karma, user.id, user.karma, user.id)))]

    @api.depends('content')
    def _get_plain_content(self):
        for post in self:
            post.plain_content = tools.html2plaintext(post.content)[0:500] if post.content else False

    @api.depends('vote_count', 'forum_id.relevancy_post_vote', 'forum_id.relevancy_time_decay')
    def _compute_relevancy(self):
        for post in self:
            if post.create_date:
                days = (datetime.today() - post.create_date).days
                post.relevancy = math.copysign(1, post.vote_count) * (abs(post.vote_count - 1) ** post.forum_id.relevancy_post_vote / (days + 2) ** post.forum_id.relevancy_time_decay)
            else:
                post.relevancy = 0

    def _get_user_vote(self):
        votes = self.env['forum.post.vote'].search_read([('post_id', 'in', self._ids), ('user_id', '=', self._uid)], ['vote', 'post_id'])
        mapped_vote = dict([(v['post_id'][0], v['vote']) for v in votes])
        for vote in self:
            vote.user_vote = mapped_vote.get(vote.id, 0)

    @api.depends('vote_ids.vote')
    def _get_vote_count(self):
        read_group_res = self.env['forum.post.vote']._read_group([('post_id', 'in', self._ids)], ['post_id', 'vote'], ['post_id', 'vote'], lazy=False)
        result = dict.fromkeys(self._ids, 0)
        for data in read_group_res:
            result[data['post_id'][0]] += data['__count'] * int(data['vote'])
        for post in self:
            post.vote_count = result[post.id]

    def _get_user_favourite(self):
        for post in self:
            post.user_favourite = post._uid in post.favourite_ids.ids

    @api.depends('favourite_ids')
    def _get_favorite_count(self):
        for post in self:
            post.favourite_count = len(post.favourite_ids)

    @api.depends('create_uid', 'parent_id')
    def _is_self_reply(self):
        for post in self:
            post.self_reply = post.parent_id.create_uid.id == post._uid

    @api.depends('child_ids')
    def _get_child_count(self):
        for post in self:
            post.child_count = len(post.child_ids)

    def _get_uid_has_answered(self):
        for post in self:
            post.uid_has_answered = post._uid in post.child_ids.create_uid.ids

    @api.depends('child_ids.is_correct')
    def _get_has_validated_answer(self):
        for post in self:
            post.has_validated_answer = any(answer.is_correct for answer in post.child_ids)

    @api.depends_context('uid')
    def _get_post_karma_rights(self):
        user = self.env.user
        is_admin = self.env.is_admin()
        # sudoed recordset instead of individual posts so values can be
        # prefetched in bulk
        for post, post_sudo in zip(self, self.sudo()):
            is_creator = post.create_uid == user

            post.karma_accept = post.forum_id.karma_answer_accept_own if post.parent_id.create_uid == user else post.forum_id.karma_answer_accept_all
            post.karma_edit = post.forum_id.karma_edit_own if is_creator else post.forum_id.karma_edit_all
            post.karma_close = post.forum_id.karma_close_own if is_creator else post.forum_id.karma_close_all
            post.karma_unlink = post.forum_id.karma_unlink_own if is_creator else post.forum_id.karma_unlink_all
            post.karma_comment = post.forum_id.karma_comment_own if is_creator else post.forum_id.karma_comment_all
            post.karma_comment_convert = post.forum_id.karma_comment_convert_own if is_creator else post.forum_id.karma_comment_convert_all
            post.karma_flag = post.forum_id.karma_flag

            post.can_ask = is_admin or user.karma >= post.forum_id.karma_ask
            post.can_answer = is_admin or user.karma >= post.forum_id.karma_answer
            post.can_accept = is_admin or user.karma >= post.karma_accept
            post.can_edit = is_admin or user.karma >= post.karma_edit
            post.can_close = is_admin or user.karma >= post.karma_close
            post.can_unlink = is_admin or user.karma >= post.karma_unlink
            post.can_upvote = is_admin or user.karma >= post.forum_id.karma_upvote or post.user_vote == -1
            post.can_downvote = is_admin or user.karma >= post.forum_id.karma_downvote or post.user_vote == 1
            post.can_comment = is_admin or user.karma >= post.karma_comment
            post.can_comment_convert = is_admin or user.karma >= post.karma_comment_convert
            post.can_view = post.can_close or post_sudo.active and (post_sudo.create_uid.karma > 0 or post_sudo.create_uid == user)
            post.can_display_biography = is_admin or post_sudo.create_uid.karma >= post.forum_id.karma_user_bio
            post.can_post = is_admin or user.karma >= post.forum_id.karma_post
            post.can_flag = is_admin or user.karma >= post.forum_id.karma_flag
            post.can_moderate = is_admin or user.karma >= post.forum_id.karma_moderate
            post.can_use_full_editor = is_admin or user.karma >= post.forum_id.karma_editor

    def _update_content(self, content, forum_id):
        forum = self.env['forum.forum'].browse(forum_id)
        if content and self.env.user.karma < forum.karma_dofollow:
            for match in re.findall(r'<a\s.*href=".*?">', content):
                escaped_match = re.escape(match)  # replace parenthesis or special char in regex
                url_match = re.match(r'^.*href="(.*)".*', match) # extracting the link allows to rebuild a clean link tag
                url = url_match.group(1)
                content = re.sub(escaped_match, f'<a rel="nofollow" href="{url}">', content)

        if self.env.user.karma < forum.karma_editor:
            filter_regexp = r'(<img.*?>)|(<a[^>]*?href[^>]*?>)|(<[a-z|A-Z]+[^>]*style\s*=\s*[\'"][^\'"]*\s*background[^:]*:[^url;]*url)'
            content_match = re.search(filter_regexp, content, re.I)
            if content_match:
                raise AccessError(_('%d karma required to post an image or link.', forum.karma_editor))
        return content

    def _default_website_meta(self):
        res = super(Post, self)._default_website_meta()
        res['default_opengraph']['og:title'] = res['default_twitter']['twitter:title'] = self.name
        res['default_opengraph']['og:description'] = res['default_twitter']['twitter:description'] = self.plain_content
        res['default_opengraph']['og:image'] = res['default_twitter']['twitter:image'] = self.env['website'].image_url(self.create_uid, 'image_1024')
        res['default_twitter']['twitter:card'] = 'summary'
        res['default_meta_description'] = self.plain_content
        return res

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create recursive forum posts.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'content' in vals and vals.get('forum_id'):
                vals['content'] = self._update_content(vals['content'], vals['forum_id'])

        posts = super(Post, self.with_context(mail_create_nolog=True)).create(vals_list)

        for post in posts:
            # deleted or closed questions
            if post.parent_id and (post.parent_id.state == 'close' or post.parent_id.active is False):
                raise UserError(_('Posting answer on a [Deleted] or [Closed] question is not possible.'))
            # karma-based access
            if not post.parent_id and not post.can_ask:
                raise AccessError(_('%d karma required to create a new question.', post.forum_id.karma_ask))
            elif post.parent_id and not post.can_answer:
                raise AccessError(_('%d karma required to answer a question.', post.forum_id.karma_answer))
            if not post.parent_id and not post.can_post:
                post.sudo().state = 'pending'

            # add karma for posting new questions
            if not post.parent_id and post.state == 'active':
                self.env.user.sudo().add_karma(post.forum_id.karma_gen_question_new)
        posts.post_notification()
        return posts

    @api.model
    def _get_mail_message_access(self, res_ids, operation, model_name=None):
        # XDO FIXME: to be correctly fixed with new _get_mail_message_access and filter access rule
        if operation in ('write', 'unlink') and (not model_name or model_name == 'forum.post'):
            # Make sure only author or moderator can edit/delete messages
            for post in self.browse(res_ids):
                if not post.can_edit:
                    raise AccessError(_('%d karma required to edit a post.', post.karma_edit))
        return super(Post, self)._get_mail_message_access(res_ids, operation, model_name=model_name)

    def write(self, vals):
        trusted_keys = ['active', 'is_correct', 'tag_ids']  # fields where security is checked manually
        if 'forum_id' in vals:
            forum = self.env['forum.forum'].browse(vals['forum_id'])
            forum.check_access_rule('write')
        if 'content' in vals:
            vals['content'] = self._update_content(vals['content'], self.forum_id.id)

        tag_ids = False
        if 'tag_ids' in vals:
            tag_ids = set(self.new({'tag_ids': vals['tag_ids']}).tag_ids.ids)

        for post in self:
            if 'state' in vals:
                if vals['state'] in ['active', 'close']:
                    if not post.can_close:
                        raise AccessError(_('%d karma required to close or reopen a post.', post.karma_close))
                    trusted_keys += ['state', 'closed_uid', 'closed_date', 'closed_reason_id']
                elif vals['state'] == 'flagged':
                    if not post.can_flag:
                        raise AccessError(_('%d karma required to flag a post.', post.forum_id.karma_flag))
                    trusted_keys += ['state', 'flag_user_id']
            if 'active' in vals:
                if not post.can_unlink:
                    raise AccessError(_('%d karma required to delete or reactivate a post.', post.karma_unlink))
            if 'is_correct' in vals:
                if not post.can_accept:
                    raise AccessError(_('%d karma required to accept or refuse an answer.', post.karma_accept))
                # update karma except for self-acceptance
                mult = 1 if vals['is_correct'] else -1
                if vals['is_correct'] != post.is_correct and post.create_uid.id != self._uid:
                    post.create_uid.sudo().add_karma(post.forum_id.karma_gen_answer_accepted * mult)
                    self.env.user.sudo().add_karma(post.forum_id.karma_gen_answer_accept * mult)
            if tag_ids:
                if set(post.tag_ids.ids) != tag_ids and self.env.user.karma < post.forum_id.karma_edit_retag:
                    raise AccessError(_('%d karma required to retag.', post.forum_id.karma_edit_retag))
            if any(key not in trusted_keys for key in vals) and not post.can_edit:
                raise AccessError(_('%d karma required to edit a post.', post.karma_edit))

        res = super(Post, self).write(vals)

        # if post content modify, notify followers
        if 'content' in vals or 'name' in vals:
            for post in self:
                if post.parent_id:
                    body, subtype_xmlid = _('Answer Edited'), 'website_forum.mt_answer_edit'
                    obj_id = post.parent_id
                else:
                    body, subtype_xmlid = _('Question Edited'), 'website_forum.mt_question_edit'
                    obj_id = post
                obj_id.message_post(body=body, subtype_xmlid=subtype_xmlid)
        if 'active' in vals:
            answers = self.env['forum.post'].with_context(active_test=False).search([('parent_id', 'in', self.ids)])
            if answers:
                answers.write({'active': vals['active']})
        return res

    def post_notification(self):
        for post in self:
            tag_partners = post.tag_ids.sudo().mapped('message_partner_ids')

            if post.state == 'active' and post.parent_id:
                post.parent_id.message_post_with_view(
                    'website_forum.forum_post_template_new_answer',
                    subject=_('Re: %s', post.parent_id.name),
                    partner_ids=[(4, p.id) for p in tag_partners],
                    subtype_id=self.env['ir.model.data']._xmlid_to_res_id('website_forum.mt_answer_new'))
            elif post.state == 'active' and not post.parent_id:
                post.message_post_with_view(
                    'website_forum.forum_post_template_new_question',
                    subject=post.name,
                    partner_ids=[(4, p.id) for p in tag_partners],
                    subtype_id=self.env['ir.model.data']._xmlid_to_res_id('website_forum.mt_question_new'))
            elif post.state == 'pending' and not post.parent_id:
                # TDE FIXME: in master, you should probably use a subtype;
                # however here we remove subtype but set partner_ids
                partners = post.sudo().message_partner_ids | tag_partners
                partners = partners.filtered(lambda partner: partner.user_ids and any(user.karma >= post.forum_id.karma_moderate for user in partner.user_ids))

                post.message_post_with_view(
                    'website_forum.forum_post_template_validation',
                    subject=post.name,
                    partner_ids=partners.ids,
                    subtype_id=self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'))
        return True

    def reopen(self):
        if any(post.parent_id or post.state != 'close' for post in self):
            return False

        reason_offensive = self.env.ref('website_forum.reason_7')
        reason_spam = self.env.ref('website_forum.reason_8')
        for post in self:
            if post.closed_reason_id in (reason_offensive, reason_spam):
                _logger.info('Upvoting user <%s>, reopening spam/offensive question',
                             post.create_uid)

                karma = post.forum_id.karma_gen_answer_flagged
                if post.closed_reason_id == reason_spam:
                    # If first post, increase the karma to add
                    count_post = post.search_count([('parent_id', '=', False), ('forum_id', '=', post.forum_id.id), ('create_uid', '=', post.create_uid.id)])
                    if count_post == 1:
                        karma *= 10
                post.create_uid.sudo().add_karma(karma * -1)

        self.sudo().write({'state': 'active'})

    def close(self, reason_id):
        if any(post.parent_id for post in self):
            return False

        reason_offensive = self.env.ref('website_forum.reason_7').id
        reason_spam = self.env.ref('website_forum.reason_8').id
        if reason_id in (reason_offensive, reason_spam):
            for post in self:
                _logger.info('Downvoting user <%s> for posting spam/offensive contents',
                             post.create_uid)
                karma = post.forum_id.karma_gen_answer_flagged
                if reason_id == reason_spam:
                    # If first post, increase the karma to remove
                    count_post = post.search_count([('parent_id', '=', False), ('forum_id', '=', post.forum_id.id), ('create_uid', '=', post.create_uid.id)])
                    if count_post == 1:
                        karma *= 10
                post.create_uid.sudo().add_karma(karma)

        self.write({
            'state': 'close',
            'closed_uid': self._uid,
            'closed_date': datetime.today().strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT),
            'closed_reason_id': reason_id,
        })
        return True

    def validate(self):
        for post in self:
            if not post.can_moderate:
                raise AccessError(_('%d karma required to validate a post.', post.forum_id.karma_moderate))
            # if state == pending, no karma previously added for the new question
            if post.state == 'pending':
                post.create_uid.sudo().add_karma(post.forum_id.karma_gen_question_new)
            post.write({
                'state': 'active',
                'active': True,
                'moderator_id': self.env.user.id,
            })
            post.post_notification()
        return True

    def refuse(self):
        for post in self:
            if not post.can_moderate:
                raise AccessError(_('%d karma required to refuse a post.', post.forum_id.karma_moderate))
            post.moderator_id = self.env.user
        return True

    def flag(self):
        res = []
        for post in self:
            if not post.can_flag:
                raise AccessError(_('%d karma required to flag a post.', post.forum_id.karma_flag))
            if post.state == 'flagged':
               res.append({'error': 'post_already_flagged'})
            elif post.state == 'active':
                # TODO: potential performance bottleneck, can be batched
                post.write({
                    'state': 'flagged',
                    'flag_user_id': self.env.user.id,
                })
                res.append(
                    post.can_moderate and
                    {'success': 'post_flagged_moderator'} or
                    {'success': 'post_flagged_non_moderator'}
                )
            else:
                res.append({'error': 'post_non_flaggable'})
        return res

    def mark_as_offensive(self, reason_id):
        for post in self:
            if not post.can_moderate:
                raise AccessError(_('%d karma required to mark a post as offensive.', post.forum_id.karma_moderate))
            # remove some karma
            _logger.info('Downvoting user <%s> for posting spam/offensive contents', post.create_uid)
            post.create_uid.sudo().add_karma(post.forum_id.karma_gen_answer_flagged)
            # TODO: potential bottleneck, could be done in batch
            post.write({
                'state': 'offensive',
                'moderator_id': self.env.user.id,
                'closed_date': fields.Datetime.now(),
                'closed_reason_id': reason_id,
                'active': False,
            })
        return True

    def mark_as_offensive_batch(self, key, values):
        spams = self.browse()
        if key == 'create_uid':
            spams = self.filtered(lambda x: x.create_uid.id in values)
        elif key == 'country_id':
            spams = self.filtered(lambda x: x.create_uid.country_id.id in values)
        elif key == 'post_id':
            spams = self.filtered(lambda x: x.id in values)

        reason_id = self.env.ref('website_forum.reason_8').id
        _logger.info('User %s marked as spams (in batch): %s' % (self.env.uid, spams))
        return spams.mark_as_offensive(reason_id)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_enough_karma(self):
        for post in self:
            if not post.can_unlink:
                raise AccessError(_('%d karma required to unlink a post.', post.karma_unlink))

    def unlink(self):
        # if unlinking an answer with accepted answer: remove provided karma
        for post in self:
            if post.is_correct:
                post.create_uid.sudo().add_karma(post.forum_id.karma_gen_answer_accepted * -1)
                self.env.user.sudo().add_karma(post.forum_id.karma_gen_answer_accepted * -1)
        return super(Post, self).unlink()

    def bump(self):
        """ Bump a question: trigger a write_date by writing on a dummy bump_date
        field. One cannot bump a question more than once every 10 days. """
        self.ensure_one()
        if self.forum_id.allow_bump and not self.child_ids and (datetime.today() - datetime.strptime(self.write_date, tools.DEFAULT_SERVER_DATETIME_FORMAT)).days > 9:
            # write through super to bypass karma; sudo to allow public user to bump any post
            return self.sudo().write({'bump_date': fields.Datetime.now()})
        return False

    def vote(self, upvote=True):
        self.ensure_one()
        Vote = self.env['forum.post.vote']
        existing_vote = Vote.search([('post_id', '=', self.id), ('user_id', '=', self._uid)])
        new_vote_value = '1' if upvote else '-1'
        if existing_vote:
            if upvote:
                new_vote_value = '0' if existing_vote.vote == '-1' else '1'
            else:
                new_vote_value = '0' if existing_vote.vote == '1' else '-1'
            existing_vote.vote = new_vote_value
        else:
            Vote.create({'post_id': self.id, 'vote': new_vote_value})
        return {'vote_count': self.vote_count, 'user_vote': new_vote_value}

    def convert_answer_to_comment(self):
        """ Tools to convert an answer (forum.post) to a comment (mail.message).
        The original post is unlinked and a new comment is posted on the question
        using the post create_uid as the comment's author. """
        self.ensure_one()
        if not self.parent_id:
            return self.env['mail.message']

        # karma-based action check: use the post field that computed own/all value
        if not self.can_comment_convert:
            raise AccessError(_('%d karma required to convert an answer to a comment.', self.karma_comment_convert))

        # post the message
        question = self.parent_id
        self_sudo = self.sudo()
        values = {
            'author_id': self_sudo.create_uid.partner_id.id,  # use sudo here because of access to res.users model
            'email_from': self_sudo.create_uid.email_formatted,  # use sudo here because of access to res.users model
            'body': tools.html_sanitize(self.content, sanitize_attributes=True, strip_style=True, strip_classes=True),
            'message_type': 'comment',
            'subtype_xmlid': 'mail.mt_comment',
            'date': self.create_date,
        }
        # done with the author user to have create_uid correctly set
        new_message = question.with_user(self_sudo.create_uid.id).with_context(mail_create_nosubscribe=True).sudo().message_post(**values).sudo(False)

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
        is_author = comment.author_id.id == self.env.user.partner_id.id
        karma_own = post.forum_id.karma_comment_convert_own
        karma_all = post.forum_id.karma_comment_convert_all
        karma_convert = is_author and karma_own or karma_all
        can_convert = self.env.user.karma >= karma_convert
        if not can_convert:
            if is_author and karma_own < karma_all:
                raise AccessError(_('%d karma required to convert your comment to an answer.', karma_own))
            else:
                raise AccessError(_('%d karma required to convert a comment to an answer.', karma_all))

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
            'name': _('Re: %s') % (question.name or ''),
        }
        # done with the author user to have create_uid correctly set
        new_post = self.with_user(post_create_uid).sudo().create(post_values).sudo(False)

        # delete comment
        comment.unlink()

        return new_post

    def unlink_comment(self, message_id):
        result = []
        for post in self:
            user = self.env.user
            comment = self.env['mail.message'].sudo().browse(message_id)
            if not comment.model == 'forum.post' or not comment.res_id == post.id:
                result.append(False)
                continue
            # karma-based action check: must check the message's author to know if own or all
            karma_unlink = (
                comment.author_id.id == user.partner_id.id and
                post.forum_id.karma_comment_unlink_own or post.forum_id.karma_comment_unlink_all
            )
            can_unlink = user.karma >= karma_unlink
            if not can_unlink:
                raise AccessError(_('%d karma required to unlink a comment.', karma_unlink))
            result.append(comment.unlink())
        return result

    def _set_viewed(self):
        self.ensure_one()
        return sql.increment_fields_skiplock(self, 'views')

    def _get_access_action(self, access_uid=None, force_website=False):
        """ Instead of the classic form view, redirect to the post on the website directly """
        self.ensure_one()
        if not force_website and not self.state == 'active':
            return super(Post, self)._get_access_action(access_uid=access_uid, force_website=force_website)
        return {
            'type': 'ir.actions.act_url',
            'url': '/forum/%s/%s' % (self.forum_id.id, self.id),
            'target': 'self',
            'target_type': 'public',
            'res_id': self.id,
        }

    def _notify_get_recipients_groups(self, msg_vals=None):
        """ Add access button to everyone if the document is active. """
        groups = super(Post, self)._notify_get_recipients_groups(msg_vals=msg_vals)
        if not self:
            return groups

        self.ensure_one()
        if self.state == 'active':
            for _group_name, _group_method, group_data in groups:
                group_data['has_button_access'] = True

        return groups

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *, message_type='notification', **kwargs):
        if self.ids and message_type == 'comment':  # user comments have a restriction on karma
            # add followers of comments on the parent post
            if self.parent_id:
                partner_ids = kwargs.get('partner_ids', [])
                comment_subtype = self.sudo().env.ref('mail.mt_comment')
                question_followers = self.env['mail.followers'].sudo().search([
                    ('res_model', '=', self._name),
                    ('res_id', '=', self.parent_id.id),
                    ('partner_id', '!=', False),
                ]).filtered(lambda fol: comment_subtype in fol.subtype_ids).mapped('partner_id')
                partner_ids += question_followers.ids
                kwargs['partner_ids'] = partner_ids

            self.ensure_one()
            if not self.can_comment:
                raise AccessError(_('%d karma required to comment.', self.karma_comment))
            if not kwargs.get('record_name') and self.parent_id:
                kwargs['record_name'] = self.parent_id.name
        return super(Post, self).message_post(message_type=message_type, **kwargs)

    def _notify_thread_by_inbox(self, message, recipients_data, msg_vals=False, **kwargs):
        """ Override to avoid keeping all notified recipients of a comment.
        We avoid tracking needaction on post comments. Only emails should be
        sufficient. """
        if msg_vals is None:
            msg_vals = {}
        if msg_vals.get('message_type', message.message_type) == 'comment':
            return
        return super(Post, self)._notify_thread_by_inbox(message, recipients_data, msg_vals=msg_vals, **kwargs)

    def _compute_website_url(self):
        self.website_url = False
        for post in self.filtered(lambda post: post.id):
            forum_slug = slug(post.forum_id)
            post_slug = slug(post)
            anchor = post.parent_id and '#answer_%d' % post.id or ''
            post.website_url = f'/forum/{forum_slug}/{post_slug}{anchor}'

    def go_to_website(self):
        self.ensure_one()
        if not self.website_url:
            return False
        return self.env['website'].get_client_action(self.website_url)

    @api.model
    def _search_get_detail(self, website, order, options):
        with_description = options['displayDescription']
        with_date = options['displayDetail']
        search_fields = ['name']
        fetch_fields = ['id', 'name', 'website_url']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'website_url', 'type': 'text', 'truncate': False},
        }

        domain = website.website_domain()
        domain += [('parent_id', '=', False), ('state', '=', 'active'), ('can_view', '=', True)]
        forum = options.get('forum')
        if forum:
            domain += [('forum_id', '=', unslug(forum)[1])]
        tags = options.get('tag')
        if tags:
            domain += [('tag_ids', 'in', [unslug(tag)[1] for tag in tags.split(',')])]
        filters = options.get('filters')
        if filters == 'unanswered':
            domain += [('child_ids', '=', False)]
        elif filters == 'solved':
            domain += [('has_validated_answer', '=', True)]
        elif filters == 'unsolved':
            domain += [('has_validated_answer', '=', False)]
        user = self.env.user
        my = options.get('my')
        if my == 'mine':
            domain += [('create_uid', '=', user.id)]
        elif my == 'followed':
            domain += [('message_partner_ids', '=', user.partner_id.id)]
        elif my == 'tagged':
            domain += [('tag_ids.message_partner_ids', '=', user.partner_id.id)]
        elif my == 'favourites':
            domain += [('favourite_ids', '=', user.id)]

        # 'sorting' from the form's "Order by" overrides order during auto-completion
        order = options.get('sorting', order)
        if 'is_published' in order:
            parts = [part for part in order.split(',') if 'is_published' not in part]
            order = ','.join(parts)

        if with_description:
            search_fields.append('content')
            fetch_fields.append('content')
            mapping['description'] = {'name': 'content', 'type': 'text', 'html': True, 'match': True}
        if with_date:
            fetch_fields.append('write_date')
            mapping['detail'] = {'name': 'date', 'type': 'html'}
        return {
            'model': 'forum.post',
            'base_domain': [domain],
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-comment-o',
            'order': order,
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        with_date = 'detail' in mapping
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)
        for post, data in zip(self, results_data):
            if with_date:
                data['date'] = self.env['ir.qweb.field.date'].record_to_html(post, 'write_date', {})
        return results_data


class PostReason(models.Model):
    _name = "forum.post.reason"
    _description = "Post Closing Reason"
    _order = 'name'

    name = fields.Char(string='Closing Reason', required=True, translate=True)
    reason_type = fields.Selection([('basic', 'Basic'), ('offensive', 'Offensive')], string='Reason Type', default='basic')


class Vote(models.Model):
    _name = 'forum.post.vote'
    _description = 'Post Vote'
    _order = 'create_date desc, id desc'

    post_id = fields.Many2one('forum.post', string='Post', ondelete='cascade', required=True)
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self._uid)
    vote = fields.Selection([('1', '1'), ('-1', '-1'), ('0', '0')], string='Vote', required=True, default='1')
    create_date = fields.Datetime('Create Date', index=True, readonly=True)
    forum_id = fields.Many2one('forum.forum', string='Forum', related="post_id.forum_id", store=True, readonly=False)
    recipient_id = fields.Many2one('res.users', string='To', related="post_id.create_uid", store=True, readonly=False)

    _sql_constraints = [
        ('vote_uniq', 'unique (post_id, user_id)', "Vote already exists !"),
    ]

    def _get_karma_value(self, old_vote, new_vote, up_karma, down_karma):
        _karma_upd = {
            '-1': {'-1': 0, '0': -1 * down_karma, '1': -1 * down_karma + up_karma},
            '0': {'-1': 1 * down_karma, '0': 0, '1': up_karma},
            '1': {'-1': -1 * up_karma + down_karma, '0': -1 * up_karma, '1': 0}
        }
        return _karma_upd[old_vote][new_vote]

    @api.model_create_multi
    def create(self, vals_list):
        # can't modify owner of a vote
        if not self.env.is_admin():
            for vals in vals_list:
                vals.pop('user_id', None)

        votes = super(Vote, self).create(vals_list)

        for vote in votes:
            vote._check_general_rights()
            vote._check_karma_rights(vote.vote == '1')

            # karma update
            vote._vote_update_karma('0', vote.vote)
        return votes

    def write(self, values):
        # can't modify owner of a vote
        if not self.env.is_admin():
            values.pop('user_id', None)

        for vote in self:
            vote._check_general_rights(values)
            if 'vote' in values:
                if (values['vote'] == '1' or vote.vote == '-1' and values['vote'] == '0'):
                    upvote = True
                elif (values['vote'] == '-1' or vote.vote == '1' and values['vote'] == '0'):
                    upvote = False
                vote._check_karma_rights(upvote)

                # karma update
                vote._vote_update_karma(vote.vote, values['vote'])

        res = super(Vote, self).write(values)
        return res

    def _check_general_rights(self, vals={}):
        post = self.post_id
        if vals.get('post_id'):
            post = self.env['forum.post'].browse(vals.get('post_id'))
        if not self.env.is_admin():
            # own post check
            if self._uid == post.create_uid.id:
                raise UserError(_('It is not allowed to vote for its own post.'))
            # own vote check
            if self._uid != self.user_id.id:
                raise UserError(_('It is not allowed to modify someone else\'s vote.'))

    def _check_karma_rights(self, upvote=None):
        # karma check
        if upvote and not self.post_id.can_upvote:
            raise AccessError(_('%d karma required to upvote.', self.post_id.forum_id.karma_upvote))
        elif not upvote and not self.post_id.can_downvote:
            raise AccessError(_('%d karma required to downvote.', self.post_id.forum_id.karma_downvote))

    def _vote_update_karma(self, old_vote, new_vote):
        if self.post_id.parent_id:
            karma_value = self._get_karma_value(old_vote, new_vote, self.forum_id.karma_gen_answer_upvote, self.forum_id.karma_gen_answer_downvote)
        else:
            karma_value = self._get_karma_value(old_vote, new_vote, self.forum_id.karma_gen_question_upvote, self.forum_id.karma_gen_question_downvote)
        self.recipient_id.sudo().add_karma(karma_value)


class Tags(models.Model):
    _name = "forum.tag"
    _description = "Forum Tag"
    _inherit = ['mail.thread', 'website.seo.metadata']

    name = fields.Char('Name', required=True)
    forum_id = fields.Many2one('forum.forum', string='Forum', required=True)
    post_ids = fields.Many2many(
        'forum.post', 'forum_tag_rel', 'forum_tag_id', 'forum_id',
        string='Posts', domain=[('state', '=', 'active')])
    posts_count = fields.Integer('Number of Posts', compute='_get_posts_count', store=True)

    _sql_constraints = [
        ('name_uniq', 'unique (name, forum_id)', "Tag name already exists !"),
    ]

    @api.depends("post_ids", "post_ids.tag_ids", "post_ids.state", "post_ids.active")
    def _get_posts_count(self):
        for tag in self:
            tag.posts_count = len(tag.post_ids)  # state filter is in field domain

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            forum = self.env['forum.forum'].browse(vals.get('forum_id'))
            if self.env.user.karma < forum.karma_tag_create:
                raise AccessError(_('%d karma required to create a new Tag.', forum.karma_tag_create))
        return super(Tags, self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True)).create(vals_list)
