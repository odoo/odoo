from odoo import fields, models


class GovAuditoriaApontamento(models.Model):
    _name = "gov.auditoria.apontamento"
    _description = "Audit Finding"
    _order = "id desc"

    ciclo_id = fields.Many2one("gov.auditoria.ciclo", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="ciclo_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="ciclo_id.currency_id", store=True, readonly=True)
    codigo = fields.Char()
    descricao = fields.Text(required=True)
    tipo = fields.Selection(
        [
            ("irregularidade", "Irregularidade"),
            ("ressalva", "Ressalva"),
            ("recomendacao", "Recomendacao"),
            ("determinacao", "Determinacao"),
            ("multa", "Multa"),
        ],
        required=True,
        default="irregularidade",
    )
    valor_multa = fields.Monetary(currency_field="currency_id")
    responsavel_ids = fields.Many2many("res.partner", string="Responsaveis")
    prazo_defesa_id = fields.Many2one("gov.auditoria.prazo", ondelete="set null")
    resposta = fields.Text()
    data_resposta = fields.Date()
    documento_resposta_ids = fields.Many2many(
        "gov.auditoria.documento",
        "gov_auditoria_apontamento_documento_rel",
        "apontamento_id",
        "documento_id",
        string="Docs de Resposta",
    )
    state = fields.Selection(
        [
            ("aberto", "Aberto"),
            ("respondido", "Respondido"),
            ("acatado", "Acatado"),
            ("rejeitado", "Rejeitado"),
        ],
        default="aberto",
        required=True,
    )
    decisao_id = fields.Many2one("gov.auditoria.decisao", ondelete="set null")

    def action_open_resposta_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Registrar Resposta",
            "res_model": "gov.auditoria.apontamento.resposta.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_ciclo_id": self.ciclo_id.id,
                "default_apontamento_id": self.id,
            },
        }

    def action_mark_acatado(self):
        for rec in self:
            rec.state = "acatado"
        return True

    def action_mark_rejeitado(self):
        for rec in self:
            rec.state = "rejeitado"
        return True
