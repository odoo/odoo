import base64
import logging
import re
from urllib.parse import quote, urlsplit

import requests

from odoo import api, models
from odoo.tools import escape_psql, misc
from odoo.tools.assets.constants import DOTTED_ASSET_EXTENSIONS as EXTENSIONS

_logger = logging.getLogger(__name__)

_match_asset_file_url_regex = re.compile(r"^(/_custom/([^/]+))?/(\w+)/([/\w]+\.\w+)$")

_GOOGLE_FONT_TIMEOUT = 5
_MAX_GOOGLE_FONTS = 20
_MAX_GOOGLE_FONT_SOURCES = 40
_MAX_GOOGLE_FONT_BYTES = 5 * 1024 * 1024
_GOOGLE_FONT_HEADERS = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.41 Safari/537.36",
}


class WebsiteAssets(models.AbstractModel):
    _name = "website.assets"
    _description = "Assets Utils"

    @api.model
    def reset_asset(self, url, bundle):
        custom_url = self._prepare_custom_asset_url(url, bundle)

        self._get_custom_attachment(custom_url).unlink()
        self._get_custom_asset(custom_url).unlink()

    @api.model
    def save_asset(self, url, bundle, content, file_type):
        custom_url = self._prepare_custom_asset_url(url, bundle)
        datas = base64.b64encode((content or "\n").encode("utf-8"))

        custom_attachment = self._get_custom_attachment(custom_url)
        if custom_attachment:
            custom_attachment.write({"datas": datas})
            self.env.registry.clear_cache("assets")
        else:
            new_attach = {
                "name": url.split("/")[-1],
                "type": "binary",
                "mimetype": ((file_type == "js" and "text/javascript") or "text/scss"),
                "datas": datas,
                "url": custom_url,
                **self._add_website_id({}),
            }
            self.env["ir.attachment"].create(new_attach)

            IrAsset = self.env["ir.asset"]
            new_asset = {
                "path": custom_url,
                "target": url,
                "directive": "replace",
                **self._add_website_id({}),
            }
            target_asset = self._get_custom_asset(url)
            if target_asset:
                new_asset["name"] = target_asset.name + " override"
                new_asset["bundle"] = target_asset.bundle
                new_asset["sequence"] = target_asset.sequence
            else:
                new_asset["name"] = "%s: replace %s" % (
                    bundle,
                    custom_url.split("/")[-1],
                )
                new_asset["bundle"] = IrAsset._get_bundle_containing_path(url, bundle)
            IrAsset.create(new_asset)

    @api.model
    def _get_content_from_url(self, url, url_info=None, custom_attachments=None):
        if url_info is None:
            url_info = self._get_data_from_url(url)

        if url_info["customized"]:
            attachment = None
            if custom_attachments is None:
                attachment = self._get_custom_attachment(url)
            else:
                attachment = custom_attachments.filtered(lambda r: r.url == url)
            return (attachment and base64.b64decode(attachment.datas)) or False

        with misc.file_open(url.strip("/"), "rb", filter_ext=EXTENSIONS) as f:
            return f.read()

    @api.model
    def _get_data_from_url(self, url):
        m = _match_asset_file_url_regex.match(url)
        if not m:
            return False
        return {
            "module": m.group(3),
            "resource_path": m.group(4),
            "customized": bool(m.group(1)),
            "bundle": m.group(2) or False,
        }

    @api.model
    def _prepare_custom_asset_url(self, url, bundle_xmlid):
        return f"/_custom/{bundle_xmlid}{url}"

    @api.model
    def update_scss_customization(self, url, values):
        IrAttachment = self.env["ir.attachment"]
        if "color-palettes-name" in values:
            self.reset_asset(
                "/website/static/src/scss/options/colors/user_color_palette.scss",
                "web.assets_frontend",
            )
            self.reset_asset(
                "/website/static/src/scss/options/colors/user_gray_color_palette.scss",
                "web.assets_frontend",
            )
            self.update_scss_customization(
                "/website/static/src/scss/options/colors/user_theme_color_palette.scss",
                {
                    "success": "null",
                    "info": "null",
                    "warning": "null",
                    "danger": "null",
                },
            )
            preset_gradients = {f"o-cc{cc}-bg-gradient": "null" for cc in range(1, 6)}
            self.update_scss_customization(
                "/website/static/src/scss/options/user_values.scss",
                {
                    "menu-gradient": "null",
                    "menu-secondary-gradient": "null",
                    "footer-gradient": "null",
                    "copyright-gradient": "null",
                    **preset_gradients,
                },
            )

        delete_attachment_id = values.pop("delete-font-attachment-id", None)
        if delete_attachment_id:
            delete_attachment_id = int(delete_attachment_id)
            IrAttachment.search(
                [
                    "|",
                    ("id", "=", delete_attachment_id),
                    ("original_id", "=", delete_attachment_id),
                    ("name", "like", "google-font"),
                ]
            ).unlink()

        google_local_fonts = values.get("google-local-fonts")
        if google_local_fonts and google_local_fonts != "null":
            google_local_fonts = dict(
                re.findall(r"'([^']+)': '?(\d*)", google_local_fonts)
            )
            google_local_fonts = self._localize_google_fonts(google_local_fonts)
            values["google-local-fonts"] = (
                str(google_local_fonts).replace("{", "(").replace("}", ")")
            )

        custom_url = self._prepare_custom_asset_url(url, "web.assets_frontend")
        updatedFileContent = self._get_content_from_url(
            custom_url
        ) or self._get_content_from_url(url)
        updatedFileContent = updatedFileContent.decode("utf-8")
        for name, value in values.items():
            if isinstance(value, str):
                value = re.sub(
                    r"var\(--([0-9]+)\)",
                    lambda matchobj: "var(--#{" + matchobj.group(1) + "})",
                    value,
                )
            pattern = "'%s': %%s,\n" % name
            regex = re.compile("'%s': .+,\n" % re.escape(name))
            replacement = pattern % value
            if regex.search(updatedFileContent):
                updatedFileContent = re.sub(regex, replacement, updatedFileContent)
            else:
                updatedFileContent = re.sub(
                    r"^( *)(.*hook.*)",
                    r"\1%s\1\2" % replacement,
                    updatedFileContent,
                    count=1,
                    flags=re.MULTILINE,
                )

        self.save_asset(url, "web.assets_frontend", updatedFileContent, "scss")

    def _localize_google_fonts(self, google_local_fonts):
        resolved = {}
        fetched = 0
        for font_name, size in google_local_fonts.items():
            if size:
                resolved[font_name] = int(size)
                continue
            if fetched >= _MAX_GOOGLE_FONTS:
                _logger.warning(
                    "Refusing to fetch more than %s Google fonts in one save; "
                    "%r left online.",
                    _MAX_GOOGLE_FONTS,
                    font_name,
                )
                continue
            fetched += 1
            attachment_id = self._get_google_local_font(font_name)
            if attachment_id:
                resolved[font_name] = attachment_id
            else:
                _logger.warning(
                    "Could not localise Google font %r; leaving it online.",
                    font_name,
                )
        return resolved

    def _get_google_local_font(self, font_name):
        IrAttachment = self.env["ir.attachment"]
        css = self._http_get_google_font(
            f"https://fonts.googleapis.com/css?family={quote(font_name)}"
            ":300,300i,400,400i,700,700i&display=swap",
            expect_binary=False,
        )
        if css is None:
            return None
        font_content = css.decode()

        font_family_attachments = IrAttachment
        source_count = 0

        def replace_src(match):
            nonlocal source_count, font_family_attachments
            statement = match.group()
            m = re.match(r"src: url\(([^\)]+)\) (.+)", statement)
            if not m:
                return statement
            if source_count >= _MAX_GOOGLE_FONT_SOURCES:
                _logger.warning(
                    "Google font %r exposes more than %s sources; truncating.",
                    font_name,
                    _MAX_GOOGLE_FONT_SOURCES,
                )
                return statement
            source_count += 1
            url, font_format = m.groups()
            content = self._http_get_google_font(url, expect_binary=True)
            if content is None:
                return statement
            name = urlsplit(url).path.lstrip("/").replace("/", "-")
            attachment = IrAttachment.create(
                {
                    "name": f"google-font-{name}",
                    "type": "binary",
                    "datas": base64.b64encode(content),
                    "public": True,
                }
            )
            font_family_attachments += attachment
            return "src: url(/web/content/%s/%s) %s" % (
                attachment.id,
                name,
                font_format,
            )

        font_content = re.sub(r"src: url\(.+\)", replace_src, font_content)
        attach_font = IrAttachment.create(
            {
                "name": f"{font_name} (google-font)",
                "type": "binary",
                "datas": base64.encodebytes(font_content.encode()),
                "mimetype": "text/css",
                "public": True,
            }
        )
        if font_family_attachments:
            font_family_attachments.original_id = attach_font.id
        return attach_font.id

    def _http_get_google_font(self, url, *, expect_binary):
        try:
            with self.env["ir.egress"].request(
                "GET",
                url,
                purpose="google_fonts",
                timeout=_GOOGLE_FONT_TIMEOUT,
                headers=_GOOGLE_FONT_HEADERS,
                stream=True,
            ) as response:
                response.raise_for_status()
                if expect_binary:
                    content_type = response.headers.get("content-type", "").lower()
                    if not any(
                        token in content_type
                        for token in ("font", "woff", "octet-stream")
                    ):
                        _logger.warning(
                            "Unexpected content-type %r for Google font %s",
                            content_type,
                            url,
                        )
                        return None
                chunks = []
                total = 0
                for chunk in response.iter_content(64 * 1024):
                    total += len(chunk)
                    if total > _MAX_GOOGLE_FONT_BYTES:
                        _logger.warning(
                            "Google Fonts resource exceeds %s bytes: %s",
                            _MAX_GOOGLE_FONT_BYTES,
                            url,
                        )
                        return None
                    chunks.append(chunk)
                return b"".join(chunks)
        except requests.RequestException:
            _logger.warning("Google Fonts request failed: %s", url)
            return None

    @api.model
    def _get_custom_attachment(self, custom_url, op="="):
        assert op in ("in", "="), "Invalid operator"
        if self.env.user.has_group("website.group_website_designer"):
            self = self.sudo()
        website = self.env["website"].get_current_website()
        res = self.env["ir.attachment"].search([("url", op, custom_url)])
        return res.with_context(website_id=website.id).filtered(
            lambda x: x.website_id == website
        )

    @api.model
    def _get_custom_asset(self, custom_url):
        website = self.env["website"].get_current_website()
        url = custom_url[1:] if custom_url.startswith(("/", "\\")) else custom_url
        res = self.env["ir.asset"].search([("path", "like", escape_psql(url))])
        return res.with_context(website_id=website.id)._filtered_most_specific()

    @api.model
    def _add_website_id(self, values):
        website = self.env["website"].get_current_website()
        values["website_id"] = website.id
        return values
