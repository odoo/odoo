from odoo import fields, models
from odoo.exceptions import UserError


class GovAuditoriaAcordaoWizard(models.TransientModel):
    _name = "gov.auditoria.acordao.wizard"
    _description = "Wizard de Registro de Acordao"

    ciclo_id = fields.Many2one("gov.auditoria.ciclo", required=True, ondelete="cascade")
    tipo_decisao = fields.Selection(
        [
            ("regular", "Regular"),
            ("regular_com_ressalvas", "Regular com Ressalvas"),
            ("irregular", "Irregular"),
            ("em_recurso", "Em Recurso"),
        ],
        required=True,
        default="regular",
    )
    numero_acordao = fields.Char(required=True)
    data_acordao = fields.Date(required=True, default=fields.Date.today)
    data_publicacao = fields.Date()
    ementa = fields.Text(required=True)
    prazo_recurso_dias = fields.Integer(default=0)
    valor_condenacao = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(related="ciclo_id.currency_id")
    attachment_ids = fields.Many2many("ir.attachment", string="Anexos")

    def action_confirm(self):
        self.ensure_one()
        ciclo = self.ciclo_id
        if ciclo.state not in ("julgamento", "recurso", "em_analise", "acordao"):
            raise UserError("O acordao so pode ser registrado apos julgamento ou em analise.")

        decisao = self.env["gov.auditoria.decisao"].create(
            {
                "ciclo_id": ciclo.id,
                "tipo": self.tipo_decisao,
                "numero_acordao": self.numero_acordao,
                "data_acordao": self.data_acordao,
                "data_publicacao": self.data_publicacao,
                "ementa": self.ementa,
                "valor_condenacao": self.valor_condenacao,
                "prazo_recurso_dias": self.prazo_recurso_dias,
                "attachment_ids": [(6, 0, self.attachment_ids.ids)],
                "state": "publicado",
            }
        )
        ciclo.action_to_acordao()
        self.env["gov.auditoria.evento"].create(
            {
                "ciclo_id": ciclo.id,
                "tipo": "acordao_proferido",
                "data_evento": fields.Datetime.now(),
                "descricao": f"Acordao {decisao.numero_acordao} registrado.",
                "responsavel_id": self.env.user.id,
                "origem": "manual",
                "state": "concluido",
            }
        )
        if self.attachment_ids:
            for attachment in self.attachment_ids:
                self.env["gov.auditoria.documento"].create(
                    {
                        "ciclo_id": ciclo.id,
                        "nome": attachment.name or f"Acordao {self.numero_acordao}",
                        "tipo": "acordao",
                        "origem": "importado",
                        "attachment_id": attachment.id,
                        "state": "finalizado",
                        "protocolo_externo": self.numero_acordao,
                    }
                )
        return {"type": "ir.actions.act_window_close"}
