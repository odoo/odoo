# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from PIL import Image
from urllib import urlencode
from urlparse import urlparse

import datetime
import io
import json
import re
import urllib2

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import image
from odoo.tools.translate import html_translate
from odoo.exceptions import Warning
from odoo.addons.website.models.website import slug


class Channel(models.Model):
    """ A channel is a container of slides. It has group-based access configuration
    allowing to configure slide upload and access. Slides can be promoted in
    channels. """
    _name = 'slide.channel'
    _description = 'Channel for Slides'
    _inherit = ['mail.thread', 'website.seo.metadata', 'website.published.mixin']
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
        default="<p>This channel is private and its content is restricted to some users.</p>", translate=html_translate, sanitize_attributes=False)
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
        return [('id', op, (req, (self._uid)))]

    @api.one
    @api.depends('visibility', 'group_ids', 'upload_group_ids')
    def _compute_access(self):
        self.can_see = self.visibility in ['public', 'private'] or bool(self.group_ids & self.env.user.groups_id)
        self.can_see_full = self.visibility == 'public' or bool(self.group_ids & self.env.user.groups_id)
        self.can_upload = self.can_see and (not self.upload_group_ids or bool(self.upload_group_ids & self.env.user.groups_id))

    @api.multi
    @api.depends('name')
    def _compute_website_url(self):
        super(Channel, self)._compute_website_url()
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for channel in self:
            if channel.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                channel.website_url = '%s/slides/%s' % (base_url, slug(channel))

    @api.onchange('visibility')
    def change_visibility(self):
        if self.visibility == 'public':
            self.group_ids = False

    @api.multi
    def write(self, vals):
        res = super(Channel, self).write(vals)
        if 'active' in vals:
            # archiving/unarchiving a channel does it on its slides, too
            self.with_context(active_test=False).mapped('slide_ids').write({'active': vals['active']})
        return res

    @api.multi
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


class EmbeddedSlide(models.Model):
    """ Embedding in third party websites. Track view count, generate statistics. """
    _name = 'slide.embed'
    _description = 'Embedded Slides View Counter'
    _rec_name = 'slide_id'

    slide_id = fields.Many2one('slide.slide', string="Presentation", required=True, index=True)
    url = fields.Char('Third Party Website URL', required=True)
    count_views = fields.Integer('# Views', default=1)

    def add_embed_url(self, slide_id, url):
        schema = urlparse(url)
        baseurl = schema.netloc
        embeds = self.search([('url', '=', baseurl), ('slide_id', '=', int(slide_id))], limit=1)
        if embeds:
            embeds.count_views += 1
        else:
            embeds = self.create({
                'slide_id': slide_id,
                'url': baseurl,
            })
        return embeds.count_views


class SlideTag(models.Model):
    """ Tag to search slides accross channels. """
    _name = 'slide.tag'
    _description = 'Slide Tag'

    name = fields.Char('Name', required=True, translate=True)

    _sql_constraints = [
        ('slide_tag_unique', 'UNIQUE(name)', 'A tag must be unique!'),
    ]


class Slide(models.Model):
    """ This model represents actual presentations. Those must be one of four
    types:

     - Presentation
     - Document
     - Infographic
     - Video

    Slide has various statistics like view count, embed count, like, dislikes """

    _name = 'slide.slide'
    _inherit = ['mail.thread', 'website.seo.metadata', 'website.published.mixin']
    _description = 'Slides'

    _PROMOTIONAL_FIELDS = [
        '__last_update', 'name', 'image_thumb', 'image_medium', 'slide_type', 'total_views', 'category_id',
        'channel_id', 'description', 'tag_ids', 'write_date', 'create_date',
        'website_published', 'website_url', 'website_meta_title', 'website_meta_description', 'website_meta_keywords']

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(channel_id, name)', 'The slide name must be unique within a channel')
    ]

    # description
    name = fields.Char('Title', required=True, translate=True)
    active = fields.Boolean(default=True)
    description = fields.Text('Description', translate=True)
    channel_id = fields.Many2one('slide.channel', string="Channel", required=True)
    category_id = fields.Many2one('slide.category', string="Category", domain="[('channel_id', '=', channel_id)]")
    tag_ids = fields.Many2many('slide.tag', 'rel_slide_tag', 'slide_id', 'tag_id', string='Tags')
    download_security = fields.Selection(
        [('none', 'No One'), ('user', 'Authentified Users Only'), ('public', 'Everyone')],
        string='Download Security',
        required=True, default='user')
    image = fields.Binary('Image', attachment=True)
    image_medium = fields.Binary('Medium', compute="_get_image", store=True, attachment=True)
    image_thumb = fields.Binary('Thumbnail', compute="_get_image", store=True, attachment=True)

    @api.depends('image')
    def _get_image(self):
        for record in self:
            if record.image:
                record.image_medium = image.crop_image(record.image, type='top', ratio=(4, 3), thumbnail_ratio=4)
                record.image_thumb = image.crop_image(record.image, type='top', ratio=(4, 3), thumbnail_ratio=6)
            else:
                record.image_medium = False
                record.iamge_thumb = False

    # content
    slide_type = fields.Selection([
        ('infographic', 'Infographic'),
        ('presentation', 'Presentation'),
        ('document', 'Document'),
        ('video', 'Video')],
        string='Type', required=True,
        default='document',
        help="The document type will be set automatically based on the document URL and properties (e.g. height and width for presentation and document).")
    index_content = fields.Text('Transcript')
    datas = fields.Binary('Content', attachment=True)
    url = fields.Char('Document URL', help="Youtube or Google Document URL")
    document_id = fields.Char('Document ID', help="Youtube or Google Document ID")
    mime_type = fields.Char('Mime-type')

    @api.onchange('url')
    def on_change_url(self):
        self.ensure_one()
        if self.url:
            res = self._parse_document_url(self.url)
            if res.get('error'):
                raise Warning(_('Could not fetch data from url. Document or access right not available:\n%s') % res['error'])
            values = res['values']
            if not values.get('document_id'):
                raise Warning(_('Please enter valid Youtube or Google Doc URL'))
            for key, value in values.iteritems():
                setattr(self, key, value)

    # website
    date_published = fields.Datetime('Publish Date')
    website_message_ids = fields.One2many(
        'mail.message', 'res_id',
        domain=lambda self: [('model', '=', self._name), ('message_type', '=', 'comment')],
        string='Website Messages', help="Website communication history")
    likes = fields.Integer('Likes')
    dislikes = fields.Integer('Dislikes')
    # views
    embedcount_ids = fields.One2many('slide.embed', 'slide_id', string="Embed Count")
    slide_views = fields.Integer('# of Website Views')
    embed_views = fields.Integer('# of Embedded Views')
    total_views = fields.Integer("Total # Views", default="0", compute='_compute_total', store=True)

    @api.depends('slide_views', 'embed_views')
    def _compute_total(self):
        for record in self:
            record.total_views = record.slide_views + record.embed_views

    embed_code = fields.Text('Embed Code', readonly=True, compute='_get_embed_code')

    def _get_embed_code(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for record in self:
            if record.datas and (not record.document_id or record.slide_type in ['document', 'presentation']):
                record.embed_code = '<iframe src="%s/slides/embed/%s?page=1" allowFullScreen="true" height="%s" width="%s" frameborder="0"></iframe>' % (base_url, record.id, 315, 420)
            elif record.slide_type == 'video' and record.document_id:
                if not record.mime_type:
                    # embed youtube video
                    record.embed_code = '<iframe src="//www.youtube.com/embed/%s?theme=light" allowFullScreen="true" frameborder="0"></iframe>' % (record.document_id)
                else:
                    # embed google doc video
                    record.embed_code = '<embed src="https://video.google.com/get_player?ps=docs&partnerid=30&docid=%s" type="application/x-shockwave-flash"></embed>' % (record.document_id)
            else:
                record.embed_code = False

    @api.multi
    @api.depends('name')
    def _compute_website_url(self):
        super(Slide, self)._compute_website_url()
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for slide in self:
            if slide.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                # link_tracker is not in dependencies, so use it to shorten url only if installed.
                if self.env.registry.get('link.tracker'):
                    url = self.env['link.tracker'].sudo().create({'url': '%s/slides/slide/%s' % (base_url, slug(slide))}).short_url
                else:
                    url = '%s/slides/slide/%s' % (base_url, slug(slide))
                slide.website_url = url

    @api.model
    def create(self, values):
        if not values.get('index_content'):
            values['index_content'] = values.get('description')
        if values.get('slide_type') == 'infographic' and not values.get('image'):
            values['image'] = values['datas']
        if values.get('website_published') and not values.get('date_published'):
            values['date_published'] = datetime.datetime.now()
        if values.get('url'):
            doc_data = self._parse_document_url(values['url']).get('values', dict())
            for key, value in doc_data.iteritems():
                values.setdefault(key, value)
        # Do not publish slide if user has not publisher rights
        if not self.user_has_groups('website.group_website_publisher'):
            values['website_published'] = False
        slide = super(Slide, self).create(values)
        slide.channel_id.message_subscribe_users()
        slide._post_publication()
        return slide

    @api.multi
    def write(self, values):
        if values.get('url'):
            doc_data = self._parse_document_url(values['url']).get('values', dict())
            for key, value in doc_data.iteritems():
                values.setdefault(key, value)
        if values.get('channel_id'):
            custom_channels = self.env['slide.channel'].search([('custom_slide_id', '=', self.id), ('id', '!=', values.get('channel_id'))])
            custom_channels.write({'custom_slide_id': False})
        res = super(Slide, self).write(values)
        if values.get('website_published'):
            self.date_published = datetime.datetime.now()
            self._post_publication()
        return res

    @api.model
    def check_field_access_rights(self, operation, fields):
        """ As per channel access configuration (visibility)
         - public  ==> no restriction on slides access
         - private ==> restrict all slides of channel based on access group defined on channel group_ids field
         - partial ==> show channel, but presentations based on groups means any user can see channel but not slide's content.
        For private: implement using record rule
        For partial: user can see channel, but channel gridview have slide detail so we have to implement
        partial field access mechanism for public user so he can have access of promotional field (name, view_count) of slides,
        but not all fields like data (actual pdf content)
        all fields should be accessible only for user group defined on channel group_ids
        """
        if self.env.uid == SUPERUSER_ID:
            return fields or list(self._fields)
        fields = super(Slide, self).check_field_access_rights(operation, fields)
        # still read not perform so we can not access self.channel_id
        if self.ids:
            self.env.cr.execute('SELECT DISTINCT channel_id FROM ' + self._table + ' WHERE id IN %s', (tuple(self.ids),))
            channel_ids = [x[0] for x in self.env.cr.fetchall()]
            channels = self.env['slide.channel'].sudo().browse(channel_ids)
            limited_access = all(channel.visibility == 'partial' and
                                 not len(channel.group_ids & self.env.user.groups_id)
                                 for channel in channels)
            if limited_access:
                fields = [field for field in fields if field in self._PROMOTIONAL_FIELDS]
        return fields

    @api.multi
    def get_access_action(self):
        """ Instead of the classic form view, redirect to website if it is published. """
        self.ensure_one()
        if self.website_published:
            return {
                'type': 'ir.actions.act_url',
                'url': '%s' % self.website_url,
                'target': 'self',
                'res_id': self.id,
            }
        return super(Slide, self).get_access_action()

    @api.multi
    def _notification_recipients(self, message, groups):
        groups = super(Slide, self)._notification_recipients(message, groups)

        self.ensure_one()
        if self.website_published:
            for group_name, group_method, group_data in groups:
                group_data['has_button_access'] = True

        return groups

    def get_related_slides(self, limit=20):
        domain = [('website_published', '=', True), ('channel_id.visibility', '!=', 'private'), ('id', '!=', self.id)]
        if self.category_id:
            domain += [('category_id', '=', self.category_id.id)]
        for record in self.search(domain, limit=limit):
            yield record

    def get_most_viewed_slides(self, limit=20):
        for record in self.search([('website_published', '=', True), ('channel_id.visibility', '!=', 'private'), ('id', '!=', self.id)], limit=limit, order='total_views desc'):
            yield record

    def _post_publication(self):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        for slide in self.filtered(lambda slide: slide.website_published and slide.channel_id.publish_template_id):
            publish_template = slide.channel_id.publish_template_id
            html_body = publish_template.with_context(base_url=base_url).render_template(publish_template.body_html, 'slide.slide', slide.id)
            subject = publish_template.render_template(publish_template.subject, 'slide.slide', slide.id)
            slide.channel_id.message_post(
                subject=subject,
                body=html_body,
                subtype='website_slides.mt_channel_slide_published')
        return True

    @api.one
    def send_share_email(self, email):
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        return self.channel_id.share_template_id.with_context(email=email, base_url=base_url).send_mail(self.id)

    # --------------------------------------------------
    # Parsing methods
    # --------------------------------------------------

    @api.model
    def _fetch_data(self, base_url, data, content_type=False, extra_params=False):
        result = {'values': dict()}
        try:
            if data:
                sep = '?' if not extra_params else '&'
                base_url = base_url + '%s%s' % (sep, urlencode(data))
            req = urllib2.Request(base_url)
            content = urllib2.urlopen(req).read()
            if content_type == 'json':
                result['values'] = json.loads(content)
            elif content_type in ('image', 'pdf'):
                result['values'] = content.encode('base64')
            else:
                result['values'] = content
        except urllib2.HTTPError as e:
            result['error'] = e.read()
            e.close()
        except urllib2.URLError as e:
            result['error'] = e.reason
        return result

    def _find_document_data_from_url(self, url):
        expr = re.compile(r'^.*((youtu.be/)|(v/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#\&\?]*).*')
        arg = expr.match(url)
        document_id = arg and arg.group(7) or False
        if document_id:
            return ('youtube', document_id)

        expr = re.compile(r'(^https:\/\/docs.google.com|^https:\/\/drive.google.com).*\/d\/([^\/]*)')
        arg = expr.match(url)
        document_id = arg and arg.group(2) or False
        if document_id:
            return ('google', document_id)

        return (None, False)

    def _parse_document_url(self, url, only_preview_fields=False):
        document_source, document_id = self._find_document_data_from_url(url)
        if document_source and hasattr(self, '_parse_%s_document' % document_source):
            return getattr(self, '_parse_%s_document' % document_source)(document_id, only_preview_fields)
        return {'error': _('Unknown document')}

    def _parse_youtube_document(self, document_id, only_preview_fields):
        key = self.env['ir.config_parameter'].sudo().get_param('website_slides.google_app_key')
        fetch_res = self._fetch_data('https://www.googleapis.com/youtube/v3/videos', {'id': document_id, 'key': key, 'part': 'snippet', 'fields': 'items(id,snippet)'}, 'json')
        if fetch_res.get('error'):
            return fetch_res

        values = {'slide_type': 'video', 'document_id': document_id}
        items = fetch_res['values'].get('items')
        if not items:
            return {'error': _('Please enter valid Youtube or Google Doc URL')}
        youtube_values = items[0]
        if youtube_values.get('snippet'):
            snippet = youtube_values['snippet']
            if only_preview_fields:
                values.update({
                    'url_src': snippet['thumbnails']['high']['url'],
                    'title': snippet['title'],
                    'description': snippet['description']
                })
                return values
            values.update({
                'name': snippet['title'],
                'image': self._fetch_data(snippet['thumbnails']['high']['url'], {}, 'image')['values'],
                'description': snippet['description'],
            })
        return {'values': values}

    @api.model
    def _parse_google_document(self, document_id, only_preview_fields):
        def get_slide_type(vals):
            # TDE FIXME: WTF ??
            slide_type = 'presentation'
            if vals.get('image'):
                image = Image.open(io.BytesIO(vals['image'].decode('base64')))
                width, height = image.size
                if height > width:
                    return 'document'
            return slide_type

        # Google drive doesn't use a simple API key to access the data, but requires an access
        # token. However, this token is generated in module google_drive, which is not in the
        # dependencies of website_slides. We still keep the 'key' parameter just in case, but that
        # is probably useless.
        params = {}
        params['projection'] = 'BASIC'
        if 'google.drive.config' in self.env:
            access_token = self.env['google.drive.config'].get_access_token()
            if access_token:
                params['access_token'] = access_token
        if not params.get('access_token'):
            params['key'] = self.env['ir.config_parameter'].sudo().get_param('website_slides.google_app_key')

        fetch_res = self._fetch_data('https://www.googleapis.com/drive/v2/files/%s' % document_id, params, "json")
        if fetch_res.get('error'):
            return fetch_res

        google_values = fetch_res['values']
        if only_preview_fields:
            return {
                'url_src': google_values['thumbnailLink'],
                'title': google_values['title'],
            }

        values = {
            'name': google_values['title'],
            'image': self._fetch_data(google_values['thumbnailLink'].replace('=s220', ''), {}, 'image')['values'],
            'mime_type': google_values['mimeType'],
            'document_id': document_id,
        }
        if google_values['mimeType'].startswith('video/'):
            values['slide_type'] = 'video'
        elif google_values['mimeType'].startswith('image/'):
            values['datas'] = values['image']
            values['slide_type'] = 'infographic'
        elif google_values['mimeType'].startswith('application/vnd.google-apps'):
            values['slide_type'] = get_slide_type(values)
            if 'exportLinks' in google_values:
                values['datas'] = self._fetch_data(google_values['exportLinks']['application/pdf'], params, 'pdf', extra_params=True)['values']
                # Content indexing
                if google_values['exportLinks'].get('text/plain'):
                    values['index_content'] = self._fetch_data(google_values['exportLinks']['text/plain'], params, extra_params=True)['values']
                elif google_values['exportLinks'].get('text/csv'):
                    values['index_content'] = self._fetch_data(google_values['exportLinks']['text/csv'], params, extra_params=True)['values']
        elif google_values['mimeType'] == 'application/pdf':
            # TODO: Google Drive PDF document doesn't provide plain text transcript
            values['datas'] = self._fetch_data(google_values['webContentLink'], {}, 'pdf')['values']
            values['slide_type'] = get_slide_type(values)

        return {'values': values}
