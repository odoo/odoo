# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EducationSchool(models.Model):
    _name = 'education.school'
    _description = 'Institusi Pendidikan (Sekolah / Kampus)'
    _order = 'level asc, name asc'
    _rec_name = 'display_name'

    name = fields.Char(
        string='Nama Institusi',
        required=True,
        help='Contoh: SMP SIF 1, SMA SIF Unggulan, Universitas SIF'
    )
    code = fields.Char(
        string='Kode Institusi',
        required=True,
        index=True,
        help='Contoh: SMP01, SMA01, SMK01, UNIV01'
    )
    level = fields.Selection([
        ('smp', 'SMP (Sekolah Menengah Pertama)'),
        ('sma', 'SMA (Sekolah Menengah Atas)'),
        ('smk', 'SMK (Sekolah Menengah Kejuruan)'),
        ('univ', 'Universitas / Perguruan Tinggi'),
    ], string='Jenjang Pendidikan', required=True, default='smp')

    display_name = fields.Char(
        string='Tampilan',
        compute='_compute_display_name',
        store=True
    )

    phone = fields.Char(string='Telepon')
    email = fields.Char(string='Email')
    address = fields.Text(string='Alamat')

    default_spp_amount = fields.Monetary(
        string='Tarif Default SPP (Bulanan)',
        currency_field='currency_id',
        default=0.0,
        help='Nominal acuan SPP bulanan untuk jenjang SMP/SMA/SMK'
    )
    default_ukt_amount = fields.Monetary(
        string='Tarif Default UKT (Semesteran)',
        currency_field='currency_id',
        default=0.0,
        help='Nominal acuan UKT per semester untuk jenjang Universitas'
    )

    category_id = fields.Many2one(
        'pendapatan.category',
        string='Kategori Pendapatan',
        required=True,
        ondelete='restrict',
        help='Kategori di modul pendapatan untuk auto-journaling dan COA'
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

    major_ids = fields.One2many(
        'education.major',
        'school_id',
        string='Jurusan / Program Studi'
    )
    class_ids = fields.One2many(
        'education.class',
        'school_id',
        string='Daftar Kelas'
    )
    student_count = fields.Integer(
        string='Jumlah Siswa',
        compute='_compute_student_count'
    )

    active = fields.Boolean(string='Aktif', default=True)

    _code_company_uniq = models.Constraint(
        'unique(code, company_id)',
        'Kode institusi pendidikan harus unik per perusahaan!',
    )

    @api.depends('code', 'name', 'level')
    def _compute_display_name(self):
        level_map = dict(self._fields['level'].selection)
        for rec in self:
            rec.display_name = f"[{rec.code}] {rec.name} ({level_map.get(rec.level, '')})" if rec.code else rec.name

    def _compute_student_count(self):
        for rec in self:
            rec.student_count = self.env['education.student'].search_count([
                ('school_id', '=', rec.id),
                ('active', '=', True)
            ])
