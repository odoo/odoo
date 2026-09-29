from odoo import models, fields, api


class SifChartOfAccounts(models.Model):
    _name = 'sif.coa'
    _description = 'Master Chart of Accounts (COA)'
    _order = 'code asc'
    _rec_name = 'display_name'

    code = fields.Char(
        string='Kode Akun',
        required=True,
        index=True
    )

    name = fields.Char(
        string='Nama Akun',
        required=True
    )

    account_type = fields.Selection([
        ('asset', 'Aset / Aktiva'),
        ('liability', 'Liabilitas / Kewajiban'),
        ('equity', 'Ekuitas / Modal'),
        ('income', 'Pendapatan'),
        ('expense', 'Beban / Biaya'),
    ], string='Kategori Akun', required=True, default='expense')

    parent_id = fields.Many2one(
        'sif.coa',
        string='Induk Akun (Parent)',
        ondelete='restrict',
        index=True
    )

    child_ids = fields.One2many(
        'sif.coa',
        'parent_id',
        string='Akun Anak'
    )

    level = fields.Integer(
        string='Level Akun',
        compute='_compute_level',
        store=True,
        recursive=True
    )

    display_name = fields.Char(
        string='Tampilan Akun',
        compute='_compute_display_name',
        store=True
    )

    active = fields.Boolean(
        string='Aktif',
        default=True
    )

    # Saldo awal yang diinput secara manual.
    # Hanya digunakan untuk COA yang tidak memiliki anak.
    opening_balance_input = fields.Float(
        string='Input Saldo Awal',
        digits=(16, 2),
        default=0.0
    )

    # Saldo awal yang ditampilkan.
    # Untuk COA anak  : mengikuti opening_balance_input
    # Untuk COA induk : otomatis menjumlahkan seluruh anak.
    opening_balance = fields.Float(
        string='Saldo Awal',
        compute='_compute_opening_balance',
        digits=(16, 2)
    )

    _sql_constraints = [
        (
            'code_unique',
            'unique(code)',
            'Kode Akun sudah terdaftar! Gunakan kode unik.'
        ),
    ]

    @api.depends('parent_id', 'parent_id.level')
    def _compute_level(self):
        for rec in self:
            rec.level = (
                rec.parent_id.level + 1
                if rec.parent_id
                else 1
            )

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name}"

    def _get_total_opening_balance(self):
        """
        Menghitung saldo awal secara rekursif.

        Jika akun tidak mempunyai anak:
            saldo = opening_balance_input

        Jika akun mempunyai anak:
            saldo = total saldo seluruh anak
        """
        self.ensure_one()

        children = self.env['sif.coa'].search([
            ('parent_id', '=', self.id),
            ('active', '=', True),
        ])

        if not children:
            return self.opening_balance_input

        return sum(
            child._get_total_opening_balance()
            for child in children
        )

    @api.depends(
        'opening_balance_input',
        'child_ids',
        'child_ids.opening_balance_input'
    )
    def _compute_opening_balance(self):
        for rec in self:
            rec.opening_balance = rec._get_total_opening_balance()