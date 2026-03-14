import base64
import json

from odoo import api, fields, models
from odoo.exceptions import UserError

from .constants import XLSX_PROFILE_SELECTION


class GovProcessoPlanilhaJob(models.Model):
    _name = "gov.processo.planilha.job"
    _description = "Job de Geracao de Planilha do Processo"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, default="Job XLSX")
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
        ondelete="set null",
        index=True,
    )
    profile = fields.Selection(
        XLSX_PROFILE_SELECTION,
        string="Perfil",
        required=True,
        default="procurement_reference",
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
    payload_json = fields.Text(string="Payload")
    error_message = fields.Text(string="Erro")
    file_data = fields.Binary(string="Planilha XLSX", attachment=True, readonly=True)
    file_name = fields.Char(string="Nome do Arquivo", readonly=True)
    sha256 = fields.Char(string="SHA-256", readonly=True)
    row_count = fields.Integer(string="Qtd. Itens", readonly=True)
    lot_count = fields.Integer(string="Qtd. Lotes", readonly=True)

    @api.model
    def create_from_doc(self, doc, profile=None):
        doc.ensure_one()
        selected_profile = profile or doc.xlsx_profile or doc.processo_id.xlsx_profile or "procurement_reference"
        return self.create(
            {
                "name": f"Planilha XLSX - {doc.name}",
                "processo_id": doc.processo_id.id,
                "doc_id": doc.id,
                "profile": selected_profile,
            }
        )

    def action_process_now(self):
        for job in self:
            job._process_job()
        return True

    def _process_job(self):
        self.ensure_one()
        service = self.env["gov.xlsx.worker.service"]
        self.write(
            {
                "state": "running",
                "started_at": fields.Datetime.now(),
                "error_message": False,
            }
        )
        try:
            result = service.generate_workbook(
                self.processo_id,
                doc=self.doc_id,
                profile=self.profile,
            )
            encoded_binary = base64.b64encode(result["binary"])
            self.write(
                {
                    "state": "done",
                    "finished_at": fields.Datetime.now(),
                    "payload_json": json.dumps(result["payload"], ensure_ascii=False, indent=2),
                    "file_data": encoded_binary,
                    "file_name": result["filename"],
                    "sha256": result["sha256"],
                    "row_count": result["row_count"],
                    "lot_count": result["lot_count"],
                }
            )
            if self.doc_id:
                self.doc_id.write(
                    {
                        "pesquisa_precos_planilha": encoded_binary,
                        "pesquisa_precos_planilha_filename": result["filename"],
                        "change_reason": "Planilha XLSX gerada pelo worker do processo",
                    }
                )
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
            raise UserError(f"Falha ao gerar a planilha XLSX: {exc}") from exc

    @api.model
    def _cron_process_pending_jobs(self, limit=10):
        pending_jobs = self.search([("state", "=", "pending")], order="id asc", limit=limit)
        for job in pending_jobs:
            try:
                job._process_job()
            except Exception:
                continue
