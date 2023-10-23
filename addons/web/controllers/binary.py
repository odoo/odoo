# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import functools
import io
import json
import logging
import os
import unicodedata

try:
    from werkzeug.utils import send_file
except ImportError:
    from odoo.tools._vendor.send_file import send_file

import odoo
import odoo.modules.registry
from odoo import SUPERUSER_ID, _, http
from odoo.addons.base.models.assetsbundle import ANY_UNIQUE
from odoo.exceptions import AccessError, UserError
from odoo.http import request, Response
from odoo.tools import file_open, file_path, replace_exceptions
from odoo.tools.image import image_guess_size_from_field_name
from odoo.tools.mimetypes import guess_mimetype

_logger = logging.getLogger(__name__)

BAD_X_SENDFILE_ERROR = """\
Odoo is running with --x-sendfile but is receiving /web/filestore requests.

With --x-sendfile enabled, NGINX should be serving the
/web/filestore route, however Odoo is receiving the
request.

This usually indicates that NGINX is badly configured,
please make sure the /web/filestore location block exists
in your configuration file and that it is similar to:

    location /web/filestore {{
        internal;
        alias {data_dir}/filestore;
    }}
"""


def clean(name):
    return name.replace('\x3c', '')


class Binary(http.Controller):

    @http.route('/web/filestore/<path:_path>', type='http', auth='none')
    def content_filestore(self, _path):
        if odoo.tools.config['x_sendfile']:
            # pylint: disable=logging-format-interpolation
            _logger.error(BAD_X_SENDFILE_ERROR.format(
                data_dir=odoo.tools.config['data_dir']
            ))
        raise http.request.not_found()

    @http.route(['/web/content',
        '/web/content/<string:xmlid>',
        '/web/content/<string:xmlid>/<string:filename>',
        '/web/content/<int:id>',
        '/web/content/<int:id>/<string:filename>',
        '/web/content/<string:model>/<int:id>/<string:field>',
        '/web/content/<string:model>/<int:id>/<string:field>/<string:filename>'], type='http', auth="public")
    # pylint: disable=redefined-builtin,invalid-name
    def content_common(self, xmlid=None, model='ir.attachment', id=None, field='raw',
                       filename=None, filename_field='name', mimetype=None, unique=False,
                       download=False, access_token=None, nocache=False):
        with replace_exceptions(UserError, by=request.not_found()):
            record = request.env['ir.binary']._find_record(xmlid, model, id and int(id), access_token)
            stream = request.env['ir.binary']._get_stream_from(record, field, filename, filename_field, mimetype)
        send_file_kwargs = {'as_attachment': download}
        if unique:
            send_file_kwargs['immutable'] = True
            send_file_kwargs['max_age'] = http.STATIC_CACHE_LONG
        if nocache:
            send_file_kwargs['max_age'] = None

        res = stream.get_response(**send_file_kwargs)
        res.headers['Content-Security-Policy'] = "default-src 'none'"
        return res

    @http.route([
        '/web/assets/<string:unique>/<string:filename>'], type='http', auth="public")
    def content_assets(self, filename=None, unique=ANY_UNIQUE, nocache=False, assets_params=None):
        assets_params = assets_params or {}
        assert isinstance(assets_params, dict)
        debug_assets = unique == 'debug'
        if unique in ('any', '%'):
            unique = ANY_UNIQUE
        attachment = None
        if unique != 'debug':
            url = request.env['ir.asset']._get_asset_bundle_url(filename, unique, assets_params)
            assert not '%' in url
            domain = [
                ('public', '=', True),
                ('url', '!=', False),
                ('url', '=like', url),
                ('res_model', '=', 'ir.ui.view'),
                ('res_id', '=', 0),
                ('create_uid', '=', SUPERUSER_ID),
            ]
            attachment = request.env['ir.attachment'].sudo().search(domain, limit=1)
        if not attachment:
            # try to generate one
            try:
                bundle_name, rtl, asset_type = request.env['ir.asset']._parse_bundle_name(filename, debug_assets)
                css = asset_type == 'css'
                js = asset_type == 'js'
                bundle = request.env['ir.qweb']._get_asset_bundle(
                    bundle_name,
                    css=css,
                    js=js,
                    debug_assets=debug_assets,
                    rtl=rtl,
                    assets_params=assets_params,
                )
                # check if the version matches. If not, redirect to the last version
                if not debug_assets and unique != ANY_UNIQUE and unique != bundle.get_version(asset_type):
                    return request.redirect(bundle.get_link(asset_type))
                if css and bundle.stylesheets:
                    attachment = bundle.css()
                elif js and bundle.javascripts:
                    attachment = bundle.js()
            except ValueError as e:
                raise request.not_found() from e
        if not attachment:
            raise request.not_found()
        stream = request.env['ir.binary']._get_stream_from(attachment, 'raw', filename)
        send_file_kwargs = {'as_attachment': False}
        if unique and unique != 'debug':
            send_file_kwargs['immutable'] = True
            send_file_kwargs['max_age'] = http.STATIC_CACHE_LONG
        if nocache:
            send_file_kwargs['max_age'] = None

        return stream.get_response(**send_file_kwargs)

    @http.route(['/web/image',
        '/web/image/<string:xmlid>',
        '/web/image/<string:xmlid>/<string:filename>',
        '/web/image/<string:xmlid>/<int:width>x<int:height>',
        '/web/image/<string:xmlid>/<int:width>x<int:height>/<string:filename>',
        '/web/image/<string:model>/<int:id>/<string:field>',
        '/web/image/<string:model>/<int:id>/<string:field>/<string:filename>',
        '/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>',
        '/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>/<string:filename>',
        '/web/image/<int:id>',
        '/web/image/<int:id>/<string:filename>',
        '/web/image/<int:id>/<int:width>x<int:height>',
        '/web/image/<int:id>/<int:width>x<int:height>/<string:filename>',
        '/web/image/<int:id>-<string:unique>',
        '/web/image/<int:id>-<string:unique>/<string:filename>',
        '/web/image/<int:id>-<string:unique>/<int:width>x<int:height>',
        '/web/image/<int:id>-<string:unique>/<int:width>x<int:height>/<string:filename>'], type='http', auth="public")
    # pylint: disable=redefined-builtin,invalid-name
    def content_image(self, xmlid=None, model='ir.attachment', id=None, field='raw',
                      filename_field='name', filename=None, mimetype=None, unique=False,
                      download=False, width=0, height=0, crop=False, access_token=None,
                      nocache=False):
        try:
            record = request.env['ir.binary']._find_record(xmlid, model, id and int(id), access_token)
            stream = request.env['ir.binary']._get_image_stream_from(
                record, field, filename=filename, filename_field=filename_field,
                mimetype=mimetype, width=int(width), height=int(height), crop=crop,
            )
        except UserError as exc:
            if download:
                raise request.not_found() from exc
            # Use the ratio of the requested field_name instead of "raw"
            if (int(width), int(height)) == (0, 0):
                width, height = image_guess_size_from_field_name(field)
            record = request.env.ref('web.image_placeholder').sudo()
            stream = request.env['ir.binary']._get_image_stream_from(
                record, 'raw', width=int(width), height=int(height), crop=crop,
            )

        send_file_kwargs = {'as_attachment': download}
        if unique:
            send_file_kwargs['immutable'] = True
            send_file_kwargs['max_age'] = http.STATIC_CACHE_LONG
        if nocache:
            send_file_kwargs['max_age'] = None

        res = stream.get_response(**send_file_kwargs)
        res.headers['Content-Security-Policy'] = "default-src 'none'"
        return res

    @http.route('/web/binary/upload_attachment', type='http', auth="user")
    def upload_attachment(self, model, id, ufile, callback=None):
        files = request.httprequest.files.getlist('ufile')
        Model = request.env['ir.attachment']
        out = """<script language="javascript" type="text/javascript">
                    var win = window.top.window;
                    win.jQuery(win).trigger(%s, %s);
                </script>"""
        args = []
        for ufile in files:

            filename = ufile.filename
            if request.httprequest.user_agent.browser == 'safari':
                # Safari sends NFD UTF-8 (where é is composed by 'e' and [accent])
                # we need to send it the same stuff, otherwise it'll fail
                filename = unicodedata.normalize('NFD', ufile.filename)

            try:
                attachment = Model.create({
                    'name': filename,
                    'raw': ufile.read(),
                    'res_model': model,
                    'res_id': int(id)
                })
                attachment._post_add_create()
            except AccessError:
                args.append({'error': _("You are not allowed to upload an attachment here.")})
            except Exception:
                args.append({'error': _("Something horrible happened")})
                _logger.exception("Fail to upload attachment %s", ufile.filename)
            else:
                args.append({
                    'filename': clean(filename),
                    'mimetype': attachment.mimetype,
                    'id': attachment.id,
                    'size': attachment.file_size
                })
        return out % (json.dumps(clean(callback)), json.dumps(args)) if callback else json.dumps(args)

    @http.route([
        '/web/binary/company_logo',
        '/logo',
        '/logo.png',
    ], type='http', auth="none", cors="*")
    def company_logo(self, dbname=None, **kw):
        imgname = 'logo'
        imgext = '.png'
        dbname = request.db
        uid = (request.session.uid if dbname else None) or odoo.SUPERUSER_ID

        if not dbname:
            response = http.Stream.from_path(file_path('web/static/img/logo.png')).get_response()
        else:
            try:
                # create an empty registry
                registry = odoo.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    company = int(kw['company']) if kw and kw.get('company') else False
                    if company:
                        cr.execute("""SELECT logo_web, write_date
                                        FROM res_company
                                       WHERE id = %s
                                   """, (company,))
                    else:
                        cr.execute("""SELECT c.logo_web, c.write_date
                                        FROM res_users u
                                   LEFT JOIN res_company c
                                          ON c.id = u.company_id
                                       WHERE u.id = %s
                                   """, (uid,))
                    row = cr.fetchone()
                    if row and row[0]:
                        image_base64 = base64.b64decode(row[0])
                        image_data = io.BytesIO(image_base64)
                        mimetype = guess_mimetype(image_base64, default='image/png')
                        imgext = '.' + mimetype.split('/')[1]
                        if imgext == '.svg+xml':
                            imgext = '.svg'
                        response = send_file(
                            image_data,
                            request.httprequest.environ,
                            download_name=imgname + imgext,
                            mimetype=mimetype,
                            last_modified=row[1],
                            response_class=Response,
                        )
                    else:
                        response = http.Stream.from_path(file_path('web/static/img/nologo.png')).get_response()
            except Exception:
                response = http.Stream.from_path(file_path(f'web/static/img/{imgname}{imgext}')).get_response()

        return response

    @http.route(['/web/sign/get_fonts', '/web/sign/get_fonts/<string:fontname>'], type='json', auth='public')
    def get_fonts(self, fontname=None):
        """This route will return a list of base64 encoded fonts.

        Those fonts will be proposed to the user when creating a signature
        using mode 'auto'.

        :return: base64 encoded fonts
        :rtype: list
        """
        supported_exts = ('.ttf', '.otf', '.woff', '.woff2')
        fonts = []
        fonts_directory = file_path('web/static/fonts/sign')
        if fontname:
            font_path = os.path.join(fonts_directory, fontname)
            with file_open(font_path, 'rb', filter_ext=supported_exts) as font_file:
                font = base64.b64encode(font_file.read())
                fonts.append(font)
        else:
            font_filenames = sorted([fn for fn in os.listdir(fonts_directory) if fn.endswith(supported_exts)])
            for filename in font_filenames:
                font_file = file_open(os.path.join(fonts_directory, filename), 'rb', filter_ext=supported_exts)
                font = base64.b64encode(font_file.read())
                fonts.append(font)
        return fonts
