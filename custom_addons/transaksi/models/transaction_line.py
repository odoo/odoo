# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


class TransaksiTransactionLine(models.Model):
    _name = "transaksi.transaction.line"
    _description = "Detail Rekening Penerima Transfer"
    _order = "sequence, id asc"

    def _check_finance_central_readonly(self):
        if self.env.user.has_group("sif_keuangan.group_sif_keuangan_central_readonly"):
            raise AccessError(_("Finance pusat memiliki akses baca saja pada detail transfer bank."))

    transaction_id = fields.Many2one(
        "transaksi.transaction",
        string="Induk Transaksi",
        ondelete="cascade",
        index=True,
        required=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Perusahaan",
        related="transaction_id.company_id",
        store=True,
        index=True,
    )
    sequence = fields.Integer(
        string="No.",
        default=1,
    )
    bank_id = fields.Many2one(
        "transaksi.bank.master",
        string="Bank Penerima",
    )
    bank_name = fields.Char(
        string="Nama Bank Penerima",
        compute="_compute_bank_name",
        store=True,
        readonly=False,
    )

    @api.depends("bank_id")
    def _compute_bank_name(self):
        for line in self:
            if line.bank_id:
                line.bank_name = line.bank_id.name
    destination_account = fields.Char(
        string="Nomor Rekening Tujuan",
        required=True,
    )
    account_holder_name = fields.Char(
        string="Nama Pemilik Rekening",
    )
    country_id = fields.Many2one(
        "res.country",
        string="Negara",
        default=lambda self: self.env["res.country"].search([("code", "=", "ID")], limit=1),
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
    transfer_method = fields.Selection(
        [
            ("bi_fast", "BI-FAST"),
            ("online", "Transfer Online"),
            ("inhouse", "Antar Rekening Bank yang Sama (Inhouse)"),
            ("rtgs", "RTGS"),
            ("llg", "Kliring (SKNBI/LLG)"),
        ],
        string="Metode Transfer",
        default="bi_fast",
        required=True,
    )
    rupiah = fields.Monetary(
        string="Rupiah",
        currency_field="currency_id",
        required=True,
    )
    line_notes = fields.Char(
        string="Catatan Baris",
    )
    ppl_id = fields.Many2one(
        "sifnext.ppl",
        string="Sumber PPL",
        readonly=True,
        copy=False,
        help="Dokumen PPL terkait baris transfer ini.",
    )
    department_id = fields.Many2one(
        "hr.department",
        string="Departemen",
        compute="_compute_department_id",
        store=True,
        index=True,
    )

    @api.depends("ppl_id.department_id", "transaction_id.department_id")
    def _compute_department_id(self):
        for line in self:
            line.department_id = line.ppl_id.department_id or line.transaction_id.department_id

    @api.constrains("transaction_id", "ppl_id")
    def _check_ppl_company(self):
        for line in self:
            if line.ppl_id and line.ppl_id.company_id != line.transaction_id.company_id:
                raise ValidationError(_("PPL pada baris transfer harus berasal dari perusahaan/cabang transaksi."))

    @api.constrains("rupiah", "ppl_id")
    def _check_ppl_amount(self):
        for line in self:
            if line.ppl_id and line.ppl_id.source_type != "payroll" and line.rupiah != line.ppl_id.total_amount:
                raise ValidationError(
                    _("Nominal transfer pada baris untuk PPL %s (Rp %s) harus sama dengan total nominal dokumen PPL (Rp %s).")
                    % (line.ppl_id.name, f"{line.rupiah:,.2f}", f"{line.ppl_id.total_amount:,.2f}")
                )

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

    @api.constrains("rupiah", "transfer_method")
    def _check_line_constraints(self):
        for line in self:
            if line.rupiah <= 0 and line.transaction_id.state != "draft":
                raise ValidationError(_("Nominal rupiah transfer per baris harus lebih dari Rp 0."))
            if line.transfer_method == "bi_fast" and line.rupiah > 0 and line.rupiah < 10000.0:
                raise ValidationError(_("Nominal transfer minimal Rp 10.000,00 untuk metode BI-FAST."))
