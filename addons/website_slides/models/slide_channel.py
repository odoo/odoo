# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.exceptions import AccessError
from odoo.osv import expression


class ChannelUsersRelation(models.Model):
    _name = 'slide.channel.partner'
    _description = 'Channel / Partners (Members)'
    _table = 'slide_channel_partner'

    channel_id = fields.Many2one('slide.channel', index=True, required=True, ondelete='cascade')
    completed = fields.Boolean('Is Completed', help='Channel validated, even if slides / lessons are added once done.')
    completion = fields.Integer('% Completed Slides')
    completed_slides_count = fields.Integer('# Completed Slides')
    partner_id = fields.Many2one('res.partner', index=True, required=True, ondelete='cascade')
    partner_email = fields.Char(related='partner_id.email', readonly=True)

    def _recompute_completion(self):
        read_group_res = self.env['slide.slide.partner'].sudo().read_group(
            ['&', '&', ('channel_id', 'in', self.mapped('channel_id').ids),
             ('partner_id', 'in', self.mapped('partner_id').ids),
             ('completed', '=', True),
             ('slide_id.is_published', '=', True),
             ('slide_id.active', '=', True)],
            ['channel_id', 'partner_id'],
            groupby=['channel_id', 'partner_id'], lazy=False)
        mapped_data = dict()
        for item in read_group_res:
            mapped_data.setdefault(item['channel_id'][0], dict())
            mapped_data[item['channel_id'][0]][item['partner_id'][0]] = item['__count']

        partner_karma = dict.fromkeys(self.mapped('partner_id').ids, 0)
        for record in self:
            record.completed_slides_count = mapped_data.get(record.channel_id.id, dict()).get(record.partner_id.id, 0)
            record.completion = 100.0 if record.completed else round(100.0 * record.completed_slides_count / (record.channel_id.total_slides or 1))
            if not record.completed and record.channel_id.active and record.completed_slides_count >= record.channel_id.total_slides:
                record.completed = True
                partner_karma[record.partner_id.id] += record.channel_id.karma_gen_channel_finish

        partner_karma = {partner_id: karma_to_add
                         for partner_id, karma_to_add in partner_karma.items() if karma_to_add > 0}

        if partner_karma:
            users = self.env['res.users'].sudo().search([('partner_id', 'in', list(partner_karma.keys()))])
            for user in users:
                users.add_karma(partner_karma[user.partner_id.id])

    def unlink(self):
        """
        Override unlink method :
        Remove attendee from a channel, then also remove slide.slide.partner related to.
        """
        removed_slide_partner_domain = []
        for channel_partner in self:
            # find all slide link to the channel and the partner
            removed_slide_partner_domain = expression.OR([
                removed_slide_partner_domain,
                [('partner_id', '=', channel_partner.partner_id.id),
                 ('slide_id', 'in', channel_partner.channel_id.slide_ids.ids)]
            ])
        if removed_slide_partner_domain:
            self.env['slide.slide.partner'].search(removed_slide_partner_domain).unlink()
        return super(ChannelUsersRelation, self).unlink()


class Channel(models.Model):
    """ A channel is a container of slides. """
    _name = 'slide.channel'
    _description = 'Course'
    _inherit = [
        'mail.thread', 'rating.mixin',
        'mail.activity.mixin',
        'image.mixin',
        'website.seo.metadata', 'website.published.multi.mixin']
    _order = 'sequence, id'

    def _default_access_token(self):
        return str(uuid.uuid4())

    def _get_default_enroll_msg(self):
        return _('Contact Responsible')

    # description
    name = fields.Char('Name', translate=True, required=True)
    active = fields.Boolean(default=True, tracking=100)
    description = fields.Text('Description', translate=True, help="The description that is displayed on top of the course page, just below the title")
    description_short = fields.Text('Short Description', translate=True, help="The description that is displayed on the course card")
    description_html = fields.Html('Detailed Description', translate=tools.html_translate, sanitize_attributes=False, sanitize_form=False)
    channel_type = fields.Selection([
        ('training', 'Training'), ('documentation', 'Documentation')],
        string="Course type", default="training", required=True)
    sequence = fields.Integer(default=10, help='Display order')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.uid)
    color = fields.Integer('Color Index', default=0, help='Used to decorate kanban view')
    tag_ids = fields.Many2many(
        'slide.channel.tag', 'slide_channel_tag_rel', 'channel_id', 'tag_id',
        string='Tags', help='Used to categorize and filter displayed channels/courses')
    # slides: promote, statistics
    slide_ids = fields.One2many('slide.slide', 'channel_id', string="Slides and categories", context={'active_test': False})
    slide_content_ids = fields.One2many('slide.slide', string='Slides', compute="_compute_category_and_slide_ids")
    slide_category_ids = fields.One2many('slide.slide', string='Categories', compute="_compute_category_and_slide_ids")
    slide_last_update = fields.Date('Last Update', compute='_compute_slide_last_update', store=True)
    slide_partner_ids = fields.One2many(
        'slide.slide.partner', 'channel_id', string="Slide User Data",
        copy=False, groups='website_slides.group_website_slides_officer')
    promote_strategy = fields.Selection([
        ('latest', 'Latest Published'),
        ('most_voted', 'Most Voted'),
        ('most_viewed', 'Most Viewed'),
        ('specific', 'Specific'),
        ('none', 'None')],
        string="Promoted Content", default='latest', required=False,
        help='Depending the promote strategy, a slide will appear on the top of the course\'s page :\n'
             ' * Latest Published : the slide created last.\n'
             ' * Most Voted : the slide which has to most votes.\n'
             ' * Most Viewed ; the slide which has been viewed the most.\n'
             ' * Specific : You choose the slide to appear.\n'
             ' * None : No slides will be shown.\n')
    promoted_slide_id = fields.Many2one('slide.slide', string='Promoted Slide')
    access_token = fields.Char("Security Token", copy=False, default=_default_access_token)
    nbr_presentation = fields.Integer('Presentations', compute='_compute_slides_statistics', store=True)
    nbr_document = fields.Integer('Documents', compute='_compute_slides_statistics', store=True)
    nbr_video = fields.Integer('Videos', compute='_compute_slides_statistics', store=True)
    nbr_infographic = fields.Integer('Infographics', compute='_compute_slides_statistics', store=True)
    nbr_webpage = fields.Integer("Webpages", compute='_compute_slides_statistics', store=True)
    nbr_quiz = fields.Integer("Number of Quizs", compute='_compute_slides_statistics', store=True)
    total_slides = fields.Integer('Content', compute='_compute_slides_statistics', store=True)
    total_views = fields.Integer('Visits', compute='_compute_slides_statistics', store=True)
    total_votes = fields.Integer('Votes', compute='_compute_slides_statistics', store=True)
    total_time = fields.Float('Duration', compute='_compute_slides_statistics', digits=(10, 2), store=True)
    rating_avg_stars = fields.Float("Rating Average (Stars)", compute='_compute_rating_stats', digits=(16, 1), compute_sudo=True)
    # configuration
    allow_comment = fields.Boolean(
        "Allow rating on Course", default=True,
        help="If checked it allows members to either:\n"
             " * like content and post comments on documentation course;\n"
             " * post comment and review on training course;")
    publish_template_id = fields.Many2one(
        'mail.template', string='New Content Email',
        help="Email template to send slide publication through email",
        default=lambda self: self.env['ir.model.data'].xmlid_to_res_id('website_slides.slide_template_published'))
    share_template_id = fields.Many2one(
        'mail.template', string='Share Template',
        help="Email template used when sharing a slide",
        default=lambda self: self.env['ir.model.data'].xmlid_to_res_id('website_slides.slide_template_shared'))
    enroll = fields.Selection([
        ('public', 'Public'), ('invite', 'On Invitation')],
        default='public', string='Enroll Policy', required=True,
        help='Condition to enroll: everyone, on invite, on payment (sale bridge).')
    enroll_msg = fields.Html(
        'Enroll Message', help="Message explaining the enroll process",
        default=_get_default_enroll_msg, translate=tools.html_translate, sanitize_attributes=False)
    enroll_group_ids = fields.Many2many('res.groups', string='Auto Enroll Groups', help="Members of those groups are automatically added as members of the channel.")
    visibility = fields.Selection([
        ('public', 'Public'), ('members', 'Members Only')],
        default='public', string='Visibility', required=True,
        help='Applied directly as ACLs. Allow to hide channels and their content for non members.')
    partner_ids = fields.Many2many(
        'res.partner', 'slide_channel_partner', 'channel_id', 'partner_id',
        string='Members', help="All members of the channel.", context={'active_test': False}, copy=False, depends=['channel_partner_ids'])
    members_count = fields.Integer('Attendees count', compute='_compute_members_count')
    members_done_count = fields.Integer('Attendees Done Count', compute='_compute_members_done_count')
    has_requested_access = fields.Boolean(string='Access Requested', compute='_compute_has_requested_access', compute_sudo=False)
    is_member = fields.Boolean(string='Is Member', compute='_compute_is_member', compute_sudo=False)
    channel_partner_ids = fields.One2many('slide.channel.partner', 'channel_id', string='Members Information', groups='website_slides.group_website_slides_officer', depends=['partner_ids'])
    upload_group_ids = fields.Many2many(
        'res.groups', 'rel_upload_groups', 'channel_id', 'group_id', string='Upload Groups',
        help="Group of users allowed to publish contents on a documentation course.")
    # not stored access fields, depending on each user
    completed = fields.Boolean('Done', compute='_compute_user_statistics', compute_sudo=False)
    completion = fields.Integer('Completion', compute='_compute_user_statistics', compute_sudo=False)
    can_upload = fields.Boolean('Can Upload', compute='_compute_can_upload', compute_sudo=False)
    partner_has_new_content = fields.Boolean(compute='_compute_partner_has_new_content', compute_sudo=False)
    # karma generation
    karma_gen_slide_vote = fields.Integer(string='Lesson voted', default=1)
    karma_gen_channel_rank = fields.Integer(string='Course ranked', default=5)
    karma_gen_channel_finish = fields.Integer(string='Course finished', default=10)
    # Karma based actions
    karma_review = fields.Integer('Add Review', default=10, help="Karma needed to add a review on the course")
    karma_slide_comment = fields.Integer('Add Comment', default=3, help="Karma needed to add a comment on a slide of this course")
    karma_slide_vote = fields.Integer('Vote', default=3, help="Karma needed to like/dislike a slide of this course.")
    can_review = fields.Boolean('Can Review', compute='_compute_action_rights', compute_sudo=False)
    can_comment = fields.Boolean('Can Comment', compute='_compute_action_rights', compute_sudo=False)
    can_vote = fields.Boolean('Can Vote', compute='_compute_action_rights', compute_sudo=False)

    @api.depends('slide_ids.is_published')
    def _compute_slide_last_update(self):
        for record in self:
            record.slide_last_update = fields.Date.today()

    @api.depends('channel_partner_ids.channel_id')
    def _compute_members_count(self):
        read_group_res = self.env['slide.channel.partner'].sudo().read_group([('channel_id', 'in', self.ids)], ['channel_id'], 'channel_id')
        data = dict((res['channel_id'][0], res['channel_id_count']) for res in read_group_res)
        for channel in self:
            channel.members_count = data.get(channel.id, 0)

    @api.depends('channel_partner_ids.channel_id', 'channel_partner_ids.completed')
    def _compute_members_done_count(self):
        read_group_res = self.env['slide.channel.partner'].sudo().read_group(['&', ('channel_id', 'in', self.ids), ('completed', '=', True)], ['channel_id'], 'channel_id')
        data = dict((res['channel_id'][0], res['channel_id_count']) for res in read_group_res)
        for channel in self:
            channel.members_done_count = data.get(channel.id, 0)

    @api.depends('activity_ids.request_partner_id')
    @api.depends_context('uid')
    @api.model
    def _compute_has_requested_access(self):
        requested_cids = self.sudo().activity_search(
            ['website_slides.mail_activity_data_access_request'],
            additional_domain=[('request_partner_id', '=', self.env.user.partner_id.id)]
        ).mapped('res_id')
        for channel in self:
            channel.has_requested_access = channel.id in requested_cids

    @api.depends('channel_partner_ids.partner_id')
    @api.depends_context('uid')
    @api.model
    def _compute_is_member(self):
        channel_partners = self.env['slide.channel.partner'].sudo().search([
            ('channel_id', 'in', self.ids),
        ])
        result = dict()
        for cp in channel_partners:
            result.setdefault(cp.channel_id.id, []).append(cp.partner_id.id)
        for channel in self:
            channel.is_member = channel.is_member = self.env.user.partner_id.id in result.get(channel.id, [])

    @api.depends('slide_ids.is_category')
    def _compute_category_and_slide_ids(self):
        for channel in self:
            channel.slide_category_ids = channel.slide_ids.filtered(lambda slide: slide.is_category)
            channel.slide_content_ids = channel.slide_ids - channel.slide_category_ids

    @api.depends('slide_ids.slide_type', 'slide_ids.is_published', 'slide_ids.completion_time',
                 'slide_ids.likes', 'slide_ids.dislikes', 'slide_ids.total_views', 'slide_ids.is_category', 'slide_ids.active')
    def _compute_slides_statistics(self):
        default_vals = dict(total_views=0, total_votes=0, total_time=0, total_slides=0)
        keys = ['nbr_%s' % slide_type for slide_type in self.env['slide.slide']._fields['slide_type'].get_values(self.env)]
        default_vals.update(dict((key, 0) for key in keys))

        result = dict((cid, dict(default_vals)) for cid in self.ids)
        read_group_res = self.env['slide.slide'].read_group(
            [('active', '=', True), ('is_published', '=', True), ('channel_id', 'in', self.ids), ('is_category', '=', False)],
            ['channel_id', 'slide_type', 'likes', 'dislikes', 'total_views', 'completion_time'],
            groupby=['channel_id', 'slide_type'],
            lazy=False)
        for res_group in read_group_res:
            cid = res_group['channel_id'][0]
            result[cid]['total_views'] += res_group.get('total_views', 0)
            result[cid]['total_votes'] += res_group.get('likes', 0)
            result[cid]['total_votes'] -= res_group.get('dislikes', 0)
            result[cid]['total_time'] += res_group.get('completion_time', 0)

        type_stats = self._compute_slides_statistics_type(read_group_res)
        for cid, cdata in type_stats.items():
            result[cid].update(cdata)

        for record in self:
            record.update(result.get(record.id, default_vals))

    def _compute_slides_statistics_type(self, read_group_res):
        """ Compute statistics based on all existing slide types """
        slide_types = self.env['slide.slide']._fields['slide_type'].get_values(self.env)
        keys = ['nbr_%s' % slide_type for slide_type in slide_types]
        result = dict((cid, dict((key, 0) for key in keys + ['total_slides'])) for cid in self.ids)
        for res_group in read_group_res:
            cid = res_group['channel_id'][0]
            slide_type = res_group.get('slide_type')
            if slide_type:
                slide_type_count = res_group.get('__count', 0)
                result[cid]['nbr_%s' % slide_type] = slide_type_count
                result[cid]['total_slides'] += slide_type_count
        return result

    def _compute_rating_stats(self):
        super(Channel, self)._compute_rating_stats()
        for record in self:
            record.rating_avg_stars = record.rating_avg

    @api.depends('slide_partner_ids', 'total_slides')
    @api.depends_context('uid')
    def _compute_user_statistics(self):
        current_user_info = self.env['slide.channel.partner'].sudo().search(
            [('channel_id', 'in', self.ids), ('partner_id', '=', self.env.user.partner_id.id)]
        )
        mapped_data = dict((info.channel_id.id, (info.completed, info.completed_slides_count)) for info in current_user_info)
        for record in self:
            completed, completed_slides_count = mapped_data.get(record.id, (False, 0))
            record.completed = completed
            record.completion = 100.0 if completed else round(100.0 * completed_slides_count / (record.total_slides or 1))

    @api.depends('upload_group_ids', 'user_id')
    @api.depends_context('uid')
    def _compute_can_upload(self):
        for record in self:
            if record.user_id == self.env.user or self.env.is_superuser():
                record.can_upload = True
            elif record.upload_group_ids:
                record.can_upload = bool(record.upload_group_ids & self.env.user.groups_id)
            else:
                record.can_upload = self.env.user.has_group('website_slides.group_website_slides_manager')

    @api.depends('channel_type', 'user_id', 'can_upload')
    @api.depends_context('uid')
    def _compute_can_publish(self):
        """ For channels of type 'training', only the responsible (see user_id field) can publish slides.
        The 'sudo' user needs to be handled because he's the one used for uploads done on the front-end when the
        logged in user is not publisher but fulfills the upload_group_ids condition. """
        for record in self:
            if not record.can_upload:
                record.can_publish = False
            elif record.user_id == self.env.user or self.env.is_superuser():
                record.can_publish = True
            else:
                record.can_publish = self.env.user.has_group('website_slides.group_website_slides_manager')

    @api.model
    def _get_can_publish_error_message(self):
        return _("Publishing is restricted to the responsible of training courses or members of the publisher group for documentation courses")

    @api.depends('slide_partner_ids')
    @api.depends_context('uid')
    def _compute_partner_has_new_content(self):
        new_published_slides = self.env['slide.slide'].sudo().search([
            ('is_published', '=', True),
            ('date_published', '>', fields.Datetime.now() - relativedelta(days=7)),
            ('channel_id', 'in', self.ids),
            ('is_category', '=', False)
        ])
        slide_partner_completed = self.env['slide.slide.partner'].sudo().search([
            ('channel_id', 'in', self.ids),
            ('partner_id', '=', self.env.user.partner_id.id),
            ('slide_id', 'in', new_published_slides.ids),
            ('completed', '=', True)
        ]).mapped('slide_id')
        for channel in self:
            new_slides = new_published_slides.filtered(lambda slide: slide.channel_id == channel)
            channel.partner_has_new_content = any(slide not in slide_partner_completed for slide in new_slides)

    @api.depends('name', 'website_id.domain')
    def _compute_website_url(self):
        super(Channel, self)._compute_website_url()
        for channel in self:
            if channel.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                base_url = channel.get_base_url()
                channel.website_url = '%s/slides/%s' % (base_url, slug(channel))

    @api.depends('can_publish', 'is_member', 'karma_review', 'karma_slide_comment', 'karma_slide_vote')
    @api.depends_context('uid')
    def _compute_action_rights(self):
        user_karma = self.env.user.karma
        for channel in self:
            if channel.can_publish:
                channel.can_vote = channel.can_comment = channel.can_review = True
            elif not channel.is_member:
                channel.can_vote = channel.can_comment = channel.can_review = False
            else:
                channel.can_review = user_karma >= channel.karma_review
                channel.can_comment = user_karma >= channel.karma_slide_comment
                channel.can_vote = user_karma >= channel.karma_slide_vote

    # ---------------------------------------------------------
    # ORM Overrides
    # ---------------------------------------------------------

    def _init_column(self, column_name):
        """ Initialize the value of the given column for existing rows.
            Overridden here because we need to generate different access tokens
            and by default _init_column calls the default method once and applies
            it for every record.
        """
        if column_name != 'access_token':
            super(Channel, self)._init_column(column_name)
        else:
            query = """
                UPDATE %(table_name)s
                SET access_token = md5(md5(random()::varchar || id::varchar) || clock_timestamp()::varchar)::uuid::varchar
                WHERE access_token IS NULL
            """ % {'table_name': self._table}
            self.env.cr.execute(query)

    @api.model
    def create(self, vals):
        # Ensure creator is member of its channel it is easier for him to manage it (unless it is odoobot)
        if not vals.get('channel_partner_ids') and not self.env.is_superuser():
            vals['channel_partner_ids'] = [(0, 0, {
                'partner_id': self.env.user.partner_id.id
            })]
        if vals.get('description') and not vals.get('description_short'):
            vals['description_short'] = vals['description']
        channel = super(Channel, self.with_context(mail_create_nosubscribe=True)).create(vals)

        if channel.user_id:
            channel._action_add_members(channel.user_id.partner_id)
        if 'enroll_group_ids' in vals:
            channel._add_groups_members()

        return channel

    def write(self, vals):
        # If description_short wasn't manually modified, there is an implicit link between this field and description.
        if vals.get('description') and not vals.get('description_short') and self.description == self.description_short:
            vals['description_short'] = vals.get('description')

        res = super(Channel, self).write(vals)

        if vals.get('user_id'):
            self._action_add_members(self.env['res.users'].sudo().browse(vals['user_id']).partner_id)
            self.activity_reschedule(['website_slides.mail_activity_data_access_request'], new_user_id=vals.get('user_id'))
        if 'enroll_group_ids' in vals:
            self._add_groups_members()

        return res

    def toggle_active(self):
        """ Archiving/unarchiving a channel does it on its slides, too.
        1. When archiving
        We want to be archiving the channel FIRST.
        So that when slides are archived and the recompute is triggered,
        it does not try to mark the channel as "completed".
        That happens because it counts slide_done / slide_total, but slide_total
        will be 0 since all the slides for the course have been archived as well.

        2. When un-archiving
        We want to archive the channel LAST.
        So that when it recomputes stats for the channel and completion, it correctly
        counts the slides_total by counting slides that are already un-archived. """

        to_archive = self.filtered(lambda channel: channel.active)
        to_activate = self.filtered(lambda channel: not channel.active)
        if to_archive:
            super(Channel, to_archive).toggle_active()
            to_archive.is_published = False
            to_archive.mapped('slide_ids').action_archive()
        if to_activate:
            to_activate.with_context(active_test=False).mapped('slide_ids').action_unarchive()
            super(Channel, to_activate).toggle_active()

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *, parent_id=False, subtype_id=False, **kwargs):
        """ Temporary workaround to avoid spam. If someone replies on a channel
        through the 'Presentation Published' email, it should be considered as a
        note as we don't want all channel followers to be notified of this answer. """
        self.ensure_one()
        if kwargs.get('message_type') == 'comment' and not self.can_review:
            raise AccessError(_('Not enough karma to review'))
        if parent_id:
            parent_message = self.env['mail.message'].sudo().browse(parent_id)
            if parent_message.subtype_id and parent_message.subtype_id == self.env.ref('website_slides.mt_channel_slide_published'):
                subtype_id = self.env.ref('mail.mt_note').id
        return super(Channel, self).message_post(parent_id=parent_id, subtype_id=subtype_id, **kwargs)

    # ---------------------------------------------------------
    # Business / Actions
    # ---------------------------------------------------------

    def action_redirect_to_members(self, state=None):
        action = self.env["ir.actions.actions"]._for_xml_id("website_slides.slide_channel_partner_action")
        action['domain'] = [('channel_id', 'in', self.ids)]
        if len(self) == 1:
            action['display_name'] = _('Attendees of %s', self.name)
            action['context'] = {'active_test': False, 'default_channel_id': self.id}
        if state:
            action['domain'] += [('completed', '=', state == 'completed')]
        return action

    def action_redirect_to_running_members(self):
        return self.action_redirect_to_members('running')

    def action_redirect_to_done_members(self):
        return self.action_redirect_to_members('completed')

    def action_channel_invite(self):
        self.ensure_one()
        template = self.env.ref('website_slides.mail_template_slide_channel_invite', raise_if_not_found=False)

        local_context = dict(
            self.env.context,
            default_channel_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            notif_layout='website_slides.mail_notification_channel_invite',
        )
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'slide.channel.invite',
            'target': 'new',
            'context': local_context,
        }

    def action_add_member(self, **member_values):
        """ Adds the logged in user in the channel members.
        (see '_action_add_members' for more info)

        Returns True if added successfully, False otherwise."""
        return bool(self._action_add_members(self.env.user.partner_id, **member_values))

    def _action_add_members(self, target_partners, **member_values):
        """ Add the target_partner as a member of the channel (to its slide.channel.partner).
        This will make the content (slides) of the channel available to that partner.

        Returns the added 'slide.channel.partner's (! as sudo !)
        """
        to_join = self._filter_add_members(target_partners, **member_values)
        if to_join:
            existing = self.env['slide.channel.partner'].sudo().search([
                ('channel_id', 'in', self.ids),
                ('partner_id', 'in', target_partners.ids)
            ])
            existing_map = dict((cid, list()) for cid in self.ids)
            for item in existing:
                existing_map[item.channel_id.id].append(item.partner_id.id)

            to_create_values = [
                dict(channel_id=channel.id, partner_id=partner.id, **member_values)
                for channel in to_join
                for partner in target_partners if partner.id not in existing_map[channel.id]
            ]
            slide_partners_sudo = self.env['slide.channel.partner'].sudo().create(to_create_values)
            to_join.message_subscribe(partner_ids=target_partners.ids, subtype_ids=[self.env.ref('website_slides.mt_channel_slide_published').id])
            return slide_partners_sudo
        return self.env['slide.channel.partner'].sudo()

    def _filter_add_members(self, target_partners, **member_values):
        allowed = self.filtered(lambda channel: channel.enroll == 'public')
        on_invite = self.filtered(lambda channel: channel.enroll == 'invite')
        if on_invite:
            try:
                on_invite.check_access_rights('write')
                on_invite.check_access_rule('write')
            except:
                pass
            else:
                allowed |= on_invite
        return allowed

    def _add_groups_members(self):
        for channel in self:
            channel._action_add_members(channel.mapped('enroll_group_ids.users.partner_id'))

    def _get_earned_karma(self, partner_ids):
        """ Compute the number of karma earned by partners on a channel
        Warning: this count will not be accurate if the configuration has been
        modified after the completion of a course!
        """
        total_karma = defaultdict(int)

        slide_completed = self.env['slide.slide.partner'].sudo().search([
            ('partner_id', 'in', partner_ids),
            ('channel_id', 'in', self.ids),
            ('completed', '=', True),
            ('quiz_attempts_count', '>', 0)
        ])
        for partner_slide in slide_completed:
            slide = partner_slide.slide_id
            if not slide.question_ids:
                continue
            gains = [slide.quiz_first_attempt_reward,
                     slide.quiz_second_attempt_reward,
                     slide.quiz_third_attempt_reward,
                     slide.quiz_fourth_attempt_reward]
            attempts = min(partner_slide.quiz_attempts_count - 1, 3)
            total_karma[partner_slide.partner_id.id] += gains[attempts]

        channel_completed = self.env['slide.channel.partner'].sudo().search([
            ('partner_id', 'in', partner_ids),
            ('channel_id', 'in', self.ids),
            ('completed', '=', True)
        ])
        for partner_channel in channel_completed:
            channel = partner_channel.channel_id
            total_karma[partner_channel.partner_id.id] += channel.karma_gen_channel_finish

        return total_karma

    def _remove_membership(self, partner_ids):
        """ Unlink (!!!) the relationships between the passed partner_ids
        and the channels and their slides (done in the unlink of slide.channel.partner model).
        Remove earned karma when completed quizz """
        if not partner_ids:
            raise ValueError("Do not use this method with an empty partner_id recordset")

        earned_karma = self._get_earned_karma(partner_ids)
        users = self.env['res.users'].sudo().search([
            ('partner_id', 'in', list(earned_karma)),
        ])
        for user in users:
            if earned_karma[user.partner_id.id]:
                user.add_karma(-1 * earned_karma[user.partner_id.id])

        removed_channel_partner_domain = []
        for channel in self:
            removed_channel_partner_domain = expression.OR([
                removed_channel_partner_domain,
                [('partner_id', 'in', partner_ids),
                 ('channel_id', '=', channel.id)]
            ])
        self.message_unsubscribe(partner_ids=partner_ids)

        if removed_channel_partner_domain:
            self.env['slide.channel.partner'].sudo().search(removed_channel_partner_domain).unlink()

    def action_view_slides(self):
        action = self.env["ir.actions.actions"]._for_xml_id("website_slides.slide_slide_action")
        action['context'] = {
            'search_default_published': 1,
            'default_channel_id': self.id
        }
        action['domain'] = [('channel_id', "=", self.id), ('is_category', '=', False)]
        return action

    def action_view_ratings(self):
        action = self.env["ir.actions.actions"]._for_xml_id("website_slides.rating_rating_action_slide_channel")
        action['name'] = _('Rating of %s') % (self.name)
        action['domain'] = [('res_id', 'in', self.ids)]
        return action

    def action_request_access(self):
        """ Request access to the channel. Returns a dict with keys being either 'error'
        (specific error raised) or 'done' (request done or not). """
        if self.env.user.has_group('base.group_public'):
            return {'error': _('You have to sign in before')}
        if not self.is_published:
            return {'error': _('Course not published yet')}
        if self.is_member:
            return {'error': _('Already member')}
        if self.enroll == 'invite':
            activities = self.sudo()._action_request_access(self.env.user.partner_id)
            if activities:
                return {'done': True}
            return {'error': _('Already Requested')}
        return {'done': False}

    def action_grant_access(self, partner_id):
        partner = self.env['res.partner'].browse(partner_id).exists()
        if partner:
            if self._action_add_members(partner):
                self.activity_search(
                    ['website_slides.mail_activity_data_access_request'],
                    user_id=self.user_id.id, additional_domain=[('request_partner_id', '=', partner.id)]
                ).action_feedback(feedback=_('Access Granted'))

    def action_refuse_access(self, partner_id):
        partner = self.env['res.partner'].browse(partner_id).exists()
        if partner:
            self.activity_search(
                ['website_slides.mail_activity_data_access_request'],
                user_id=self.user_id.id, additional_domain=[('request_partner_id', '=', partner.id)]
            ).action_feedback(feedback=_('Access Refused'))

    # ---------------------------------------------------------
    # Mailing Mixin API
    # ---------------------------------------------------------

    def _rating_domain(self):
        """ Only take the published rating into account to compute avg and count """
        domain = super(Channel, self)._rating_domain()
        return expression.AND([domain, [('is_internal', '=', False)]])

    def _action_request_access(self, partner):
        activities = self.env['mail.activity']
        requested_cids = self.sudo().activity_search(
            ['website_slides.mail_activity_data_access_request'],
            additional_domain=[('request_partner_id', '=', partner.id)]
        ).mapped('res_id')
        for channel in self:
            if channel.id not in requested_cids:
                activities += channel.activity_schedule(
                    'website_slides.mail_activity_data_access_request',
                    note=_('<b>%s</b> is requesting access to this course.') % partner.name,
                    user_id=channel.user_id.id,
                    request_partner_id=partner.id
                )
        return activities

    # ---------------------------------------------------------
    # Data / Misc
    # ---------------------------------------------------------

    def _get_categorized_slides(self, base_domain, order, force_void=True, limit=False, offset=False):
        """ Return an ordered structure of slides by categories within a given
        base_domain that must fulfill slides. As a course structure is based on
        its slides sequences, uncategorized slides must have the lowest sequences.

        Example
          * category 1 (sequence 1), category 2 (sequence 3)
          * slide 1 (sequence 0), slide 2 (sequence 2)
          * course structure is: slide 1, category 1, slide 2, category 2
            * slide 1 is uncategorized,
            * category 1 has one slide : Slide 2
            * category 2 is empty.

        Backend and frontend ordering is the same, uncategorized first. It
        eases resequencing based on DOM / displayed order, notably when
        drag n drop is involved. """
        self.ensure_one()
        all_categories = self.env['slide.slide'].sudo().search([('channel_id', '=', self.id), ('is_category', '=', True)])
        all_slides = self.env['slide.slide'].sudo().search(base_domain, order=order)
        category_data = []

        # Prepare all categories by natural order
        for category in all_categories:
            category_slides = all_slides.filtered(lambda slide: slide.category_id == category)
            if not category_slides and not force_void:
                continue
            category_data.append({
                'category': category, 'id': category.id,
                'name': category.name, 'slug_name': slug(category),
                'total_slides': len(category_slides),
                'slides': category_slides[(offset or 0):(limit + offset or len(category_slides))],
            })

        # Add uncategorized slides in first position
        uncategorized_slides = all_slides.filtered(lambda slide: not slide.category_id)
        if uncategorized_slides or force_void:
            category_data.insert(0, {
                'category': False, 'id': False,
                'name': _('Uncategorized'), 'slug_name': _('Uncategorized'),
                'total_slides': len(uncategorized_slides),
                'slides': uncategorized_slides[(offset or 0):(offset + limit or len(uncategorized_slides))],
            })

        return category_data

    def _move_category_slides(self, category, new_category):
        if not category.slide_ids:
            return
        truncated_slide_ids = [slide_id for slide_id in self.slide_ids.ids if slide_id not in category.slide_ids.ids]
        if new_category:
            place_idx = truncated_slide_ids.index(new_category.id)
            ordered_slide_ids = truncated_slide_ids[:place_idx] + category.slide_ids.ids + truncated_slide_ids[place_idx]
        else:
            ordered_slide_ids = category.slide_ids.ids + truncated_slide_ids
        for index, slide_id in enumerate(ordered_slide_ids):
            self.env['slide.slide'].browse([slide_id]).sequence = index + 1

    def _resequence_slides(self, slide, force_category=False):
        ids_to_resequence = self.slide_ids.ids
        index_of_added_slide = ids_to_resequence.index(slide.id)
        next_category_id = None
        if self.slide_category_ids:
            force_category_id = force_category.id if force_category else slide.category_id.id
            index_of_category = self.slide_category_ids.ids.index(force_category_id) if force_category_id else None
            if index_of_category is None:
                next_category_id = self.slide_category_ids.ids[0]
            elif index_of_category < len(self.slide_category_ids.ids) - 1:
                next_category_id = self.slide_category_ids.ids[index_of_category + 1]

        if next_category_id:
            added_slide_id = ids_to_resequence.pop(index_of_added_slide)
            index_of_next_category = ids_to_resequence.index(next_category_id)
            ids_to_resequence.insert(index_of_next_category, added_slide_id)
            for i, record in enumerate(self.env['slide.slide'].browse(ids_to_resequence)):
                record.write({'sequence': i + 1})  # start at 1 to make people scream
        else:
            slide.write({
                'sequence': self.env['slide.slide'].browse(ids_to_resequence[-1]).sequence + 1
            })

    def get_backend_menu_id(self):
        return self.env.ref('website_slides.website_slides_menu_root').id
