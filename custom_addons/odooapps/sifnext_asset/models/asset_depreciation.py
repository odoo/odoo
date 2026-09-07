from odoo import fields, models


class SifnextAssetDepreciation(models.Model):
    _name = "sifnext.asset.depreciation"
    _description = "SIFNEXT Asset Depreciation"
    _order = "depreciation_date, id"

    # =====================================================
    # ASSET
    # =====================================================

    asset_id = fields.Many2one(
        "sifnext.asset",
        string="Aset",
        required=True,
        ondelete="cascade",
    )

    # =====================================================
    # TANGGAL
    # =====================================================

    depreciation_date = fields.Date(
        string="Tanggal Penyusutan",
        required=True,
    )

    # =====================================================
    # NILAI PENYUSUTAN
    # =====================================================

    depreciation_amount = fields.Monetary(
        string="Penyusutan",
        required=True,
        currency_field="currency_id",
    )

    accumulated_depreciation = fields.Monetary(
        string="Akumulasi Penyusutan",
        required=True,
        currency_field="currency_id",
    )

    book_value = fields.Monetary(
        string="Nilai Buku",
        required=True,
        currency_field="currency_id",
    )

    # =====================================================
    # CURRENCY
    # =====================================================

    currency_id = fields.Many2one(
        "res.currency",
        string="Mata Uang",
        related="asset_id.currency_id",
        store=True,
        readonly=True,
    )

    # =====================================================
    # STATUS
    # =====================================================

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Tercatat"),
        ],
        string="Status",
        default="draft",
        required=True,
    )