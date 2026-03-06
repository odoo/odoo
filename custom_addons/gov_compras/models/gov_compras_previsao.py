from odoo import api, fields, models
from odoo.exceptions import UserError


class GovComprasPrevisao(models.Model):
    _name = "gov.compras.previsao"
    _description = "Previsão Orçamentária de Compras"
    _inherit = ["mail.thread"]
    _order = "ano desc, id desc"

    name = fields.Char(
        string="Nome",
        compute="_compute_name",
        store=True,
    )
    ano = fields.Integer(
        string="Ano da Previsão",
        required=True,
        default=lambda self: fields.Date.today().year + 1,
        tracking=True,
    )
    ug_id = fields.Many2one(
        "res.company",
        string="Unidade Gestora",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    state = fields.Selection(
        [
            ("rascunho", "Rascunho"),
            ("revisao", "Em Revisão"),
            ("aprovado", "Aprovado"),
        ],
        string="Estado",
        default="rascunho",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    line_ids = fields.One2many(
        "gov.compras.previsao.line",
        "previsao_id",
        string="Itens",
    )
    total_previsto = fields.Monetary(
        string="Total Previsto",
        currency_field="currency_id",
        compute="_compute_total_previsto",
        store=True,
    )
    observacao = fields.Text(string="Observações")

    _ano_ug_unique = models.Constraint(
        "unique(ano, ug_id)",
        "Ja existe previsao para este ano e UG.",
    )

    @api.depends("ano", "ug_id")
    def _compute_name(self):
        for rec in self:
            rec.name = f"Previsão {rec.ano} - {rec.ug_id.name or ''}".strip(" -")

    @api.depends("line_ids.valor_total_previsto")
    def _compute_total_previsto(self):
        for rec in self:
            rec.total_previsto = sum(rec.line_ids.mapped("valor_total_previsto"))

    def action_gerar_linhas_catalogo(self):
        for rec in self:
            if rec.state != "rascunho":
                raise UserError("Só é possível gerar linhas em previsão de rascunho.")
            catalog_items = self.env["gov.compras.catalog.item"].search(
                [("ug_ids", "in", rec.ug_id.id), ("ativo_previsao", "=", True)]
            )
            Track = self.env["gov.compras.item.track"]
            existing_by_item = {line.catalog_item_id.id: line for line in rec.line_ids}
            for item in catalog_items:
                metrics = Track.get_conservative_metrics(rec.ug_id.id, item.id)
                vals = {
                    "quantidade_prevista": metrics.get("avg_qty", 0.0) or 1.0,
                    "valor_unit_previsto": metrics.get("conservative_price", 0.0),
                    "natureza_despesa": item.natureza_despesa_id.natureza_despesa if item.natureza_despesa_id else "",
                }
                if item.id in existing_by_item:
                    existing_by_item[item.id].write(vals)
                else:
                    self.env["gov.compras.previsao.line"].create(
                        {
                            "previsao_id": rec.id,
                            "catalog_item_id": item.id,
                            **vals,
                        }
                    )

    def action_enviar_revisao(self):
        for rec in self:
            if rec.state != "rascunho":
                raise UserError("A previsão precisa estar em rascunho.")
            if not rec.line_ids:
                raise UserError("Inclua ao menos um item antes de enviar para revisão.")
            rec.state = "revisao"

    def action_aprovar(self):
        for rec in self:
            if rec.state != "revisao":
                raise UserError("A previsão precisa estar em revisão para ser aprovada.")
            rec.state = "aprovado"

    def action_voltar_rascunho(self):
        for rec in self:
            rec.state = "rascunho"


class GovComprasPrevisaoLine(models.Model):
    _name = "gov.compras.previsao.line"
    _description = "Linha da Previsão Orçamentária de Compras"
    _order = "id asc"

    previsao_id = fields.Many2one(
        "gov.compras.previsao",
        string="Previsão",
        required=True,
        ondelete="cascade",
    )
    ug_id = fields.Many2one(related="previsao_id.ug_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="previsao_id.currency_id", store=True, readonly=True)
    catalog_item_id = fields.Many2one(
        "gov.compras.catalog.item",
        string="Item",
        required=True,
        domain="[('ug_ids', 'in', ug_id)]",
    )
    quantidade_prevista = fields.Float(string="Quantidade Prevista", default=1.0)
    valor_unit_previsto = fields.Monetary(
        string="Valor Unitário Previsto",
        currency_field="currency_id",
    )
    valor_total_previsto = fields.Monetary(
        string="Valor Total Previsto",
        currency_field="currency_id",
        compute="_compute_valor_total_previsto",
        store=True,
    )
    natureza_despesa = fields.Char(string="Natureza da Despesa")
    justificativa = fields.Text(string="Justificativa")

    _previsao_item_unique = models.Constraint(
        "unique(previsao_id, catalog_item_id)",
        "O item ja existe nesta previsao.",
    )

    @api.depends("quantidade_prevista", "valor_unit_previsto")
    def _compute_valor_total_previsto(self):
        for rec in self:
            rec.valor_total_previsto = (rec.quantidade_prevista or 0.0) * (rec.valor_unit_previsto or 0.0)

    @api.constrains("quantidade_prevista", "valor_unit_previsto")
    def _check_non_negative(self):
        for rec in self:
            if rec.quantidade_prevista and rec.quantidade_prevista < 0:
                raise UserError("Quantidade prevista nao pode ser negativa.")
            if rec.valor_unit_previsto and rec.valor_unit_previsto < 0:
                raise UserError("Valor unitario previsto nao pode ser negativo.")
