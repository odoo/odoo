import base64
import io
import json
import re
import zipfile

from odoo import _, api, fields, models, release
from odoo.exceptions import UserError
from odoo.tools.urls import urljoin as url_join

from .website_transfer_utils import (
    ATTACHMENT_PAYLOAD_FIELDS,
    ASSET_PAYLOAD_FIELDS,
    CONTROLLER_PAGE_PAYLOAD_FIELDS,
    MENU_PAYLOAD_FIELDS,
    PAGE_PAYLOAD_FIELDS,
    VIEW_PAYLOAD_FIELDS,
    compute_payload_checksum,
    extract_payload_values,
)

MAX_IMPORT_FILE_SIZE = 100 * 1024 * 1024
MAX_IMPORT_TOTAL_SIZE = 200 * 1024 * 1024
MAX_IMPORT_FILES = 2000

HEADER_TEMPLATE_KEYS = (
    "website.template_header_default",
    "website.template_header_hamburger",
    "website.template_header_boxed",
    "website.template_header_stretch",
    "website.template_header_vertical",
    "website.template_header_search",
    "website.template_header_sales_one",
    "website.template_header_sales_two",
    "website.template_header_sales_three",
    "website.template_header_sales_four",
    "website.template_header_sidebar",
)


class WebsiteImportWizard(models.TransientModel):
    _name = "website.import.wizard"
    _description = "Website Import Wizard"

    import_file = fields.Binary(string="Import File", required=True)
    import_filename = fields.Char(string="Import Filename")
    website_name = fields.Char(string="New Website Name", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )

    @api.onchange("import_file")
    def _onchange_import_file(self):
        if not self.import_file:
            return
        try:
            with self._open_import_archive() as archive:
                manifest = self._read_archive_json(archive, "manifest.json")
                website = manifest.get("website", {})
                if website.get("name"):
                    self.website_name = website["name"]
        except UserError:
            return

    def _open_import_archive(self):
        if not self.import_file:
            raise UserError(_("Please upload an export file."))
        try:
            data = base64.b64decode(self.import_file)
        except Exception as e:
            raise UserError(_("The uploaded file could not be decoded.")) from e
        try:
            archive = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as e:
            raise UserError(_("The uploaded file is not a valid zip archive.")) from e
        self._validate_archive(archive)
        return archive

    def _validate_archive(self, archive):
        entries = archive.infolist()
        if len(entries) > MAX_IMPORT_FILES:
            raise UserError(_("Import archive contains too many files."))
        total_size = 0
        for entry in entries:
            if entry.file_size > MAX_IMPORT_FILE_SIZE:
                raise UserError(_("File '%s' exceeds maximum allowed size.", entry.filename))
            total_size += entry.file_size
            if total_size > MAX_IMPORT_TOTAL_SIZE:
                raise UserError(_("Import archive exceeds maximum allowed size."))

    def _read_archive_json(self, archive, filename):
        try:
            content = archive.read(filename)
        except KeyError as e:
            raise UserError(_("Missing required file: %s", filename)) from e
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise UserError(_("Invalid JSON in %s", filename)) from e

    def _validate_manifest(self, manifest):
        version = manifest.get("odoo_version")
        if version != release.version:
            raise UserError(_(
                "Version mismatch: expected %(odoo_version)s, got %(archive_version)s.",
                odoo_version=release.version,
                archive_version=version,
            ))
            # TODO DUAU: do we add a dialog: "Do you want to continue? You may experience some errors etc"

        modules = manifest.get("modules", [])

        installed = set(self.env["ir.module.module"].search([
            ("state", "=", "installed"),
            ("name", "in", modules),
        ]).mapped("name"))
        missing_modules = sorted(set(modules) - installed)
        if missing_modules:
            raise UserError(_("Missing required modules: %s", ", ".join(missing_modules)))

    def _validate_payload_checksum(self, manifest, payload_files):
        manifest_checksum = manifest.get("payload_checksum")
        checksum = compute_payload_checksum(payload_files)
        if not manifest_checksum or checksum != manifest_checksum:
            raise UserError(_("Invalid payload checksum."))

    def _validate_attachments(self, archive, attachments):
        if not attachments:
            return
        attachment_model = self.env["ir.attachment"]
        for item in attachments:
            file_path = item.get("file_path")
            if not file_path:
                continue
            try:
                content = archive.read(file_path)
            except KeyError as e:
                raise UserError(_("Missing attachment file: %s", file_path)) from e
            checksum = item.get("checksum")
            if not checksum or attachment_model._compute_checksum(content) != checksum:
                raise UserError(_("Invalid attachment checksum: %s", file_path))

    def _prepare_target_website(self, website):
        # Clear homepage/menu created at website creation in _bootstrap_homepage()
        self.env["website.menu"].search([
            ("website_id", "=", website.id),
        ]).unlink()
        self.env["website.page"].search([
            ("website_id", "=", website.id),
        ]).unlink()

    def _get_website_settings_fields(self):
        return []

    def _apply_header_template_selection(self, website, views_payload):
        active_keys = {
            view.get("key")
            for view in views_payload
            if view.get("active") and view.get("key") in HEADER_TEMPLATE_KEYS
        }
        if not active_keys:
            return
        view_model = self.env["ir.ui.view"].with_context(active_test=False)
        for key in HEADER_TEMPLATE_KEYS:
            website_view = view_model.search([
                ("key", "=", key),
                ("website_id", "=", website.id),
            ], limit=1)
            if key in active_keys:
                if website_view:
                    if not website_view.active:
                        website_view.write({"active": True})
                    continue
                generic_view = view_model.search([
                    ("key", "=", key),
                    ("website_id", "=", False),
                ], limit=1)
                if generic_view:
                    generic_view.copy({
                        "website_id": website.id,
                        "key": key,
                        "active": True,
                    })
                continue
            if website_view:
                if website_view.active:
                    website_view.write({"active": False})
                continue
            generic_view = view_model.search([
                ("key", "=", key),
                ("website_id", "=", False),
            ], limit=1)
            if generic_view:
                generic_view.copy({
                    "website_id": website.id,
                    "key": key,
                    "active": False,
                })

    def _import_views(self, views, website):
        view_model = self.env["ir.ui.view"]
        pending = {view["id"]: view for view in views}
        view_map = {}
        while pending:
            progress = False
            for view_id, view in list(pending.items()):
                inherit_id = view.get("inherit_id")
                inherit_key = view.get("inherit_key")

                if inherit_id and inherit_id in pending:
                    continue
                new_inherit_id = view_map.get(inherit_id)

                if not new_inherit_id and inherit_key:
                    inherit_view = self.env["website"].with_context(
                        website_id=website.id,
                    ).viewref(inherit_key)
                    new_inherit_id = inherit_view.id
                elif inherit_id and inherit_id not in view_map:
                    raise UserError(_("Missing inherited view mapping for: %s", view.get("name")))

                values = extract_payload_values(
                    view,
                    VIEW_PAYLOAD_FIELDS,
                    skip=("inherit_id", "website_id"),
                )
                values.update({
                    "inherit_id": new_inherit_id,
                    "website_id": website.id,
                })

                new_view = view_model.create(values)
                view_map[view_id] = new_view.id
                pending.pop(view_id)
                progress = True
            if not progress:
                raise UserError(_("Failed to resolve view inheritance during import."))
        return view_map

    def _select_pages(self, pages, source_website_id):
        pages_by_url = {}
        for page in pages:
            url = page.get("url")
            existing = pages_by_url.get(url)
            if not existing:
                pages_by_url[url] = page
                continue
            if page.get("website_id") == source_website_id and existing.get("website_id") != source_website_id:
                pages_by_url[url] = page
        return pages_by_url

    def _import_pages(self, pages, view_map, source_website_id):
        page_model = self.env["website.page"]
        pages_by_url = self._select_pages(pages, source_website_id)
        created_by_url = {}
        page_map = {}
        for page in pages_by_url.values():
            new_view_id = view_map.get(page.get("view_id"))
            if not new_view_id:
                raise UserError(_("Missing view mapping for page %s.", page.get("name")))
            values = extract_payload_values(
                page,
                PAGE_PAYLOAD_FIELDS,
                skip=("parent_id", "view_id", "website_id"),
            )
            values["view_id"] = new_view_id
            new_page = page_model.create(values)
            created_by_url[page.get("url")] = new_page.id
        for page in pages:
            page_map[page["id"]] = created_by_url.get(page.get("url"))
        for page in pages_by_url.values():
            if page.get("parent_id"):
                new_parent = page_map.get(page["parent_id"])
                if new_parent:
                    page_model.browse(created_by_url.get(page.get("url"))).parent_id = new_parent
        return page_map

    def _import_controller_pages(self, controller_pages, view_map):
        controller_page_model = self.env["website.controller.page"]
        controller_page_map = {}
        for controller_page in controller_pages:
            new_view_id = view_map.get(controller_page.get("view_id"))
            if not new_view_id:
                raise UserError(_("Missing view mapping for controller page %s.", controller_page.get("name_slugified")))
            record_view_id = controller_page.get("record_view_id")
            new_record_view_id = False
            if record_view_id:
                new_record_view_id = view_map.get(record_view_id)
                if not new_record_view_id:
                    raise UserError(_("Missing record view mapping for controller page %s.", controller_page.get("name_slugified")))
            values = extract_payload_values(
                controller_page,
                CONTROLLER_PAGE_PAYLOAD_FIELDS,
                skip=("view_id", "record_view_id"),
            )
            values.update({
                "view_id": new_view_id,
                "record_view_id": new_record_view_id,
            })
            new_controller_page = controller_page_model.create(values)
            controller_page_map[controller_page["id"]] = new_controller_page.id
        return controller_page_map

    def _select_menus(self, menus, source_website_id):
        preferred = [menu for menu in menus if menu.get("website_id") == source_website_id]
        if preferred:
            return preferred
        fallback = [menu for menu in menus if not menu.get("website_id")]
        return fallback or menus

    def _import_menus(self, menus, website, page_map, controller_page_map, source_website_id):
        menu_model = self.env["website.menu"]
        menus = self._select_menus(menus, source_website_id)
        menu_map = {}
        pending = {menu["id"]: menu for menu in menus}
        while pending:
            progress = False
            for menu_id, menu in list(pending.items()):
                parent_id = menu.get("parent_id")
                if parent_id and parent_id not in menu_map:
                    continue
                values = extract_payload_values(
                    menu,
                    MENU_PAYLOAD_FIELDS,
                    skip=("page_id", "parent_id", "website_id"),
                )
                values.update({
                    "page_id": page_map.get(menu.get("page_id"), False),
                    "controller_page_id": controller_page_map.get(menu.get("controller_page_id"), False),
                    "parent_id": menu_map.get(parent_id, False),
                    "website_id": website.id,
                })
                new_menu = menu_model.create(values)
                menu_map[menu_id] = new_menu.id
                pending.pop(menu_id)
                progress = True
            if not progress:
                raise UserError(_("Failed to resolve menu hierarchy during import."))
        created_menus = menu_model.browse(menu_map.values())
        top_menus = created_menus.filtered(lambda menu: not menu.parent_id)
        if len(top_menus) > 1:
            root_menu = top_menus.filtered(
                lambda menu: not menu.page_id and (menu.url in ("#", False))
            )[:1] or top_menus[:1]
            (top_menus - root_menu).write({"parent_id": root_menu.id})
        return menu_map

    def _replace_attachment_ids(self, arch, attachment_map):
        if not arch:
            return arch

        def replace_web_image(match):
            old_id = int(match.group(1))
            new_id = attachment_map.get(old_id, old_id)
            return match.group(0).replace(match.group(1), str(new_id), 1)

        arch = re.sub(r"/web/image/(\d+)(?:[-/]|\b)", replace_web_image, arch)
        arch = re.sub(r"/web/content/(\d+)(?:[-/?#]|\b)", replace_web_image, arch)
        arch = re.sub(
            r'data-attachment-id="(\d+)"',
            lambda m: f'data-attachment-id="{attachment_map.get(int(m.group(1)), int(m.group(1)))}"',
            arch,
        )
        arch = re.sub(
            r'data-original-id="(\d+)"',
            lambda m: f'data-original-id="{attachment_map.get(int(m.group(1)), int(m.group(1)))}"',
            arch,
        )
        return arch

    def _import_attachments(self, archive, attachments, website, view_map, page_map, controller_page_map, menu_map):
        attachment_model = self.env["ir.attachment"]
        attachment_map = {}
        dedupe_map = {}
        for item in attachments:
            file_path = item.get("file_path")
            datas = False
            if file_path:
                content = archive.read(file_path)
                datas = base64.b64encode(content)
            checksum = item.get("checksum")
            name = item.get("name")
            if checksum and name:
                dedupe_key = (checksum, name)
                existing_id = dedupe_map.get(dedupe_key)
                if existing_id:
                    attachment_map[item["id"]] = existing_id
                    continue
            res_model = item.get("res_model")
            res_id = item.get("res_id")
            if res_model == "ir.ui.view":
                res_id = view_map.get(res_id)
            elif res_model == "website.page":
                res_id = page_map.get(res_id)
            elif res_model == "website.controller.page":
                res_id = controller_page_map.get(res_id)
            elif res_model == "website.menu":
                res_id = menu_map.get(res_id)
            values = extract_payload_values(
                item,
                ATTACHMENT_PAYLOAD_FIELDS,
                skip=("res_id", "website_id"),
            )
            values.update({
                "res_model": res_model,
                "res_id": res_id or False,
                "website_id": website.id,
                "datas": datas or False,
            })
            attachment = attachment_model.create(values)
            attachment_map[item["id"]] = attachment.id
            if checksum and name:
                dedupe_map[dedupe_key] = attachment.id
        if attachment_map:
            views = self.env["ir.ui.view"].browse(view_map.values())
            for view in views:
                new_arch = self._replace_attachment_ids(view.arch_db, attachment_map)
                if new_arch != view.arch_db:
                    view.arch_db = new_arch
            menus = self.env["website.menu"].browse(menu_map.values())
            for menu in menus:
                new_content = self._replace_attachment_ids(menu.mega_menu_content, attachment_map)
                if new_content != menu.mega_menu_content:
                    menu.mega_menu_content = new_content
        return attachment_map

    def _import_assets(self, assets, website):
        if not assets:
            return
        asset_model = self.env["ir.asset"].with_context(active_test=False)
        for asset in assets:
            values = extract_payload_values(
                asset,
                ASSET_PAYLOAD_FIELDS,
                skip=("website_id",),
            )
            values["website_id"] = website.id
            asset_model.create(values)

    def _finalize_import(self):
        self.env.registry.clear_cache('templates')
        self.env.registry.clear_cache('routing')

    def _build_import_summary(self, website, view_map, page_map, menu_map, attachment_map):
        return {
            "website_id": website.id,
            "website_name": website.name,
            "views": len(view_map),
            "pages": len(page_map),
            "menus": len(menu_map),
            "attachments": len(attachment_map),
        }

    def action_import(self):
        self.ensure_one()
        with self._open_import_archive() as archive:
            manifest = self._read_archive_json(archive, "manifest.json")
            archive_files = set(archive.namelist())
            website_settings_payload = {}
            if "website_settings.json" in archive_files:
                website_settings_payload = self._read_archive_json(archive, "website_settings.json")
            pages_payload = self._read_archive_json(archive, "pages.json")
            controller_pages_payload = []
            if "controller_pages.json" in archive_files:
                controller_pages_payload = self._read_archive_json(archive, "controller_pages.json")
            views_payload = self._read_archive_json(archive, "views.json")
            assets_payload = []
            if "assets.json" in archive_files:
                assets_payload = self._read_archive_json(archive, "assets.json")
            menus_payload = self._read_archive_json(archive, "menus.json")
            attachments = self._read_archive_json(archive, "attachments.json")
            self._validate_manifest(manifest)
            payload_files = {
                "pages.json": pages_payload,
                "views.json": views_payload,
                "menus.json": menus_payload,
                "attachments.json": attachments,
            }
            if "website_settings.json" in archive_files:
                payload_files["website_settings.json"] = website_settings_payload
            if "controller_pages.json" in archive_files:
                payload_files["controller_pages.json"] = controller_pages_payload
            if "assets.json" in archive_files:
                payload_files["assets.json"] = assets_payload
            self._validate_payload_checksum(manifest, payload_files)
            self._validate_attachments(archive, attachments)

            manifest_website = manifest.get("website", {})
            existing = self.env["website"].search([
                ("name", "=", self.website_name),
                ("company_id", "=", self.company_id.id),
            ], limit=1)
            if existing:
                raise UserError(_("Website '%s' already exists.", self.website_name))
            website_values = {
                "name": self.website_name,
                "company_id": self.company_id.id,
            }
            if "homepage_url" in manifest_website:
                website_values["homepage_url"] = manifest_website.get("homepage_url", False)
            website = self.env["website"].create(website_values)
            if website_settings_payload:
                settings = {
                    field_name: website_settings_payload.get(field_name)
                    for field_name in self._get_website_settings_fields()
                    if field_name in website._fields and field_name in website_settings_payload
                }
                if settings:
                    website.write(settings)
            self._prepare_target_website(website)
            view_map = self._import_views(views_payload, website)
            self._apply_header_template_selection(website, views_payload)
            page_map = self._import_pages(pages_payload, view_map, manifest_website.get("id"))
            controller_page_map = self._import_controller_pages(controller_pages_payload, view_map)
            menu_map = self._import_menus(
                menus_payload,
                website,
                page_map,
                controller_page_map,
                manifest_website.get("id"),
            )
            attachment_map = self._import_attachments(
                archive,
                attachments,
                website,
                view_map,
                page_map,
                controller_page_map,
                menu_map,
            )
            self._import_assets(assets_payload, website)
            self._finalize_import()
            summary = self._build_import_summary(website, view_map, page_map, menu_map, attachment_map)
            summary_wizard = self.env["website.import.summary.wizard"].create({
                "website_id": website.id,
                "website_name": summary["website_name"],
                "pages_count": summary["pages"],
                "menus_count": summary["menus"],
                "attachments_count": summary["attachments"],
            })

        return {
            "type": "ir.actions.act_window",
            "res_model": "website.import.summary.wizard",
            "view_mode": "form",
            "view_id": self.env.ref("website.view_website_import_summary_wizard").id,
            "res_id": summary_wizard.id,
            "target": "new",
        }


class WebsiteImportSummaryWizard(models.TransientModel):
    _name = "website.import.summary.wizard"
    _description = "Website Import Summary"

    website_id = fields.Many2one("website", string="Website", readonly=True)
    website_name = fields.Char(string="Website Name", readonly=True)
    pages_count = fields.Integer(string="Pages", readonly=True)
    menus_count = fields.Integer(string="Menus", readonly=True)
    attachments_count = fields.Integer(string="Attachments", readonly=True)

    def action_go_homepage(self):
        self.ensure_one()
        website = self.website_id
        return {
            "type": "ir.actions.act_url",
            "url": url_join(
                website.get_base_url(),
                f"/website/force/{website.id}?path=/",
            ),
            "target": "self",
        }
