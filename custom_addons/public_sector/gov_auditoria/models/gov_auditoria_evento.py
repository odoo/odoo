from odoo import api, fields, models


class GovAuditoriaEvento(models.Model):
    _name = "gov.auditoria.evento"
    _description = "Cycle Event"
    _order = "data_evento desc, id desc"

    ciclo_id = fields.Many2one("gov.auditoria.ciclo", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="ciclo_id.company_id", store=True, readonly=True)
    tipo = fields.Selection(
        [
            ("protocolo_envio", "Protocolo de Envio"),
            ("oficio_recebido", "Oficio Recebido"),
            ("diligencia_emitida", "Diligencia Emitida"),
            ("prazo_defesa_aberto", "Prazo de Defesa Aberto"),
            ("resposta_defesa_enviada", "Resposta de Defesa Enviada"),
            ("parecer_tecnico", "Parecer Tecnico"),
            ("relatorio_previo", "Relatorio Previo"),
            ("sessao_julgamento_pautada", "Sessao de Julgamento Pautada"),
            ("acordao_proferido", "Acordao Proferido"),
            ("recurso_interposto", "Recurso Interposto"),
            ("transito_julgado", "Transito em Julgado"),
            ("determinacao_cumprida", "Determinacao Cumprida"),
            ("nota_interna", "Nota Interna"),
        ],
        required=True,
        default="nota_interna",
    )
    data_evento = fields.Datetime(default=fields.Datetime.now, required=True)
    data_limite = fields.Date()
    descricao = fields.Text(required=True)
    documento_ids = fields.Many2many(
        "gov.auditoria.documento",
        "gov_auditoria_evento_documento_rel",
        "evento_id",
        "documento_id",
        string="Documentos",
    )
    responsavel_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    state = fields.Selection(
        [
            ("pendente", "Pendente"),
            ("concluido", "Concluido"),
            ("vencido", "Vencido"),
            ("cancelado", "Cancelado"),
        ],
        default="concluido",
        required=True,
    )
    origem = fields.Selection(
        [
            ("manual", "Manual"),
            ("automatico", "Automatico"),
            ("importado", "Importado"),
        ],
        default="manual",
        required=True,
    )
    documento_count = fields.Integer(compute="_compute_documento_count", store=False)

    @api.onchange("data_limite")
    def _onchange_data_limite(self):
        for rec in self:
            if rec.data_limite and rec.data_limite < fields.Date.today():
                rec.state = "vencido"

    @api.depends("documento_ids")
    def _compute_documento_count(self):
        for rec in self:
            rec.documento_count = len(rec.documento_ids)
