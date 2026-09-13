import re
from collections import OrderedDict
from urllib.parse import urlsplit

from odoo import models
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import lazy

from odoo.addons.website.models import ir_http
from odoo.addons.website.tools import add_form_signature

re_background_image = re.compile(
    r"(background-image\s*:\s*url\(\s*['\"]?\s*)([^)'\"]+)"
)


class IrQweb(models.AbstractModel):
    _inherit = "ir.qweb"

    URL_ATTRS = {
        "form": "action",
        "a": "href",
        "link": "href",
        "script": "src",
        "img": "src",
    }

    def _get_template(self, template):
        element, document, ref = super()._get_template(template)
        if self.env.context.get("website_id"):
            add_form_signature(element, self.sudo().env)
        return element, document, ref

    def _get_template_cache_keys(self):
        return super()._get_template_cache_keys() + ["website_id", "cookies_allowed"]

    def _save_esm_attachment_rows(self, vals_list, touch_ids=(), bundle=""):
        # Compiled ESM rows are content-addressed and served without a website
        # filter, so they belong to no website. Left to ir.attachment.create,
        # they would take the request's forced website, which an autonomous
        # save cannot see when that website is still uncommitted.
        vals_list = [dict(vals, website_id=False) for vals in vals_list]
        super()._save_esm_attachment_rows(vals_list, touch_ids, bundle)

    def _prepare_frontend_environment(self, values):
        irQweb = super()._prepare_frontend_environment(values)

        current_website = request.website
        editable = irQweb.env.user.has_group("website.group_website_designer")
        has_group_restricted_editor = irQweb.env.user.has_group(
            "website.group_website_restricted_editor"
        )
        if not editable and has_group_restricted_editor and "main_object" in values:
            try:
                main_object = values["main_object"].with_user(irQweb.env.user.id)
                current_website._check_access_to_modify(main_object)
                editable = True
            except AccessError:
                pass
        translatable = (
            has_group_restricted_editor
            and irQweb.env.context.get("lang")
            != irQweb.env["ir.http"]._get_default_lang().code
        )
        editable = editable and not translatable

        if has_group_restricted_editor and irQweb.env.user.has_group(
            "website.group_multi_website"
        ):
            values["multi_website_websites_current"] = lazy(
                lambda: current_website.name
            )
            values["multi_website_websites"] = lazy(
                lambda: [
                    {
                        "website_id": website.id,
                        "name": website.name,
                        "domain": website.domain,
                    }
                    for website in current_website.search(
                        [("id", "!=", current_website.id)]
                    )
                ]
            )

            cur_company = irQweb.env.company
            values["multi_website_companies_current"] = lazy(
                lambda: {"company_id": cur_company.id, "name": cur_company.name}
            )
            values["multi_website_companies"] = lazy(
                lambda: [
                    {"company_id": comp.id, "name": comp.name}
                    for comp in irQweb.env.user.company_ids
                    if comp != cur_company
                ]
            )

        values.update(
            {
                "website": current_website,
                "is_view_active": lazy(lambda: current_website.is_view_active),
                "res_company": lazy(
                    request.env["res.company"]
                    .browse(current_website._get_cached("company_id"))
                    .sudo
                ),
                "translatable": translatable,
                "editable": editable,
            }
        )

        if editable:
            if "main_object" in values and has_group_restricted_editor:
                func = getattr(values["main_object"], "get_backend_menu_id", False)
                values["backend_menu_id"] = lazy(
                    lambda: (
                        (func and func())
                        or irQweb.env["ir.model.data"]._xmlid_to_res_id(
                            "website.menu_website_configuration"
                        )
                    )
                )

        irQweb = irQweb.with_context(website_id=current_website.id)
        if "inherit_branding" not in irQweb.env.context and not self.env.context.get(
            "rendering_bundle"
        ):
            if editable:
                irQweb = irQweb.with_context(inherit_branding=True)
            elif has_group_restricted_editor:
                irQweb = irQweb.with_context(inherit_branding_auto=True)

        is_allowed_optional_cookies = request.env["ir.http"]._is_allowed_cookie(
            "optional"
        )
        irQweb = irQweb.with_context(cookies_allowed=is_allowed_optional_cookies)

        return irQweb

    def _get_post_processing_att_names(self):
        return None

    def _post_processing_att(self, tagName, atts, *, is_static=False):
        if atts.get("data-no-post-process"):
            return super()._post_processing_att(tagName, atts, is_static=is_static)

        atts = super()._post_processing_att(tagName, atts, is_static=is_static)

        website = ir_http.get_request_website()
        if not website and self.env.context.get("website_id"):
            website = self.env["website"].browse(self.env.context["website_id"])
        if website and tagName == "img" and "loading" not in atts:
            atts["loading"] = "lazy"

        skip_post_processing = (
            self.env.context.get("inherit_branding")
            or self.env.context.get("rendering_bundle")
            or self.env.context.get("edit_translations")
        )
        if not is_static:
            skip_post_processing = (
                skip_post_processing
                or self.env.context.get("debug")
                or (request and request.session.debug)
            )
        if skip_post_processing:
            return atts

        if not website:
            return atts

        if (
            website.cookies_bar
            and website.block_third_party_domains
            and not self.env.context.get("cookies_allowed")
            and not (
                request
                and request.env.user.has_group(
                    "website.group_website_restricted_editor"
                )
            )
        ):
            cookies_watchlist = {
                "domains": website._get_blocked_third_party_domains_list(),
                "classes": website._get_blocked_iframe_containers_classes(),
            }
            remove_src = False
            if tagName in ("iframe", "script"):
                src_host = urlsplit((atts.get("src") or "").lower()).hostname
                if src_host:
                    remove_src = any(
                        src_host == domain.removeprefix("www.")
                        or src_host.endswith("." + domain.removeprefix("www."))
                        for domain in cookies_watchlist["domains"]
                    )
            if remove_src or cookies_watchlist["classes"].intersection(
                (atts.get("class") or "").split(" ")
            ):
                atts["data-need-cookies-approval"] = "true"
                if "src" in atts:
                    atts["data-nocookie-src"] = atts["src"]
                    atts["src"] = "about:blank"

        name = self.URL_ATTRS.get(tagName)
        if request:
            value = atts.get(name) if name else None
            if value not in (None, False, ()):
                atts[name] = self.env["ir.http"]._url_for(str(value))

            atts = self._adapt_style_background_image(
                atts, self.env["ir.http"]._url_for
            )

        if not website.cdn_activated:
            return atts

        data_name = f"data-{name}"
        if name and (name in atts or data_name in atts):
            atts = OrderedDict(atts)
            if name in atts and atts[name] not in (False, None, ()):
                atts[name] = website.get_cdn_url(atts[name])
            if data_name in atts and atts[data_name] not in (False, None, ()):
                atts[data_name] = website.get_cdn_url(atts[data_name])
        return self._adapt_style_background_image(atts, website.get_cdn_url)

    def _adapt_style_background_image(self, atts, url_adapter):
        if isinstance(atts.get("style"), str) and "background-image" in atts["style"]:
            atts["style"] = re_background_image.sub(
                lambda m: "%s%s" % (m[1], url_adapter(m[2])), atts["style"]
            )
        return atts

    def _get_bundles_to_pregenerate(self):
        js_assets, css_assets = super()._get_bundles_to_pregenerate()
        assets = {
            "website.assets_all_wysiwyg",
        }
        return (js_assets | assets, css_assets | assets)
