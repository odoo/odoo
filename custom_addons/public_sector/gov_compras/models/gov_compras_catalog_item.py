from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GovComprasCatalogItem(models.Model):
    _name = "gov.compras.catalog.item"
    _description = "Catálogo de Itens de Compras por UG"
    _order = "code asc, name asc, id asc"

    name = fields.Char(string="Item", required=True)
    code = fields.Char(
        string="Código Interno",
        required=True,
        readonly=True,
        copy=False,
        default="Novo",
        index=True,
    )
    external_code = fields.Char(
        string="ID Externo",
        index=True,
        copy=False,
        help="Identificador original do item importado para o catálogo geral.",
    )
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
    _external_code_unique = models.Constraint(
        "unique(external_code)",
        "Ja existe um item no Catálogo Geral com este ID externo.",
    )

    @api.model
    def _next_internal_code(self):
        return self.env["ir.sequence"].next_by_code("gov.compras.catalog.item.code") or "Novo"

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = []
        for vals in vals_list:
            prepared_vals = dict(vals)
            prepared_vals["name"] = (prepared_vals.get("name") or "").strip()

            code = (prepared_vals.get("code") or "").strip()
            if not code or code == "Novo":
                prepared_vals["code"] = self._next_internal_code()
            else:
                prepared_vals["code"] = code

            if "external_code" in prepared_vals:
                prepared_vals["external_code"] = (prepared_vals.get("external_code") or "").strip() or False

            prepared_vals_list.append(prepared_vals)

        return super().create(prepared_vals_list)

    def write(self, vals):
        prepared_vals = dict(vals)
        if "name" in prepared_vals:
            prepared_vals["name"] = (prepared_vals.get("name") or "").strip()
        if "external_code" in prepared_vals:
            prepared_vals["external_code"] = (prepared_vals.get("external_code") or "").strip() or False
        if "code" in prepared_vals and not self.env.context.get("allow_catalog_code_write"):
            prepared_vals.pop("code")
        elif "code" in prepared_vals:
            prepared_vals["code"] = (prepared_vals.get("code") or "").strip()
        return super().write(prepared_vals)

    @api.constrains("code", "external_code", "name")
    def _check_codes(self):
        for rec in self:
            if not (rec.code or "").strip():
                raise ValidationError("Código interno do item nao pode ser vazio.")
            if rec.external_code is not False and not (rec.external_code or "").strip():
                raise ValidationError("ID externo do item nao pode ser vazio.")
            if not (rec.name or "").strip():
                raise ValidationError("Nome do item nao pode ser vazio.")

    def action_add_to_my_ug(self):
        for rec in self:
            rec.ug_ids = [(4, self.env.company.id)]
