# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import json
import re
import zipfile
from hashlib import sha256

from odoo import api, fields, models, release


class WebsiteExportWizard(models.TransientModel):
    _name = "website.export.wizard"
    _description = "Website Export Wizard"


    def _get_page_domain(self):
        website_id = self.website_id.id if self.website_id else False
        return [
            ("website_id", "in", [website_id, False]),
            ("key", "not ilike", "%_debug_page_view%"),
        ]

    website_id = fields.Many2one(
        "website",
        string="Website",
        required=True,
        default=lambda self: self.env["website"].get_current_website(),
    )
    page_scope = fields.Selection(
        [
            ("all", "All Pages"),
            ("selection", "Selected Pages"),
        ],
        string="Pages to Export",
        required=True,
        default="all",
    )
    page_ids = fields.Many2many(
        "website.page",
        string="Pages",
        domain="[('website_id', 'in', [website_id, False]), ('key', 'not ilike', '%_debug_page_view%')]",
    )
    include_assets = fields.Boolean(string="Include Assets", default=True)
    export_file = fields.Binary(string="Export File", readonly=True)
    export_filename = fields.Char(string="Export Filename", readonly=True)

    @api.onchange("page_scope", "website_id")
    def _onchange_page_ids(self):
        if self.page_scope == "all":
            self.page_ids = self.env["website.page"].search(self._get_page_domain())
        else:
            self.page_ids = False

    def _get_pages_to_export(self):
        return self.page_ids

    def _collect_pages(self, pages):
        data = []
        for page in pages:
            data.append({
                "id": page.id,
                "name": page.name,
                "url": page.url,
                "website_id": page.website_id.id,
                "view_id": page.view_id.id,
                "is_published": page.is_published,
                "publish_on": page.publish_on,
                "website_indexed": page.website_indexed,
                "is_new_page_template": page.is_new_page_template,
                "parent_id": page.parent_id.id,
                "header_visible": page.header_visible,
                "footer_visible": page.footer_visible,
                "breadcrumb_visible": page.breadcrumb_visible,
                "header_overlay": page.header_overlay,
                "header_color": page.header_color,
                "header_text_color": page.header_text_color,
                "breadcrumb_overlay": page.breadcrumb_overlay,
                "breadcrumb_color": page.breadcrumb_color,
                "breadcrumb_text_color": page.breadcrumb_text_color,
            })
        return data

    def _collect_views(self, views):
        data = []
        for view in views:
            data.append({
                "id": view.id,
                "key": view.key,
                "name": view.name,
                "type": view.type,
                "arch_db": view.arch_db,
                "inherit_id": view.inherit_id.id,
                "website_id": view.website_id.id,
                "active": view.active,
                "track": view.track,
                "visibility": view.visibility,
                "visibility_password": view.visibility_password,
                "group_ids": view.group_ids.ids,
                "website_meta_title": view.website_meta_title,
                "website_meta_description": view.website_meta_description,
                "website_meta_keywords": view.website_meta_keywords,
                "website_meta_og_img": view.website_meta_og_img,
                "seo_name": view.seo_name,
            })
        return data

    def _collect_menus(self, pages):
        menus = self.env["website.menu"].search([("page_id", "in", pages.ids)])
        parents = menus.mapped("parent_id")
        while parents:
            new_parents = parents - menus
            if not new_parents:
                break
            menus |= new_parents
            parents = new_parents.mapped("parent_id")

        data = []
        for menu in menus:
            data.append({
                "id": menu.id,
                "name": menu.name,
                "url": menu.url,
                "page_id": menu.page_id.id,
                "parent_id": menu.parent_id.id,
                "website_id": menu.website_id.id,
                "sequence": menu.sequence,
                "new_window": menu.new_window,
                "is_mega_menu": menu.is_mega_menu,
                "mega_menu_content": menu.mega_menu_content,
                "mega_menu_classes": menu.mega_menu_classes,
                "group_ids": menu.group_ids.ids,
            })
        return data

    def _extract_attachment_ids(self, arch):
        ids = set()
        if not arch:
            return ids

        for match in re.findall(r"/web/image/(\d+)(?:[-/]|\\b)", arch):
            ids.add(int(match))
        for match in re.findall(r'data-attachment-id="(\d+)"', arch):
            ids.add(int(match))
        for match in re.findall(r'data-original-id="(\d+)"', arch):
            ids.add(int(match))
        return ids

    def _collect_attachments(self, views):
        attachment_ids = set()
        for view in views:
            attachment_ids |= self._extract_attachment_ids(view.arch_db)

        if not attachment_ids:
            return []

        attachments = self.env["ir.attachment"].browse(sorted(attachment_ids))
        data = []
        for attachment in attachments:
            data.append({
                "id": attachment.id,
                "name": attachment.name,
                "mimetype": attachment.mimetype,
                "checksum": attachment.checksum,
                "type": attachment.type,
                "url": attachment.url,
                "public": attachment.public,
                "res_model": attachment.res_model,
                "res_id": attachment.res_id,
                "website_id": attachment.website_id.id,
            })
        return data

    def _sanitize_filename(self, name):
        if not name:
            return "attachment"
        name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
        return name[:64] or "attachment"

    def _get_export_filename(self):
        safe_name = self._sanitize_filename(self.website_id.name) or "website"
        timestamp = fields.Datetime.to_string(fields.Datetime.now()).replace(" ", "_").replace(":", "")
        return f"website_export_{safe_name}_{timestamp}.zip"

    def _collect_export_data(self):
        self.ensure_one()
        pages = self._get_pages_to_export()
        views = pages.mapped("view_id")
        attachments = self._collect_attachments(views) if self.include_assets else []
        return {
            "website": {
                "id": self.website_id.id,
                "name": self.website_id.name,
            },
            "pages": self._collect_pages(pages),
            "views": self._collect_views(views),
            "menus": self._collect_menus(pages),
            "attachments": attachments,
        }

    def _build_manifest(self, payload, payload_checksum):
        modules = self.env["ir.module.module"].search([
            ("state", "=", "installed"),
            ("name", "=like", "website%"),
        ]).mapped("name")
        return {
            "odoo_version": release.version,
            "generated_at": fields.Datetime.to_string(fields.Datetime.now()),
            "website": payload["website"],
            "modules": sorted(modules),
            "page_ids": [page["id"] for page in payload["pages"]],
            "payload_checksum": payload_checksum,
        }

    def _write_export_zip(self, payload):
        attachments = payload["attachments"]
        attachment_map = {}
        if attachments:
            attachment_ids = [item["id"] for item in attachments if item.get("id")]
            attachment_map = {att.id: att for att in self.env["ir.attachment"].browse(attachment_ids)}

        with io.BytesIO() as buf:
            with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED, allowZip64=False) as zf:
                if attachments:
                    for item in attachments:
                        record = attachment_map.get(item["id"])
                        if not record or not record.datas:
                            item["file_path"] = False
                            continue
                        filename = f"{record.id}_{self._sanitize_filename(record.name)}"
                        file_path = f"attachments/{filename}"
                        zf.writestr(file_path, base64.b64decode(record.datas))
                        item["file_path"] = file_path

                payload_files = {
                    "website.json": payload["website"],
                    "pages.json": payload["pages"],
                    "views.json": payload["views"],
                    "menus.json": payload["menus"],
                    "attachments.json": attachments,
                }
                for filename, content in payload_files.items():
                    zf.writestr(filename, json.dumps(content, ensure_ascii=True, sort_keys=True))

                checksum_source = json.dumps(payload_files, ensure_ascii=True, sort_keys=True).encode()
                manifest = self._build_manifest(payload, sha256(checksum_source).hexdigest())
                zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=True, sort_keys=True))

            return buf.getvalue()

    def action_export(self):
        self.ensure_one()
        payload = self._collect_export_data()
        archive = self._write_export_zip(payload)
        self.export_filename = self._get_export_filename()
        self.export_file = base64.b64encode(archive)
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
        }
