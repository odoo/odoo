# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    sale_lock_date = fields.Date(
        string='Kunci Penjualan / Pendapatan',
        help='Mencegah penambahan, perubahan, atau pembatalan transaksi penjualan dan pendapatan pada atau sebelum tanggal ini (inklusif).'
    )
    purchase_lock_date = fields.Date(
        string='Kunci Pembelian / Pengadaan',
        help='Mencegah penambahan, perubahan, atau pembatalan transaksi pembelian dan pengadaan PPL pada atau sebelum tanggal ini (inklusif).'
    )
    tax_lock_date = fields.Date(
        string='Kunci Pajak (Tax Return)',
        help='Mencegah penambahan, perubahan, atau pembatalan transaksi perpajakan pada atau sebelum tanggal ini (setelah penutupan pajak).'
    )
    user_lock_date = fields.Date(
        string='Kunci Semua Pengguna Biasa',
        help='Mencegah seluruh transaksi jurnal pada atau sebelum tanggal ini untuk staf umum. Manajer Keuangan masih diizinkan membuat penyesuaian.'
    )
    fiscalyear_lock_date = fields.Date(
        string='Hard Lock (Semua Pengguna)',
        help='Kunci mutlak dan permanen. Seluruh pengguna termasuk Administrator dan Manajer Keuangan tidak dapat mengubah atau memposting transaksi pada atau sebelum tanggal ini.'
    )
