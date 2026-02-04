import base64
import io
import json
import re
import zipfile

from odoo import Command, api, fields, models, release

from .website_transfer_utils import (
    ATTACHMENT_PAYLOAD_FIELDS,
    ASSET_PAYLOAD_FIELDS,
    CONTROLLER_PAGE_PAYLOAD_FIELDS,
    MENU_PAYLOAD_FIELDS,
    PAGE_PAYLOAD_FIELDS,
    VIEW_PAYLOAD_FIELDS,
    compute_payload_checksum,
    serialize_record,
)


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
    page_ids = fields.Many2many("website.page", string="Pages")
    include_assets = fields.Boolean(string="Include Assets", default=True)
    export_file = fields.Binary(string="Export File", readonly=True)
    export_filename = fields.Char(string="Export Filename", readonly=True)

    @api.onchange("page_scope", "website_id")
    def _onchange_page_ids(self):
        domain = self._get_page_domain()
        if self.page_scope == "all":
            self.page_ids = self.env["website.page"].search(domain)
        else:
            self.page_ids = [Command.clear()]

    def _get_pages_to_export(self):
        if self.page_scope == "all":
            return self.env["website.page"].search(self._get_page_domain())
        return self.page_ids

    def _get_controller_page_domain(self):
        website_id = self.website_id.id if self.website_id else False
        return [("website_id", "in", [website_id, False])]

    def _get_controller_pages_to_export(self):
        return self.env["website.controller.page"].search(self._get_controller_page_domain())

    def _get_website_settings_fields(self):
        return []

    def _get_extra_views_to_export(self, views):
        extra_views = self.env["ir.ui.view"].search([
            ("website_id", "=", self.website_id.id),
            ("type", "=", "qweb"),
        ])
        return extra_views - views

    def _collect_pages(self, pages):
        data = []
        for page in pages:
            data.append(serialize_record(page, PAGE_PAYLOAD_FIELDS))
        return data

    def _collect_views(self, views):
        data = []
        for view in views:
            values = serialize_record(view, VIEW_PAYLOAD_FIELDS)
            values["inherit_key"] = view.inherit_id.key
            data.append(values)
        return data

    def _collect_controller_pages(self, controller_pages):
        data = []
        for controller_page in controller_pages:
            data.append(serialize_record(controller_page, CONTROLLER_PAGE_PAYLOAD_FIELDS))
        return data

    def _collect_assets(self):
        assets = self.env["ir.asset"].with_context(active_test=False).search([
            ("website_id", "=", self.website_id.id),
        ])
        data = []
        for asset in assets:
            data.append(serialize_record(asset, ASSET_PAYLOAD_FIELDS))
        return data

    def _collect_asset_attachments(self, assets):
        attachment_ids = set()
        for asset in assets:
            path = asset.get("path") if isinstance(asset, dict) else asset.path
            if path and path.startswith("/_custom/"):
                attachment = self.env["ir.attachment"].search([("url", "=", path)], limit=1)
                if attachment:
                    attachment_ids.add(attachment.id)
        if not attachment_ids:
            return []
        data = []
        for attachment in self.env["ir.attachment"].browse(sorted(attachment_ids)):
            data.append(serialize_record(attachment, ATTACHMENT_PAYLOAD_FIELDS))
        return data

    def _collect_website_settings(self):
        settings = {}
        for field_name in self._get_website_settings_fields():
            if field_name in self.website_id._fields:
                settings[field_name] = self.website_id[field_name]
        return settings

    def _collect_menus(self, pages):
        menus = self.env["website.menu"].search([
            "|",
            ("page_id", "in", pages.ids),
            "&",
            ("page_id", "=", False),
            ("website_id", "in", [self.website_id.id, False]),
        ])
        parents = menus.mapped("parent_id")
        while parents:
            new_parents = parents - menus
            if not new_parents:
                break
            menus |= new_parents
            parents = new_parents.mapped("parent_id")

        data = []
        for menu in menus:
            values = serialize_record(menu, MENU_PAYLOAD_FIELDS)
            data.append(values)
        return data

    def _extract_attachment_ids(self, arch):
        ids = set()
        if not arch:
            return ids

        for match in re.findall(r"/web/image/(\d+)(?:[-/]|\b)", arch):
            ids.add(int(match))
        for match in re.findall(r"/web/content/(\d+)(?:[-/?#]|\b)", arch):
            ids.add(int(match))
        for match in re.findall(r'data-attachment-id="(\d+)"', arch):
            ids.add(int(match))
        for match in re.findall(r'data-original-id="(\d+)"', arch):
            ids.add(int(match))
        return ids

    def _collect_attachments(self, views, menus=None):
        attachment_ids = set()
        for view in views:
            attachment_ids |= self._extract_attachment_ids(view.arch_db)
        if menus:
            for menu in menus:
                attachment_ids |= self._extract_attachment_ids(menu.get("mega_menu_content"))

        if not attachment_ids:
            return []

        attachments = self.env["ir.attachment"].browse(sorted(attachment_ids))
        data = []
        for attachment in attachments:
            data.append(serialize_record(attachment, ATTACHMENT_PAYLOAD_FIELDS))
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
        controller_pages = self._get_controller_pages_to_export()
        views = (
            pages.mapped("view_id")
            | controller_pages.mapped("view_id")
            | controller_pages.mapped("record_view_id")
        )
        views |= self._get_extra_views_to_export(views)
        assets = self._collect_assets()
        menus = self._collect_menus(pages)
        attachments = self._collect_attachments(views, menus) if self.include_assets else []
        if self.include_assets and assets:
            asset_attachments = self._collect_asset_attachments(assets)
            if asset_attachments:
                existing_ids = {item.get("id") for item in attachments}
                attachments.extend([item for item in asset_attachments if item.get("id") not in existing_ids])
        return {
            "website": {
                "id": self.website_id.id,
                "name": self.website_id.name,
                "homepage_url": self.website_id.homepage_url,
            },
            "website_settings": self._collect_website_settings(),
            "pages": self._collect_pages(pages),
            "controller_pages": self._collect_controller_pages(controller_pages),
            "views": self._collect_views(views),
            "assets": assets,
            "menus": menus,
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

        with io.BytesIO() as buffer:
            with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED, allowZip64=False) as archive:
                if attachments:
                    for item in attachments:
                        record = attachment_map.get(item["id"])
                        if not record or not record.datas:
                            item["file_path"] = False
                            continue
                        filename = f"{record.id}_{self._sanitize_filename(record.name)}"
                        file_path = f"attachments/{filename}"
                        archive.writestr(file_path, base64.b64decode(record.datas))
                        item["file_path"] = file_path

                payload_files = {
                    "website_settings.json": payload["website_settings"],
                    "pages.json": payload["pages"],
                    "controller_pages.json": payload["controller_pages"],
                    "views.json": payload["views"],
                    "assets.json": payload["assets"],
                    "menus.json": payload["menus"],
                    "attachments.json": attachments,
                }
                for filename, content in payload_files.items():
                    archive.writestr(filename, json.dumps(content, ensure_ascii=True, sort_keys=True))

                checksum = compute_payload_checksum(payload_files)
                manifest = self._build_manifest(payload, checksum)
                archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=True, sort_keys=True))

            return buffer.getvalue()

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
