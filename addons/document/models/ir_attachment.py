import io
import logging
from collections import defaultdict

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools.pdf import OdooPdfFileReader, OdooPdfFileWriter

from odoo.addons.document.tools import UserFolder

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    document_ids = fields.One2many(
        comodel_name="document.document",
        inverse_name="attachment_id",
        export_string_translation=False,
    )

    def get_documents_operation_add_destination(self) -> dict:
        self.check_singleton()
        return {
            "destination": UserFolder.MY,
            "display_name": self.env._("My Drive"),
        }

    @api.model
    def _pdf_split(
        self, new_files: list | None = None, open_files: list | None = None
    ) -> IrAttachment:
        vals_list = []
        pdf_from_files = [
            OdooPdfFileReader(open_file, strict=False) for open_file in open_files
        ]

        for new_file in new_files:
            output = OdooPdfFileWriter()
            used_pages_by_pdf = defaultdict(set)
            for page in new_file["new_pages"]:
                file_index = int(page["old_file_index"])
                page_index = int(page["old_page_number"]) - 1
                if not 0 <= file_index < len(pdf_from_files):
                    raise ValueError(f"Invalid source file index {file_index}")
                input_pdf = pdf_from_files[file_index]
                if not 0 <= page_index < len(input_pdf.pages):
                    raise ValueError(f"Invalid page number {page['old_page_number']}")
                output.add_page(input_pdf.pages[page_index])
                used_pages_by_pdf[file_index].add(page_index)
                if len(used_pages_by_pdf[file_index]) != len(input_pdf.pages):
                    continue
                try:
                    for fname, fcontent in input_pdf.get_attachments():
                        output.add_attachment(name=fname, data=fcontent)
                except Exception:
                    _logger.warning(
                        "Impossible to add (all) attachments from pdf at index %i",
                        file_index,
                        exc_info=True,
                    )
            with io.BytesIO() as stream:
                output.write(stream)
                _debug.pipeline(
                    "pdf_page_set_written",
                    name=new_file["name"],
                    pages=len(new_file["new_pages"]),
                    sources=len(used_pages_by_pdf),
                )
                vals_list.append(
                    {
                        "name": new_file["name"] + ".pdf",
                        "raw": stream.getvalue(),
                    }
                )
        return self.create(vals_list)

    def _create_document(self, res_model: str | None, res_id: int | None) -> bool:
        if res_model == "document.document" and res_id:
            document = self.env["document.document"].search_fetch(
                [("id", "=", res_id)], []
            )
            if document and not document.attachment_id and document.type == "binary":
                _debug.lifecycle("document_attachment_filled", document=document)
                document.attachment_id = self[0].id
            return False

        model = self.env.get(res_model)
        if (
            model is None
            or not res_id
            or not issubclass(self.pool[res_model], self.pool["mixin.documents"])
        ):
            _debug.logic("auto_document_skipped", reason="model", res_model=res_model)
            return False
        record = model.browse(res_id)
        if not record._check_create_documents():
            _debug.logic("auto_document_skipped", reason="no_folder", record=record)
            return False
        candidates = self.filtered(lambda attachment: not attachment.res_field)
        already_documented = set(
            self.env["document.document"]
            .sudo()
            .with_context(active_test=False)
            .search_fetch([("attachment_id", "in", candidates.ids)], ["attachment_id"])
            .mapped("attachment_id")
            .ids
        )
        vals_list = [
            document_vals
            for attachment in candidates
            if attachment.id not in already_documented
            and (document_vals := record._prepare_document_vals(attachment))
        ]
        if not vals_list:
            trashed = (
                self.env["document.document"]
                .sudo()
                .with_context(active_test=False)
                .search_count(
                    [
                        ("attachment_id", "in", list(already_documented)),
                        ("active", "=", False),
                    ]
                )
                if already_documented
                else 0
            )
            _debug.logic(
                "auto_document_skipped",
                reason="already_documented",
                candidates=len(candidates),
                documented=len(already_documented),
                trashed=trashed,
            )
            return False
        _debug.pipeline(
            "auto_document_created",
            res_model=res_model,
            count=len(vals_list),
            with_attachment=sum(1 for vals in vals_list if vals.get("attachment_id")),
        )
        self.env["document.document"].create(vals_list)
        return True

    @api.model_create_multi
    def create(self, vals_list: list[dict]) -> IrAttachment:
        attachments = super().create(vals_list)
        if self.env.context.get("no_document"):
            _debug.logic("auto_document_skipped", reason="no_document_context")
            return attachments
        to_document = attachments.filtered(lambda a: not a.res_field)
        for (res_model, res_id), grouped in to_document.grouped(
            lambda attachment: (attachment.res_model, attachment.res_id)
        ).items():
            grouped.sudo()._create_document(res_model, res_id)
        return attachments

    def write(self, vals: dict) -> bool:
        if self.env.context.get("no_document"):
            _debug.logic("auto_document_skipped", reason="no_document_context")
            return super().write(vals)
        # Decided before `super().write`, because only a write that moves
        # res_model/res_id can create a document and `a.res_field` is about to
        # change. Reading it at all costs a fetch, so the cheap test that
        # rules the whole thing out comes first.
        if not {"res_model", "res_id"} & vals.keys():
            return super().write(vals)
        to_document = self.filtered(
            lambda a: not (vals.get("res_field") or a.res_field)
        )
        result = super().write(vals)
        _debug.pipeline("auto_document_rescan", attachments=to_document)
        for (res_model, res_id), attachments in to_document.grouped(
            lambda attachment: (attachment.res_model, attachment.res_id)
        ).items():
            attachments.sudo()._create_document(res_model, res_id)
        return result
