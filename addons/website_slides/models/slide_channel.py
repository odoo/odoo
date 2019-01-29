# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.tools.translate import html_translate


class Channel(models.Model):
    """ A channel is a container of slides. It has group-based access configuration
    allowing to configure slide upload and access. Slides can be promoted in
    channels. """
    _name = 'slide.channel'
    _description = 'Slide Channel'
    _inherit = ['mail.thread', 'website.seo.metadata', 'website.published.multi.mixin']
    _order = 'sequence, id'
    _order_by_strategy = {
        'most_viewed': 'total_views desc',
        'most_voted': 'likes desc',
        'latest': 'date_published desc',
    }

    name = fields.Char('Name', translate=True, required=True)
    active = fields.Boolean(default=True)
    description = fields.Html('Description', translate=html_translate, sanitize_attributes=False)
    sequence = fields.Integer(default=10, help='Display order')
    category_ids = fields.One2many('slide.category', 'channel_id', string="Categories")
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
                    limit=1, order=self._order_by_strategy[record.promote_strategy])
                record.promoted_slide_id = slides and slides[0] or False

    nbr_presentations = fields.Integer('Number of Presentations', compute='_count_presentations', store=True)
    nbr_documents = fields.Integer('Number of Documents', compute='_count_presentations', store=True)
    nbr_videos = fields.Integer('Number of Videos', compute='_count_presentations', store=True)
    nbr_infographics = fields.Integer('Number of Infographics', compute='_count_presentations', store=True)
    total = fields.Integer(compute='_count_presentations', store=True)

    @api.depends('slide_ids.slide_type', 'slide_ids.website_published')
    def _count_presentations(self):
        result = dict.fromkeys(self.ids, dict())
        res = self.env['slide.slide'].read_group(
            [('website_published', '=', True), ('channel_id', 'in', self.ids)],
            ['channel_id', 'slide_type'], ['channel_id', 'slide_type'],
            lazy=False)
        for res_group in res:
            result[res_group['channel_id'][0]][res_group['slide_type']] = result[res_group['channel_id'][0]].get(res_group['slide_type'], 0) + res_group['__count']
        for record in self:
            record.nbr_presentations = result[record.id].get('presentation', 0)
            record.nbr_documents = result[record.id].get('document', 0)
            record.nbr_videos = result[record.id].get('video', 0)
            record.nbr_infographics = result[record.id].get('infographic', 0)
            record.total = record.nbr_presentations + record.nbr_documents + record.nbr_videos + record.nbr_infographics

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
        ('private', 'Private'),
        ('partial', 'Show channel but restrict presentations')],
        default='public', required=True)
    group_ids = fields.Many2many(
        'res.groups', 'rel_channel_groups', 'channel_id', 'group_id',
        string='Channel Groups', help="Groups allowed to see presentations in this channel")
    access_error_msg = fields.Html(
        'Error Message', help="Message to display when not accessible due to access rights",
        default=lambda s: _("<p>This channel is private and its content is restricted to some users.</p>"),
        translate=html_translate, sanitize_attributes=False)
    upload_group_ids = fields.Many2many(
        'res.groups', 'rel_upload_groups', 'channel_id', 'group_id',
        string='Upload Groups', help="Groups allowed to upload presentations in this channel. If void, every user can upload.")
    # not stored access fields, depending on each user
    can_see = fields.Boolean('Can See', compute='_compute_access', search='_search_can_see')
    can_see_full = fields.Boolean('Full Access', compute='_compute_access')
    can_upload = fields.Boolean('Can Upload', compute='_compute_access')

    def _search_can_see(self, operator, value):
        if operator not in ('=', '!=', '<>'):
            raise ValueError('Invalid operator: %s' % (operator,))

        if not value:
            operator = operator == "=" and '!=' or '='

        if self._uid == SUPERUSER_ID:
            return [(1, '=', 1)]

        # Better perfs to split request and use inner join that left join
        req = """
            SELECT id FROM slide_channel WHERE visibility='public'
                UNION
            SELECT c.id
                FROM slide_channel c
                    INNER JOIN rel_channel_groups rg on c.id = rg.channel_id
                    INNER JOIN res_groups g on g.id = rg.group_id
                    INNER JOIN res_groups_users_rel u on g.id = u.gid and uid = %s
        """
        op = operator == "=" and "inselect" or "not inselect"
        # don't use param named because orm will add other param (test_active, ...)
        return [('id', op, (req, (self._uid, )))]

    @api.one
    @api.depends('visibility', 'group_ids', 'upload_group_ids')
    def _compute_access(self):
        self.can_see = self.visibility in ['public', 'partial'] or bool(self.group_ids & self.env.user.groups_id)
        self.can_see_full = self.visibility == 'public' or bool(self.group_ids & self.env.user.groups_id)
        self.can_upload = not self.env.user.share and (not self.upload_group_ids or bool(self.upload_group_ids & self.env.user.groups_id))

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
        if self.visibility == 'public':
            self.group_ids = False

    @api.model
    def create(self, vals):
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

    def list_all(self):
        return {
            'channels': [{'id': channel.id, 'name': channel.name, 'website_url': channel.website_url} for channel in self.search([])]
        }


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