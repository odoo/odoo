import io
import zipfile

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.libs.filesystem import guess_mimetype
from odoo.tools.misc import format_date

_debug = DebugLog(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @_debug.perf.timed
    def _prepare_zip_from_attachments(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(
            buffer, "w", compression=zipfile.ZIP_DEFLATED
        ) as zipfile_obj:
            for attachment in self:
                zipfile_obj.writestr(attachment.display_name, attachment.raw)
        return buffer.getvalue()

    @api.ondelete(at_uninstall=True)
    @_debug.perf.timed
    def _except_audit_trail(self):
        _debug.lifecycle("_except_audit_trail", records=self)
        audit_trail_attachments = self.filtered(
            lambda attachment: (
                attachment.res_model == "account.move"
                and attachment.res_id
                and attachment.raw
                and guess_mimetype(attachment.raw)
                in (
                    "application/pdf",
                    "application/xml",
                )
            )
        )
        id2move = (
            self.env["account.move"]
            .browse(set(audit_trail_attachments.mapped("res_id")))
            .exists()
            .grouped("id")
        )
        for attachment in audit_trail_attachments:
            move = id2move.get(attachment.res_id)
            if (
                move
                and move.posted_before
                and move.company_id.account_config_id.restrictive_audit_trail
            ):
                ue = UserError(
                    _("You cannot remove parts of a restricted audit trail.")
                )
                ue._audit_trail = True
                raise ue

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        if vals.keys() & {
            "res_id",
            "res_model",
            "raw",
            "datas",
            "store_fname",
            "db_datas",
            "company_id",
        }:
            try:
                self._except_audit_trail()
            except UserError as e:
                if (
                    not hasattr(e, "_audit_trail")
                    or vals.get("res_model") != "document.document"
                    or vals.keys() & {"raw", "datas", "store_fname", "db_datas"}
                ):
                    raise
                _debug.logic(
                    "audit_trail_relinked_document", records=self, fields=sorted(vals)
                )
                vals.pop("res_model", None)
                vals.pop("res_id", None)
        return super().write(vals)

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        invoice_pdf_attachments = self.filtered(
            lambda attachment: (
                attachment.res_model == "account.move"
                and attachment.res_id
                and attachment.res_field
                in ("invoice_pdf_report_file", "ubl_cii_xml_file")
                and attachment.company_id.account_config_id.restrictive_audit_trail
            )
        )
        _debug.logic(
            "audit_pdfs_detached",
            detached=invoice_pdf_attachments,
            unlinked=len(self) - len(invoice_pdf_attachments),
        )
        if invoice_pdf_attachments:
            invoice_pdf_attachments.res_field = False
            today = format_date(self.env, fields.Date.context_today(self))
            for attachment in invoice_pdf_attachments:
                attachment_name = attachment.name
                attachment_extension = ""
                dot_index = attachment_name.rfind(".")
                if dot_index > 0:
                    attachment_name = attachment.name[:dot_index]
                    attachment_extension = attachment.name[dot_index:]
                attachment.name = _(
                    "%(attachment_name)s (detached by %(user)s on %(date)s)%(attachment_extension)s",
                    attachment_name=attachment_name,
                    attachment_extension=attachment_extension,
                    user=self.env.user.name,
                    date=today,
                )
        return super(IrAttachment, self - invoice_pdf_attachments).unlink()

    @_debug.perf.timed
    def _post_add_create(self, **kwargs):
        _debug.lifecycle("_post_add_create", records=self)
        for move_id, attachments in (
            self.filtered(lambda attachment: attachment.res_model == "account.move")
            .grouped("res_id")
            .items()
        ):
            move = self.env["account.move"].browse(move_id)
            files_data = move._to_files_data(attachments)
            files_data.extend(move._unwrap_attachments(files_data))
            move._extend_with_attachments(files_data)
        super()._post_add_create(**kwargs)
