from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SifnextAsset(models.Model):
    _name = "sifnext.asset"
    _description = "SIFNEXT Asset"
    _order = "id desc"

    # =====================================================
    # IDENTITAS ASET
    # =====================================================

    name = fields.Char(
        string="Nama Aset",
        required=True,
    )

    code = fields.Char(
        string="Kode Aset",
        required=True,
        copy=False,
        readonly=True,
        default="New",
    )

    category_id = fields.Many2one(
        "sifnext.asset.category",
        string="Kategori Aset",
        required=True,
        ondelete="restrict",
    )

    owner_unit = fields.Char(
        string="Unit Pemilik",
        required=True,
    )

    project_code = fields.Char(
        string="Kode Proyek",
        required=True,
        default="000",
    )

    reference = fields.Char(
        string="Referensi Dokumen",
    )

    # =====================================================
    # INFORMASI PEROLEHAN
    # =====================================================

    acquisition_date = fields.Date(
        string="Tanggal Perolehan",
        required=True,
        default=fields.Date.context_today,
    )

    acquisition_value = fields.Monetary(
        string="Nilai Perolehan",
        required=True,
        currency_field="currency_id",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Mata Uang",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    # =====================================================
    # PENYUSUTAN
    # =====================================================

    depreciation_start_date = fields.Date(
        string="Mulai Penyusutan",
        required=True,
        default=fields.Date.context_today,
    )

    useful_life_years = fields.Integer(
        string="Umur Manfaat (Tahun)",
        related="category_id.useful_life_years",
        readonly=True,
    )

    depreciation_method = fields.Selection(
        related="category_id.depreciation_method",
        string="Metode Penyusutan",
        readonly=True,
    )

    residual_value = fields.Monetary(
        string="Nilai Residu",
        currency_field="currency_id",
        default=0.0,
    )

    useful_life_months = fields.Integer(
        string="Umur Manfaat (Bulan)",
        compute="_compute_depreciation",
        store=True,
    )

    depreciation_amount = fields.Monetary(
        string="Penyusutan per Bulan",
        currency_field="currency_id",
        compute="_compute_depreciation",
        store=True,
    )

    accumulated_depreciation = fields.Monetary(
        string="Akumulasi Penyusutan",
        currency_field="currency_id",
        default=0.0,
    )

    book_value = fields.Monetary(
        string="Nilai Buku",
        currency_field="currency_id",
        compute="_compute_book_value",
        store=True,
    )

    # =====================================================
    # JADWAL PENYUSUTAN
    # =====================================================

    depreciation_ids = fields.One2many(
        "sifnext.asset.depreciation",
        "asset_id",
        string="Jadwal Penyusutan",
    )

    # =====================================================
    # STATUS
    # =====================================================

    active = fields.Boolean(
        string="Aktif",
        default=True,
    )

    # =====================================================
    # COMPUTE PENYUSUTAN
    # =====================================================

    @api.depends(
        "acquisition_value",
        "residual_value",
        "category_id",
        "category_id.useful_life_years",
    )
    def _compute_depreciation(self):
        for record in self:

            years = record.category_id.useful_life_years or 0
            months = years * 12

            record.useful_life_months = months

            if months > 0:

                depreciable_value = (
                    record.acquisition_value
                    - record.residual_value
                )

                record.depreciation_amount = max(
                    depreciable_value / months,
                    0,
                )

            else:
                record.depreciation_amount = 0.0

    # =====================================================
    # COMPUTE NILAI BUKU
    # =====================================================

    @api.depends(
        "acquisition_value",
        "accumulated_depreciation",
    )
    def _compute_book_value(self):
        for record in self:

            record.book_value = max(
                record.acquisition_value
                - record.accumulated_depreciation,
                0,
            )

    # =====================================================
    # VALIDASI
    # =====================================================

    @api.constrains(
        "acquisition_value",
        "residual_value",
        "accumulated_depreciation",
    )
    def _check_values(self):

        for record in self:

            if record.acquisition_value < 0:
                raise ValidationError(
                    "Nilai perolehan tidak boleh kurang dari 0."
                )

            if record.residual_value < 0:
                raise ValidationError(
                    "Nilai residu tidak boleh kurang dari 0."
                )

            if record.residual_value > record.acquisition_value:
                raise ValidationError(
                    "Nilai residu tidak boleh lebih besar "
                    "dari nilai perolehan."
                )

            if record.accumulated_depreciation < 0:
                raise ValidationError(
                    "Akumulasi penyusutan tidak boleh kurang dari 0."
                )

            if record.accumulated_depreciation > (
                record.acquisition_value
                - record.residual_value
            ):
                raise ValidationError(
                    "Akumulasi penyusutan tidak boleh melebihi "
                    "nilai yang dapat disusutkan."
                )

    # =====================================================
    # AUTO GENERATE KODE ASET
    # =====================================================

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            if vals.get("code", "New") == "New":

                vals["code"] = (
                    self.env["ir.sequence"].next_by_code(
                        "sifnext.asset"
                    )
                    or "New"
                )

        records = super().create(vals_list)

        # Generate jadwal penyusutan otomatis
        for record in records:
            record._generate_depreciation_schedule()

        return records

    # =====================================================
    # UPDATE ASSET
    # =====================================================

    def write(self, vals):

        schedule_fields = {
            "category_id",
            "acquisition_value",
            "residual_value",
            "depreciation_start_date",
        }

        regenerate_schedule = bool(
            schedule_fields.intersection(vals.keys())
        )

        result = super().write(vals)

        if regenerate_schedule:

            for record in self:
                record._generate_depreciation_schedule()

        return result

    # =====================================================
    # GENERATE JADWAL PENYUSUTAN
    # =====================================================

    def _generate_depreciation_schedule(self):

        Depreciation = self.env["sifnext.asset.depreciation"]

        for record in self:

            # Hapus jadwal lama
            record.depreciation_ids.unlink()

            months = record.useful_life_months

            if (
                not record.depreciation_start_date
                or months <= 0
                or record.depreciation_amount <= 0
            ):
                continue

            depreciation_amount = record.depreciation_amount

            depreciable_value = max(
                record.acquisition_value
                - record.residual_value,
                0,
            )

            accumulated = 0.0

            # Penyusutan dimulai bulan berikutnya
            first_month = (
                fields.Date.to_date(
                    record.depreciation_start_date
                ).replace(day=1)
                + relativedelta(months=1)
            )

            schedule_values = []

            for month_index in range(months):

                depreciation_date = (
                    first_month
                    + relativedelta(months=month_index + 1)
                    - relativedelta(days=1)
                )

                # Pastikan penyusutan terakhir tidak
                # melebihi nilai yang dapat disusutkan
                remaining_value = (
                    depreciable_value
                    - accumulated
                )

                current_depreciation = min(
                    depreciation_amount,
                    max(remaining_value, 0),
                )

                accumulated += current_depreciation

                book_value = max(
                    record.acquisition_value
                    - accumulated,
                    record.residual_value,
                )

                schedule_values.append({
                    "asset_id": record.id,
                    "depreciation_date": depreciation_date,
                    "depreciation_amount": current_depreciation,
                    "accumulated_depreciation": accumulated,
                    "book_value": book_value,
                    "state": "draft",
                })

            if schedule_values:
                Depreciation.create(schedule_values)

    # =====================================================
    # MANUAL REGENERATE SCHEDULE
    # =====================================================

    def action_generate_depreciation_schedule(self):

        for record in self:
            record._generate_depreciation_schedule()

        return True

    # =====================================================
    # ARCHIVE / UNARCHIVE
    # =====================================================

    def toggle_active(self):

        for record in self:
            record.active = not record.active