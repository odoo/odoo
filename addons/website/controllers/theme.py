"""Theme customisation, font upload and the assets editor.

Mixed into `Website` in `main.py` rather than registered as a controller of its
own: every method stays on that class, so `website_sale`'s override of
`theme_customize_data` keeps working unchanged, and so does every `self.` call
between these methods and the ones that stayed.
"""

import base64
import binascii
import logging
import re
import zipfile
import zlib
from io import BytesIO

import werkzeug.exceptions
from lxml import etree

from odoo import _, http
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.tools.json import scriptsafe as json

logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

MAX_FONT_FILE_SIZE = 10 * 1024 * 1024
MAX_FONT_UPLOAD_SIZE = 100 * 1024 * 1024
MAX_FONT_ARCHIVE_SIZE = 100 * 1024 * 1024
MAX_FONT_ARCHIVE_ENTRIES = 1000
SUPPORTED_FONT_EXTENSIONS = ["ttf", "woff", "woff2", "otf"]


def _font_content_matches_extension(filename, data):
    ext = filename.rsplit(".")[-1].lower()
    if ext == "otf":
        return data.startswith(b"OTTO")
    elif ext == "woff":
        return data.startswith(b"wOFF")
    elif ext == "woff2":
        return data.startswith(b"wOF2")
    elif ext == "ttf":
        TOC_OFFSET = 12
        TOC_ENTRY_LENGTH = 16
        table_size = int.from_bytes(data[4:6], "big") * TOC_ENTRY_LENGTH
        if TOC_OFFSET + table_size > len(data):
            return False
        mandatory_tags = {
            b"cmap",
            b"glyf",
            b"head",
            b"hhea",
            b"hmtx",
            b"loca",
            b"maxp",
            b"name",
            b"post",
        }
        for offset in range(TOC_OFFSET, TOC_OFFSET + table_size, TOC_ENTRY_LENGTH):
            tag = data[offset : offset + 4]
            mandatory_tags.discard(tag)
        return not mandatory_tags
    return False


def _create_font_attachment(font, data):
    ext = font["name"].rsplit(".")[-1].lower()
    font["mimetype"] = f"font/{ext}"
    attachment = request.env["ir.attachment"].create(
        {
            "name": font["name"],
            "mimetype": font["mimetype"],
            "raw": data,
            "public": True,
        }
    )
    font["id"] = attachment.id
    font["url"] = f"/web/content/{attachment.id}/{font['name']}"
    _debug.lifecycle(
        "font_attachment_created", name=font["name"], attachment=attachment.id
    )
    return font


class WebsiteThemeRoutes:
    def _get_customization_records(self, keys, is_view_data):
        model = "ir.ui.view" if is_view_data else "ir.asset"
        Model = request.env[model].with_context(active_test=False)
        domain = Domain("key", "in", keys) & request.website.website_domain()
        return Model.search(domain)._filtered_most_specific()

    @http.route(
        ["/website/theme_customize_data_get"],
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def theme_customize_data_get(self, keys, is_view_data):
        records = self._get_customization_records(keys, is_view_data)
        return records.filtered("active").mapped("key")

    @http.route(
        ["/website/theme_customize_data"], type="jsonrpc", auth="user", website=True
    )
    def theme_customize_data(
        self, is_view_data, enable=None, disable=None, reset_view_arch=False
    ):
        if disable:
            records = self._get_customization_records(disable, is_view_data).filtered(
                "active"
            )
            _debug.lifecycle(
                "theme_customize",
                action="disable",
                views=is_view_data,
                records=records,
                reset_arch=reset_view_arch,
            )
            if reset_view_arch:
                records.reset_arch(mode="hard")
            records.write({"active": False})

        if enable:
            records = self._get_customization_records(enable, is_view_data)
            enabled = records.filtered(lambda x: not x.active)
            _debug.lifecycle(
                "theme_customize", action="enable", views=is_view_data, records=enabled
            )
            enabled.write({"active": True})

    @http.route(
        ["/website/theme_customize_bundle_reload"],
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def theme_customize_bundle_reload(self):
        return {
            "web.assets_frontend": request.env["ir.qweb"]._get_asset_link_urls(
                "web.assets_frontend", request.session.debug
            ),
        }

    @http.route(
        ["/website/update_footer_template"], type="jsonrpc", auth="user", website=True
    )
    def update_footer_template(self, template_key, possible_values):
        views_enable = [template_key]
        views_disable = self.theme_customize_data_get(
            possible_values, is_view_data=True
        )

        width_views = {
            "container-fluid": "website.footer_copyright_content_width_fluid",
            "o_container_small": "website.footer_copyright_content_width_small",
        }

        new_template = self._get_customization_records(
            [template_key], is_view_data=True
        )
        if not new_template or not new_template[0].arch:
            return

        tree = etree.HTML(new_template[0].arch)
        container_classes = ["container", "container-fluid", "o_container_small"]
        classes_selector = " or ".join([f"hasclass('{c}')" for c in container_classes])
        res = tree.xpath(f"//div[{classes_selector}]")

        if res:
            classes = res[0].get("class").split()
            width = next((c for c in container_classes if c in classes), False)
            if width:
                view = width_views.get(width)
                if view is not None:
                    views_enable += [view]
                views_disable += [v for k, v in width_views.items() if k != width]

        self.theme_customize_data(
            is_view_data=True,
            enable=views_enable,
            disable=views_disable,
            reset_view_arch=False,
        )

    @http.route(
        ["/website/theme_upload_font"], type="jsonrpc", auth="user", website=True
    )
    def theme_upload_font(self, name, data):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            _debug.logic("font_upload_refused", reason="not_restricted_editor")
            raise werkzeug.exceptions.Forbidden

        result = []
        if len(data) > 4 * ((MAX_FONT_UPLOAD_SIZE + 2) // 3):
            _debug.logic("font_upload_refused", reason="encoded_too_large")
            raise UserError(_("Font upload exceeds maximum allowed file size"))
        try:
            binary_data = base64.b64decode(data, validate=True)
        except binascii.Error, ValueError:
            _debug.logic("font_upload_refused", reason="not_base64")
            raise UserError(_("Font upload is not valid base64 data")) from None
        if len(binary_data) > MAX_FONT_UPLOAD_SIZE:
            _debug.logic(
                "font_upload_refused", reason="too_large", bytes=len(binary_data)
            )
            raise UserError(_("Font upload exceeds maximum allowed file size"))
        readable_data = BytesIO(binary_data)
        if zipfile.is_zipfile(readable_data):
            with zipfile.ZipFile(readable_data, "r") as zip_file:
                entries = zip_file.infolist()
                expanded_size = sum(entry.file_size for entry in entries)
                logger.debug(
                    "Font archive entries=%d expanded_bytes=%d",
                    len(entries),
                    expanded_size,
                )
                if (
                    len(entries) > MAX_FONT_ARCHIVE_ENTRIES
                    or expanded_size > MAX_FONT_ARCHIVE_SIZE
                ):
                    _debug.logic(
                        "font_upload_refused",
                        reason="archive_too_large",
                        entries=len(entries),
                        expanded=expanded_size,
                    )
                    raise UserError(
                        _(
                            "Font archive exceeds maximum allowed size or number of files"
                        )
                    )
                for entry in entries:
                    if entry.file_size > MAX_FONT_FILE_SIZE:
                        _debug.logic(
                            "font_upload_refused",
                            reason="entry_too_large",
                            entry=entry.filename,
                        )
                        raise UserError(
                            _(
                                "File '%s' exceeds maximum allowed file size",
                                entry.filename,
                            )
                        )
                for entry in entries:
                    if (
                        entry.filename.rsplit(".", 1)[-1].lower()
                        not in SUPPORTED_FONT_EXTENSIONS
                        or entry.filename.startswith("__MACOSX")
                        or "/." in entry.filename
                    ):
                        continue
                    try:
                        data = zip_file.read(entry)
                    except (
                        zipfile.BadZipFile,
                        EOFError,
                        OSError,
                        RuntimeError,
                        NotImplementedError,
                        zlib.error,
                    ):
                        _debug.logic(
                            "font_upload_refused",
                            reason="corrupt_entry",
                            entry=entry.filename,
                        )
                        raise UserError(
                            _("File '%s' is corrupted", entry.filename)
                        ) from None
                    if not _font_content_matches_extension(entry.filename, data):
                        continue
                    result.append(
                        _create_font_attachment(
                            {
                                "name": f"{name}-{entry.filename.replace('/', '-')}",
                            },
                            data,
                        )
                    )
        elif len(binary_data) > MAX_FONT_FILE_SIZE:
            logger.debug("Oversized standalone font bytes=%d", len(binary_data))
            _debug.logic(
                "font_upload_refused", reason="file_too_large", bytes=len(binary_data)
            )
            raise UserError(_("File '%s' exceeds maximum allowed file size", name))
        elif name.rsplit(".", 1)[
            -1
        ].lower() in SUPPORTED_FONT_EXTENSIONS and _font_content_matches_extension(
            name, binary_data
        ):
            result.append(
                _create_font_attachment(
                    {
                        "name": name,
                    },
                    binary_data,
                )
            )
        if not result:
            _debug.logic("font_upload_refused", reason="unrecognized", name=name)
            raise UserError(_("File '%s' is not recognized as a font", name))
        _debug.lifecycle("fonts_uploaded", name=name, fonts=len(result))
        return result

    @http.route(
        "/website/get_assets_editor_resources",
        type="jsonrpc",
        auth="user",
        website=True,
    )
    def get_assets_editor_resources(
        self,
        key,
        get_views=True,
        get_scss=True,
        get_js=True,
        bundles=False,
        bundles_restriction=None,
        only_user_custom_files=True,
    ):
        if bundles_restriction is None:
            bundles_restriction = []
        views = (
            request.env["ir.ui.view"]
            .with_context(no_primary_children=True, __views_get_original_hierarchy=[])
            .get_related_views(key, bundles=bundles)
        )
        views = views.read(
            ["name", "id", "key", "xml_id", "arch", "active", "inherit_id"]
        )

        scss_files_data_by_bundle = []
        js_files_data_by_bundle = []

        if get_scss:
            scss_files_data_by_bundle = self._load_resources(
                "scss", views, bundles_restriction, only_user_custom_files
            )
        if get_js:
            js_files_data_by_bundle = self._load_resources(
                "js", views, bundles_restriction, only_user_custom_files
            )

        _debug.pipeline(
            "assets_editor_resources",
            key=key,
            views=len(views),
            scss_bundles=len(scss_files_data_by_bundle),
            js_bundles=len(js_files_data_by_bundle),
        )
        return {
            "views": (get_views and views) or [],
            "scss": (get_scss and scss_files_data_by_bundle) or [],
            "js": (get_js and js_files_data_by_bundle) or [],
        }

    def _load_resources(
        self, file_type, views, bundles_restriction, only_user_custom_files
    ):
        AssetsUtils = request.env["website.assets"]

        files_data_by_bundle = []
        t_call_assets_attribute = "t-js"
        if file_type == "scss":
            t_call_assets_attribute = "t-css"

        excluded_url_matcher = re.compile(r"^(.+/lib/.+)|(.+import_bootstrap.+\.scss)$")

        url_infos = {}
        seen_bundles = set()
        seen_urls = set()
        restricted_bundles = set(bundles_restriction)
        for v in views:
            for asset_call_node in etree.fromstring(v["arch"]).xpath(
                "//t[@t-call-assets]"
            ):
                attr = asset_call_node.get(t_call_assets_attribute)
                if attr and not json.loads(attr.lower()):
                    continue
                asset_name = asset_call_node.get("t-call-assets")
                if asset_name in seen_bundles or (
                    restricted_bundles and asset_name not in restricted_bundles
                ):
                    continue
                seen_bundles.add(asset_name)

                files_data = []
                for file_info in request.env["ir.qweb"]._get_asset_content(asset_name)[
                    0
                ]:
                    if file_info["url"].rpartition(".")[2] != file_type:
                        continue
                    url = file_info["url"]

                    if url in seen_urls or excluded_url_matcher.match(url):
                        continue

                    file_data = AssetsUtils._get_data_from_url(url)
                    if not file_data:
                        continue

                    url_infos[url] = file_data

                    if (
                        "/user_custom_" in url
                        or file_data["customized"]
                        or (file_type == "scss" and not only_user_custom_files)
                    ):
                        files_data.append(url)
                        seen_urls.add(url)

                if files_data:
                    files_data_by_bundle.append([asset_name, files_data])

        urls = []
        for bundle_data in files_data_by_bundle:
            urls += bundle_data[1]
        custom_attachments = AssetsUtils._get_custom_attachment(urls, op="in")

        for bundle_data in files_data_by_bundle:
            for i in range(len(bundle_data[1])):
                url = bundle_data[1][i]
                url_info = url_infos[url]

                content = AssetsUtils._get_content_from_url(
                    url, url_info, custom_attachments
                )

                bundle_data[1][i] = {
                    "url": "/%s/%s" % (url_info["module"], url_info["resource_path"]),
                    "arch": content,
                    "customized": url_info["customized"],
                }

        _debug.perf.count(
            "editor_resources_loaded",
            file_type=file_type,
            bundles=len(files_data_by_bundle),
            urls=len(urls),
        )
        return files_data_by_bundle
