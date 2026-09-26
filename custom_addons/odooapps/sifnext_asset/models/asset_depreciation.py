from odoo import fields, models
from odoo.exceptions import UserError


class SifnextAssetDepreciation(models.Model):
    _name = "sifnext.asset.depreciation"
    _description = "SIFNEXT Asset Depreciation"
    _order = "depreciation_date, id"

    asset_id = fields.Many2one(
        "sifnext.asset",
        string="Aset",
        required=True,
        ondelete="cascade",
    )

    depreciation_date = fields.Date(
        string="Tanggal Penyusutan",
        required=True,
    )

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

    currency_id = fields.Many2one(
        "res.currency",
        string="Mata Uang",
        related="asset_id.currency_id",
        store=True,
        readonly=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Tercatat"),
        ],
        string="Status",
        default="draft",
        required=True,
    )

    journal_entry_id = fields.Many2one(
        "sif.jurnal.entry",
        string="Jurnal Penyusutan",
        readonly=True,
        copy=False,
    )

    # =====================================================
    # POST PENYUSUTAN
    # =====================================================

    def action_post_depreciation(self):

        for record in self:

            # -------------------------------------------------
            # 1. Validasi schedule
            # -------------------------------------------------

            if record.state != "draft":
                raise UserError(
                    "Penyusutan ini sudah diposting."
                )

            asset = record.asset_id

            if not asset:
                raise UserError(
                    "Aset tidak ditemukan."
                )

            # Aset harus sudah acquired/depreciating
            if asset.state not in (
                "acquired",
                "depreciating",
            ):
                raise UserError(
                    "Aset belum berada pada status "
                    "yang dapat disusutkan."
                )

            # -------------------------------------------------
            # 2. Validasi akun Finance
            # -------------------------------------------------

            if not asset.account_dep_id:
                raise UserError(
                    "Akun Akumulasi Penyusutan belum dipilih."
                )

            if not asset.account_exp_id:
                raise UserError(
                    "Akun Beban Penyusutan belum dipilih."
                )

            if record.depreciation_amount <= 0:
                raise UserError(
                    "Nilai penyusutan harus lebih besar dari 0."
                )

            # -------------------------------------------------
            # 3. Hitung nilai yang dapat disusutkan
            # -------------------------------------------------

            depreciable_value = max(
                asset.acquisition_value
                - asset.residual_value,
                0,
            )

            # -------------------------------------------------
            # 4. Hitung penyusutan yang sudah diposting
            # -------------------------------------------------

            posted_lines = asset.depreciation_ids.filtered(
                lambda line: line.state == "posted"
            )

            posted_before = sum(
                posted_lines.mapped(
                    "depreciation_amount"
                )
            )

            remaining_value = max(
                depreciable_value
                - posted_before,
                0,
            )

            if remaining_value <= 0:
                raise UserError(
                    "Aset sudah mencapai nilai penyusutan maksimal."
                )

            # Jangan sampai penyusutan melebihi nilai yang tersedia
            amount = min(
                record.depreciation_amount,
                remaining_value,
            )

            # -------------------------------------------------
            # 5. Tentukan periode jurnal
            # -------------------------------------------------

            period_date = fields.Date.to_date(
                record.depreciation_date
            )

            period_name = period_date.strftime(
                "%B %Y"
            )

            # -------------------------------------------------
            # 6. Buat Jurnal Penyusutan di Finance
            # -------------------------------------------------

            journal = self.env[
                "sif.jurnal.entry"
            ].create_asset_depreciation_journal(
                asset_name=asset.name,
                asset_code=asset.code,
                amount=amount,
                dep_account_id=asset.account_dep_id.id,
                exp_account_id=asset.account_exp_id.id,
                date=record.depreciation_date,
                period_name=period_name,
                unit_name=asset.owner_unit or "KANTOR",
            )

            # -------------------------------------------------
            # 7. Post schedule
            # -------------------------------------------------

            record.write({
                "depreciation_amount": amount,
                "journal_entry_id": journal.id,
                "state": "posted",
            })

            # -------------------------------------------------
            # 8. Hitung ulang total akumulasi
            # -------------------------------------------------

            posted_lines = asset.depreciation_ids.filtered(
                lambda line: line.state == "posted"
            )

            posted_total = sum(
                posted_lines.mapped(
                    "depreciation_amount"
                )
            )

            posted_total = min(
                posted_total,
                depreciable_value,
            )

            # -------------------------------------------------
            # 9. Update Asset
            # -------------------------------------------------

            asset.accumulated_depreciation = posted_total

            # -------------------------------------------------
            # 10. Update status Asset
            # -------------------------------------------------

            if posted_total >= depreciable_value:
                asset.state = "fully_depreciated"
            else:
                asset.state = "depreciating"

        return True

    # =====================================================
    # PROTECT POSTED DATA
    # =====================================================

    def write(self, vals):

        for record in self:

            if record.state == "posted":

                allowed_fields = {
                    "journal_entry_id",
                }

                changed_fields = (
                    set(vals.keys())
                    - allowed_fields
                )

                if changed_fields:
                    raise UserError(
                        "Penyusutan yang sudah diposting "
                        "tidak dapat diubah."
                    )

        return super().write(vals)

    # =====================================================
    # PROTECT DELETE
    # =====================================================

    def unlink(self):

        for record in self:

            if record.state == "posted":
                raise UserError(
                    "Penyusutan yang sudah diposting "
                    "tidak dapat dihapus."
                )

        return super().unlink()