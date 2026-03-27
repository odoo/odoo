from odoo import fields, models
from odoo.exceptions import UserError


class GovAuditoriaApontamentoRespostaWizard(models.TransientModel):
    _name = "gov.auditoria.apontamento.resposta.wizard"
    _description = "Wizard de Resposta a Apontamento"

    ciclo_id = fields.Many2one("gov.auditoria.ciclo", required=True, ondelete="cascade")
    apontamento_id = fields.Many2one(
        "gov.auditoria.apontamento",
        required=True,
        ondelete="cascade",
        domain="[('ciclo_id', '=', ciclo_id)]",
    )
    data_resposta = fields.Date(required=True, default=fields.Date.today)
    resposta = fields.Text(required=True)
    protocolo_externo = fields.Char()
    marcar_prazo_cumprido = fields.Boolean(default=True)
    attachment_ids = fields.Many2many("ir.attachment", string="Anexos")

    def action_confirm(self):
        self.ensure_one()
        apontamento = self.apontamento_id
        ciclo = self.ciclo_id
        if apontamento.ciclo_id != ciclo:
            raise UserError("O apontamento informado nao pertence ao ciclo selecionado.")

        documentos = self.env["gov.auditoria.documento"]
        for attachment in self.attachment_ids:
            documentos |= self.env["gov.auditoria.documento"].create(
                {
                    "ciclo_id": ciclo.id,
                    "nome": attachment.name or f"Resposta {apontamento.codigo or apontamento.id}",
                    "tipo": "defesa",
                    "origem": "importado",
                    "attachment_id": attachment.id,
                    "state": "finalizado",
                    "protocolo_externo": self.protocolo_externo,
                    "resumo": self.resposta,
                }
            )

        evento = self.env["gov.auditoria.evento"].create(
            {
                "ciclo_id": ciclo.id,
                "tipo": "resposta_defesa_enviada",
                "data_evento": fields.Datetime.now(),
                "descricao": f"Resposta registrada para o apontamento {apontamento.codigo or apontamento.id}.",
                "responsavel_id": self.env.user.id,
                "origem": "manual",
                "state": "concluido",
                "documento_ids": [(6, 0, documentos.ids)],
            }
        )
        apontamento.write(
            {
                "resposta": self.resposta,
                "data_resposta": self.data_resposta,
                "state": "respondido",
                "documento_resposta_ids": [(6, 0, documentos.ids)],
            }
        )
        if self.marcar_prazo_cumprido and apontamento.prazo_defesa_id:
            apontamento.prazo_defesa_id.write({"state": "cumprido"})
        if ciclo.state == "diligencia":
            ciclo.action_to_defesa()
        return {
            "type": "ir.actions.act_window_close",
            "context": {"created_event_id": evento.id},
        }
