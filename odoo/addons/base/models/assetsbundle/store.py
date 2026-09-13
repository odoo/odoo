from collections.abc import Callable
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from odoo import release
from odoo.api import SUPERUSER_ID, Environment
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL
from odoo.tools.assets.constants import ANY_UNIQUE

if TYPE_CHECKING:
    from odoo.addons.base.models.ir_attachment import IrAttachment
from .common import _logger

_debug = DebugLog(__name__)


class AssetAttachmentStore:
    TRACKED_BUNDLES = {"web.assets_web"}

    _CSS_EXTENSIONS = frozenset({"css", "min.css", "css.map"})

    @classmethod
    def register_tracked_bundle(cls, name: str) -> None:
        cls.TRACKED_BUNDLES.add(name)

    _ATTACHMENT_MIMETYPES = MappingProxyType(
        {
            "js": "application/javascript",
            "min.js": "application/javascript",
            "js.map": "application/json",
            "css": "text/css",
            "min.css": "text/css",
            "css.map": "application/json",
        }
    )

    def __init__(
        self,
        env: Environment,
        name: str,
        *,
        assets_params: dict[str, Any],
        rtl: bool,
        autoprefix: bool,
        version_provider: Callable[[str], str],
    ) -> None:
        self.env = env
        self.name = name
        self.assets_params = assets_params
        self.rtl = rtl
        self.autoprefix = autoprefix
        self._version = version_provider

    def is_css(self, extension: str) -> bool:
        return extension in self._CSS_EXTENSIONS

    def get_asset_url(self, unique: str, extension: str) -> str:
        return self._asset_url(unique, extension)

    def get_asset_url_pattern(
        self, unique: str = ANY_UNIQUE, extension: str = "%"
    ) -> str:
        return self._asset_url(unique, extension, pattern=True)

    def _asset_url(self, unique: str, extension: str, pattern: bool = False) -> str:
        direction = ".rtl" if self.is_css(extension) and self.rtl else ""
        autoprefixed = (
            ".autoprefixed" if self.is_css(extension) and self.autoprefix else ""
        )
        bundle_name = f"{self.name}{direction}{autoprefixed}.{extension}"
        builder = self.env["ir.asset"]
        build = (
            builder._get_asset_bundle_url_pattern
            if pattern
            else builder._get_asset_bundle_url
        )
        return build(bundle_name, unique, self.assets_params)

    def _attachment_values(
        self, *, name: str, mimetype: str, raw: bytes, url: str
    ) -> dict[str, Any]:
        return self.env["ir.attachment"]._prepare_generated_asset_vals(
            name=name, mimetype=mimetype, raw=raw, url=url
        )

    def _unlink_attachments(self, attachments: IrAttachment) -> None:
        fname_by_id = {
            attach.id: attach.store_fname
            for attach in attachments
            if attach.store_fname
        }
        table = SQL.identifier(attachments._table)
        self.env.cr.execute(
            SQL(
                """DELETE FROM %s WHERE id IN (
            SELECT id FROM %s WHERE id = ANY(%s) FOR NO KEY UPDATE SKIP LOCKED
        ) RETURNING id""",
                table,
                table,
                list(attachments.ids),
            )
        )
        deleted_ids = {row[0] for row in self.env.cr.fetchall()}
        to_delete = {
            fname
            for attach_id, fname in fname_by_id.items()
            if attach_id in deleted_ids
        }
        _debug.lifecycle(
            "attachments_unlinked",
            bundle=self.name,
            requested=len(attachments),
            deleted=len(deleted_ids),
            files=len(to_delete),
        )
        if to_delete:
            attachments._remove_stored_file_multi(to_delete)

    def _clean_attachments(self, extension: str, keep_url: str) -> None:
        ira = self.env["ir.attachment"]
        to_clean_pattern = self.get_asset_url_pattern(extension=extension)
        domain = [
            ("url", "=like", to_clean_pattern),
            ("url", "!=", keep_url),
            ("public", "=", True),
            ("res_model", "=", "ir.ui.view"),
            ("res_id", "=", 0),
            ("create_uid", "=", SUPERUSER_ID),
        ]

        attachments = ira.sudo().search(domain)
        _debug.logic(
            "stale_attachments",
            bundle=self.name,
            extension=extension,
            stale=len(attachments),
        )
        if attachments:
            _logger.info(
                "Deleting attachments %s (matching %s) because it was replaced with %s",
                attachments.ids,
                to_clean_pattern,
                keep_url,
            )
            self._unlink_attachments(attachments)

    def get_attachments(
        self, extension: str, ignore_version: bool = False
    ) -> IrAttachment:
        unique = (
            ANY_UNIQUE
            if ignore_version
            else self._version("css" if self.is_css(extension) else "js")
        )
        url_pattern = self.get_asset_url_pattern(unique=unique, extension=extension)
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
        self.env.cr.execute(SQL(query, SUPERUSER_ID, url_pattern))

        attachment_ids = [r[0] for r in self.env.cr.fetchall()]
        _debug.logic(
            "attachments_looked_up",
            bundle=self.name,
            extension=extension,
            ignore_version=ignore_version,
            found=len(attachment_ids),
        )
        return self.env["ir.attachment"].sudo().browse(attachment_ids)

    def save_attachment(self, extension: str, content: str) -> IrAttachment:
        mimetype = self._ATTACHMENT_MIMETYPES.get(extension)
        if mimetype is None:
            raise ValueError(f"Invalid asset extension {extension!r}")
        ira = self.env["ir.attachment"]

        fname = f"{self.name}.{extension}"
        unique = self._version("css" if self.is_css(extension) else "js")
        url = self.get_asset_url(
            unique=unique,
            extension=extension,
        )
        values = self._attachment_values(
            name=fname, mimetype=mimetype, raw=content.encode("utf-8"), url=url
        )
        attachment = ira.with_user(SUPERUSER_ID).create(values)

        _logger.info(
            "Generating a new asset bundle attachment %s (id:%s)",
            attachment.url,
            attachment.id,
        )
        _debug.lifecycle(
            "attachment_saved",
            bundle=self.name,
            extension=extension,
            attachment=attachment.id,
            bytes=len(content),
        )

        self._clean_attachments(extension, url)

        if "bus.bus" in self.env and self.name in self.TRACKED_BUNDLES:
            self._broadcast_bundle_changed(unique)

        return attachment

    _BROADCAST_KEY = "assetsbundle.bundle_changed"

    def _broadcast_bundle_changed(self, unique: str) -> None:
        sent = self.env.cr.precommit.data.setdefault(self._BROADCAST_KEY, set())
        if self.name in sent:
            _debug.logic("bundle_changed_already_sent", bundle=self.name)
            return
        sent.add(self.name)
        self.env["bus.bus"]._sendone(
            "broadcast",
            "bundle_changed",
            {"server_version": release.version},
        )
        _logger.debug("Asset Changed: bundle: %s -- version: %s", self.name, unique)
        _debug.lifecycle("bundle_changed_broadcast", bundle=self.name, unique=unique)
