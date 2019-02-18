# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
import uuid

from odoo import api, fields, models, tools, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.exceptions import UserError
from odoo.osv import expression


class ChannelUsersRelation(models.Model):
    _name = 'slide.channel.partner'
    _description = 'Channel / Partners (Members)'
    _table = 'slide_channel_partner'

    channel_id = fields.Many2one('slide.channel', index=True, required=True)
    completed = fields.Boolean('Is Completed', help='Channel validated, even if slides / lessons are added once done.')
    completion = fields.Integer('Completion', compute='_compute_completion', store=True)
    partner_id = fields.Many2one('res.partner', index=True, required=True)
    partner_email = fields.Char(related='partner_id.email', readonly=True)

    @api.depends('channel_id.slide_partner_ids.partner_id', 'channel_id.slide_partner_ids.completed', 'channel_id.total_slides', 'partner_id')
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

        channel_data = {}
        channel_ids = mapped_data.keys()
        if channel_ids:
            channel_read_res = self.env['slide.channel'].sudo().browse(channel_ids).read(['total_slides'])
            channel_data = dict((channel['id'], channel['total_slides']) for channel in channel_read_res)

        for record in self:
            slide_done = mapped_data.get(record.channel_id.id, dict()).get(record.partner_id.id, 0)
            slide_total = channel_data.get(record.channel_id.id) or 1
            record.completion = math.ceil(100.0 * slide_done / slide_total)

    def _write(self, values):
        if 'completion' in values and values['completion'] >= 100:
            values['completed'] = True
            result = super(ChannelUsersRelation, self)._write(values)
            partner_has_completed = {channel_partner.partner_id.id: channel_partner.channel_id for channel_partner in self}
            users = self.env['res.users'].sudo().search([('partner_id', 'in', list(partner_has_completed.keys()))])
            for user in users:
                users.add_karma(partner_has_completed[user.partner_id.id].karma_gen_channel_finish)
        else:
            result = super(ChannelUsersRelation, self)._write(values)
        return result


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
    description = fields.Html('Description', translate=tools.html_translate, sanitize_attributes=False)
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
    nbr_presentations = fields.Integer('Number of Presentations', compute='_compute_slides_statistics', store=True)
    nbr_documents = fields.Integer('Number of Documents', compute='_compute_slides_statistics', store=True)
    nbr_videos = fields.Integer('Number of Videos', compute='_compute_slides_statistics', store=True)
    nbr_infographics = fields.Integer('Number of Infographics', compute='_compute_slides_statistics', store=True)
    nbr_webpages = fields.Integer("Number of Webpages", compute='_compute_slides_statistics', store=True)
    total_slides = fields.Integer('# Slides', compute='_compute_slides_statistics', store=True, oldname='total')
    total_views = fields.Integer('# Views', compute='_compute_slides_statistics', store=True)
    total_votes = fields.Integer('# Votes', compute='_compute_slides_statistics', store=True)
    total_time = fields.Float('# Hours', compute='_compute_slides_statistics', digits=(10, 4), store=True)
    # configuration
    allow_comment = fields.Boolean("Allow comment on Content", default=False, help="When checked, the options will allow member to add comment on content:\n"
             "  * Documentation channel: allow to like content and post comments\n"
             "  * Training channel: allow to post comments and reviews\n")
    publish_template_id = fields.Many2one(
        'mail.template', string='Published Template',
        help="Email template to send slide publication through email",
        default=lambda self: self.env['ir.model.data'].xmlid_to_res_id('website_slides.slide_template_published'))
    share_template_id = fields.Many2one(
        'mail.template', string='Shared Template',
        help="Email template used when sharing a slide",
        default=lambda self: self.env['ir.model.data'].xmlid_to_res_id('website_slides.slide_template_shared'))
    visibility = fields.Selection([
        ('public', 'Public'),
        ('invite', 'Invite')],
        default='public', required=True)
    partner_ids = fields.Many2many(
        'res.partner', 'slide_channel_partner', 'channel_id', 'partner_id',
        string='Members', help="All members of the channel.", context={'active_test': False})
    members_count = fields.Integer('Attendees count', compute='_compute_members_count')
    is_member = fields.Boolean(string='Is Member', compute='_compute_is_member')
    channel_partner_ids = fields.One2many('slide.channel.partner', 'channel_id', string='Members Information', groups='website.group_website_publisher')
    enroll_msg = fields.Html(
        'Enroll Message', help="Message explaining the enroll process",
        default=False, translate=tools.html_translate, sanitize_attributes=False)
    upload_group_ids = fields.Many2many(
        'res.groups', 'rel_upload_groups', 'channel_id', 'group_id',
        string='Upload Groups', help="Groups allowed to upload presentations in this channel. If void, every user can upload.")
    # not stored access fields, depending on each user
    completed = fields.Boolean('Done', compute='_compute_user_statistics')
    completion = fields.Integer('Completion', compute='_compute_user_statistics')
    can_upload = fields.Boolean('Can Upload', compute='_compute_access')
    can_publish = fields.Boolean('Can Publish', compute='_compute_access')
    # karma generation
    karma_gen_slide_vote = fields.Integer(string='Lesson voted', default=1)
    karma_gen_channel_share = fields.Integer(string='Course shared', default=2)
    karma_gen_channel_rank = fields.Integer(string='Course ranked', default=5)
    karma_gen_channel_finish = fields.Integer(string='Course finished', default=10)
    # TODO DBE : Add karma based action rules (like in forum)

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
            channel.valid_channel_partner_ids = result.get(channel.id, False)
            channel.is_member = self.env.user.partner_id.id in channel.valid_channel_partner_ids if channel.valid_channel_partner_ids else False

    @api.depends('slide_ids.slide_type', 'slide_ids.is_published', 'slide_ids.completion_time',
                 'slide_ids.likes', 'slide_ids.dislikes', 'slide_ids.total_views')
    def _compute_slides_statistics(self):
        result = dict((cid, dict(total_slides=0, total_views=0, total_votes=0, total_time=0)) for cid in self.ids)
        read_group_res = self.env['slide.slide'].read_group(
            [('is_published', '=', True), ('channel_id', 'in', self.ids)],
            ['channel_id', 'slide_type', 'likes', 'dislikes', 'total_views', 'completion_time'],
            groupby=['channel_id', 'slide_type'],
            lazy=False)
        for res_group in read_group_res:
            cid = res_group['channel_id'][0]
            result[cid]['total_slides'] += res_group['__count']
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
        """ Can be overridden to compute stats on added slide_types """
        result = dict((cid, dict(nbr_presentations=0, nbr_documents=0, nbr_videos=0, nbr_infographics=0, nbr_webpages=0)) for cid in self.ids)
        for res_group in read_group_res:
            cid = res_group['channel_id'][0]
            result[cid]['nbr_presentations'] += res_group.get('slide_type', '') == 'presentation' and res_group['__count'] or 0
            result[cid]['nbr_documents'] += res_group.get('slide_type', '') == 'document' and res_group['__count'] or 0
            result[cid]['nbr_videos'] += res_group.get('slide_type', '') == 'video' and res_group['__count'] or 0
            result[cid]['nbr_infographics'] += res_group.get('slide_type', '') == 'infographic' and res_group['__count'] or 0
            result[cid]['nbr_webpages'] += res_group.get('slide_type', '') == 'webpage' and res_group['__count'] or 0
        return result

    @api.depends('slide_partner_ids')
    def _compute_user_statistics(self):
        current_user_info = self.env['slide.channel.partner'].sudo().search(
            [('channel_id', 'in', self.ids), ('partner_id', '=', self.env.user.partner_id.id)]
        )
        mapped_data = dict((info.channel_id.id, (info.completed, info.completion)) for info in current_user_info)
        for record in self:
            record.completed, record.completion = mapped_data.get(record.id, (False, 0))

    @api.depends('channel_type', 'partner_ids', 'upload_group_ids')
    def _compute_access(self):
        for record in self:
            is_doc = record.channel_type == 'documentation'
            record.can_upload = not self.env.user.share and (not record.upload_group_ids or bool(record.upload_group_ids & self.env.user.groups_id))
            record.can_publish = record.can_upload and self.env.user.has_group('website.group_website_publisher') and (is_doc or record.user_id == self.env.user)

    @api.multi
    @api.depends('name')
    def _compute_website_url(self):
        super(Channel, self)._compute_website_url()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for channel in self:
            if channel.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                channel.website_url = '%s/slides/%s' % (base_url, slug(channel))

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

        if self.visibility != 'invite':
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
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'slide.channel.invite',
            'target': 'new',
            'context': local_context,
        }

    # ---------------------------------------------------------
    # ORM Overrides
    # ---------------------------------------------------------

    @api.model_cr_context
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
        # Ensure creator is member of its channel it is easier for him to manage it
        if not vals.get('channel_partner_ids'):
            vals['channel_partner_ids'] = [(0, 0, {
                'partner_id': self.env.user.partner_id.id
            })]
        return super(Channel, self.with_context(mail_create_nosubscribe=True)).create(vals)

    @api.multi
    def write(self, vals):
        res = super(Channel, self).write(vals)
        if 'active' in vals:
            # archiving/unarchiving a channel does it on its slides, too
            self.with_context(active_test=False).mapped('slide_ids').write({'active': vals['active']})
        return res

    @api.multi
    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, parent_id=False, subtype=None, **kwargs):
        """ Temporary workaround to avoid spam. If someone replies on a channel
        through the 'Presentation Published' email, it should be considered as a
        note as we don't want all channel followers to be notified of this answer. """
        self.ensure_one()
        if parent_id:
            parent_message = self.env['mail.message'].sudo().browse(parent_id)
            if parent_message.subtype_id and parent_message.subtype_id == self.env.ref('website_slides.mt_channel_slide_published'):
                if kwargs.get('subtype_id'):
                    kwargs['subtype_id'] = False
                subtype = 'mail.mt_note'
        return super(Channel, self).message_post(parent_id=parent_id, subtype=subtype, **kwargs)

    # ---------------------------------------------------------
    # Rating Mixin API
    # ---------------------------------------------------------

    def action_add_member(self, **member_values):
        """ Adds the logged in user in the channel members.
        (see '_action_add_member' for more info)

        Returns True if added successfully, False otherwise."""
        return bool(self._action_add_member(target_partner=self.env.user.partner_id, **member_values))

    def _action_add_member(self, target_partner=False, **member_values):
        """ Add the target_partner as a member of the channel (to its slide.channel.partner).
        This will make the content (slides) of the channel available to that partner.

        Returns the added 'slide.channel.partner's (! as sudo !)
        """
        existing = self.env['slide.channel.partner'].sudo().search([
            ('channel_id', 'in', self.ids),
            ('partner_id', '=', target_partner.id)
        ])
        to_join = (self - existing.mapped('channel_id'))._filter_add_member(target_partner, **member_values)
        if to_join:
            slide_partners_sudo = self.env['slide.channel.partner'].sudo().create([
                dict(channel_id=channel.id, partner_id=target_partner.id, **member_values)
                for channel in to_join
            ])
            return slide_partners_sudo
        return self.env['slide.channel.partner'].sudo()

    def _filter_add_member(self, target_partner, **member_values):
        allowed = self.filtered(lambda channel: channel.visibility == 'public')
        on_invite = self.filtered(lambda channel: channel.visibility == 'invite')
        if on_invite:
            try:
                on_invite.check_access_rights('write')
                on_invite.check_access_rule('write')
            except:
                pass
            else:
                allowed |= on_invite
        return allowed

    def list_all(self):
        return {
            'channels': [{'id': channel.id, 'name': channel.name, 'website_url': channel.website_url} for channel in self.search([])]
        }

    # ---------------------------------------------------------
    # Rating Mixin API
    # ---------------------------------------------------------

    @api.multi
    def _rating_domain(self):
        """ Only take the published rating into account to compute avg and count """
        domain = super(Channel, self)._rating_domain()
        return expression.AND([domain, [('website_published', '=', True)]])


class Category(models.Model):
    """ Channel contain various categories to manage its slides """
    _name = 'slide.category'
    _description = "Slides Category"
    _order = "sequence, id"

    name = fields.Char('Name', translate=True, required=True)
    channel_id = fields.Many2one('slide.channel', string="Channel", required=True, ondelete='cascade')
    sequence = fields.Integer(default=10, help='Display order')
    slide_ids = fields.One2many('slide.slide', 'category_id', string="Slides")
    nbr_presentations = fields.Integer("Number of Presentations", compute='_count_presentations', store=True)
    nbr_documents = fields.Integer("Number of Documents", compute='_count_presentations', store=True)
    nbr_videos = fields.Integer("Number of Videos", compute='_count_presentations', store=True)
    nbr_infographics = fields.Integer("Number of Infographics", compute='_count_presentations', store=True)
    nbr_webpages = fields.Integer("Number of Webpages", compute='_count_presentations', store=True)
    total_slides = fields.Integer(compute='_count_presentations', store=True, oldname='total')

    @api.depends('slide_ids.slide_type', 'slide_ids.is_published')
    def _count_presentations(self):
        result = dict.fromkeys(self.ids, dict())
        res = self.env['slide.slide'].read_group(
            [('is_published', '=', True), ('category_id', 'in', self.ids)],
            ['category_id', 'slide_type'], ['category_id', 'slide_type'],
            lazy=False)
        for res_group in res:
            result[res_group['category_id'][0]][res_group['slide_type']] = result[res_group['category_id'][0]].get(res_group['slide_type'], 0) + res_group['__count']

        for record in self:
            record.update(self._extract_count_presentations_type(result, record.id))

    def _extract_count_presentations_type(self, result, record_id):
        """ Can be overridden to compute stats on added slide_types """
        statistics = {
            'nbr_presentations': result[record_id].get('presentation', 0),
            'nbr_documents': result[record_id].get('document', 0),
            'nbr_videos': result[record_id].get('video', 0),
            'nbr_infographics': result[record_id].get('infographic', 0),
            'nbr_webpages': result[record_id].get('webpage', 0),
            'total_slides': 0
        }

        statistics['total_slides'] += statistics['nbr_presentations']
        statistics['total_slides'] += statistics['nbr_documents']
        statistics['total_slides'] += statistics['nbr_videos']
        statistics['total_slides'] += statistics['nbr_infographics']
        statistics['total_slides'] += statistics['nbr_webpages']

        return statistics
