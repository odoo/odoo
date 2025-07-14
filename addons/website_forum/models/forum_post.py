# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import math
import re
from datetime import datetime

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError, AccessError
from odoo.fields import Domain
from odoo.tools import sql, SQL
from odoo.tools.json import scriptsafe as json_safe

_logger = logging.getLogger(__name__)


class ForumPost(models.Model):
    _name = 'forum.post'
    _description = 'Forum Post'
    _inherit = [
        'mail.thread',
        'website.seo.metadata',
        'website.searchable.mixin',
    ]
    _order = "is_correct DESC, vote_count DESC, last_activity_date DESC"

    _CUSTOMER_HEADERS_LIMIT_COUNT = 0  # never use X-Msg-To headers

    name = fields.Char('Title')
    forum_id = fields.Many2one('forum.forum', string='Forum', required=True, index=True)
    content = fields.Html('Content', strip_style=True)
    plain_content = fields.Text(
        'Plain Content',
        compute='_compute_plain_content', store=True)
    tag_ids = fields.Many2many('forum.tag', 'forum_tag_rel', 'forum_post_id', 'forum_tag_id', string='Tags')
    state = fields.Selection(
        [
            ('active', 'Active'), ('pending', 'Waiting Validation'),
            ('close', 'Closed'), ('offensive', 'Offensive'),
            ('flagged', 'Flagged'),
        ], string='Status', default='active')
    views = fields.Integer('Views', default=0, readonly=True, copy=False)
    active = fields.Boolean('Active', default=True)
    website_message_ids = fields.One2many(domain=lambda self: [('model', '=', self._name), ('message_type', 'in', ['email', 'comment', 'email_outgoing'])])
    website_url = fields.Char('Website URL', compute='_compute_website_url')
    website_id = fields.Many2one(related='forum_id.website_id', readonly=True)

    # history
    create_date = fields.Datetime('Asked on', index=True, readonly=True)
    create_uid = fields.Many2one('res.users', string='Created by', index=True, readonly=True)
    write_date = fields.Datetime('Updated on', index=True, readonly=True)
    last_activity_date = fields.Datetime(
        'Last activity on', readonly=True, required=True, default=fields.Datetime.now,
        help="Field to keep track of a post's last activity. Updated whenever it is replied to, "
             "or when a comment is added on the post or one of its replies."
    )
    write_uid = fields.Many2one('res.users', string='Updated by', index=True, readonly=True)
    relevancy = fields.Float('Relevance', compute="_compute_relevancy", store=True)

    # vote
    vote_ids = fields.One2many('forum.post.vote', 'post_id', string='Votes')
    user_vote = fields.Integer('My Vote', compute='_compute_user_vote')
    vote_count = fields.Integer('Total Votes', compute='_compute_vote_count', store=True)

    # favorite
    favourite_ids = fields.Many2many('res.users', string='Favourite')
    user_favourite = fields.Boolean('Is Favourite', compute='_compute_user_favourite')
    favourite_count = fields.Integer('Favorite', compute='_compute_favorite_count', store=True)

    # hierarchy
    is_correct = fields.Boolean('Correct', help='Correct answer or answer accepted')
    parent_id = fields.Many2one(
        'forum.post', string='Question',
        ondelete='cascade', readonly=True, index=True)
    self_reply = fields.Boolean('Reply to own question', compute='_compute_self_reply', store=True)
    child_ids = fields.One2many(
        'forum.post', 'parent_id', string='Post Answers',
        domain="[('forum_id', '=', forum_id)]")
    child_count = fields.Integer('Answers', compute='_compute_child_count', store=True)
    uid_has_answered = fields.Boolean('Has Answered', compute='_compute_uid_has_answered')
    has_validated_answer = fields.Boolean(
        'Is answered',
        compute='_compute_has_validated_answer', store=True)

    # offensive moderation tools
    flag_user_id = fields.Many2one('res.users', string='Flagged by')
    moderator_id = fields.Many2one('res.users', string='Reviewed by', readonly=True)

    # closing
    closed_reason_id = fields.Many2one('forum.post.reason', string='Reason', copy=False)
    closed_uid = fields.Many2one('res.users', string='Closed by', readonly=True, copy=False)
    closed_date = fields.Datetime('Closed on', readonly=True, copy=False)

    # karma calculation and access
    karma_accept = fields.Integer(
        'Convert comment to answer',
        compute='_compute_post_karma_rights', compute_sudo=False)
    karma_edit = fields.Integer(
        'Karma to edit',
        compute='_compute_post_karma_rights', compute_sudo=False)
    karma_close = fields.Integer(
        'Karma to close',
        compute='_compute_post_karma_rights', compute_sudo=False)
    karma_unlink = fields.Integer(
        'Karma to unlink',
        compute='_compute_post_karma_rights', compute_sudo=False)
    karma_comment = fields.Integer(
        'Karma to comment',
        compute='_compute_post_karma_rights', compute_sudo=False)
    karma_comment_convert = fields.Integer(
        'Karma to convert comment to answer',
        compute='_compute_post_karma_rights', compute_sudo=False)
    karma_flag = fields.Integer(
        'Flag a post as offensive',
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_ask = fields.Boolean(
        'Can Ask',
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_answer = fields.Boolean(
        'Can Answer',
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_accept = fields.Boolean(
        'Can Accept',
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_edit = fields.Boolean(
        'Can Edit',
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_close = fields.Boolean(
        'Can Close',
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_unlink = fields.Boolean(
        'Can Unlink',
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_upvote = fields.Boolean(
        'Can Upvote',
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_downvote = fields.Boolean(
        'Can Downvote',
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_comment = fields.Boolean(
        'Can Comment',
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_comment_convert = fields.Boolean(
        'Can Convert to Comment',
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_view = fields.Boolean(
        'Can View',
        compute='_compute_post_karma_rights', compute_sudo=False, search='_search_can_view')
    can_display_biography = fields.Boolean(
        "Is the author's biography visible from his post",
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_post = fields.Boolean(
        'Can Automatically be Validated',
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_flag = fields.Boolean(
        'Can Flag',
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_moderate = fields.Boolean(
        'Can Moderate',
        compute='_compute_post_karma_rights', compute_sudo=False)
    can_use_full_editor = fields.Boolean(  # Editor Features: image and links
        'Can Use Full Editor',
        compute='_compute_post_karma_rights', compute_sudo=False)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if self._has_cycle():
            raise ValidationError(_('You cannot create recursive forum posts.'))

    @api.depends('content')
    def _compute_plain_content(self):
        for post in self:
            post.plain_content = tools.html2plaintext(post.content)[0:500] if post.content else False

    @api.depends('name')
    def _compute_website_url(self):
        self.website_url = False
        for post in self.filtered(lambda post: post.id):
            anchor = f'#answer_{post.id}' if post.parent_id else ''
            post.website_url = f'/forum/{self.env["ir.http"]._slug(post.forum_id)}/{self.env["ir.http"]._slug(post)}{anchor}'

    @api.depends('vote_count', 'forum_id.relevancy_post_vote', 'forum_id.relevancy_time_decay')
    def _compute_relevancy(self):
        for post in self:
            if post.create_date:
                days = (datetime.today() - post.create_date).days
                post.relevancy = math.copysign(1, post.vote_count) * (abs(post.vote_count - 1) ** post.forum_id.relevancy_post_vote / (days + 2) ** post.forum_id.relevancy_time_decay)
            else:
                post.relevancy = 0

    @api.depends_context('uid')
    def _compute_user_vote(self):
        votes = self.env['forum.post.vote'].sudo().search_read([('post_id', 'in', self._ids), ('user_id', '=', self.env.uid)], ['vote', 'post_id'])
        mapped_vote = dict([(v['post_id'][0], v['vote']) for v in votes])
        for vote in self:
            vote.user_vote = mapped_vote.get(vote.id, 0)

    @api.depends('vote_ids.vote')
    def _compute_vote_count(self):
        read_group_res = self.env['forum.post.vote']._read_group([('post_id', 'in', self._ids)], ['post_id', 'vote'], ['__count'])
        result = dict.fromkeys(self._ids, 0)
        for post, vote, count in read_group_res:
            result[post.id] += count * int(vote)
        for post in self:
            post.vote_count = result[post.id]

    @api.depends_context('uid')
    def _compute_user_favourite(self):
        for post in self:
            post.user_favourite = post.env.uid in post.favourite_ids.ids

    @api.depends('favourite_ids')
    def _compute_favorite_count(self):
        for post in self:
            post.favourite_count = len(post.favourite_ids)

    @api.depends('create_uid', 'parent_id')
    def _compute_self_reply(self):
        for post in self:
            post.self_reply = post.parent_id.create_uid == post.create_uid

    @api.depends('child_ids')
    def _compute_child_count(self):
        for post in self:
            post.child_count = len(post.child_ids)

    @api.depends_context('uid')
    def _compute_uid_has_answered(self):
        for post in self:
            post.uid_has_answered = post.env.uid in post.child_ids.create_uid.ids

    @api.depends('child_ids.is_correct')
    def _compute_has_validated_answer(self):
        for post in self:
            post.has_validated_answer = any(answer.is_correct for answer in post.child_ids)

    @api.depends_context('uid')
    def _compute_post_karma_rights(self):
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
            post.can_display_biography = is_admin or (post_sudo.create_uid.karma >= post.forum_id.karma_user_bio and post_sudo.create_uid.website_published)
            post.can_post = is_admin or user.karma >= post.forum_id.karma_post
            post.can_flag = is_admin or user.karma >= post.forum_id.karma_flag
            post.can_moderate = is_admin or user.karma >= post.forum_id.karma_moderate
            post.can_use_full_editor = is_admin or user.karma >= post.forum_id.karma_editor

    def _search_can_view(self, operator, value):
        if operator != 'in':
            return NotImplemented

        user = self.env.user
        # Won't impact sitemap, search() in converter is forced as public user
        if self.env.is_admin():
            return [(1, '=', 1)]

        sql = SQL("""(
            SELECT p.id
            FROM forum_post p
                   LEFT JOIN res_users u ON p.create_uid = u.id
                   LEFT JOIN forum_forum f ON p.forum_id = f.id
            WHERE
                (p.create_uid = %(user_id)s and f.karma_close_own <= %(karma)s)
                or (p.create_uid != %(user_id)s and f.karma_close_all <= %(karma)s)
                or (
                    u.karma > 0
                    and (p.active or p.create_uid = %(user_id)s)
                )
        )""", user_id=user.id, karma=user.karma)
        return [('id', 'in', sql)]

    # EXTENDS WEBSITE.SEO.METADATA

    def _default_website_meta(self):
        res = super()._default_website_meta()
        res['default_opengraph']['og:title'] = res['default_twitter']['twitter:title'] = self.name
        res['default_opengraph']['og:description'] = res['default_twitter']['twitter:description'] = self.plain_content
        res['default_opengraph']['og:image'] = res['default_twitter']['twitter:image'] = self.env['website'].image_url(self.create_uid, 'image_1024')
        res['default_twitter']['twitter:card'] = 'summary'
        res['default_meta_description'] = self.plain_content
        return res

    # ----------------------------------------------------------------------
    # CRUD
    # ----------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        defaults_to_check = self.default_get(['content', 'forum_id'])
        for vals in vals_list:
            content = vals.get('content', defaults_to_check.get('content'))
            if content:
                forum_id = vals.get('forum_id', defaults_to_check.get('forum_id'))
                vals['content'] = self._update_content(content, forum_id)

        posts = super(ForumPost, self.with_context(mail_create_nolog=True)).create(vals_list)

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
                post.create_uid.sudo()._add_karma(post.forum_id.karma_gen_question_new, post, _('Ask a new question'))
        posts.sudo()._notify_state_update()
        return posts

    def unlink(self):
        # if unlinking an answer with accepted answer: remove provided karma
        for post in self:
            if post.is_correct:
                post.create_uid.sudo()._add_karma(post.forum_id.karma_gen_answer_accepted * -1, post, _('The accepted answer is deleted'))
                self.env.user.sudo()._add_karma(post.forum_id.karma_gen_answer_accepted * -1, post, _('Delete the accepted answer'))
        return super().unlink()

    def write(self, vals):
        trusted_keys = ['active', 'is_correct', 'tag_ids']  # fields where security is checked manually
        if 'forum_id' in vals:
            forum = self.env['forum.forum'].browse(vals['forum_id'])
            forum.check_access('write')
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
                if vals['is_correct'] != post.is_correct and post.create_uid.id != self.env.uid:
                    post.create_uid.sudo()._add_karma(post.forum_id.karma_gen_answer_accepted * mult, post,
                                                      _('User answer accepted') if mult > 0 else _('Accepted answer removed'))
                    self.env.user.sudo()._add_karma(post.forum_id.karma_gen_answer_accept * mult, post,
                                                    _('Validate an answer') if mult > 0 else _('Remove validated answer'))
            if tag_ids:
                if set(post.tag_ids.ids) != tag_ids and self.env.user.karma < post.forum_id.karma_edit_retag:
                    raise AccessError(_('%d karma required to retag.', post.forum_id.karma_edit_retag))
            if any(key not in trusted_keys for key in vals) and not post.can_edit:
                raise AccessError(_('%d karma required to edit a post.', post.karma_edit))

        res = super().write(vals)

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

    def _get_access_action(self, access_uid=None, force_website=False):
        """ Instead of the classic form view, redirect to the post on the website directly """
        self.ensure_one()
        if not force_website and not self.state == 'active':
            return super()._get_access_action(access_uid=access_uid, force_website=force_website)
        return {
            'type': 'ir.actions.act_url',
            'url': '/forum/%s/%s' % (self.forum_id.id, self.id),
            'target': 'self',
            'target_type': 'public',
            'res_id': self.id,
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_if_enough_karma(self):
        for post in self:
            if not post.can_unlink:
                raise AccessError(_('%d karma required to unlink a post.', post.karma_unlink))

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

    # ----------------------------------------------------------------------
    # BUSINESS
    # ----------------------------------------------------------------------

    def _notify_state_update(self):
        for post in self:
            tag_partners = post.tag_ids.sudo().mapped('message_partner_ids')

            if post.state == 'active' and post.parent_id:
                post.parent_id.message_post_with_source(
                    'website_forum.forum_post_template_new_answer',
                    subject=_('Re: %s', post.parent_id.name),
                    partner_ids=tag_partners.ids,
                    subtype_xmlid='website_forum.mt_answer_new',
                )
            elif post.state == 'active' and not post.parent_id:
                post.message_post_with_source(
                    'website_forum.forum_post_template_new_question',
                    subject=post.name,
                    partner_ids=tag_partners.ids,
                    subtype_xmlid='website_forum.mt_question_new',
                )
            elif post.state == 'pending' and not post.parent_id:
                # TDE FIXME: in master, you should probably use a subtype;
                # however here we remove subtype but set partner_ids
                partners = post.sudo().message_partner_ids | tag_partners
                partners = partners.filtered(lambda partner: partner.user_ids and any(user.karma >= post.forum_id.karma_moderate for user in partner.user_ids))

                post.message_post_with_source(
                    'website_forum.forum_post_template_validation',
                    subject=post.name,
                    partner_ids=partners.ids,
                    subtype_xmlid='mail.mt_note',
                )
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
                post.create_uid.sudo()._add_karma(karma * -1, post, _('Reopen a banned question'))

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
                message = (
                    _('Post is closed and marked as spam')
                    if reason_id == reason_spam else
                    _('Post is closed and marked as offensive content')
                )
                post.create_uid.sudo()._add_karma(karma, post, message)

        self.write({
            'state': 'close',
            'closed_uid': self.env.uid,
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
                post.create_uid.sudo()._add_karma(
                    post.forum_id.karma_gen_question_new,
                    post,
                    _('Ask a question'),
                )
            post.write({
                'state': 'active',
                'active': True,
                'moderator_id': self.env.user.id,
            })
            post.sudo()._notify_state_update()
        return True

    def _refuse(self):
        for post in self:
            if not post.can_moderate:
                raise AccessError(_('%d karma required to refuse a post.', post.forum_id.karma_moderate))
            post.moderator_id = self.env.user
        return True

    def _flag(self):
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

    def _mark_as_offensive(self, reason_id):
        for post in self:
            if not post.can_moderate:
                raise AccessError(_('%d karma required to mark a post as offensive.', post.forum_id.karma_moderate))
            # remove some karma
            _logger.info('Downvoting user <%s> for posting spam/offensive contents', post.create_uid)
            post.create_uid.sudo()._add_karma(post.forum_id.karma_gen_answer_flagged, post, _('Downvote for posting offensive contents'))
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
        return spams._mark_as_offensive(reason_id)

    def vote(self, upvote=True):
        self.ensure_one()
        Vote = self.env['forum.post.vote']
        existing_vote = Vote.search([('post_id', '=', self.id), ('user_id', '=', self.env.uid)])
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
        new_message = question.with_user(self_sudo.create_uid.id).with_context(mail_post_autofollow_author_skip=True).sudo().message_post(**values).sudo(False)

        # unlink the original answer, using SUPERUSER_ID to avoid karma issues
        self.sudo().unlink()

        return new_message

    @api.model
    def convert_comment_to_answer(self, message_id):
        """ Tool to convert a comment (mail.message) into an answer (forum.post).
        The original comment is unlinked and a new answer from the comment's author
        is created. Nothing is done if the comment's author already answered the
        question. """
        comment_sudo = self.env['mail.message'].sudo().browse(message_id)
        post = self.browse(comment_sudo.res_id)
        if not comment_sudo.author_id or not comment_sudo.author_id.user_ids:  # only comment posted by users can be converted
            return False

        # karma-based action check: must check the message's author to know if own / all
        is_author = comment_sudo.author_id.id == self.env.user.partner_id.id
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
        post_create_uid = comment_sudo.author_id.user_ids[0]
        if any(answer.create_uid.id == post_create_uid.id for answer in question.child_ids):
            return False

        # create the new post
        post_values = {
            'forum_id': question.forum_id.id,
            'content': comment_sudo.body,
            'parent_id': question.id,
            'name': _('Re: %s', question.name or ''),
        }
        # done with the author user to have create_uid correctly set
        new_post = self.with_user(post_create_uid).sudo().create(post_values).sudo(False)

        # delete comment
        comment_sudo.unlink()

        return new_post

    def unlink_comment(self, message_id):
        comment_sudo = self.env['mail.message'].sudo().browse(message_id)
        if comment_sudo.model != 'forum.post':
            return [False] * len(self)

        user_karma = self.env.user.karma
        result = []
        for post in self:
            if comment_sudo.res_id != post.id:
                result.append(False)
                continue
            # karma-based action check: must check the message's author to know if own or all
            karma_required = (
                post.forum_id.karma_comment_unlink_own
                if comment_sudo.author_id.id == self.env.user.partner_id.id
                else post.forum_id.karma_comment_unlink_all
            )
            if user_karma < karma_required:
                raise AccessError(_('%d karma required to delete a comment.', karma_required))
            result.append(comment_sudo.unlink())
        return result

    def _set_viewed(self):
        self.ensure_one()
        return sql.increment_fields_skiplock(self, 'views')

    def _update_last_activity(self):
        self.ensure_one()
        return self.sudo().write({'last_activity_date': fields.Datetime.now()})

    # ----------------------------------------------------------------------
    # MESSAGING
    # ----------------------------------------------------------------------

    def _mail_get_operation_for_mail_message_operation(self, message_operation):
        if message_operation in ('write', 'unlink'):
            filtered_self = self.filtered(lambda post: post.can_edit)
        else:
            filtered_self = self
        return super(ForumPost, filtered_self)._mail_get_operation_for_mail_message_operation(message_operation)

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=False):
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        self.ensure_one()
        if self.state == 'active':
            for _group_name, _group_method, group_data in groups:
                group_data['has_button_access'] = True

        return groups

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
            if not kwargs.get('force_record_name') and self.parent_id.name:
                kwargs['force_record_name'] = self.parent_id.name
        return super().message_post(message_type=message_type, **kwargs)

    def _notify_thread_by_inbox(self, message, recipients_data, msg_vals=False, **kwargs):
        # Override to avoid keeping all notified recipients of a comment.
        # We avoid tracking needaction on post comments. Only emails should be
        # ufficient.
        msg_vals = msg_vals or {}
        if msg_vals.get('message_type', message.message_type) == 'comment':
            return
        return super()._notify_thread_by_inbox(message, recipients_data, msg_vals=msg_vals, **kwargs)

    # ----------------------------------------------------------------------
    # WEBSITE
    # ----------------------------------------------------------------------

    def _get_microdata(self):
        """
        Generate structured data (microdata) for the post.

        Returns:
            str or None: Microdata in JSON format representing the post, or None
            if not applicable.
        """
        self.ensure_one()
        # Return if it's not a question.
        if self.parent_id:
            return None
        correct_posts = self.child_ids.filtered(lambda post: post.is_correct)
        suggested_posts = self.child_ids.filtered(lambda post: not post.is_correct)[:5]
        # A QAPage schema must have one accepted answer or at least one suggested answer
        if not suggested_posts and not correct_posts:
            return None

        structured_data = {
            "@context": "https://schema.org",
            "@type": "QAPage",
            "mainEntity": self._get_structured_data(post_type="question"),
        }
        if correct_posts:
            structured_data["mainEntity"]["acceptedAnswer"] = correct_posts[0]._get_structured_data()
        if suggested_posts:
            structured_data["mainEntity"]["suggestedAnswer"] = [
                suggested_post._get_structured_data()
                for suggested_post in suggested_posts
            ]
        return json_safe.dumps(structured_data, indent=2)

    def _get_structured_data(self, post_type="answer"):
        """
        Generate structured data (microdata) for an answer or a question.

        Returns:
            dict: microdata.
        """
        res = {
            "upvoteCount": self.vote_count,
            "datePublished": self.create_date.isoformat() + 'Z',
            "url": self.env['ir.http']._url_for(self.website_url),
            "author": {
                "@type": "Person",
                "name": self.create_uid.sudo().name,
            },
        }
        if post_type == "answer":
            res["@type"] = "Answer"
            res["text"] = self.plain_content
        else:
            res["@type"] = "Question"
            res["name"] = self.name
            res["text"] = self.plain_content or self.name
            res["answerCount"] = self.child_count
        if self.create_uid.sudo().website_published:
            res["author"]["url"] = self.env['ir.http']._url_for(f"/profile/user/{ self.create_uid.sudo().id }")
        return res

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
        domain &= Domain('state', '=', 'active') & Domain('can_view', '=', True)
        include_answers = options.get('include_answers', False)
        if not include_answers:
            domain &= Domain('parent_id', '=', False)
        forum = options.get('forum')
        if forum:
            domain &= Domain('forum_id', '=', self.env['ir.http']._unslug(forum)[1])
        tags = options.get('tag')
        if tags:
            domain &= Domain('tag_ids', 'in', [self.env['ir.http']._unslug(tag)[1] for tag in tags.split(',')])
        filters = options.get('filters')
        if filters == 'unanswered':
            domain &= Domain('child_ids', '=', False)
        elif filters == 'solved':
            domain &= Domain('has_validated_answer', '=', True)
        elif filters == 'unsolved':
            domain &= Domain('has_validated_answer', '=', False)
        user = self.env.user
        my = options.get('my')
        create_uid = user.id if my == 'mine' else options.get('create_uid')
        if create_uid:
            domain &= Domain('create_uid', '=', create_uid)
        if my == 'followed':
            domain &= Domain('message_partner_ids', '=', user.partner_id.id)
        elif my == 'tagged':
            domain &= Domain('tag_ids.message_partner_ids', '=', user.partner_id.id)
        elif my == 'favourites':
            domain &= Domain('favourite_ids', '=', user.id)
        elif my == 'upvoted':
            domain &= Domain('vote_ids.user_id', '=', user.id)

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

    def _get_related_posts(self, limit=5):
        """Return at most a list of {limit} posts related to the main post, based on tag
        Jaccard similarity. It computes similarity of sets based on ratio of sets
        intersection divided by sets union (and thus varies from 0 to 1, 1 being
        identical sets)."""

        self.ensure_one()

        if not self.tag_ids:
            return self.env['forum.post']

        self.env.cr.execute(SQL("""
            SELECT forum_post.id,
              -- Jaccard similarity
                   (COUNT(DISTINCT intersection_tag_rel.forum_tag_id))::DECIMAL
                   / COUNT(DISTINCT union_tag_rel.forum_tag_id)::DECIMAL AS similarity
              FROM forum_post
              -- common tags (intersection)
              JOIN forum_tag_rel AS intersection_tag_rel
                ON intersection_tag_rel.forum_post_id = forum_post.id
               AND intersection_tag_rel.forum_tag_id = ANY(%(tag_ids)s)
              -- union tags
        RIGHT JOIN forum_tag_rel AS union_tag_rel
                ON union_tag_rel.forum_post_id = forum_post.id
                OR union_tag_rel.forum_post_id = %(current_post_id)s
             WHERE id != %(current_post_id)s
          GROUP BY forum_post.id
          ORDER BY similarity DESC,
                   forum_post.last_activity_date DESC
             LIMIT %(limit)s
        """, current_post_id=self.id, tag_ids=self.tag_ids.ids, limit=limit))

        result = self.env.cr.dictfetchall()
        return self.browse([r["id"] for r in result])
