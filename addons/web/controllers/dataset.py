# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import threading

from werkzeug.exceptions import NotFound

from odoo import _, http
from odoo.exceptions import UserError
from odoo.http import request
from odoo.models import get_public_method
from odoo.service.model import call_kw

from .utils import clean_action


class DataSet(http.Controller):

    def _call_kw_readonly(self, rule, args):
        params = request.get_json_data()['params']
        try:
            model_class = request.registry[params['model']]
        except KeyError as e:
            raise NotFound() from e
        method_name = params['method']
        for cls in model_class.mro():
            method = getattr(cls, method_name, None)
            if method is not None and hasattr(method, '_readonly'):
                return method._readonly
        return False

    @http.route(['/web/dataset/call_kw', '/web/dataset/call_kw/<path:path>'], type='jsonrpc', auth="user", readonly=_call_kw_readonly)
    def call_kw(self, model, method, args, kwargs, path=None):
        if path != f'{model}.{method}':
            threading.current_thread().rpc_model_method = f'{model}.{method}'
        return call_kw(request.env[model], method, args, kwargs)

    @http.route(['/web/dataset/call_button', '/web/dataset/call_button/<path:path>'], type='jsonrpc', auth="user", readonly=_call_kw_readonly)
    def call_button(self, model, method, args, kwargs, path=None):
        if path != f'{model}.{method}':
            threading.current_thread().rpc_model_method = f'{model}.{method}'
        action = call_kw(request.env[model], method, args, kwargs)
        if isinstance(action, dict) and action.get('type') != '':  # noqa: PLC1901
            return clean_action(action, env=request.env)
        return False

    def _check_uploaded_files(self, attachments):
        if not attachments:
            raise UserError(_("No file was uploaded."))
        if empty := attachments.filtered(lambda attachment: not attachment.file_size):
            raise UserError(_("These files are empty: %s", ", ".join(empty.mapped('name'))))

    @http.route('/web/dataset/call_upload', type='http', auth="user", methods=['POST'])
    def call_upload(self, model, method, ufile=None, res_ids='[]', context='{}'):
        """ Backend of the ``<button type="upload" name="method"/>`` view button.

        Creates an unattached attachment for each uploaded file (``ufile``),
        then calls ``method`` with their ids as the ``attachment_ids``
        argument, on the records ``res_ids`` (an empty recordset if none).
        """
        if model not in request.registry:
            raise NotFound
        # a private or unknown method is refused before the files are stored
        upload_method = get_public_method(request.env[model], method)
        records = request.env[model].with_context(json.loads(context)).browse(json.loads(res_ids))
        Attachment = records.env['ir.attachment']
        attachment_ids = []
        # `ufile` holds only the first file
        for file in request.httprequest.files.getlist('ufile'):
            attachment = Attachment._upload_file(file, {
                'name': file.filename,
                'mimetype': file.content_type,
            })
            attachment._post_add_create()
            attachment_ids.append(attachment.id)
        try:
            self._check_uploaded_files(Attachment.browse(attachment_ids))
            action = upload_method(records, attachment_ids)
        except UserError as e:
            request.env.cr.rollback()
            return request.make_json_response({'error': {'message': e.args[0]}})
        if isinstance(action, dict) and action.get('type') != '':  # noqa: PLC1901
            action = clean_action(action, env=request.env)
        else:
            action = False
        return request.make_json_response({'result': action})
