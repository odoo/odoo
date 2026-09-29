# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EducationAcademicYear(models.Model):
    _name = 'education.academic.year'
    _description = 'Tahun Ajaran Akademik'
    _order = 'start_date desc, name desc'

    name = fields.Char(
        string='Tahun Ajaran',
        required=True,
        help='Contoh: 2025/2026, 2026/2027'
    )
    code = fields.Char(
        string='Kode',
        required=True,
        index=True,
        help='Contoh: TA2526'
    )
    start_date = fields.Date(
        string='Tanggal Mulai',
        required=True
    )
    end_date = fields.Date(
        string='Tanggal Selesai',
        required=True
    )
    is_current = fields.Boolean(
        string='Tahun Ajaran Aktif',
        default=False
    )
    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company
    )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.start_date >= rec.end_date:
                raise ValidationError(_('Tanggal mulai harus lebih awal dari tanggal selesai!'))

    def set_as_current(self):
        self.ensure_one()
        self.search([('company_id', '=', self.company_id.id)]).write({'is_current': False})
        self.write({'is_current': True})


class EducationMajor(models.Model):
    _name = 'education.major'
    _description = 'Jurusan / Program Studi'
    _order = 'school_id asc, name asc'

    name = fields.Char(
        string='Nama Jurusan / Prodi',
        required=True,
        help='Contoh: Rekayasa Perangkat Lunak, Teknik Komputer, Manajemen Bisnis'
    )
    code = fields.Char(
        string='Kode Jurusan',
        required=True
    )
    school_id = fields.Many2one(
        'education.school',
        string='Sekolah / Kampus',
        required=True,
        ondelete='cascade'
    )
    level = fields.Selection(
        related='school_id.level',
        string='Jenjang',
        store=True
    )
    description = fields.Text(string='Keterangan')


class EducationClass(models.Model):
    _name = 'education.class'
    _description = 'Kelas / Rombel'
    _order = 'school_id asc, name asc'

    name = fields.Char(
        string='Nama Kelas',
        required=True,
        help='Contoh: VII-A, X-RPL-1, TI-Semester 2'
    )
    code = fields.Char(
        string='Kode Kelas',
        required=True
    )
    school_id = fields.Many2one(
        'education.school',
        string='Sekolah / Kampus',
        required=True,
        ondelete='cascade'
    )
    major_id = fields.Many2one(
        'education.major',
        string='Jurusan / Program Studi',
        domain="[('school_id', '=', school_id)]"
    )
    academic_year_id = fields.Many2one(
        'education.academic.year',
        string='Tahun Ajaran',
        default=lambda self: self.env['education.academic.year'].search([('is_current', '=', True)], limit=1),
        required=True
    )
    level = fields.Selection(
        related='school_id.level',
        string='Jenjang',
        store=True
    )
    student_ids = fields.One2many(
        'education.student',
        'class_id',
        string='Daftar Siswa/Mahasiswa'
    )
    student_count = fields.Integer(
        string='Jumlah Siswa',
        compute='_compute_student_count'
    )
    monthly_spp_amount = fields.Monetary(
        string='Tarif SPP Kelas (Bulanan)',
        currency_field='currency_id',
        help='Kosongkan jika mengikuti tarif default sekolah atau tarif khusus per siswa'
    )
    semester_ukt_amount = fields.Monetary(
        string='Tarif UKT Kelas (Semesteran)',
        currency_field='currency_id',
        help='Kosongkan jika mengikuti tarif default universitas atau tarif khusus per mahasiswa'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids.filtered(lambda s: s.active))
