# -*- coding: utf-8 -*-
from urllib.parse import quote
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import html_escape


MONTH_SELECTIONS = [
    ('01', 'Januari'),
    ('02', 'Februari'),
    ('03', 'Maret'),
    ('04', 'April'),
    ('05', 'Mei'),
    ('06', 'Juni'),
    ('07', 'Juli'),
    ('08', 'Agustus'),
    ('09', 'September'),
    ('10', 'Oktober'),
    ('11', 'November'),
    ('12', 'Desember'),
]

SEMESTER_SELECTIONS = [
    ('ganjil', 'Semester Ganjil'),
    ('genap', 'Semester Genap'),
    ('1', 'Semester 1'),
    ('2', 'Semester 2'),
    ('3', 'Semester 3'),
    ('4', 'Semester 4'),
    ('5', 'Semester 5'),
    ('6', 'Semester 6'),
    ('7', 'Semester 7'),
    ('8', 'Semester 8'),
]


class EducationBill(models.Model):
    _name = 'education.bill'
    _description = 'Tagihan Pendidikan (SPP / UKT)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'bill_date desc, id desc'

    name = fields.Char(
        string='Nomor Tagihan',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        tracking=True,
        index=True
    )

    student_id = fields.Many2one(
        'education.student',
        string='Siswa / Mahasiswa',
        required=True,
        tracking=True,
        index=True,
        ondelete='restrict'
    )
    student_id_number = fields.Char(
        related='student_id.student_id_number',
        string='NISN / NIM',
        readonly=True,
        store=True
    )
    school_id = fields.Many2one(
        'education.school',
        string='Sekolah / Kampus',
        required=True,
        tracking=True,
        index=True
    )
    level = fields.Selection(
        related='school_id.level',
        string='Jenjang',
        store=True
    )
    class_id = fields.Many2one(
        'education.class',
        string='Kelas / Rombel',
        domain="[('school_id', '=', school_id)]",
        tracking=True
    )
    major_id = fields.Many2one(
        'education.major',
        string='Jurusan / Prodi',
        domain="[('school_id', '=', school_id)]"
    )

    # Data Orang Tua / Wali untuk Reminder
    parent_id = fields.Many2one(
        'education.parent',
        related='student_id.parent_id',
        string='Orang Tua / Wali',
        store=True,
        readonly=True
    )
    parent_whatsapp = fields.Char(
        related='student_id.parent_whatsapp',
        string='WhatsApp Orang Tua',
        readonly=True
    )
    parent_email = fields.Char(
        related='student_id.parent_email',
        string='Email Orang Tua',
        readonly=True
    )
    parent_mobile = fields.Char(
        related='student_id.parent_mobile',
        string='No. HP Orang Tua',
        readonly=True
    )

    bill_type = fields.Selection([
        ('spp', 'SPP Bulanan'),
        ('ukt', 'UKT Semesteran'),
        ('admission', 'Uang Masuk / Gedung'),
        ('other', 'Biaya Pendidikan Lainnya'),
    ], string='Tipe Tagihan', required=True, default='spp', tracking=True)

    month = fields.Selection(
        MONTH_SELECTIONS,
        string='Bulan',
        help='Bulan tagihan untuk SPP bulanan'
    )
    year = fields.Integer(
        string='Tahun',
        default=lambda self: fields.Date.today().year,
        required=True
    )
    semester = fields.Selection(
        SEMESTER_SELECTIONS,
        string='Semester',
        help='Semester tagihan untuk UKT'
    )
    academic_year_id = fields.Many2one(
        'education.academic.year',
        string='Tahun Ajaran',
        default=lambda self: self.env['education.academic.year'].search([('is_current', '=', True)], limit=1)
    )
    period_label = fields.Char(
        string='Periode Tagihan',
        compute='_compute_period_label',
        store=True,
        tracking=True
    )

    bill_date = fields.Date(
        string='Tanggal Tagihan',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    due_date = fields.Date(
        string='Jatuh Tempo',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )

    amount = fields.Monetary(
        string='Nominal Tagihan',
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
    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company
    )

    # State Workflow
    state = fields.Selection([
        ('draft', 'Draft'),
        ('unpaid', 'Belum Dibayar'),
        ('waiting_verification', 'Menunggu Verifikasi'),
        ('verified', 'Terverifikasi / Lunas'),
        ('rejected', 'Bukti Ditolak'),
        ('cancelled', 'Dibatalkan'),
    ], string='Status Tagihan', default='draft', required=True, tracking=True, index=True)

    # Detail Pembayaran & Bukti
    payment_date = fields.Date(
        string='Tanggal Bayar',
        tracking=True
    )
    payment_method = fields.Selection([
        ('transfer', 'Transfer Bank'),
        ('cash', 'Kasir / Tunai'),
        ('va', 'Virtual Account'),
        ('qris', 'QRIS'),
    ], string='Metode Pembayaran', default='transfer', tracking=True)
    payment_ref = fields.Char(
        string='No. Ref / Bukti Transfer',
        tracking=True,
        help='Nomor transaksi transfer bank / struk pembayaran'
    )
    payment_proof = fields.Binary(
        string='Bukti Pembayaran',
        attachment=True
    )
    payment_proof_filename = fields.Char(string='Nama File Bukti')

    # Verifikasi Staf
    verified_by_id = fields.Many2one(
        'res.users',
        string='Diverifikasi Oleh',
        readonly=True,
        tracking=True
    )
    verified_date = fields.Datetime(
        string='Waktu Verifikasi',
        readonly=True,
        tracking=True
    )
    reject_reason = fields.Text(
        string='Alasan Penolakan',
        readonly=True,
        tracking=True
    )
    notes = fields.Text(string='Catatan Tambahan')

    # Integrasi ke Modul Pendapatan & Jurnal Besar
    category_id = fields.Many2one(
        'pendapatan.category',
        string='Kategori Pendapatan',
        compute='_compute_category_id',
        store=True,
        readonly=False,
        help='Kategori pendapatan untuk memicu auto-journaling'
    )
    pendapatan_id = fields.Many2one(
        'pendapatan.pendapatan',
        string='Dokumen Pendapatan',
        readonly=True,
        copy=False,
        ondelete='restrict'
    )
    journal_id = fields.Many2one(
        'sif.jurnal.entry',
        related='pendapatan_id.journal_id',
        string='Jurnal Buku Besar',
        readonly=True,
        store=True
    )

    # Reminder Stats
    reminder_count = fields.Integer(
        string='Jumlah Reminder Terkirim',
        default=0,
        readonly=True
    )
    last_reminder_date = fields.Datetime(
        string='Reminder Terakhir',
        readonly=True
    )

    _amount_positive = models.Constraint(
        'CHECK(amount > 0)',
        'Nominal tagihan harus lebih besar dari 0!',
    )

    @api.depends('student_id')
    def _onchange_student_id(self):
        for rec in self:
            if rec.student_id:
                rec.school_id = rec.student_id.school_id.id
                rec.class_id = rec.student_id.class_id.id
                rec.major_id = rec.student_id.major_id.id
                if not rec.amount or rec.amount == 0.0:
                    rec.amount = rec.student_id.effective_amount
                if rec.student_id.billing_scheme == 'ukt_semester':
                    rec.bill_type = 'ukt'
                else:
                    rec.bill_type = 'spp'

    @api.depends('school_id', 'school_id.category_id')
    def _compute_category_id(self):
        for rec in self:
            if rec.school_id and rec.school_id.category_id:
                rec.category_id = rec.school_id.category_id.id
            elif not rec.category_id:
                default_cat = self.env['pendapatan.category'].search([('code', '=', 'SPP-NON-AFILIASI')], limit=1)
                rec.category_id = default_cat.id if default_cat else False

    @api.depends('bill_type', 'month', 'year', 'semester', 'academic_year_id')
    def _compute_period_label(self):
        month_dict = dict(MONTH_SELECTIONS)
        semester_dict = dict(SEMESTER_SELECTIONS)
        for rec in self:
            if rec.bill_type == 'spp':
                month_name = month_dict.get(rec.month, '')
                year_str = str(rec.year) if rec.year else ''
                rec.period_label = f"SPP {month_name} {year_str}".strip()
            elif rec.bill_type == 'ukt':
                sem_name = semester_dict.get(rec.semester, '')
                ta_name = rec.academic_year_id.name if rec.academic_year_id else ''
                rec.period_label = f"UKT {sem_name} {ta_name}".strip()
            elif rec.bill_type == 'admission':
                ta_name = rec.academic_year_id.name if rec.academic_year_id else ''
                rec.period_label = f"Uang Masuk / Gedung {ta_name}".strip()
            else:
                rec.period_label = f"Biaya Pendidikan {rec.year or ''}".strip()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('education.bill') or 'New'
        return super(EducationBill, self).create(vals_list)

    # ---------------------------------------------------------
    # WORKFLOW ACTIONS
    # ---------------------------------------------------------
    def action_publish_bill(self):
        """Draft -> Unpaid (Tagihan Diterbitkan)"""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Hanya tagihan berstatus Draft yang dapat diterbitkan.'))
            if rec.amount <= 0:
                raise UserError(_('Nominal tagihan harus lebih besar dari 0.'))
            rec.write({'state': 'unpaid'})
        return True

    def action_submit_payment(self):
        """Unpaid / Rejected -> Waiting Verification (Staf / Siswa upload bukti bayar)"""
        for rec in self:
            if rec.state not in ('unpaid', 'rejected', 'draft'):
                raise UserError(_('Tagihan tidak dalam status yang dapat mengajukan verifikasi.'))
            if not rec.payment_date:
                rec.payment_date = fields.Date.context_today(self)
            rec.write({
                'state': 'waiting_verification',
                'reject_reason': False
            })
        return True

    def action_verify_payment(self):
        """
        Waiting Verification / Unpaid -> Verified (Lunas)
        Otomatis membuat record di `pendapatan.pendapatan` & auto-post ke `sif.jurnal.entry`
        """
        for rec in self:
            if rec.state not in ('waiting_verification', 'unpaid'):
                raise UserError(_('Hanya tagihan berstatus Menunggu Verifikasi atau Belum Dibayar yang dapat diverifikasi.'))

            if not rec.category_id:
                raise UserError(_('Kategori Pendapatan belum terisi pada tagihan %s.') % rec.name)
            if not rec.category_id.coa_pendapatan_id or not rec.category_id.coa_kas_id:
                raise UserError(_('Kategori Pendapatan "%s" belum memiliki COA Pendapatan atau COA Kas/Bank.') % rec.category_id.name)

            payment_date = rec.payment_date or fields.Date.context_today(self)

            # Buat entri di modul Pendapatan
            pendapatan_vals = {
                'tanggal': payment_date,
                'period_label': f"{rec.period_label} - {rec.student_id.name} ({rec.student_id.student_id_number})",
                'category_id': rec.category_id.id,
                'amount': rec.amount,
                'unit_name': rec.school_id.name,
                'source_partner_id': rec.student_id.partner_id.id if rec.student_id.partner_id else False,
                'description': _('Pembayaran %s a.n %s (%s) - Kelas: %s') % (
                    rec.period_label,
                    rec.student_id.name,
                    rec.student_id.student_id_number,
                    rec.class_id.name if rec.class_id else '-'
                ),
                'attachment': rec.payment_proof,
                'company_id': rec.company_id.id,
            }

            pendapatan_rec = self.env['pendapatan.pendapatan'].sudo().create_pendapatan_from_external(pendapatan_vals)

            rec.write({
                'state': 'verified',
                'payment_date': payment_date,
                'verified_by_id': self.env.user.id,
                'verified_date': fields.Datetime.now(),
                'pendapatan_id': pendapatan_rec.id,
                'reject_reason': False,
            })

            rec.message_post(body=_("Pembayaran telah diverifikasi oleh %s. Dokumen Pendapatan: %s, Jurnal: %s") % (
                self.env.user.name,
                pendapatan_rec.name,
                pendapatan_rec.journal_id.name if pendapatan_rec.journal_id else '-'
            ))

        return True

    def action_reject_payment_wizard(self):
        """Membuka pop-up reject wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tolak Verifikasi Pembayaran'),
            'res_model': 'education.bill.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_bill_id': self.id}
        }

    def action_cancel(self):
        """Membatalkan tagihan"""
        for rec in self:
            if rec.state == 'verified':
                raise UserError(_('Tagihan yang sudah diverifikasi (Lunas) tidak dapat dibatalkan secara langsung. Harap periksa modul Pendapatan & Jurnal Keuangan.'))
            rec.write({'state': 'cancelled'})
        return True

    def action_reset_draft(self):
        """Kembalikan ke status Draft"""
        for rec in self:
            if rec.state == 'verified':
                raise UserError(_('Tagihan yang sudah diverifikasi tidak dapat direset ke draft.'))
            rec.write({
                'state': 'draft',
                'verified_by_id': False,
                'verified_date': False,
                'reject_reason': False,
            })
        return True

    # ---------------------------------------------------------
    # MASS WORKFLOW ACTIONS
    # ---------------------------------------------------------
    def action_mass_verify_payment(self):
        """Mass Action: Verifikasi & Tandai Lunas seluruh record yang dipilih"""
        valid_bills = self.filtered(lambda r: r.state in ('unpaid', 'waiting_verification', 'draft'))
        for b in valid_bills:
            if b.state == 'draft':
                b.action_publish_bill()
            b.action_verify_payment()
        return True

    def action_mass_submit_payment(self):
        """Mass Action: Ajukan Pembayaran seluruh record yang dipilih"""
        valid_bills = self.filtered(lambda r: r.state in ('unpaid', 'draft', 'rejected'))
        for b in valid_bills:
            b.action_submit_payment()
        return True

    def action_mass_publish_bill(self):
        """Mass Action: Terbitkan Tagihan seluruh record draft yang dipilih"""
        valid_bills = self.filtered(lambda r: r.state == 'draft')
        for b in valid_bills:
            b.action_publish_bill()
        return True

    def action_mass_cancel(self):
        """Mass Action: Batalkan seluruh record non-lunas yang dipilih"""
        valid_bills = self.filtered(lambda r: r.state != 'verified')
        for b in valid_bills:
            b.action_cancel()
        return True

    # ---------------------------------------------------------
    # REMINDER HELPER (WhatsApp & Email)
    # ---------------------------------------------------------
    def get_reminder_message(self):
        """Menyusun teks reminder pembayaran"""
        self.ensure_one()
        school_name = self.school_id.name or 'Sekolah/Kampus'
        student_name = self.student_id.name or '-'
        nisn_nim = self.student_id.student_id_number or '-'
        period = self.period_label or '-'
        amount_fmt = f"Rp {self.amount:,.0f}".replace(',', '.')
        due_date_fmt = self.due_date.strftime('%d/%m/%Y') if self.due_date else '-'

        msg = (
            f"Yth. Bapak/Ibu Orang Tua/Wali dari {student_name} ({nisn_nim}),\n\n"
            f"Kami menginformasikan tagihan biaya pendidikan dari {school_name}:\n"
            f"• Jenis/Periode: {period}\n"
            f"• Nominal: {amount_fmt}\n"
            f"• Batas Pembayaran (Jatuh Tempo): {due_date_fmt}\n"
            f"• Status: Belum Lunas\n\n"
            f"Mohon untuk segera melakukan pembayaran dan konfirmasi kepada pihak sekolah/kampus. "
            f"Abaikan pesan ini jika sudah melakukan pembayaran.\n\n"
            f"Terima kasih.\n{school_name}"
        )
        return msg

    def action_send_whatsapp_reminder(self):
        """Membuka link WhatsApp web untuk mengirim reminder ke Orang Tua"""
        self.ensure_one()
        parent = self.parent_id
        if not parent:
            raise UserError(_('Data Orang Tua / Wali belum terisi pada siswa %s.') % self.student_id.name)

        clean_phone = parent.get_clean_whatsapp_number()
        if not clean_phone:
            raise UserError(_('Nomor WhatsApp Orang Tua (%s) belum valid.') % parent.name)

        msg = self.get_reminder_message()
        url = parent.build_whatsapp_url(msg)

        # Update stats
        self.write({
            'reminder_count': self.reminder_count + 1,
            'last_reminder_date': fields.Datetime.now()
        })
        self.message_post(body=_("Reminder WhatsApp dikirimkan ke Orang Tua (%s - %s)") % (parent.name, clean_phone))

        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }

    def action_send_email_reminder(self):
        """Kirim reminder via chatter / email"""
        for rec in self:
            parent = rec.parent_id
            email_target = parent.email if parent and parent.email else rec.student_id.email
            if not email_target:
                raise UserError(_('Email Orang Tua atau Siswa belum diisi.'))

            plain_body = rec.get_reminder_message()
            html_body = html_escape(plain_body).replace('\n', '<br/>')
            rec.message_post(
                body=f"<b>Pemberitahuan Tagihan Pendidikan</b><br/>{html_body}",
                subject=f"Tagihan {rec.period_label} - {rec.student_id.name}",
                partner_ids=[rec.student_id.partner_id.id] if rec.student_id.partner_id else [],
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )
            rec.write({
                'reminder_count': rec.reminder_count + 1,
                'last_reminder_date': fields.Datetime.now()
            })
        return True
