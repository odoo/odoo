# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import textwrap
from collections import defaultdict
from operator import itemgetter

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.addons.http_routing.models.ir_http import slug
from odoo.tools.translate import html_translate

MOST_USED_TAGS_COUNT = 5  # Number of tags to track as "most used" to display on frontend


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
    _order = "sequence, id"

    @api.model
    def _get_default_welcome_message(self):
        return Markup("""
                <h2 class="display-3-fs" style="text-align: center;clear-both;font-weight: bold;">%(message_intro)s</h2>
                <div class="text-white">
                    <p class="lead o_default_snippet_text" style="text-align: center;">%(message_post)s</p>
                    <p style="text-align: center;">
                        <a class="btn btn-primary forum_register_url" href="/web/login">%(register_text)s</a>
                        <button type="button" class="btn btn-light js_close_intro" aria-label="Dismiss message">
                            %(hide_text)s
                        </button>
                    </p>
                </div>
            """) % {
            'message_intro': _("Welcome!"),
            'message_post': _(
                "Share and discuss the best content and new marketing ideas, build your professional profile and become"
                " a better marketer together."
            ),
            'hide_text': _('Dismiss'),
            'register_text': _('Sign up'),
        }

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
    faq = fields.Html(
        'Guidelines', translate=html_translate,
        sanitize=True, sanitize_overridable=True)
    description = fields.Text('Description', translate=True)
    teaser = fields.Text('Teaser', compute='_compute_teaser', store=True)
    welcome_message = fields.Html(
        'Welcome Message', translate=html_translate,
        default=_get_default_welcome_message,
        sanitize_attributes=False, sanitize_form=False)
    default_order = fields.Selection([
        ('create_date desc', 'Newest'),
        ('last_activity_date desc', 'Last Updated'),
        ('vote_count desc', 'Most Voted'),
        ('relevancy desc', 'Relevance'),
        ('child_count desc', 'Answered')],
        string='Default', required=True, default='last_activity_date desc')
    relevancy_post_vote = fields.Float('First Relevance Parameter', default=0.8, help="This formula is used in order to sort by relevance. The variable 'votes' represents number of votes for a post, and 'days' is number of days since the post creation")
    relevancy_time_decay = fields.Float('Second Relevance Parameter', default=1.8)
    allow_share = fields.Boolean('Sharing Options', default=True,
                                 help='After posting the user will be proposed to share its question '
                                      'or answer on social networks, enabling social network propagation '
                                      'of the forum content.')
    # posts statistics
    post_ids = fields.One2many('forum.post', 'forum_id', string='Posts')
    last_post_id = fields.Many2one('forum.post', compute='_compute_last_post_id')
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
    has_pending_post = fields.Boolean(string='Has pending post', compute='_compute_has_pending_post')
    can_moderate = fields.Boolean(string="Is a moderator", compute="_compute_can_moderate")

    # tags
    tag_ids = fields.One2many('forum.tag', 'forum_id', string='Tags')
    tag_most_used_ids = fields.One2many('forum.tag', string="Most used tags", compute='_compute_tag_ids_usage')
    tag_unused_ids = fields.One2many('forum.tag', string="Unused tags", compute='_compute_tag_ids_usage')

    @api.depends_context('uid')
    def _compute_has_pending_post(self):
        domain = [
            ('create_uid', '=', self.env.user.id),
            ('state', '=', 'pending'),
            ('parent_id', '=', False),
        ]
        pending_forums = self.env['forum.forum'].search([
            ('id', 'in', self.ids),
            ('post_ids', 'any', domain),
        ])
        pending_forums.has_pending_post = True
        (self - pending_forums).has_pending_post = False

    @api.depends_context('uid')
    @api.depends('karma_moderate')
    def _compute_can_moderate(self):
        for forum in self:
            forum.can_moderate = self.env.user.karma >= forum.karma_moderate

    @api.depends('post_ids', 'post_ids.tag_ids', 'post_ids.tag_ids.posts_count', 'tag_ids')
    def _compute_tag_ids_usage(self):
        forums_without_tags = self.filtered(lambda f: not f.tag_ids)
        forums_without_tags.tag_most_used_ids = forums_without_tags.tag_unused_ids = False
        forums_with_tags = self - forums_without_tags
        if not forums_with_tags:
            return

        tags_data = self.env['forum.tag'].search_read(
            [('forum_id', 'in', forums_with_tags.ids)],
            fields=['id', 'forum_id', 'posts_count'],
            order='forum_id, posts_count DESC, name, id',
        )
        current_forum_id = tags_data[0]['forum_id'][0]
        forum_tags = defaultdict(lambda: {'most_used_ids': [], 'unused_ids': []})

        for tag_data in tags_data:
            tag_id, tag_forum_id, posts_count = itemgetter('id', 'forum_id', 'posts_count')(tag_data)
            if tag_forum_id[0] != current_forum_id:
                current_forum_id = tag_forum_id[0]
            if not posts_count:  # Could be 0 or None
                forum_tags[current_forum_id]['unused_ids'].append(tag_id)
            elif len(forum_tags[current_forum_id]['most_used_ids']) < MOST_USED_TAGS_COUNT:
                forum_tags[current_forum_id]['most_used_ids'].append(tag_id)

        for forum in forums_with_tags:
            forum.tag_most_used_ids = self.env['forum.tag'].browse(forum_tags[forum.id]['most_used_ids'])
            forum.tag_unused_ids = self.env['forum.tag'].browse(forum_tags[forum.id]['unused_ids'])

    @api.depends('description')
    def _compute_teaser(self):
        for forum in self:
            forum.teaser = textwrap.shorten(forum.description, width=180, placeholder='...') if forum.description else ""

    @api.depends('post_ids')
    def _compute_last_post_id(self):
        for forum in self:
            forum.last_post_id = forum.post_ids.search(
                [('forum_id', '=', forum.id), ('parent_id', '=', False), ('state', '=', 'active')],
                order='create_date desc', limit=1,
            )

    @api.depends('post_ids.state', 'post_ids.views', 'post_ids.child_count', 'post_ids.favourite_count')
    def _compute_forum_statistics(self):
        default_stats = {'total_posts': 0, 'total_views': 0, 'total_answers': 0, 'total_favorites': 0}

        if not self.ids:
            self.update(default_stats)
            return

        result = {cid: dict(default_stats) for cid in self.ids}
        read_group_res = self.env['forum.post']._read_group(
            [('forum_id', 'in', self.ids), ('state', 'in', ('active', 'close')), ('parent_id', '=', False)],
            ['forum_id'],
            ['__count', 'views:sum', 'child_count:sum', 'favourite_count:sum'])
        for forum, count, views_sum, child_count_sum, favourite_count_sum in read_group_res:
            stat_forum = result[forum.id]
            stat_forum['total_posts'] += count
            stat_forum['total_views'] += views_sum
            stat_forum['total_answers'] += child_count_sum
            stat_forum['total_favorites'] += 1 if favourite_count_sum else 0

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

    # EXTENDS WEBSITE.MULTI.MIXIN

    def _compute_website_url(self):
        if not self.id:
            return False
        return f'/forum/{slug(self)}'

    # ----------------------------------------------------------------------
    # CRUD
    # ----------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        forums = super(
            Forum,
            self.with_context(mail_create_nolog=True, mail_create_nosubscribe=True)
        ).create(vals_list)
        self.env['website'].sudo()._update_forum_count()
        forums._set_default_faq()
        return forums

    def unlink(self):
        self.env['website'].sudo()._update_forum_count()
        return super().unlink()

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

        res = super().write(vals)
        if 'active' in vals:
            # archiving/unarchiving a forum does it on its posts, too
            self.env['forum.post'].with_context(active_test=False).search([('forum_id', 'in', self.ids)]).write({'active': vals['active']})

        if 'active' in vals or 'website_id' in vals:
            self.env['website'].sudo()._update_forum_count()
        return res

    def _set_default_faq(self):
        for forum in self:
            forum.faq = self.env['ir.ui.view']._render_template('website_forum.faq_accordion', {"forum": forum})

    # ----------------------------------------------------------------------
    # TOOLS
    # ----------------------------------------------------------------------

    def _tag_to_write_vals(self, tags=''):
        Tag = self.env['forum.tag']
        post_tags = []
        existing_keep = []
        user = self.env.user
        for tag_id_or_new_name in (tag.strip() for tag in tags.split(',') if tag and tag.strip()):
            if tag_id_or_new_name.startswith('_'):  # it's a new tag
                tag_name = tag_id_or_new_name[1:]
                # check that not already created meanwhile or maybe excluded by the limit on the search
                tag_ids = Tag.search([('name', '=', tag_name), ('forum_id', '=', self.id)], limit=1)
                if tag_ids:
                    existing_keep.append(tag_ids.id)
                else:
                    # check if user have Karma needed to create need tag
                    if user.exists() and user.karma >= self.karma_tag_create and tag_name:
                        post_tags.append((0, 0, {'name': tag_name, 'forum_id': self.id}))
            else:
                existing_keep.append(int(tag_id_or_new_name))
        post_tags.insert(0, [6, 0, existing_keep])
        return post_tags

    def _get_tags_first_char(self, tags=None):
        """Get set of first letter of forum tags.

        :param tags: tags recordset to further filter forum's tags that are also in these tags.
        """
        tag_ids = self.tag_ids if tags is None else (self.tag_ids & tags)
        return sorted({tag.name[0].upper() for tag in tag_ids if len(tag.name)})

    # ----------------------------------------------------------------------
    # WEBSITE
    # ----------------------------------------------------------------------

    def go_to_website(self):
        self.ensure_one()
        website_url = self._compute_website_url()
        if not website_url:
            return False
        return self.env['website'].get_client_action(self._compute_website_url())

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
