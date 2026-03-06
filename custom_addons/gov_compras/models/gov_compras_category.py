from odoo import api, fields, models


class GovComprasCategory(models.Model):
    _name = "gov.compras.category"
    _description = "Categoria de Itens de Compra"
    _parent_name = "parent_id"
    _parent_store = True
    _rec_name = "name"
    _order = "code, name"

    name = fields.Char(string="Nome", required=True)
    code = fields.Char(string="Código de Classificação")
    parent_id = fields.Many2one(
        "gov.compras.category",
        string="Categoria Pai",
        index=True,
        ondelete="cascade",
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        "gov.compras.category",
        "parent_id",
        string="Sub-Categorias",
    )
    item_ids = fields.One2many(
        "gov.compras.catalog.item",
        "category_id",
        string="Itens",
    )

    @api.depends("name", "parent_id.name")
    def _compute_display_name(self):
        for category in self:
            if category.parent_id:
                category.display_name = f"{category.parent_id.display_name} / {category.name}"
            else:
                category.display_name = category.name
