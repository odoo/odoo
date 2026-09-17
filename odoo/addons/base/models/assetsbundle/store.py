from collections.abc import Callable
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from odoo import release
from odoo.api import SUPERUSER_ID, Environment
from odoo.fields import Domain
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
        _debug.lifecycle("tracked_bundle_registered", bundle=name)

    _ATTACHMENT_MIMETYPES = MappingProxyType(
        {
            "js": "text/javascript",
            "min.js": "text/javascript",
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

    def get_asset_url_pattern(self, extension: str, unique: str = ANY_UNIQUE) -> str:
        return self._asset_url(unique, extension, pattern=True)

    def _unique_for(self, extension: str) -> str:
        return self._version("css" if self.is_css(extension) else "js")

    def get_versioned_url(self, extension: str) -> str:
        return self.get_asset_url(self._unique_for(extension), extension)

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
        attachments.browse(deleted_ids).invalidate_recordset()
        if _debug.logic.enabled and len(deleted_ids) < len(attachments):
            _debug.logic(
                "attachments_skipped_locked",
                bundle=self.name,
                skipped=len(attachments) - len(deleted_ids),
            )
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

    def _clean_attachments(self, extension: str, keep_id: int) -> None:
        ira = self.env["ir.attachment"].sudo()
        to_clean_pattern = self.get_asset_url_pattern(extension)
        domain = ira._get_domain_generated_assets(
            url_pattern=to_clean_pattern
        ) & Domain("id", "!=", keep_id)

        attachments = ira.search(domain)
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
                keep_id,
            )
            self._unlink_attachments(attachments)

    def get_attachments(
        self, extension: str, ignore_version: bool = False
    ) -> IrAttachment:
        unique = ANY_UNIQUE if ignore_version else self._unique_for(extension)
        url_pattern = self.get_asset_url_pattern(extension, unique)
        _debug.logic(
            "attachment_lookup",
            bundle=self.name,
            extension=extension,
            versioned=not ignore_version,
        )
        ira = self.env["ir.attachment"].sudo()
        # parallel transactions can each store the same version; one row per name
        attachment_ids = [
            max_id
            for _name, max_id in ira._read_group(
                ira._get_domain_generated_assets(url_pattern=url_pattern),
                groupby=["name"],
                aggregates=["id:max"],
                order="name",
            )
        ]
        _debug.logic(
            "attachments_looked_up",
            bundle=self.name,
            extension=extension,
            ignore_version=ignore_version,
            found=len(attachment_ids),
        )
        return ira.browse(attachment_ids)

    def save_attachment(self, extension: str, content: str) -> IrAttachment:
        mimetype = self._ATTACHMENT_MIMETYPES.get(extension)
        if mimetype is None:
            _debug.logic(
                "attachment_save_rejected", bundle=self.name, extension=extension
            )
            raise ValueError(f"Invalid asset extension {extension!r}")
        ira = self.env["ir.attachment"]

        fname = f"{self.name}.{extension}"
        url = self.get_versioned_url(extension)
        values = self._attachment_values(
            name=fname, mimetype=mimetype, raw=content.encode("utf-8"), url=url
        )
        with _debug.perf(
            "attachment_create", cr=self.env.cr, bundle=self.name, extension=extension
        ):
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

        self._clean_attachments(extension, attachment.id)

        broadcast = "bus.bus" in self.env and self.name in self.TRACKED_BUNDLES
        if broadcast:
            self._broadcast_bundle_changed(self._unique_for(extension))
        if _debug.logic.enabled and not broadcast:
            _debug.logic(
                "bundle_changed_not_broadcast",
                bundle=self.name,
                tracked=self.name in self.TRACKED_BUNDLES,
                bus="bus.bus" in self.env,
            )

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
