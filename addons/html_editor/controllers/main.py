import contextlib
import math
import re
import uuid
from base64 import b64decode, b64encode
from datetime import datetime
from os.path import join as opj
from urllib.parse import urlencode, urlparse

import requests
import werkzeug.exceptions
from lxml import etree, html

from odoo import SUPERUSER_ID, _, http, tools
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.libs.filesystem import guess_mimetype
from odoo.libs.guarded_http import RefusedDestination
from odoo.tools.image import (
    binary_to_image,
    get_webp_size,
    image_data_uri,
    image_process,
)
from odoo.tools.misc import file_open

from ..models.ir_attachment import SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_IMAGE_MIMETYPES
from odoo.addons.html_editor.tools import get_video_url_data
from odoo.addons.iap.tools import iap_tools
from odoo.addons.mail.tools import link_preview

_debug = DebugLog(__name__)

DEFAULT_LIBRARY_ENDPOINT = "https://media-api.odoo.com"
LIBRARY_MEDIA_MAX_BYTES = 32 * 1024 * 1024
DEFAULT_OLG_ENDPOINT = "https://olg.api.odoo.com"


CSS_ANIMATION_RULE_REGEX = (
    r"(?P<declaration>animation(-duration)?:\s*.*?)"
    r"(?P<value>(\d+(\.\d+)?)|(\.\d+))"
    r"(?P<unit>ms|s)"
    r"(?P<separator>\s|;|\"|$)"
)
SVG_DUR_TIMECOUNT_VAL_REGEX = (
    r"(?P<attribute_name>\sdur=\"\s*)"
    r"(?P<value>(\d+(\.\d+)?)|(\.\d+))"
    r"(?P<unit>h|min|ms|s)?\s*\""
)
CSS_ANIMATION_RATIO_REGEX = r"(--animation_ratio: (?P<ratio>\d*(\.\d+)?));"


def get_existing_attachment(IrAttachment, vals):
    fields = dict(vals)
    fields["res_id"] = fields.get("res_id") or 0
    raw, datas = fields.pop("raw", None), fields.pop("datas", None)
    domain = [(field, "=", value) for field, value in fields.items()]
    if fields.get("type") == "url":
        if "url" not in fields:
            return None
        domain.append(("checksum", "=", False))
    else:
        if not (raw or datas):
            return None
        domain.append(
            (
                "checksum",
                "=",
                IrAttachment._get_content_checksum(raw or b64decode(datas)),
            )
        )
    return IrAttachment.search(domain, limit=1) or None


class HTML_Editor(http.Controller):
    def _get_shape_svg(self, module, *segments):
        shape_path = opj(module, "static", *segments)  # noqa: PTH118 - path contained by file_open()'s is_relative_to check
        try:
            with file_open(shape_path, "r", filter_ext=(".svg",)) as file:
                return file.read()
        except FileNotFoundError:
            _debug.logic("shape_refused", reason="missing", path=shape_path)
            raise werkzeug.exceptions.NotFound from None
        except ValueError:
            _debug.logic("shape_refused", reason="outside_addons", path=shape_path)
            raise werkzeug.exceptions.NotFound from None

    _SVG_DEFAULT_PALETTE = {
        "1": "#3AADAA",
        "2": "#7C6576",
        "3": "#F6F6F6",
        "4": "#FFFFFF",
        "5": "#383E45",
    }

    def _update_svg_colors(self, options, svg):
        user_colors = []
        svg_options = {}
        bundle_css = None
        regex_hex = r"#[0-9A-F]{6,8}"
        regex_rgba = r"rgba?\(\d{1,3}, ?\d{1,3}, ?\d{1,3}(?:, ?[0-9.]{1,4})?\)"
        for key, value in options.items():
            colorMatch = re.match(r"^c([1-5])$", key)
            if colorMatch:
                css_color_value = value
                if not re.match(
                    rf"(?i)^{regex_hex}$|^{regex_rgba}$",
                    css_color_value.replace(" ", ""),
                ):
                    o_color_match = re.match(r"^o-color-([1-5])$", css_color_value)
                    if o_color_match:
                        if bundle_css is None:
                            bundle = "web.assets_frontend"
                            asset = request.env["ir.qweb"]._get_asset_bundle(bundle)
                            bundle_css = asset.css().raw.decode("utf-8")
                        color_search = re.search(
                            rf"(?i)--{css_color_value}:\s*({regex_hex}|{regex_rgba})",
                            bundle_css,
                        )
                        if color_search:
                            css_color_value = color_search.group(1)
                        else:
                            css_color_value = self._SVG_DEFAULT_PALETTE[
                                o_color_match.group(1)
                            ]
                    else:
                        _debug.logic("shape_color_refused", key=str(key))
                        raise werkzeug.exceptions.BadRequest
                user_colors.append(
                    [tools.html_escape(css_color_value), colorMatch.group(1)]
                )
            else:
                svg_options[key] = value

        color_mapping = {
            self._SVG_DEFAULT_PALETTE[palette_number]: color
            for color, palette_number in user_colors
        }
        if not color_mapping:
            return svg, svg_options
        regex = "(?i)" + "|".join(f"({color})" for color in color_mapping)

        def subber(match):
            key = match.group().upper()
            return color_mapping.get(key, key)

        return re.sub(regex, subber, svg), svg_options

    def replace_animation_duration(self, shape_animation_speed: float, svg: str):
        ratio = (
            1 + shape_animation_speed
            if shape_animation_speed >= 0
            else 1 / (1 - shape_animation_speed)
        )

        def callback_css_animation_rule(match):
            declaration, value, unit, separator = (
                match.group("declaration"),
                match.group("value"),
                match.group("unit"),
                match.group("separator"),
            )
            value = str(float(value) / (ratio or 1))
            return f"{declaration}{value}{unit}{separator}"

        def callback_svg_dur_timecount_val(match):
            attribute_name, value, unit = (
                match.group("attribute_name"),
                match.group("value"),
                match.group("unit"),
            )
            value = str(float(value) / (ratio or 1))
            return f'{attribute_name}{value}{unit or "s"}"'

        def callback_css_animation_ratio(match):
            ratio = match.group("ratio")
            return f"--animation_ratio: {ratio};"

        svg = re.sub(CSS_ANIMATION_RULE_REGEX, callback_css_animation_rule, svg)
        svg = re.sub(SVG_DUR_TIMECOUNT_VAL_REGEX, callback_svg_dur_timecount_val, svg)
        if re.search(CSS_ANIMATION_RATIO_REGEX, svg):
            svg = re.sub(CSS_ANIMATION_RATIO_REGEX, callback_css_animation_ratio, svg)
        else:
            regex = r"<svg .*?>"
            declaration = f"--animation_ratio: {ratio}"
            subst = (
                "\\g<0>\n\t<style>\n\t\t:root { \n\t\t\t"
                + declaration
                + ";\n\t\t}\n\t</style>"
            )
            svg = re.sub(regex, subst, svg, count=1, flags=re.DOTALL)
        return svg

    @http.route(
        "/html_editor/attachment/remove", type="jsonrpc", auth="user", website=True
    )
    def remove(self, ids, **kwargs):
        self._clean_context()
        Attachment = attachments_to_remove = request.env["ir.attachment"]
        # sudo(): the existence-check must see every referencing view, not
        # just the ones visible under the caller's own ACL/record rules
        # (e.g. a restricted-visibility website page) -- otherwise a
        # lower-privileged caller could delete an attachment still in use
        # by a page they can't see.
        Views = request.env["ir.ui.view"].sudo()

        removal_blocked_by = {}

        for attachment in Attachment.browse(ids):
            url = tools.html_escape(attachment.local_url)
            views = Views.search(  # noqa: E8507 - one probe per attachment, on its own url
                ["|", ("arch_db", "like", f'"{url}"'), ("arch_db", "like", f"'{url}'")]
            )

            if views:
                _debug.logic(
                    "attachment_remove_blocked",
                    attachment=attachment.id,
                    views=len(views),
                )
                removal_blocked_by[attachment.id] = views.read(["name"])
            else:
                attachments_to_remove += attachment
        if attachments_to_remove:
            _debug.lifecycle("attachments_removed", attachments=attachments_to_remove)
            attachments_to_remove.unlink()
        return removal_blocked_by

    def _clean_context(self):
        context = dict(request.env.context)
        context.pop("allowed_company_ids", None)
        request.update_env(context=context)

    def _attachment_create(
        self, name="", data=False, url=False, res_id=False, res_model="ir.ui.view"
    ):
        IrAttachment = request.env["ir.attachment"]

        if name.lower().endswith(".bmp"):
            name = name[:-4]

        if not name and url:
            name = url.split("/").pop()

        if res_model != "ir.ui.view" and res_id:
            res_id = int(res_id)
        else:
            res_id = False

        attachment_data = {
            "name": name,
            "public": res_model == "ir.ui.view",
            "res_id": res_id,
            "res_model": res_model,
        }

        if data:
            attachment_data["raw"] = data
            if url:
                attachment_data["url"] = url
        elif url:
            attachment_data.update(
                {
                    "type": "url",
                    "url": url,
                }
            )
            try:
                response = request.env["ir.egress"].request(
                    "HEAD", url, purpose="media_url", timeout=10, allow_redirects=False
                )
            except (
                RefusedDestination,
                requests.exceptions.InvalidSchema,
                requests.exceptions.MissingSchema,
                requests.exceptions.InvalidURL,
            ):
                _debug.logic("media_url_refused", reason="unfetchable", url=url)
                raise UserError(_("The provided URL cannot be fetched.")) from None
            except requests.RequestException:
                _debug.logic("media_url_probe_failed", url=url)
                response = None
            if response is not None and response.status_code == 200:
                mime_type = response.headers.get("content-type")
                if mime_type in SUPPORTED_IMAGE_MIMETYPES:
                    attachment_data["mimetype"] = mime_type
        else:
            _debug.logic("attachment_create_refused", reason="no_data_or_url")
            raise UserError(
                _("You need to specify either data or url to create an attachment.")
            )

        if (
            not request.env.is_admin()
            and IrAttachment._can_bypass_rights_on_media_dialog(**attachment_data)
        ):
            attachment = IrAttachment.sudo().create(attachment_data)
            if not attachment_data["public"]:
                attachment.sudo().generate_access_token()
        else:
            attachment = get_existing_attachment(
                IrAttachment, attachment_data
            ) or IrAttachment.create(attachment_data)

        return attachment

    @http.route(
        ["/web_editor/get_image_info", "/html_editor/get_image_info"],
        type="jsonrpc",
        auth="user",
        website=True,
    )
    def get_image_info(self, src=""):
        self._clean_context()
        attachment = None
        if src.startswith("/web/image"):
            with contextlib.suppress(werkzeug.exceptions.NotFound, MissingError):
                _, args = request.env["ir.http"]._match(src)
                record = request.env["ir.binary"]._get_record(
                    xmlid=args.get("xmlid"),
                    res_model=args.get("model", "ir.attachment"),
                    res_id=args.get("id"),
                )
                if record._name == "ir.attachment":
                    attachment = record
        if not attachment:
            attachment = request.env["ir.attachment"].search(
                [
                    "|",
                    ("url", "=like", src),
                    ("url", "=like", f"{src}?%"),
                    ("mimetype", "in", list(SUPPORTED_IMAGE_MIMETYPES.keys())),
                ],
                limit=1,
            )
        if not attachment:
            return {
                "attachment": False,
                "original": False,
            }
        return {
            "attachment": attachment.read(["id"])[0],
            "original": (attachment.original_id or attachment).read(
                ["id", "image_src", "mimetype"]
            )[0],
        }

    @http.route(
        ["/web_editor/video_url/data", "/html_editor/video_url/data"],
        type="jsonrpc",
        auth="user",
        website=True,
    )
    def video_url_data(
        self,
        video_url,
        autoplay=False,
        loop=False,
        hide_controls=False,
        hide_fullscreen=False,
        hide_dm_logo=False,
        hide_dm_share=False,
        start_from=False,
    ):
        return get_video_url_data(
            video_url,
            autoplay=autoplay,
            loop=loop,
            hide_controls=hide_controls,
            hide_fullscreen=hide_fullscreen,
            hide_dm_logo=hide_dm_logo,
            hide_dm_share=hide_dm_share,
            start_from=start_from,
        )

    @http.route(
        ["/web_editor/attachment/add_data", "/html_editor/attachment/add_data"],
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def add_data(
        self,
        name,
        data,
        is_image,
        quality=0,
        width=0,
        height=0,
        res_id=False,
        res_model="ir.ui.view",
        **kwargs,
    ):
        data = b64decode(data)
        if is_image:
            format_error_msg = _(
                "Uploaded image's format is not supported. Try with: %s",
                ", ".join(f".{extension}" for extension in SUPPORTED_IMAGE_EXTENSIONS),
            )
            try:
                mimetype = guess_mimetype(data)
                if mimetype not in SUPPORTED_IMAGE_MIMETYPES:
                    return {"error": format_error_msg}
                if not name:
                    name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}{SUPPORTED_IMAGE_MIMETYPES[mimetype]}"
                data = image_process(
                    data, size=(width, height), quality=quality, verify_resolution=True
                )
            except (ValueError, UserError) as e:
                return {"error": e.args[0]}

        self._clean_context()
        attachment = self._attachment_create(
            name=name, data=data, res_id=res_id, res_model=res_model
        )
        return attachment._get_media_info()

    @http.route(
        ["/web_editor/attachment/add_url", "/html_editor/attachment/add_url"],
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        website=True,
    )
    def add_url(self, url, res_id=False, res_model="ir.ui.view", **kwargs):
        self._clean_context()
        attachment = self._attachment_create(
            url=url, res_id=res_id, res_model=res_model
        )
        return attachment._get_media_info()

    @http.route(
        [
            '/web_editor/modify_image/<model("ir.attachment"):attachment>',
            '/html_editor/modify_image/<model("ir.attachment"):attachment>',
        ],
        type="jsonrpc",
        auth="user",
        website=True,
    )
    def modify_image(
        self,
        attachment,
        res_model=None,
        res_id=None,
        name=None,
        data=None,
        original_id=None,
        mimetype=None,
        alt_data=None,
    ):
        self._clean_context()
        attachment = request.env["ir.attachment"].browse(attachment.id)
        if not data and attachment.datas:
            data = attachment.datas

        fields = {
            "original_id": attachment.id,
            "datas": data,
            "type": "binary",
            "res_model": res_model or "ir.ui.view",
            "mimetype": mimetype or attachment.mimetype,
            "name": name or attachment.name,
            "res_id": 0,
        }
        if fields["res_model"] == "ir.ui.view":
            fields["res_id"] = 0
        elif res_id:
            fields["res_id"] = res_id
        if fields["mimetype"] == "image/webp":
            fields["name"] = re.sub(
                r"\.(jpe?g|png)$", ".webp", fields["name"], flags=re.IGNORECASE
            )

        existing_attachment = get_existing_attachment(
            request.env["ir.attachment"], fields
        )
        if existing_attachment and not existing_attachment.url:
            attachment = existing_attachment
        else:
            if attachment.res_model and attachment.res_id:
                request.env[attachment.res_model].browse(
                    attachment.res_id
                ).check_access("read")

            request.env[fields["res_model"]].browse(fields["res_id"]).check_access(
                "write"
            )

            attachment = attachment.sudo().copy(fields).sudo(False)
            if attachment.mimetype == "text/plain" != fields["mimetype"]:
                attachment.with_user(SUPERUSER_ID).mimetype = fields["mimetype"]

        if alt_data:
            for size, per_type in alt_data.items():
                reference_id = attachment.id
                if "image/webp" in per_type:
                    resized = attachment.create_unique(
                        [
                            {
                                "name": attachment.name,
                                "description": f"resize: {size}",
                                "datas": per_type["image/webp"],
                                "res_id": reference_id,
                                "res_model": "ir.attachment",
                                "mimetype": "image/webp",
                            }
                        ]
                    )
                    reference_id = resized[0]
                if "image/jpeg" in per_type:
                    attachment.create_unique(
                        [
                            {
                                "name": re.sub(
                                    r"\.webp$",
                                    ".jpg",
                                    attachment.name,
                                    flags=re.IGNORECASE,
                                ),
                                "description": "format: jpeg",
                                "datas": per_type["image/jpeg"],
                                "res_id": reference_id,
                                "res_model": "ir.attachment",
                                "mimetype": "image/jpeg",
                            }
                        ]
                    )

        if attachment.url:
            if re.match(r"^/\w+/static/", attachment.url):
                attachment.url = None
            else:
                url_fragments = attachment.url.split("/")
                url_fragments.insert(-1, str(attachment.id))
                attachment.url = "/".join(url_fragments)

        if attachment.public:
            return attachment.image_src

        attachment.generate_access_token()
        return f"{attachment.image_src}?access_token={attachment.access_token}"

    @http.route(
        ["/web_editor/save_library_media", "/html_editor/save_library_media"],
        type="jsonrpc",
        auth="user",
        methods=["POST"],
    )
    def save_library_media(self, media):
        attachments = []
        ICP = request.env["ir.config_parameter"].sudo()
        library_endpoint = ICP.get_param(
            "html_editor.media_library_endpoint", DEFAULT_LIBRARY_ENDPOINT
        )

        media_ids = ",".join(media.keys())
        params = {
            "dbuuid": ICP.get_param("database.uuid"),
            "media_ids": media_ids,
        }
        session = request.env["ir.egress"].session(
            purpose="media_library", max_bytes=LIBRARY_MEDIA_MAX_BYTES
        )
        response = session.post(
            f"{library_endpoint}/media-library/1/download_urls", data=params, timeout=15
        )
        if response.status_code != requests.codes.ok:
            raise UserError(_("Could not get download URLs from the media library."))

        slug = request.env["ir.http"]._slug
        for media_id, url in response.json().items():
            if media_id not in media:
                continue
            try:
                req = session.get(url, timeout=15)
            except RefusedDestination:
                continue
            name = "_".join([media[media_id]["query"], url.split("/")[-1]])
            IrAttachment = request.env["ir.attachment"]
            attachment_data = {
                "name": name,
                "mimetype": req.headers.get("content-type"),
                "public": True,
                "raw": req.content,
                "res_model": "ir.ui.view",
                "res_id": 0,
            }
            attachment = get_existing_attachment(IrAttachment, attachment_data)
            if not attachment:
                attachment = IrAttachment.with_user(SUPERUSER_ID).create(
                    attachment_data
                )
            if media[media_id]["is_dynamic_svg"]:
                colorParams = urlencode(media[media_id]["dynamic_colors"])
                attachment["url"] = (
                    f"/html_editor/shape/illustration/{slug(attachment)}?{colorParams}"
                )
            attachments.append(attachment._get_media_info())

        return attachments

    @http.route(
        [
            "/web_editor/shape/<module>/<path:filename>",
            "/html_editor/shape/<module>/<path:filename>",
        ],
        type="http",
        auth="public",
        website=True,
    )
    def shape(self, module, filename, **kwargs):
        svg = None
        if module == "illustration":
            unslug = request.env["ir.http"]._unslug
            attachment = request.env["ir.attachment"].sudo().browse(unslug(filename)[1])
            if (
                not attachment.exists()
                or attachment.type != "binary"
                or not attachment.public
                or not (attachment.url or "").startswith(request.httprequest.path)
            ):
                attachment = (
                    request.env["ir.attachment"]
                    .sudo()
                    .search(
                        [
                            ("type", "=", "binary"),
                            ("public", "=", True),
                            ("url", "=", request.httprequest.path),
                        ],
                        limit=1,
                    )
                )
                if not attachment:
                    raise werkzeug.exceptions.NotFound
            svg = attachment.raw.decode("utf-8")
        else:
            if module == "web_editor":
                module = "html_builder"
            svg = self._get_shape_svg(module, "shapes", filename)

        svg, options = self._update_svg_colors(kwargs, svg)
        flip_value = options.get("flip", False)
        if flip_value == "x":
            svg = svg.replace("<svg ", '<svg style="transform: scaleX(-1);" ', 1)
        elif flip_value == "y":
            svg = svg.replace("<svg ", '<svg style="transform: scaleY(-1)" ', 1)
        elif flip_value == "xy":
            svg = svg.replace("<svg ", '<svg style="transform: scale(-1)" ', 1)

        try:
            shape_animation_speed = float(options.get("shapeAnimationSpeed", 0.0))
        except TypeError, ValueError:
            raise werkzeug.exceptions.BadRequest(
                "Invalid shapeAnimationSpeed"
            ) from None
        if not math.isfinite(shape_animation_speed):
            raise werkzeug.exceptions.BadRequest("Invalid shapeAnimationSpeed")
        if shape_animation_speed:
            svg = self.replace_animation_duration(
                shape_animation_speed=shape_animation_speed, svg=svg
            )
        return request.prepare_response(
            svg,
            [
                ("Content-type", "image/svg+xml"),
                ("Cache-control", f"max-age={http.STATIC_CACHE_LONG}"),
            ],
        )

    @http.route(
        [
            "/web_editor/image_shape/<string:img_key>/<module>/<path:filename>",
            "/html_editor/image_shape/<string:img_key>/<module>/<path:filename>",
        ],
        type="http",
        auth="public",
        website=True,
    )
    def image_shape(self, module, filename, img_key, **kwargs):
        if module == "web_editor":
            module = "html_builder"
        svg = self._get_shape_svg(module, "image_shapes", filename)

        record = request.env["ir.binary"]._get_record(img_key)
        stream = request.env["ir.binary"]._get_stream_image_from_record(record)
        if stream.type == "url":
            return stream.prepare_response()

        image = stream.read()
        if record.mimetype == "image/webp":
            width, height = (str(size) for size in get_webp_size(image))
        else:
            img = binary_to_image(image)
            width, height = (str(size) for size in img.size)
        root = etree.fromstring(svg)

        if root.attrib.get("data-forced-size"):
            svgHeight = float(root.attrib.get("height"))
            svgWidth = float(root.attrib.get("width"))
            svgAspectRatio = svgWidth / svgHeight
            height = str(float(width) / svgAspectRatio)

        root.attrib.update({"width": width, "height": height})
        svg, _ = self._update_svg_colors(
            kwargs, etree.tostring(root, pretty_print=True).decode("utf-8")
        )
        uri = image_data_uri(b64encode(image))
        svg = svg.replace('<image xlink:href="', f'<image xlink:href="{uri}')

        return request.prepare_response(
            svg,
            [
                ("Content-type", "image/svg+xml"),
                ("Cache-control", f"max-age={http.STATIC_CACHE_LONG}"),
            ],
        )

    @http.route(
        ["/web_editor/generate_text", "/html_editor/generate_text"],
        type="jsonrpc",
        auth="user",
    )
    def generate_text(self, prompt, conversation_history):
        try:
            IrConfigParameter = request.env["ir.config_parameter"].sudo()
            olg_api_endpoint = IrConfigParameter.get_param(
                "html_editor.olg_api_endpoint", DEFAULT_OLG_ENDPOINT
            )
            database_id = IrConfigParameter.get_param("database.uuid")
            response = iap_tools.iap_jsonrpc(
                olg_api_endpoint + "/api/olg/1/chat",
                params={
                    "prompt": prompt,
                    "conversation_history": conversation_history or [],
                    "database_id": database_id,
                },
                timeout=30,
                env=request.env,
            )
            if response["status"] == "success":
                return response["content"]
            elif response["status"] == "error_prompt_too_long":
                raise UserError(
                    _("Sorry, your prompt is too long. Try to say it in fewer words.")
                )
            elif response["status"] == "limit_call_reached":
                raise UserError(
                    _(
                        "You have reached the maximum number of requests for this service. Try again later."
                    )
                )
            else:
                raise UserError(
                    _(
                        "Sorry, we could not generate a response. Please try again later."
                    )
                )
        except AccessError:
            raise AccessError(_("Oops, it looks like our AI is unreachable!")) from None

    @http.route(
        ["/web_editor/get_ice_servers", "/html_editor/get_ice_servers"],
        type="jsonrpc",
        auth="user",
    )
    def get_ice_servers(self):
        return request.env["mail.ice.server"]._get_ice_servers()

    @http.route(
        ["/web_editor/bus_broadcast", "/html_editor/bus_broadcast"],
        type="jsonrpc",
        auth="user",
    )
    def bus_broadcast(self, model_name, field_name, res_id, bus_data):
        if model_name not in request.env:
            raise werkzeug.exceptions.BadRequest

        document = request.env[model_name].browse([res_id])
        if not document.exists():
            raise werkzeug.exceptions.NotFound

        document.check_access("read")
        document.check_access("write")
        field = document._fields.get(field_name)
        if not field:
            raise werkzeug.exceptions.BadRequest
        document._check_field_access(field, "read")
        document._check_field_access(field, "write")

        channel = (
            request.db,
            "editor_collaboration",
            model_name,
            field_name,
            int(res_id),
        )
        bus_data.update(
            {"model_name": model_name, "field_name": field_name, "res_id": res_id}
        )
        request.env["bus.bus"]._sendone(channel, "editor_collaboration", bus_data)

    @http.route(
        "/html_editor/link_preview_external",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
    )
    def link_preview_metadata(self, preview_url):
        link_preview_data = link_preview.get_link_preview_from_url(
            preview_url, link_preview.get_link_preview_session(request.env)
        )
        if link_preview_data and link_preview_data.get("og_description"):
            link_preview_data["og_description"] = html.fromstring(
                link_preview_data["og_description"]
            ).text_content()
        return link_preview_data

    @http.route(
        "/html_editor/link_preview_internal",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
    )
    def link_preview_metadata_internal(self, preview_url):
        try:
            Actions = request.env["ir.actions.actions"]
            context = dict(request.env.context)
            parsed_preview_url = urlparse(preview_url)
            words = parsed_preview_url.path.strip("/").split("/")
            last_segment = words[-1]

            if not (
                last_segment.isnumeric()
                and (
                    parsed_preview_url.path.startswith("/odoo")
                    or parsed_preview_url.path.startswith("/web")
                    or parsed_preview_url.path.startswith("/@/")
                )
            ):
                link_preview_data = self.link_preview_metadata(preview_url)
                result = {}
                if link_preview_data and link_preview_data.get("og_description"):
                    result["description"] = link_preview_data["og_description"]
                return result

            record_id = int(words.pop())
            action_name = words.pop()
            model_name = action_name.removeprefix("m-")
            if (
                (action_name.startswith("m-") or "." in action_name)
                and model_name in request.env
                and not request.env[model_name]._abstract
            ):
                model = request.env[model_name].with_context(context)
            else:
                action_sudo = Actions._get_action_by_path(action_name).sudo()
                if not action_sudo:
                    return {
                        "error_msg": _(
                            "Action %s not found, link preview is not available, please check your url is correct",
                            action_name,
                        )
                    }
                if action_sudo._name != "ir.actions.act_window":
                    return {
                        "other_error_msg": _(
                            "Action %s is not a window action, link preview is not available",
                            action_name,
                        )
                    }

                model = request.env[action_sudo.res_model].with_context(context)

            record = model.browse(record_id)

            result = {}
            if "description" in record:
                result["description"] = (
                    html.fromstring(record.description).text_content()
                    if record.description
                    else ""
                )

            if "link_preview_name" in record:
                result["link_preview_name"] = record.link_preview_name
            elif "display_name" in record:
                result["display_name"] = record.display_name

            return result
        except MissingError as e:
            return {
                "error_msg": _(
                    "Link preview is not available because %s, please check if your url is correct",
                    str(e),
                )
            }
        except Exception as e:
            return {"other_error_msg": str(e)}

    @http.route(
        ["/html_editor/media_library_search"], type="jsonrpc", auth="user", website=True
    )
    def media_library_search(self, **params):
        ICP = request.env["ir.config_parameter"].sudo()
        endpoint = ICP.get_param(
            "html_editor.media_library_endpoint", DEFAULT_LIBRARY_ENDPOINT
        )
        params["dbuuid"] = ICP.get_param("database.uuid")
        response = request.env["ir.egress"].request(
            "POST",
            f"{endpoint}/media-library/1/search",
            purpose="media_library",
            data=params,
            timeout=5,
        )
        if (
            response.status_code == requests.codes.ok
            and response.headers["content-type"] == "application/json"
        ):
            return response.json()
        else:
            return {"error": response.status_code}
