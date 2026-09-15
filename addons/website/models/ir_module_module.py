import logging
from collections import OrderedDict, defaultdict
from itertools import batched

import werkzeug

from odoo import api, fields, models
from odoo.exceptions import MissingError
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.models import PREFETCH_MAX
from odoo.modules import Manifest
from odoo.tools import SQL

from odoo.addons.base.models.ir_model_common import MODULE_UNINSTALL_FLAG

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrModuleModule(models.Model):
    _name = "ir.module.module"
    _description = "Module"
    _inherit = ["ir.module.module"]

    _theme_model_names = OrderedDict(
        [
            ("ir.ui.view", "theme.ir.ui.view"),
            ("ir.asset", "theme.ir.asset"),
            ("website.page", "theme.website.page"),
            ("website.menu", "theme.website.menu"),
            ("ir.attachment", "theme.ir.attachment"),
        ]
    )
    _theme_translated_fields = {
        "theme.ir.ui.view": [("theme.ir.ui.view,arch", "ir.ui.view,arch_db")],
        "theme.website.menu": [("theme.website.menu,name", "website.menu,name")],
    }

    image_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        string="Screenshots",
        readonly=True,
        domain=[
            ("res_model", "=", "ir.module.module"),
            ("mimetype", "=like", "image/%"),
        ],
    )
    is_installed_on_current_website = fields.Boolean(
        compute="_compute_is_installed_on_current_website"
    )

    def _compute_is_installed_on_current_website(self):
        for module in self:
            module.is_installed_on_current_website = (
                module == self.env["website"].get_current_website().theme_id
            )

    def write(self, vals):
        if (
            request
            and request.db
            and request.env
            and request.env.context.get("apply_new_theme")
        ):
            self = self.with_context(apply_new_theme=True)

        for module in self:
            if module.name.startswith("theme_") and vals.get("state") == "installed":
                _logger.info(
                    "Module %s has been loaded as theme template (%s)",
                    module.name,
                    module.state,
                )

                if module.state in ["to install", "to upgrade"]:
                    websites_to_update = module._theme_get_stream_website_ids()

                    if module.state == "to upgrade" and request:
                        Website = self.env["website"]
                        current_website = Website.get_current_website()
                        websites_to_update = (
                            current_website
                            if current_website in websites_to_update
                            else Website
                        )

                    _debug.pipeline(
                        "theme_stream_load",
                        module=module.name,
                        state=module.state,
                        websites=len(websites_to_update),
                    )
                    for website in websites_to_update:
                        module._theme_load(website)

        return super().write(vals)

    def _get_module_data(self, model_name):
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            _debug.logic(
                "theme_data_refused",
                reason="not_restricted_editor",
                model=model_name,
            )
            raise werkzeug.exceptions.Forbidden

        self_sudo = self.sudo()

        theme_model_name = self_sudo._theme_model_names[model_name]
        IrModelData = self_sudo.env["ir.model.data"]
        records = self_sudo.env[theme_model_name]

        imd_ids = IrModelData.search(
            [
                ("module", "in", self_sudo.mapped("name")),
                ("model", "=", theme_model_name),
            ]
        ).mapped("res_id")
        return records.with_context(active_test=False).browse(imd_ids)

    def _update_records(self, model_name, website):
        self.check_singleton()

        remaining = self._get_module_data(model_name)
        last_len = -1
        while len(remaining) != last_len:
            last_len = len(remaining)
            queued = self.env[remaining._name]
            for rec in remaining:
                rec_data = rec._convert_to_base_model(website)
                if not rec_data:
                    _logger.info("Record queued: %s", rec.display_name)
                    queued |= rec
                    continue

                find = (
                    rec.with_context(active_test=False)
                    .mapped("copy_ids")
                    .filtered(lambda m: m.website_id == website)[:1]
                )

                if not find and model_name == "ir.attachment":
                    find = rec.copy_ids.search(
                        [
                            ("key", "=", rec.key),
                            ("website_id", "=", website.id),
                            ("original_id", "=", False),
                        ],
                        limit=1,
                    )

                if find:
                    imd = self.env["ir.model.data"].search(  # noqa: E8507 - the copy is resolved one record at a time; it may have been created by an earlier pass of this loop
                        [("model", "=", find._name), ("res_id", "=", find.id)]
                    )
                    if imd and imd.noupdate:
                        _logger.info("Noupdate set for %s (%s)", find, imd)
                        _debug.logic(
                            "theme_record_kept",
                            reason="noupdate",
                            model=model_name,
                            record=find.id,
                        )
                    else:
                        if "active" in rec_data:
                            rec_data.pop("active")
                        if model_name == "ir.ui.view" and (
                            find.arch_updated or find.arch == rec_data["arch"]
                        ):
                            rec_data.pop("arch")
                        _debug.lifecycle(
                            "theme_record_updated",
                            model=model_name,
                            template=rec.id,
                            record=find.id,
                            website=website.id,
                        )
                        find.update(rec_data)
                        self._post_copy(rec, find)
                else:
                    new_rec = self.env[model_name].create(rec_data)
                    _debug.lifecycle(
                        "theme_record_created",
                        model=model_name,
                        template=rec.id,
                        record=new_rec.id,
                        website=website.id,
                    )
                    self._post_copy(rec, new_rec)

            remaining = queued

        if len(remaining):
            error = "Error - Remaining: %s" % remaining.mapped("display_name")
            _logger.error(error)
            _debug.logic(
                "theme_records_unresolved",
                model=model_name,
                website=website.id,
                remaining=len(remaining),
            )
            raise MissingError(error)

        self._theme_cleanup(model_name, website)

    def _post_copy(self, old_rec, new_rec):
        self.check_singleton()
        translated_fields = self._theme_translated_fields.get(old_rec._name, [])
        cur_lang = self.env.lang or "en_US"
        valid_langs = {code for code, _ in self.env["res.lang"].get_installed()} | {
            "en_US"
        }
        old_rec.flush_recordset()
        for src_field, dst_field in translated_fields:
            __, src_fname = src_field.split(",")
            dst_mname, dst_fname = dst_field.split(",")
            if dst_mname != new_rec._name:
                continue
            old_field = old_rec._fields[src_fname]
            old_stored_translations = old_field._get_stored_translations(old_rec)
            if not old_stored_translations:
                continue
            if old_field.translate is True:
                if old_rec[src_fname] != new_rec[dst_fname]:
                    continue
                new_rec.update_field_translations(
                    dst_fname,
                    {
                        k: v
                        for k, v in old_stored_translations.items()
                        if k in valid_langs and k != cur_lang
                    },
                )
            else:
                old_translations = {
                    k: old_stored_translations.get(f"_{k}", v)
                    for k, v in old_stored_translations.items()
                    if k in valid_langs
                }
                if cur_lang in old_translations:
                    source_translation = old_translations.pop(cur_lang)
                else:
                    source_translation = old_translations.get("en_US", "")
                translation_dictionary = old_field.get_translation_dictionary(
                    source_translation,
                    old_translations,
                )
                translations = defaultdict(dict)
                for from_lang_term, to_lang_terms in translation_dictionary.items():
                    for lang, to_lang_term in to_lang_terms.items():
                        translations[lang][from_lang_term] = to_lang_term
                new_rec.with_context(
                    install_filename="dummy"
                ).update_field_translations(dst_fname, translations)

    def _theme_load(self, website):
        for module in self:
            _logger.info(
                "Load theme %s for website %s from template.",
                module.mapped("name"),
                website.id,
            )

            for model_name in self._theme_model_names:
                with _debug.perf(
                    "theme_model_loaded",
                    cr=self.env.cr,
                    module=module.name,
                    model=model_name,
                    website=website.id,
                ):
                    module._update_records(model_name, website)

            if self.env.context.get("apply_new_theme"):
                self.env["theme.utils"].with_context(website_id=website.id)._post_copy(
                    module
                )

    def _theme_unload(self, website):
        for module in self:
            _logger.info(
                "Unload theme %s for website %s from template.",
                self.mapped("name"),
                website.id,
            )

            for model_name in module._theme_model_names:
                template = module._get_module_data(model_name)
                models = (
                    template.with_context(
                        **{"active_test": False, MODULE_UNINSTALL_FLAG: True}
                    )
                    .mapped("copy_ids")
                    .filtered(lambda m: m.website_id == website)
                )
                _debug.lifecycle(
                    "theme_model_unloaded",
                    module=module.name,
                    model=model_name,
                    website=website.id,
                    records=len(models),
                )
                models.unlink()
                module._theme_cleanup(model_name, website)

    def _theme_cleanup(self, model_name, website):
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            _debug.logic(
                "theme_cleanup_refused",
                reason="not_restricted_editor",
                model=model_name,
            )
            raise werkzeug.exceptions.Forbidden

        self.check_singleton()
        model_sudo = self.env[model_name].sudo()

        if model_name in ("website.page", "website.menu"):
            return model_sudo
        orphans = model_sudo.with_context(
            **{"active_test": False, MODULE_UNINSTALL_FLAG: True}
        ).search(
            [
                ("key", "=like", self.name + ".%"),
                ("website_id", "=", website.id),
                ("theme_template_id", "=", False),
            ]
        )
        _debug.lifecycle(
            "theme_orphans_removed",
            module=self.name,
            model=model_name,
            website=website.id,
            orphans=len(orphans),
        )
        orphans.unlink()
        return None

    def _theme_get_upstream(self):
        self.check_singleton()
        return self.upstream_dependencies(exclude_states=("",)).filtered(
            lambda x: x.name.startswith("theme_")
        )

    def _theme_get_downstream(self):
        self.check_singleton()
        return self.downstream_dependencies().filtered(
            lambda x: x.name.startswith(self.name)
        )

    def _theme_get_stream_themes(self):
        self.check_singleton()
        all_mods = self + self._theme_get_downstream()
        for down_mod in self._theme_get_downstream() + self:
            for up_mod in down_mod._theme_get_upstream():
                all_mods = up_mod | all_mods
        return all_mods

    def _theme_get_stream_website_ids(self):
        self.check_singleton()
        websites = self.env["website"]
        for website in websites.search([("theme_id", "!=", False)]):
            if self in website.theme_id._theme_get_stream_themes():
                websites |= website
        return websites

    def _theme_upgrade_upstream(self):
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            _debug.logic("theme_upgrade_refused", reason="not_restricted_editor")
            raise werkzeug.exceptions.Forbidden

        themes = self.env["ir.module.module"].search(self.get_domain_themes())
        if self - themes:
            _debug.logic(
                "theme_upgrade_refused", reason="not_a_theme", modules=self - themes
            )
            raise werkzeug.exceptions.Forbidden
        _debug.pipeline("theme_upgrade_upstream", modules=self)

        def install_or_upgrade(theme):
            if theme.state != "installed":
                theme.button_install()
            themes = theme + theme._theme_get_upstream()
            themes.filtered(lambda m: m.state == "installed").button_upgrade()

        self.sudo()._button_immediate_function(install_or_upgrade)

    @api.model
    def _theme_remove(self, website):
        self.env["theme.utils"].with_context(
            website_id=website.id
        )._reset_default_config()

        if not website.theme_id:
            _debug.logic("theme_remove_skipped", reason="no_theme", website=website.id)
            return

        _debug.lifecycle(
            "theme_removed", website=website.id, theme=website.theme_id.name
        )
        for theme in reversed(website.theme_id._theme_get_stream_themes()):
            theme._theme_unload(website)
        website.theme_id = False

    @_debug.perf.timed
    def button_choose_theme(self):
        self.check_singleton()
        website = self.env["website"].get_current_website()

        self._theme_remove(website)

        _debug.lifecycle("theme_chosen", website=website.id, theme=self.name)
        website.theme_id = self

        if request:
            request.update_context(apply_new_theme=True)
        self._theme_upgrade_upstream()

        return website.button_go_website()

    def button_remove_theme(self):
        website = self.env["website"].get_current_website()
        self._theme_remove(website)

    def button_refresh_theme(self):
        website = self.env["website"].get_current_website()
        website.theme_id._theme_upgrade_upstream()

    @api.model
    def update_list(self):
        res = super().update_list()
        self.update_theme_images()
        return res

    @api.model
    def update_theme_images(self):
        IrAttachment = self.env["ir.attachment"]
        existing_urls = IrAttachment.search_read(
            [["res_model", "=", self._name], ["type", "=", "url"]], ["url"]
        )
        existing_urls = {url_wrapped["url"] for url_wrapped in existing_urls}

        themes = (
            self.env["ir.module.module"]
            .with_context(active_test=False)
            .search(
                [
                    (
                        "category_id",
                        "child_of",
                        self.env.ref("base.module_category_theme").id,
                    ),
                ],
                order="name",
            )
        )

        for theme in themes:
            terp = self.get_module_info(theme.name)
            images = terp["images"] if terp else []
            image_paths = ["/%s/%s" % (theme.name, image) for image in images]
            if all(image_path in existing_urls for image_path in image_paths):
                continue
            _debug.lifecycle(
                "theme_images_registered", theme=theme.name, images=len(image_paths)
            )
            for image_path in image_paths:
                image_name = image_path.split("/")[-1]
                IrAttachment.create(
                    {
                        "type": "url",
                        "name": image_name,
                        "url": image_path,
                        "res_model": self._name,
                        "res_id": theme.id,
                    }
                )

    def get_domain_themes(self):
        def get_id(model_id):
            return self.env["ir.model.data"]._xmlid_to_res_id(model_id)

        return [
            ("state", "!=", "uninstallable"),
            (
                "category_id",
                "not in",
                [
                    get_id("base.module_category_hidden"),
                    get_id("base.module_category_theme_hidden"),
                ],
            ),
            "|",
            ("category_id", "=", get_id("base.module_category_theme")),
            ("category_id.parent_id", "=", get_id("base.module_category_theme")),
        ]

    def _check(self):
        super()._check()
        View = self.env["ir.ui.view"]
        views_to_adapt = self.pool.loading.state("ir.ui.view.cow_views_to_adapt", list)
        _debug.pipeline("cow_views_replayed", views=len(views_to_adapt))
        for view_replay in views_to_adapt:
            cow_view = View.browse(view_replay[0])
            View._load_records_write_on_cow(cow_view, view_replay[1], view_replay[2])
        views_to_adapt.clear()

    def _load_specific_view_terms(
        self,
        View,
        field,
        generic_arch_db,
        specific_arch_db,
        specific_id,
        langs,
        overwrite,
    ):
        langs_update = (langs & generic_arch_db.keys()) - {"en_US"}
        if not langs_update:
            return 0
        generic_arch_db_en = generic_arch_db.get("_en_US", generic_arch_db.get("en_US"))
        specific_arch_db_en = specific_arch_db.get(
            "_en_US", specific_arch_db.get("en_US")
        )
        generic_arch_db_update = {
            k: generic_arch_db.get("_" + k, generic_arch_db[k]) for k in langs_update
        }
        specific_arch_db_update = {
            k: specific_arch_db.get(
                "_" + k, specific_arch_db.get(k, specific_arch_db_en)
            )
            for k in langs_update
        }
        generic_translation_dictionary = field.get_translation_dictionary(
            generic_arch_db_en, generic_arch_db_update
        )
        specific_translation_dictionary = field.get_translation_dictionary(
            specific_arch_db_en, specific_arch_db_update
        )
        for term_en, specific_term_langs in specific_translation_dictionary.items():
            if term_en not in generic_translation_dictionary:
                continue
            for lang, generic_term_lang in generic_translation_dictionary[
                term_en
            ].items():
                if overwrite or term_en == specific_term_langs[lang]:
                    specific_term_langs[lang] = generic_term_lang
        for lang in langs_update:
            if specific_arch_db.get("_" + lang) == specific_arch_db.get(lang):
                specific_arch_db.pop("_" + lang, None)
            specific_arch_db[
                ("_" + lang) if ("_" + lang) in specific_arch_db else lang
            ] = field.translate(
                lambda term, lang=lang, translations=specific_translation_dictionary: (
                    translations.get(term, {lang: None})[lang]
                ),
                specific_arch_db_en,
            )
        field._update_cache(
            View.with_context(prefetch_langs=True).browse(specific_id),
            specific_arch_db,
            dirty=True,
        )
        _debug.lifecycle(
            "specific_view_terms", view=specific_id, langs=sorted(langs_update)
        )
        return 1

    @api.model
    def _load_module_terms(self, modules, langs, overwrite=False):
        res = super()._load_module_terms(modules, langs, overwrite=overwrite)

        if not langs or langs == ["en_US"] or not modules:
            return res

        self.env.cr.flush()
        View = self.env["ir.ui.view"]
        field = self.env["ir.ui.view"]._fields["arch_db"]
        batch_size = PREFETCH_MAX // 10
        self.env.cr.execute(""" SELECT generic.arch_db, specific.arch_db, specific.id
                                          FROM ir_ui_view generic
                                         INNER JOIN ir_ui_view specific
                                            ON generic.key = specific.key
                                         WHERE generic.website_id IS NULL AND generic.type = 'qweb'
                                         AND specific.website_id IS NOT NULL
                                         AND generic.arch_db IS NOT NULL
                                         AND specific.arch_db IS NOT NULL
                            """)
        views_updated = 0
        while batch := self.env.cr.fetchmany(batch_size):
            for generic_arch_db, specific_arch_db, specific_id in batch:
                views_updated += self._load_specific_view_terms(
                    View,
                    field,
                    generic_arch_db,
                    specific_arch_db,
                    specific_id,
                    langs,
                    overwrite,
                )
        _debug.pipeline(
            "specific_view_terms_loaded",
            modules=len(modules),
            langs=sorted(langs),
            views=views_updated,
        )
        default_menu = self.env.ref("website.main_menu", raise_if_not_found=False)
        if not default_menu:
            return res

        lang_value_list = [
            SQL("%(lang)s, o_menu.name->>%(lang)s", lang=SQL("'%s'" % lang))
            for lang in langs
            if lang != "en_US"
        ]  # pylint: disable=sql-injection
        update_jsonb_list = [
            SQL("jsonb_build_object(%s)", SQL(", ").join(items))
            for items in batched(lang_value_list, 50, strict=False)
        ]
        update_jsonb = SQL(" || ").join(update_jsonb_list)
        o_menu_name = SQL(
            "menu.name || %s" if overwrite else "%s || menu.name", update_jsonb
        )
        self.env.cr.execute(
            SQL(
                """
            UPDATE website_menu menu
               SET name = %(o_menu_name)s
              FROM website_menu o_menu
             INNER JOIN website_menu s_menu
                ON o_menu.name->>'en_US' = s_menu.name->>'en_US' AND o_menu.url = s_menu.url
             INNER JOIN website_menu root_menu
                ON s_menu.parent_id = root_menu.id AND root_menu.parent_id IS NULL
             WHERE o_menu.website_id IS NULL AND o_menu.parent_id = %(default_menu_id)s
               AND s_menu.website_id IS NOT NULL
               AND menu.id = s_menu.id
            """,
                o_menu_name=o_menu_name,
                default_menu_id=default_menu.id,
            )
        )

        return res

    @api.model
    def _create_model_data(self, views):
        self.env["ir.model.data"].create(
            [
                {
                    "name": view.key.split(".")[1],
                    "module": view.key.split(".")[0],
                    "model": "ir.ui.view",
                    "res_id": view.id,
                    "noupdate": True,
                }
                for view in views
            ]
        )

    def _create_missing_snippet_views(self, create_values):
        create_values = [values for values in create_values if values]

        keys = [values["key"] for values in create_values]
        existing_primary_template_keys = (
            self.env["ir.ui.view"]
            .with_context(active_test=False)
            .search_fetch(
                [
                    ("mode", "=", "primary"),
                    ("key", "in", keys),
                ],
                ["key"],
            )
            .mapped("key")
        )
        missing_create_values = [
            values
            for values in create_values
            if values["key"] not in existing_primary_template_keys
        ]
        missing_records = (
            self.env["ir.ui.view"]
            .with_context(no_cow=True)
            .create(missing_create_values)
        )
        self._create_model_data(missing_records)
        _debug.lifecycle(
            "snippet_templates_created",
            module=self.name,
            wanted=len(create_values),
            created=len(missing_records),
        )
        return len(missing_records)

    def _prepare_snippet_template_vals(self, name, snippet_key, parent_wrap, new_wrap):
        module, xmlid = (
            snippet_key.split(".") if "." in snippet_key else ("website", snippet_key)
        )
        parent_key = f"{module}.{parent_wrap % xmlid}"
        parent_id = self.env["ir.model.data"]._xmlid_to_res_model_res_id(
            parent_key, False
        )
        if not parent_id:
            _logger.warning("No such snippet template: %r", parent_key)
            _debug.logic(
                "snippet_template_skipped", reason="no_parent", parent=parent_key
            )
            return None
        return {
            "name": name,
            "key": f"{module}.{new_wrap % xmlid}",
            "inherit_id": parent_id[1],
            "mode": "primary",
            "type": "qweb",
            "arch": "<t/>",
        }

    def _create_new_page_snippet_templates(self, templates, get_distinct_snippet_names):
        get_create_vals = self._prepare_snippet_template_vals
        create_count = 0

        create_values = [
            get_create_vals(
                f"Snippet {snippet_name!r} for new page templates",
                snippet_name,
                "%s",
                "new_page_template_%s",
            )
            for snippet_name in get_distinct_snippet_names(templates)
        ]
        create_count += self._create_missing_snippet_views(create_values)

        create_values = [
            get_create_vals(
                f"Snippet {snippet_name!r} for new page {group!r} templates",
                snippet_name,
                "new_page_template_%s",
                f"new_page_template_{group}_%s",
            )
            for group in templates
            for snippet_name in get_distinct_snippet_names(templates[group])
        ]
        create_count += self._create_missing_snippet_views(create_values)

        create_values = [
            get_create_vals(
                f"Snippet {snippet_name!r} for new page {group!r} template {template_name!r}",
                snippet_name,
                f"new_page_template_{group}_%s",
                f"new_page_template_{group}_{template_name}_%s",
            )
            for group in templates
            for template_name in templates[group]
            for snippet_name in templates[group][template_name]
        ]
        create_count += self._create_missing_snippet_views(create_values)
        return create_count

    def _create_primary_snippet_templates(self):
        get_create_vals = self._prepare_snippet_template_vals
        create_missing_views = self._create_missing_snippet_views

        def get_distinct_snippet_names(structure):
            items = []
            for value in structure.values():
                if isinstance(value, list):
                    items.extend(value)
                else:
                    items.extend(get_distinct_snippet_names(value))
            return set(items)

        create_count = 0
        manifest = Manifest.for_addon(self.name)

        configurator_snippets = dict(manifest.get("configurator_snippets", {}))
        addons = manifest.get("configurator_snippets_addons", {})
        installed_modules = self.env["ir.module.module"]._get_installed_module_ids()

        for module_name, pages in addons.items():
            if module_name not in installed_modules and module_name != self.name:
                continue
            for page, snippets_to_insert in pages.items():
                snippets = configurator_snippets.setdefault(page, [])
                dynamic_snippets = [snippet for snippet, *_ in snippets_to_insert]
                configurator_snippets[page] = list(
                    dict.fromkeys(snippets + dynamic_snippets)
                )

        create_values = [
            get_create_vals(
                f"Snippet {snippet_name!r} for pages generated by the configurator",
                snippet_name,
                "%s",
                "configurator_%s",
            )
            for snippet_name in get_distinct_snippet_names(configurator_snippets)
        ]
        create_count += create_missing_views(create_values)

        create_values = []
        for page_name, page_snippets in configurator_snippets.items():
            for snippet_name in set(page_snippets):
                create_values.append(
                    get_create_vals(
                        f"Snippet {snippet_name!r} for {page_name!r} pages generated by the configurator",
                        snippet_name,
                        "configurator_%s",
                        f"configurator_{page_name}_%s",
                    )
                )
        create_count += create_missing_views(create_values)

        templates = manifest.get("new_page_templates", {})
        create_count += self._create_new_page_snippet_templates(
            templates, get_distinct_snippet_names
        )

        _debug.pipeline(
            "primary_snippet_templates",
            module=self.name,
            created=create_count,
            configurator_pages=len(configurator_snippets),
            template_groups=len(templates),
        )
        if create_count:
            _logger.info(
                "Generated %s primary snippet templates for %r", create_count, self.name
            )

    def _create_primary_page_templates(self):
        View = self.env["ir.ui.view"]
        manifest = Manifest.for_addon(self.name)
        templates = manifest["new_page_templates"]

        create_values = []
        for group in templates:
            for template_name in templates[group]:
                xmlid = (
                    f"{self.name}.new_page_template_sections_{group}_{template_name}"
                )
                wrapper = f"%s.new_page_template_{group}_{template_name}_%s"
                calls = "\n    ".join(
                    [
                        f'''<t t-snippet-call="{wrapper % (snippet_key.split(".") if "." in snippet_key else ("website", snippet_key))}"/>'''
                        for snippet_key in templates[group][template_name]
                    ]
                )
                create_values.append(
                    {
                        "name": f"New page template: {template_name!r} in {group!r}",
                        "type": "qweb",
                        "key": xmlid,
                        "arch": f'<div id="wrap">\n    {calls}\n</div>',
                    }
                )
        keys = [values["key"] for values in create_values]
        existing_primary_templates = View.search_read(
            [("mode", "=", "primary"), ("key", "in", keys)], ["key"]
        )
        existing_primary_template_keys = {
            data["key"]: data["id"] for data in existing_primary_templates
        }
        missing_create_values = []
        update_count = 0
        for create_value in create_values:
            if create_value["key"] in existing_primary_template_keys:
                View.browse(
                    existing_primary_template_keys[create_value["key"]]
                ).with_context(no_cow=True).write(
                    {
                        "arch": create_value["arch"],
                    }
                )
                update_count += 1
            else:
                missing_create_values.append(create_value)
        _debug.pipeline(
            "primary_page_templates",
            module=self.name,
            wanted=len(create_values),
            created=len(missing_create_values),
            updated=update_count,
        )
        if missing_create_values:
            missing_records = View.create(missing_create_values)
            self._create_model_data(missing_records)
            _logger.info(
                "Generated %s primary page templates for %r",
                len(missing_create_values),
                self.name,
            )
        if update_count:
            _logger.info(
                "Updated %s primary page templates for %r", update_count, self.name
            )
