from odoo import fields, models


class SifnextAssetCategory(models.Model):
    _name = "sifnext.asset.category"
    _description = "SIFNEXT Asset Category"
    _order = "name"

    name = fields.Char(
        string="Nama Kategori",
        required=True,
    )

    useful_life_years = fields.Integer(
        string="Umur Manfaat (Tahun)",
        required=True,
        default=5,
    )

    depreciation_method = fields.Selection(
        [
            ("straight_line", "Garis Lurus"),
        ],
        string="Metode Penyusutan",
        required=True,
        default="straight_line",
    )

    residual_value = fields.Monetary(
        string="Nilai Residu",
        currency_field="currency_id",
        default=0.0,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Mata Uang",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    active = fields.Boolean(
        string="Aktif",
        default=True,
    )