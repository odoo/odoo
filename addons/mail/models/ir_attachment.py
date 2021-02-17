# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import requests

from lxml import html
from odoo import models, api
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import image_process


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _post_add_create(self):
        """ Overrides behaviour when the attachment is created through the controller
        """
        super(IrAttachment, self)._post_add_create()
        for record in self:
            record.register_as_main_attachment(force=False)

    def register_as_main_attachment(self, force=True):
        """ Registers this attachment as the main one of the model it is
        attached to.
        """
        self.ensure_one()
        if not self.res_model:
            return
        related_record = self.env[self.res_model].browse(self.res_id)
        if not related_record.check_access_rights('write', raise_exception=False):
            return
        # message_main_attachment_id field can be empty, that's why we compare to False;
        # we are just checking that it exists on the model before writing it
        if related_record and hasattr(related_record, 'message_main_attachment_id'):
            if force or not related_record.message_main_attachment_id:
                #Ignore AccessError, if you don't have access to modify the document
                #Just don't set the value
                try:
                    related_record.message_main_attachment_id = self
                except AccessError:
                    pass

    def _delete_and_notify(self):
        for attachment in self:
            if attachment.res_model == 'mail.channel':
                self.env['bus.bus'].sendone((self._cr.dbname, 'mail.channel', attachment.res_id), {
                    'type': 'mail.attachment_delete',
                    'payload': {
                        'id': attachment.id,
                    },
                })
        self.unlink()

    def _attachment_format(self, commands=False):
        safari = request and request.httprequest.user_agent and request.httprequest.user_agent.browser == 'safari'
        attachments = []
        for attachment in self:
            res = {
                'checksum': attachment.checksum,
                'description': attachment.description,
                'id': attachment.id,
                'filename': attachment.name,
                'name': attachment.name,
                'mimetype': 'application/octet-stream' if safari and attachment.mimetype and 'video' in attachment.mimetype else attachment.mimetype,
                'url': attachment.url,
            }
            if commands:
                res['originThread'] = [('insert', {
                    'id': attachment.res_id,
                    'model': attachment.res_model,
                })]
            else:
                res.update({
                    'res_id': attachment.res_id,
                    'res_model': attachment.res_model,
                })
            attachments.append(res)
        return attachments

    @api.model
    def _get_data_from_url(self, url):
        """
        This will create attachment data based on what we can read from the URL.
        If the URL is an HTML page, this will parse the OpenGraph meta data.
        If the URL is an image, this will create an image attachment.
        """
        data = {}
        request_image = None
        try:
            page = requests.get(url, timeout=1)
        except requests.exceptions.RequestException:
            return False

        if page.status_code != requests.codes.ok:
            return False
        image_mimetype = [
            'image/bmp',
            'image/gif',
            'image/jpeg',
            'image/png',
            'image/tiff',
            'image/x-icon',
        ]
        if page.headers['Content-Type'] in image_mimetype:
            image = image_process(
                base64.b64encode(page.content),
                size=(300, 300),
                verify_resolution=True
            )
            data = {
                'url': url,
                'name': url,
                'description': False,
                'datas': image,
                'mimetype': 'image/o-linkpreview-image',
                'res_model': 'mail.compose.message',
                'res_id': 0,
            }
            return data
        elif 'text/html' in page.headers['Content-Type']:
            tree = html.fromstring(page.content)
            title = tree.xpath('//meta[@property="og:title"]/@content')
            if title:
                image = tree.xpath('//meta[@property="og:image"]/@content')
                if image:
                    request_image = requests.get(image[0], timeout=1)
                    image = image_process(
                        base64.b64encode(request_image.content),
                        size=(300, 300),
                        verify_resolution=True
                    )
                description = tree.xpath('//meta[@property="og:description"]/@content')
                data = {
                    'url': url,
                    'name': title[0] if title else url,
                    'datas': image if image else False,
                    'description': description[0] if description else False,
                    'mimetype': 'application/o-linkpreview-with-thumbnail' if image else 'application/o-linkpreview',
                    'res_model': 'mail.compose.message',
                    'res_id': 0,
                }
                return data
        return False
