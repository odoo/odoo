from odoo import models, fields, api, _
from odoo.exceptions import AccessError

class SifChartOfAccounts(models.Model):
    _name = 'sif.coa'
    _description = 'Master Chart of Accounts (COA)'
    _order = 'code asc'
    _rec_name = 'display_name'

    code = fields.Char(string='Kode Akun', required=True, index=True)
    name = fields.Char(string='Nama Akun', required=True)
    account_type = fields.Selection([
        ('asset', 'Aset / Aktiva'),
        ('liability', 'Liabilitas / Kewajiban'),
        ('equity', 'Ekuitas / Modal'),
        ('income', 'Pendapatan'),
        ('expense', 'Beban / Biaya'),
    ], string='Kategori Akun', required=True, default='expense')
    parent_id = fields.Many2one('sif.coa', string='Induk Akun (Parent)', ondelete='restrict', index=True)
    level = fields.Integer(string='Level Akun', compute='_compute_level', store=True, recursive=True)
    display_name = fields.Char(string='Tampilan Akun', compute='_compute_display_name', store=True)
    active = fields.Boolean(string='Aktif', default=True)  # <-- Tambahkan ini

    _code_unique = models.Constraint(
        'unique(code)',
        'Kode Akun sudah terdaftar! Gunakan kode unik.',
    )

    def _check_finance_central_readonly(self):
        if self.env.user.has_group('sif_keuangan.group_sif_keuangan_central_readonly'):
            raise AccessError(_('Finance pusat memiliki akses baca saja pada data Keuangan.'))

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

    @api.depends('parent_id', 'parent_id.level')
    def _compute_level(self):
        for rec in self:
            rec.level = (rec.parent_id.level + 1) if rec.parent_id else 1

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}"
