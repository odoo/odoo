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
    state = fields.Selection(
        [
            ("minuta", "Minuta"),
            ("publicado", "Publicado"),
            ("transitado", "Transitado"),
        ],
        default="publicado",
        required=True,
    )

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

    def action_mark_transitado(self):
        for rec in self:
            rec.write(
                {
                    "state": "transitado",
                    "data_transito": rec.data_transito or fields.Date.today(),
                }
            )
            rec.ciclo_id.action_to_acordao()


class GovAuditoriaDeterminacao(models.Model):
    _name = "gov.auditoria.determinacao"
    _description = "Decision Determination"
    _order = "prazo_cumprimento, id"

    decisao_id = fields.Many2one("gov.auditoria.decisao", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="decisao_id.company_id", store=True, readonly=True)
    descricao = fields.Text(required=True)
    prazo_cumprimento = fields.Date()
    prazo_id = fields.Many2one("gov.auditoria.prazo", ondelete="set null")
    responsavel_id = fields.Many2one("res.partner")
    evidencia_ids = fields.Many2many("ir.attachment", string="Evidencias")
    data_cumprimento = fields.Date()
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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._sync_deadline_records()
        return records

    def write(self, vals):
        result = super().write(vals)
        self._sync_deadline_records()
        return result

    def _sync_deadline_records(self):
        Prazo = self.env["gov.auditoria.prazo"]
        for rec in self:
            ciclo = rec.decisao_id.ciclo_id
            if not ciclo:
                continue
            if rec.prazo_cumprimento:
                prazo_vals = {
                    "ciclo_id": ciclo.id,
                    "tipo": "interno",
                    "descricao": f"Cumprimento de determinacao: {rec.descricao[:80]}",
                    "data_inicio": rec.decisao_id.data_acordao or fields.Date.today(),
                    "data_fim_legal": rec.prazo_cumprimento,
                }
                if rec.prazo_id:
                    rec.prazo_id.write(prazo_vals)
                else:
                    rec.prazo_id = Prazo.create(prazo_vals).id
            elif rec.prazo_id:
                rec.prazo_id.unlink()
                rec.prazo_id = False

            if rec.prazo_id and rec.state == "cumprido":
                rec.prazo_id.write({"state": "cumprido"})

    def action_mark_cumprido(self):
        for rec in self:
            rec.write(
                {
                    "state": "cumprido",
                    "data_cumprimento": rec.data_cumprimento or fields.Date.today(),
                }
            )
            self.env["gov.auditoria.evento"].create(
                {
                    "ciclo_id": rec.decisao_id.ciclo_id.id,
                    "tipo": "determinacao_cumprida",
                    "data_evento": fields.Datetime.now(),
                    "descricao": rec.descricao,
                    "responsavel_id": self.env.user.id,
                    "origem": "manual",
                    "state": "concluido",
                }
            )
        return True
