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
    user_lock_date = fields.Date(
        string='Kunci Semua Pengguna Biasa',
        help='Mencegah seluruh transaksi jurnal pada atau sebelum tanggal ini untuk staf umum. Manajer Keuangan masih diizinkan membuat penyesuaian.'
    )
    fiscalyear_lock_date = fields.Date(
        string='Hard Lock (Semua Pengguna)',
        help='Kunci mutlak dan permanen. Seluruh pengguna termasuk Administrator dan Manajer Keuangan tidak dapat mengubah atau memposting transaksi pada atau sebelum tanggal ini.'
    )

    def check_lock_date(self, target_date, lock_type='general'):
        """
        Memeriksa apakah target_date berada dalam batas tanggal kunci aktif.
        - target_date: date object / str
        - lock_type: 'sales', 'purchase', 'general', or 'all'
        """
        if not target_date or not self:
            return
        target_date = fields.Date.to_date(target_date)

        # 1. Hard Lock (Mutlak untuk semua pengguna)
        if self.fiscalyear_lock_date and target_date <= self.fiscalyear_lock_date:
            raise UserError(_(
                'Transaksi terkunci oleh Hard Lock hingga tanggal %s (inklusif).\n'
                'Tidak ada pengguna yang diizinkan menambah, mengubah, memposting, atau membatalkan transaksi pada periode ini.'
            ) % self.fiscalyear_lock_date.strftime('%d/%m/%Y'))

        # 2. Lock Sales / Pendapatan
        if lock_type in ('sales', 'all') and self.sale_lock_date and target_date <= self.sale_lock_date:
            raise UserError(_(
                'Transaksi Penjualan / Pendapatan terkunci hingga tanggal %s (inklusif).'
            ) % self.sale_lock_date.strftime('%d/%m/%Y'))

        # 3. Lock Purchases / Pengadaan / Bank
        if lock_type in ('purchase', 'all') and self.purchase_lock_date and target_date <= self.purchase_lock_date:
            raise UserError(_(
                'Transaksi Pembelian / Pengadaan / Bank terkunci hingga tanggal %s (inklusif).'
            ) % self.purchase_lock_date.strftime('%d/%m/%Y'))

        # 4. Lock Everything (General Lock)
        if self.user_lock_date and target_date <= self.user_lock_date:
            raise UserError(_(
                'Seluruh transaksi terkunci oleh Tanggal Kunci (Lock Everything) hingga tanggal %s (inklusif).'
            ) % self.user_lock_date.strftime('%d/%m/%Y'))
