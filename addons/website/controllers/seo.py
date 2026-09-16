"""SEO metadata, alt text, broken links and field translations.

Mixed into `Website` in `main.py` rather than registered as a controller of its
own: every method stays on that class, so an addon overriding one -- and
`website_sale`, `website_appointment` and `website_helpdesk` each override one --
keeps working unchanged, and so does every `self.` call between them.
"""

import logging
import re
from hashlib import sha256

import werkzeug.exceptions
from defusedxml.ElementTree import fromstring as defused_fromstring
from lxml import html

from odoo import _, http
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.tools.json import scriptsafe as json

logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class WebsiteSeoRoutes:
    @http.route(
        ["/website/seo_suggest"],
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def seo_suggest(self, keywords=None, lang=None):
        pattern = r"^([a-zA-Z]+)(?:_(\w+))?(?:@(\w+))?$"
        match = re.match(pattern, lang or "")
        language = [match.group(1), match.group(2) or ""] if match else ["en", "US"]
        url = "https://www.google.com/complete/search"
        try:
            with _debug.perf("seo_suggest_requested", lang=language[0]) as span:
                req = request.env["ir.egress"].request(
                    "GET",
                    url,
                    purpose="seo_suggest",
                    params={
                        "ie": "utf8",
                        "oe": "utf8",
                        "output": "toolbar",
                        "q": keywords,
                        "hl": language[0],
                        "gl": language[1],
                    },
                    timeout=5,
                )
                span.set(status=getattr(req, "status_code", None))
            req.raise_for_status()
            response = req.content
        except OSError:
            _debug.logic("seo_suggest_failed", reason="unreachable")
            return json.dumps([])
        xmlroot = defused_fromstring(response)
        return json.dumps(
            [
                sugg[0].attrib["data"]
                for sugg in xmlroot
                if len(sugg) and sugg[0].attrib["data"]
            ]
        )

    @http.route(["/website/get_alt_images"], type="jsonrpc", auth="user", website=True)
    def get_alt_images(self, models):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            _debug.logic("alt_images_refused", reason="not_restricted_editor")
            raise werkzeug.exceptions.Forbidden
        result = []
        for model in models:
            record = self._get_html_record(model["model"], model["id"])
            if not record.has_access("read"):
                _debug.logic(
                    "alt_images_record_skipped",
                    reason="no_read_access",
                    model=model["model"],
                    record=model["id"],
                )
                continue
            field_name = "arch_db" if model["field"] == "arch" else model["field"]
            tree = self._get_html_tree(record, field_name)
            if tree is None:
                continue
            for index, el in enumerate(tree.xpath("//img[@src]")):
                role = el.get("role")
                decorative = role == "presentation"
                alt = el.get("alt")
                if not decorative or alt is None:
                    result.append(
                        {
                            "src": el.get("src"),
                            "alt": alt or "",
                            "decorative": False,
                            "updated": False,
                            "res_model": model["model"],
                            "res_id": model["id"],
                            "id": f"{model['model']}-{model['id']}-{index}",
                            "field": field_name,
                        }
                    )
        _debug.pipeline("alt_images", records=len(models), images=len(result))
        return json.dumps(result)

    @http.route(
        ["/website/update_alt_images"], type="jsonrpc", auth="user", website=True
    )
    def update_alt_images(self, imgs):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            _debug.logic("update_alt_images_refused", reason="not_restricted_editor")
            raise werkzeug.exceptions.Forbidden
        _debug.lifecycle("update_alt_images", images=len(imgs))
        self._update_html_fields(imgs, self._update_image_attributes)

    def _update_image_attributes(self, tree, imgs):
        images_by_id = {img["id"]: img for img in imgs}
        prefix = f"{imgs[0]['res_model']}-{imgs[0]['res_id']}-"
        modified = False
        elements = tree.xpath("//img[@src]") if tree is not None else ()
        for index, element in enumerate(elements):
            if img := images_by_id.pop(f"{prefix}{index}", None):
                if "src" in img and img["src"] != element.get("src"):
                    logger.debug("Stale website image target id=%s", img["id"])
                    _debug.logic(
                        "image_update_refused", reason="stale_src", img=img["id"]
                    )
                    raise UserError(
                        _(
                            "The page images have changed. Refresh the page before saving image descriptions."
                        )
                    )
                if img["decorative"]:
                    if (
                        element.get("alt") == ""
                        and element.get("role") == "presentation"
                    ):
                        continue
                    element.set("alt", "")
                    element.set("role", "presentation")
                else:
                    if (
                        element.get("alt") == img["alt"]
                        and "role" not in element.attrib
                    ):
                        continue
                    element.set("alt", img["alt"])
                    element.attrib.pop("role", None)
                modified = True
        if any("src" in img for img in images_by_id.values()):
            logger.debug("Missing website image targets count=%d", len(images_by_id))
            _debug.logic(
                "image_update_refused",
                reason="missing_targets",
                missing=len(images_by_id),
            )
            raise UserError(
                _(
                    "The page images have changed. Refresh the page before saving image descriptions."
                )
            )
        return modified

    @http.route(
        ["/website/update_broken_links"], type="jsonrpc", auth="user", website=True
    )
    def update_broken_links(self, links):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            _debug.logic("update_links_refused", reason="not_restricted_editor")
            raise werkzeug.exceptions.Forbidden
        _debug.lifecycle("update_broken_links", links=len(links))
        self._update_html_fields(links, self._update_link_urls)

    def _update_link_urls(self, tree, links):
        if tree is None:
            return False
        modified = False
        for link in links:
            for element in tree.xpath("//a"):
                href = element.get("href")
                if href and (link["oldLink"] == href or link["oldLink"] == href + "/"):
                    if link["remove"]:
                        element.drop_tag()
                    elif href != link["newLink"]:
                        element.set("href", link["newLink"])
                    else:
                        continue
                    modified = True
        return modified

    def _update_html_fields(self, updates, update_tree):
        updates_by_field = {}
        for update in updates:
            field_name = "arch_db" if update["field"] == "arch" else update["field"]
            key = (update["res_model"], update["res_id"], field_name)
            updates_by_field.setdefault(key, []).append(update)
        for (
            model_name,
            record_id,
            field_name,
        ), field_updates in updates_by_field.items():
            record = self._get_html_record(model_name, record_id)
            if not record.has_access("write"):
                _debug.logic(
                    "html_update_skipped",
                    reason="no_write_access",
                    model=model_name,
                    record=record_id,
                )
                continue
            field = record._fields.get(field_name)
            if not field or field.type not in ("html", "text") or not field.store:
                _debug.logic(
                    "html_update_skipped",
                    reason="not_a_stored_html_field",
                    model=model_name,
                    field=field_name,
                )
                continue
            tree = self._get_html_tree(record, field_name)
            modified = update_tree(tree, field_updates)
            logger.debug(
                "Website HTML update model=%s record=%s field=%s updates=%d modified=%s",
                model_name,
                record_id,
                field_name,
                len(field_updates),
                modified,
            )
            if modified:
                new_html_content = html.tostring(
                    tree, encoding="unicode", method="html"
                )
                _debug.lifecycle(
                    "html_field_rewritten",
                    model=model_name,
                    record=record_id,
                    field=field_name,
                    updates=len(field_updates),
                )
                record.write({field_name: new_html_content})

    def _get_html_tree(self, record, field_name):
        content = record[field_name]
        if not content or not str(content).strip():
            logger.debug(
                "Empty website HTML model=%s record=%s field=%s",
                record._name,
                record.id,
                field_name,
            )
            return None
        return html.fromstring(str(content))

    def _resolve_model(self, model_name):
        """A client-supplied model name, refused rather than raised through.

        `request.env[unknown]` is a bare KeyError and therefore a 500; every
        neighbouring route in this file answers with a typed refusal.
        """
        if not isinstance(model_name, str) or model_name not in request.env:
            _debug.logic("unknown_model_refused", model=model_name)
            raise werkzeug.exceptions.NotFound
        return request.env[model_name]

    def _get_html_record(self, model_name, record_id):
        record = self._resolve_model(model_name).browse(record_id)
        website_id = request.env.context.get("website_id")
        if (
            model_name == "ir.ui.view"
            and website_id
            and not request.env.context.get("no_cow")
            and record.has_access("read")
        ):
            if not record.website_id and record.key:
                specific = record.with_context(active_test=False).search(
                    [("key", "=", record.key), ("website_id", "=", website_id)],
                    limit=1,
                )
                if specific:
                    logger.debug(
                        "Website HTML view resolved generic=%s specific=%s website=%s",
                        record.id,
                        specific.id,
                        website_id,
                    )
                    record = specific
        return record

    @http.route(
        ["/website/get_seo_data"],
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def get_seo_data(self, res_id, res_model):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            try:
                record = request.env[res_model].browse(res_id)
                record.check_access("write")
            except AccessError:
                _debug.logic("seo_data_refused", model=res_model, record=res_id)
                raise werkzeug.exceptions.Forbidden from None

        fields = [
            "website_meta_title",
            "website_meta_description",
            "website_meta_keywords",
            "website_meta_og_img",
        ]
        res = {"can_edit_seo": True}
        record = request.env[res_model].browse(res_id)
        if res_model == "website.page":
            fields.extend(["website_indexed", "website_id"])
            res["website_is_published"] = record.website_published

        try:
            request.website._check_access_to_modify(record)
        except AccessError:
            _debug.logic("seo_read_only", model=res_model, record=res_id)
            res["can_edit_seo"] = False
        if request.env.user.has_group("website.group_website_restricted_editor"):
            record = record.sudo()

        res.update(record.read(fields)[0])
        res["has_social_default_image"] = request.website.has_social_default_image

        if res_model not in ("website.page", "ir.ui.view") and "seo_name" in record:
            res["seo_name_default"] = request.env["ir.http"]._slugify(
                record.display_name or ""
            )
            res["seo_name"] = (
                record.seo_name and request.env["ir.http"]._slugify(record.seo_name)
            ) or ""

        return res

    @http.route(
        ["/website/check_can_modify_any"],
        type="jsonrpc",
        auth="user",
        website=True,
        readonly=True,
    )
    def check_can_modify_any(self, records):
        if not request.env.user.has_group("website.group_website_restricted_editor"):
            _debug.logic("check_modify_refused", reason="not_restricted_editor")
            raise werkzeug.exceptions.Forbidden
        first_error = None
        for rec in records:
            try:
                record = request.env[rec["res_model"]].browse(rec["res_id"])
                request.website._check_access_to_modify(record)
                return True
            except AccessError as e:
                if not first_error:
                    first_error = e
                continue
        if first_error:
            _debug.logic(
                "check_modify_refused",
                reason="no_writable_record",
                records=len(records),
            )
            raise first_error
        return True

    @http.route(
        "/website/field/translation/update", type="jsonrpc", auth="user", website=True
    )
    def update_field_translation(self, model, record_id, field_name, translations):
        record = self._resolve_model(model).browse(record_id)
        field = record._fields.get(field_name)
        if field is None:
            _debug.logic("unknown_field_refused", model=model, field=field_name)
            raise werkzeug.exceptions.NotFound
        source_lang = None
        if callable(field.translate):
            for translation in translations.values():
                for key, value in translation.items():
                    translation[key] = field.translate.term_converter(value)
            source_lang = record._get_base_lang()
        _debug.lifecycle(
            "field_translation_updated",
            model=model,
            record=record_id,
            field=field_name,
            langs=sorted(translations or ()),
        )
        return record._update_field_translations(
            field_name,
            translations,
            lambda old_term: sha256(old_term.encode()).hexdigest(),
            source_lang=source_lang,
        )
