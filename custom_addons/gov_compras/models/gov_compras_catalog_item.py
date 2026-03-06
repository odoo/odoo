from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GovComprasCatalogItem(models.Model):
    _name = "gov.compras.catalog.item"
    _description = "Catálogo de Itens de Compras por UG"
    _order = "name asc, id asc"

    name = fields.Char(string="Item", required=True)
    code = fields.Char(string="Código Interno", required=True)
    ug_ids = fields.Many2many(
        "res.company",
        string="Unidades Gestoras Permitidas",
        help="UGs que possuem acesso a este item.",
    )
    category_id = fields.Many2one("gov.compras.category", string="Categoria", index=True)
    natureza_despesa_id = fields.Many2one(
        "gov.account.config",
        string="Natureza da Despesa",
        required=True,
    )
    uom_id = fields.Many2one(
        "uom.uom",
        string="Unidade de Medida",
        required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit", raise_if_not_found=False).id if self.env.ref("uom.product_uom_unit", raise_if_not_found=False) else False
    )
    descricao = fields.Text(string="Descrição Técnica")
    ativo_previsao = fields.Boolean(
        string="Ativo para Previsão",
        default=True,
        help="Quando ativo, o item entra no cálculo de previsão orçamentária anual.",
    )
    active = fields.Boolean(default=True)

    _code_unique = models.Constraint(
        "unique(code)",
        "Ja existe um item no Catálogo Geral com este código.",
    )

    @api.constrains("code")
    def _check_code(self):
        for rec in self:
            if not (rec.code or "").strip():
                raise ValidationError("Código do item não pode ser vazio.")

    def action_add_to_my_ug(self):
        for rec in self:
            rec.ug_ids = [(4, self.env.company.id)]
