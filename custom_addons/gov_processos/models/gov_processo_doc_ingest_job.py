from odoo import api, fields, models
from odoo.exceptions import UserError

from .gov_template_service import GovTemplateService


class GovProcessoDocIngestJob(models.Model):
    _name = "gov.processo.doc.ingest.job"
    _description = "Job de Conversao de Upload do Documento"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, default="Conversao de Upload")
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
    target_format = fields.Selection(
        selection=lambda self: GovTemplateService.get_target_format_selection(),
        string="Formato de Destino",
        required=True,
        default="latex",
    )
    source_filename = fields.Char(string="Arquivo de Origem", readonly=True)
    source_input_format = fields.Selection(
        selection=lambda self: GovTemplateService.get_source_format_selection(),
        string="Formato de Origem",
        readonly=True,
    )
    parser_used = fields.Char(string="Parser Utilizado", readonly=True)
    state = fields.Selection(
        [
            ("pending", "Pendente"),
            ("running", "Processando"),
            ("done", "Concluído"),
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
    apply_to_document = fields.Boolean(
        string="Aplicar no Documento",
        default=True,
        help="Quando marcado, grava as fontes convertidas no documento do dossiê.",
    )
    started_at = fields.Datetime(string="Iniciado em", readonly=True)
    finished_at = fields.Datetime(string="Finalizado em", readonly=True)
    payload_json = fields.Text(string="Payload", readonly=True)
    normalized_source = fields.Text(string="Saída Normalizada", readonly=True)
    native_source_text = fields.Text(string="Fonte Extraída", readonly=True)
    error_message = fields.Text(string="Erro", readonly=True)
    applied_version_number = fields.Integer(string="Versão Aplicada", readonly=True)

    @api.model
    def create_from_doc(self, doc, target_format=None, apply_to_document=True):
        doc.ensure_one()
        if not doc.upload_externo:
            raise UserError("Envie um arquivo na aba Upload Externo antes de criar o job.")
        selected_format = target_format or doc.ingest_target_format or "latex"
        return self.create(
            {
                "name": f"Conversão de Upload - {doc.name}",
                "processo_id": doc.processo_id.id,
                "doc_id": doc.id,
                "target_format": selected_format,
                "apply_to_document": apply_to_document,
            }
        )

    def action_process_now(self):
        for job in self:
            job._process_job()
        return True

    def _process_job(self):
        self.ensure_one()
        service = self.env["gov.document.ingest.worker.service"]
        self.write(
            {
                "state": "running",
                "started_at": fields.Datetime.now(),
                "error_message": False,
            }
        )
        try:
            payload = service.build_payload(self.doc_id, target_format=self.target_format)
            values = {
                "state": "done",
                "finished_at": fields.Datetime.now(),
                "source_filename": payload.get("source_filename"),
                "source_input_format": payload.get("native_format") or "unknown",
                "parser_used": payload.get("parser_used") or False,
                "payload_json": service.prepare_payload_json(payload),
                "normalized_source": payload.get("normalized_source") or "",
                "native_source_text": payload.get("native_source_text") or "",
            }
            if self.apply_to_document and self.doc_id:
                service.apply_payload_to_doc(self.doc_id, payload)
                values["applied_version_number"] = self.doc_id.version
            self.write(values)
        except Exception as exc:
            self.write(
                {
                    "state": "error",
                    "finished_at": fields.Datetime.now(),
                    "error_message": str(exc),
                }
            )
            if isinstance(exc, UserError):
                raise
            raise UserError(f"Falha ao converter upload externo: {exc}") from exc

    @api.model
    def _cron_process_pending_jobs(self, limit=10):
        pending_jobs = self.search([("state", "=", "pending")], order="id asc", limit=limit)
        for job in pending_jobs:
            try:
                job._process_job()
            except Exception:
                continue
