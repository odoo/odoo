import json

from odoo import api, models
from odoo.exceptions import UserError

from .gov_template_service import GovTemplateService


class GovDocumentIngestWorkerService(models.AbstractModel):
    _name = "gov.document.ingest.worker.service"
    _description = "Worker de Ingestao Documental"

    @api.model
    def build_payload(self, doc, target_format="latex"):
        doc.ensure_one()
        if not doc.upload_externo:
            raise UserError("Nenhum upload externo encontrado no documento.")

        payload = GovTemplateService.extract_template_source_from_upload(
            self.env,
            doc.upload_externo,
            doc.upload_externo_filename,
            target_format=target_format or "latex",
        )
        payload["target_format"] = target_format or "latex"
        payload["doc_name"] = doc.name or ""
        payload["doc_id"] = doc.id
        payload["processo_id"] = doc.processo_id.id if doc.processo_id else False
        return payload

    @api.model
    def _build_change_reason(self, payload):
        source_format = (payload.get("native_format") or "arquivo").upper()
        target_format = (payload.get("target_format") or "latex").upper()
        parser_used = payload.get("parser_used")
        suffix = f" via {parser_used}" if parser_used else ""
        return f"Conversão de upload externo ({source_format} -> {target_format}){suffix}"

    @api.model
    def apply_payload_to_doc(self, doc, payload):
        doc.ensure_one()
        change_reason = self._build_change_reason(payload)
        vals = {
            "latex_source": payload.get("latex_source") or False,
            "typst_source": payload.get("typst_source") or False,
            "content_html": payload.get("html_source") or False,
            "change_reason": change_reason,
            "ai_generated": False,
        }
        doc.write(vals)
        self.env["gov.processo.versao"].create(
            {
                "doc_id": doc.id,
                "version_number": doc.version,
                "content_snapshot_html": doc.content_html,
                "typst_snapshot": doc.typst_source,
                "latex_snapshot": doc.latex_source,
                "pdf_snapshot": doc.pdf_file,
                "changed_by": self.env.user.id,
                "changed_at": doc.write_date,
                "change_reason": change_reason,
                "ai_generated": doc.ai_generated,
            }
        )
        return change_reason

    @api.model
    def prepare_payload_json(self, payload):
        compact = {
            "source_filename": payload.get("source_filename"),
            "native_format": payload.get("native_format"),
            "target_format": payload.get("target_format"),
            "parser_used": payload.get("parser_used"),
            "normalized_source_preview": (payload.get("normalized_source") or "")[:4000],
            "native_source_preview": (payload.get("native_source_text") or "")[:4000],
        }
        return json.dumps(compact, ensure_ascii=False, indent=2)
