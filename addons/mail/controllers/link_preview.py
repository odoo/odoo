import base64
import requests

from odoo import http, _
from odoo.addons.web.controllers.main import Binary
from odoo.http import request
from odoo.exceptions import AccessError


class LinkPreviewController(Binary):
    @http.route('/mail/link_preview', type='json', auth='user')
    def link_preview(self, url):
        open_graph_data = request.env['mail.link.preview'].get_open_graph_data(url)
        if open_graph_data:
            attachment = request.env['ir.attachment'].sudo().create({
                'name': open_graph_data.get('url'),
                'url': open_graph_data.get('url'),
                'res_model': 'mail.compose.message',
            })
            request_image = None
            if open_graph_data.get('image'):
                image = open_graph_data.get('image')
                request_image = requests.get(image, timeout=10)
            request.env['mail.link.preview'].sudo().create({
                'attachment_id': attachment.id,
                'type': open_graph_data.get('type'),
                'url': open_graph_data.get('url'),
                'title': open_graph_data.get('title'),
                'image_url': open_graph_data.get('image'),
                'image': base64.b64encode(request_image.content) if request_image else False,
                'description': open_graph_data.get('description'),
            })
            return attachment._attachment_format()[0]
        return False

    @http.route('/mail/image/<int:res_id>', type='http', auth="public")
    def preview_image(self, res_id):
        return self._preview_content_image(res_id, model='mail.link.preview', field='image')

    def _preview_content_image(self, res_id, model='ir.attachment', field='datas',
                               filename_field='name', unique=None, filename=None, mimetype=None,
                               download=None, width=0, height=0, crop=False, quality=0, access_token=None, **kwargs):
        attachment = request.env[model].sudo().browse(res_id).attachment_id
        if attachment.res_model != "mail.compose.message":
            thread = request.env[attachment.res_model].browse(attachment.res_id)
            thread.check_access_rights('read')
            thread.check_access_rule('read')
        elif attachment.create_uid.id != request.env.user.id:
            raise AccessError(_("You are not allowed to access '%(document_kind)s' (%(document_model)s) records.", document_kind="link preview", document_model="mail.link.preview"))

        status, headers, image_base64 = request.env['ir.http'].sudo().binary_content(
            model=model, id=res_id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype,
            default_mimetype='image/png', access_token=access_token)

        return self._content_image_get_response(
            status, headers, image_base64, model=model, id=res_id, field=field, download=download,
            width=width, height=height, crop=crop, quality=quality)
