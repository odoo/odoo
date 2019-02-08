# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.tools.translate import html_translate
from odoo.osv import expression


class ChannelUsersRelation(models.Model):
    _name = 'slide.channel.partner'
    _description = 'Channel / Partners (Members)'
    _table = 'slide_channel_partner'

    channel_id = fields.Many2one('slide.channel', index=True, required=True)
    partner_id = fields.Many2one('res.partner', index=True, required=True)


class Channel(models.Model):
    """ A channel is a container of slides. It has group-based access configuration
    allowing to configure slide upload and access. Slides can be promoted in
    channels. """
    _name = 'slide.channel'
    _description = 'Slide Channel'
    _inherit = ['mail.thread', 'website.seo.metadata', 'website.published.multi.mixin', 'rating.mixin']
    _order = 'sequence, id'

    def _default_access_token(self):
        return str(uuid.uuid4())

    # description
    name = fields.Char('Name', translate=True, required=True)
    active = fields.Boolean(default=True)
    description = fields.Html('Description', translate=html_translate, sanitize_attributes=False)
    sequence = fields.Integer(default=10, help='Display order')
    category_ids = fields.One2many('slide.category', 'channel_id', string="Categories")
    # slides: promote, statistics
    slide_ids = fields.One2many('slide.slide', 'channel_id', string="Slides")
    promote_strategy = fields.Selection([
        ('none', 'No Featured Presentation'),
        ('latest', 'Latest Published'),
        ('most_voted', 'Most Voted'),
        ('most_viewed', 'Most Viewed'),
        ('custom', 'Featured Presentation')],
        string="Featuring Policy", default='most_voted', required=True)
    custom_slide_id = fields.Many2one('slide.slide', string='Slide to Promote')
    promoted_slide_id = fields.Many2one('slide.slide', string='Featured Slide', compute='_compute_promoted_slide_id', store=True)
    access_token = fields.Char("Security Token", copy=False, default=_default_access_token)
    nbr_presentations = fields.Integer('Number of Presentations', compute='_count_presentations', store=True)
    nbr_documents = fields.Integer('Number of Documents', compute='_count_presentations', store=True)
    nbr_videos = fields.Integer('Number of Videos', compute='_count_presentations', store=True)
    nbr_infographics = fields.Integer('Number of Infographics', compute='_count_presentations', store=True)
    total = fields.Integer(compute='_count_presentations', store=True)
    # configuration
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
        string='Members', help="All members of the channel.")
    is_member = fields.Boolean(string='Is Member', compute='_compute_is_member')
    channel_partner_ids = fields.One2many('slide.channel.partner', 'channel_id', string='Members Information', groups='base.group_system')
    enroll_msg = fields.Html(
        'Enroll Message', help="Message explaining the enroll process",
        default=False, translate=html_translate, sanitize_attributes=False)
    upload_group_ids = fields.Many2many(
        'res.groups', 'rel_upload_groups', 'channel_id', 'group_id',
        string='Upload Groups', help="Groups allowed to upload presentations in this channel. If void, every user can upload.")
    # not stored access fields, depending on each user
    can_upload = fields.Boolean('Can Upload', compute='_compute_access')
    can_publish = fields.Boolean('Can Publish', compute='_compute_access')

    @api.depends('custom_slide_id', 'promote_strategy', 'slide_ids.likes',
                 'slide_ids.total_views', "slide_ids.date_published")
    def _compute_promoted_slide_id(self):
        for record in self:
            if record.promote_strategy == 'none':
                record.promoted_slide_id = False
            elif record.promote_strategy == 'custom':
                record.promoted_slide_id = record.custom_slide_id
            elif record.promote_strategy:
                slides = self.env['slide.slide'].search(
                    [('website_published', '=', True), ('channel_id', '=', record.id)],
                    limit=1, order=self.env['slide.slide']._order_by_strategy[record.promote_strategy])
                record.promoted_slide_id = slides and slides[0] or False

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

    @api.depends('slide_ids.slide_type', 'slide_ids.website_published')
    def _count_presentations(self):
        result = dict.fromkeys(self.ids, dict())
        res = self.env['slide.slide'].read_group(
            [('website_published', '=', True), ('channel_id', 'in', self.ids)],
            ['channel_id', 'slide_type'],
            groupby=['channel_id', 'slide_type'],
            lazy=False)
        for res_group in res:
            result[res_group['channel_id'][0]][res_group['slide_type']] = result[res_group['channel_id'][0]].get(res_group['slide_type'], 0) + res_group['__count']
        for record in self:
            record.nbr_presentations = result[record.id].get('presentation', 0)
            record.nbr_documents = result[record.id].get('document', 0)
            record.nbr_videos = result[record.id].get('video', 0)
            record.nbr_infographics = result[record.id].get('infographic', 0)
            record.total = record.nbr_presentations + record.nbr_documents + record.nbr_videos + record.nbr_infographics

    @api.one
    @api.depends('visibility', 'partner_ids', 'upload_group_ids')
    def _compute_access(self):
        self.can_upload = not self.env.user.share and (not self.upload_group_ids or bool(self.upload_group_ids & self.env.user.groups_id))
        self.can_publish = self.can_upload and self.env.user.has_group('website.group_website_publisher')

    @api.multi
    @api.depends('name')
    def _compute_website_url(self):
        super(Channel, self)._compute_website_url()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for channel in self:
            if channel.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                channel.website_url = '%s/slides/%s' % (base_url, slug(channel))

    @api.onchange('visibility')
    def change_visibility(self):
        pass

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
        if vals.get('visibility') == 'invite' and not vals.get('channel_partner_ids'):
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

    def action_add_member(self, target_partner=False, **member_values):
        if not target_partner:
            target_partner = self.env.user.partner_id
        existing = self.env['slide.channel.partner'].sudo().search([
            ('channel_id', 'in', self.ids),
            ('partner_id', '=', target_partner.id)
        ])
        to_join = (self - existing.mapped('channel_id'))._filter_add_member(target_partner, **member_values)
        if to_join:
            self.env['slide.channel.partner'].sudo().create([
                dict(channel_id=channel.id, partner_id=target_partner.id, **member_values)
                for channel in to_join
            ])
            return to_join
        return False

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
    total = fields.Integer(compute='_count_presentations', store=True)

    @api.depends('slide_ids.slide_type', 'slide_ids.website_published')
    def _count_presentations(self):
        result = dict.fromkeys(self.ids, dict())
        res = self.env['slide.slide'].read_group(
            [('website_published', '=', True), ('category_id', 'in', self.ids)],
            ['category_id', 'slide_type'], ['category_id', 'slide_type'],
            lazy=False)
        for res_group in res:
            result[res_group['category_id'][0]][res_group['slide_type']] = result[res_group['category_id'][0]].get(res_group['slide_type'], 0) + res_group['__count']
        for record in self:
            record.nbr_presentations = result[record.id].get('presentation', 0)
            record.nbr_documents = result[record.id].get('document', 0)
            record.nbr_videos = result[record.id].get('video', 0)
            record.nbr_infographics = result[record.id].get('infographic', 0)
            record.total = record.nbr_presentations + record.nbr_documents + record.nbr_videos + record.nbr_infographics
