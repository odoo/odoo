# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import requests

from datetime import timedelta
from lxml import html

from odoo import api, models, fields, tools
from odoo.tools.misc import OrderedSet
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tools.link_preview import get_link_preview_from_url


class LinkPreview(models.Model):
    _name = 'mail.link.preview'
    _inherit = "bus.listener.mixin"
    _description = "Store link preview data"

    message_id = fields.Many2one('mail.message', string='Message', index=True, ondelete='cascade')
    is_hidden = fields.Boolean()
    source_url = fields.Char('URL', required=True)
    og_type = fields.Char('Type')
    og_title = fields.Char('Title')
    og_site_name = fields.Char('Site name')
    og_image = fields.Char('Image')
    og_description = fields.Text('Description')
    og_mimetype = fields.Char('MIME type')
    image_mimetype = fields.Char('Image MIME type')
    create_date = fields.Datetime(index=True)

    def _bus_channel(self):
        return self.message_id._bus_channel()

    @api.model
    def _create_from_message_and_notify(self, message, request_url=None):
        if tools.is_html_empty(message.body):
            return self
        urls = OrderedSet(html.fromstring(message.body).xpath('//a[not(@data-oe-model)]/@href'))
        link_previews = self.env['mail.link.preview']
        requests_session = requests.Session()
        link_preview_values = []
        link_previews_by_url = {
            preview.source_url: preview for preview in message.sudo().link_preview_ids
        }
        ignore_pattern = (
            re.compile(f"{re.escape(request_url)}(odoo|web|chat)(/|$|#|\\?)") if request_url else None
        )
        for url in urls:
            if ignore_pattern and ignore_pattern.match(url):
                continue
            if url in link_previews_by_url:
                preview = link_previews_by_url.pop(url)
                if not preview.is_hidden:
                    link_previews += preview
                continue
            if preview := get_link_preview_from_url(url, requests_session):
                preview['message_id'] = message.id
                link_preview_values.append(preview)
            if len(link_preview_values) + len(link_previews) > 5:
                break
        for unused_preview in link_previews_by_url.values():
            unused_preview._unlink_and_notify()
        if link_preview_values:
            link_previews += link_previews.create(link_preview_values)
        if link_previews := link_previews.sorted(key=lambda p: list(urls).index(p.source_url)):
            message._bus_send_store(message, {"linkPreviews": Store.many(link_previews)})

    def _hide_and_notify(self):
        if not self:
            return True
        for link_preview in self:
            link_preview._bus_send_store(
                link_preview.message_id,
                {"linkPreviews": Store.many(link_preview, "DELETE", only_id=True)},
            )
        self.is_hidden = True

    def _unlink_and_notify(self):
        if not self:
            return True
        for link_preview in self:
            link_preview._bus_send_store(
                link_preview.message_id,
                {"linkPreviews": Store.many(link_preview, "DELETE", only_id=True)},
            )
        self.unlink()

    @api.model
    def _is_link_preview_enabled(self):
        link_preview_throttle = int(self.env['ir.config_parameter'].sudo().get_param('mail.link_preview_throttle', 99))
        return link_preview_throttle > 0

    @api.model
    def _search_or_create_from_url(self, url):
        """Return the URL preview, first from the database if available otherwise make the request."""
        lifetime = int(self.env['ir.config_parameter'].sudo().get_param('mail.mail_link_preview_lifetime_days', 3))
        preview = self.env['mail.link.preview'].search([
            ('source_url', '=', url),
            ('create_date', '>=', fields.Datetime.now() - timedelta(days=lifetime)),
        ], order='create_date DESC', limit=1)
        if not preview:
            preview_values = get_link_preview_from_url(url)
            if not preview_values:
                return self.env["mail.link.preview"]
            preview = self.env['mail.link.preview'].create(preview_values)
        return preview

    def _to_store(self, store: Store, /):
        for preview in self:
            data = preview._read_format(
                [
                    "image_mimetype",
                    "og_description",
                    "og_image",
                    "og_mimetype",
                    "og_site_name",
                    "og_title",
                    "og_type",
                    "source_url",
                ],
                load=False,
            )[0]
            data["message"] = Store.one(preview.message_id, only_id=True)
            store.add(preview, data)

    @api.autovacuum
    def _gc_mail_link_preview(self):
        lifetime = int(self.env['ir.config_parameter'].sudo().get_param('mail.mail_link_preview_lifetime_days', 3))
        self.env['mail.link.preview'].search([
            ('message_id', '=', False),
            ('create_date', '<', fields.Datetime.now() - timedelta(days=lifetime)),
        ], order='create_date ASC', limit=1000).unlink()
