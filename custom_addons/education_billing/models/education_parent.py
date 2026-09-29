# -*- coding: utf-8 -*-
from urllib.parse import quote
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EducationParent(models.Model):
    _name = 'education.parent'
    _description = 'Data Orang Tua / Wali'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    name = fields.Char(
        string='Nama Orang Tua / Wali',
        required=True,
        tracking=True
    )
    relation_type = fields.Selection([
        ('ayah', 'Ayah Kandung'),
        ('ibu', 'Ibu Kandung'),
        ('wali', 'Wali Murid'),
    ], string='Hubungan / Relasi', required=True, default='ayah', tracking=True)

    nik = fields.Char(string='NIK / No. Identitas')
    phone = fields.Char(string='Telepon')
    mobile = fields.Char(string='No. Handphone', tracking=True)
    whatsapp = fields.Char(
        string='No. WhatsApp',
        help='Nomor WhatsApp aktif untuk reminder tagihan SPP/UKT, format: 628123456789',
        tracking=True
    )
    email = fields.Char(string='Email', tracking=True)
    job = fields.Char(string='Pekerjaan')
    address = fields.Text(string='Alamat Rumah')

    student_ids = fields.One2many(
        'education.student',
        'parent_id',
        string='Daftar Anak / Mahasiswa'
    )
    student_count = fields.Integer(
        string='Jumlah Anak',
        compute='_compute_student_count'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company
    )
    active = fields.Boolean(string='Aktif', default=True)

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids.filtered(lambda s: s.active))

    def get_clean_whatsapp_number(self):
        """Format nomor HP ke standard international tanpa 0 di depan (misal: 628xxx)"""
        self.ensure_one()
        raw = self.whatsapp or self.mobile or ''
        clean = ''.join(filter(str.isdigit, raw))
        if clean.startswith('0'):
            clean = '62' + clean[1:]
        elif clean.startswith('8'):
            clean = '62' + clean
        return clean

    def build_whatsapp_url(self, message):
        """Generate URL WhatsApp click-to-chat"""
        self.ensure_one()
        phone = self.get_clean_whatsapp_number()
        if not phone:
            return False
        encoded_msg = quote(message)
        return f"https://api.whatsapp.com/send?phone={phone}&text={encoded_msg}"
