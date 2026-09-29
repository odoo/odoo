# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EducationStudent(models.Model):
    _name = 'education.student'
    _description = 'Data Siswa / Mahasiswa'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'school_id asc, class_id asc, name asc'
    _rec_name = 'display_name'

    name = fields.Char(
        string='Nama Lengkap',
        required=True,
        tracking=True
    )
    student_id_number = fields.Char(
        string='Nomor Induk (NISN / NIM)',
        required=True,
        index=True,
        tracking=True,
        help='NIS/NISN untuk siswa sekolah atau NIM untuk mahasiswa universitas'
    )
    display_name = fields.Char(
        string='Tampilan',
        compute='_compute_display_name',
        store=True
    )

    school_id = fields.Many2one(
        'education.school',
        string='Sekolah / Kampus',
        required=True,
        tracking=True
    )
    level = fields.Selection(
        related='school_id.level',
        string='Jenjang',
        store=True
    )
    major_id = fields.Many2one(
        'education.major',
        string='Jurusan / Program Studi',
        domain="[('school_id', '=', school_id)]",
        tracking=True
    )
    class_id = fields.Many2one(
        'education.class',
        string='Kelas / Rombel',
        domain="[('school_id', '=', school_id)]",
        tracking=True
    )

    parent_id = fields.Many2one(
        'education.parent',
        string='Orang Tua / Wali',
        tracking=True,
        ondelete='restrict',
        help='Orang tua / wali yang akan menerima reminder tagihan SPP/UKT'
    )
    parent_whatsapp = fields.Char(
        related='parent_id.whatsapp',
        string='WhatsApp Orang Tua',
        readonly=True
    )
    parent_email = fields.Char(
        related='parent_id.email',
        string='Email Orang Tua',
        readonly=True
    )
    parent_mobile = fields.Char(
        related='parent_id.mobile',
        string='HP Orang Tua',
        readonly=True
    )

    gender = fields.Selection([
        ('male', 'Laki-laki'),
        ('female', 'Perempuan'),
    ], string='Jenis Kelamin', default='male')
    birth_date = fields.Date(string='Tanggal Lahir')
    phone = fields.Char(string='No. HP Siswa / Mahasiswa')
    email = fields.Char(string='Email Siswa / Mahasiswa')
    address = fields.Text(string='Alamat')

    # Skema Tarif Tagihan (Otomatis berdasarkan Jenjang Sekolah / Kampus)
    billing_scheme = fields.Selection([
        ('spp_bulanan', 'SPP Bulanan (Sekolah)'),
        ('ukt_semester', 'UKT Semesteran (Universitas)'),
    ], string='Skema Tagihan', compute='_compute_billing_scheme', store=True, readonly=True, tracking=True)

    custom_amount = fields.Monetary(
        string='Tarif Khusus / Beasiswa',
        currency_field='currency_id',
        default=0.0,
        help='Isi jika siswa/mahasiswa ini memiliki tarif khusus (misal beasiswa/potongan). Jika 0, memakai tarif kelas/sekolah.'
    )
    effective_amount = fields.Monetary(
        string='Tarif Tagihan Berlaku',
        currency_field='currency_id',
        compute='_compute_effective_amount',
        store=True,
        help='Tarif final yang digunakan untuk generate tagihan otomatis.'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Kontak Terkait (Partner)',
        help='Partner res.partner untuk sinkronisasi jika diperlukan'
    )

    bill_ids = fields.One2many(
        'education.bill',
        'student_id',
        string='Daftar Tagihan'
    )
    total_bills_count = fields.Integer(
        string='Total Tagihan',
        compute='_compute_bill_stats'
    )
    unpaid_bills_count = fields.Integer(
        string='Tagihan Belum Lunas',
        compute='_compute_bill_stats'
    )
    total_unpaid_amount = fields.Monetary(
        string='Total Tunggakan',
        currency_field='currency_id',
        compute='_compute_bill_stats'
    )

    active = fields.Boolean(string='Aktif', default=True)

    _student_id_number_company_uniq = models.Constraint(
        'unique(student_id_number, company_id)',
        'Nomor Induk (NISN/NIM) harus unik per perusahaan!',
    )

    @api.depends('student_id_number', 'name', 'class_id')
    def _compute_display_name(self):
        for rec in self:
            class_str = f" - {rec.class_id.name}" if rec.class_id else ""
            rec.display_name = f"[{rec.student_id_number}] {rec.name}{class_str}"

    @api.depends('school_id', 'school_id.level')
    def _compute_billing_scheme(self):
        for rec in self:
            if rec.school_id and rec.school_id.level == 'univ':
                rec.billing_scheme = 'ukt_semester'
            else:
                rec.billing_scheme = 'spp_bulanan'

    @api.depends('custom_amount', 'class_id', 'class_id.monthly_spp_amount', 'class_id.semester_ukt_amount',
                 'school_id', 'school_id.default_spp_amount', 'school_id.default_ukt_amount', 'billing_scheme')
    def _compute_effective_amount(self):
        for rec in self:
            if rec.custom_amount > 0:
                rec.effective_amount = rec.custom_amount
            elif rec.billing_scheme == 'ukt_semester':
                if rec.class_id and rec.class_id.semester_ukt_amount > 0:
                    rec.effective_amount = rec.class_id.semester_ukt_amount
                elif rec.school_id:
                    rec.effective_amount = rec.school_id.default_ukt_amount
                else:
                    rec.effective_amount = 0.0
            else:
                if rec.class_id and rec.class_id.monthly_spp_amount > 0:
                    rec.effective_amount = rec.class_id.monthly_spp_amount
                elif rec.school_id:
                    rec.effective_amount = rec.school_id.default_spp_amount
                else:
                    rec.effective_amount = 0.0

    def _compute_bill_stats(self):
        for rec in self:
            bills = rec.bill_ids
            rec.total_bills_count = len(bills)
            unpaid = bills.filtered(lambda b: b.state in ('unpaid', 'waiting_verification', 'rejected'))
            rec.unpaid_bills_count = len(unpaid)
            rec.total_unpaid_amount = sum(unpaid.mapped('amount'))
