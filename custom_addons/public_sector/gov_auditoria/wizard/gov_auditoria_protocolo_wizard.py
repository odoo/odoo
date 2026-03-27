from odoo import fields, models
from odoo.exceptions import UserError


class GovAuditoriaProtocoloWizard(models.TransientModel):
    _name = "gov.auditoria.protocolo.wizard"
    _description = "Wizard de Protocolo de Envio"

    ciclo_id = fields.Many2one("gov.auditoria.ciclo", required=True, ondelete="cascade")
    protocolo_externo = fields.Char(required=True)
    data_envio = fields.Datetime(required=True, default=fields.Datetime.now)
    observacao = fields.Text()
    documento_ids = fields.Many2many(
        "gov.auditoria.documento",
        string="Documentos",
        domain="[('ciclo_id', '=', ciclo_id), ('state', 'in', ['rascunho', 'finalizado'])]",
    )
    recibo_attachment_id = fields.Many2one("ir.attachment", string="Recibo")

    def action_confirm(self):
        self.ensure_one()
        ciclo = self.ciclo_id
        if ciclo.state not in ("remessa", "em_analise", "defesa", "recurso", "acordao"):
            raise UserError("O protocolo so pode ser registrado apos a remessa.")
        if not self.documento_ids:
            raise UserError("Selecione ao menos um documento para protocolar.")

        self.documento_ids.write(
            {
                "state": "enviado",
                "data_envio": self.data_envio,
                "protocolo_externo": self.protocolo_externo,
            }
        )
        evento = self.env["gov.auditoria.evento"].create(
            {
                "ciclo_id": ciclo.id,
                "tipo": "protocolo_envio",
                "data_evento": self.data_envio,
                "descricao": self.observacao or f"Protocolo externo {self.protocolo_externo} registrado.",
                "responsavel_id": self.env.user.id,
                "origem": "manual",
                "state": "concluido",
                "documento_ids": [(6, 0, self.documento_ids.ids)],
            }
        )
        if self.recibo_attachment_id:
            recibo = self.env["gov.auditoria.documento"].create(
                {
                    "ciclo_id": ciclo.id,
                    "event_id": evento.id,
                    "nome": self.recibo_attachment_id.name or f"Recibo {self.protocolo_externo}",
                    "tipo": "certidao",
                    "origem": "importado",
                    "attachment_id": self.recibo_attachment_id.id,
                    "state": "enviado",
                    "data_envio": self.data_envio,
                    "protocolo_externo": self.protocolo_externo,
                    "resumo": self.observacao,
                }
            )
            evento.documento_ids = [(4, recibo.id)]

        ciclo.write(
            {
                "numero_protocolo": self.protocolo_externo,
                "data_remessa": ciclo.data_remessa or fields.Date.to_date(self.data_envio),
            }
        )
        if ciclo.state == "remessa":
            ciclo.action_to_em_analise()
        return {"type": "ir.actions.act_window_close"}
