from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SifnextOperationalRoomBooking(models.Model):
    _name = "sifnext.operational.room.booking"
    _description = "SIFNEXT Room Booking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

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

    room_id = fields.Many2one(
        "sifnext.operational.room",
        string="Ruangan",
        required=True,
        tracking=True,
    )

    purpose = fields.Text(
        string="Keperluan",
        required=True,
    )

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

    participant_count = fields.Integer(
        string="Jumlah Peserta",
    )

    availability = fields.Selection(
        [
            ("available", "Tersedia"),
            ("unavailable", "Tidak Tersedia"),
        ],
        string="Ketersediaan",
        readonly=True,
        tracking=True,
    )

    rejection_reason = fields.Text(
        string="Alasan Penolakan",
    )

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        "sifnext.operational.room.booking"
                    )
                    or "New"
                )
        return super().create(vals_list)

    def action_submit(self):
        for record in self:
            if not record.room_id:
                raise ValidationError(
                    "Silakan pilih ruangan."
                )

            if not record.start_datetime or not record.end_datetime:
                raise ValidationError(
                    "Tanggal dan waktu peminjaman harus diisi."
                )

            if record.end_datetime <= record.start_datetime:
                raise ValidationError(
                    "Waktu selesai harus lebih besar dari waktu mulai."
                )

            if record.participant_count < 0:
                raise ValidationError(
                    "Jumlah peserta tidak boleh negatif."
                )

            if (
                record.room_id.capacity
                and record.participant_count
                > record.room_id.capacity
            ):
                raise ValidationError(
                    "Jumlah peserta melebihi kapasitas ruangan."
                )

            record.state = "submitted"

    def action_check_availability(self):
        for record in self:
            if record.end_datetime <= record.start_datetime:
                raise ValidationError(
                    "Waktu selesai harus lebih besar dari waktu mulai."
                )

            conflict = self.search(
                [
                    ("id", "!=", record.id),
                    ("room_id", "=", record.room_id.id),
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
                record.availability = "unavailable"
                return

            record.availability = "available"
            record.state = "waiting_approval"

    def action_approve(self):
        self.write({
            "state": "approved",
        })

    def action_reject(self):
        self.write({
            "state": "rejected",
        })

    def action_book(self):
        for record in self:
            if record.state != "approved":
                raise ValidationError(
                    "Pengajuan harus Approved sebelum booking jadwal."
                )

            record.state = "booked"

    def action_done(self):
        self.write({
            "state": "done",
        })

    def action_cancel(self):
        self.write({
            "state": "cancelled",
        })

    def action_reset_draft(self):
        self.write({
            "state": "draft",
            "availability": False,
            "rejection_reason": False,
        })