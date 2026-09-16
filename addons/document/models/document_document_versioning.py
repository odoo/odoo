from odoo import _, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class DocumentsDocument(models.Model):
    _inherit = "document.document"

    def action_delete_from_history(self, attachment_id: int) -> None:
        self.check_singleton()
        self._check_access_or_raise(
            "write", _("You are not allowed to delete a version of this document.")
        )
        attachment = self.env["ir.attachment"].browse(attachment_id)

        if attachment not in self.previous_attachment_ids and (
            attachment != self.attachment_id or not self.previous_attachment_ids
        ):
            _debug.logic(
                "version_delete_refused", document=self, attachment=attachment_id
            )
            raise UserError(_("You cannot delete this attachment."))

        deleted_name = attachment.name
        _debug.lifecycle(
            "version_deleted",
            document=self,
            attachment=attachment_id,
            was_current=attachment == self.attachment_id,
        )
        if attachment == self.attachment_id:
            promoted = max(
                self.previous_attachment_ids, key=lambda a: (a.create_date, a.id)
            )
            self.attachment_id = promoted
            self.message_post(
                body=_(
                    "Version deleted: “%(deleted)s” removed, “%(promoted)s” is now "
                    "the current version.",
                    deleted=deleted_name,
                    promoted=promoted.name,
                )
            )
        else:
            self.message_post(
                body=_("Version deleted from the history: “%s”.", deleted_name)
            )

        attachment.unlink()

    def action_restore_version(self, attachment_id: int) -> None:
        self.check_singleton()
        self._check_access_or_raise(
            "write", _("You are not allowed to restore a version of this document.")
        )

        attachment = self.env["ir.attachment"].browse(attachment_id).exists()
        if attachment not in self.previous_attachment_ids:
            _debug.logic(
                "version_restore_refused", document=self, attachment=attachment_id
            )
            raise UserError(_("This version does not belong to this document."))

        replaced = self.attachment_id
        _debug.lifecycle(
            "version_restored",
            document=self,
            restored=attachment_id,
            replaced=replaced.id,
        )
        self.write({"attachment_id": attachment.id})
        self.message_post(
            body=_(
                "Version restored: “%(restored)s” replaces “%(replaced)s”.",
                restored=attachment.name,
                replaced=replaced.name,
            )
        )

    def _remove_excess_versions(self) -> None:
        max_versions = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param_int("document.max_versions", 0)
        )
        if max_versions <= 0:
            return
        _debug.pipeline("version_trim", documents=self, max_versions=max_versions)
        excess = self.env["ir.attachment"]
        for document in self:
            versions = document.previous_attachment_ids.sorted(
                key=lambda attachment: (attachment.create_date, attachment.id),
                reverse=True,
            )
            if len(versions) > max_versions:
                _debug.lifecycle(
                    "versions_dropped",
                    document=document,
                    dropped=len(versions) - max_versions,
                )
                excess |= versions[max_versions:]
        # One unlink for every document being trimmed: `unlink` is a delete
        # plus its filestore work, and calling it per document made trimming N
        # documents cost N round-trips.
        excess.sudo().unlink()
