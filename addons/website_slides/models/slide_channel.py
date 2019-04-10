# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import api, fields, models, tools, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.gamification.models.gamification_karma_rank import KarmaError
from odoo.exceptions import UserError
from odoo.osv import expression


class ChannelUsersRelation(models.Model):
    _name = 'slide.channel.partner'
    _description = 'Channel / Partners (Members)'
    _table = 'slide_channel_partner'

    channel_id = fields.Many2one('slide.channel', index=True, required=True)
    completed = fields.Boolean('Is Completed', help='Channel validated, even if slides / lessons are added once done.')
    # Todo master: rename this field to avoid confusion between completion (%) and completed count (#)
    completion = fields.Integer('# Completed Slides', compute='_compute_completion', store=True)
    partner_id = fields.Many2one('res.partner', index=True, required=True)
    partner_email = fields.Char(related='partner_id.email', readonly=True)

    @api.depends('channel_id.slide_partner_ids.partner_id', 'channel_id.slide_partner_ids.completed', 'partner_id')
    def _compute_completion(self):
        read_group_res = self.env['slide.slide.partner'].sudo().read_group(
            ['&', '&', ('channel_id', 'in', self.mapped('channel_id').ids),
             ('partner_id', 'in', self.mapped('partner_id').ids),
             ('completed', '=', True)],
            ['channel_id', 'partner_id'],
            groupby=['channel_id', 'partner_id'], lazy=False)
        mapped_data = dict()
        for item in read_group_res:
            mapped_data.setdefault(item['channel_id'][0], dict())
            mapped_data[item['channel_id'][0]][item['partner_id'][0]] = item['__count']

        for record in self:
            slide_done = mapped_data.get(record.channel_id.id, dict()).get(record.partner_id.id, 0)
            record.completion = slide_done

    def _write(self, values):
        partner_karma = False
        to_complete = self.env['slide.channel.partner']
        if values.get('completion'):
            incomplete_self = self.filtered(lambda cp: not cp.completed)
            channels_data = {result['id']: result['total_slides'] for result in incomplete_self.mapped('channel_id').read(['total_slides'])}
            for cp in incomplete_self:
                if values.get('completion') >= channels_data[cp.channel_id.id]:
                    to_complete |= cp

            partner_karma = dict.fromkeys(to_complete.mapped('partner_id').ids, 0)
            for channel_partner in to_complete:
                partner_karma[channel_partner.partner_id.id] += channel_partner.channel_id.karma_gen_channel_finish
            partner_karma = {partner_id: karma_to_add
                             for partner_id, karma_to_add in partner_karma.items() if karma_to_add > 0}

        if to_complete:
            result = super(ChannelUsersRelation, (self - to_complete))._write(values)
            completion_values = dict(values, completed=True)
            super(ChannelUsersRelation, to_complete)._write(completion_values)
            to_complete._post_completion_hook()
        else:
            result = super(ChannelUsersRelation, self)._write(values)

        if partner_karma:
            users = self.env['res.users'].sudo().search([('partner_id', 'in', list(partner_karma.keys()))])
            for user in users:
                users.add_karma(partner_karma[user.partner_id.id])
        return result

    def _post_completion_hook(self):
        pass

class Channel(models.Model):
    """ A channel is a container of slides. """
    _name = 'slide.channel'
    _description = 'Slide Channel'
    _inherit = [
        'mail.thread', 'rating.mixin',
        'image.mixin',
        'website.seo.metadata', 'website.published.multi.mixin']
    _order = 'sequence, id'

    def _default_access_token(self):
        return str(uuid.uuid4())

    # description
    name = fields.Char('Name', translate=True, required=True)
    active = fields.Boolean(default=True)
    description = fields.Text('Short Description', translate=True)
    description_html = fields.Html('Description', translate=tools.html_translate, sanitize_attributes=False)
    channel_type = fields.Selection([
        ('documentation', 'Documentation'), ('training', 'Training')],
        string="Course type", default="documentation", required=True)
    sequence = fields.Integer(default=10, help='Display order')
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.uid)
    tag_ids = fields.Many2many(
        'slide.channel.tag', 'slide_channel_tag_rel', 'channel_id', 'tag_id',
        string='Tags', help='Used to categorize and filter displayed channels/courses')
    category_ids = fields.One2many('slide.category', 'channel_id', string="Categories")
    # slides: promote, statistics
    slide_ids = fields.One2many('slide.slide', 'channel_id', string="Slides")
    slide_last_update = fields.Date('Last Update', compute='_compute_slide_last_update', store=True)
    slide_partner_ids = fields.One2many('slide.slide.partner', 'channel_id', string="Slide User Data", groups='website.group_website_publisher')
    promote_strategy = fields.Selection([
        ('latest', 'Latest Published'),
        ('most_voted', 'Most Voted'),
        ('most_viewed', 'Most Viewed')],
        string="Featuring Policy", default='latest', required=True)
    access_token = fields.Char("Security Token", copy=False, default=_default_access_token)
    nbr_presentation = fields.Integer('Number of Presentations', compute='_compute_slides_statistics', store=True)
    nbr_document = fields.Integer('Number of Documents', compute='_compute_slides_statistics', store=True)
    nbr_video = fields.Integer('Number of Videos', compute='_compute_slides_statistics', store=True)
    nbr_infographic = fields.Integer('Number of Infographics', compute='_compute_slides_statistics', store=True)
    nbr_webpage = fields.Integer("Number of Webpages", compute='_compute_slides_statistics', store=True)
    nbr_quiz = fields.Integer("Number of Quizs", compute='_compute_slides_statistics', store=True)
    total_slides = fields.Integer('# Slides', compute='_compute_slides_statistics', store=True, oldname='total')
    total_views = fields.Integer('# Views', compute='_compute_slides_statistics', store=True)
    total_votes = fields.Integer('# Votes', compute='_compute_slides_statistics', store=True)
    total_time = fields.Float('# Hours', compute='_compute_slides_statistics', digits=(10, 4), store=True)
    # configuration
    allow_comment = fields.Boolean(
        "Allow rating on Course", default=False,
        help="If checked it allows members to either:\n"
             " * like content and post comments on documentation course;\n"
             " * post comment and review on training course;")
    publish_template_id = fields.Many2one(
        'mail.template', string='Published Template',
        help="Email template to send slide publication through email",
        default=lambda self: self.env['ir.model.data'].xmlid_to_res_id('website_slides.slide_template_published'))
    share_template_id = fields.Many2one(
        'mail.template', string='Shared Template',
        help="Email template used when sharing a slide",
        default=lambda self: self.env['ir.model.data'].xmlid_to_res_id('website_slides.slide_template_shared'))
    enroll = fields.Selection([
        ('public', 'Public'), ('invite', 'Invite')],
        default='public', string='Enroll Policy', required=True,
        help='Condition to enroll: everyone, on invite, on payment (sale bridge).')
    enroll_msg = fields.Html(
        'Enroll Message', help="Message explaining the enroll process",
        default=False, translate=tools.html_translate, sanitize_attributes=False)
    enroll_group_ids = fields.Many2many('res.groups', string='Auto Enroll Groups', help="Members of those groups are automatically added as members of the channel.")
    visibility = fields.Selection([
        ('public', 'Public'), ('members', 'Members')],
        default='public', string='Visibility', required=True,
        help='Applied directly as ACLs. Allow to hide channels and their content for non members.')
    partner_ids = fields.Many2many(
        'res.partner', 'slide_channel_partner', 'channel_id', 'partner_id',
        string='Members', help="All members of the channel.", context={'active_test': False})
    members_count = fields.Integer('Attendees count', compute='_compute_members_count')
    is_member = fields.Boolean(string='Is Member', compute='_compute_is_member')
    channel_partner_ids = fields.One2many('slide.channel.partner', 'channel_id', string='Members Information', groups='website.group_website_publisher')
    upload_group_ids = fields.Many2many(
        'res.groups', 'rel_upload_groups', 'channel_id', 'group_id', string='Upload Groups',
        help="Who can publish: responsible, members of upload_group_ids if defined or website publisher group members.")
    # not stored access fields, depending on each user
    completed = fields.Boolean('Done', compute='_compute_user_statistics')
    completion = fields.Integer('Completion', compute='_compute_user_statistics')
    can_upload = fields.Boolean('Can Upload', compute='_compute_can_upload')
    # karma generation
    karma_gen_slide_vote = fields.Integer(string='Lesson voted', default=1)
    karma_gen_channel_rank = fields.Integer(string='Course ranked', default=5)
    karma_gen_channel_finish = fields.Integer(string='Course finished', default=10)
    # Karma based actions
    karma_review = fields.Integer('Add a review', default=10, help="Karma needed to add a review on the course")
    karma_slide_comment = fields.Integer('Add a comment', default=3, help="Karma needed to add a comment on a slide of this course")
    karma_slide_vote = fields.Integer('Vote on slide', default=3, help="Karma needed to like/dislike a slide of this course.")
    can_review = fields.Boolean('Can Review', compute='_compute_action_rights')
    can_comment = fields.Boolean('Can Comment', compute='_compute_action_rights')
    can_vote = fields.Boolean('Can Vote', compute='_compute_action_rights')

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

    @api.depends('channel_partner_ids.partner_id')
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

    @api.depends('slide_ids.slide_type', 'slide_ids.is_published', 'slide_ids.completion_time',
                 'slide_ids.likes', 'slide_ids.dislikes', 'slide_ids.total_views')
    def _compute_slides_statistics(self):
        result = dict((cid, dict(total_views=0, total_votes=0, total_time=0)) for cid in self.ids)
        read_group_res = self.env['slide.slide'].read_group(
            [('is_published', '=', True),('channel_id', 'in', self.ids)],
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
            record.update(result[record.id])

    def _compute_slides_statistics_type(self, read_group_res):
        """ Compute statistics based on all existing slide types """
        slide_types = self.env['slide.slide']._fields['slide_type'].get_values(self.env)
        keys = ['nbr_%s' % slide_type for slide_type in slide_types]
        keys.append('total_slides')
        result = dict((cid, dict((key, 0) for key in keys)) for cid in self.ids)
        for res_group in read_group_res:
            cid = res_group['channel_id'][0]
            for slide_type in slide_types:
                result[cid]['nbr_%s' % slide_type] += res_group.get('slide_type', '') == slide_type and res_group['__count'] or 0
                result[cid]['total_slides'] += res_group.get('slide_type', '') == slide_type and res_group['__count'] or 0
        return result

    @api.depends('slide_partner_ids', 'total_slides')
    def _compute_user_statistics(self):
        current_user_info = self.env['slide.channel.partner'].sudo().search(
            [('channel_id', 'in', self.ids), ('partner_id', '=', self.env.user.partner_id.id)]
        )
        mapped_data = dict((info.channel_id.id, (info.completed, info.completion)) for info in current_user_info)
        for record in self:
            completed, completion = mapped_data.get(record.id, (False, 0))
            record.completed = completed
            record.completion = round(100.0 * completion / (record.total_slides or 1))

    @api.depends('upload_group_ids', 'user_id')
    def _compute_can_upload(self):
        for record in self:
            if record.user_id == self.env.user:
                record.can_upload = True
            elif record.upload_group_ids:
                record.can_upload = bool(record.upload_group_ids & self.env.user.groups_id)
            else:
                record.can_upload = self.env.user.has_group('website.group_website_publisher')

    @api.depends('channel_type', 'user_id', 'can_upload')
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
                record.can_publish = self.env.user.has_group('website.group_website_publisher')

    @api.model
    def _get_can_publish_error_message(self):
        return _("Publishing is restricted to the responsible of training courses or members of the publisher group for documentation courses")

    @api.multi
    @api.depends('name')
    def _compute_website_url(self):
        super(Channel, self)._compute_website_url()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for channel in self:
            if channel.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                channel.website_url = '%s/slides/%s' % (base_url, slug(channel))

    @api.multi
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
                SET %(column_name)s = md5(md5(random()::varchar || id::varchar) || clock_timestamp()::varchar)::uuid::varchar
                WHERE %(column_name)s IS NULL
            """ % {'table_name': self._table, 'column_name': column_name}
            self.env.cr.execute(query)

    @api.model
    def create(self, vals):
        # Ensure creator is member of its channel it is easier for him to manage it (unless it is odoobot)
        if not vals.get('channel_partner_ids') and not self.env.is_superuser():
            vals['channel_partner_ids'] = [(0, 0, {
                'partner_id': self.env.user.partner_id.id
            })]
        channel = super(Channel, self.with_context(mail_create_nosubscribe=True)).create(vals)

        if channel.user_id:
            channel._action_add_members(channel.user_id.partner_id)
        if 'enroll_group_ids' in vals:
            channel._add_groups_members()
        return channel

    @api.multi
    def write(self, vals):
        res = super(Channel, self).write(vals)
        if vals.get('user_id'):
            self._action_add_members(self.env['res.users'].sudo().browse(vals['user_id']).partner_id)
        if 'active' in vals:
            # archiving/unarchiving a channel does it on its slides, too
            self.with_context(active_test=False).mapped('slide_ids').write({'active': vals['active']})
        if 'enroll_group_ids' in vals:
            self._add_groups_members()
        return res

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, parent_id=False, subtype=None, **kwargs):
        """ Temporary workaround to avoid spam. If someone replies on a channel
        through the 'Presentation Published' email, it should be considered as a
        note as we don't want all channel followers to be notified of this answer. """
        self.ensure_one()
        if kwargs.get('message_type') == 'comment' and not self.can_review:
            raise KarmaError(_('Not enough karma to review'))
        if parent_id:
            parent_message = self.env['mail.message'].sudo().browse(parent_id)
            if parent_message.subtype_id and parent_message.subtype_id == self.env.ref('website_slides.mt_channel_slide_published'):
                if kwargs.get('subtype_id'):
                    kwargs['subtype_id'] = False
                subtype = 'mail.mt_note'
        return super(Channel, self).message_post(parent_id=parent_id, subtype=subtype, **kwargs)

    # ---------------------------------------------------------
    # Business / Actions
    # ---------------------------------------------------------

    @api.multi
    def action_redirect_to_members(self):
        action = self.env.ref('website_slides.slide_channel_partner_action').read()[0]
        action['view_mode'] = 'tree'
        action['domain'] = [('channel_id', 'in', self.ids)]
        if len(self) == 1:
            action['context'] = {'default_channel_id': self.id}

        return action

    @api.multi
    def action_channel_invite(self):
        self.ensure_one()

        if self.enroll != 'invite':
            raise UserError(_("You cannot send invitations for channels that are not set as 'invite'."))

        template = self.env.ref('website_slides.mail_template_slide_channel_invite', raise_if_not_found=False)

        local_context = dict(
            self.env.context,
            default_channel_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            notif_layout='mail.mail_notification_light',
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

    def _remove_membership(self, partner_ids):
        """ Unlink (!!!) the relationships between the passed partner_ids
        and the channels and their slides. """
        if not partner_ids:
            raise ValueError("Do not use this method with an empty partner_id recordset")

        removed_slide_partner_domain = []
        removed_channel_partner_domain = []
        for channel in self:
            removed_slide_partner_domain = expression.OR([
                removed_slide_partner_domain,
                [('partner_id', 'in', partner_ids.ids),
                 ('slide_id', 'in', channel.slide_ids.ids)]
            ])

            removed_channel_partner_domain = expression.OR([
                removed_channel_partner_domain,
                [('partner_id', 'in', partner_ids.ids),
                 ('channel_id', '=', channel.id)]
            ])

        if removed_slide_partner_domain:
            self.env['slide.slide.partner'].sudo().search(removed_slide_partner_domain).unlink()

        if removed_channel_partner_domain:
            self.env['slide.channel.partner'].sudo().search(removed_channel_partner_domain).unlink()

    # ---------------------------------------------------------
    # Rating Mixin API
    # ---------------------------------------------------------

    @api.multi
    def _rating_domain(self):
        """ Only take the published rating into account to compute avg and count """
        domain = super(Channel, self)._rating_domain()
        return expression.AND([domain, [('website_published', '=', True)]])

    # ---------------------------------------------------------
    # Data / Misc
    # ---------------------------------------------------------

    def _get_categorized_slides(self, base_domain, order, force_void=True, limit=False, offset=False):
        """ Return an ordered structure of slides by categories within a given
        base_domain that must fulfill slides. """
        self.ensure_one()
        all_categories = self.env['slide.category'].search([('channel_id', '=', self.id)])
        all_slides = self.env['slide.slide'].sudo().search(base_domain, order=order)
        category_data = []

        # First add uncategorized slides
        uncategorized_slides = all_slides.filtered(lambda slide: not slide.category_id)
        if uncategorized_slides or force_void:
            category_data.append({
                'category': False, 'id': False,
                'name': _('Uncategorized'), 'slug_name': _('Uncategorized'),
                'total_slides': len(uncategorized_slides),
                'slides': uncategorized_slides[(offset or 0):(offset + limit or len(uncategorized_slides))],
            })
        # Then all categories by natural order
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
        return category_data


class Category(models.Model):
    """ Channel contain various categories to manage its slides """
    _name = 'slide.category'
    _description = "Slides Category"
    _order = "sequence, id"

    name = fields.Char('Name', translate=True, required=True)
    channel_id = fields.Many2one('slide.channel', string="Channel", required=True, ondelete='cascade')
    sequence = fields.Integer(default=10, help='Display order')
    slide_ids = fields.One2many('slide.slide', 'category_id', string="Slides")
    nbr_presentation = fields.Integer("Number of Presentations", compute='_count_presentations', store=True)
    nbr_document = fields.Integer("Number of Documents", compute='_count_presentations', store=True)
    nbr_video = fields.Integer("Number of Videos", compute='_count_presentations', store=True)
    nbr_infographic = fields.Integer("Number of Infographics", compute='_count_presentations', store=True)
    nbr_webpage = fields.Integer("Number of Webpages", compute='_count_presentations', store=True)
    nbr_quiz = fields.Integer("Number of Quizs", compute="_count_presentations", store=True)
    total_slides = fields.Integer(compute='_count_presentations', store=True, oldname='total')

    @api.depends('slide_ids.slide_type', 'slide_ids.is_published')
    def _count_presentations(self):
        result = dict.fromkeys(self.ids, dict())
        res = self.env['slide.slide'].read_group(
            [('is_published', '=', True), ('category_id', 'in', self.ids)],
            ['category_id', 'slide_type'], ['category_id', 'slide_type'],
            lazy=False)

        type_stats = self._compute_slides_statistics_type(res)
        for cid, cdata in type_stats.items():
            result[cid].update(cdata)

        for record in self:
            record.update(result[record.id])

    def _compute_slides_statistics_type(self, read_group_res):
        """ Compute statistics based on all existing slide types """
        slide_types = self.env['slide.slide']._fields['slide_type'].get_values(self.env)
        keys = ['nbr_%s' % slide_type for slide_type in slide_types]
        keys.append('total_slides')
        result = dict((cid, dict((key, 0) for key in keys)) for cid in self.ids)
        for res_group in read_group_res:
            cid = res_group['category_id'][0]
            for slide_type in slide_types:
                result[cid]['nbr_%s' % slide_type] += res_group.get('slide_type', '') == slide_type and res_group['__count'] or 0
                result[cid]['total_slides'] += res_group.get('slide_type', '') == slide_type and res_group['__count'] or 0
        return result
