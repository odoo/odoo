from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_hr_kpd_category_id = fields.Many2one(
        comodel_name="l10n_hr.kpd.category",
        string="KPD category",
    )


class L10nHrKpdCategory(models.Model):
    _name = "l10n_hr.kpd.category"
    _description = "Croatian KPD Category"
    _rec_names_search = ["name", "description"]

    name = fields.Char(
        string="Code",
        required=True,
    )
    sector = fields.Char(string="Industry")
    description = fields.Char()

    @api.depends("name", "description")
    def _compute_display_name(self):
        for category in self:
            category.display_name = f"[{category.name}] {category.description}"


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_import_product_classification_specs(self):
        return super()._get_import_product_classification_specs() + [
            {
                "value_key": "cg_item_classification_code",
                "field": "l10n_hr_kpd_category_id",
                "comodel": "l10n_hr.kpd.category",
                "code_field": "name",
            },
        ]
