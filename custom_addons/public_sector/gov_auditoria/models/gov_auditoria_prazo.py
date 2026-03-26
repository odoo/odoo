from datetime import timedelta

from odoo import api, fields, models


class GovAuditoriaPrazo(models.Model):
    _name = "gov.auditoria.prazo"
    _description = "Cycle Deadline"
    _order = "data_fim_real, data_fim_legal, id"

    ciclo_id = fields.Many2one("gov.auditoria.ciclo", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="ciclo_id.company_id", store=True, readonly=True)
    evento_id = fields.Many2one("gov.auditoria.evento", ondelete="set null")
    tipo = fields.Selection(
        [
            ("legal", "Legal"),
            ("interno", "Interno"),
            ("suspensao", "Suspensao"),
            ("prorrogacao", "Prorrogacao"),
        ],
        required=True,
        default="legal",
    )
    descricao = fields.Char(required=True)
    data_inicio = fields.Date(required=True, default=fields.Date.today)
    data_fim_legal = fields.Date(required=True)
    data_fim_real = fields.Date(compute="_compute_data_fim_real", store=True)
    dias = fields.Integer(default=0)
    dias_uteis = fields.Boolean(default=False)
    suspensao_ids = fields.One2many("gov.auditoria.prazo.suspensao", "prazo_id")
    state = fields.Selection(
        [
            ("vigente", "Vigente"),
            ("vencido", "Vencido"),
            ("suspenso", "Suspenso"),
            ("cumprido", "Cumprido"),
            ("cancelado", "Cancelado"),
        ],
        default="vigente",
        required=True,
    )
    alerta_antecedencia_dias = fields.Integer(default=3)

    @api.depends("data_fim_legal", "suspensao_ids.data_inicio_suspensao", "suspensao_ids.data_fim_suspensao")
    def _compute_data_fim_real(self):
        for rec in self:
            end_date = rec.data_fim_legal
            extra_days = 0
            for suspension in rec.suspensao_ids:
                if suspension.data_inicio_suspensao and suspension.data_fim_suspensao:
                    extra_days += (suspension.data_fim_suspensao - suspension.data_inicio_suspensao).days + 1
            rec.data_fim_real = end_date and fields.Date.to_date(end_date) + timedelta(days=extra_days) or False


class GovAuditoriaPrazoSuspensao(models.Model):
    _name = "gov.auditoria.prazo.suspensao"
    _description = "Deadline Suspension"
    _order = "data_inicio_suspensao, id"

    prazo_id = fields.Many2one("gov.auditoria.prazo", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="prazo_id.company_id", store=True, readonly=True)
    data_inicio_suspensao = fields.Date(required=True)
    data_fim_suspensao = fields.Date(required=True)
    motivo = fields.Text()
