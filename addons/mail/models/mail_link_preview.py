# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import html
import requests
from odoo import api, models, fields
from dateutil.relativedelta import relativedelta
from datetime import datetime

class link_preview(models.Model):
    _name = 'mail.link.preview'
    _description = "Store link preview data's"

    attachment_id = fields.Many2one('ir.attachment', 'Attachement previewed', index=True, ondelete='cascade')
    type = fields.Char('type')
    url = fields.Char('url')
    title = fields.Char('title')
    image_url = fields.Char('image_url')
    description = fields.Text('description')
    image = fields.Image('Image')

    @api.model
    def get_open_graph_data(self, url):
        try:
            page = requests.get(url, timeout=10)
            if page.status_code != requests.codes.ok:
                return False
            image_mimetype = [
                'image/bmp',
                'image/gif',
                'image/jpeg',
                'image/png',
                'image/svg+xml',
                'image/tiff',
                'image/x-icon',
            ]
            if (page.headers['content-type'] in image_mimetype):
                data = {
                    'url': url,
                    'title': url,
                    'type': False,
                    'image': url,
                    'description': False
                }
                return data
            else:
                tree = html.fromstring(page.content)
                if tree.xpath('//meta[@property="og:title"]/@content'):
                    data = {
                        'url': url,
                        'title': tree.xpath('//meta[@property="og:title"]/@content')[0] if tree.xpath('//meta[@property="og:title"]/@content') else False,
                        'type': tree.xpath('//meta[@property="og:type"]/@content')[0] if tree.xpath('//meta[@property="og:type"]/@content') else False,
                        'image': tree.xpath('//meta[@property="og:image"]/@content')[0] if tree.xpath('//meta[@property="og:image"]/@content') else False,
                        'description': tree.xpath('//meta[@property="og:description"]/@content')[0] if tree.xpath('//meta[@property="og:description"]/@content') else False,
                    }
                    return data
                return False
        except requests.exceptions.RequestException:
            return False

    @api.model
    def _cron_delete_old_preview(self):
        today = fields.Date.to_string((datetime.now() + relativedelta(days=-1)))
        self.sudo().search([('create_date', '<', today)]).unlink()
        return

    def _link_preview_format(self):
        return [{
            'type': preview.type,
            'url': preview.url,
            'title': preview.title,
            'image_url': preview.image_url,
            'image': f'/mail/image/{preview.id}',
            'description': preview.description,
        } for preview in self]
