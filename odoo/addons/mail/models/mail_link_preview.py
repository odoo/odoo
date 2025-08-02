# Part of Odoo. See LICENSE file for full copyright and licensing details.


from datetime import datetime
from dateutil.relativedelta import relativedelta
from lxml import html
from urllib.parse import urlparse
import re
import requests

from odoo import api, models, fields, tools
from odoo.addons.mail.tools import link_preview


class LinkPreview(models.Model):
    _name = 'mail.link.preview'
    _description = "Store link preview data"

    message_id = fields.Many2one('mail.message', string='Message', index=True, ondelete='cascade', required=True)
    source_url = fields.Char('URL', required=True)
    og_type = fields.Char('Type')
    og_title = fields.Char('Title')
    og_site_name = fields.Char('Site name')
    og_image = fields.Char('Image')
    og_description = fields.Text('Description')
    og_mimetype = fields.Char('MIME type')
    image_mimetype = fields.Char('Image MIME type')
    create_date = fields.Datetime(index=True)

    @api.model
    def _create_from_message_and_notify(self, message, request_url=None):
        if tools.is_html_empty(message.body):
            return self
        urls = set(html.fromstring(message.body).xpath('//a[not(@data-oe-model)]/@href'))
        link_previews = self.env['mail.link.preview']
        requests_session = requests.Session()
        # Some websites are blocking non browser user agent.
        requests_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0'
        })
        link_preview_values = []
        link_previews_by_url = {
            preview.source_url: preview for preview in message.sudo().link_preview_ids
        }
        ignore_pattern = (
            re.compile(f"{re.escape(request_url)}(chat|web)(/|$|#|\\?)") if request_url else None
        )
        for url in urls:
            if ignore_pattern and ignore_pattern.match(url):
                continue
            if url in link_previews_by_url:
                preview = link_previews_by_url.pop(url)
                if not preview.is_hidden:
                    link_previews += preview
                continue
            if preview := link_preview.get_link_preview_from_url(url, requests_session):
                preview['message_id'] = message.id
                link_preview_values.append(preview)
            if len(link_preview_values) > 5:
                break
        if link_preview_values:
            link_previews = self.env['mail.link.preview'].create(link_preview_values)
            self.env['bus.bus']._sendone(message._bus_notification_target(), 'mail.record/insert', {
                'LinkPreview': link_previews._link_preview_format()
            })

    def _unlink_and_notify(self):
        if not self:
            return True
        notifications = [
            (
                link_preview.message_id._bus_notification_target(),
                'mail.link.preview/delete', {'id': link_preview.id, 'message_id': link_preview.message_id.id}
            ) for link_preview in self
        ]
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
            'og_site_name': preview.og_site_name,
            'source_url': preview.source_url,
        } for preview in self]
