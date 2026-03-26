from datetime import timedelta

from odoo import api, fields, models


class GovAuditoriaDecisao(models.Model):
    _name = "gov.auditoria.decisao"
    _description = "Final Decision"
    _order = "data_acordao desc, id desc"

    ciclo_id = fields.Many2one("gov.auditoria.ciclo", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="ciclo_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="ciclo_id.currency_id", store=True, readonly=True)
    tipo = fields.Selection(
        [
            ("regular", "Regular"),
            ("regular_com_ressalvas", "Regular com Ressalvas"),
            ("irregular", "Irregular"),
            ("em_recurso", "Em Recurso"),
        ],
        required=True,
        default="regular",
    )
    numero_acordao = fields.Char()
    data_acordao = fields.Date(required=True, default=fields.Date.today)
    data_publicacao = fields.Date()
    ementa = fields.Text()
    valor_condenacao = fields.Monetary(currency_field="currency_id")
    apontamento_ids = fields.Many2many("gov.auditoria.apontamento", string="Apontamentos")
    prazo_recurso_dias = fields.Integer(default=0)
    data_limite_recurso = fields.Date(compute="_compute_data_limite_recurso", store=True)
    data_transito = fields.Date()
    attachment_ids = fields.Many2many("ir.attachment", string="Anexos")
    determination_ids = fields.One2many("gov.auditoria.determinacao", "decisao_id", string="Determinacoes")

    @api.depends("data_acordao", "prazo_recurso_dias")
    def _compute_data_limite_recurso(self):
        for rec in self:
            if rec.data_acordao and rec.prazo_recurso_dias:
                rec.data_limite_recurso = rec.data_acordao + timedelta(days=rec.prazo_recurso_dias)
            else:
                rec.data_limite_recurso = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.ciclo_id.write({"decisao_id": rec.id})
        return records


class GovAuditoriaDeterminacao(models.Model):
    _name = "gov.auditoria.determinacao"
    _description = "Decision Determination"
    _order = "prazo_cumprimento, id"

    decisao_id = fields.Many2one("gov.auditoria.decisao", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="decisao_id.company_id", store=True, readonly=True)
    descricao = fields.Text(required=True)
    prazo_cumprimento = fields.Date()
    responsavel_id = fields.Many2one("res.partner")
    evidencia_ids = fields.Many2many("ir.attachment", string="Evidencias")
    state = fields.Selection(
        [
            ("pendente", "Pendente"),
            ("cumprido", "Cumprido"),
            ("parcial", "Parcial"),
            ("descumprido", "Descumprido"),
        ],
        default="pendente",
        required=True,
    )
