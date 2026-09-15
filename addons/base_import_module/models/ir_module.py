import ast
import base64
import io
import json
import logging
import zipfile
from collections import defaultdict
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path

import lxml
import requests
from babel.messages import extract

from odoo import _, api, fields, models
from odoo.exceptions import AccessDenied, AccessError, UserError
from odoo.fields import Domain
from odoo.http import request
from odoo.modules.module import MANIFEST_NAMES, Manifest
from odoo.release import major_version
from odoo.tools import (
    SQL,
    convert_file,
    file_open,
    file_open_temporary_directory,
    file_path,
    ormcache,
)
from odoo.tools.misc import OrderedSet, topological_sort
from odoo.tools.translate import (
    JAVASCRIPT_TRANSLATION_COMMENT,
    CodeTranslations,
    TranslationImporter,
    get_base_langs,
)

from odoo.addons.base.models.ir_asset import is_wildcard_glob

_logger = logging.getLogger(__name__)

APPS_URL = "https://apps.odoo.com"
MAX_FILE_SIZE = 100 * 1024 * 1024  # in bytes (100 MB)
# Cumulative cap across every file actually written to disk while extracting
# an uploaded module zip. `ZipInfo.file_size` (used for the per-file MAX_FILE_SIZE
# check above) is declared, attacker-controlled metadata from the zip's central
# directory — it does not bound the real decompressed size of a hand-crafted
# deflate stream (classic zip-bomb). This second cap is checked against bytes
# actually on disk after each extraction (t24068).
MAX_TOTAL_EXTRACTED_SIZE = 500 * 1024 * 1024  # in bytes (500 MB)


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    imported = fields.Boolean(string="Imported Module")
    module_type = fields.Selection(
        selection=[
            ("official", "Official Apps"),
            ("industries", "Industries"),
        ],
        default="official",
    )

    @api.model
    @ormcache(cache="stable")
    def _get_imported_module_names(self):
        return OrderedSet(
            self.sudo()
            .search_fetch(
                [("imported", "=", True), ("state", "=", "installed")], ["name"]
            )
            .mapped("name")
        )

    def _get_domain_modules_to_load(self):
        # imported modules are not expected to be loaded as regular modules
        return super()._get_domain_modules_to_load() + [("imported", "=", False)]

    @api.model
    def _load_module_terms(self, modules, langs, overwrite=False):
        super()._load_module_terms(modules, langs, overwrite=overwrite)

        translation_importer = TranslationImporter(self.env.cr, verbose=False)
        IrAttachment = self.env["ir.attachment"]

        for module in modules:
            if Manifest.for_addon(module, display_warning=False):
                continue
            for lang in langs:
                for lang_ in get_base_langs(lang):
                    # Translations for imported data modules only works with imported po files
                    attachment = IrAttachment.sudo().search(  # noqa: E8507 - one lookup per (module, language) pair
                        [
                            ("name", "=", f"{module}_{lang_}.po"),
                            ("url", "=", f"/{module}/i18n/{lang_}.po"),
                            ("type", "=", "binary"),
                        ],
                        limit=1,
                    )
                    if attachment.raw:
                        try:
                            with io.BytesIO(attachment.raw) as fileobj:
                                fileobj.name = attachment.name
                                translation_importer.load(
                                    fileobj, "po", lang, module=module
                                )
                        except Exception:
                            _logger.warning(
                                "module %s: failed to load translation attachment %s for language %s",
                                module,
                                attachment.name,
                                lang,
                            )
                if lang != "en_US" and lang not in translation_importer.imported_langs:
                    _logger.info(
                        "module %s: no translation for language %s", module, lang
                    )

        translation_importer.save(overwrite=overwrite)

    @api.depends("name")
    def _compute_manifest_version(self):
        imported_modules = self.filtered(lambda m: m.imported and m.db_version)
        for module in imported_modules:
            module.manifest_version = module.db_version
        super(IrModuleModule, self - imported_modules)._compute_manifest_version()

    @api.depends("icon")
    def _compute_icon_display(self):
        super()._compute_icon_display()
        IrAttachment = self.env["ir.attachment"]
        for module in self.filtered("imported"):
            attachment = IrAttachment.sudo().search(  # noqa: E8507 - one lookup per imported module, on its own icon attachment
                [
                    ("url", "=", module.icon),
                    ("type", "=", "binary"),
                    ("res_model", "=", "ir.ui.view"),
                ],
                limit=1,
            )
            if attachment:
                module.icon_image = attachment.datas

    @contextmanager
    def _neutralized_website(self):
        # Do not involve specific website during import by resetting
        # information used by website's get_current_website.
        force_website_id = None
        if request and request.session.get("force_website_id"):
            force_website_id = request.session.pop("force_website_id")
        try:
            yield
        finally:
            if force_website_id:
                request.session["force_website_id"] = force_website_id

    def _prepare_imported_module_vals(self, terp, with_demo):
        values = self.get_values_from_terp(terp)
        try:
            icon_path = terp.get_raw_value("icon") or str(
                Path(terp.name) / "static/description/icon.png"
            )
            file_path(icon_path, env=self.env, check_exists=True)
            values["icon"] = "/" + icon_path
        except OSError:
            pass  # keep the default icon
        values["db_version"] = terp.version
        if self.env.context.get("data_module"):
            values["module_type"] = "industries"
        if with_demo:
            values["demo"] = True
        return values

    def _install_manifest_dependencies(self, terp, path, known_mods, installed_mods):
        unmet_dependencies = set(terp.get("depends", [])).difference(installed_mods)
        if not unmet_dependencies:
            if "web_studio" not in installed_mods and _is_studio_custom(path):
                raise UserError(_("Studio customizations require the Odoo Studio app."))
            return

        wrong_dependencies = unmet_dependencies.difference(known_mods.mapped("name"))
        if wrong_dependencies:
            raise UserError(
                _("Unknown module dependencies:")
                + "\n - "
                + "\n - ".join(wrong_dependencies)
            )
        to_install = known_mods.filtered(lambda mod: mod.name in unmet_dependencies)
        # t27114: button_immediate_install() hard-commits the current
        # transaction (twice) and reloads the registry — it cannot be
        # wrapped in a savepoint, because a real COMMIT ends the
        # transaction a savepoint lives in. So if _import_zipfile's
        # per-module loop later fails on a *different* module in the
        # same zip, this dependency install is NOT rolled back with it:
        # the user-facing "import failed" error does not mean nothing
        # was applied. This is accepted, not fixed — there is no
        # transactional way to undo a registry-reloading install once
        # it has committed.
        to_install.button_immediate_install()

    def _upsert_imported_module(self, module, values, terp, known_mods, force):
        mod = next((m for m in known_mods if m.name == module), None)
        if mod:
            mod.write(dict(state="installed", **values))
            return mod, "update" if not force else "init"

        assert terp.get("installable", True), "Module not installable"
        mod = self.create(dict(name=module, state="installed", imported=True, **values))
        return mod, "init"

    def _get_cloc_exclude_paths(self, terp, base_dir):
        exclude_list = set()
        for pattern in terp.get("cloc_exclude", []):
            exclude_list.update(
                str(p.relative_to(base_dir))
                for p in base_dir.glob(pattern)
                if p.is_file()
            )
        return exclude_list

    def _load_imported_data_files(
        self, module, path, terp, mode, with_demo, exclude_list
    ):
        kind_of_files = ["data", "init_xml"]
        if with_demo:
            kind_of_files.append("demo")
        for kind in kind_of_files:
            for filename in terp.get(kind, []):
                ext = Path(filename).suffix.lower()
                if ext not in (".xml", ".csv", ".sql"):
                    _logger.info(
                        "module %s: skip unsupported file %s", module, filename
                    )
                    continue
                _logger.info("module %s: loading %s", module, filename)
                noupdate = ext == ".csv" and kind == "init_xml"
                idref = {}
                convert_file(
                    self.env,
                    module,
                    filename,
                    idref,
                    mode,
                    noupdate,
                    pathname=str(Path(path) / filename),
                )
                if filename in exclude_list:
                    self._mark_cloc_excluded_records(idref)

    def _mark_cloc_excluded_records(self, idref):
        IrModelData = self.env["ir.model.data"]
        for xml_id, rec_id in idref.items():
            name = xml_id.replace(".", "_")
            if self.env.ref(f"__cloc_exclude__.{name}", raise_if_not_found=False):
                continue
            IrModelData.create(
                [
                    {
                        "name": name,
                        "model": IrModelData._get_xmlid_target(xml_id)[0],
                        "module": "__cloc_exclude__",
                        "res_id": rec_id,
                    }
                ]
            )

    def _get_attachments_by_url(self, urls, domain):
        """Every existing attachment for ``urls``, grouped by url, in one query.

        The lookup used to sit inside the per-file loop, so importing a module
        issued one ``ir.attachment`` SELECT per static file and per translation
        it shipped. Grouped rather than flat because the url is not unique by
        construction, and the callers' write-or-create must keep seeing every
        row a per-file search would have returned.

        :param urls: the urls to look for
        :param list domain: the rest of the callers' search domain
        :rtype: dict[str, odoo.models.Model]
        """
        urls = list(urls)
        if not urls:
            return {}
        attachments = (
            self.env["ir.attachment"].sudo().search([("url", "in", urls), *domain])
        )
        by_url = {}
        for attachment in attachments:
            by_url[attachment.url] = (
                by_url.get(attachment.url, attachments.browse()) | attachment
            )
        return by_url

    def _import_static_attachments(self, module, path, base_dir, exclude_list):
        path_static = Path(path) / "static"
        if not path_static.is_dir():
            return

        IrAttachment = self.env["ir.attachment"]
        IrModelData = self.env["ir.model.data"]
        # Do not create a bridge module for this check.
        is_public_aware = "public" in IrAttachment._fields

        static_files = [
            str(root / static_file)
            for root, _dirs, files in path_static.walk()
            for static_file in files
        ]
        url_paths = {
            full_path: f"/{module}/{Path(full_path).relative_to(path).as_posix()}"
            for full_path in static_files
        }
        existing = self._get_attachments_by_url(
            url_paths.values(),
            [("type", "=", "binary"), ("res_model", "=", "ir.ui.view")],
        )

        for full_path in static_files:
            url_path = url_paths[full_path]
            with file_open(full_path, "rb", env=self.env) as fp:
                data = base64.b64encode(fp.read())
            values = {
                "name": Path(url_path).name,
                "url": url_path,
                "res_model": "ir.ui.view",
                "type": "binary",
                "datas": data,
            }
            if is_public_aware:
                # Static data is public and not website-specific.
                values["public"] = True

            attachment = existing.get(url_path)
            if attachment:
                attachment.write(values)
                continue

            attachment = IrAttachment.create(values)
            IrModelData.create(
                {
                    "name": f"attachment_{url_path}".replace(".", "_").replace(
                        " ", "_"
                    ),
                    "model": "ir.attachment",
                    "module": module,
                    "res_id": attachment.id,
                }
            )
            if str(Path(full_path).relative_to(base_dir)) in exclude_list:
                IrModelData.create(
                    {
                        "name": f"cloc_exclude_attachment_{url_path}".replace(
                            ".", "_"
                        ).replace(" ", "_"),
                        "model": "ir.attachment",
                        "module": "__cloc_exclude__",
                        "res_id": attachment.id,
                    }
                )

    def _import_translation_attachments(self, module, path, mod):
        # store translation files as attachments to allow loading translations
        # for webclient
        path_lang = Path(path) / "i18n"
        if not path_lang.is_dir():
            return

        IrAttachment = self.env["ir.attachment"]
        entries = [
            entry
            for entry in path_lang.iterdir()
            # we don't support sub-directories in i18n
            if entry.is_file() and entry.name.endswith(".po")
        ]
        langs = {entry: entry.name.split(".")[0] for entry in entries}
        existing = self._get_attachments_by_url(
            [f"/{module}/i18n/{lang}.po" for lang in langs.values()],
            [("type", "=", "binary")],
        )

        for entry in entries:
            lang = langs[entry]
            with file_open(str(entry), "rb", env=self.env) as fp:
                raw = fp.read()
            # store as binary ir.attachment
            values = {
                "name": f"{module}_{lang}.po",
                "url": f"/{module}/i18n/{lang}.po",
                "res_model": "ir.module.module",
                "res_id": mod.id,
                "type": "binary",
                "raw": raw,
            }
            candidates = existing.get(values["url"], IrAttachment)
            attachment = candidates.filtered(lambda a, n=values["name"]: a.name == n)
            if attachment:
                attachment.write(values)
                continue

            attachment = IrAttachment.create(values)
            self.env["ir.model.data"].create(
                {
                    "name": f"attachment_{module}_{lang}".replace(".", "_").replace(
                        " ", "_"
                    ),
                    "model": "ir.attachment",
                    "module": module,
                    "res_id": attachment.id,
                }
            )

    def _prepare_manifest_asset_vals(self, module, terp):
        IrAsset = self.env["ir.asset"]
        assets_vals = []
        for bundle, commands in terp.get("assets", {}).items():
            for command in commands:
                directive, target, path = IrAsset._parse_manifest_command(command)
                if is_wildcard_glob(path):
                    raise UserError(
                        _(
                            "The assets path in the manifest of imported module "
                            "'%(module_name)s' cannot contain glob wildcards "
                            "(e.g., *, **).",
                            module_name=module,
                        )
                    )
                path = path if path.startswith("/") else "/" + path
                assets_vals.append(
                    {
                        "name": f"{module}.{bundle}.{path}",
                        "directive": directive,
                        "target": target,
                        "path": path,
                        "bundle": bundle,
                    }
                )
        return assets_vals

    def _import_manifest_assets(self, module, terp):
        IrAsset = self.env["ir.asset"]
        assets_vals = self._prepare_manifest_asset_vals(module, terp)

        existing_assets = {
            asset.name: asset
            for asset in IrAsset.search(
                [("name", "in", [vals["name"] for vals in assets_vals])]
            )
        }
        assets_to_create = []
        for values in assets_vals:
            if values["name"] in existing_assets:
                existing_assets[values["name"]].write(values)
            else:
                assets_to_create.append(values)

        created_assets = IrAsset.create(assets_to_create)
        self.env["ir.model.data"].create(
            [
                {
                    "name": f"{asset['bundle']}_{asset['path']}".replace(".", "_"),
                    "model": "ir.asset",
                    "module": module,
                    "res_id": asset.id,
                }
                for asset in created_assets
            ]
        )

    def _render_welcome_article(self, module):
        if "knowledge.article" not in self.env:
            return
        article_record = self.env.ref(
            f"{module}.welcome_article", raise_if_not_found=False
        )
        if (
            not article_record
            or article_record._name != "knowledge.article"
            or not self.env.ref(
                f"{module}.welcome_article_body", raise_if_not_found=False
            )
        ):
            return
        body = self.env["ir.qweb"]._render(
            f"{module}.welcome_article_body", lang=self.env.user.lang
        )
        article_record.write({"body": body})

    def _import_module(self, module, path, force=False, with_demo=False):
        """Import module at path into the database, installing it if needed."""
        # Do not create a bridge module for these neutralizations.
        self = self.with_context(website_id=None)
        with self._neutralized_website():
            terp = Manifest._from_path(path, env=self.env)
            if not terp:
                return False

            known_mods = self.search([])
            installed_mods = [m.name for m in known_mods if m.state == "installed"]

            values = self._prepare_imported_module_vals(terp, with_demo)
            self._install_manifest_dependencies(terp, path, known_mods, installed_mods)
            mod, mode = self._upsert_imported_module(
                module, values, terp, known_mods, force
            )

            base_dir = Path(path)
            exclude_list = self._get_cloc_exclude_paths(terp, base_dir)
            self._load_imported_data_files(
                module, path, terp, mode, with_demo, exclude_list
            )
            self._import_static_attachments(module, path, base_dir, exclude_list)
            self._import_translation_attachments(module, path, mod)
            self._import_manifest_assets(module, terp)

            self._load_module_terms(
                [module],
                [lang for lang, _name in self.env["res.lang"].get_installed()],
                overwrite=True,
            )
            self._render_welcome_article(module)

            mod._update_from_terp(terp)
            _logger.info("Successfully imported module '%s'", module)
            return True

    def _check_zip_upload(self, module_file):
        """Refuse an upload that is not an admin-sent zip archive."""
        if not self.env.is_admin():
            raise AccessError(_("Only administrators can install data modules."))
        if not module_file:
            raise UserError(_("No file sent."))
        if not zipfile.is_zipfile(module_file):
            raise UserError(_("Only zip files are supported."))

    def _read_zip_manifests(self, z, extract, module_dir, with_demo):
        """Extract each module's manifest and read what it declares.

        :param z: the open archive
        :param extract: the size-budgeted extractor, see :meth:`_import_zipfile`
        :param str module_dir: the temporary directory being extracted into
        :param bool with_demo: whether demo data is wanted too
        :returns: ``({module: [data file, ...]}, {module: [dependency, ...]})``
        :rtype: tuple[dict, dict]
        """
        manifest_files = sorted(
            (file.filename.split("/")[0], file)
            for file in z.infolist()
            if file.filename.count("/") == 1
            and file.filename.split("/")[1] in MANIFEST_NAMES
        )
        module_data_files = defaultdict(list)
        dependencies = defaultdict(list)
        module_dir_path = Path(module_dir)
        for mod_name, manifest in manifest_files:
            extract(manifest)
            terp = Manifest._from_path(str(module_dir_path / mod_name), env=self.env)
            if not terp:
                continue
            files_to_import = (
                terp.get("data", [])
                + terp.get("init_xml", [])
                + terp.get("update_xml", [])
            )
            if with_demo:
                files_to_import += terp.get("demo", [])
            for filename in files_to_import:
                if Path(filename).suffix.lower() not in (".xml", ".csv", ".sql"):
                    continue
                module_data_files[mod_name].append(f"{mod_name}/{filename}")
            dependencies[mod_name] = terp.get("depends", [])
        return module_data_files, dependencies

    def _sort_zip_modules(self, module_dir, dependencies):
        """The archive's modules in dependency order.

        Refuses the whole archive if it holds a directory no manifest claimed,
        rather than importing the rest and leaving that one silently dropped.

        :rtype: list[str]
        """
        dirs = {d.name for d in Path(module_dir).iterdir() if d.is_dir()}
        sorted_dirs = topological_sort(dependencies)
        if wrong_modules := dirs.difference(sorted_dirs):
            raise UserError(
                _(
                    "No manifest found in '%(modules)s'. Can't import the zip file.",
                    modules=", ".join(wrong_modules),
                )
            )
        return sorted_dirs

    def _extract_zip_module_files(self, z, extract, module_data_files):
        """Extract the data, static and translation files of every module.

        Everything else in the archive stays unextracted, which is what keeps
        the extraction budget spent on files that will actually be loaded.
        """
        for file in z.infolist():
            filename = file.filename
            mod_name = filename.split("/")[0]
            is_data_file = filename in module_data_files[mod_name]
            is_static = filename.startswith(f"{mod_name}/static")
            is_translation = filename.startswith(
                f"{mod_name}/i18n"
            ) and filename.endswith(".po")
            if is_data_file or is_static or is_translation:
                extract(file)

    def _import_zip_modules(self, sorted_dirs, module_dir, force, with_demo):
        """Import every module of the archive, in dependency order.

        :rtype: list[str]
        """
        module_names = []
        for mod_name in sorted_dirs:
            module_names.append(mod_name)
            try:
                path = str(Path(module_dir) / mod_name)
                self.sudo()._import_module(
                    mod_name, path, force=force, with_demo=with_demo
                )
            except Exception as e:
                # Full traceback (file paths, line numbers) goes to the
                # server log only; the user-facing UserError carries just
                # the exception's own message (t24068 — this message was
                # embedding traceback.format_exc() verbatim, surfaced
                # as-is in both the wizard's error dialog and the CLI
                # deploy endpoint's HTTP 500 body). Note this message
                # does not mean the whole zip's effects were undone: an
                # earlier module's dependency auto-install
                # (_import_module's button_immediate_install() call,
                # t27114) hard-commits before this loop even gets here.
                _logger.exception("Error while importing module %r from zip", mod_name)
                raise UserError(
                    _(
                        "Error while importing module '%(module)s'.\n\n%(error_message)s",
                        module=mod_name,
                        error_message=e,
                    )
                ) from e
        return module_names

    @api.model
    def _import_zipfile(self, module_file, force=False, with_demo=False):
        """Extract and import every module found in the uploaded zip archive."""
        self._check_zip_upload(module_file)

        with zipfile.ZipFile(module_file, "r") as z:
            for zf in z.infolist():
                if zf.file_size > MAX_FILE_SIZE:
                    raise UserError(
                        _("File '%s' exceed maximum allowed file size", zf.filename)
                    )

            with file_open_temporary_directory(self.env) as module_dir:
                extracted_total_size = 0

                def _extract(zip_info):
                    nonlocal extracted_total_size
                    path = z.extract(zip_info, module_dir)
                    extracted_total_size += Path(path).stat().st_size
                    if extracted_total_size > MAX_TOTAL_EXTRACTED_SIZE:
                        raise UserError(
                            _("The module archive is too large once extracted.")
                        )
                    return path

                module_data_files, dependencies = self._read_zip_manifests(
                    z, _extract, module_dir, with_demo
                )
                sorted_dirs = self._sort_zip_modules(module_dir, dependencies)
                self._extract_zip_module_files(z, _extract, module_data_files)
                module_names = self._import_zip_modules(
                    sorted_dirs, module_dir, force, with_demo
                )
        return "", module_names

    def module_uninstall(self):
        # Delete an ir_module_module record completely if it was an imported
        # one. The rationale behind this is that an imported module *cannot* be
        # reinstalled anyway, as it requires the data files. Any attempt to
        # install it again will simply fail without trace.
        # /!\ modules_to_delete must be calculated before calling super().module_uninstall(),
        # because when uninstalling `base_import_module` the `imported` column will no longer be
        # in the database but we'll still have an old registry that runs this code.
        modules_to_delete = self.filtered("imported")
        res = super().module_uninstall()
        if modules_to_delete:
            deleted_modules_names = modules_to_delete.mapped("name")
            _logger.info(
                "deleting imported modules upon uninstallation: %s",
                ", ".join(deleted_modules_names),
            )
            modules_to_delete.unlink()
        return res

    @api.model
    def web_search_read(
        self, domain, specification, offset=0, limit=None, order=None, count_limit=None
    ):
        if _domain_asks_for_industries(domain):
            fields_name = list(specification.keys())
            modules_list = self._get_modules_from_apps(
                fields_name, "industries", False, domain, offset=offset
            )
            return {
                "length": len(modules_list) + offset,
                "records": modules_list[: (limit or 80)],
            }
        else:
            return super().web_search_read(
                domain,
                specification,
                offset=offset,
                limit=limit,
                order=order,
                count_limit=count_limit,
            )

    def more_info(self):
        return {
            "name": _("Apps"),
            "type": "ir.actions.act_window",
            "res_model": "ir.module.module",
            "view_mode": "form",
            "res_id": self.id,
            "context": self.env.context,
        }

    def web_read(self, specification):
        fields = list(specification.keys())
        module_type = self.env.context.get("module_type", "official")
        if module_type == "industries":
            return self._get_modules_from_apps(
                fields, module_type, self.env.context.get("module_name")
            )
        else:
            return super().web_read(specification)

    def _decorate_apps_modules(self, modules_list, fields, module_type):
        """Fill in the fields apps.odoo.com cannot know, in place.

        Whether the module is installed here, and the URLs that are only
        meaningful relative to this deployment's series.
        """
        existing_modules = self.search(
            [
                ("name", "in", [mod["name"] for mod in modules_list]),
                ("state", "=", "installed"),
            ]
        )
        existing_module_ids = {mod.name: mod.id for mod in existing_modules}
        for mod in modules_list:
            mod_name = mod["name"]
            existing_mod_id = existing_module_ids.get(mod_name)
            mod["id"] = existing_mod_id or -1
            if "icon" in fields:
                mod["icon"] = f"{APPS_URL}{mod['icon']}"
            if "state" in fields:
                mod["state"] = "installed" if existing_mod_id else "uninstalled"
            if "module_type" in fields:
                mod["module_type"] = module_type
            if "website" in fields:
                mod["website"] = f"{APPS_URL}/apps/modules/{major_version}/{mod_name}/"

    def _filter_apps_modules(self, modules_list, domain):
        """Re-apply ``domain`` to the fields only this side could fill in.

        :rtype: list[dict]
        """
        # t27114: `domain` is forwarded to apps.odoo.com by the caller, but
        # fields computed only locally (e.g. `state`, just set from local
        # install status) can never be filtered by the remote server.
        # Re-apply the domain locally against those now-known values.
        # `category_id` is excluded: it does not exist on these modules and
        # was already applied server-side (same caveat as upstream).
        domain_without_category = Domain(domain).map_conditions(
            lambda c: Domain.TRUE if c.field_expr == "category_id" else c
        )
        new_records = self.browse()
        for mod in modules_list:
            new_records += self.new({k: v for k, v in mod.items() if k in self._fields})
        # `.ids` resolves to real/origin ids and is empty for pure
        # `.new()` records (no origin) — use the raw `._ids` tuple
        # (NewId objects) to match filtered_domain()'s own result.
        kept_ids = set(new_records.filtered_domain(domain_without_category)._ids)
        return [
            mod
            for mod, rec_id in zip(modules_list, new_records._ids, strict=True)
            if rec_id in kept_ids
        ]

    @api.model
    def _get_modules_from_apps(
        self, fields, module_type, module_name, domain=None, limit=None, offset=None
    ):
        if "name" not in fields:
            fields = [*fields, "name"]
        payload = {
            "params": {
                "series": major_version,
                "module_fields": fields,
                "module_type": module_type,
                "module_name": module_name,
                "domain": domain,
                "limit": limit,
                "offset": offset,
            }
        }

        try:
            resp = self._call_apps(json.dumps(payload))
            resp.raise_for_status()
            modules_list = resp.json().get("result", [])
            self._decorate_apps_modules(modules_list, fields, module_type)
            if domain:
                modules_list = self._filter_apps_modules(modules_list, domain)
            return modules_list
        except requests.exceptions.HTTPError:
            raise UserError(
                _(
                    "The list of industry applications cannot be fetched. Please try again later"
                )
            ) from None
        except requests.exceptions.ConnectionError:
            raise UserError(
                _(
                    "Connection to %s failed The list of industry modules cannot be fetched"
                )
                % APPS_URL
            ) from None

    @api.model
    @ormcache("payload")
    def _call_apps(self, payload):
        headers = {"Content-type": "application/json", "Accept": "text/plain"}
        return self.env["ir.egress"].request(
            "POST",
            f"{APPS_URL}/loempia/listdatamodules",
            purpose="apps_store",
            data=payload,
            headers=headers,
            timeout=5.0,
        )

    @api.model
    @ormcache()
    def _get_industry_categories_from_apps(self):
        try:
            resp = self.env["ir.egress"].request(
                "POST",
                f"{APPS_URL}/loempia/listindustrycategory/{major_version}",
                purpose="apps_store",
                json={"params": {}},
                timeout=5.0,
            )
            resp.raise_for_status()
            return resp.json().get("result", [])
        except requests.exceptions.HTTPError:
            return []
        except requests.exceptions.ConnectionError:
            return []

    def button_upgrade(self):
        res = super().button_upgrade()
        # revert states for imported modules since they cannot be upgraded
        self.search(
            [("imported", "=", True), ("state", "=", "to upgrade")]
        ).state = "installed"
        return res

    def button_immediate_install_app(self):
        if not self.env.is_admin():
            raise AccessDenied
        module_name = self.env.context.get("module_name")
        try:
            resp = self.env["ir.egress"].request(
                "GET",
                f"{APPS_URL}/loempia/download/data_app/{module_name}/{major_version}",
                purpose="apps_store",
                timeout=5.0,
            )
            resp.raise_for_status()
            missing_dependencies_description, unavailable_modules = (
                self._get_missing_dependencies(resp.content)
            )
            if unavailable_modules:
                raise UserError(missing_dependencies_description)
            import_module = self.env["base.import.module"].create(
                {
                    "module_file": base64.b64encode(resp.content),
                    "state": "init",
                    "modules_dependencies": missing_dependencies_description,
                }
            )
            return {
                "name": _("Install an Industry"),
                "view_mode": "form",
                "target": "new",
                "res_id": import_module.id,
                "res_model": "base.import.module",
                "type": "ir.actions.act_window",
                "context": {"data_module": True},
            }
        except requests.exceptions.HTTPError:
            raise UserError(
                _("The module %s cannot be downloaded") % module_name
            ) from None
        except requests.exceptions.ConnectionError:
            raise UserError(
                _(
                    "Connection to %(url)s failed, the module %(module)s cannot be downloaded.",
                    url=APPS_URL,
                    module=module_name,
                )
            ) from None

    @api.model
    def _get_missing_dependencies(self, zip_data):
        _modules, unavailable_modules = self._get_missing_dependencies_modules(zip_data)
        description = ""
        if unavailable_modules:
            description = _(
                "The installation of the data module would fail as the following dependencies can't"
                " be found in the addons-path:\n"
            )
            for module in unavailable_modules:
                description += "- " + module + "\n"
            description += _(
                "\nYou may need the Enterprise version to install the data module. Please visit "
                "https://www.odoo.com/pricing-plan for more information.\n"
                "If you need Website themes, it can be downloaded from https://github.com/odoo/design-themes.\n"
            )
        else:
            description = _(
                "Load demo data to test the industry's features with sample records. "
                "Do not load them if this is your production database.",
            )
        return description, unavailable_modules

    def _get_missing_dependencies_modules(self, zip_data):
        dependencies_to_install = self.env["ir.module.module"]
        known_mods = self.search([("to_buy", "=", False)])
        installed_mods = [m.name for m in known_mods if m.state == "installed"]
        not_found_modules = set()
        with zipfile.ZipFile(BytesIO(zip_data), "r") as z:
            manifest_files = [
                file
                for file in z.infolist()
                if file.filename.count("/") == 1
                and file.filename.split("/")[1] in MANIFEST_NAMES
            ]
            modules_in_zip = {
                manifest.filename.split("/")[0] for manifest in manifest_files
            }
            for manifest_file in manifest_files:
                if manifest_file.file_size > MAX_FILE_SIZE:
                    raise UserError(
                        _(
                            "File '%s' exceed maximum allowed file size",
                            manifest_file.filename,
                        )
                    )
                try:
                    with z.open(manifest_file) as manifest:
                        terp = ast.literal_eval(manifest.read().decode())
                except Exception:
                    _logger.debug(
                        "skipping invalid manifest %s in uploaded zip",
                        manifest_file.filename,
                    )
                    continue
                unmet_dependencies = set(terp.get("depends", [])).difference(
                    installed_mods, modules_in_zip
                )
                dependencies_to_install |= known_mods.filtered(
                    lambda m, unmet=unmet_dependencies: m.name in unmet
                )
                not_found_modules |= {
                    mod
                    for mod in unmet_dependencies
                    if mod not in dependencies_to_install.mapped("name")
                }
        return dependencies_to_install, not_found_modules

    @api.model
    def search_panel_select_range(self, field_name, **kwargs):
        if field_name == "category_id" and _domain_asks_for_industries(
            kwargs.get("category_domain", [])
        ):
            categories = self._get_industry_categories_from_apps()
            return {
                "parent_field": "parent_id",
                "values": categories,
            }
        return super().search_panel_select_range(field_name, **kwargs)

    @api.model
    @ormcache("module", "lang", cache="stable")
    def _get_imported_module_translations_for_webclient(self, module, lang):
        if not lang:
            lang = self.env.context.get("lang") or "en_US"
        IrAttachment = self.env["ir.attachment"]

        def filter_func(row):
            return (
                row.get("value") and JAVASCRIPT_TRANSLATION_COMMENT in row["comments"]
            )

        translations = {}
        for lang_ in get_base_langs(lang):
            attachment = IrAttachment.sudo().search(  # noqa: E8507 - one lookup per base language of the requested one
                [
                    ("name", "=", f"{module}_{lang_}.po"),
                    ("url", "=", f"/{module}/i18n/{lang_}.po"),
                    ("res_model", "=", "ir.module.module"),
                    ("res_id", "=", self._get_id(module)),
                    ("type", "=", "binary"),
                ],
                limit=1,
            )
            if attachment.raw:
                try:
                    with io.BytesIO(attachment.raw) as fileobj:
                        fileobj.name = attachment.name
                        webclient_translations = (
                            CodeTranslations._read_code_translations_file(
                                fileobj, filter_func
                            )
                        )
                        translations.update(webclient_translations)
                except Exception:
                    _logger.warning(
                        "module %s: failed to load translation attachment %s for language %s",
                        module,
                        attachment.name,
                        lang,
                    )

        return {
            "messages": tuple(
                {
                    "id": src,
                    "string": value,
                }
                for src, value in translations.items()
            )
        }

    @api.model
    def _extract_resource_attachment_translations(self, module, lang):
        yield from super()._extract_resource_attachment_translations(module, lang)
        if not self._get(module).imported:
            return
        self.env["ir.model.data"].flush_model()
        IrAttachment = self.env["ir.attachment"]
        IrAttachment.flush_model()
        module_ = module.replace("_", r"\_")
        ids = [
            r[0]
            for r in self.env.execute_query(
                SQL(
                    """
                SELECT ia.id
                FROM ir_attachment ia
                JOIN ir_model_data imd
                ON ia.id = imd.res_id
                AND imd.model = 'ir.attachment'
                AND imd.module = %(module)s
                AND ia.res_model = 'ir.ui.view'
                AND ia.res_field IS NULL
                AND ia.res_id IS NULL
                AND (ia.url ilike %(js_pattern)s or ia.url ilike %(xml_pattern)s)
                AND ia.type = 'binary'
                ORDER BY ia.url
            """,
                    module=module,
                    js_pattern=f"/{module_}/static/src/%.js",
                    xml_pattern=f"/{module_}/static/src/%.xml",
                )
            )
        ]
        attachments = IrAttachment.browse(OrderedSet(ids))
        if not attachments:
            return
        translations = self._get_imported_module_translations_for_webclient(
            module, lang
        )
        translations = {tran["id"]: tran["string"] for tran in translations["messages"]}
        for attachment in attachments.filtered("raw"):
            display_path = f"addons{attachment.url}"
            if attachment.url.endswith("js"):
                extract_method = "odoo.tools.babel_extractors:extract_javascript"
                extract_keywords = {"_t": None}
            else:
                extract_method = "odoo.tools.translate:babel_extract_qweb"
                extract_keywords = {}
            try:
                with io.BytesIO(attachment.raw) as fileobj:
                    for extracted in extract.extract(
                        extract_method, fileobj, keywords=extract_keywords
                    ):
                        lineno, message, comments = extracted[:3]
                        value = translations.get(message, "")
                        # (module, ttype, name, res_id, source, comments, record_id, value)
                        yield (
                            module,
                            "code",
                            display_path,
                            lineno,
                            message,
                            comments + [JAVASCRIPT_TRANSLATION_COMMENT],
                            None,
                            value,
                        )
            except Exception:
                _logger.exception(
                    "Failed to extract terms from attachment with url %s",
                    attachment.url,
                )


def _domain_asks_for_industries(domain):
    for condition in Domain(domain).iter_conditions():
        if condition.field_expr == "module_type":
            if condition.operator == "=":
                if condition.value == "industries":
                    return True
            elif condition.operator == "in" and len(condition.value) == 1:
                if "industries" in condition.value:
                    return True
            else:
                raise UserError(f"Unsupported domain condition {condition!r}")  # pylint: disable=missing-gettext
    return False


def _is_studio_custom(path):
    """Check whether path's records reference Studio.

    :param str path: directory to scan for XML data files
    :return: whether any record's context carries a ``studio`` key
    :rtype: bool
    """
    xml_files = [
        dirpath / fn
        for dirpath, _dirs, files in Path(path).walk()
        for fn in files
        if fn.lower().endswith(".xml")
    ]

    for fp in xml_files:
        try:
            root = lxml.etree.parse(fp).getroot()
        except Exception:
            # t27114: this walk visits every .xml file extracted from the
            # zip, not just manifest-declared data files (e.g. anything
            # under static/), so a malformed/non-Odoo XML asset must not
            # abort the whole module's import — skip it like an
            # unparseable context below.
            _logger.debug("skipping unparseable XML file %s", fp)
            continue

        for record in root:
            # there might not be a context if it's a non-studio module
            try:
                # ast.literal_eval is like eval(), but safer
                # context is a string representing a python dict
                ctx = ast.literal_eval(record.get("context"))
                # there are no cases in which studio is false
                # so just checking for its existence is enough
                if ctx and ctx.get("studio"):
                    return True
            except Exception:
                _logger.debug("skipping record with unparseable context")
                continue
    return False
