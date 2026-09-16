import logging
from collections import defaultdict

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import frozendict

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class DocumentsAccessTracking(models.Model):
    _name = "document.access.tracking"
    _description = "Document Access Tracking"
    _log_access = False

    changes = fields.Json(
        string="Changes need to be tracked",
        required=True,
    )
    documents = fields.Json(
        string="Impacted Document Ids",
        required=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
    )

    @api.model
    def _create_access_tracking(self, changes_by_document_dict: dict) -> None:
        # Nothing changed -> nothing to track, and nothing for the cron to
        # drain. `action_update_access_rights` reaches here unconditionally, so
        # without this an update that changed nothing (the value was already the
        # one asked for, a propagation that matched no row, a dialog saved
        # untouched) still read `document.tracking_batch_size`, resolved the
        # cron and inserted an `ir_cron_trigger` row -- waking the cron to drain
        # an empty queue. `_trigger` does not de-duplicate, so a bulk sharing
        # pass queued one such row per call.
        if not changes_by_document_dict:
            _debug.logic("tracking_skipped", reason="no_changes")
            return
        documents_by_changes = defaultdict(list)
        for document_id, changes in changes_by_document_dict.items():
            documents_by_changes[frozendict(changes)].append(document_id)

        batch_size = int(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("document.tracking_batch_size", "500")
        )
        for changes, documents in documents_by_changes.items():
            self.sudo().create(
                [
                    {
                        "changes": changes,
                        "documents": documents[offset : offset + batch_size],
                        "user_id": self.env.user.id,
                    }
                    for offset in range(0, len(documents), batch_size)
                ]
            )

        _debug.pipeline(
            "tracking_queued",
            documents=len(changes_by_document_dict),
            shapes=len(documents_by_changes),
            batch_size=batch_size,
        )
        cron = self.env.ref(
            "document.ir_cron_documents_access_tracking", raise_if_not_found=False
        )
        if cron:
            cron.sudo()._trigger()

    @api.model
    def _cron_generate_tracking(self) -> None:
        Cron = self.env["ir.cron"]
        remaining = self.search_count([])
        _debug.pipeline("tracking_cron_start", queued=remaining)
        # Fetch the queue a page at a time. The previous shape ran one
        # `search` per row, so draining a queue of N cost N extra queries on
        # top of the N it had to do anyway.
        while batch := self.search([], limit=self._cron_batch_size()):
            for tracking in batch:
                try:
                    with self.env.cr.savepoint():
                        tracking._create_message_track()
                except Exception:
                    _debug.logic("tracking_dropped", tracking=tracking.id)
                    _logger.warning(
                        "Documents: dropping unrenderable access tracking %s",
                        tracking.id,
                        exc_info=True,
                    )
                tracking.unlink()
                remaining = max(remaining - 1, 0)
                if Cron._commit_progress(processed=1, remaining=remaining) <= 0:
                    return
        Cron._commit_progress(remaining=0)

    @api.model
    def _cron_batch_size(self) -> int:
        return 100

    def _create_message_track(self) -> None:
        self.check_singleton()
        document_ids = self.env["document.document"].browse(self.documents)
        if initial_values := self._get_initial_values():
            _debug.logic("tracking_rendered", by="field_track", documents=document_ids)
            if "members" in self.changes:
                self._add_pre_commit_members_data()
            document_ids.with_user(self.user_id)._message_track(
                [
                    "access_internal",
                    "access_via_link",
                    "is_access_via_link_hidden",
                ],
                initial_values,
            )
        else:
            _debug.logic("tracking_rendered", by="members_body", documents=document_ids)
            body = self._get_members_change_template_body()
            document_ids.with_user(self.user_id)._message_log_batch(
                bodies=dict.fromkeys(document_ids.ids, body)
            )

    def _get_initial_values(self) -> dict:
        self.check_singleton()
        fields_list = [
            "access_internal",
            "access_via_link",
            "is_access_via_link_hidden",
        ]
        common_values = {
            field: self.changes[field] for field in fields_list if field in self.changes
        }
        return {doc_id: common_values for doc_id in self.documents if common_values}

    def _add_pre_commit_members_data(self) -> None:
        self.check_singleton()
        common_body = self._get_members_change_template_body()
        self.env.cr.precommit.data.setdefault(
            "mail.tracking.message.document.document",
            dict.fromkeys(self.documents, common_body),
        )

    def _get_members_change_template_body(self) -> str:
        self.check_singleton()
        members = self.changes["members"]
        partner_map = self._get_partners_mapping()
        return self.env["ir.qweb"]._render(
            "document.tracking_access_members_change",
            {
                "created_access": {
                    key: value
                    for key, value in members["added"].items()
                    if key in partner_map
                },
                "updated_access": {
                    key: value
                    for key, value in members["updated"].items()
                    if key in partner_map
                },
                "removed_access": [
                    key for key in members["removed"] if key in partner_map
                ],
                "partner_map": partner_map,
            },
            lang=self.user_id.lang,
            minimal_qcontext=True,
        )

    def _get_partners_mapping(self) -> dict:
        self.check_singleton()
        members_dict = self.changes["members"]
        keys = [
            *members_dict["added"],
            *members_dict["updated"],
            *members_dict["removed"],
        ]
        partners_by_id = (
            self.env["res.partner"].browse(int(key) for key in keys).exists()
        ).grouped("id")
        return {
            key: partner
            for key in keys
            if (partner := partners_by_id.get(int(key))) is not None
        }
