# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class Pendapatan(models.Model):
    _name = 'pendapatan.pendapatan'
    _description = 'Pencatatan Pendapatan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'tanggal desc, id desc'

    finance_central_readonly = fields.Boolean(compute='_compute_finance_central_readonly')

    @api.depends_context('uid')
    def _compute_finance_central_readonly(self):
        is_readonly = self.env.user.has_group('pendapatan.group_pendapatan_finance_central')
        for record in self:
            record.finance_central_readonly = is_readonly

    def _check_finance_central_readonly(self):
        if self.env.user.has_group('pendapatan.group_pendapatan_finance_central'):
            raise AccessError(_('Finance pusat memiliki akses baca saja pada modul Pendapatan.'))

    def _check_pendapatan_manager(self):
        self._check_finance_central_readonly()
        if not self.env.user.has_group('pendapatan.group_pendapatan_manager'):
            raise AccessError(_('Hanya Manager Pendapatan yang dapat melakukan tindakan ini.'))

    # ------------------------------------------------------------------
    # HEADER FIELDS
    # ------------------------------------------------------------------
    name = fields.Char(
        string='Nomor Pendapatan',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )
    tanggal = fields.Date(
        string='Tanggal Pendapatan',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )

    period_label = fields.Char(
        string='Label Periode',
        required=True,
        help='Contoh: "Januari 2026", "Semester Genap 2025/2026", "TA 2026/2027"',
        tracking=True
    )

    # ------------------------------------------------------------------
    # KATEGORI
    # ------------------------------------------------------------------
    category_id = fields.Many2one(
        'pendapatan.category',
        string='Kategori Pendapatan',
        required=True,
        ondelete='restrict',
        check_company=True,
        tracking=True
    )

    # ------------------------------------------------------------------
    # NOMINAL & SUMBER
    # ------------------------------------------------------------------
    amount = fields.Monetary(
        string='Nominal Pendapatan',
        required=True,
        currency_field='currency_id',
        tracking=True
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    unit_name = fields.Char(
        string='Nama Unit Lama (Legacy)',
        copy=False,
        help='Nilai teks historis yang dipertahankan untuk migrasi dan kompatibilitas. Transaksi baru memakai department_id.',
    )

    source_partner_id = fields.Many2one(
        'res.partner',
        string='Pemberi Pendapatan (Opsional)',
        help='Misal: nama siswa / customer (jika diperlukan)'
    )

    description = fields.Text(
        string='Keterangan / Uraian'
    )

    attachment = fields.Binary(
        string='Bukti / Kwitansi',
        attachment=True
    )

    # ------------------------------------------------------------------
    # STATE MACHINE
    # ------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Diajukan'),
        ('approved', 'Disetujui'),
        ('posted', 'Diposting'),
        ('cancelled', 'Dibatalkan'),
    ], string='Status', default='draft', required=True, tracking=True)

    submitted_by_id = fields.Many2one(
        'res.users',
        string='Diajukan Oleh',
        readonly=True
    )
    submitted_date = fields.Datetime(
        string='Tanggal Diajukan',
        readonly=True
    )

    approved_by_id = fields.Many2one(
        'res.users',
        string='Disetujui Oleh',
        readonly=True,
        tracking=True
    )
    approved_date = fields.Datetime(
        string='Tanggal Disetujui',
        readonly=True
    )

    posted_by_id = fields.Many2one(
        'res.users',
        string='Diposting Oleh',
        readonly=True
    )
    posted_date = fields.Datetime(
        string='Tanggal Diposting',
        readonly=True
    )

    cancel_reason = fields.Text(
        string='Alasan Pembatalan'
    )

    # ------------------------------------------------------------------
    # INTEGRASI JURNAL
    # ------------------------------------------------------------------
    journal_id = fields.Many2one(
        'sif.jurnal.entry',
        string='Jurnal Besar',
        readonly=True,
        copy=False,
        ondelete='restrict'
    )

    # ------------------------------------------------------------------
    # COMPANY
    # ------------------------------------------------------------------
    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company
    )

    department_id = fields.Many2one(
        'hr.department',
        string='Departemen',
        ondelete='restrict',
        check_company=True,
        default=lambda self: self._default_department_id(),
        domain="[('company_id', '=', company_id)]",
        tracking=True,
    )

    @api.model
    def _default_department_id(self):
        department = self.env.user.department_id
        return department.id if department and department.company_id == self.env.company else False

    # ------------------------------------------------------------------
    # SQL CONSTRAINTS
    # ------------------------------------------------------------------
    _amount_positive = models.Constraint(
        'CHECK(amount > 0)',
        'Nominal pendapatan harus lebih besar dari 0!',
    )

    @api.constrains('company_id', 'department_id', 'category_id')
    def _check_company_department_category(self):
        for record in self:
            if not record.department_id:
                raise ValidationError(_('Departemen wajib diisi untuk setiap pendapatan.'))
            if record.department_id.company_id != record.company_id:
                raise ValidationError(_('Departemen harus berasal dari cabang yang sama dengan perusahaan pendapatan.'))
            if record.category_id and record.category_id.company_id != record.company_id:
                raise ValidationError(_('Kategori pendapatan harus berasal dari cabang yang sama.'))

    # ------------------------------------------------------------------
    # CREATE - SEQUENCE
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        self._check_finance_central_readonly()
        for vals in vals_list:
            company = self.env['res.company'].browse(vals.get('company_id') or self.env.company.id).exists()
            if not company:
                raise ValidationError(_('Perusahaan/cabang pendapatan tidak ditemukan.'))
            if company not in self.env.companies:
                raise AccessError(_('Anda tidak memiliki akses ke perusahaan/cabang ini.'))

            department_id = vals.get('department_id') or self.env.user.department_id.id
            department = self.env['hr.department'].browse(department_id).exists()
            if not department:
                raise ValidationError(_('Departemen wajib dipilih sebelum membuat pendapatan.'))
            if department.company_id != company:
                raise ValidationError(_('Departemen harus berasal dari cabang yang sama dengan pendapatan.'))

            category = self.env['pendapatan.category'].browse(vals.get('category_id')).exists()
            if category and category.company_id != company:
                raise ValidationError(_('Kategori pendapatan harus berasal dari cabang yang sama.'))

            vals['company_id'] = company.id
            vals['department_id'] = department.id
            vals.setdefault('currency_id', company.currency_id.id)
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'pendapatan.pendapatan'
                ) or 'New'
        return super(Pendapatan, self).create(vals_list)

    def write(self, vals):
        self._check_finance_central_readonly()
        for record in self:
            company = self.env['res.company'].browse(vals.get('company_id') or record.company_id.id).exists()
            if not company or company not in self.env.companies:
                raise AccessError(_('Anda tidak memiliki akses ke perusahaan/cabang ini.'))
            department = self.env['hr.department'].browse(
                vals.get('department_id') or record.department_id.id
            ).exists()
            if not department or department.company_id != company:
                raise ValidationError(_('Departemen harus berasal dari cabang yang sama dengan pendapatan.'))
            category = self.env['pendapatan.category'].browse(
                vals.get('category_id') or record.category_id.id
            ).exists()
            if category and category.company_id != company:
                raise ValidationError(_('Kategori pendapatan harus berasal dari cabang yang sama.'))
        return super().write(vals)

    def unlink(self):
        self._check_finance_central_readonly()
        return super().unlink()

    # ------------------------------------------------------------------
    # STATE TRANSITIONS - WORKFLOW
    # ------------------------------------------------------------------
    def action_submit(self):
        """Draft → Submitted (oleh user biasa)"""
        self._check_finance_central_readonly()
        if not self.env.user.has_group('pendapatan.group_pendapatan_user'):
            raise AccessError(_('Anda tidak memiliki akses untuk mengajukan pendapatan.'))
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Hanya pendapatan berstatus Draft yang dapat diajukan.'))
            if rec.amount <= 0:
                raise UserError(_('Nominal pendapatan harus lebih besar dari 0.'))
            if not rec.category_id.coa_pendapatan_id:
                raise UserError(_('Kategori "%s" belum memiliki Akun Pendapatan (COA).') % rec.category_id.name)
            if not rec.category_id.coa_kas_id:
                raise UserError(_('Kategori "%s" belum memiliki Akun Kas/Bank Penerima.') % rec.category_id.name)

            rec.write({
                'state': 'submitted',
                'submitted_by_id': self.env.user.id,
                'submitted_date': fields.Datetime.now(),
            })
        return True

    def action_approve(self):
        """Submitted → Approved (oleh manager)"""
        self._check_pendapatan_manager()
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Hanya pendapatan berstatus Diajukan yang dapat disetujui.'))

            rec.write({
                'state': 'approved',
                'approved_by_id': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })
        return True

    def action_reject(self):
        """Submitted → Draft (tolak, kembali ke draft untuk revisi)"""
        self._check_pendapatan_manager()
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Hanya pendapatan berstatus Diajukan yang dapat ditolak.'))
            rec.write({
                'state': 'draft',
                'submitted_by_id': False,
                'submitted_date': False,
            })
        return True

    def action_post(self):
        """Approved → Posted + auto-create Jurnal di sif.jurnal.entry"""
        self._check_pendapatan_manager()
        JurnalEntry = self.env['sif.jurnal.entry']
        JurnalLine = self.env['sif.jurnal.line']

        for rec in self:
            if rec.state != 'approved':
                raise UserError(_('Hanya pendapatan berstatus Disetujui yang dapat diposting.'))
            if rec.journal_id:
                raise UserError(_('Pendapatan ini sudah memiliki jurnal terkait.'))
            if not rec.category_id.coa_pendapatan_id or not rec.category_id.coa_kas_id:
                raise UserError(_('Akun COA Pendapatan dan Kas/Bank pada kategori harus terisi untuk posting.'))

            coa_kas = rec.category_id.coa_kas_id
            coa_pendapatan = rec.category_id.coa_pendapatan_id

            lines = [
                (0, 0, {
                    'account_id': coa_kas.id,
                    'name': _('Pendapatan %s - %s') % (rec.name, rec.period_label or ''),
                    'debit': rec.amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': coa_pendapatan.id,
                    'name': _('Pendapatan %s - %s') % (rec.name, rec.period_label or ''),
                    'debit': 0.0,
                    'credit': rec.amount,
                }),
            ]

            entry_vals = {
                'date': rec.tanggal,
                'ref': rec.name,
                'kwitansi_ref': rec.name,
                'unit_name': rec.department_id.name,
                'company_id': rec.company_id.id,
                'department_id': rec.department_id.id,
                'source_type': 'pendapatan',
                'line_ids': lines,
            }

            entry = JurnalEntry.sudo().create(entry_vals)
            entry.action_post()

            rec.write({
                'state': 'posted',
                'journal_id': entry.id,
                'posted_by_id': self.env.user.id,
                'posted_date': fields.Datetime.now(),
            })

        return True

    def action_cancel(self):
        """Batalkan pendapatan (hanya dari submitted/approved/posted)"""
        self._check_pendapatan_manager()
        for rec in self:
            if rec.state in ('draft', 'cancelled'):
                raise UserError(_('Pendapatan sudah dalam status Draft / Dibatalkan.'))
            if rec.state == 'posted' and rec.journal_id:
                raise UserError(_(
                    'Pendapatan ini sudah terposting dan memiliki jurnal di Buku Besar.\n'
                    'Batalkan jurnal tersebut lebih dulu di modul Jurnal Besar.'
                ))

            rec.write({
                'state': 'cancelled',
                'cancel_reason': rec.cancel_reason or 'Dibatalkan oleh %s' % self.env.user.name,
            })
        return True

    def action_reset_to_draft(self):
        """Kembalikan ke draft (untuk koreksi, hanya manager)"""
        self._check_pendapatan_manager()
        for rec in self:
            if rec.state == 'posted':
                raise UserError(_('Pendapatan yang sudah terposting tidak dapat dikembalikan ke draft.'))
            rec.write({
                'state': 'draft',
                'submitted_by_id': False,
                'submitted_date': False,
                'approved_by_id': False,
                'approved_date': False,
                'cancel_reason': False,
            })
        return True

    # ------------------------------------------------------------------
    # RPC HOOK UNTUK INTEGRASI MODUL LAIN
    # ------------------------------------------------------------------
    @api.model
    def create_pendapatan_from_external(self, vals):
        """
        RPC helper untuk membuat pendapatan dari modul lain.
        Akan langsung mengajukan (action_submit) & auto-approve & post.
        """
        self._check_pendapatan_manager()
        values = dict(vals)
        company = self.env['res.company'].browse(values.get('company_id') or self.env.company.id).exists()
        if not company or company not in self.env.companies:
            raise AccessError(_('Integrasi tidak memiliki akses ke perusahaan/cabang Pendapatan ini.'))
        department = self.env['hr.department'].browse(
            values.get('department_id') or self.env.user.department_id.id
        ).exists()
        if not department or department.company_id != company:
            raise ValidationError(_('Integrasi harus mengirim departemen yang sesuai dengan cabang Pendapatan.'))
        values['company_id'] = company.id
        values['department_id'] = department.id
        rec = self.sudo().create(values)
        rec.action_submit()
        rec.action_approve()
        rec.action_post()
        return rec
