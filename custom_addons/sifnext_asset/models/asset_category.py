from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class SifnextAssetCategory(models.Model):
    _name = "sifnext.asset.category"
    _description = "SIFNEXT Asset Category"
    _order = "name"

    def _check_finance_central_readonly(self):
        if self.env.user.has_group("sif_keuangan.group_sif_keuangan_central_readonly"):
            raise AccessError(_("Finance pusat memiliki akses baca saja pada kategori aset."))

    @api.model_create_multi
    def create(self, vals_list):
        self._check_finance_central_readonly()
        return super().create(vals_list)

    def write(self, vals):
        self._check_finance_central_readonly()
        return super().write(vals)

    def unlink(self):
        self._check_finance_central_readonly()
        return super().unlink()

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
