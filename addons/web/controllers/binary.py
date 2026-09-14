import base64
import hashlib
import io
import logging
import unicodedata
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from werkzeug.utils import send_file

import odoo
from odoo import _, api, http
from odoo.exceptions import AccessError, UserError
from odoo.http import Response, request
from odoo.libs.filesystem import guess_mimetype
from odoo.tools import file_open, file_path, replace_exceptions, str2bool
from odoo.tools.assets.constants import ANY_UNIQUE
from odoo.tools.image import image_guess_size_from_field_name
from odoo.tools.misc import is_valid_limited_field_access_token

from ..tools import debug_log as dbg

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


def clean(name: str) -> str:
    return name.replace("<", "").replace(">", "")


def _get_int_or_zero(value) -> int:
    try:
        return int(value)
    except TypeError, ValueError:
        return 0


def _resolve_res_id(value) -> int | None:
    if value is None or value is False or value == "":
        return None
    try:
        return int(value)
    except TypeError, ValueError:
        return None


def _get_send_file_kwargs(unique, download, nocache) -> dict[str, Any]:
    send_file_kwargs: dict[str, Any] = {"as_attachment": str2bool(download, False)}
    if unique:
        send_file_kwargs["immutable"] = True
        send_file_kwargs["max_age"] = http.STATIC_CACHE_LONG
    if str2bool(nocache, False):
        send_file_kwargs["max_age"] = None
    return send_file_kwargs


def _get_static_image_response(name: str) -> Response:
    return http.Stream.from_path(file_path(f"web/static/img/{name}")).prepare_response()


def _is_public_access_token_valid(record, field, access_token) -> bool:
    if not access_token:
        return False
    valid = bool(
        is_valid_limited_field_access_token(record, field, access_token, scope="binary")
    )
    dbg.logic.debug(
        "[content:%s/%s/%s] limited access token valid=%s",
        record._name,
        record.id,
        field,
        valid,
    )
    return valid


class Binary(http.Controller):
    @http.route("/web/filestore/<path:_path>", type="http", auth="none")
    def content_filestore(self, _path: str) -> Response:
        dbg.lifecycle.debug(
            "[filestore] %s x_sendfile=%s -> 404",
            dbg.req(),
            bool(odoo.tools.config["x_sendfile"]),
        )
        if odoo.tools.config["x_sendfile"]:
            _logger.error(
                BAD_X_SENDFILE_ERROR.format(data_dir=odoo.tools.config["data_dir"])
            )
        raise http.request.prepare_not_found_error()

    @http.route(
        [
            "/web/content",
            "/web/content/<string:xmlid>",
            "/web/content/<string:xmlid>/<string:filename>",
            "/web/content/<int:id>",
            "/web/content/<int:id>/<string:filename>",
            "/web/content/<string:model>/<int:id>/<string:field>",
            "/web/content/<string:model>/<int:id>/<string:field>/<string:filename>",
        ],
        type="http",
        auth="public",
        readonly=True,
    )
    def content_common(
        self,
        xmlid: str | None = None,
        model: str = "ir.attachment",
        id: int | str | None = None,
        field: str = "raw",
        filename: str | None = None,
        filename_field: str = "name",
        mimetype: str | None = None,
        unique: str | bool = False,
        download: str | bool = False,
        access_token: str | None = None,
        nocache: str | bool = False,
    ) -> Response:
        dbg.lifecycle.debug(
            "[content:%s/%s/%s] %s xmlid=%s filename=%r unique=%r download=%r "
            "nocache=%r token=%s",
            model,
            id,
            field,
            dbg.req(),
            xmlid,
            filename,
            unique,
            download,
            nocache,
            bool(access_token),
        )
        with replace_exceptions(UserError, by=request.prepare_not_found_error()):
            with dbg.timer(request.env, "[content:%s/%s/%s] resolve", model, id, field):
                record = request.env["ir.binary"]._get_record(
                    xmlid, model, _resolve_res_id(id), access_token, field_name=field
                )
                stream = request.env["ir.binary"]._get_stream_from_record(
                    record, field, filename, filename_field, mimetype
                )
            if _is_public_access_token_valid(record, field, access_token):
                stream.public = True
        dbg.pipeline.debug(
            "[content:%s/%s/%s] -> %s stream type=%s size=%s mimetype=%s public=%s",
            model,
            id,
            field,
            dbg.rec(record),
            stream.type,
            stream.size,
            stream.mimetype,
            stream.public,
        )

        send_file_kwargs = _get_send_file_kwargs(unique, download, nocache)
        dbg.logic.debug(
            "[content:%s/%s/%s] send_file %s", model, id, field, send_file_kwargs
        )

        return stream.prepare_response(**send_file_kwargs)

    @http.route(
        ["/web/assets/scope/<string:scope>/<string:unique>/<string:filename>"],
        type="http",
        auth="public",
        readonly=True,
    )
    def content_assets_scoped(self, scope: str, **kwargs: Any) -> Response:
        if scope not in request.env["ir.asset"]._get_addons_installed():
            dbg.logic.debug(
                "[asset:%s] scope %s not installed -> 404",
                kwargs.get("filename"),
                scope,
            )
            raise request.prepare_not_found_error()
        dbg.pipeline.debug("[asset:%s] scoped to %s", kwargs.get("filename"), scope)
        return self.content_assets(**kwargs, assets_params={"unit_test_scope": scope})

    @http.route(
        ["/web/assets/<string:unique>/<string:filename>"],
        type="http",
        auth="public",
        readonly=True,
    )
    def content_assets(
        self,
        filename: str,
        unique: str = ANY_UNIQUE,
        nocache: str | bool = False,
        assets_params: dict[str, Any] | None = None,
    ) -> Response:
        dbg.lifecycle.debug(
            "[asset:%s] %s unique=%s nocache=%r params=%s",
            filename,
            dbg.req(),
            unique,
            nocache,
            dbg.keys(assets_params or {}),
        )
        env = request.env
        assets_params = assets_params or {}
        if not isinstance(assets_params, dict):
            dbg.logic.debug("[asset:%s] assets_params not a dict -> 404", filename)
            raise request.prepare_not_found_error()
        debug_assets = unique == "debug"
        stream = None
        if unique in ("any", "%"):
            unique = ANY_UNIQUE
        if not debug_assets:
            url = env["ir.asset"]._get_asset_bundle_url_pattern(
                filename, unique, assets_params
            )
            if "%" in url:
                dbg.logic.debug("[asset:%s] url pattern still has %% -> 404", filename)
                raise request.prepare_not_found_error()
            IrAttachment = env["ir.attachment"].sudo()
            with dbg.timer(env, "[asset:%s] attachment lookup", filename):
                attachment = IrAttachment.search(
                    IrAttachment._get_domain_generated_assets(url_pattern=url), limit=1
                )
            dbg.logic.debug(
                "[asset:%s] cached attachment: %s",
                filename,
                attachment.id if attachment else "miss",
            )
            if attachment:
                stream = env["ir.binary"]._get_stream_from_record(
                    attachment, "raw", filename
                )
        if stream is None:
            dbg.pipeline.debug(
                "[asset:%s] no cached stream: generate (debug=%s)",
                filename,
                debug_assets,
            )
            stream, redirect = self._get_generated_asset_stream(
                filename, unique, debug_assets, assets_params
            )
            if redirect is not None:
                dbg.pipeline.debug("[asset:%s] version mismatch -> redirect", filename)
                return redirect
        if stream is None:
            dbg.logic.debug("[asset:%s] no stream after generation -> 404", filename)
            raise request.prepare_not_found_error()
        if stream.type == "url":
            dbg.logic.debug("[asset:%s] url stream blanked to empty data", filename)
            stream.type = "data"
            stream.data = b""
            stream.size = 0
            stream.url = None
        dbg.performance.debug(
            "[asset:%s] stream type=%s size=%s", filename, stream.type, stream.size
        )
        send_file_kwargs = {
            "as_attachment": False,
            "content_security_policy": None,
        }
        if str2bool(nocache, False):
            send_file_kwargs["max_age"] = None
        elif not debug_assets:
            send_file_kwargs["immutable"] = True
            send_file_kwargs["max_age"] = http.STATIC_CACHE_LONG

        return stream.prepare_response(**send_file_kwargs)

    def _get_generated_asset_stream(
        self,
        filename: str,
        unique: str,
        debug_assets: bool,
        assets_params: dict[str, Any],
    ) -> tuple[Any, Response | None]:
        if filename.endswith(".map"):
            _logger.error(
                ".map should have been generated through debug assets, (version %s most likely outdated)",
                unique,
            )
            raise request.prepare_not_found_error()
        env = request.env
        stream = None
        if env.cr.readonly:
            dbg.logic.debug(
                "[asset:%s] generate: request cursor is readonly, rollback + rw cursor",
                filename,
            )
            env.cr.rollback()
            cursor_manager = env.registry.cursor(readonly=False)
        else:
            cursor_manager = nullcontext(env.cr)
        with cursor_manager as rw_cr:
            digest = hashlib.blake2b(filename.encode(), digest_size=8).digest()
            with dbg.timer(None, "[asset:%s] generate: advisory lock wait", filename):
                rw_cr.execute(
                    "SELECT pg_advisory_xact_lock(%s)",
                    (int.from_bytes(digest, "big", signed=True),),
                )
            rw_env = api.Environment(rw_cr, env.user.id, {})
            try:
                bundle_name, rtl, asset_type, autoprefix = rw_env[
                    "ir.asset"
                ]._parse_bundle_name(filename, debug_assets)
                css = asset_type == "css"
                js = asset_type == "js"
                dbg.pipeline.debug(
                    "[asset:%s] generate: bundle=%s type=%s rtl=%s autoprefix=%s",
                    filename,
                    bundle_name,
                    asset_type,
                    rtl,
                    autoprefix,
                )
                with dbg.timer(rw_env, "[asset:%s] generate: build bundle", filename):
                    bundle = rw_env["ir.qweb"]._get_asset_bundle(
                        bundle_name,
                        css=css,
                        js=js,
                        debug_assets=debug_assets,
                        rtl=rtl,
                        autoprefix=autoprefix,
                        assets_params=assets_params,
                    )
                if (
                    not debug_assets
                    and unique != ANY_UNIQUE
                    and unique != bundle.get_version(asset_type)
                ):
                    dbg.logic.debug(
                        "[asset:%s] generate: requested %s != current %s",
                        filename,
                        unique,
                        bundle.get_version(asset_type),
                    )
                    return None, request.redirect(bundle.get_link(asset_type))
                attachment = None
                with dbg.timer(
                    rw_env, "[asset:%s] generate: %s()", filename, asset_type
                ):
                    if css:
                        attachment = bundle.css()
                    elif js:
                        attachment = bundle.js()
                dbg.logic.debug(
                    "[asset:%s] generate: attachment %s",
                    filename,
                    attachment.id if attachment else None,
                )
                if attachment:
                    stream = rw_env["ir.binary"]._get_stream_from_record(
                        attachment, "raw", filename
                    )
            except ValueError as e:
                dbg.logic.debug("[asset:%s] generate: bundle name unparsable", filename)
                _logger.warning("Parsing asset bundle %s has failed: %s", filename, e)
                raise request.prepare_not_found_error() from e
        return stream, None

    @http.route(
        ["/web/assets/esm/<string:unique>/<string:filename>"],
        type="http",
        auth="public",
        readonly=True,
    )
    def content_esm_assets(self, unique: str, filename: str) -> Response:
        return self._serve_generated_esm(f"/web/assets/esm/{unique}/{filename}")

    @http.route(
        ["/web/assets/lib/<string:unique>/<path:path>"],
        type="http",
        auth="public",
        readonly=True,
    )
    def content_esm_lib(self, unique: str, path: str) -> Response:
        return self._serve_generated_esm(f"/web/assets/lib/{unique}/{path}")

    @staticmethod
    def _serve_generated_esm(url: str) -> Response:
        dbg.lifecycle.debug("[esm:%s] %s", url, dbg.req())
        IrAttachment = request.env["ir.attachment"].sudo()
        with dbg.timer(request.env, "[esm:%s] attachment lookup", url):
            attachment = IrAttachment.search(
                IrAttachment._get_domain_generated_assets(url),
                limit=1,
                order="id desc",
            )
        if not attachment:
            dbg.logic.debug("[esm:%s] no generated attachment -> 404", url)
            raise request.prepare_not_found_error()
        stream = request.env["ir.binary"]._get_stream_from_record(
            attachment,
            "raw",
            url.rsplit("/", 1)[-1],
        )
        dbg.pipeline.debug(
            "[esm:%s] attachment %s size=%s", url, attachment.id, stream.size
        )
        return stream.prepare_response(
            as_attachment=False,
            content_security_policy=None,
            immutable=True,
            max_age=http.STATIC_CACHE_LONG,
        )

    @http.route(
        [
            "/web/image",
            "/web/image/<string:xmlid>",
            "/web/image/<string:xmlid>/<string:filename>",
            "/web/image/<string:xmlid>/<int:width>x<int:height>",
            "/web/image/<string:xmlid>/<int:width>x<int:height>/<string:filename>",
            "/web/image/<string:model>/<int:id>/<string:field>",
            "/web/image/<string:model>/<int:id>/<string:field>/<string:filename>",
            "/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>",
            "/web/image/<string:model>/<int:id>/<string:field>/<int:width>x<int:height>/<string:filename>",
            "/web/image/<int:id>",
            "/web/image/<int:id>/<string:filename>",
            "/web/image/<int:id>/<int:width>x<int:height>",
            "/web/image/<int:id>/<int:width>x<int:height>/<string:filename>",
            "/web/image/<int:id>-<string:unique>",
            "/web/image/<int:id>-<string:unique>/<string:filename>",
            "/web/image/<int:id>-<string:unique>/<int:width>x<int:height>",
            "/web/image/<int:id>-<string:unique>/<int:width>x<int:height>/<string:filename>",
        ],
        type="http",
        auth="public",
        readonly=True,
        save_session=False,
    )
    def content_image(
        self,
        xmlid: str | None = None,
        model: str = "ir.attachment",
        id: int | str | None = None,
        field: str = "raw",
        filename_field: str = "name",
        filename: str | None = None,
        mimetype: str | None = None,
        unique: str | bool = False,
        download: str | bool = False,
        width: int | str = 0,
        height: int | str = 0,
        crop: str | bool = False,
        access_token: str | None = None,
        nocache: str | bool = False,
    ) -> Response:
        crop = str2bool(crop, False)
        width = _get_int_or_zero(width)
        height = _get_int_or_zero(height)
        dbg.lifecycle.debug(
            "[image:%s/%s/%s] %s xmlid=%s %dx%d crop=%s unique=%r download=%r token=%s",
            model,
            id,
            field,
            dbg.req(),
            xmlid,
            width,
            height,
            crop,
            unique,
            download,
            bool(access_token),
        )
        try:
            with dbg.timer(request.env, "[image:%s/%s/%s] resolve", model, id, field):
                record = request.env["ir.binary"]._get_record(
                    xmlid, model, _resolve_res_id(id), access_token, field_name=field
                )
                stream = request.env["ir.binary"]._get_stream_image_from_record(
                    record,
                    field,
                    filename=filename,
                    filename_field=filename_field,
                    mimetype=mimetype,
                    width=width,
                    height=height,
                    crop=crop,
                )
            if _is_public_access_token_valid(record, field, access_token):
                stream.public = True
            dbg.pipeline.debug(
                "[image:%s/%s/%s] -> %s type=%s size=%s mimetype=%s",
                model,
                id,
                field,
                dbg.rec(record),
                stream.type,
                stream.size,
                stream.mimetype,
            )
        except UserError as exc:
            if str2bool(download, False):
                dbg.logic.debug(
                    "[image:%s/%s/%s] unavailable (%s), download -> 404",
                    model,
                    id,
                    field,
                    type(exc).__name__,
                )
                raise request.prepare_not_found_error() from exc
            if (width, height) == (0, 0):
                width, height = image_guess_size_from_field_name(field)
            dbg.logic.debug(
                "[image:%s/%s/%s] unavailable (%s) -> placeholder %dx%d",
                model,
                id,
                field,
                type(exc).__name__,
                width,
                height,
            )
            record = request.env.ref("web.image_placeholder").sudo()
            stream = request.env["ir.binary"]._get_stream_image_from_record(
                record,
                "raw",
                width=width,
                height=height,
                crop=crop,
            )
            stream.public = False

        return stream.prepare_response(
            **_get_send_file_kwargs(unique, download, nocache)
        )

    @http.route("/web/binary/upload_attachment", type="http", auth="user")
    def upload_attachment(
        self,
        model: str,
        id: int | str,
        ufile: Any,
    ) -> Response:
        files = request.httprequest.files.getlist("ufile")
        dbg.lifecycle.debug(
            "[upload:%s/%s] %s files=%d", model, id, dbg.req(), len(files)
        )
        Attachment = request.env["ir.attachment"]
        results = []
        for uploaded_file in files:
            filename = uploaded_file.filename
            if request.httprequest.user_agent.browser == "safari":
                dbg.logic.debug("[upload:%s/%s] safari: NFD-normalize name", model, id)
                filename = unicodedata.normalize("NFD", uploaded_file.filename)

            try:
                uploaded_file.filename = filename
                with dbg.timer(
                    request.env, "[upload:%s/%s] create %r", model, id, filename
                ):
                    attachment = Attachment._create_from_request_file(
                        uploaded_file,
                        res_model=model,
                        res_id=int(id),
                    )
                    attachment._post_add_create()
            except AccessError:
                dbg.logic.debug("[upload:%s/%s] %r: access denied", model, id, filename)
                results.append(
                    {"error": _("You are not allowed to upload an attachment here.")}
                )
            except Exception:
                dbg.logic.debug(
                    "[upload:%s/%s] %r: unexpected failure", model, id, filename
                )
                results.append({"error": _("Something horrible happened")})
                _logger.exception(
                    "Fail to upload attachment %s", uploaded_file.filename
                )
            else:
                dbg.lifecycle.debug(
                    "[upload:%s/%s] %r -> attachment %s (%s, %s bytes)",
                    model,
                    id,
                    filename,
                    attachment.id,
                    attachment.mimetype,
                    attachment.file_size,
                )
                results.append(
                    {
                        "filename": clean(filename),
                        "mimetype": attachment.mimetype,
                        "id": attachment.id,
                        "size": attachment.file_size,
                    }
                )
        return request.prepare_json_response(results)

    @http.route(
        [
            "/web/binary/company_logo",
            "/logo",
            "/logo.png",
        ],
        type="http",
        auth="none",
        cors="*",
        readonly=True,
    )
    def company_logo(self, **kw: Any) -> Response:
        dbname = request.db
        uid = (request.session.uid if dbname else None) or odoo.SUPERUSER_ID
        dbg.lifecycle.debug(
            "[logo] %s company=%r uid=%s", dbg.req(), kw.get("company"), uid
        )

        if not dbname:
            dbg.logic.debug("[logo] no db -> static odoo logo")
            response = _get_static_image_response("logo.png")
        else:
            try:
                try:
                    company = int(kw["company"]) if kw.get("company") else False
                except ValueError, TypeError:
                    company = False
                dbg.logic.debug(
                    "[logo] lookup by %s",
                    f"company {company}" if company else f"uid {uid}",
                )
                if company:
                    request.env.cr.execute(
                        """
                        SELECT logo_web, write_date
                          FROM res_company
                         WHERE id = %s
                    """,
                        (company,),
                    )
                else:
                    request.env.cr.execute(
                        """
                        SELECT c.logo_web, c.write_date
                          FROM res_users u
                     LEFT JOIN res_company c
                            ON c.id = u.company_id
                         WHERE u.id = %s
                    """,
                        (uid,),
                    )
                row = request.env.cr.fetchone()
                if row and row[0]:
                    image_base64 = base64.b64decode(row[0])
                    image_data = io.BytesIO(image_base64)
                    mimetype = guess_mimetype(image_base64, default="image/png")
                    imgext = "." + mimetype.split("/")[1]
                    if imgext == ".svg+xml":
                        imgext = ".svg"
                    dbg.pipeline.debug(
                        "[logo] company logo %s, %d bytes, modified %s",
                        mimetype,
                        len(image_base64),
                        row[1],
                    )
                    response = send_file(
                        image_data,
                        request.httprequest.environ,
                        download_name=f"logo{imgext}",
                        mimetype=mimetype,
                        last_modified=row[1],
                        response_class=Response,
                    )
                else:
                    dbg.logic.debug("[logo] no logo_web row -> nologo.png")
                    response = _get_static_image_response("nologo.png")
            except Exception as exc:
                dbg.logic.debug(
                    "[logo] lookup failed (%s) -> odoo logo", type(exc).__name__
                )
                _logger.warning(
                    "While retrieving the company logo, using the Odoo logo instead",
                    exc_info=True,
                )
                response = _get_static_image_response("logo.png")

        return response

    @http.route(
        [
            "/web/sign/get_fonts",
            "/web/sign/get_fonts/<string:fontname>",
        ],
        type="jsonrpc",
        auth="none",
        readonly=True,
    )
    def get_fonts(self, fontname: str | None = None) -> list[bytes]:
        supported_exts = (".ttf", ".otf", ".woff", ".woff2")
        fonts_dir = Path(file_path("web/static/fonts/sign"))
        dbg.lifecycle.debug("[fonts] %s fontname=%r", dbg.req(), fontname)
        if fontname:
            if Path(fontname).name != fontname:
                dbg.logic.debug("[fonts] %r is not a bare name -> 404", fontname)
                raise request.prepare_not_found_error()
            font_filenames = [fontname]
        else:
            font_filenames = sorted(
                fn.name for fn in fonts_dir.iterdir() if fn.suffix in supported_exts
            )
        fonts = []
        for filename in font_filenames:
            try:
                with file_open(
                    str(fonts_dir / filename), "rb", filter_ext=supported_exts
                ) as font_file:
                    fonts.append(base64.b64encode(font_file.read()))
            except FileNotFoundError, ValueError:
                dbg.logic.debug("[fonts] %r not a sign font -> 404", filename)
                raise request.prepare_not_found_error() from None
        dbg.performance.debug(
            "[fonts] %d fonts, %d base64 bytes", len(fonts), sum(map(len, fonts))
        )
        return fonts
