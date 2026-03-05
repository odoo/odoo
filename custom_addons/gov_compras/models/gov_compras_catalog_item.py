from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GovComprasCatalogItem(models.Model):
    _name = "gov.compras.catalog.item"
    _description = "Catálogo de Itens de Compras por UG"
    _order = "name asc, id asc"

    name = fields.Char(string="Item", required=True)
    code = fields.Char(string="Código Interno", required=True)
    ug_id = fields.Many2one(
        "res.company",
        string="Unidade Gestora",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    categoria = fields.Char(string="Categoria")
    natureza_despesa = fields.Char(string="Natureza da Despesa")
    unidade_medida = fields.Char(string="Unidade de Medida", default="UN")
    descricao = fields.Text(string="Descrição Técnica")
    ativo_previsao = fields.Boolean(
        string="Ativo para Previsão",
        default=True,
        help="Quando ativo, o item entra no cálculo de previsão orçamentária anual.",
    )
    active = fields.Boolean(default=True)

    _code_ug_unique = models.Constraint(
        "unique(code, ug_id)",
        "Ja existe item com este codigo para a UG informada.",
    )

    @api.constrains("code")
    def _check_code(self):
        for rec in self:
            if not (rec.code or "").strip():
                raise ValidationError("Código do item não pode ser vazio.")
