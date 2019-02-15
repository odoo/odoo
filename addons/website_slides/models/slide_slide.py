# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import requests
from PIL import Image

import base64
import datetime
import io
import re
import uuid

from werkzeug import urls

from odoo import api, fields, models, tools, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.exceptions import Warning, UserError
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import url_for


class SlidePartnerRelation(models.Model):
    _name = 'slide.slide.partner'
    _description = 'Slide / Partner decorated m2m'
    _table = 'slide_slide_partner'

    slide_id = fields.Many2one('slide.slide', index=True, required=True)
    channel_id = fields.Many2one('slide.channel', string="Channel", related="slide_id.channel_id", store=True, index=True)
    partner_id = fields.Many2one('res.partner', index=True, required=True)
    vote = fields.Integer('Vote', default=0)
    completed = fields.Boolean('Completed')


class SlideLink(models.Model):
    _name = 'slide.slide.link'
    _description = "External URL for a particular slide"

    slide_id = fields.Many2one('slide.slide', required=True)
    name = fields.Char('Title', required=True)
    link = fields.Char("External Link", required=True)


class EmbeddedSlide(models.Model):
    """ Embedding in third party websites. Track view count, generate statistics. """
    _name = 'slide.embed'
    _description = 'Embedded Slides View Counter'
    _rec_name = 'slide_id'

    slide_id = fields.Many2one('slide.slide', string="Presentation", required=True, index=True)
    url = fields.Char('Third Party Website URL', required=True)
    count_views = fields.Integer('# Views', default=1)

    def add_embed_url(self, slide_id, url):
        baseurl = urls.url_parse(url).netloc
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
     - Webpage

    Slide has various statistics like view count, embed count, like, dislikes """

    _name = 'slide.slide'
    _inherit = ['mail.thread', 'website.seo.metadata', 'website.published.mixin', 'rating.mixin']
    _description = 'Slides'
    _mail_post_access = 'read'
    _order_by_strategy = {
        'most_viewed': 'total_views desc',
        'most_voted': 'likes desc',
        'latest': 'date_published desc',
    }

    _sql_constraints = [
        ('exclusion_html_content_and_url', "CHECK(html_content IS NULL OR url IS NULL)", "A slide is either filled with a document url or HTML content. Not both.")
    ]

    def _default_access_token(self):
        return str(uuid.uuid4())

    # description
    name = fields.Char('Title', required=True, translate=True)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', string='Uploaded by', default=lambda self: self.env.uid)
    description = fields.Text('Description', translate=True)
    channel_id = fields.Many2one('slide.channel', string="Channel", required=True)
    category_id = fields.Many2one('slide.category', string="Category", domain="[('channel_id', '=', channel_id)]")
    tag_ids = fields.Many2many('slide.tag', 'rel_slide_tag', 'slide_id', 'tag_id', string='Tags')
    download_security = fields.Selection(
        [('none', 'No One'), ('user', 'Authenticated Users Only'), ('public', 'Everyone')],
        string='Download Security',
        required=True, default='user')
    access_token = fields.Char("Security Token", copy=False, default=_default_access_token)
    is_preview = fields.Boolean('Always visible', default=False)
    completion_time = fields.Float('# Hours', default=1, digits=(10, 4))
    image = fields.Binary("Image", attachment=True)
    image_large = fields.Binary("Large image", attachment=True)
    image_medium = fields.Binary("Medium image", attachment=True)
    image_small = fields.Binary("Small image", attachment=True)
    # subscribers
    partner_ids = fields.Many2many('res.partner', 'slide_slide_partner', 'slide_id', 'partner_id',
                                   string='Subscribers', groups='base.group_website_publisher')
    slide_partner_ids = fields.One2many('slide.slide.partner', 'slide_id', string='Subscribers information', groups='base.group_website_publisher')
    user_membership_id = fields.Many2one('slide.slide.partner', string="Subscriber information", compute='_compute_user_membership_id',
        help="Subscriber information for the current logged in user")
    # content
    slide_type = fields.Selection([
        ('infographic', 'Infographic'),
        ('presentation', 'Presentation'),
        ('document', 'Document'),
        ('webpage', 'Web Page'),
        ('video', 'Video')],
        string='Type', required=True,
        default='document', readonly=True,
        help="The document type will be set automatically based on the document URL and properties (e.g. height and width for presentation and document).")
    index_content = fields.Text('Transcript')
    datas = fields.Binary('Content', attachment=True)
    url = fields.Char('Document URL', help="Youtube or Google Document URL")
    document_id = fields.Char('Document ID', help="Youtube or Google Document ID")
    link_ids = fields.One2many('slide.slide.link', 'slide_id', string="External URL for this slide")
    mime_type = fields.Char('Mime-type')
    html_content = fields.Html("HTML Content", help="Custom HTML content for slides of type 'Web Page'.", translate=True)
    # website
    website_id = fields.Many2one(related='channel_id.website_id', readonly=True)
    date_published = fields.Datetime('Publish Date')
    likes = fields.Integer('Likes', compute='_compute_user_info', store=True)
    dislikes = fields.Integer('Dislikes', compute='_compute_user_info', store=True)
    user_vote = fields.Integer('User vote', compute='_compute_user_info')
    embed_code = fields.Text('Embed Code', readonly=True, compute='_get_embed_code')
    # views
    embedcount_ids = fields.One2many('slide.embed', 'slide_id', string="Embed Count")
    slide_views = fields.Integer('# of Website Views', store=True, compute="_compute_slide_views")
    public_views = fields.Integer('# of Public Views')
    total_views = fields.Integer("Total # Views", default="0", compute='_compute_total', store=True)

    @api.depends('slide_views', 'public_views')
    def _compute_total(self):
        for record in self:
            record.total_views = record.slide_views + record.public_views

    @api.depends('slide_partner_ids.vote')
    def _compute_user_info(self):
        slide_data = dict.fromkeys(self.ids, dict({'likes': 0, 'dislikes': 0, 'user_vote': False}))
        slide_partners = self.env['slide.slide.partner'].sudo().search([
            ('slide_id', 'in', self.ids)
        ])
        for slide_partner in slide_partners:
            if slide_partner.vote == 1:
                slide_data[slide_partner.slide_id.id]['likes'] += 1
                if slide_partner.partner_id == self.env.user.partner_id:
                    slide_data[slide_partner.slide_id.id]['user_vote'] = 1
            elif slide_partner.vote == -1:
                slide_data[slide_partner.slide_id.id]['dislikes'] += 1
                if slide_partner.partner_id == self.env.user.partner_id:
                    slide_data[slide_partner.slide_id.id]['user_vote'] = -1
        for slide_sudo in self.sudo():
            slide_sudo.update(slide_data[slide_sudo.id])

    @api.depends('slide_partner_ids.slide_id')
    def _compute_slide_views(self):
        # TODO awa: tried compute_sudo, for some reason it doesn't work in here...
        read_group_res = self.env['slide.slide.partner'].sudo().read_group(
            [('slide_id', 'in', self.ids)],
            ['slide_id'],
            groupby=['slide_id']
        )
        mapped_data = dict((res['slide_id'][0], res['slide_id_count']) for res in read_group_res)
        for slide in self:
            slide.slide_views = mapped_data.get(slide.id, 0)

    @api.depends('slide_partner_ids.partner_id')
    def _compute_user_membership_id(self):
        slide_partners = self.env['slide.slide.partner'].sudo().search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', self.env.user.partner_id.id),
        ])

        for record in self:
            record.user_membership_id = next(
                (slide_partner for slide_partner in slide_partners if slide_partner.slide_id == record),
                self.env['slide.slide.partner']
            )

    def _get_embed_code(self):
        base_url = request and request.httprequest.url_root or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if base_url[-1] == '/':
            base_url = base_url[:-1]
        for record in self:
            if record.datas and (not record.document_id or record.slide_type in ['document', 'presentation']):
                slide_url = base_url + url_for('/slides/embed/%s?page=1' % record.id)
                record.embed_code = '<iframe src="%s" class="o_wslides_iframe_viewer" allowFullScreen="true" height="%s" width="%s" frameborder="0"></iframe>' % (slide_url, 315, 420)
            elif record.slide_type == 'video' and record.document_id:
                if not record.mime_type:
                    # embed youtube video
                    record.embed_code = '<iframe src="//www.youtube.com/embed/%s?theme=light" allowFullScreen="true" frameborder="0"></iframe>' % (record.document_id)
                else:
                    # embed google doc video
                    record.embed_code = '<iframe src="//drive.google.com/file/d/%s/preview" allowFullScreen="true" frameborder="0"></iframe>' % (record.document_id)
            else:
                record.embed_code = False

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
            for key, value in values.items():
                self[key] = value

    @api.multi
    @api.depends('name')
    def _compute_website_url(self):
        super(Slide, self)._compute_website_url()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for slide in self:
            if slide.id:  # avoid to perform a slug on a not yet saved record in case of an onchange.
                # link_tracker is not in dependencies, so use it to shorten url only if installed.
                if self.env.registry.get('link.tracker'):
                    url = self.env['link.tracker'].sudo().create({
                        'url': '%s/slides/slide/%s' % (base_url, slug(slide)),
                        'title': slide.name,
                    }).short_url
                else:
                    url = '%s/slides/slide/%s' % (base_url, slug(slide))
                slide.website_url = url

    # ---------------------------------------------------------
    # ORM Overrides
    # ---------------------------------------------------------

    @api.model
    def create(self, values):
        # Do not publish slide if user has not publisher rights
        channel = self.env['slide.channel'].browse(values['channel_id'])
        if not channel.can_publish:
            values['website_published'] = False
            values['date_published'] = False

        if not values.get('index_content'):
            values['index_content'] = values.get('description')
        if values.get('slide_type') == 'infographic' and not values.get('image'):
            values['image'] = values['datas']
        if values.get('website_published') and not values.get('date_published'):
            values['date_published'] = datetime.datetime.now()
        if values.get('url') and not values.get('document_id'):
            doc_data = self._parse_document_url(values['url']).get('values', dict())
            for key, value in doc_data.items():
                values.setdefault(key, value)

        if 'image' in values:
            tools.image_resize_images(values, return_large=True)

        slide = super(Slide, self).create(values)

        if slide.website_published:
            slide._post_publication()
        return slide

    @api.multi
    def write(self, values):
        if 'website_published' in values and any(not slide.channel_id.can_publish for slide in self):
            values.pop('website_published')

        if values.get('url') and values['url'] != self.url:
            doc_data = self._parse_document_url(values['url']).get('values', dict())
            for key, value in doc_data.items():
                values.setdefault(key, value)

        if 'image' in values:
            tools.image_resize_images(values, return_large=True)

        res = super(Slide, self).write(values)
        if values.get('website_published'):
            self.date_published = datetime.datetime.now()
            self._post_publication()
        return res

    @api.multi
    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to website if it is published. """
        self.ensure_one()
        if self.website_published:
            return {
                'type': 'ir.actions.act_url',
                'url': '%s' % self.website_url,
                'target': 'self',
                'target_type': 'public',
                'res_id': self.id,
            }
        return super(Slide, self).get_access_action(access_uid)

    # ---------------------------------------------------------
    # Business Methods
    # ---------------------------------------------------------

    @api.multi
    def _notify_get_groups(self, message, groups):
        """ Add access button to everyone if the document is active. """
        groups = super(Slide, self)._notify_get_groups(message, groups)

        if self.website_published:
            for group_name, group_method, group_data in groups:
                group_data['has_button_access'] = True

        return groups

    def get_related_slides(self, limit=20):
        domain = request.website.website_domain()
        domain += [('website_published', '=', True), ('id', '!=', self.id)]
        if self.category_id:
            domain += [('category_id', '=', self.category_id.id)]
        for record in self.search(domain, limit=limit):
            yield record

    def get_most_viewed_slides(self, limit=20):
        domain = request.website.website_domain()
        domain += [('website_published', '=', True), ('id', '!=', self.id)]
        for record in self.search(domain, limit=limit, order='total_views desc'):
            yield record

    def _post_publication(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for slide in self.filtered(lambda slide: slide.website_published and slide.channel_id.publish_template_id):
            publish_template = slide.channel_id.publish_template_id
            html_body = publish_template.with_context(base_url=base_url)._render_template(publish_template.body_html, 'slide.slide', slide.id)
            subject = publish_template._render_template(publish_template.subject, 'slide.slide', slide.id)
            slide.channel_id.with_context(mail_create_nosubscribe=True).message_post(
                subject=subject,
                body=html_body,
                subtype='website_slides.mt_channel_slide_published',
                notif_layout='mail.mail_notification_light',
            )
        return True

    def _generate_signed_token(self, partner_id):
        """ Lazy generate the acces_token and return it signed by the given partner_id
            :rtype tuple (string, int)
            :return (signed_token, partner_id)
        """
        if not self.access_token:
            self.write({'access_token': self._default_access_token()})
        return self._sign_token(partner_id)

    @api.one
    def send_share_email(self, email):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return self.channel_id.share_template_id.with_context(email=email, base_url=base_url).send_mail(self.id, notif_layout='mail.mail_notification_light')

    def action_like(self):
        self.check_access_rights('read')
        self.check_access_rule('read')
        return self._action_vote(upvote=True)

    def action_dislike(self):
        self.check_access_rights('read')
        self.check_access_rule('read')
        return self._action_vote(upvote=False)

    def _action_vote(self, upvote=True):
        """ Private implementation of voting. It does not check for any real access
        rights; public methods should grant access before calling this method.

          :param upvote: if True, is a like; if False, is a dislike
        """
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env['slide.slide.partner'].sudo()
        slide_partners = SlidePartnerSudo.search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', self.env.user.partner_id.id)
        ])
        new_slides = self_sudo - slide_partners.mapped('slide_id')

        for slide_partner in slide_partners:
            if upvote:
                new_vote = 0 if slide_partner.vote == -1 else 1
            else:
                new_vote = 0 if slide_partner.vote == 1 else -1
            slide_partner.vote = new_vote

        for new_slide in new_slides:
            new_vote = 1 if upvote else -1
            new_slide.write({
                'slide_partner_ids': [(0, 0, {'vote': new_vote, 'partner_id': self.env.user.partner_id.id})]
            })

    def action_set_viewed(self):
        if not all(slide.channel_id.is_member for slide in self):
            raise UserError(_('You cannot mark a slide as viewed if you are not among its members.'))

        return bool(self._action_set_viewed(self.env.user.partner_id))

    def _action_set_viewed(self, target_partner):
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env['slide.slide.partner'].sudo()
        existing_sudo = SlidePartnerSudo.search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', target_partner.id)
        ])

        new_slides = self_sudo - existing_sudo.mapped('slide_id')
        return SlidePartnerSudo.create([{
            'slide_id': new_slide.id,
            'channel_id': new_slide.channel_id.id,
            'partner_id': target_partner.id,
            'vote': 0} for new_slide in new_slides])

    def action_set_completed(self):
        if not all(slide.channel_id.is_member for slide in self):
            raise UserError(_('You cannot mark a slide as completed if you are not among its members.'))

        return self._action_set_completed(self.env.user.partner_id)

    def _action_set_completed(self, target_partner):
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env['slide.slide.partner'].sudo()
        existing_sudo = SlidePartnerSudo.search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', target_partner.id)
        ])
        existing_sudo.write({'completed': True})

        new_slides = self_sudo - existing_sudo.mapped('slide_id')
        SlidePartnerSudo.create([{
            'slide_id': new_slide.id,
            'channel_id': new_slide.channel_id.id,
            'partner_id': target_partner.id,
            'vote': 0,
            'completed': True} for new_slide in new_slides])

        return True

    # --------------------------------------------------
    # Parsing methods
    # --------------------------------------------------

    @api.model
    def _fetch_data(self, base_url, data, content_type=False, extra_params=False):
        result = {'values': dict()}
        try:
            response = requests.get(base_url, params=data)
            response.raise_for_status()
            if content_type == 'json':
                result['values'] = response.json()
            elif content_type in ('image', 'pdf'):
                result['values'] = base64.b64encode(response.content)
            else:
                result['values'] = response.content
        except requests.exceptions.HTTPError as e:
            result['error'] = e.response.content
        except requests.exceptions.ConnectionError as e:
            result['error'] = str(e)
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
        key = self.env['website'].get_current_website().website_slide_google_app_key
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
                'mime_type': False,
            })
        return {'values': values}

    @api.model
    def _parse_google_document(self, document_id, only_preview_fields):
        def get_slide_type(vals):
            # TDE FIXME: WTF ??
            slide_type = 'presentation'
            if vals.get('image'):
                image = Image.open(io.BytesIO(base64.b64decode(vals['image'])))
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
            params['key'] = self.env['website'].get_current_website().website_slide_google_app_key

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

    def _default_website_meta(self):
        res = super(Slide, self)._default_website_meta()
        res['default_opengraph']['og:title'] = res['default_twitter']['twitter:title'] = self.name
        res['default_opengraph']['og:description'] = res['default_twitter']['twitter:description'] = self.description
        res['default_opengraph']['og:image'] = res['default_twitter']['twitter:image'] = "/web/image/slide.slide/%s/image_small" % (self.id)
        return res
