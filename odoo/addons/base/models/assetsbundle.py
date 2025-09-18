import functools
import hashlib
import io
import logging
import os
import re
import textwrap
import uuid
from collections import OrderedDict
from contextlib import closing, suppress
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Any

from lxml import etree
from rjsmin import jsmin as rjsmin

from odoo import release
from odoo.api import SUPERUSER_ID
from odoo.http import request
from odoo.libs.constants import (
    ANY_UNIQUE,
    SCRIPT_EXTENSIONS,
    STYLE_EXTENSIONS,
)
from odoo.libs.constants import (
    DOTTED_ASSET_EXTENSIONS as EXTENSIONS,
)
from odoo.libs.profiling.sourcemap_generator import SourceMapGenerator
from odoo.libs.web.js_transpiler import is_odoo_module, transpile_javascript
from odoo.tools import SQL, OrderedSet, misc, profiler
from odoo.tools.json import scriptsafe as json
from odoo.tools.misc import file_open, file_path

_logger = logging.getLogger(__name__)


class CompileError(RuntimeError):
    pass


class AssetError(Exception):
    pass


class AssetNotFoundError(AssetError):
    pass


AssetNotFound = AssetNotFoundError  # backward-compatibility alias


class XMLAssetError(Exception):
    pass


class AssetsBundle:
    rx_css_import = re.compile(r"(@import[^;{]+;?)", re.MULTILINE)
    rx_preprocess_imports = re.compile(r"""(@import\s?['"]([^'"]+)['"](;?))""")
    rx_css_split = re.compile(r"\/\*\! ([a-f0-9-]+) \*\/")

    TRACKED_BUNDLES = ["web.assets_web"]

    def __init__(
        self,
        name: str,
        files: list[dict[str, Any]],
        external_assets: tuple | list = (),
        env: Any = None,
        css: bool = True,
        js: bool = True,
        debug_assets: bool = False,
        rtl: bool = False,
        assets_params: dict[str, Any] | None = None,
        autoprefix: bool = False,
    ) -> None:
        """
        :param name: bundle name
        :param files: files to be added to the bundle
        :param css: if css is True, the stylesheets files are added to the bundle
        :param js: if js is True, the javascript files are added to the bundle
        """
        self.name = name
        self.env = request.env if env is None else env
        self.javascripts = []
        self.templates = []
        self.stylesheets = []
        self.css_errors = []
        self.files = files
        self.rtl = rtl
        self.assets_params = assets_params or {}
        self.autoprefix = autoprefix
        self.has_css = css
        self.has_js = js
        self._checksum_cache = {}
        self.is_debug_assets = debug_assets
        self.external_assets = [
            url
            for url in external_assets
            if (css and url.rpartition(".")[2] in STYLE_EXTENSIONS)
            or (js and url.rpartition(".")[2] in SCRIPT_EXTENSIONS)
        ]

        # asset-wide html "media" attribute
        for f in files:
            extension = f["url"].rpartition(".")[2]
            params = {
                "url": f["url"],
                "filename": f["filename"],
                "inline": f["content"],
                "last_modified": (
                    None if self.is_debug_assets else f.get("last_modified")
                ),
            }
            if css:
                css_params = {
                    "rtl": self.rtl,
                    "autoprefix": self.autoprefix,
                }
                match extension:
                    case "sass" | "scss":
                        self.stylesheets.append(
                            ScssStylesheetAsset(self, **params, **css_params)
                        )
                    case "less":
                        self.stylesheets.append(
                            LessStylesheetAsset(self, **params, **css_params)
                        )
                    case "css":
                        self.stylesheets.append(
                            StylesheetAsset(self, **params, **css_params)
                        )
            if js:
                match extension:
                    case "js":
                        self.javascripts.append(JavascriptAsset(self, **params))
                    case "xml":
                        self.templates.append(XMLAsset(self, **params))

    def get_links(self) -> list[str]:
        """
        :returns a list of tuple. a tuple can be (url, None) or (None, inlineContent)
        """
        response = []

        if self.has_css and self.stylesheets:
            response.append(self.get_link("css"))

        if self.has_js and self.javascripts:
            response.append(self.get_link("js"))

        return self.external_assets + response

    def get_link(self, asset_type: str) -> str:
        unique = self.get_version(asset_type) if not self.is_debug_assets else "debug"
        extension = asset_type if self.is_debug_assets else f"min.{asset_type}"
        return self.get_asset_url(unique=unique, extension=extension)

    def get_version(self, asset_type: str) -> str:
        return self.get_checksum(asset_type)[0:7]

    def get_checksum(self, asset_type: str) -> str:
        """
        Not really a full checksum.
        We compute a SHA512/256 on the rendered bundle + combined linked files last_modified date
        """
        if asset_type not in self._checksum_cache:
            if asset_type == "css":
                assets = self.stylesheets
            elif asset_type == "js":
                assets = self.javascripts + self.templates
            else:
                raise ValueError(f"Asset type {asset_type} not known")

            h = hashlib.sha256()
            for asset in assets:
                h.update(asset.unique_descriptor.encode())
            self._checksum_cache[asset_type] = h.hexdigest()
        return self._checksum_cache[asset_type]

    def get_asset_url(
        self,
        unique: str = ANY_UNIQUE,
        extension: str = "%",
        ignore_params: bool = False,
    ) -> str:
        direction = ".rtl" if self.is_css(extension) and self.rtl else ""
        autoprefixed = (
            ".autoprefixed" if self.is_css(extension) and self.autoprefix else ""
        )
        bundle_name = f"{self.name}{direction}{autoprefixed}.{extension}"
        return self.env["ir.asset"]._get_asset_bundle_url(
            bundle_name, unique, self.assets_params, ignore_params
        )

    def _unlink_attachments(self, attachments: Any) -> None:
        """Unlinks attachments without actually calling unlink, so that the ORM cache is not cleared.

        Specifically, if an attachment is generated while a view is rendered, clearing the ORM cache
        could unload fields loaded with a sudo(), and expected to be readable by the view.
        Such a view would be website.layout when main_object is an ir.ui.view.
        """
        to_delete = {attach.store_fname for attach in attachments if attach.store_fname}
        table = SQL.identifier(attachments._table)
        self.env.cr.execute(
            SQL(
                """DELETE FROM %s WHERE id IN (
            SELECT id FROM %s WHERE id = ANY(%s) FOR NO KEY UPDATE SKIP LOCKED
        )""",
                table,
                table,
                list(attachments.ids),
            )
        )
        for fpath in to_delete:
            attachments._file_delete(fpath)

    def is_css(self, extension: str) -> bool:
        return extension in ["css", "min.css", "css.map"]

    def _clean_attachments(self, extension: str, keep_url: str) -> bool:
        """Takes care of deleting any outdated ir.attachment records associated to a bundle before
        saving a fresh one.

        When `extension` is js we need to check that we are deleting a different version (and not *any*
        version) because, as one of the creates in `save_attachment` can trigger a rollback, the
        call to `clean_attachments ` is made at the end of the method in order to avoid the rollback
        of an ir.attachment unlink (because we cannot rollback a removal on the filestore), thus we
        must exclude the current bundle.
        """
        ira = self.env["ir.attachment"]
        to_clean_pattern = self.get_asset_url(
            unique=ANY_UNIQUE,
            extension=extension,
        )
        domain = [
            ("url", "=like", to_clean_pattern),
            ("url", "!=", keep_url),
            ("public", "=", True),
        ]

        attachments = ira.sudo().search(domain)
        # avoid to invalidate cache if it's already empty (mainly useful for test)

        if attachments:
            _logger.info(
                "Deleting attachments %s (matching %s) because it was replaced with %s",
                attachments.ids,
                to_clean_pattern,
                keep_url,
            )
            self._unlink_attachments(attachments)
            # clear_cache was removed

        return True

    def get_attachments(self, extension: str, ignore_version: bool = False) -> Any:
        """Return the ir.attachment records for a given bundle. This method takes care of mitigating
        an issue happening when parallel transactions generate the same bundle: while the file is not
        duplicated on the filestore (as it is stored according to its hash), there are multiple
        ir.attachment records referencing the same version of a bundle. As we don't want to source
        multiple time the same bundle in our `to_html` function, we group our ir.attachment records
        by file name and only return the one with the max id for each group.

        :param extension: file extension (js, min.js, css)
        :param ignore_version: if ignore_version, the url contains a version => web/assets/%/name.extension
                                (the second '%' corresponds to the version),
                               else: the url contains a version equal to that of the self.get_version(type)
                                => web/assets/self.get_version(type)/name.extension.
        """
        unique = (
            ANY_UNIQUE
            if ignore_version
            else self.get_version("css" if self.is_css(extension) else "js")
        )
        url_pattern = self.get_asset_url(
            unique=unique,
            extension=extension,
        )
        query = """
             SELECT max(id)
               FROM ir_attachment
              WHERE create_uid = %s
                AND url like %s
                AND res_model = 'ir.ui.view'
                AND res_id = 0
                AND public = true
           GROUP BY name
           ORDER BY name
        """
        self.env.cr.execute(query, [SUPERUSER_ID, url_pattern])

        attachment_id = [r[0] for r in self.env.cr.fetchall()]
        if not attachment_id and not ignore_version:
            fallback_url_pattern = self.get_asset_url(
                unique=unique,
                extension=extension,
                ignore_params=True,
            )
            self.env.cr.execute(query, [SUPERUSER_ID, fallback_url_pattern])
            similar_attachment_ids = [r[0] for r in self.env.cr.fetchall()]
            if similar_attachment_ids:
                similar = (
                    self.env["ir.attachment"].sudo().browse(similar_attachment_ids[0])
                )
                _logger.info(
                    "Found a similar attachment for %s, copying from %s",
                    url_pattern,
                    similar.url,
                )
                url = url_pattern
                values = {
                    "name": similar.name,
                    "mimetype": similar.mimetype,
                    "res_model": "ir.ui.view",
                    "res_id": False,
                    "type": "binary",
                    "public": True,
                    "raw": similar.raw,
                    "url": url,
                }
                attachment = (
                    self.env["ir.attachment"].with_user(SUPERUSER_ID).create(values)
                )
                attachment_id = attachment.id
                self._clean_attachments(extension, url)

        return self.env["ir.attachment"].sudo().browse(attachment_id)

    def save_attachment(self, extension: str, content: str) -> Any:
        """Record the given bundle in an ir.attachment and delete
        all other ir.attachments referring to this bundle (with the same name and extension).

        :param extension: extension of the bundle to be recorded
        :param content: bundle content to be recorded

        :return the ir.attachment records for a given bundle.
        """
        if extension not in (
            "js",
            "min.js",
            "js.map",
            "css",
            "min.css",
            "css.map",
            "xml",
            "min.xml",
        ):
            raise ValueError(f"Invalid asset extension {extension!r}")
        ira = self.env["ir.attachment"]

        # Set user direction in name to store two bundles
        # 1 for ltr and 1 for rtl, this will help during cleaning of assets bundle
        # and allow to only clear the current direction bundle
        # (this applies to css bundles only)
        fname = f"{self.name}.{extension}"
        mimetype = (
            "text/css"
            if extension in ["css", "min.css"]
            else (
                "text/xml"
                if extension in ["xml", "min.xml"]
                else (
                    "application/json"
                    if extension in ["js.map", "css.map"]
                    else "application/javascript"
                )
            )
        )
        unique = self.get_version("css" if self.is_css(extension) else "js")
        url = self.get_asset_url(
            unique=unique,
            extension=extension,
        )
        values = {
            "name": fname,
            "mimetype": mimetype,
            "res_model": "ir.ui.view",
            "res_id": False,
            "type": "binary",
            "public": True,
            "raw": content.encode("utf8"),
            "url": url,
        }
        attachment = ira.with_user(SUPERUSER_ID).create(values)

        _logger.info(
            "Generating a new asset bundle attachment %s (id:%s)",
            attachment.url,
            attachment.id,
        )

        self._clean_attachments(extension, url)

        # For end-user assets (common and backend), send a message on the bus
        # to invite the user to refresh their browser
        if self.env and "bus.bus" in self.env and self.name in self.TRACKED_BUNDLES:
            self.env["bus.bus"]._sendone(
                "broadcast",
                "bundle_changed",
                {"server_version": release.version},  # Needs to be dynamically imported
            )
            _logger.debug("Asset Changed: bundle: %s -- version: %s", self.name, unique)

        return attachment

    def js(self) -> Any:
        is_minified = not self.is_debug_assets
        extension = "min.js" if is_minified else "js"
        js_attachment = self.get_attachments(extension)

        if not js_attachment:
            template_bundle = ""
            if self.templates:
                templates = self.generate_xml_bundle()
                template_bundle = textwrap.dedent(f"""

                    /*******************************************
                    *  Templates                               *
                    *******************************************/

                    odoo.define("{self.name}.bundle.xml", ["@web/core/templates"], function(require) {{
                        "use strict";
                        const {{ checkPrimaryTemplateParents, registerTemplate, registerTemplateExtension }} = require("@web/core/templates");
                        /* {self.name} */
                        {templates}
                    }});
                """)

            if is_minified:
                content_bundle = ";\n".join(
                    asset.minify() for asset in self.javascripts
                )
                content_bundle += template_bundle
                js_attachment = self.save_attachment(extension, content_bundle)
            else:
                js_attachment = self.js_with_sourcemap(template_bundle=template_bundle)

        return js_attachment[0]

    def js_with_sourcemap(self, template_bundle: str | None = None) -> Any:
        """Create the ir.attachment representing the not-minified content of the bundleJS
        and create/modify the ir.attachment representing the linked sourcemap.

        :return ir.attachment representing the un-minified content of the bundleJS
        """
        sourcemap_attachment = self.get_attachments("js.map") or self.save_attachment(
            "js.map", ""
        )
        generator = SourceMapGenerator(
            source_root="/".join(
                [".." for i in range(len(self.get_asset_url().split("/")) - 2)]
            )
            + "/",
        )
        content_bundle_list = []
        content_line_count = 0
        line_header = 5  # number of lines added by with_header()
        for asset in self.javascripts:
            if asset.is_transpiled:
                # '+ 3' corresponds to the 3 lines added at the beginning of the file during transpilation.
                generator.add_source(
                    asset.url,
                    asset._content,
                    content_line_count,
                    start_offset=line_header + 3,
                )
            else:
                generator.add_source(
                    asset.url,
                    asset.content,
                    content_line_count,
                    start_offset=line_header,
                )

            content_bundle_list.append(asset.with_header(asset.content, minimal=False))
            content_line_count += len(asset.content.split("\n")) + line_header

        content_bundle = ";\n".join(content_bundle_list)
        if template_bundle:
            content_bundle += template_bundle

        content_bundle += "\n\n//# sourceMappingURL=" + sourcemap_attachment.url
        js_attachment = self.save_attachment("js", content_bundle)

        generator._file = js_attachment.url
        sourcemap_attachment.write({"raw": generator.get_content()})

        return js_attachment

    def generate_xml_bundle(self) -> str:
        content = []
        blocks = []
        try:
            blocks = self.xml()
        except XMLAssetError as e:
            content.append(f"throw new Error({json.dumps(str(e))});")

        def get_template(element: etree._Element) -> str:
            element.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            string = etree.tostring(element, encoding="unicode")
            return (
                string.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
            )

        names = OrderedSet()
        primary_parents = OrderedSet()
        extension_parents = OrderedSet()
        for block in blocks:
            if block["type"] == "templates":
                for element, url, inherit_from in block["templates"]:
                    if inherit_from:
                        primary_parents.add(inherit_from)
                    name = element.get("t-name")
                    names.add(name)
                    template = get_template(element)
                    content.append(
                        f'registerTemplate("{name}", `{url}`, `{template}`);'
                    )
            else:
                for inherit_from, elements in block["extensions"].items():
                    extension_parents.add(inherit_from)
                    for element, url in elements:
                        template = get_template(element)
                        content.append(
                            f'registerTemplateExtension("{inherit_from}", `{url}`, `{template}`);'
                        )

        missing_names_for_primary = primary_parents - names
        if missing_names_for_primary:
            content.append(
                f"checkPrimaryTemplateParents({json.dumps(list(missing_names_for_primary))});"
            )
        missing_names_for_extension = extension_parents - names
        if missing_names_for_extension:
            content.append(
                f'console.error("Missing (extension) parent templates: {", ".join(missing_names_for_extension)}");'
            )

        return "\n".join(content)

    def xml(self) -> list[dict[str, Any]] | str:
        """
        Create a list of blocks. A block can have one of the two types "templates" or "extensions".
        A template with no parent or template with t-inherit-mode="primary" goes in a block of type "templates".
        A template with t-inherit-mode="extension" goes in a block of type "extensions".

        Used parsed attributes:
        * `t-name`: template name
        * `t-inherit`: inherited template name.
        * 't-inherit-mode':  'primary' or 'extension'.

        :return a list of blocks
        """
        parser = etree.XMLParser(ns_clean=True, recover=True, remove_comments=True)

        blocks = []
        block = None
        for asset in self.templates:
            # Load content.
            try:
                content = asset.content.strip()
                template = (
                    content
                    if content.startswith("<odoo>")
                    else f"<templates>{asset.content}</templates>"
                )
                io_content = io.BytesIO(template.encode("utf-8"))
                content_templates_tree = etree.parse(
                    io_content, parser=parser
                ).getroot()
            except etree.ParseError as e:
                return asset.generate_error(f"Could not parse file: {e.msg}")
            # Process every templates.
            for template_tree in list(content_templates_tree):
                template_name = template_tree.get("t-name")
                inherit_from = template_tree.get("t-inherit")
                inherit_mode = None
                if inherit_from:
                    inherit_mode = template_tree.get("t-inherit-mode", "primary")
                    if inherit_mode not in ["primary", "extension"]:
                        addon = asset.url.split("/")[1]
                        return asset.generate_error(
                            self.env._(
                                'Invalid inherit mode. Module "%(module)s" and template name "%(template_name)s"',
                                module=addon,
                                template_name=template_name,
                            )
                        )
                if inherit_mode == "extension":
                    if block is None or block["type"] != "extensions":
                        block = {
                            "type": "extensions",
                            "extensions": OrderedDict(),
                        }
                        blocks.append(block)
                    block["extensions"].setdefault(inherit_from, [])
                    block["extensions"][inherit_from].append((template_tree, asset.url))
                elif template_name:
                    if block is None or block["type"] != "templates":
                        block = {"type": "templates", "templates": []}
                        blocks.append(block)
                    block["templates"].append((template_tree, asset.url, inherit_from))
                else:
                    return asset.generate_error(self.env._("Template name is missing."))
        return blocks

    def css(self) -> Any:
        is_minified = not self.is_debug_assets
        extension = "min.css" if is_minified else "css"
        attachments = self.get_attachments(extension)
        if attachments:
            return attachments

        css = self.preprocess_css()
        if self.css_errors:
            error_message = (
                "\n".join(self.css_errors)
                .replace('"', r"\"")
                .replace("\n", r"\A")
                .replace("*", r"\*")
            )
            previous_attachment = self.get_attachments(extension, ignore_version=True)
            previous_css = (
                previous_attachment.raw.decode() if previous_attachment else ""
            )
            css_error_message_header = "\n\n/* ## CSS error message ##*/"
            previous_css = previous_css.split(css_error_message_header)[0]
            css = css_error_message_header.join(
                [
                    previous_css,
                    f"""
body::before {{
  font-weight: bold;
  content: "A css error occurred, using an old style to render this page";
  position: fixed;
  left: 0;
  bottom: 0;
  z-index: 100000000000;
  background-color: #C00;
  color: #DDD;
}}

css_error_message {{
  content: "{error_message.replace('"', r'\"')}";
}}
""",
                ]
            )
            return self.save_attachment(extension, css)

        matches = []
        css = re.sub(
            self.rx_css_import,
            lambda matchobj: matches.append(matchobj.group(0)) or "",
            css,
        )

        if is_minified:
            # move up all @import rules to the top
            matches.append(css)
            css = "\n".join(matches)

            return self.save_attachment(extension, css)
        else:
            return self.css_with_sourcemap("\n".join(matches))

    def css_with_sourcemap(self, content_import_rules: str) -> Any:
        """Create the ir.attachment representing the not-minified content of the bundleCSS
        and create/modify the ir.attachment representing the linked sourcemap.

        :param content_import_rules: string containing all the @import rules to put at the beginning of the bundle
        :return ir.attachment representing the un-minified content of the bundleCSS
        """
        sourcemap_attachment = self.get_attachments("css.map") or self.save_attachment(
            "css.map", ""
        )
        debug_asset_url = self.get_asset_url(unique="debug")
        generator = SourceMapGenerator(
            source_root="/".join(
                [".." for i in range(len(debug_asset_url.split("/")) - 2)]
            )
            + "/",
        )

        # adds the @import rules at the beginning of the bundle
        content_bundle_list = [content_import_rules]
        content_line_count = len(content_import_rules.split("\n"))
        for asset in self.stylesheets:
            if asset.content:
                content = asset.with_header(asset.content)
                if asset.url:
                    generator.add_source(asset.url, content, content_line_count)
                # comments all @import rules that have been added at the beginning of the bundle
                content = re.sub(
                    self.rx_css_import,
                    lambda matchobj: f"/* {matchobj.group(0)} */",
                    content,
                )
                content_bundle_list.append(content)
                content_line_count += len(content.split("\n"))

        content_bundle = (
            "\n".join(content_bundle_list)
            + f"\n/*# sourceMappingURL={sourcemap_attachment.url} */"
        )
        css_attachment = self.save_attachment("css", content_bundle)

        generator._file = css_attachment.url
        sourcemap_attachment.write(
            {
                "raw": generator.get_content(),
            }
        )

        return css_attachment

    def preprocess_css(self, debug: bool = False, old_attachments: Any = None) -> str:
        """
        Checks if the bundle contains any sass/less content, then compiles it to css.
        If user language direction is Right to Left then consider css files to call run_rtlcss,
        css files are also stored in ir.attachment after processing done by rtlcss.
        Returns the bundle's flat css.
        """
        if self.stylesheets:
            compiled = ""
            for atype in (
                ScssStylesheetAsset,
                LessStylesheetAsset,
            ):
                assets = [
                    asset for asset in self.stylesheets if isinstance(asset, atype)
                ]
                if assets:
                    source = "\n".join([asset.get_source() for asset in assets])
                    compiled += self.compile_css(assets[0].compile, source)

            if self.autoprefix:
                compiled = self.autoprefix_css(compiled)

            # We want to run rtlcss on normal css, so merge it in compiled
            if self.rtl:
                stylesheet_assets = [
                    asset
                    for asset in self.stylesheets
                    if not isinstance(
                        asset,
                        (ScssStylesheetAsset, LessStylesheetAsset),
                    )
                ]
                compiled += "\n".join(
                    [asset.get_source() for asset in stylesheet_assets]
                )
                compiled = self.run_rtlcss(compiled)

            if not self.css_errors and old_attachments:
                self._unlink_attachments(old_attachments)
                old_attachments = None

            fragments = self.rx_css_split.split(compiled)
            at_rules = fragments.pop(0)
            if at_rules:
                # Sass and less moves @at-rules to the top in order to stay css 2.1 compatible
                self.stylesheets.insert(0, StylesheetAsset(self, inline=at_rules))
            while fragments:
                asset_id = fragments.pop(0)
                asset = next(
                    (a for a in self.stylesheets if a.id == asset_id),
                    None,
                )
                if asset is None:
                    raise RuntimeError(
                        f"CSS asset {asset_id!r} not found in stylesheets — "
                        "compiled output is out of sync with the asset list"
                    )
                asset._content = fragments.pop(0)

        return "\n".join(asset.minify() for asset in self.stylesheets)

    def compile_css(self, compiler: Any, source: str) -> str:
        """Sanitizes @import rules, remove duplicates @import rules, then compile"""
        imports = []

        def handle_compile_error(e: Exception, source: str) -> str:
            error = self.get_preprocessor_error(str(e), source=source)
            _logger.warning(error)
            self.css_errors.append(error)
            return ""

        def sanitize(matchobj: re.Match) -> str:
            ref = matchobj.group(2)
            line = f'@import "{ref}"{matchobj.group(3)}'
            if (
                "." not in ref
                and line not in imports
                and not ref.startswith((".", "/", "~"))
            ):
                imports.append(line)
                return line
            msg = (
                "Local import '%s' is forbidden for security reasons. Please remove all @import {your_file} imports in your custom files. In Odoo you have to import all files in the assets, and not through the @import statement."
                % ref
            )
            _logger.warning(msg)
            self.css_errors.append(msg)
            return ""

        source = re.sub(self.rx_preprocess_imports, sanitize, source)

        try:
            compiled = compiler(source)
        except CompileError as e:
            return handle_compile_error(e, source=source)

        return compiled.strip()

    def autoprefix_css(self, source: str) -> str:
        """Post-process compiled CSS to add required vendor prefixes."""
        compiled = source.strip()

        # Add -webkit- and -moz- vendor prefixes for `appearance` property.
        # Handles both expanded ("  appearance: none;") and compressed
        # ("{appearance:none}") output from Dart Sass.
        return re.sub(
            r"([{; \t])(appearance:\s*(\w+))(;?)",
            r"\1-webkit-appearance:\3;-moz-appearance:\3;\2\4",
            compiled,
        )

    def run_rtlcss(self, source: str) -> str:
        rtlcss = "rtlcss"
        if os.name == "nt":
            try:
                rtlcss = misc.find_in_path("rtlcss.cmd")
            except OSError:
                rtlcss = "rtlcss"

        cmd = [rtlcss, "-c", file_path("base/data/rtlcss.json"), "-"]

        try:
            rtlcss = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE, encoding="utf-8")
        except OSError:
            # Check the presence of rtlcss, if rtlcss not available then we should return normal less file
            try:
                Popen(["rtlcss", "--version"], stdout=PIPE, stderr=PIPE)
            except OSError:
                _logger.warning(
                    "You need https://rtlcss.com/ to convert css file to right to left compatiblity. Use: npm install -g rtlcss"
                )
                return source

            msg = "Could not execute command %r" % cmd[0]
            _logger.error(msg)
            self.css_errors.append(msg)
            return ""

        out, err = rtlcss.communicate(input=source)
        if rtlcss.returncode or (source and not out):
            if rtlcss.returncode:
                error = self.get_rtlcss_error(
                    err or f"Process exited with return code {rtlcss.returncode}",
                    source=source,
                )
            else:
                error = "rtlcss: error processing payload\n"
            _logger.warning("%s", error)
            self.css_errors.append(error)
            return ""
        return out.strip()

    def get_preprocessor_error(self, stderr: str, source: str | None = None) -> str:
        """Improve and remove sensitive information from sass/less compiler error messages."""
        error = stderr.split("Load paths", maxsplit=1)[0].replace(
            "  Use --trace for backtrace.", ""
        )
        error += (
            f"This error occurred while compiling the bundle '{self.name}' containing:"
        )
        for asset in self.stylesheets:
            if isinstance(asset, PreprocessedCSS):
                error += f"\n    - {asset.url or '<inline sass>'}"
        return error

    def get_rtlcss_error(self, stderr: str, source: str | None = None) -> str:
        """Improve and remove sensitive information from sass/less compilator error messages"""
        error = stderr.split("Load paths", maxsplit=1)[0].replace(
            "  Use --trace for backtrace.", ""
        )
        return f"{error}This error occurred while compiling the bundle {self.name!r} containing:"


class WebAsset:
    _content = None
    _filename = None
    _ir_attach = None
    _id = None

    def __init__(
        self,
        bundle: AssetsBundle,
        inline: str | None = None,
        url: str | None = None,
        filename: str | None = None,
        last_modified: float | None = None,
    ) -> None:
        self.bundle = bundle
        self.inline = inline
        self._filename = filename
        self.url = url
        self._last_modified = last_modified
        if not inline and not url:
            raise ValueError(
                "An asset should either be inlined or url linked, defined in bundle '%s'"
                % bundle.name
            )

    def generate_error(self, msg: str) -> str:
        msg = f"{msg!r} in file {self.url!r}"
        _logger.error(msg)  # log it in the python console in all cases.
        return msg

    @functools.cached_property
    def id(self) -> str:
        if self._id is None:
            self._id = str(uuid.uuid4())
        return self._id

    @functools.cached_property
    def unique_descriptor(self) -> str:
        return f"{self.url or self.inline},{self.last_modified}"

    @functools.cached_property
    def name(self) -> str:
        return "<inline asset>" if self.inline else self.url

    def stat(self) -> None:
        if not (self.inline or self._filename or self._ir_attach):
            try:
                # Test url against ir.attachments
                self._ir_attach = (
                    self.bundle.env["ir.attachment"]
                    .sudo()
                    ._get_serve_attachment(self.url)
                )
                self._ir_attach.ensure_one()
            except ValueError:
                raise AssetNotFoundError(f"Could not find {self.name}")

    @property
    def last_modified(self) -> float | int:
        if self._last_modified is None:
            with suppress(Exception):
                self.stat()
            if (
                self._filename and self.bundle and self.bundle.is_debug_assets
            ):  # usually _last_modified should be set exept in debug=assets
                self._last_modified = Path(self._filename).stat().st_mtime
            elif self._ir_attach:
                self._last_modified = self._ir_attach.write_date.timestamp()
            if not self._last_modified:
                self._last_modified = -1
        return self._last_modified

    @property
    def content(self) -> str:
        if self._content is None:
            self._content = self.inline or self._fetch_content()
        return self._content

    def _fetch_content(self) -> str:
        """Fetch content from file or database"""
        try:
            self.stat()
            if self._filename:
                with closing(
                    file_open(self._filename, "rb", filter_ext=EXTENSIONS)
                ) as fp:
                    return fp.read().decode("utf-8")
            else:
                return self._ir_attach.raw.decode()
        except UnicodeDecodeError:
            raise AssetError(f"{self.name} is not utf-8 encoded.")
        except OSError:
            raise AssetNotFoundError(f"File {self.name} does not exist.")
        except (AssetError, ValueError) as e:
            raise AssetError(f"Could not get content for {self.name}.") from e

    def minify(self) -> str:
        return self.content

    def with_header(self, content: str | None = None) -> str:
        if content is None:
            content = self.content
        return f"\n/* {self.name} */\n{content}"


class JavascriptAsset(WebAsset):
    def __init__(self, bundle: AssetsBundle, **kwargs: Any) -> None:
        super().__init__(bundle, **kwargs)
        self._is_transpiled = None
        self._converted_content = None

    def generate_error(self, msg: str) -> str:
        msg = super().generate_error(msg)
        return f"console.error({json.dumps(msg)});"

    @property
    def bundle_version(self) -> str:
        return self.bundle.get_version("js")

    @property
    def is_transpiled(self) -> bool:
        if self._is_transpiled is None:
            self._is_transpiled = bool(is_odoo_module(self.url, super().content))
        return self._is_transpiled

    @property
    def content(self) -> str:
        content = super().content
        if self.is_transpiled:
            if not self._converted_content:
                self._converted_content = transpile_javascript(self.url, content)
            return self._converted_content
        return content

    def minify(self) -> str:
        return self.with_header(rjsmin(self.content, keep_bang_comments=True))

    def _fetch_content(self) -> str:
        try:
            return super()._fetch_content()
        except AssetError as e:
            return self.generate_error(str(e))

    def with_header(self, content: str | None = None, minimal: bool = True) -> str:
        if minimal:
            return super().with_header(content)

        # format the header like
        #   /**************************
        #   *  Filepath: <asset_url>  *
        #   *  Lines: 42              *
        #   **************************/
        line_count = content.count("\n")
        lines = [
            f"Filepath: {self.url}",
            f"Lines: {line_count}",
        ]
        length = max(map(len, lines))
        return "\n".join(
            [
                "",
                "/" + "*" * (length + 5),
                *(f"*  {line:<{length}}  *" for line in lines),
                "*" * (length + 5) + "/",
                content,
            ]
        )


class XMLAsset(WebAsset):
    def _fetch_content(self) -> str:
        try:
            content = super()._fetch_content()
        except AssetError as e:
            return self.generate_error(str(e))

        parser = etree.XMLParser(
            ns_clean=True, remove_comments=True, resolve_entities=False
        )
        try:
            root = etree.fromstring(content.encode("utf-8"), parser=parser)
        except etree.XMLSyntaxError as e:
            return self.generate_error(f"Invalid XML template: {e.msg}")
        if root.tag in ("templates", "template"):
            return "".join(etree.tostring(el, encoding="unicode") for el in root)
        return etree.tostring(root, encoding="unicode")

    def generate_error(self, msg: str) -> str:
        msg = super().generate_error(msg)
        raise XMLAssetError(msg)

    @property
    def bundle_version(self) -> str:
        return self.bundle.get_version("js")

    def with_header(self, content: str | None = None) -> str:
        if content is None:
            content = self.content

        # format the header like
        #   <!--=========================-->
        #   <!--  Filepath: <asset_url>  -->
        #   <!--  Bundle: <name>         -->
        #   <!--  Lines: 42              -->
        #   <!--=========================-->
        line_count = content.count("\n")
        lines = [
            f"Filepath: {self.url}",
            f"Lines: {line_count}",
        ]
        length = max(map(len, lines))
        return "\n".join(
            [
                "",
                "<!--  " + "=" * length + "  -->",
                *(f"<!--  {line:<{length}}  -->" for line in lines),
                "<!--  " + "=" * length + "  -->",
                content,
            ]
        )


class StylesheetAsset(WebAsset):
    rx_import = re.compile(r"""@import\s+('|")(?!'|"|/|https?://)""", re.UNICODE)
    rx_url = re.compile(
        r"""(?<!")url\s*\(\s*('|"|)(?!'|"|/|https?://|data:|#{str)""",
        re.UNICODE,
    )
    rx_sourceMap = re.compile(r"(/\*# sourceMappingURL=.*)", re.UNICODE)
    rx_charset = re.compile(r'(@charset "[^"]+";)', re.UNICODE)

    def __init__(
        self, *args: Any, rtl: bool = False, autoprefix: bool = False, **kw: Any
    ) -> None:
        self.rtl = rtl
        self.autoprefix = autoprefix
        super().__init__(*args, **kw)

    @property
    def bundle_version(self) -> str:
        return self.bundle.get_version("css")

    @functools.cached_property
    def unique_descriptor(self) -> str:
        direction = (self.rtl and "rtl") or "ltr"
        autoprefixed = (self.autoprefix and "autoprefixed") or ""
        return (
            f"{self.url or self.inline},{self.last_modified},{direction},{autoprefixed}"
        )

    def _fetch_content(self) -> str:
        try:
            content = super()._fetch_content()
            web_dir = str(Path(self.url).parent)

            if self.rx_import:
                content = self.rx_import.sub(
                    r"""@import \1%s/""" % (web_dir,),
                    content,
                )

            if self.rx_url:
                content = self.rx_url.sub(
                    r"url(\1%s/" % (web_dir,),
                    content,
                )

            if self.rx_charset:
                # remove charset declarations, we only support utf-8
                content = self.rx_charset.sub("", content)

            return content
        except AssetError as e:
            self.bundle.css_errors.append(str(e))
            return ""

    def get_source(self) -> str:
        content = self.inline or self._fetch_content()
        return f"/*! {self.id} */\n{content}"

    def minify(self) -> str:
        # remove existing sourcemaps, make no sense after re-mini
        content = self.rx_sourceMap.sub("", self.content)
        # comments
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        # space
        content = re.sub(r"\s+", " ", content)
        content = re.sub(r" *([{}]) *", r"\1", content)
        return self.with_header(content)


class PreprocessedCSS(StylesheetAsset):
    rx_import = None

    def get_command(self) -> list[str]:
        raise NotImplementedError

    def compile(self, source: str) -> str:
        command = self.get_command()
        try:
            compiler = Popen(
                command, stdin=PIPE, stdout=PIPE, stderr=PIPE, encoding="utf-8"
            )
        except OSError:
            raise CompileError(f"Could not execute command {command[0]!r}")

        out, err = compiler.communicate(input=source)
        if compiler.returncode:
            cmd_output = out + err
            if not cmd_output:
                cmd_output = f"Process exited with return code {compiler.returncode}\n"
            raise CompileError(cmd_output)
        return out


class ScssStylesheetAsset(PreprocessedCSS):
    """Compile SCSS (.scss) using Dart Sass (embedded protocol or CLI)."""

    @property
    def bootstrap_path(self) -> str:
        return file_path("web/static/lib/bootstrap/scss")

    @property
    def output_style(self) -> str:
        """Use compressed output in production for AST-aware minification."""
        return (
            "expanded" if self.bundle and self.bundle.is_debug_assets else "compressed"
        )

    @property
    def _sass_syntax(self) -> str:
        """Sass syntax identifier for this asset type."""
        return "scss"

    def minify(self) -> str:
        """Skip regex minification when Dart Sass already compressed."""
        if self.bundle and self.bundle.is_debug_assets:
            return super().minify()
        return self.with_header()

    def compile(self, source: str) -> str:
        """Compile SCSS: embedded Dart Sass -> Dart Sass CLI."""
        import odoo.addons

        # Try 1: Embedded Sass Protocol (fast, custom importers)
        try:
            from odoo.tools.sass_embedded import (
                OdooSassImporter,
                SassCompileError,
                get_sass_compiler,
            )

            compiler = get_sass_compiler()
            profiler.force_hook()
            return compiler.compile_string(
                source,
                syntax=self._sass_syntax,
                importers=[OdooSassImporter(self.bootstrap_path)],
                load_paths=[self.bootstrap_path, *odoo.addons.__path__],
                style=self.output_style,
                quiet_deps=True,
            )
        except SassCompileError:
            raise
        except Exception:
            _logger.debug(
                "Dart Sass embedded unavailable, trying CLI",
                exc_info=True,
            )
            # Close the singleton to reap any zombie process.
            from odoo.tools.sass_embedded import close_sass_compiler

            close_sass_compiler()

        # Try 2: Dart Sass CLI (no custom importers, uses --load-path)
        return super().compile(source)

    def get_command(self) -> list[str]:
        """Build the Dart Sass CLI command."""
        import odoo.addons

        try:
            sass = misc.find_in_path("sass")
        except OSError:
            sass = "sass"
        load_paths = [self.bootstrap_path, *odoo.addons.__path__]
        cmd = [
            sass,
            "--stdin",
            "--no-source-map",
            "--style",
            self.output_style,
            "--quiet-deps",
            "--silence-deprecation=import",
            "--silence-deprecation=global-builtin",
            "--silence-deprecation=if-function",
            "--silence-deprecation=duplicate-var-flags",
            "--silence-deprecation=color-functions",
        ]
        for path in load_paths:
            cmd.extend(["--load-path", path])
        return cmd


class LessStylesheetAsset(PreprocessedCSS):
    def get_command(self) -> list[str]:
        try:
            if os.name == "nt":
                lessc = misc.find_in_path("lessc.cmd")
            else:
                lessc = misc.find_in_path("lessc")
        except OSError:
            lessc = "lessc"
        return [lessc, "-", "--no-js", "--no-color"]
