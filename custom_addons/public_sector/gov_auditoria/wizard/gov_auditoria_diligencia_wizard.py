from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import UserError


class GovAuditoriaDiligenciaWizard(models.TransientModel):
    _name = "gov.auditoria.diligencia.wizard"
    _description = "Wizard de Registro de Diligencia"

    ciclo_id = fields.Many2one("gov.auditoria.ciclo", required=True, ondelete="cascade")
    descricao = fields.Text(required=True, default="Diligencia registrada no ciclo.")
    data_evento = fields.Datetime(required=True, default=fields.Datetime.now)
    prazo_dias = fields.Integer(default=lambda self: self.ciclo_id.orgao_id.prazo_defesa_dias or 15)
    criar_prazo = fields.Boolean(default=True)
    documento_ids = fields.Many2many("ir.attachment", string="Anexos")

    def action_confirm(self):
        self.ensure_one()
        ciclo = self.ciclo_id
        if ciclo.state not in ("em_analise", "diligencia", "defesa"):
            raise UserError("A diligencia so pode ser registrada em ciclos em analise, diligencia ou defesa.")

        ciclo.action_to_diligencia()
        event = self.env["gov.auditoria.evento"].create(
            {
                "ciclo_id": ciclo.id,
                "tipo": "diligencia_emitida",
                "data_evento": self.data_evento,
                "descricao": self.descricao,
                "responsavel_id": self.env.user.id,
                "origem": "manual",
                "state": "concluido",
            }
        )

        if self.criar_prazo and self.prazo_dias:
            start_date = fields.Date.to_date(self.data_evento)
            self.env["gov.auditoria.prazo"].create(
                {
                    "ciclo_id": ciclo.id,
                    "evento_id": event.id,
                    "tipo": "legal",
                    "descricao": "Prazo de resposta a diligencia",
                    "data_inicio": start_date,
                    "data_fim_legal": start_date + timedelta(days=self.prazo_dias),
                    "dias": self.prazo_dias,
                    "alerta_antecedencia_dias": 3,
                }
            )

        for attachment in self.documento_ids:
            documento = self.env["gov.auditoria.documento"].create(
                {
                    "ciclo_id": ciclo.id,
                    "event_id": event.id,
                    "nome": attachment.name or "Documento de Diligencia",
                    "tipo": "notificacao",
                    "origem": "importado",
                    "attachment_id": attachment.id,
                    "state": "finalizado",
                }
            )
            event.documento_ids = [(4, documento.id)]

        return {"type": "ir.actions.act_window_close"}
