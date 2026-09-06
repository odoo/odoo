from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SifnextOperationalVehicleBooking(models.Model):
    _name = "sifnext.operational.vehicle.booking"
    _description = "SIFNEXT Vehicle Booking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    # =========================================================
    # INFORMASI PENGAJUAN
    # =========================================================

    name = fields.Char(
        string="Nomor Pengajuan",
        required=True,
        readonly=True,
        copy=False,
        default="New",
        tracking=True,
    )

    applicant_id = fields.Many2one(
        "res.users",
        string="Pemohon",
        required=True,
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )

    vehicle_id = fields.Many2one(
        "sifnext.operational.vehicle",
        string="Kendaraan",
        required=True,
        tracking=True,
    )

    purpose = fields.Text(
        string="Keperluan",
        required=True,
    )

    destination = fields.Char(
        string="Tujuan",
        required=True,
    )

    # =========================================================
    # JADWAL
    # =========================================================

    start_datetime = fields.Datetime(
        string="Mulai",
        required=True,
        tracking=True,
    )

    end_datetime = fields.Datetime(
        string="Selesai",
        required=True,
        tracking=True,
    )

    passenger_count = fields.Integer(
        string="Jumlah Penumpang",
        default=0,
    )

    # =========================================================
    # KETERSEDIAAN
    # =========================================================

    availability = fields.Selection(
        [
            ("available", "Tersedia"),
            ("unavailable", "Tidak Tersedia"),
        ],
        string="Ketersediaan",
        readonly=True,
        tracking=True,
    )

    # =========================================================
    # APPROVAL
    # =========================================================

    rejection_reason = fields.Text(
        string="Alasan Penolakan",
        tracking=True,
    )

    # =========================================================
    # STATUS
    # =========================================================

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Diajukan"),
            ("waiting_approval", "Menunggu Approval GA"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("booked", "Booked"),
            ("done", "Selesai"),
            ("cancelled", "Dibatalkan"),
        ],
        string="Status",
        default="draft",
        required=True,
        tracking=True,
    )

    # =========================================================
    # ACTIVE ROLE
    # =========================================================

    sifnext_active_role = fields.Selection(
        [
            ("user", "Operational User"),
            ("ga", "General Affair"),
        ],
        string="SIFNEXT Active Role",
        compute="_compute_sifnext_active_role",
    )

    @api.depends_context("uid")
    def _compute_sifnext_active_role(self):
        for record in self:
            record.sifnext_active_role = self.env.user.sifnext_active_role

    # =========================================================
    # CREATE
    # =========================================================

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "sifnext.operational.vehicle.booking"
                    )
                    or "New"
                )

        return super().create(vals_list)

    # =========================================================
    # AJUKAN PEMINJAMAN
    # =========================================================

    def action_submit(self):
        for record in self:

            if record.state != "draft":
                raise ValidationError(
                    "Pengajuan hanya dapat diajukan dari status Draft."
                )

            if not record.vehicle_id:
                raise ValidationError(
                    "Silakan pilih kendaraan."
                )

            if not record.destination:
                raise ValidationError(
                    "Tujuan perjalanan harus diisi."
                )

            if not record.start_datetime or not record.end_datetime:
                raise ValidationError(
                    "Tanggal dan waktu peminjaman harus diisi."
                )

            if record.end_datetime <= record.start_datetime:
                raise ValidationError(
                    "Waktu selesai harus lebih besar dari waktu mulai."
                )

            if record.passenger_count < 0:
                raise ValidationError(
                    "Jumlah penumpang tidak boleh negatif."
                )

            if (
                record.vehicle_id.capacity
                and record.passenger_count > record.vehicle_id.capacity
            ):
                raise ValidationError(
                    "Jumlah penumpang melebihi kapasitas kendaraan."
                )

            record.write(
                {
                    "state": "submitted",
                    "availability": False,
                    "rejection_reason": False,
                }
            )

    # =========================================================
    # CEK KETERSEDIAAN
    # =========================================================

    def action_check_availability(self):
        for record in self:

            if record.state not in ["submitted", "draft"]:
                raise ValidationError(
                    "Cek ketersediaan hanya dapat dilakukan pada "
                    "pengajuan yang belum diproses."
                )

            if not record.vehicle_id:
                raise ValidationError(
                    "Silakan pilih kendaraan."
                )

            if not record.start_datetime or not record.end_datetime:
                raise ValidationError(
                    "Tanggal dan waktu peminjaman harus diisi."
                )

            if record.end_datetime <= record.start_datetime:
                raise ValidationError(
                    "Waktu selesai harus lebih besar dari waktu mulai."
                )

            conflict = self.search(
                [
                    ("id", "!=", record.id),
                    ("vehicle_id", "=", record.vehicle_id.id),
                    (
                        "state",
                        "in",
                        [
                            "submitted",
                            "waiting_approval",
                            "approved",
                            "booked",
                        ],
                    ),
                    ("start_datetime", "<", record.end_datetime),
                    ("end_datetime", ">", record.start_datetime),
                ],
                limit=1,
            )

            if conflict:
                record.write(
                    {
                        "availability": "unavailable",
                    }
                )

                raise ValidationError(
                    "Kendaraan tidak tersedia pada jadwal tersebut."
                )

            record.write(
                {
                    "availability": "available",
                    "state": "waiting_approval",
                }
            )

    # =========================================================
    # APPROVAL GA
    # =========================================================

    def action_approve(self):
        for record in self:

            # Pastikan akun memiliki privilege General Affair
            if not record.env.user.has_group(
                "sifnext_operational.group_sifnext_operational_ga"
            ):
                raise ValidationError(
                    "Akun ini tidak memiliki role General Affair."
                )

            # Pastikan role aktif adalah General Affair
            if record.env.user.sifnext_active_role != "ga":
                raise ValidationError(
                    "Silakan aktifkan role General Affair terlebih dahulu."
                )

            if record.state != "waiting_approval":
                raise ValidationError(
                    "Pengajuan harus berada pada status "
                    "Menunggu Approval GA."
                )

            if record.availability != "available":
                raise ValidationError(
                    "Kendaraan belum dinyatakan tersedia."
                )

            record.write(
                {
                    "state": "approved",
                    "rejection_reason": False,
                }
            )

    # =========================================================
    # REJECT GA
    # =========================================================

    def action_reject(self):
        for record in self:

            # Pastikan akun memiliki privilege General Affair
            if not record.env.user.has_group(
                "sifnext_operational.group_sifnext_operational_ga"
            ):
                raise ValidationError(
                    "Akun ini tidak memiliki role General Affair."
                )

            # Pastikan role aktif adalah General Affair
            if record.env.user.sifnext_active_role != "ga":
                raise ValidationError(
                    "Silakan aktifkan role General Affair terlebih dahulu."
                )

            if record.state != "waiting_approval":
                raise ValidationError(
                    "Pengajuan harus berada pada status "
                    "Menunggu Approval GA."
                )

            if not record.rejection_reason:
                raise ValidationError(
                    "Alasan penolakan wajib diisi."
                )

            record.write(
                {
                    "state": "rejected",
                }
            )

    # =========================================================
    # BOOKING JADWAL
    # =========================================================

    def action_book(self):
        for record in self:

            if record.state != "approved":
                raise ValidationError(
                    "Pengajuan harus Approved sebelum booking jadwal."
                )

            if record.availability != "available":
                raise ValidationError(
                    "Kendaraan tidak tersedia untuk jadwal ini."
                )

            # Cek ulang agar tidak terjadi double booking
            conflict = self.search(
                [
                    ("id", "!=", record.id),
                    ("vehicle_id", "=", record.vehicle_id.id),
                    (
                        "state",
                        "in",
                        [
                            "approved",
                            "booked",
                        ],
                    ),
                    ("start_datetime", "<", record.end_datetime),
                    ("end_datetime", ">", record.start_datetime),
                ],
                limit=1,
            )

            if conflict:
                raise ValidationError(
                    "Kendaraan sudah digunakan pada jadwal tersebut."
                )

            record.write(
                {
                    "state": "booked",
                }
            )

    # =========================================================
    # SELESAI
    # =========================================================

    def action_done(self):
        for record in self:

            if record.state != "booked":
                raise ValidationError(
                    "Pengajuan harus berstatus Booked "
                    "sebelum dinyatakan selesai."
                )

            record.write(
                {
                    "state": "done",
                }
            )

    # =========================================================
    # BATAL
    # =========================================================

    def action_cancel(self):
        for record in self:

            if record.state in ["done", "cancelled"]:
                raise ValidationError(
                    "Pengajuan yang sudah selesai atau dibatalkan "
                    "tidak dapat dibatalkan lagi."
                )

            record.write(
                {
                    "state": "cancelled",
                }
            )

    # =========================================================
    # KEMBALI KE DRAFT
    # =========================================================

    def action_reset_draft(self):
        for record in self:

            record.write(
                {
                    "state": "draft",
                    "availability": False,
                    "rejection_reason": False,
                }
            )