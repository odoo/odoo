# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class TransaksiBankMaster(models.Model):
    _name = "transaksi.bank.master"
    _description = "Master Data Bank"
    _order = "name asc"

    name = fields.Char(string="Nama Bank", required=True, help="Contoh: BCA, BNI, Mandiri, BRI")
    code = fields.Char(string="Kode Bank")
    active = fields.Boolean(default=True)


class TransaksiBankAccount(models.Model):
    _name = "transaksi.bank.account"
    _description = "Master Data Rekening Bank"
    _order = "bank_name asc, name asc"

    name = fields.Char(string="Nama / Alias Rekening", required=True)
    bank_id = fields.Many2one("transaksi.bank.master", string="Bank", required=True)
    bank_name = fields.Char(string="Nama Bank", related="bank_id.name", store=True, readonly=True)
    account_number = fields.Char(string="Nomor Rekening", required=True)
    account_holder = fields.Char(string="Nama Pemilik Rekening / Atas Nama", required=True)
    company_id = fields.Many2one(
        "res.company",
        string="Perusahaan",
        default=lambda self: self.env.company,
        required=True,
    )
    active = fields.Boolean(default=True)

    @api.depends('bank_id', 'bank_name', 'account_number', 'account_holder', 'name')
    def _compute_display_name(self):
        for rec in self:
            bank = rec.bank_name or (rec.bank_id.name if rec.bank_id else "")
            acc = rec.account_number or ""
            holder = rec.account_holder or ""
            alias = rec.name or ""
            if bank and acc:
                rec.display_name = f"{bank} - {acc} ({holder})" if holder else f"{bank} - {acc}"
            else:
                rec.display_name = alias
