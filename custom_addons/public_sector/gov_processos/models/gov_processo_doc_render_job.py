import base64
import hashlib
import json
import re
import time

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..services.gov_odoo_bridge import GovOdooBridge
from ..services.gov_template_registry import GovTemplateRegistry
from ..services.gov_typst_serializer import GovTypstSerializer
from ..services.gov_typst_workspace import GovTypstWorkspace


class GovProcessoDocRenderJob(models.Model):
    _name = "gov.processo.doc.render.job"
    _description = "Job de Render Estruturado Typst"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, default="Render Typst")
    processo_id = fields.Many2one(
        "gov.processo",
        string="Processo",
        required=True,
        ondelete="cascade",
        index=True,
    )
    doc_id = fields.Many2one(
        "gov.processo.doc",
        string="Documento",
        required=True,
        ondelete="cascade",
        index=True,
    )
    template_ref = fields.Many2one(
        "gov.ai.template",
        string="Template Typst",
        readonly=True,
        ondelete="set null",
    )
    state = fields.Selection(
        [
            ("pending", "Pendente"),
            ("running", "Processando"),
            ("done", "Concluido"),
            ("error", "Erro"),
        ],
        string="Status",
        required=True,
        default="pending",
    )
    requested_by = fields.Many2one(
        "res.users",
        string="Solicitado por",
        default=lambda self: self.env.user,
        readonly=True,
    )
    started_at = fields.Datetime(string="Iniciado em", readonly=True)
    finished_at = fields.Datetime(string="Finalizado em", readonly=True)
    duration_secs = fields.Float(string="Duracao (s)", readonly=True)
    payload_json = fields.Text(string="Payload", readonly=True)
    dados_frozen = fields.Text(string="dados.typ congelado", readonly=True)
    template_snapshot = fields.Text(string="template.typ congelado", readonly=True)
    template_sha256 = fields.Char(string="SHA-256 Template", readonly=True, size=64)
    error_message = fields.Text(string="Erro", readonly=True)
    render_log = fields.Text(string="Log do Render", readonly=True)
    pdf_file = fields.Binary(string="PDF Gerado", attachment=True, readonly=True)
    pdf_filename = fields.Char(string="Nome do PDF", readonly=True)
    pdf_sha256 = fields.Char(string="SHA-256 PDF", readonly=True, size=64)

    @api.model
    def create_from_doc(self, doc, template=None):
        doc.ensure_one()
        if doc.state == "assinado":
            raise UserError("Documento assinado nao pode receber novo render estruturado.")

        resolved_template = template or doc._get_structured_typst_template()
        if not resolved_template:
            raise UserError("Selecione um template Typst para o render estruturado.")
        if resolved_template.output_format != "typst":
            raise UserError("O template selecionado nao esta configurado para Typst.")

        running_job = doc.render_job_ids.filtered(lambda job: job.state in ("pending", "running"))[:1]
        if running_job:
            raise UserError(
                f"Ja existe um render em andamento para este documento: {running_job.name}."
            )

        resolved_template.sync_process_parameters(doc.processo_id)
        bridge_payload = GovOdooBridge(doc, template=resolved_template).build()
        dados_frozen = GovTypstSerializer().dumps_all(bridge_payload)
        registry = GovTemplateRegistry(doc.env)
        template_snapshot = registry.resolve_text(resolved_template)
        template_sha256 = registry.resolve_sha256(resolved_template)
        payload_json = json.dumps(
            {
                "doc_id": doc.id,
                "doc_name": doc.name,
                "processo_id": doc.processo_id.id,
                "template_id": resolved_template.id,
                "template_name": resolved_template.name,
                "bindings": bridge_payload,
            },
            ensure_ascii=False,
            indent=2,
        )

        job = self.create(
            {
                "name": f"Render Typst - {doc.name}",
                "processo_id": doc.processo_id.id,
                "doc_id": doc.id,
                "template_ref": resolved_template.id,
                "payload_json": payload_json,
                "dados_frozen": dados_frozen,
                "template_snapshot": template_snapshot,
                "template_sha256": template_sha256,
            }
        )

        doc.write(
            {
                "render_state": "queued",
                "render_mode": "structured_typst",
                "template_ref": resolved_template.id,
                "dados_snapshot": dados_frozen,
                "template_snapshot": template_snapshot,
                "template_sha256": template_sha256,
                "last_render_job_id": job.id,
            }
        )
        return job

    def action_process_now(self):
        for job in self:
            job._process_job()
        return True

    def _process_job(self):
        self.ensure_one()
        start = time.monotonic()
        self.write(
            {
                "state": "running",
                "started_at": fields.Datetime.now(),
                "error_message": False,
            }
        )
        self.doc_id.write({"render_state": "running"})

        try:
            workspace = GovTypstWorkspace(env=self.env)
            pdf_bytes = workspace.compile(
                dados_typ_text=self.dados_frozen or "",
                template_typ_text=self.template_snapshot or "",
            )
            self._persist_artifacts(pdf_bytes, workspace.render_log, start)
        except Exception as exc:
            self.write(
                {
                    "state": "error",
                    "finished_at": fields.Datetime.now(),
                    "duration_secs": time.monotonic() - start,
                    "error_message": str(exc),
                }
            )
            self.doc_id.write({"render_state": "error"})
            if isinstance(exc, UserError):
                raise
            raise UserError(f"Falha ao gerar PDF estruturado Typst: {exc}") from exc

    def _persist_artifacts(self, pdf_bytes, render_log, start_time):
        self.ensure_one()
        pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        encoded_pdf = base64.b64encode(pdf_bytes).decode("ascii")
        safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", self.doc_id.name or "documento").strip("_")
        safe_name = safe_name or "documento"
        pdf_filename = f"{safe_name}_{pdf_sha256[:8]}.pdf"

        attachment = self.env["ir.attachment"].create(
            {
                "name": pdf_filename,
                "type": "binary",
                "datas": encoded_pdf,
                "res_model": "gov.processo.doc",
                "res_id": self.doc_id.id,
                "mimetype": "application/pdf",
            }
        )

        self.write(
            {
                "state": "done",
                "finished_at": fields.Datetime.now(),
                "duration_secs": time.monotonic() - start_time,
                "render_log": render_log or "",
                "pdf_file": encoded_pdf,
                "pdf_filename": pdf_filename,
                "pdf_sha256": pdf_sha256,
            }
        )

        self.doc_id.write(
            {
                "render_state": "done",
                "render_attachment_id": attachment.id,
                "pdf_file": encoded_pdf,
                "pdf_filename": pdf_filename,
                "hash_sha256": pdf_sha256,
            }
        )
        self.doc_id.message_post(
            body=Markup(
                "📄 <b>PDF estruturado gerado via Typst.</b><br/>"
                f"Arquivo: <b>{pdf_filename}</b><br/>"
                f"SHA-256: <code>{pdf_sha256}</code>"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
            attachment_ids=[attachment.id],
        )

    @api.model
    def _cron_process_pending_jobs(self, limit=10):
        pending_jobs = self.search([("state", "=", "pending")], order="id asc", limit=limit)
        for job in pending_jobs:
            try:
                job._process_job()
            except Exception:
                continue
