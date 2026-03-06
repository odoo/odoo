import statistics
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GovComprasItemTrack(models.Model):
    _name = "gov.compras.item.track"
    _description = "Trilha de Item de Compras no Processo"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(
        string="Descrição",
        compute="_compute_name",
        store=True,
    )
    track_id = fields.Char(
        string="ID de Rastreio",
        required=True,
        readonly=True,
        copy=False,
        default="Novo",
        index=True,
    )
    processo_id = fields.Many2one(
        "gov.processo",
        string="Processo",
        required=True,
        ondelete="cascade",
        index=True,
    )
    ug_id = fields.Many2one(
        "res.company",
        related="processo_id.ug_id",
        store=True,
        readonly=True,
    )
    catalog_item_id = fields.Many2one(
        "gov.compras.catalog.item",
        string="Item do Catálogo",
        required=True,
        domain="[('ug_ids', 'in', ug_id)]",
    )
    descricao = fields.Text(string="Descrição da Demanda")
    unidade_medida = fields.Char(string="Unidade", default="UN")
    quantidade = fields.Float(string="Quantidade", default=1.0)
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
    )
    valor_etp = fields.Monetary(string="Valor no ETP", currency_field="currency_id")
    valor_estimado_ref = fields.Monetary(
        string="Valor de Referência",
        currency_field="currency_id",
        help="Valor estimado com base no banco de preços e histórico.",
    )
    valor_arrematado = fields.Monetary(
        string="Valor Arrematado",
        currency_field="currency_id",
        help="Valor final da contratação que deve limitar o empenho.",
    )
    fornecedor_arrematado = fields.Char(string="Licitante/Fornecedor")
    data_arremate = fields.Date(string="Data do Arremate")
    status = fields.Selection(
        [
            ("rascunho", "Rascunho"),
            ("requisitado", "Requisição"),
            ("nad", "NAD"),
            ("licitado", "Licitado"),
            ("empenhado", "Empenhado"),
            ("encerrado", "Encerrado"),
        ],
        string="Etapa",
        default="rascunho",
        tracking=True,
    )
    empenho_id = fields.Many2one(
        "gov.empenho",
        string="Empenho Vinculado",
        ondelete="set null",
    )

    media_preco_historico = fields.Monetary(
        string="Média Histórica",
        currency_field="currency_id",
        compute="_compute_indicadores",
    )
    media_preco_sazonal = fields.Monetary(
        string="Média Sazonal",
        currency_field="currency_id",
        compute="_compute_indicadores",
    )
    preco_referencia_conservador = fields.Monetary(
        string="Preço Conservador",
        currency_field="currency_id",
        compute="_compute_indicadores",
    )
    media_qtd_historica = fields.Float(string="Qtd. Média Histórica", compute="_compute_indicadores")

    _track_id_unique = models.Constraint(
        "unique(track_id)",
        "ID de rastreio ja existente.",
    )

    @api.depends("catalog_item_id", "quantidade")
    def _compute_name(self):
        for rec in self:
            item = rec.catalog_item_id.name or "Item"
            rec.name = f"{item} ({rec.quantidade:g} {rec.unidade_medida or 'UN'})"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("track_id", "Novo") == "Novo":
                vals["track_id"] = self.env["ir.sequence"].next_by_code("gov.compras.item.track") or "Novo"
        return super().create(vals_list)

    @api.depends("catalog_item_id", "ug_id")
    def _compute_indicadores(self):
        for rec in self:
            metrics = self.get_conservative_metrics(rec.ug_id.id, rec.catalog_item_id.id) if rec.catalog_item_id else {}
            rec.media_preco_historico = metrics.get("avg_price", 0.0)
            rec.media_preco_sazonal = metrics.get("seasonal_price", 0.0)
            rec.preco_referencia_conservador = metrics.get("conservative_price", 0.0)
            rec.media_qtd_historica = metrics.get("avg_qty", 0.0)

    @api.model
    def get_conservative_metrics(self, ug_id, catalog_item_id):
        if not ug_id or not catalog_item_id:
            return {
                "avg_price": 0.0,
                "seasonal_price": 0.0,
                "conservative_price": 0.0,
                "avg_qty": 0.0,
            }

        domain = [
            ("ug_id", "=", ug_id),
            ("catalog_item_id", "=", catalog_item_id),
            ("status", "in", ("licitado", "empenhado", "encerrado")),
        ]
        records = self.search(domain, limit=240, order="data_arremate desc, id desc")
        prices = [
            (r.valor_arrematado or r.valor_estimado_ref or r.valor_etp)
            for r in records
            if (r.valor_arrematado or r.valor_estimado_ref or r.valor_etp) > 0
        ]
        qtys = [r.quantidade for r in records if r.quantidade > 0]

        if not prices:
            return {
                "avg_price": 0.0,
                "seasonal_price": 0.0,
                "conservative_price": 0.0,
                "avg_qty": statistics.mean(qtys) if qtys else 0.0,
            }

        avg_price = statistics.mean(prices)
        median_price = statistics.median(prices)
        current_month = fields.Date.context_today(self).month if isinstance(fields.Date.context_today(self), date) else date.today().month
        seasonal_prices = [
            (r.valor_arrematado or r.valor_estimado_ref or r.valor_etp)
            for r in records
            if r.data_arremate and r.data_arremate.month == current_month and (r.valor_arrematado or r.valor_estimado_ref or r.valor_etp) > 0
        ]
        seasonal_price = statistics.mean(seasonal_prices) if seasonal_prices else avg_price
        conservative_price = max(avg_price, median_price, seasonal_price)
        avg_qty = statistics.mean(qtys) if qtys else 0.0

        return {
            "avg_price": avg_price,
            "seasonal_price": seasonal_price,
            "conservative_price": conservative_price,
            "avg_qty": avg_qty,
        }

    @api.onchange("catalog_item_id")
    def _onchange_catalog_item_id(self):
        for rec in self:
            item = rec.catalog_item_id
            if not item:
                continue
            rec.unidade_medida = item.uom_id.name if item.uom_id else rec.unidade_medida
            rec.descricao = rec.descricao or item.descricao
            if not rec.valor_estimado_ref:
                metrics = self.get_conservative_metrics(rec.ug_id.id, item.id)
                rec.valor_estimado_ref = metrics.get("conservative_price", 0.0)

    @api.constrains("valor_arrematado", "valor_estimado_ref", "valor_etp")
    def _check_values(self):
        for rec in self:
            for value in (rec.valor_etp, rec.valor_estimado_ref, rec.valor_arrematado):
                if value and value < 0:
                    raise ValidationError("Valores monetarios do item nao podem ser negativos.")
            if rec.quantidade and rec.quantidade < 0:
                raise ValidationError("Quantidade do item nao pode ser negativa.")
