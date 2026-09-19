import json
import logging
import re

from lxml import etree, html
from markupsafe import escape

from odoo import api, models, release
from odoo.exceptions import AccessError, MissingError
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.modules.module import get_manifest
from odoo.tools.translate import _

from odoo.addons.iap.tools import iap_tools

logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

DEFAULT_WEBSITE_ENDPOINT = "https://website.api.odoo.com"
DEFAULT_OLG_ENDPOINT = "https://olg.api.odoo.com"
CONFIGURATOR_IMAGE_MAX_BYTES = 10 * 1024 * 1024


FALLBACK_INDUSTRY_IMAGES = [
    ("s_intro_pill_default_image", "library_image_10"),
    ("s_intro_pill_default_image_2", "library_image_14"),
    ("s_banner_default_image_2", "s_image_text_default_image"),
    ("s_banner_default_image_3", "s_product_list_default_image_1"),
    ("s_striped_top_default_image", "s_picture_default_image"),
    ("s_text_cover_default_image", "s_cover_default_image"),
    ("s_showcase_default_image", "s_image_text_default_image"),
    ("s_image_hexagonal_default_image", "s_cover_default_image"),
    ("s_image_hexagonal_default_image_1", "s_company_team_image_1"),
    ("s_accordion_image_default_image", "s_image_text_default_image"),
    ("s_pricelist_boxed_default_background", "s_product_catalog_default_image"),
    ("s_image_title_default_image", "s_cover_default_image"),
    ("s_key_images_default_image_1", "s_media_list_default_image_1"),
    ("s_key_images_default_image_2", "s_image_text_default_image"),
    ("s_key_images_default_image_3", "s_media_list_default_image_2"),
    ("s_key_images_default_image_4", "s_text_image_default_image"),
    ("s_kickoff_default_image", "s_cover_default_image"),
    ("s_quadrant_default_image_1", "library_image_03"),
    ("s_quadrant_default_image_2", "library_image_10"),
    ("s_quadrant_default_image_3", "library_image_13"),
    ("s_quadrant_default_image_4", "library_image_05"),
    ("s_sidegrid_default_image_1", "library_image_03"),
    ("s_sidegrid_default_image_2", "library_image_10"),
    ("s_sidegrid_default_image_3", "library_image_13"),
    ("s_sidegrid_default_image_4", "library_image_05"),
    ("s_cta_box_default_image", "library_image_02"),
    ("s_image_punchy_default_image", "s_cover_default_image"),
    ("s_image_frame_default_image", "s_carousel_default_image_2"),
    ("s_carousel_intro_default_image_1", "s_cover_default_image"),
    ("s_carousel_intro_default_image_2", "s_image_text_default_image"),
    ("s_carousel_intro_default_image_3", "s_text_image_default_image"),
    ("s_website_form_overlay_default_image", "s_cover_default_image"),
    ("s_website_form_cover_default_image", "s_cover_default_image"),
    ("s_split_intro_default_image", "s_cover_default_image"),
    ("s_framed_intro_default_image", "s_cover_default_image"),
    ("s_wavy_grid_default_image_1", "s_cover_default_image"),
    ("s_wavy_grid_default_image_2", "s_image_text_default_image"),
    ("s_wavy_grid_default_image_3", "s_text_image_default_image"),
    ("s_wavy_grid_default_image_4", "s_carousel_default_image_1"),
    ("s_timeline_images_default_image_1", "s_media_list_default_image_1"),
    ("s_timeline_images_default_image_2", "s_media_list_default_image_2"),
    ("s_carousel_cards_default_image_1", "s_carousel_default_image_1"),
    ("s_carousel_cards_default_image_2", "s_carousel_default_image_2"),
    ("s_carousel_cards_default_image_3", "s_carousel_default_image_3"),
    ("s_banner_connected_default_image", "s_cover_default_image"),
]


class Website(models.Model):
    _inherit = "website"

    def create_and_redirect_configurator(self):
        self._force()
        configurator_action_todo = self.env.ref("website.website_configurator_todo")
        return configurator_action_todo.action_launch()

    def _api_rpc(self, route, params, endpoint_param_name, default_endpoint, **kwargs):
        params["version"] = release.version
        IrConfigParameter = self.env["ir.config_parameter"].sudo()
        api_endpoint = IrConfigParameter.get_param(
            endpoint_param_name, default_endpoint
        )
        with _debug.perf("configurator_api_rpc", route=route, endpoint=api_endpoint):
            return iap_tools.iap_jsonrpc(
                api_endpoint + route, params=params, **kwargs, env=self.env
            )

    def _website_api_rpc(self, route, params):
        return self._api_rpc(
            route, params, "website.website_api_endpoint", DEFAULT_WEBSITE_ENDPOINT
        )

    def _OLG_api_rpc(self, route, params):
        return self._api_rpc(
            route, params, "website.olg_api_endpoint", DEFAULT_OLG_ENDPOINT, timeout=45
        )

    def prepare_configurator_cta_data(self, website_purpose, website_type):
        return {"cta_btn_text": False, "cta_btn_href": "/contactus"}

    def _get_snippet_defaults(self, snippet):
        return {}

    def _get_snippet_view_key(self, snippet, page_code):
        if "." not in snippet:
            snippet = "website." + snippet
        module, snippet = snippet.split(".")
        return f"{module}.configurator_{page_code}_{snippet}"

    def _preconfigure_snippet(self, snippet, el, customizations):
        def modify_class(target_classes, class_name, operation):
            if operation == "remove" and class_name in target_classes:
                target_classes.remove(class_name)
            elif operation == "add" and class_name not in target_classes:
                target_classes.append(class_name)

        default_settings = self._get_snippet_defaults(snippet)
        if not (customizations or default_settings):
            return

        snippet_classes = el.get("class", "").split()

        filter_name = customizations.get("filter_xmlid") or default_settings.get(
            "filter_xmlid"
        )
        if filter_name:
            selected_filter = self.env.ref(filter_name)
            el.set("data-filter-id", str(selected_filter.id))
            el.set("data-number-of-records", str(selected_filter.limit))

        selected_template_key = customizations.get(
            "template_key"
        ) or default_settings.get("template_key")
        if selected_template_key:
            el.set("data-template-key", selected_template_key)
            template_class = re.sub(
                r".*\.dynamic_filter_template_", "s_", selected_template_key
            )
            if template_class not in snippet_classes:
                snippet_classes.append(template_class)

        snippet_classes.append("o_colored_level")

        class_modifications = [
            (
                "remove",
                customizations.get("remove_classes", [])
                or default_settings.get("remove_classes", []),
            ),
            (
                "add",
                customizations.get("add_classes", [])
                or default_settings.get("add_classes", []),
            ),
        ]

        for operation, items in class_modifications:
            for item in items:
                if isinstance(item, dict):
                    for selector, classes in item.items():
                        child_el = el.xpath(f"//*[hasclass('{selector}')]")
                        if child_el:
                            node = child_el[0]
                            child_classes = node.get("class", "").split()
                            modify_class(child_classes, classes, operation)
                            node.set("class", " ".join(child_classes))
                else:
                    modify_class(snippet_classes, item, operation)

        data_attributes = {
            **default_settings.get("data_attributes", {}),
            **customizations.get("data_attributes", {}),
        }
        for key, value in data_attributes.items():
            el.set(f"data-{key}", value)

        el.set("class", " ".join(snippet_classes))

        style = customizations.get("style", {}) or default_settings.get("style", {})
        if style:
            style_attr = " ".join(f"{attr}: {value};" for attr, value in style.items())
            el.set("style", style_attr)

        if "background" in customizations:
            self._update_background_options(el, customizations["background"])

        return

    def _update_background_options(self, el, background_options):
        snippet_classes = el.get("class").split()
        snippet_style = (el.get("style") or "").split()

        if "color" in background_options:
            snippet_classes = [c for c in snippet_classes if not c.startswith("o_cc")]
            snippet_classes.append("o_cc " + background_options["color"])
        if "image" in background_options:
            snippet_classes.append("oe_img_bg o_bg_img_center")
            snippet_style.append(background_options["image"])
        if "shape" in background_options:
            el.set(
                "data-oe-shape-data", background_options["shape"]["data-oe-shape-data"]
            )
            shape_el = html.fromstring(background_options["shape"]["element"])
            el.insert(0, shape_el)

        el.set("class", " ".join(snippet_classes))
        el.set("style", " ".join(snippet_style))

    @api.model
    def get_theme_configurator_snippets(self, theme_name):
        configurator_snippets = {
            **get_manifest("website")["configurator_snippets"],
            **get_manifest(theme_name).get("configurator_snippets", {}),
        }
        configurator_snippets_addons = {
            **get_manifest(theme_name).get("configurator_snippets_addons", {}),
        }

        if not configurator_snippets_addons:
            return configurator_snippets

        installed_modules = self.env["ir.module.module"]._get_installed_module_ids()

        for module_name, module_addon in configurator_snippets_addons.items():
            if module_name not in installed_modules:
                continue
            for page, snippets_to_insert in module_addon.items():
                snippet_list = configurator_snippets.setdefault(page, [])
                for snippet_name, position, target in snippets_to_insert:
                    if snippet_name in snippet_list:
                        continue
                    try:
                        snippet_idx = snippet_list.index(target) + (position == "after")
                        snippet_list.insert(snippet_idx, snippet_name)
                    except ValueError:
                        logger.error(
                            "Skipping snippet '%s' because the target snippet is misconfigured.",
                            snippet_name,
                        )
                        _debug.logic(
                            "configurator_snippet_skipped",
                            reason="unknown_target",
                            snippet=snippet_name,
                            target=target,
                        )

        return configurator_snippets

    def configurator_set_menu_links(self, menu_company, module_data):
        menus = self.env["website.menu"].search(
            [("url", "in", list(module_data.keys())), ("website_id", "=", self.id)]
        )
        _debug.lifecycle(
            "configurator_menu_links",
            website=self.id,
            menus=len(menus),
            urls=len(module_data),
        )
        for m in menus:
            m.sequence = module_data[m.url]["sequence"]

    def configurator_get_footer_links(self):
        return [
            {"text": _("Privacy Policy"), "href": "/privacy"},
        ]

    @api.model
    def configurator_init(self):
        r = {}
        current_website = self.get_current_website()
        company = current_website.company_id
        configurator_features = self.env["website.configurator.feature"].search([])
        r["features"] = [
            {
                "id": feature.id,
                "name": feature.name,
                "description": feature.description,
                "type": "page" if feature.page_view_id else "app",
                "icon": feature.icon,
                "website_config_preselection": feature.website_config_preselection,
                "module_state": feature.module_id.state,
            }
            for feature in configurator_features
        ]
        r["logo"] = False
        if not company.uses_default_logo:
            r["logo"] = company.image_1920.decode("utf-8")
        r["configurator_done"] = current_website.configurator_done
        try:
            result = self._website_api_rpc(
                "/api/website/1/configurator/industries",
                {"lang": self.env.context.get("lang")},
            )
            r["industries"] = result["industries"]
        except AccessError as e:
            logger.warning(e.args[0])
            _debug.logic("configurator_industries_unavailable")
            r["industries"] = []
        _debug.pipeline(
            "configurator_init",
            website=current_website.id,
            features=len(configurator_features),
            industries=len(r["industries"]),
            done=r["configurator_done"],
        )
        return r

    @api.model
    def configurator_recommended_themes(self, industry_id, palette, result_nbr_max=3):
        Module = request.env["ir.module.module"]
        domain = Module.get_domain_themes()
        domain = Domain.AND([[("name", "!=", "theme_default")], domain])
        client_themes = Module.search(domain).mapped("name")
        client_themes_img = {
            t: get_manifest(t).get("images_preview_theme", {})
            for t in client_themes
            if get_manifest(t)
        }
        themes_suggested = self._website_api_rpc(
            "/api/website/2/configurator/recommended_themes/%s"
            % (industry_id if industry_id > 0 else ""),
            {
                "client_themes": client_themes_img,
                "result_nbr_max": result_nbr_max,
            },
        )
        process_svg = self.env["website.configurator.feature"]._process_svg
        for theme in themes_suggested:
            theme["svg"] = process_svg(theme["name"], palette, theme.pop("image_urls"))
        _debug.pipeline(
            "configurator_recommended_themes",
            industry=industry_id,
            client_themes=len(client_themes),
            suggested=len(themes_suggested),
        )
        return themes_suggested

    @api.model
    def configurator_skip(self):
        website = self.get_current_website()
        theme = self.env["ir.module.module"].search([("name", "=", "theme_default")])
        _debug.lifecycle("configurator_skipped", website=website.id)
        website.configurator_done = True
        return theme.button_choose_theme()

    @api.model
    def configurator_missing_industry(self, unknown_industry):
        self._website_api_rpc(
            "/api/website/unknown_industry",
            {
                "unknown_industry": unknown_industry,
                "lang": self.env.context.get("lang"),
            },
        )

    def _configurator_write_footer_links(self, website):
        footer_links = website.configurator_get_footer_links()
        footer_ids = [
            "website.template_footer_contact",
            "website.footer_custom",
            "website.template_footer_links",
            "website.template_footer_minimalist",
            "website.template_footer_mega",
            "website.template_footer_mega_columns",
            "website.template_footer_mega_links",
        ]
        for footer_id in footer_ids:
            view_id = self.env["website"].viewref(footer_id)
            if view_id:
                try:
                    arch_string = etree.fromstring(view_id.arch_db)
                except etree.XMLSyntaxError as e:
                    logger.warning(
                        "Failed to update footer links in view %s: %s", footer_id, e
                    )
                    _debug.logic(
                        "footer_links_skipped",
                        reason="unparseable_arch",
                        view=footer_id,
                    )
                else:
                    el = arch_string.xpath("//t[@t-set='configurator_footer_links']")
                    if not el:
                        logger.warning(
                            "No 'configurator_footer_links' found in view %s", footer_id
                        )
                        _debug.logic(
                            "footer_links_skipped",
                            reason="no_anchor",
                            view=footer_id,
                        )
                        continue
                    el[0].attrib["t-value"] = json.dumps(footer_links)
                    _debug.lifecycle(
                        "footer_links_written",
                        view=footer_id,
                        website=website.id,
                        links=len(footer_links),
                    )
                    view_id.with_context(website_id=website.id).write(
                        {"arch_db": etree.tostring(arch_string)}
                    )

    def _configurator_stored_image_names(self, website):
        return (
            self.env["ir.model.data"]
            .search(
                [
                    ("name", "=ilike", f"configurator\\_{website.id}\\_%"),
                    ("module", "=", "website"),
                    ("model", "=", "ir.attachment"),
                ]
            )
            .mapped("name")
        )

    def _configurator_download_images(self, website, images, names):
        stored = 0
        for name, image_src in images.items():
            extn_identifier = "configurator_%s_%s" % (website.id, name.split(".")[1])
            if extn_identifier in names:
                continue
            try:
                with _debug.perf("configurator_image_requested", name=name) as span:
                    response = self.env["ir.egress"].request(
                        "GET",
                        image_src,
                        purpose="website_configurator",
                        timeout=3,
                        max_bytes=CONFIGURATOR_IMAGE_MAX_BYTES,
                    )
                    span.set(status=getattr(response, "status_code", None))
                response.raise_for_status()
            except Exception as e:
                logger.warning("Failed to download image: %s.\n%s", image_src, e)
                _debug.logic("configurator_image_failed", name=name, src=image_src)
            else:
                attachment = self.env["ir.attachment"].create(
                    {
                        "name": name,
                        "website_id": website.id,
                        "key": name,
                        "type": "binary",
                        "raw": response.content,
                        "public": True,
                    }
                )
                self.env["ir.model.data"].create(
                    {
                        "name": extn_identifier,
                        "module": "website",
                        "model": "ir.attachment",
                        "res_id": attachment.id,
                        "noupdate": True,
                    }
                )
                stored += 1
        _debug.pipeline(
            "configurator_images",
            website=website.id,
            offered=len(images),
            stored=stored,
        )

    def _configurator_write_cta(self, website, cta_data):
        parent_view = (
            self.env["website"]
            .with_context(website_id=website.id)
            .viewref("website.snippets")
        )
        _debug.lifecycle(
            "configurator_cta", website=website.id, href=cta_data["cta_btn_href"]
        )
        self.env["ir.ui.view"].create(
            {
                "name": parent_view.key + " CTA",
                "key": parent_view.key + "_cta",
                "inherit_id": parent_view.id,
                "website_id": website.id,
                "type": "qweb",
                "priority": 32,
                "arch_db": """
                <data>
                    <xpath expr="//t[@t-set='cta_btn_href']" position="replace">
                        <t t-set="cta_btn_href">%s</t>
                    </xpath>
                    <xpath expr="//t[@t-set='cta_btn_text']" position="replace">
                        <t t-set="cta_btn_text">%s</t>
                    </xpath>
                </data>
            """
                % (
                    escape(cta_data["cta_btn_href"]),
                    escape(cta_data["cta_btn_text"]),
                ),
            }
        )
        try:
            view_id = self.env["website"].viewref("website.header_call_to_action")
            el = etree.fromstring(view_id.arch_db)
        except (MissingError, etree.XMLSyntaxError) as e:
            logger.warning("Could not update the header call to action: %s", e)
            _debug.logic("configurator_cta_header_skipped", website=website.id)
        else:
            btn_cta_el = el.xpath("//a[hasclass('btn_cta')]")
            if btn_cta_el:
                btn_cta_el[0].attrib["href"] = cta_data["cta_btn_href"]
                btn_cta_el[0].text = cta_data["cta_btn_text"]
            view_id.with_context(website_id=website.id).write(
                {"arch_db": etree.tostring(el)}
            )

    def _configurator_write_palette(self, selected_palette):
        if not selected_palette:
            return
        Assets = self.env["website.assets"]
        selected_palette_name = (
            selected_palette if isinstance(selected_palette, str) else "base-1"
        )
        Assets.update_scss_customization(
            "/website/static/src/scss/options/user_values.scss",
            {"color-palettes-name": "'%s'" % selected_palette_name},
        )
        if isinstance(selected_palette, list):
            Assets.update_scss_customization(
                "/website/static/src/scss/options/colors/user_color_palette.scss",
                {f"o-color-{i}": color for i, color in enumerate(selected_palette, 1)},
            )

    def _configurator_write_logo(self, website, logo_attachment_id):
        company = website.company_id
        if logo_attachment_id:
            attachment = self.env["ir.attachment"].browse(logo_attachment_id)
            attachment.write(
                {
                    "res_model": "website",
                    "res_field": "logo",
                    "res_id": website.id,
                }
            )
        elif not company.uses_default_logo:
            website.logo = company.image_1920.decode("utf-8")
        _debug.lifecycle(
            "configurator_logo",
            website=website.id,
            by="upload"
            if logo_attachment_id
            else ("company" if not company.uses_default_logo else "default"),
        )

    def _configurator_apply_features(self, website, features, menu_company):
        pages_views = {}
        modules = self.env["ir.module.module"]
        module_data = {}
        for feature in features:
            add_menu = bool(feature.menu_sequence)
            if feature.module_id:
                if feature.module_id.state != "installed":
                    modules += feature.module_id
                if add_menu:
                    if feature.module_id.name != "website_blog":
                        module_data[feature.feature_url] = {
                            "sequence": feature.menu_sequence
                        }
                    else:
                        blogs = module_data.setdefault("#blog", [])
                        blogs.append(
                            {"name": feature.name, "sequence": feature.menu_sequence}
                        )
            elif feature.page_view_id:
                result = self.env["website"].new_page(
                    name=feature.name,
                    add_menu=add_menu,
                    page_values={"url": feature.feature_url, "is_published": True},
                    menu_values=add_menu
                    and {
                        "url": feature.feature_url,
                        "sequence": feature.menu_sequence,
                        "parent_id": (feature.menu_company and menu_company.id)
                        or website.menu_id.id,
                    },
                    template=feature.page_view_id.key,
                )
                pages_views[feature.iap_page_code] = result["view_id"]
        _debug.pipeline(
            "configurator_features",
            website=website.id,
            features=features,
            to_install=modules,
            pages=len(pages_views),
        )
        return pages_views, modules, module_data

    @api.model
    @_debug.perf.timed
    def configurator_apply(self, **kwargs):
        website = self.get_current_website()
        theme_name = kwargs["theme_name"]
        theme = self.env["ir.module.module"].search([("name", "=", theme_name)])
        _debug.pipeline(
            "configurator_apply",
            website=website.id,
            theme=theme_name,
            industry=kwargs.get("industry_name"),
            features=len(kwargs.get("selected_features") or ()),
        )
        redirect_url = theme.button_choose_theme()

        website.configurator_done = True

        tour_asset_id = self.env.ref("website.configurator_tour")
        tour_asset_id.copy(
            {"key": tour_asset_id.key, "website_id": website.id, "active": True}
        )

        self._configurator_write_logo(website, kwargs.get("logo_attachment_id"))

        self._configurator_write_palette(kwargs.get("selected_palette"))

        cta_data = website.prepare_configurator_cta_data(
            kwargs.get("website_purpose"), kwargs.get("website_type")
        )
        if cta_data["cta_btn_text"]:
            self._configurator_write_cta(website, cta_data)

        features = self.env["website.configurator.feature"].browse(
            kwargs.get("selected_features")
        )

        menu_company = self.env["website.menu"]
        if (
            len(features.filtered("menu_sequence")) > 5
            and len(features.filtered("menu_company")) > 1
        ):
            _debug.logic(
                "configurator_company_menu",
                website=website.id,
                features=len(features),
            )
            menu_company = self.env["website.menu"].create(
                {
                    "name": _("Company"),
                    "parent_id": website.menu_id.id,
                    "website_id": website.id,
                    "sequence": 40,
                }
            )

        pages_views, modules, module_data = self._configurator_apply_features(
            website, features, menu_company
        )

        if modules:
            with _debug.perf("modules_install", cr=self.env.cr, modules=modules):
                modules.button_immediate_install()

        self.env["website"].browse(website.id).configurator_set_menu_links(
            menu_company, module_data
        )

        self.env["website"].configurator_addons_apply(**kwargs)

        website = self.env["website"].browse(website.id)

        self._configurator_write_footer_links(website)

        industry_id = kwargs["industry_id"]
        custom_resources = self._website_api_rpc(
            "/api/website/2/configurator/custom_resources/%s"
            % (industry_id if industry_id > 0 else ""),
            {"theme": theme_name},
        )

        requested_pages = set(pages_views.keys()).union({"homepage"})
        configurator_snippets = website.get_theme_configurator_snippets(theme_name)
        industry = kwargs["industry_name"]

        IrQweb = self.env["ir.qweb"].with_context(
            website_id=website.id, lang=website.default_lang_id.code
        )
        text_generation_target_lang = self.get_current_website().default_lang_id.code
        text_must_be_translated_for_openai = not text_generation_target_lang.startswith(
            "en_"
        )

        html_text_processor = self.env[
            "website.html.text.processor"
        ]._with_processing_context(
            IrQweb=IrQweb,
            cta_data=cta_data,
            text_generation_target_lang=text_generation_target_lang,
            text_must_be_translated_for_openai=text_must_be_translated_for_openai,
        )
        generated_content = {}
        translated_content = {}
        for page_code in requested_pages - {"privacy_policy"}:
            snippet_list = configurator_snippets.get(page_code, [])
            for snippet in snippet_list:
                snippet_key = website._get_snippet_view_key(snippet, page_code)
                (
                    html_text_processor,
                    snippet_generated_content,
                    snippet_translated_content,
                ) = html_text_processor._get_snippet_content(snippet_key)
                generated_content.update(snippet_generated_content)
                translated_content.update(snippet_translated_content)

        translated_ratio = html_text_processor._get_translation_ratio(
            generated_content, translated_content
        )
        _debug.pipeline(
            "configurator_content_collected",
            pages=len(requested_pages),
            placeholders=len(generated_content),
            translated=len(translated_content),
            ratio=translated_ratio,
        )
        if translated_ratio > 0.8:
            try:
                database_id = (
                    self.env["ir.config_parameter"].sudo().get_param("database.uuid")
                )
                with _debug.perf(
                    "configurator_ai_text",
                    placeholders=len(generated_content),
                    industry=industry,
                ):
                    response = self._OLG_api_rpc(
                        "/api/olg/1/generate_placeholder",
                        {
                            "placeholders": list(generated_content.keys()),
                            "lang": website.default_lang_id.name,
                            "industry": industry,
                            "database_id": database_id,
                        },
                    )
                name_replace_parser = re.compile(r"XXXX", re.MULTILINE)
                for key in generated_content:
                    if response.get(key):
                        generated_content[key] = name_replace_parser.sub(
                            lambda _m: website.name, response[key]
                        )
            except AccessError:
                pass
        else:
            logger.info(
                "Skip AI text generation because translation coverage is too low (%s%%)",
                translated_ratio * 100,
            )
            _debug.logic(
                "configurator_ai_text_skipped",
                reason="low_translation_coverage",
                ratio=translated_ratio,
            )

        for index, page_code in enumerate(sorted(requested_pages)):
            snippet_list = configurator_snippets.get(page_code, [])
            if page_code == "homepage":
                page_view_id = self.with_context(website_id=website.id).viewref(
                    "website.homepage"
                )
            else:
                page_view_id = self.env["ir.ui.view"].browse(pages_views[page_code])
            rendered_snippets = []
            nb_snippets = len(snippet_list)
            theme_customizations = get_manifest(theme_name).get(
                "theme_customizations", {}
            )
            for i, snippet in enumerate(snippet_list, start=1):
                try:
                    snippet_key = website._get_snippet_view_key(snippet, page_code)
                    el = html_text_processor._update_snippet_content(
                        generated_content, snippet_key
                    )

                    el.attrib["data-snippet"] = snippet

                    customizations = theme_customizations.get(snippet, {})

                    website._preconfigure_snippet(snippet, el, customizations)

                    dialog_preview_els = el.find_class("s_dialog_preview")
                    for preview_el in dialog_preview_els:
                        preview_el.getparent().remove(preview_el)

                    if i == 1:
                        shape_el = el.xpath("//*[hasclass('o_we_shape')]")
                        if shape_el:
                            shape_el[0].attrib["class"] += (
                                " o_header_extra_shape_mapping"
                            )

                    if i == nb_snippets:
                        shape_el = el.xpath("//*[hasclass('o_we_shape')]")
                        if shape_el:
                            shape_el[0].attrib["class"] += (
                                " o_footer_extra_shape_mapping"
                            )
                    rendered_snippet = etree.tostring(el, encoding="unicode")
                    rendered_snippets.append(rendered_snippet)
                except ValueError as e:
                    logger.warning(e)
                    _debug.logic(
                        "configurator_snippet_render_failed",
                        page=page_code,
                        snippet=snippet,
                    )
            _debug.lifecycle(
                "configurator_page_built",
                page=page_code,
                view=page_view_id.id,
                snippets=len(rendered_snippets),
                wanted=nb_snippets,
            )
            page_view_id.save(
                value=f'<div class="oe_structure">{"".join(rendered_snippets)}</div>',
                xpath="(//div[hasclass('oe_structure')])[last()]",
            )
            page_view_id.copy(
                {
                    "key": f"{index}_{page_view_id.key}_configurator_pages_landing",
                    "website_id": website.id,
                }
            )

        images = custom_resources.get("images", {})
        names = self._configurator_stored_image_names(website)
        self._configurator_download_images(website, images, names)

        def fallback_create_missing_industry_image(image_name, fallback_img_name):
            image_name = f"website.{image_name}"
            if image_name not in images and f"website.{fallback_img_name}" in images:
                extn_identifier = "configurator_%s_%s" % (
                    website.id,
                    image_name.split(".")[1],
                )
                if extn_identifier not in names:
                    attachment = self.env["ir.attachment"].create(
                        {
                            "name": image_name,
                            "website_id": website.id,
                            "key": image_name,
                            "type": "binary",
                            "raw": self.env.ref(
                                f"website.configurator_{website.id}_{fallback_img_name}"
                            ).raw,
                            "public": True,
                        }
                    )
                    self.env["ir.model.data"].create(
                        {
                            "name": extn_identifier,
                            "module": "website",
                            "model": "ir.attachment",
                            "res_id": attachment.id,
                            "noupdate": True,
                        }
                    )

        for image_name, fallback_img_name in FALLBACK_INDUSTRY_IMAGES:
            try:
                fallback_create_missing_industry_image(image_name, fallback_img_name)
            except Exception:
                logger.debug(
                    "Configurator fallback image %s could not be created",
                    image_name,
                    exc_info=True,
                )
                _debug.logic("configurator_fallback_image_failed", name=image_name)

        _debug.lifecycle(
            "configurator_applied",
            website=website.id,
            theme=theme_name,
            url=redirect_url,
        )
        return {"url": redirect_url, "website_id": website.id}

    def configurator_addons_apply(self, industry_name=None, **kwargs):
        pass
