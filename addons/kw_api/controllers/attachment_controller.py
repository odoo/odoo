import base64
import logging

from odoo import http
from odoo.addons.http_routing.models.ir_http import slugify_one
from odoo.addons.web.controllers.main import Binary
from odoo.http import request

from .controller_base import kw_api_wrapper, KwApiError

_logger = logging.getLogger(__name__)

content_route = [
    '/kw_api/image/<string:model>/<int:img_id>/<string:field>',
    '/kw_api/image/<string:model>/<int:img_id>/<string:field>/<string:unique>',
    '/kw_api/image/<int:img_id>',
    '/kw_api/image/<int:img_id>/<string:filename>',
    '/kw_api/image/<int:img_id>-<string:unique>',
    '/kw_api/image/<int:img_id>-<string:unique>/<string:filename>',
]


class AttachmentController(http.Controller):

    @http.route(route=content_route, type='http', auth='public')
    @kw_api_wrapper(api_key=False, token=False, paginate=False,
                    get_json=False, )
    def content_image(self, kw_api, model='ir.attachment', field='datas',
                      img_id=None, **kw):
        self.check_api_key(kw_api=kw_api)
        if model == 'ir.attachment':
            domain = [('id', '=', img_id)]
        else:
            domain = [('res_id', '=', img_id), ('res_model', '=', model),
                      ('res_field', '=', field), ]
        attachment = request.env['ir.attachment'].sudo().search(
            domain, limit=1, order='create_date DESC')
        if not attachment:
            raise KwApiError('file_error', 'No file with this id')
        res = Binary.content_common(
            request, id=attachment.id, filename=attachment.name,
            filename_field='name',
            access_token=attachment.generate_access_token()[0])
        res.headers['Content-Disposition'] = \
            'attachment; %s' % slugify_one(attachment.name)
        return res

    @http.route(route='/kw_api/attachment', methods=['POST'],
                auth='public', csrf=False, type='http', )
    @kw_api_wrapper(api_key=False, token=False, paginate=False,
                    get_json=False, )
    def post_file(self, kw_api, **kw):
        self.check_api_key(kw_api=kw_api)
        file = kw_api.get_param_by_name(kw, 'file')
        name = str(file.filename)
        file = base64.b64encode(file.read())
        attachment = request.env['ir.attachment'].sudo().create({
            'name': name, 'datas': file})
        file_url = request.httprequest.host_url[:-1] + attachment.local_url
        data = {'fileUrl': file_url, 'id': attachment.id,
                'originalFileName': name, 'sizeKb': attachment.file_size, }
        return kw_api.data_response(data)

    @http.route(route='/kw_api/attachment/<int:file_id>', methods=['GET'],
                auth='public', csrf=False, type='http', )
    @kw_api_wrapper(api_key=False, token=False, paginate=False,
                    get_json=False, )
    def get_file(self, kw_api, file_id, **kw):
        self.check_api_key(kw_api=kw_api)
        attachment = request.env['ir.attachment'].sudo().search(
            [('id', '=', file_id)], limit=1)
        if not attachment.id:
            raise KwApiError(
                'file_error', 'File with FileID is missing from the system')
        file_url = request.httprequest.host_url[:-1] + attachment.local_url
        # fileUrl = '/api/'.join(fileUrl.split('/web/'))
        return kw_api.data_response(
            {'fileUrl': file_url, 'fileData': str(attachment.datas)})

    @staticmethod
    def check_api_key(kw_api):
        api_key_attachment_required = request.env['ir.config_parameter'].sudo(
        ).get_param(key='kw_api.kw_api_key_attachment_required')
        if api_key_attachment_required:
            for k, v in request.env['kw.api.key'].sudo().get_api_key().items():
                setattr(kw_api, k, v)
            if kw_api.api_key:
                kw_api.log.login = kw_api.api_key.name
            if not kw_api.allowed_api_key_ip:
                raise KwApiError(
                    'auth_error', 'No API-key were given or given wrong one '
                                  'or not allowed request source ip')
