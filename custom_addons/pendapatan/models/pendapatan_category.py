# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


class PendapatanCategory(models.Model):
    _name = 'pendapatan.category'
    _description = 'Master Kategori Pendapatan'
    _order = 'code asc, name asc'
    _rec_name = 'display_name'

    finance_central_readonly = fields.Boolean(compute='_compute_finance_central_readonly')

    @api.depends_context('uid')
    def _compute_finance_central_readonly(self):
        is_readonly = self.env.user.has_group('pendapatan.group_pendapatan_finance_central')
        for record in self:
            record.finance_central_readonly = is_readonly

    name = fields.Char(
        string='Nama Kategori',
        required=True
    )
    code = fields.Char(
        string='Kode Kategori',
        required=True,
        index=True,
        help='Kode singkat, misal: SPP, SMR, DON, SEWA'
    )
    display_name = fields.Char(
        string='Tampilan',
        compute='_compute_display_name',
        store=True
    )

    periodicity = fields.Selection([
        ('bulanan', 'Bulanan'),
        ('semester', 'Semester (6 Bulanan)'),
        ('tahunan', 'Tahunan'),
        ('insidentil', 'Insidentil / Tidak Tetap'),
    ], string='Periode', required=True, default='bulanan')

    coa_pendapatan_id = fields.Many2one(
        'sif.coa',
        string='Default COA Pendapatan',
        required=True,
        ondelete='restrict',
        domain=[('account_type', '=', 'income')],
        help='Akun pendapatan (income) yang akan di-kredit saat posting'
    )

    coa_kas_id = fields.Many2one(
        'sif.coa',
        string='Default COA Kas/Bank Penerima',
        ondelete='restrict',
        domain=[('account_type', '=', 'asset')],
        help='Akun Kas/Bank tujuan kredit. Kosongkan untuk diisi manual di transaksi'
    )

    description = fields.Text(
        string='Keterangan'
    )
    active = fields.Boolean(
        string='Aktif',
        default=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company
    )

    _code_company_unique = models.Constraint(
        'unique(code, company_id)',
        'Kode kategori pendapatan harus unik per perusahaan!',
    )

    def _check_finance_central_readonly(self):
        if self.env.user.has_group('pendapatan.group_pendapatan_finance_central'):
            raise AccessError(_('Finance pusat memiliki akses baca saja pada kategori Pendapatan.'))

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

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}" if rec.code else rec.name

    @api.constrains('coa_pendapatan_id')
    def _check_coa_pendapatan(self):
        for rec in self:
            if rec.coa_pendapatan_id and rec.coa_pendapatan_id.account_type != 'income':
                raise ValidationError(
                    _('COA "%s" bukan tipe Pendapatan (income). Pilih akun bertipe income.')
                    % rec.coa_pendapatan_id.display_name
                )
