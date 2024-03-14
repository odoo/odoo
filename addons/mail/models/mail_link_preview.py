# Part of Odoo. See LICENSE file for full copyright and licensing details.


from datetime import datetime
from dateutil.relativedelta import relativedelta
from lxml import html, etree
from urllib.parse import urlparse
import requests

from odoo import api, models, fields


class LinkPreview(models.Model):
    _name = 'mail.link.preview'
    _description = "Store link preview data"

    message_id = fields.Many2one('mail.message', string='Message', index=True, ondelete='cascade', required=True)
    source_url = fields.Char('URL', required=True)
    og_type = fields.Char('Type')
    og_title = fields.Char('Title')
    og_image = fields.Char('Image')
    og_description = fields.Text('Description')
    og_mimetype = fields.Char('MIME type')
    image_mimetype = fields.Char('Image MIME type')
    create_date = fields.Datetime(index=True)

    @api.model
    def _create_link_previews(self, message):
        if not message.body:
            return
        tree = html.fromstring(message.body)
        urls = tree.xpath('//a[not(@data-oe-model)]/@href')
        link_previews = self.env['mail.link.preview']
        requests_session = requests.Session()
        # Some websites are blocking non browser user agent.
        requests_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'
        })
        for url in set(urls):
            if len(link_previews) >= 5:
                break
            link_previews |= self.env['mail.link.preview']._create_link_preview(url, message.id, requests_session)
        if not link_previews:
            return
        guest = self.env['mail.guest']._get_guest_from_context()
        if message.model == 'mail.channel' and message.res_id:
            target = self.env['mail.channel'].browse(message.res_id)
        elif self.env.user._is_public() and guest:
            target = guest
        else:
            target = self.env.user.partner_id
        self.env['bus.bus']._sendmany([(target, 'mail.link.preview/insert', link_previews._link_preview_format())])

    @api.model
    def _create_link_preview(self, url, message_id, request_session):
        if self._is_domain_throttled(url):
            return self.env['mail.link.preview']
        link_preview_data = self._get_link_preview_from_url(url, request_session)
        if link_preview_data:
            link_preview_data['message_id'] = message_id
            return self.create(link_preview_data)
        return self.env['mail.link.preview']

    def _delete_and_notify(self):
        notifications = []
        guest = self.env['mail.guest']._get_guest_from_context()
        for link_preview in self:
            if link_preview.message_id.model == 'mail.channel' and link_preview.message_id.res_id:
                target = self.env['mail.channel'].browse(link_preview.message_id.res_id)
            elif self.env.user._is_public() and guest:
                target = guest
            else:
                target = self.env.user.partner_id
            notifications.append((target, 'mail.link.preview/delete', {'id': link_preview.id}))
        self.env['bus.bus']._sendmany(notifications)
        self.unlink()

    @api.model
    def _is_link_preview_enabled(self):
        link_preview_throttle = int(self.env['ir.config_parameter'].sudo().get_param('mail.link_preview_throttle', 99))
        return link_preview_throttle > 0

    @api.model
    def _is_domain_throttled(self, url):
        domain = urlparse(url).netloc
        date_interval = fields.Datetime.to_string((datetime.now() - relativedelta(seconds=10)))
        call_counter = self.search_count([
            ('source_url', 'ilike', domain),
            ('create_date', '>', date_interval),
        ])
        link_preview_throttle = int(self.env['ir.config_parameter'].get_param('mail.link_preview_throttle', 99))
        return call_counter > link_preview_throttle

    @api.model
    def _get_link_preview_from_url(self, url, request_session):
        try:
            response = request_session.head(url, timeout=3, allow_redirects=True)
        except requests.exceptions.RequestException:
            return False
        if response.status_code != requests.codes.ok:
            return False
        image_mimetype = (
            'image/bmp',
            'image/gif',
            'image/jpeg',
            'image/png',
            'image/tiff',
            'image/x-icon',
        )
        if not response.headers.get('Content-Type'):
            return False
        # Content-Type header can return a charset, but we just need the
        # mimetype (eg: image/jpeg;charset=ISO-8859-1)
        content_type = response.headers['Content-Type'].split(';')
        if response.headers['Content-Type'].startswith(image_mimetype):
            return {
                'image_mimetype': content_type[0],
                'source_url': url,
            }
        if response.headers['Content-Type'].startswith('text/html'):
            return self._get_link_preview_from_html(url, request_session)
        return False

    def _get_link_preview_from_html(self, url, request_session):
        response = request_session.get(url, timeout=3)
        parser = etree.HTMLParser(encoding=response.encoding)
        tree = html.fromstring(response.content, parser=parser)
        og_title = tree.xpath('//meta[@property="og:title"]/@content')
        if not og_title:
            return False
        og_description = tree.xpath('//meta[@property="og:description"]/@content')
        og_type = tree.xpath('//meta[@property="og:type"]/@content')
        og_image = tree.xpath('//meta[@property="og:image"]/@content')
        og_mimetype = tree.xpath('//meta[@property="og:image:type"]/@content')
        return {
            'og_description': og_description[0] if og_description else None,
            'og_image': og_image[0] if og_image else None,
            'og_mimetype': og_mimetype[0] if og_mimetype else None,
            'og_title': og_title[0],
            'og_type': og_type[0] if og_type else None,
            'source_url': url,
        }

    def _link_preview_format(self):
        return [{
            'id': preview.id,
            'message': {'id': preview.message_id.id},
            'image_mimetype': preview.image_mimetype,
            'og_description': preview.og_description,
            'og_image': preview.og_image,
            'og_mimetype': preview.og_mimetype,
            'og_title': preview.og_title,
            'og_type': preview.og_type,
            'source_url': preview.source_url,
        } for preview in self]
