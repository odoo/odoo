# -*- coding: utf-8 -*-
from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class TransaksiTransaction(models.Model):
    _name = "transaksi.transaction"
    _description = "Dokumen Transaksi Mutasi Rekening"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    def _check_finance_central_readonly(self):
        if self.env.user.has_group("sif_keuangan.group_sif_keuangan_central_readonly"):
            raise AccessError(_("Finance pusat memiliki akses baca saja pada transaksi bank."))

    name = fields.Char(
        string="Nomor Transaksi",
        default="New",
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    transfer_type = fields.Selection(
        [
            ("single", "Transfer Tunggal"),
            ("multiple", "Transfer Massal"),
        ],
        string="Tipe Transfer",
        default="single",
        required=True,
        tracking=True,
    )
    transfer_category = fields.Selection(
        [
            ("inhouse", "Mutasi Antar Rekening"),
            ("interbank", "Mutasi Antar Bank"),
        ],
        string="Kategori Mutasi",
        default="inhouse",
        required=True,
        tracking=True,
    )
    sender_account_id = fields.Many2one(
        "transaksi.bank.account",
        string="Rekening Pengirim",
        tracking=True,
        help="Rekening bank pengirim dari Data Rekening.",
    )
    sender_bank_name = fields.Char(
        string="Bank Pengirim",
        related="sender_account_id.bank_name",
        store=True,
        readonly=True,
    )
    sender_account_number = fields.Char(
        string="No Rekening Pengirim",
        related="sender_account_id.account_number",
        store=True,
        readonly=True,
    )
    sender_account_holder = fields.Char(
        string="Nama Pemilik Rekening Pengirim",
        related="sender_account_id.account_holder",
        store=True,
        readonly=True,
    )
    @api.model
    def _default_submission_time(self):
        return fields.Datetime.context_timestamp(self, fields.Datetime.now()).strftime("%H:%M")

    date = fields.Date(
        string="Tanggal Pengajuan",
        default=fields.Date.context_today,
        required=True,
        tracking=True,
    )
    submission_time = fields.Char(
        string="Jam Pengajuan",
        default=_default_submission_time,
        size=5,
        required=True,
        tracking=True,
        help="Jam pengajuan transaksi (format HH:MM).",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Pemohon",
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
        tracking=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Departemen",
        default=lambda self: self.env.user.department_id,
        tracking=True,
        domain="[('company_id', '=', company_id)]",
        check_company=True,
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Perusahaan",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )

    @api.onchange("company_id", "ppl_id", "ppl_ids")
    def _onchange_organization_scope(self):
        for record in self:
            linked_ppls = record.ppl_id | record.ppl_ids
            if linked_ppls:
                companies = linked_ppls.mapped("company_id")
                if len(companies) == 1:
                    record.company_id = companies
                departments = linked_ppls.mapped("department_id")
                record.department_id = departments if len(departments) == 1 else False
            elif record.department_id and record.department_id.company_id != record.company_id:
                record.department_id = False

    # Sumber Dana disimpan opsional di model untuk fase berikutnya, disembunyikan dari tampilan
    source_account_id = fields.Many2one(
        "sif.coa",
        string="Sumber Dana (Opsional)",
        required=False,
        tracking=False,
        domain="[('active', '=', True), ('account_type', '=', 'asset')]",
        help="Rekening sumber dana (Kas & Bank).",
    )
    source_account_number = fields.Char(
        string="Nomor Rekening Sumber",
        compute="_compute_source_account_number",
        store=True,
        readonly=True,
        required=False,
    )

    charge_to = fields.Selection(
        [
            ("our", "Ditanggung Pengirim (OUR)"),
            ("ben", "Ditanggung Penerima (BEN)"),
        ],
        string="Beban Biaya Transfer",
        default="our",
        required=True,
        tracking=True,
    )
    purpose = fields.Selection(
        [
            ("operational", "Operasional"),
            ("purchase", "Pembelian"),
            ("salary", "Gaji"),
            ("other", "Lainnya"),
        ],
        string="Tujuan Transaksi",
        required=True,
        default="operational",
        tracking=True,
    )
    ref_number = fields.Char(
        string="Referensi Transaksi",
        size=19,
        tracking=True,
        help="Catatan yang muncul di rekening koran (maksimal 19 karakter).",
    )
    remark = fields.Char(
        string="Catatan Transaksi",
        size=200,
        tracking=True,
        help="Catatan internal transaksi (maksimal 200 karakter).",
    )
    email_notification = fields.Char(
        string="Notifikasi Email",
        tracking=True,
        help="Email tujuan notifikasi, dipisah koma (opsional).",
    )
    sms_notification = fields.Char(
        string="Notifikasi SMS",
        tracking=True,
        help="Nomor telepon tujuan notifikasi SMS, dipisah koma (opsional).",
    )
    execution_time = fields.Selection(
        [
            ("immediate", "Langsung / Sekarang"),
            ("scheduled", "Terjadwal"),
        ],
        string="Waktu Pelaksanaan",
        default="immediate",
        required=True,
        tracking=True,
    )
    scheduled_date = fields.Datetime(
        string="Tanggal Pelaksanaan Terjadwal",
        tracking=True,
    )

    @api.model
    def _default_currency_id(self):
        idr = self.env.ref("base.IDR", raise_if_not_found=False)
        if idr:
            if not idr.active:
                idr.sudo().write({"active": True})
            return idr.id
        return self.env.company.currency_id.id

    currency_id = fields.Many2one(
        "res.currency",
        string="Mata Uang",
        default=_default_currency_id,
        required=True,
    )

    # Penamaan amount diubah menjadi rupiah
    total_rupiah = fields.Monetary(
        string="Total Rupiah",
        currency_field="currency_id",
        compute="_compute_total_rupiah",
        store=True,
        tracking=True,
    )

    attachment_ids = fields.Many2many(
        "ir.attachment",
        "transaksi_transaction_attachment_rel",
        "transaction_id",
        "attachment_id",
        string="Dokumen Lampiran",
        help="Bukti memo atau dokumen persetujuan fisik.",
    )
    state = fields.Selection(
        [
            ("draft", "Draf"),
            ("submitted", "Diajukan"),
            ("verified", "Diverifikasi Keuangan"),
            ("approved", "Disetujui Direktur"),
            ("rejected", "Ditolak"),
            ("failed", "Gagal"),
        ],
        string="Status",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
        index=True,
    )
    reject_reason = fields.Text(
        string="Alasan Penolakan",
        readonly=True,
        copy=False,
        tracking=True,
    )
    submitted_at = fields.Datetime(
        string="Waktu Pengajuan",
        readonly=True,
        copy=False,
        tracking=True,
    )
    verified_by = fields.Many2one(
        "res.users",
        string="Diverifikasi Oleh",
        readonly=True,
        copy=False,
        tracking=True,
    )
    verified_at = fields.Datetime(
        string="Waktu Verifikasi",
        readonly=True,
        copy=False,
        tracking=True,
    )
    approved_by = fields.Many2one(
        "res.users",
        string="Disetujui Oleh",
        readonly=True,
        copy=False,
        tracking=True,
    )
    approved_at = fields.Datetime(
        string="Waktu Persetujuan",
        readonly=True,
        copy=False,
        tracking=True,
    )

    # --- Mode Transfer Tunggal (Single) ---
    single_bank_id = fields.Many2one(
        "transaksi.bank.master",
        string="Bank Penerima",
        tracking=True,
    )
    single_bank_name = fields.Char(
        string="Bank Penerima",
        compute="_compute_single_bank_name",
        store=True,
        readonly=False,
        tracking=True,
    )

    @api.depends("single_bank_id")
    def _compute_single_bank_name(self):
        for rec in self:
            if rec.single_bank_id:
                rec.single_bank_name = rec.single_bank_id.name
    single_destination_account = fields.Char(
        string="Nomor Rekening Tujuan",
        tracking=True,
    )
    single_account_holder_name = fields.Char(
        string="Nama Pemilik Rekening",
        tracking=True,
    )
    single_country_id = fields.Many2one(
        "res.country",
        string="Negara",
        default=lambda self: self.env["res.country"].search([("code", "=", "ID")], limit=1),
    )
    single_transfer_method = fields.Selection(
        [
            ("bi_fast", "BI-FAST"),
            ("online", "Transfer Online"),
            ("inhouse", "Antar Rekening Bank yang Sama (Inhouse)"),
            ("rtgs", "RTGS"),
            ("llg", "Kliring (SKNBI/LLG)"),
        ],
        string="Metode Transfer",
        default="bi_fast",
        tracking=True,
    )
    single_rupiah = fields.Monetary(
        string="Rupiah",
        currency_field="currency_id",
        tracking=True,
    )
    single_notes = fields.Char(
        string="Catatan Baris",
    )

    # --- Mode Transfer Massal (Multiple) ---
    line_ids = fields.One2many(
        "transaksi.transaction.line",
        "transaction_id",
        string="Daftar Rekening Penerima",
        copy=True,
    )

    # --- Integrasi Dokumen Sumber PPL ---
    ppl_id = fields.Many2one(
        "sifnext.ppl",
        string="Dokumen Sumber PPL",
        readonly=True,
        copy=False,
        help="PPL sumber untuk transfer tunggal.",
    )
    ppl_ids = fields.Many2many(
        "sifnext.ppl",
        "transaksi_ppl_rel",
        "transaction_id",
        "ppl_id",
        string="Daftar Dokumen PPL",
        readonly=True,
        copy=False,
        help="Daftar PPL yang dibayarkan dalam transfer massal ini.",
    )

    # --- Ringkasan Rekening Penerima untuk List View ---
    recipient_bank = fields.Char(
        string="Bank Penerima",
        compute="_compute_recipient_info",
        store=True,
    )
    recipient_account = fields.Char(
        string="Nomor Rekening",
        compute="_compute_recipient_info",
        store=True,
    )
    recipient_name = fields.Char(
        string="Nama Pemilik Rekening",
        compute="_compute_recipient_info",
        store=True,
    )

    @api.depends(
        "transfer_type",
        "single_bank_name",
        "single_destination_account",
        "single_account_holder_name",
        "line_ids.bank_name",
        "line_ids.destination_account",
        "line_ids.account_holder_name",
    )
    def _compute_recipient_info(self):
        for rec in self:
            if rec.transfer_type == "single":
                rec.recipient_bank = rec.single_bank_name or ""
                rec.recipient_account = rec.single_destination_account or ""
                rec.recipient_name = rec.single_account_holder_name or ""
            else:
                lines = rec.line_ids
                count = len(lines)
                if count == 0:
                    rec.recipient_bank = ""
                    rec.recipient_account = ""
                    rec.recipient_name = ""
                elif count == 1:
                    rec.recipient_bank = lines[0].bank_name or ""
                    rec.recipient_account = lines[0].destination_account or ""
                    rec.recipient_name = lines[0].account_holder_name or ""
                else:
                    banks = list(dict.fromkeys(filter(None, lines.mapped("bank_name"))))
                    rec.recipient_bank = ", ".join(banks) if len(banks) <= 2 else f"{len(banks)} Bank ({count} Rekening)"
                    rec.recipient_account = f"{count} Rekening"
                    first_holder = lines[0].account_holder_name or lines[0].destination_account
                    rec.recipient_name = f"{first_holder} (+{count - 1} lainnya)" if first_holder else f"{count} Penerima"

    @api.depends("source_account_id")
    def _compute_source_account_number(self):
        for rec in self:
            if rec.source_account_id:
                rec.source_account_number = rec.source_account_id.code or ""
            else:
                rec.source_account_number = False

    @api.depends("transfer_type", "single_rupiah", "line_ids.rupiah")
    def _compute_total_rupiah(self):
        for rec in self:
            if rec.transfer_type == "single":
                rec.total_rupiah = rec.single_rupiah or 0.0
            else:
                rec.total_rupiah = sum(rec.line_ids.mapped("rupiah"))

    @api.onchange("sender_account_id", "single_bank_name", "transfer_category", "line_ids")
    def _onchange_bank_category_check(self):
        for rec in self:
            sender_bank = (rec.sender_bank_name or "").strip().lower()
            if not sender_bank:
                continue

            recipient_bank = False
            if rec.transfer_type == "single":
                recipient_bank = (rec.single_bank_name or "").strip().lower()
            elif rec.line_ids:
                banks = set(filter(None, [b.strip().lower() for b in rec.line_ids.mapped("bank_name") if b]))
                if len(banks) == 1:
                    recipient_bank = list(banks)[0]

            if not recipient_bank:
                continue

            if rec.transfer_category == "interbank" and sender_bank == recipient_bank:
                return {
                    "warning": {
                        "title": _("Bank Pengirim & Penerima Sama"),
                        "message": _(
                            "Bank pengirim dan penerima sama (%s).\n"
                            "Untuk transfer ke bank yang sama, disarankan beralih ke Mutasi Antar Rekening."
                        ) % rec.sender_bank_name,
                    }
                }
            elif rec.transfer_category == "inhouse" and sender_bank != recipient_bank:
                return {
                    "warning": {
                        "title": _("Bank Pengirim & Penerima Berbeda"),
                        "message": _(
                            "Bank pengirim (%s) dan penerima (%s) berbeda.\n"
                            "Untuk transfer antar bank berbeda, disarankan beralih ke Mutasi Antar Bank."
                        ) % (rec.sender_bank_name, rec.single_bank_name or "lainnya"),
                    }
                }

    @api.constrains("transfer_category", "sender_account_id", "single_bank_name", "line_ids")
    def _check_bank_category_matching(self):
        for rec in self:
            sender_bank = (rec.sender_bank_name or "").strip().lower()
            if not sender_bank:
                continue

            recipient_bank = False
            if rec.transfer_type == "single":
                recipient_bank = (rec.single_bank_name or "").strip().lower()
            elif rec.line_ids:
                banks = set(filter(None, [b.strip().lower() for b in rec.line_ids.mapped("bank_name") if b]))
                if len(banks) == 1:
                    recipient_bank = list(banks)[0]

            if not recipient_bank:
                continue

            if rec.transfer_category == "interbank" and sender_bank == recipient_bank:
                raise ValidationError(
                    _("Bank pengirim dan penerima sama (%s). Untuk transfer ke bank yang sama, silakan gunakan menu Mutasi Antar Rekening.")
                    % rec.sender_bank_name
                )
            elif rec.transfer_category == "inhouse" and sender_bank != recipient_bank:
                raise ValidationError(
                    _("Bank pengirim (%s) dan penerima (%s) berbeda. Untuk transfer antar bank berbeda, silakan gunakan menu Mutasi Antar Bank.")
                    % (rec.sender_bank_name, rec.single_bank_name or "lainnya")
                )

    @api.constrains("ref_number")
    def _check_ref_number(self):
        for rec in self:
            if rec.ref_number and len(rec.ref_number) > 19:
                raise ValidationError(_("Referensi transaksi maksimal 19 karakter."))

    @api.constrains("remark")
    def _check_remark(self):
        for rec in self:
            if rec.remark and len(rec.remark) > 200:
                raise ValidationError(_("Catatan internal transaksi maksimal 200 karakter."))

    @api.constrains("execution_time", "scheduled_date")
    def _check_scheduled_date(self):
        for rec in self:
            if rec.execution_time == "scheduled" and not rec.scheduled_date:
                raise ValidationError(_("Tanggal pelaksanaan terjadwal wajib diisi jika waktu pelaksanaan dijadwalkan."))

    @api.constrains("submission_time")
    def _check_submission_time(self):
        for rec in self:
            if rec.submission_time:
                parts = rec.submission_time.strip().split(":")
                if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit() or not (0 <= int(parts[0]) <= 23) or not (0 <= int(parts[1]) <= 59):
                    raise ValidationError(_("Format Jam Pengajuan harus HH:MM (contoh: 14:30)."))

    @api.constrains("company_id", "department_id", "ppl_id", "ppl_ids", "line_ids")
    def _check_company_department_scope(self):
        for record in self:
            if record.department_id and record.department_id.company_id != record.company_id:
                raise ValidationError(_("Departemen transaksi harus berasal dari perusahaan/cabang yang sama."))
            ppls = record.ppl_id | record.ppl_ids | record.line_ids.mapped("ppl_id")
            if any(ppl.company_id != record.company_id for ppl in ppls):
                raise ValidationError(_("PPL dalam satu transaksi harus berasal dari perusahaan/cabang yang sama."))
            if record.department_id and any(ppl.department_id != record.department_id for ppl in ppls):
                raise ValidationError(_("Departemen transaksi harus sama dengan departemen PPL yang ditautkan."))
            if not record.department_id and not ppls:
                raise ValidationError(_("Departemen wajib diisi untuk transaksi tanpa PPL."))

    @api.constrains("transfer_type", "single_rupiah", "single_transfer_method", "single_destination_account", "source_account_number", "line_ids")
    def _check_business_rules(self):
        for rec in self:
            if rec.transfer_type == "single":
                if rec.single_rupiah <= 0 and rec.state != "draft":
                    raise ValidationError(_("Nominal rupiah transfer harus lebih dari Rp 0."))
                if rec.single_transfer_method == "bi_fast" and rec.single_rupiah > 0 and rec.single_rupiah < 10000.0:
                    raise ValidationError(_("Nominal transfer minimal Rp 10.000,00 untuk metode BI-FAST."))
                if rec.single_transfer_method == "inhouse" and rec.source_account_number and rec.single_destination_account:
                    if rec.single_destination_account.strip() == rec.source_account_number.strip():
                        raise ValidationError(_("Nomor rekening tujuan tidak boleh sama dengan rekening sumber untuk transfer Inhouse."))
            else:
                if rec.state != "draft" and not rec.line_ids:
                    raise ValidationError(_("Minimal harus ada satu rekening tujuan transfer untuk tipe Transfer Massal."))
                for line in rec.line_ids:
                    if line.rupiah <= 0 and rec.state != "draft":
                        raise ValidationError(_("Nominal rupiah transfer per baris tujuan harus lebih dari Rp 0."))
                    if line.transfer_method == "bi_fast" and line.rupiah > 0 and line.rupiah < 10000.0:
                        raise ValidationError(_("Nominal transfer minimal Rp 10.000,00 untuk metode BI-FAST."))
                    if line.transfer_method == "inhouse" and rec.source_account_number and line.destination_account:
                        if line.destination_account.strip() == rec.source_account_number.strip():
                            raise ValidationError(_("Nomor rekening tujuan (%s) tidak boleh sama dengan rekening sumber untuk transfer Inhouse.") % line.destination_account)

    @api.constrains("single_rupiah", "ppl_id")
    def _check_single_ppl_amount(self):
        for rec in self:
            if rec.transfer_type == "single" and rec.ppl_id and rec.single_rupiah != rec.ppl_id.total_amount:
                raise ValidationError(
                    _("Nominal transfer untuk PPL %s (Rp %s) harus sama dengan total nominal dokumen PPL (Rp %s).")
                    % (rec.ppl_id.name, f"{rec.single_rupiah:,.2f}", f"{rec.ppl_id.total_amount:,.2f}")
                )

    def _sync_single_line(self):
        """Memastikan recordset line_ids sinkron dengan input transfer tunggal."""
        for rec in self:
            if rec.transfer_type == "single":
                vals = {
                    "bank_id": rec.single_bank_id.id if rec.single_bank_id else False,
                    "bank_name": rec.single_bank_name or False,
                    "destination_account": rec.single_destination_account or "",
                    "account_holder_name": rec.single_account_holder_name or False,
                    "country_id": rec.single_country_id.id if rec.single_country_id else False,
                    "currency_id": rec.currency_id.id,
                    "transfer_method": rec.single_transfer_method or "bi_fast",
                    "rupiah": rec.single_rupiah or 0.0,
                    "line_notes": rec.single_notes or False,
                    "ppl_id": rec.ppl_id.id if rec.ppl_id else False,
                }
                if rec.line_ids:
                    rec.line_ids[0].write(vals)
                else:
                    self.env["transaksi.transaction.line"].create({
                        **vals,
                        "transaction_id": rec.id,
                        "sequence": 1,
                    })

    @api.model_create_multi
    def create(self, vals_list):
        self._check_finance_central_readonly()
        for vals in vals_list:
            company = self.env["res.company"].browse(vals.get("company_id") or self.env.company.id).exists()
            if not company or company not in self.env.companies:
                raise AccessError(_("Anda tidak memiliki akses ke perusahaan/cabang transaksi ini."))
            vals["company_id"] = company.id
            if "department_id" not in vals:
                if vals.get("ppl_ids"):
                    vals["department_id"] = False
                elif vals.get("ppl_id"):
                    ppl = self.env["sifnext.ppl"].browse(vals["ppl_id"]).exists()
                    vals["department_id"] = ppl.department_id.id if ppl else False
                else:
                    vals["department_id"] = self.env.user.department_id.id or False
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("transaksi.transaction") or "New"
        records = super().create(vals_list)
        for record in records:
            if record.transfer_type == "single":
                record._sync_single_line()
        return records

    def write(self, vals):
        self._check_finance_central_readonly()
        organization_fields = {"company_id", "department_id"}
        if organization_fields.intersection(vals) and any(record.state != "draft" for record in self):
            raise UserError(_("Perusahaan dan departemen transaksi hanya dapat diubah pada status Draf."))
        res = super().write(vals)
        for record in self:
            if record.transfer_type == "single" and not self.env.context.get("skip_single_sync"):
                record.with_context(skip_single_sync=True)._sync_single_line()
        return res

    def unlink(self):
        self._check_finance_central_readonly()
        for rec in self:
            if rec.state not in ("draft", "rejected"):
                raise UserError(_("Hanya transaksi berstatus Draf atau Ditolak yang dapat dihapus."))
            target_ppls = rec.ppl_id | rec.ppl_ids | rec.line_ids.mapped("ppl_id")
            for ppl in target_ppls:
                ppl.sudo().write({"transaction_id": False})
        return super().unlink()

    # --- Aksi Alur Status (State Machine) ---
    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Hanya transaksi berstatus Draf yang dapat diajukan."))
            if rec.transfer_type == "single":
                if not rec.single_destination_account:
                    raise ValidationError(_("Nomor rekening tujuan wajib diisi."))
                if rec.single_rupiah <= 0:
                    raise ValidationError(_("Nominal rupiah transfer harus lebih dari Rp 0."))
                if rec.single_transfer_method == "bi_fast" and rec.single_rupiah < 10000.0:
                    raise ValidationError(_("Nominal transfer minimal Rp 10.000,00 untuk metode BI-FAST."))
                if rec.single_transfer_method == "inhouse" and rec.source_account_number and rec.single_destination_account:
                    if rec.single_destination_account.strip() == rec.source_account_number.strip():
                        raise ValidationError(_("Nomor rekening tujuan tidak boleh sama dengan rekening sumber untuk transfer Inhouse."))
                rec._sync_single_line()
            else:
                if not rec.line_ids:
                    raise ValidationError(_("Minimal harus ada satu rekening tujuan transfer."))
                for line in rec.line_ids:
                    if not line.destination_account:
                        raise ValidationError(_("Setiap baris transfer wajib mengisi nomor rekening tujuan."))
                    if line.rupiah <= 0:
                        raise ValidationError(_("Nominal rupiah transfer per baris harus lebih dari Rp 0."))
                    if line.transfer_method == "bi_fast" and line.rupiah < 10000.0:
                        raise ValidationError(_("Nominal transfer minimal Rp 10.000,00 untuk metode BI-FAST."))
                    if line.transfer_method == "inhouse" and rec.source_account_number and line.destination_account:
                        if line.destination_account.strip() == rec.source_account_number.strip():
                            raise ValidationError(_("Nomor rekening tujuan tidak boleh sama dengan rekening sumber untuk transfer Inhouse."))

            rec.write({
                "state": "submitted",
                "submitted_at": fields.Datetime.now(),
            })
            rec.message_post(body=_("Transaksi telah diajukan ke Bagian Keuangan untuk verifikasi."))
        return True

    def action_verify(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Hanya transaksi berstatus Diajukan yang dapat diverifikasi."))
            rec.write({
                "state": "verified",
                "verified_by": self.env.user.id,
                "verified_at": fields.Datetime.now(),
            })
            rec.message_post(body=_("Transaksi telah diverifikasi oleh Bagian Keuangan (%s) dan menunggu persetujuan Direktur.") % self.env.user.name)
        return True

    def action_approve(self):
        for rec in self:
            if rec.state not in ("submitted", "verified"):
                raise UserError(_("Hanya transaksi berstatus Diajukan atau Diverifikasi Keuangan yang dapat disetujui."))
            vals = {
                "state": "approved",
                "approved_by": self.env.user.id,
                "approved_at": fields.Datetime.now(),
            }
            if rec.state == "submitted" and not rec.verified_by:
                vals.update({
                    "verified_by": self.env.user.id,
                    "verified_at": fields.Datetime.now(),
                })
            rec.write(vals)
            rec._action_post_approval_journal()
            rec.message_post(body=_("Transaksi telah disetujui oleh Direktur (%s).") % self.env.user.name)
        return True

    def action_approve_direct(self):
        """Aksi khusus Super User untuk menyetujui langsung tanpa melalui verifikasi keuangan."""
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Persetujuan langsung hanya dapat dilakukan pada transaksi berstatus Diajukan."))
            rec.write({
                "state": "approved",
                "verified_by": self.env.user.id,
                "verified_at": fields.Datetime.now(),
                "approved_by": self.env.user.id,
                "approved_at": fields.Datetime.now(),
            })
            rec._action_post_approval_journal()
            rec.message_post(body=_("Transaksi telah disetujui langsung oleh Super User (%s).") % self.env.user.name)
        return True

    def _action_post_approval_journal(self):
        """Hook pencatatan jurnal otomatis dan auto-pay PPL."""
        for rec in self:
            target_ppls = rec.ppl_id | rec.ppl_ids | rec.line_ids.mapped("ppl_id")
            for ppl in target_ppls.filtered(lambda p: p.state == "approved"):
                vals = {
                    "payment_reference": rec.name,
                    "payment_date": rec.date or fields.Date.context_today(rec),
                }
                if not ppl.payment_method:
                    vals["payment_method"] = "bank"
                if not ppl.payment_source_account_id:
                    if rec.source_account_id:
                        vals["payment_source_account_id"] = rec.source_account_id.id
                    else:
                        bank_coa = self.env["sif.coa"].search([
                            ("account_type", "=", "asset"),
                            ("name", "ilike", "bank"),
                            ("parent_id", "!=", False),
                            ("active", "=", True)
                        ], limit=1)
                        if bank_coa:
                            vals["payment_source_account_id"] = bank_coa.id
                ppl.sudo().write(vals)
                ppl.sudo().with_context(from_bank_transfer_approval=True).action_pay()
                ppl.message_post(
                    body=Markup(_(
                        "Pembayaran telah direalisasikan secara otomatis melalui "
                        "Transaksi Transfer Bank <a href='#' data-oe-model='transaksi.transaction' data-oe-id='%d'>%s</a>."
                    ))
                    % (rec.id, rec.name)
                )

    def action_reject(self, reason=None):
        for rec in self:
            if rec.state not in ("submitted", "verified"):
                raise UserError(_("Transaksi pada status saat ini tidak dapat ditolak."))
            rec.write({
                "state": "rejected",
                "reject_reason": reason or False,
            })
            body = _("Transaksi ditolak oleh %s.") % self.env.user.name
            if reason:
                body = Markup(_("Transaksi ditolak oleh %s.<br/><strong>Alasan Penolakan:</strong> %s")) % (self.env.user.name, reason)
            rec.message_post(body=body)

            target_ppls = rec.ppl_id | rec.ppl_ids | rec.line_ids.mapped("ppl_id")
            for ppl in target_ppls:
                ppl_msg = Markup(_(
                    "Pengajuan Transfer Bank <a href='#' data-oe-model='transaksi.transaction' data-oe-id='%d'>%s</a> ditolak oleh %s."
                )) % (rec.id, rec.name, self.env.user.name)
                if reason:
                    ppl_msg += Markup(_("<br/><strong>Alasan Penolakan:</strong> %s")) % reason
                ppl.message_post(body=ppl_msg)
                ppl.sudo().write({"transaction_id": False})
        return True

    def action_reset_draft(self):
        for rec in self:
            if rec.state not in ("rejected", "failed"):
                raise UserError(_("Hanya transaksi Ditolak atau Gagal yang dapat dikembalikan ke Draf."))
            rec.write({"state": "draft"})
            rec.message_post(body=_("Transaksi dikembalikan ke status Draf."))
        return True

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Alasan Penolakan Transaksi"),
            "res_model": "transaksi.reject.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_transaction_id": self.id},
        }
