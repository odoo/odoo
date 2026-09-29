# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SifChangeLockDateWizard(models.TransientModel):
    _name = 'sif.change.lock.date'
    _description = 'Kunci Entri Jurnal (Lock Journal Entries)'

    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        default=lambda self: self.env.company,
        required=True
    )
    sale_lock_date = fields.Date(
        string='Lock Sales',
        default=lambda self: self.env.company.sale_lock_date,
        help='Kunci transaksi penjualan dan pendapatan pada atau sebelum tanggal ini (inklusif).'
    )
    purchase_lock_date = fields.Date(
        string='Lock Purchases',
        default=lambda self: self.env.company.purchase_lock_date,
        help='Kunci transaksi pembelian dan pengadaan PPL pada atau sebelum tanggal ini (inklusif).'
    )
    tax_lock_date = fields.Date(
        string='Lock Tax Return',
        default=lambda self: self.env.company.tax_lock_date,
        help='Kunci transaksi perpajakan setelah penutupan pajak (tax closing).'
    )
    user_lock_date = fields.Date(
        string='Lock Everything',
        default=lambda self: self.env.company.user_lock_date,
        help='Kunci seluruh transaksi untuk staf operasional, namun mengizinkan pengecualian bagi Manajer Keuangan.'
    )
    fiscalyear_lock_date = fields.Date(
        string='Hard Lock',
        default=lambda self: self.env.company.fiscalyear_lock_date,
        help='Kunci mutlak dan permanen untuk seluruh pengguna termasuk Administrator.'
    )

    has_draft_entries = fields.Boolean(
        string='Ada Draft Jurnal',
        compute='_compute_draft_entries'
    )
    draft_entry_count = fields.Integer(
        string='Jumlah Draft Jurnal',
        compute='_compute_draft_entries'
    )

    @api.depends('company_id', 'sale_lock_date', 'purchase_lock_date', 'tax_lock_date', 'user_lock_date', 'fiscalyear_lock_date')
    def _compute_draft_entries(self):
        for rec in self:
            dates = [d for d in [rec.sale_lock_date, rec.purchase_lock_date, rec.tax_lock_date, rec.user_lock_date, rec.fiscalyear_lock_date] if d]
            if not dates or not rec.company_id:
                rec.has_draft_entries = False
                rec.draft_entry_count = 0
                continue
            max_date = max(dates)
            count = self.env['sif.jurnal.entry'].search_count([
                ('company_id', '=', rec.company_id.id),
                ('state', '=', 'draft'),
                ('date', '<=', max_date)
            ])
            rec.draft_entry_count = count
            rec.has_draft_entries = count > 0

    def action_review_draft_entries(self):
        self.ensure_one()
        dates = [d for d in [self.sale_lock_date, self.purchase_lock_date, self.tax_lock_date, self.user_lock_date, self.fiscalyear_lock_date] if d]
        max_date = max(dates) if dates else fields.Date.today()
        return {
            'name': _('Jurnal Masih Draft (Perlu Diposting / Dihapus)'),
            'type': 'ir.actions.act_window',
            'res_model': 'sif.jurnal.entry',
            'view_mode': 'list,form',
            'domain': [
                ('company_id', '=', self.company_id.id),
                ('state', '=', 'draft'),
                ('date', '<=', max_date)
            ],
            'context': {'default_state': 'draft'},
        }

    def action_save_lock_dates(self):
        self.ensure_one()
        # Validasi Hard Lock: tidak boleh dimundurkan jika sudah ada hard lock sebelumnya
        old_hard_lock = self.company_id.fiscalyear_lock_date
        if old_hard_lock and self.fiscalyear_lock_date and self.fiscalyear_lock_date < old_hard_lock:
            raise UserError(_(
                'Tanggal Hard Lock (%s) tidak boleh dimundurkan dari tanggal yang sudah terkunci sebelumnya (%s).'
            ) % (self.fiscalyear_lock_date.strftime('%d/%m/%Y'), old_hard_lock.strftime('%d/%m/%Y')))
        if old_hard_lock and not self.fiscalyear_lock_date:
            raise UserError(_('Tanggal Hard Lock tidak dapat dihapus setelah ditetapkan.'))

        self.company_id.write({
            'sale_lock_date': self.sale_lock_date,
            'purchase_lock_date': self.purchase_lock_date,
            'tax_lock_date': self.tax_lock_date,
            'user_lock_date': self.user_lock_date,
            'fiscalyear_lock_date': self.fiscalyear_lock_date,
        })
        return {'type': 'ir.actions.act_window_close'}
