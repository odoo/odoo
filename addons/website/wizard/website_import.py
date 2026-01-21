# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import json
import re
import zipfile
from hashlib import sha256

from odoo import _, api, fields, models, release
from odoo.exceptions import UserError
from odoo.tools.urls import urljoin as url_join


class WebsiteImportWizard(models.TransientModel):
    _name = "website.import.wizard"
    _description = "Website Import Wizard"

    import_file = fields.Binary(string="Import File", required=True)
    import_filename = fields.Char(string="Import Filename")
    website_name = fields.Char(string="New Website Name", required=True)
    website_domain = fields.Char(string="Website Domain")
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
        except Exception as exc:
            raise UserError(_("The uploaded file could not be decoded.")) from exc
        try:
            return zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as exc:
            raise UserError(_("The uploaded file is not a valid zip archive.")) from exc

    def _read_archive_json(self, archive, filename):
        try:
            content = archive.read(filename)
        except KeyError as exc:
            raise UserError(_("Missing required file: %s") % filename) from exc
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise UserError(_("Invalid JSON in %s") % filename) from exc

    def _validate_manifest(self, manifest):
        version = manifest.get("odoo_version")
        if version != release.version:
            raise UserError(_(
                "Version mismatch: expected %s, got %s."
            ) % (release.version, version))

        modules = manifest.get("modules")
        if not isinstance(modules, list):
            raise UserError(_("Invalid manifest modules list."))

        installed = set(self.env["ir.module.module"].search([
            ("state", "=", "installed"),
            ("name", "in", modules),
        ]).mapped("name"))
        missing = sorted(set(modules) - installed)
        if missing:
            raise UserError(_("Missing required modules: %s") % ", ".join(missing))

        if not manifest.get("payload_checksum"):
            raise UserError(_("Missing payload checksum in manifest."))

    def _validate_payload_checksum(self, manifest, payload_files):
        checksum_source = json.dumps(payload_files, ensure_ascii=True, sort_keys=True).encode()
        checksum = sha256(checksum_source).hexdigest()
        if checksum != manifest.get("payload_checksum"):
            raise UserError(_("Payload checksum mismatch."))

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
            except KeyError as exc:
                raise UserError(_("Missing attachment file: %s") % file_path) from exc
            checksum = item.get("checksum")
            if not checksum:
                raise UserError(_("Missing attachment checksum for: %s") % file_path)
            if attachment_model._compute_checksum(content) != checksum:
                raise UserError(_("Attachment checksum mismatch: %s") % file_path)

    def _validate_target_website(self, website):
        extra_page = self.env["website.page"].search([
            ("website_id", "=", website.id),
            ("url", "!=", "/"),
        ], limit=1)
        if extra_page:
            raise UserError(_("Target website must be empty before import."))

    def _prepare_target_website(self, website):
        self.env["website.menu"].search([
            ("website_id", "=", website.id),
        ]).unlink()
        self.env["website.page"].search([
            ("website_id", "=", website.id),
        ]).unlink()

    def _import_views(self, views, website):
        view_model = self.env["ir.ui.view"]
        pending = {view["id"]: view for view in views}
        view_map = {}
        while pending:
            progress = False
            for view_id, view in list(pending.items()):
                inherit_id = view.get("inherit_id")
                if inherit_id and inherit_id in pending:
                    continue
                new_inherit_id = view_map.get(inherit_id, inherit_id or False)
                values = {
                    "name": view.get("name"),
                    "key": view.get("key"),
                    "type": view.get("type"),
                    "arch_db": view.get("arch_db"),
                    "inherit_id": new_inherit_id,
                    "website_id": website.id,
                    "active": view.get("active"),
                    "track": view.get("track"),
                    "visibility": view.get("visibility"),
                    "visibility_password": view.get("visibility_password"),
                    "group_ids": [(6, 0, view.get("group_ids", []))],
                    "website_meta_title": view.get("website_meta_title"),
                    "website_meta_description": view.get("website_meta_description"),
                    "website_meta_keywords": view.get("website_meta_keywords"),
                    "website_meta_og_img": view.get("website_meta_og_img"),
                    "seo_name": view.get("seo_name"),
                }
                new_view = view_model.create(values)
                view_map[view_id] = new_view.id
                pending.pop(view_id)
                progress = True
            if not progress:
                raise UserError(_("Failed to resolve view inheritance during import."))
        return view_map

    def _select_pages(self, pages, preferred_website_id):
        pages_by_url = {}
        for page in pages:
            url = page.get("url")
            existing = pages_by_url.get(url)
            if not existing:
                pages_by_url[url] = page
                continue
            existing_is_preferred = existing.get("website_id") == preferred_website_id
            page_is_preferred = page.get("website_id") == preferred_website_id
            if page_is_preferred and not existing_is_preferred:
                pages_by_url[url] = page
        return pages_by_url

    def _import_pages(self, pages, view_map, preferred_website_id):
        page_model = self.env["website.page"]
        pages_by_url = self._select_pages(pages, preferred_website_id)
        created_by_url = {}
        page_map = {}
        for page in pages_by_url.values():
            new_view_id = view_map.get(page.get("view_id"))
            if not new_view_id:
                raise UserError(_("Missing view mapping for page %s.") % page.get("name"))
            values = {
                "view_id": new_view_id,
                "url": page.get("url"),
                "is_published": page.get("is_published"),
                "publish_on": page.get("publish_on"),
                "website_indexed": page.get("website_indexed"),
                "is_new_page_template": page.get("is_new_page_template"),
                "header_visible": page.get("header_visible"),
                "footer_visible": page.get("footer_visible"),
                "breadcrumb_visible": page.get("breadcrumb_visible"),
                "header_overlay": page.get("header_overlay"),
                "header_color": page.get("header_color"),
                "header_text_color": page.get("header_text_color"),
                "breadcrumb_overlay": page.get("breadcrumb_overlay"),
                "breadcrumb_color": page.get("breadcrumb_color"),
                "breadcrumb_text_color": page.get("breadcrumb_text_color"),
            }
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

    def _select_menus(self, menus, preferred_website_id):
        preferred = [menu for menu in menus if menu.get("website_id") == preferred_website_id]
        if preferred:
            return preferred
        fallback = [menu for menu in menus if not menu.get("website_id")]
        return fallback or menus

    def _import_menus(self, menus, website, page_map, preferred_website_id):
        menu_model = self.env["website.menu"]
        menus = self._select_menus(menus, preferred_website_id)
        menu_map = {}
        pending = {menu["id"]: menu for menu in menus}
        while pending:
            progress = False
            for menu_id, menu in list(pending.items()):
                parent_id = menu.get("parent_id")
                if parent_id and parent_id not in menu_map:
                    continue
                values = {
                    "name": menu.get("name"),
                    "url": menu.get("url"),
                    "page_id": page_map.get(menu.get("page_id")) or False,
                    "parent_id": menu_map.get(parent_id) or False,
                    "website_id": website.id,
                    "sequence": menu.get("sequence"),
                    "new_window": menu.get("new_window"),
                    "is_mega_menu": menu.get("is_mega_menu"),
                    "mega_menu_content": menu.get("mega_menu_content"),
                    "mega_menu_classes": menu.get("mega_menu_classes"),
                    "group_ids": [(6, 0, menu.get("group_ids", []))],
                }
                new_menu = menu_model.create(values)
                menu_map[menu_id] = new_menu.id
                pending.pop(menu_id)
                progress = True
            if not progress:
                raise UserError(_("Failed to resolve menu hierarchy during import."))
        return menu_map

    def _replace_attachment_ids(self, arch, attachment_map):
        if not arch:
            return arch
        def replace_web_image(match):
            old_id = int(match.group(1))
            new_id = attachment_map.get(old_id, old_id)
            return match.group(0).replace(match.group(1), str(new_id), 1)

        arch = re.sub(r"/web/image/(\d+)(?:[-/]|\b)", replace_web_image, arch)
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

    def _import_attachments(self, archive, attachments, website, view_map, page_map):
        attachment_model = self.env["ir.attachment"]
        attachment_map = {}
        for item in attachments:
            file_path = item.get("file_path")
            datas = False
            if file_path:
                content = archive.read(file_path)
                datas = base64.b64encode(content)
            res_model = item.get("res_model")
            res_id = item.get("res_id")
            if res_model == "ir.ui.view":
                res_id = view_map.get(res_id)
            elif res_model == "website.page":
                res_id = page_map.get(res_id)
            values = {
                "name": item.get("name"),
                "mimetype": item.get("mimetype"),
                "type": item.get("type"),
                "url": item.get("url"),
                "public": item.get("public"),
                "res_model": res_model,
                "res_id": res_id or False,
                "website_id": website.id,
                "datas": datas or False,
            }
            attachment = attachment_model.create(values)
            attachment_map[item["id"]] = attachment.id
        if attachment_map:
            views = self.env["ir.ui.view"].browse(view_map.values())
            for view in views:
                new_arch = self._replace_attachment_ids(view.arch_db, attachment_map)
                if new_arch != view.arch_db:
                    view.arch_db = new_arch
        return attachment_map

    def action_import(self):
        self.ensure_one()
        with self._open_import_archive() as archive:
            manifest = self._read_archive_json(archive, "manifest.json")
            website_payload = self._read_archive_json(archive, "website.json")
            pages_payload = self._read_archive_json(archive, "pages.json")
            views_payload = self._read_archive_json(archive, "views.json")
            menus_payload = self._read_archive_json(archive, "menus.json")
            attachments = self._read_archive_json(archive, "attachments.json")
            self._validate_manifest(manifest)
            self._validate_payload_checksum(manifest, {
                "website.json": website_payload,
                "pages.json": pages_payload,
                "views.json": views_payload,
                "menus.json": menus_payload,
                "attachments.json": attachments,
            })
            self._validate_attachments(archive, attachments)

            website = self.env["website"].create({
                "name": self.website_name,
                "domain": self.website_domain or False,
                "company_id": self.company_id.id,
            })
            self._validate_target_website(website)
            self._prepare_target_website(website)
            view_map = self._import_views(views_payload, website)
            page_map = self._import_pages(pages_payload, view_map, manifest["website"]["id"])
            self._import_menus(menus_payload, website, page_map, manifest["website"]["id"])
            self._import_attachments(archive, attachments, website, view_map, page_map)

        return {
            "type": "ir.actions.act_url",
            "url": url_join(
                website.get_base_url(),
                f"/website/force/{website.id}?path=/",
            ),
            "target": "self",
            # TODO DUAU: could not show success notification after redirect
        }
