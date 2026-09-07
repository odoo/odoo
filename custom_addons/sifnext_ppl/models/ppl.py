from odoo import Command, api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class SifnextPPL(models.Model):
    _name = "sifnext.ppl"
    _description = "Permintaan Pembayaran Langsung"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "request_date desc, id desc"

    name = fields.Char(default="New", readonly=True, copy=False, tracking=True, index=True)
    request_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    applicant_id = fields.Many2one(
        "res.users", required=True, default=lambda self: self.env.user,
        readonly=True, tracking=True,
    )
    unit_id = fields.Many2one(
        "sifnext.unit",
        string="Unit",
        default=lambda self: self.env.user.unit_id,
        tracking=True,
        domain="[('company_id', '=', company_id)]",
        help="Wajib untuk PPL baru. Dibiarkan kosong hanya pada PPL lama sebelum master Unit diterapkan.",
    )
    partner_id = fields.Many2one("res.partner", string="Penerima/Vendor", tracking=True)
    title = fields.Char(required=True, tracking=True)
    description = fields.Text(required=True)
    source_type = fields.Selection(
        [("manual", "Pegawai"), ("finance", "Finance"), ("payroll", "Payroll")],
        required=True, default="manual", tracking=True,
    )
    line_ids = fields.One2many("sifnext.ppl.line", "ppl_id", string="Detail", copy=True)
    total_amount = fields.Monetary(compute="_compute_total_amount", store=True, tracking=True)
    currency_id = fields.Many2one(
        "res.currency", required=True,
        default=lambda self: self.env.company.currency_id,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        index=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Diajukan"),
            ("verified", "Diverifikasi"),
            ("approved", "Disetujui"),
            ("paid", "Dibayar"),
            ("done", "Selesai"),
        ],
        required=True, default="draft", copy=False, tracking=True, index=True,
    )
    return_reason = fields.Text(readonly=True, tracking=True)
    payment_method = fields.Selection(
        [("cash", "Kas"), ("bank", "Bank")], string="Metode Pembayaran", tracking=True,
    )
    payment_source_account_id = fields.Many2one(
        "sif.coa",
        string="Sumber Dana (Kas/Bank)",
        tracking=True,
        domain="[('active', '=', True), ('parent_id', '!=', False), ('account_type', '=', 'asset'),"
        " '|', ('name', 'ilike', 'kas'), ('name', 'ilike', 'bank')]",
        help="Akun kas/bank sumber dana pembayaran; sisi Kredit jurnal mengikuti akun ini.",
    )
    payment_date = fields.Date(string="Tanggal Pembayaran", tracking=True)
    payment_reference = fields.Char(string="Referensi Pembayaran", tracking=True)
    submitted_by = fields.Many2one("res.users", readonly=True, copy=False)
    submitted_at = fields.Datetime(readonly=True, copy=False)
    verified_by = fields.Many2one("res.users", readonly=True, copy=False)
    verified_at = fields.Datetime(readonly=True, copy=False)
    approved_by = fields.Many2one("res.users", readonly=True, copy=False)
    approved_at = fields.Datetime(readonly=True, copy=False)
    paid_by = fields.Many2one("res.users", readonly=True, copy=False)
    paid_at = fields.Datetime(readonly=True, copy=False)
    done_by = fields.Many2one("res.users", readonly=True, copy=False)
    done_at = fields.Datetime(readonly=True, copy=False)

    _name_company_uniq = models.Constraint(
        "unique (name, company_id)",
        "Nomor PPL harus unik dalam satu perusahaan.",
    )

    @api.depends("line_ids.subtotal")
    def _compute_total_amount(self):
        for record in self:
            record.total_amount = sum(record.line_ids.mapped("subtotal"))

    @api.constrains("line_ids")
    def _check_positive_lines(self):
        for record in self:
            if any(line.subtotal <= 0 for line in record.line_ids):
                raise ValidationError(_("Nilai setiap detail PPL harus lebih dari nol."))

    @api.model_create_multi
    def create(self, vals_list):
        is_finance = self.env.user.has_group("sifnext_ppl.group_ppl_finance")
        for vals in vals_list:
            applicant = self.env["res.users"].browse(vals.get("applicant_id", self.env.user.id))
            if not is_finance and applicant != self.env.user:
                raise AccessError(_("Pegawai hanya dapat membuat PPL atas nama sendiri."))
            if not is_finance:
                applicant = self.env.user
                vals["applicant_id"] = applicant.id
                vals["source_type"] = "manual"
            unit = self.env["sifnext.unit"].browse(vals.get("unit_id") or applicant.unit_id.id)
            if not unit:
                raise ValidationError(_("Unit pemohon wajib ditentukan sebelum membuat PPL."))
            company = self.env["res.company"].browse(vals.get("company_id", self.env.company.id))
            if unit.company_id != company:
                raise ValidationError(_("Unit PPL harus berasal dari perusahaan yang sama."))
            vals["unit_id"] = unit.id
            request_date = fields.Date.to_date(vals.get("request_date")) or fields.Date.context_today(self)
            sequence = self.env["ir.sequence"].next_by_code(
                "sifnext.ppl", sequence_date=request_date,
            ) or "New"
            vals["name"] = f"{unit.code}/{sequence}"
        return super().create(vals_list)

    def _is_submitted_coa_update(self, commands):
        """Allow the one2many payload used by the form to update only existing COAs."""
        if not self.env.user.has_group("sifnext_ppl.group_ppl_finance"):
            return False
        if any(record.state != "submitted" for record in self):
            return False
        line_ids = set(self.line_ids.ids)
        for command in commands:
            if not isinstance(command, (list, tuple)) or len(command) < 3:
                return False
            operation, line_id, values = command[0], command[1], command[2]
            if operation != Command.UPDATE or line_id not in line_ids:
                return False
            classification_fields = {"journal_account_id", "rka_id"}
            if not isinstance(values, dict) or not values or set(values) - classification_fields:
                return False
        return bool(commands)

    def write(self, vals):
        if "name" in vals and any(record.name != vals["name"] for record in self):
            raise UserError(_("Nomor PPL tidak dapat diubah."))
        workflow_fields = {
            "state", "return_reason", "submitted_by", "submitted_at", "verified_by", "verified_at",
            "approved_by", "approved_at", "paid_by", "paid_at", "done_by", "done_at",
        }
        if workflow_fields.intersection(vals) and not self.env.context.get("ppl_workflow_write"):
            raise AccessError(_("Status dan audit workflow hanya dapat diubah melalui tindakan PPL."))
        if "applicant_id" in vals and not self.env.user.has_group("sifnext_ppl.group_ppl_finance"):
            if vals["applicant_id"] != self.env.user.id:
                raise AccessError(_("Pegawai tidak dapat mengubah pemohon PPL."))
        protected = {
            "request_date", "applicant_id", "unit_id", "partner_id", "title", "description",
            "source_type",
        }
        protected_values = {field: vals[field] for field in protected.intersection(vals)}
        for record in self.filtered(lambda item: item.state != "draft"):
            for field_name, new_value in protected_values.items():
                field = record._fields[field_name]
                current_value = record[field_name]
                if field.type == "many2one":
                    current_value = current_value.id or False
                    new_value = new_value or False
                elif field.type == "date":
                    current_value = fields.Date.to_string(current_value)
                    new_value = fields.Date.to_string(new_value) if new_value else False
                if current_value != new_value:
                    raise UserError(_("Data pengajuan hanya dapat diubah pada status Draft."))
        if "line_ids" in vals and any(record.state != "draft" for record in self):
            if not self._is_submitted_coa_update(vals["line_ids"]):
                raise UserError(_("Detail kebutuhan hanya dapat diubah pada status Draft."))
        payment_fields = {"payment_method", "payment_source_account_id", "payment_date", "payment_reference"}
        if payment_fields.intersection(vals):
            if not self.env.user.has_group("sifnext_ppl.group_ppl_finance"):
                raise AccessError(_("Hanya Keuangan yang dapat mengisi data pembayaran."))
            if any(record.state != "approved" for record in self):
                raise UserError(_("Data pembayaran hanya dapat diisi pada PPL Disetujui."))
        return super().write(vals)

    def _workflow_write(self, vals):
        return self.with_context(ppl_workflow_write=True).write(vals)

    def unlink(self):
        if any(record.state != "draft" for record in self):
            raise UserError(_("Hanya PPL Draft yang dapat dihapus."))
        return super().unlink()

    def _check_submit_data(self):
        for record in self:
            if not record.line_ids:
                raise ValidationError(_("PPL harus memiliki minimal satu detail."))
            if any(line.subtotal <= 0 for line in record.line_ids):
                raise ValidationError(_("Nilai setiap detail PPL harus lebih dari nol."))

    def _check_finance_group(self):
        if not self.env.user.has_group("sifnext_ppl.group_ppl_finance"):
            raise AccessError(_("Hanya Finance yang dapat melakukan tindakan ini."))

    def _check_group(self, xmlid, message):
        if not self.env.user.has_group(xmlid):
            raise AccessError(_(message))

    def _prepare_integration_payload(self):
        """Return the versioned, primitive-only contract consumed by downstream addons."""
        self.ensure_one()
        return {
            "schema_version": 1,
            "event": "ppl.paid",
            "idempotency_key": f"ppl.paid:{self.company_id.id}:{self.id}",
            "ppl": {
                "id": self.id,
                "number": self.name,
                "state": self.state,
                "source_type": self.source_type,
                "request_date": fields.Date.to_string(self.request_date),
                "title": self.title,
                "description": self.description,
                "applicant": {
                    "id": self.applicant_id.id,
                    "name": self.applicant_id.name,
                },
                "unit": {
                    "id": self.unit_id.id,
                    "code": self.unit_id.code,
                    "name": self.unit_id.name,
                } if self.unit_id else None,
                "partner": {
                    "id": self.partner_id.id,
                    "name": self.partner_id.name,
                } if self.partner_id else None,
                "company": {
                    "id": self.company_id.id,
                    "name": self.company_id.name,
                },
                "currency": {
                    "id": self.currency_id.id,
                    "name": self.currency_id.name,
                },
                "total_amount": self.total_amount,
                "payment": {
                    "method": self.payment_method,
                    "date": fields.Date.to_string(self.payment_date),
                    "reference": self.payment_reference,
                    "paid_by_id": self.paid_by.id,
                    "paid_at": fields.Datetime.to_string(self.paid_at),
                    "source_account": {
                        "id": self.payment_source_account_id.id,
                        "code": self.payment_source_account_id.code,
                        "name": self.payment_source_account_id.name,
                    } if self.payment_source_account_id else None,
                },
                "lines": [{
                    "id": line.id,
                    "sequence": line.sequence,
                    "description": line.description,
                    "quantity": line.quantity,
                    "unit_price": line.unit_price,
                    "amount": line.subtotal,
                    "account": {
                        "id": line.journal_account_id.id,
                        "code": line.journal_account_id.code,
                        "name": line.journal_account_id.name,
                    } if line.journal_account_id else None,
                } for line in self.line_ids.sorted(key=lambda item: (item.sequence, item.id))],
            },
        }

    def _prepare_budget_check_payload(self):
        """Return budget inputs without assuming the technical model used by RKA."""
        self.ensure_one()
        return {
            "schema_version": 1,
            "ppl_id": self.id,
            "ppl_number": self.name,
            "company_id": self.company_id.id,
            "unit_id": self.unit_id.id,
            "request_date": fields.Date.to_string(self.request_date),
            "currency_id": self.currency_id.id,
            "total_amount": self.total_amount,
            "lines": [{
                "line_id": line.id,
                "amount": line.subtotal,
            } for line in self.line_ids],
        }

    def _validate_rka_budget(self, payload):
        """RKA extension point; raise ValidationError when budget is unavailable."""
        return True

    def _check_budget(self):
        self.ensure_one()
        result = self._validate_rka_budget(self._prepare_budget_check_payload())
        self.line_ids.write({"budget_status": "sufficient"})
        return result

    def _notify_rka_paid(self, payload):
        """RKA extension point for idempotent realization after payment."""
        return True

    def _notify_general_ledger_paid(self, payload):
        """General Ledger extension point; PPL itself never creates a journal entry."""
        # ponytail: PPL shouldn't create journal, but cyclic dependency prevents sif_keuangan from inheriting PPL.
        # Upgrade path: Extract this to a third bridge module (sifnext_ppl_keuangan).
        jurnal_lines = []
        for line in payload['ppl']['lines']:
            if line.get('account') and line['account'].get('id'):
                jurnal_lines.append({
                    'account_id': line['account']['id'],
                    'name': line['description'],
                    'debit': line['amount'],
                    'credit': 0.0,
                })
        source_account = payload['ppl']['payment'].get('source_account')
        if not source_account or not source_account.get('id'):
            raise UserError(_("Sumber dana (kas/bank) pembayaran belum dipilih."))
        jurnal_lines.append({
            'account_id': source_account['id'],
            'name': f"Pembayaran {payload['ppl']['number']}",
            'debit': 0.0,
            'credit': payload['ppl']['total_amount'],
        })
        self.env['sif.jurnal.entry'].sudo().create_journal_from_ppl({
            'date': payload['ppl']['payment']['date'],
            'reference': payload['ppl']['title'],
            'source_document': payload['ppl']['number'],
            'unit_dept': self.unit_id.journal_unit_dept if self.unit_id else 'pusat',
            'lines': jurnal_lines,
        })
        return True

    def _on_ppl_paid(self):
        """Dispatch the paid event in the same transaction as the state transition."""
        self.ensure_one()
        payload = self._prepare_integration_payload()
        self._notify_rka_paid(payload)
        self._notify_general_ledger_paid(payload)
        return True

    def action_submit(self):
        is_finance = self.env.user.has_group("sifnext_ppl.group_ppl_finance")
        for record in self:
            if record.state != "draft":
                raise UserError(_("Hanya PPL Draft yang dapat diajukan."))
        self._check_submit_data()
        submitted_at = fields.Datetime.now()
        values = {
            "state": "submitted",
            "submitted_by": self.env.user.id,
            "submitted_at": submitted_at,
            "return_reason": False,
        }
        if is_finance:
            for record in self:
                if any(not line.journal_account_id for line in record.line_ids):
                    raise ValidationError(_("Keuangan harus memilih COA untuk seluruh detail sebelum mengajukan PPL."))
                record._check_budget()
            values.update({
                "state": "verified",
                "verified_by": self.env.user.id,
                "verified_at": submitted_at,
            })
        self._workflow_write(values)

    def action_verify(self):
        self._check_finance_group()
        for record in self:
            if record.state != "submitted":
                raise UserError(_("Hanya PPL Diajukan yang dapat diverifikasi."))
            if any(not line.journal_account_id for line in record.line_ids):
                raise ValidationError(_("Finance harus memilih COA untuk seluruh detail sebelum verifikasi."))
            record._check_budget()
        self._workflow_write({
            "state": "verified",
            "verified_by": self.env.user.id,
            "verified_at": fields.Datetime.now(),
        })

    def action_approve(self):
        self._check_group("sifnext_ppl.group_ppl_approver", "Hanya Direktur yang dapat menyetujui PPL.")
        for record in self:
            if record.state != "verified":
                raise UserError(_("Hanya PPL Diverifikasi yang dapat disetujui."))
            record._check_budget()
        self._workflow_write({
            "state": "approved",
            "approved_by": self.env.user.id,
            "approved_at": fields.Datetime.now(),
        })

    def action_pay(self):
        self._check_group("sifnext_ppl.group_ppl_finance", "Hanya Keuangan yang dapat mencatat pembayaran.")
        for record in self:
            if record.state != "approved":
                raise UserError(_("Hanya PPL Disetujui yang dapat dibayar."))
            if not record.payment_method or not record.payment_date or not record.payment_reference \
                    or not record.payment_source_account_id:
                raise ValidationError(_("Metode, tanggal, referensi, dan sumber dana pembayaran wajib diisi."))
            record._check_budget()
        self._workflow_write({
            "state": "paid",
            "paid_by": self.env.user.id,
            "paid_at": fields.Datetime.now(),
        })
        for record in self:
            record._on_ppl_paid()

    def action_done(self):
        self._check_group("sifnext_ppl.group_ppl_finance", "Hanya Keuangan yang dapat menyelesaikan PPL.")
        for record in self:
            if record.state != "paid":
                raise UserError(_("Hanya PPL Dibayar yang dapat diselesaikan."))
        self._workflow_write({
            "state": "done",
            "done_by": self.env.user.id,
            "done_at": fields.Datetime.now(),
        })

    def action_return_to_draft(self):
        self._check_finance_group()
        reason = self.env.context.get("return_reason")
        if not reason:
            raise ValidationError(_("Alasan revisi wajib diisi."))
        for record in self:
            if record.state not in ("submitted", "verified"):
                raise UserError(_("PPL pada status ini tidak dapat dikembalikan."))
        self._workflow_write({"state": "draft", "return_reason": reason})


class SifnextPPLLine(models.Model):
    _name = "sifnext.ppl.line"
    _description = "Detail Permintaan Pembayaran Langsung"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    ppl_id = fields.Many2one("sifnext.ppl", required=True, ondelete="cascade", index=True)
    description = fields.Char(required=True)
    quantity = fields.Float(required=True, default=1)
    unit_price = fields.Monetary(required=True)
    subtotal = fields.Monetary(compute="_compute_subtotal", store=True)
    currency_id = fields.Many2one(related="ppl_id.currency_id", store=True)
    company_id = fields.Many2one(related="ppl_id.company_id", store=True)
    journal_account_id = fields.Many2one(
        "sif.coa",
        string="COA",
        domain="[('active', '=', True), ('parent_id', '!=', False), ('account_type', '=', 'expense')]",
        help="Sub-COA atau sub-sub-COA dari Master COA modul Keuangan.",
    )
    budget_status = fields.Selection(
        [("unchecked", "Belum Dicek"), ("sufficient", "Cukup"), ("insufficient", "Tidak Cukup")],
        default="unchecked", readonly=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "sifnext_ppl_line_attachment_rel",
        "line_id",
        "attachment_id",
        string="Lampiran",
        copy=False,
        help="Bukti atau dokumen pendukung untuk item PPL ini.",
    )
    attachment_count = fields.Integer(compute="_compute_attachment_count", string="Jumlah Lampiran")
    ppl_state = fields.Selection(related="ppl_id.state", string="Status PPL")

    @api.depends("attachment_ids")
    def _compute_attachment_count(self):
        for line in self:
            line.attachment_count = len(line.attachment_ids)

    @api.depends("quantity", "unit_price")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_price

    @api.constrains("quantity", "unit_price")
    def _check_positive_amount(self):
        for line in self:
            if line.quantity <= 0 or line.unit_price <= 0:
                raise ValidationError(_("Kuantitas dan harga satuan harus lebih dari nol."))

    @api.onchange("journal_account_id")
    def _onchange_journal_account_id(self):
        self.budget_status = "unchecked"

    def _check_finance_account_access(self, vals):
        if "journal_account_id" not in vals:
            return
        if not self.env.user.has_group("sifnext_ppl.group_ppl_finance"):
            raise AccessError(_("Hanya Finance yang dapat memilih atau mengubah COA."))
        for line in self:
            if line.ppl_id.state not in ("draft", "submitted"):
                raise UserError(_("COA hanya dapat diubah sebelum PPL diverifikasi."))

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get("journal_account_id") for vals in vals_list):
            if not self.env.user.has_group("sifnext_ppl.group_ppl_finance"):
                raise AccessError(_("Hanya Finance yang dapat memilih COA."))
        parent_ids = {vals.get("ppl_id") for vals in vals_list if vals.get("ppl_id")}
        if parent_ids and any(ppl.state != "draft" for ppl in self.env["sifnext.ppl"].browse(parent_ids)):
            raise UserError(_("Detail hanya dapat ditambahkan pada status Draft."))
        return super().create(vals_list)

    def write(self, vals):
        self._check_finance_account_access(vals)
        content_fields = {"description", "quantity", "unit_price", "attachment_ids"}
        if content_fields.intersection(vals) and any(line.ppl_id.state != "draft" for line in self):
            raise UserError(_("Detail dan lampiran hanya dapat diubah pada status Draft."))
        return super().write(vals)

    def unlink(self):
        if any(line.ppl_id.state != "draft" for line in self):
            raise UserError(_("Detail hanya dapat dihapus pada status Draft."))
        return super().unlink()


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _ppl_lines(self):
        """Find PPL lines owning attachments, including links made through the M2M field."""
        lines = self.env["sifnext.ppl.line"].sudo().search([
            ("attachment_ids", "in", self.ids),
        ])
        direct_line_ids = [
            attachment.res_id
            for attachment in self
            if attachment.res_model == "sifnext.ppl.line" and attachment.res_id
        ]
        return lines | self.env["sifnext.ppl.line"].sudo().browse(direct_line_ids).exists()

    def _check_ppl_attachment_draft(self):
        if any(line.ppl_id.state != "draft" for line in self._ppl_lines()):
            raise UserError(_("Lampiran item PPL hanya dapat diubah atau dihapus pada status Draft."))

    @api.model_create_multi
    def create(self, vals_list):
        direct_line_ids = [
            vals.get("res_id")
            for vals in vals_list
            if vals.get("res_model") == "sifnext.ppl.line" and vals.get("res_id")
        ]
        lines = self.env["sifnext.ppl.line"].sudo().browse(direct_line_ids).exists()
        if any(line.ppl_id.state != "draft" for line in lines):
            raise UserError(_("Lampiran item PPL hanya dapat ditambahkan pada status Draft."))
        return super().create(vals_list)

    def write(self, vals):
        self._check_ppl_attachment_draft()
        return super().write(vals)

    def unlink(self):
        self._check_ppl_attachment_draft()
        return super().unlink()
