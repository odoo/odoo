# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

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


class EducationBillGenerateWizard(models.TransientModel):
    _name = 'education.bill.generate.wizard'
    _description = 'Wizard Generate Tagihan Massal'

    school_id = fields.Many2one(
        'education.school',
        string='Sekolah / Kampus',
        required=True,
        default=lambda self: self.env['education.school'].search([], limit=1)
    )
    level = fields.Selection(
        related='school_id.level',
        string='Jenjang',
        readonly=True
    )
    target_scope = fields.Selection([
        ('all', 'Semua Siswa di Institusi'),
        ('class', 'Berdasarkan Kelas Tertentu'),
    ], string='Cakupan Tagihan', default='all', required=True)

    class_id = fields.Many2one(
        'education.class',
        string='Pilih Kelas Tertentu',
        domain="[('school_id', '=', school_id)]",
        help='Pilih rombel/kelas yang ingin ditagihkan.'
    )

    bill_type = fields.Selection([
        ('spp', 'SPP Bulanan (Sekolah)'),
        ('ukt', 'UKT Semesteran (Universitas)'),
    ], string='Tipe Tagihan', compute='_compute_bill_type', readonly=True)

    month = fields.Selection(
        MONTH_SELECTIONS,
        string='Bulan Tagihan',
        default=lambda self: str(fields.Date.today().month).zfill(2)
    )
    year = fields.Integer(
        string='Tahun',
        default=lambda self: fields.Date.today().year,
        required=True
    )
    semester = fields.Selection(
        SEMESTER_SELECTIONS,
        string='Semester Tagihan',
        default='ganjil'
    )
    academic_year_id = fields.Many2one(
        'education.academic.year',
        string='Tahun Ajaran',
        default=lambda self: self.env['education.academic.year'].search([('is_current', '=', True)], limit=1),
        required=True
    )

    bill_date = fields.Date(
        string='Tanggal Tagihan',
        required=True,
        default=fields.Date.context_today
    )
    due_date = fields.Date(
        string='Tanggal Jatuh Tempo',
        required=True,
        default=fields.Date.context_today
    )
    target_state = fields.Selection([
        ('unpaid', 'Diajukan (Belum Dibayar)'),
        ('waiting_verification', 'Menunggu Verifikasi'),
        ('verified', 'Terverifikasi (Lunas & Auto Jurnal)'),
        ('draft', 'Draft (Konsep)'),
    ], string='Status Tagihan', default='unpaid', required=True,
       help='Pilih status tagihan yang akan dihasilkan setelah proses generate.')

    select_all = fields.Boolean(
        string='Pilih Semua Siswa yang Siap Ditagih',
        default=True
    )

    preview_line_ids = fields.One2many(
        'education.bill.generate.wizard.line',
        'wizard_id',
        string='Daftar Rencana Tagihan Siswa',
        compute='_compute_preview_lines',
        readonly=False,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        default=lambda self: self.env.company.currency_id
    )
    candidate_count = fields.Integer(
        string='Total Siswa Terdeteksi',
        compute='_compute_summary'
    )
    ready_count = fields.Integer(
        string='Siap Diterbitkan',
        compute='_compute_summary'
    )
    skipped_count = fields.Integer(
        string='Dilewati',
        compute='_compute_summary'
    )
    total_amount_estimated = fields.Monetary(
        string='Estimasi Total Tagihan',
        compute='_compute_summary',
        currency_field='currency_id'
    )

    @api.depends('school_id', 'school_id.level')
    def _compute_bill_type(self):
        for rec in self:
            if rec.school_id and rec.school_id.level == 'univ':
                rec.bill_type = 'ukt'
            else:
                rec.bill_type = 'spp'

    @api.depends('preview_line_ids', 'preview_line_ids.selected', 'preview_line_ids.state_preview', 'preview_line_ids.amount')
    def _compute_summary(self):
        for wiz in self:
            lines = wiz.preview_line_ids
            wiz.candidate_count = len(lines)
            ready_lines = lines.filtered(lambda l: l.state_preview == 'ready')
            selected_ready = lines.filtered(lambda l: l.selected and l.state_preview == 'ready')
            wiz.ready_count = len(selected_ready)
            wiz.skipped_count = len(lines) - len(ready_lines)
            wiz.total_amount_estimated = sum(selected_ready.mapped('amount'))

    def _get_preview_line_vals(self, select_override=None):
        if not self.school_id or not self.academic_year_id:
            return []

        effective_bill_type = self.bill_type or ('ukt' if self.school_id.level == 'univ' else 'spp')

        domain = [
            ('school_id', '=', self.school_id.id),
            ('active', '=', True)
        ]
        if self.target_scope == 'class' and self.class_id:
            domain.append(('class_id', '=', self.class_id.id))
        elif not self.target_scope and self.class_id:
            domain.append(('class_id', '=', self.class_id.id))

        students = self.env['education.student'].search(domain, order='class_id, name')
        vals_list = []

        for st in students:
            amount = st.effective_amount

            # Cek apakah sudah ada tagihan aktif untuk periode ini
            dup_domain = [
                ('student_id', '=', st.id),
                ('bill_type', '=', effective_bill_type),
                ('state', '!=', 'cancelled'),
            ]
            if effective_bill_type == 'spp':
                dup_domain.extend([('month', '=', self.month), ('year', '=', self.year)])
                month_name = dict(MONTH_SELECTIONS).get(self.month, '')
                period_str = f"SPP {month_name} {self.year}"
            else:
                dup_domain.extend([('semester', '=', self.semester), ('academic_year_id', '=', self.academic_year_id.id)])
                sem_name = dict(SEMESTER_SELECTIONS).get(self.semester, '')
                period_str = f"UKT {sem_name} {self.academic_year_id.name}"

            existing = self.env['education.bill'].search(dup_domain, limit=1)

            if existing:
                status = 'already_exists'
                selected = False
            elif amount <= 0:
                status = 'zero_amount'
                selected = False
            else:
                status = 'ready'
                if select_override is not None:
                    selected = bool(select_override)
                else:
                    selected = bool(self.select_all)

            parent = st.parent_id
            contact = parent.whatsapp or parent.mobile or parent.phone or '-' if parent else '-'

            vals_list.append({
                'wizard_id': self.id,
                'student_id': st.id,
                'student_name': st.name or '',
                'student_id_number': st.student_id_number or '',
                'school_id': st.school_id.id if st.school_id else self.school_id.id,
                'school_name': st.school_id.name or self.school_id.name,
                'class_id': st.class_id.id if st.class_id else False,
                'class_name': st.class_id.name if st.class_id else '-',
                'major_id': st.major_id.id if st.major_id else False,
                'major_name': st.major_id.name if st.major_id else '-',
                'parent_id': parent.id if parent else False,
                'parent_name': parent.name if parent else '-',
                'parent_contact': contact,
                'parent_whatsapp': parent.whatsapp or '-' if parent else '-',
                'parent_email': parent.email or '-' if parent and parent.email else '-',
                'bill_type': effective_bill_type,
                'bill_type_label': 'SPP Bulanan (Sekolah)' if effective_bill_type == 'spp' else 'UKT Semesteran (Universitas)',
                'month': self.month if effective_bill_type == 'spp' else False,
                'year': self.year,
                'semester': self.semester if effective_bill_type == 'ukt' else False,
                'academic_year_id': self.academic_year_id.id if self.academic_year_id else False,
                'academic_year_name': self.academic_year_id.name if self.academic_year_id else '-',
                'bill_date': self.bill_date,
                'due_date': self.due_date,
                'period_label': period_str,
                'amount': amount,
                'state_preview': status,
                'selected': selected,
                'currency_id': self.currency_id.id if self.currency_id else False,
            })

        return vals_list

    @api.onchange('target_scope', 'school_id', 'class_id', 'bill_type', 'month', 'year', 'semester', 'academic_year_id')
    def _onchange_filter_parameters(self):
        if self.target_scope == 'all':
            self.class_id = False
        line_vals = self._get_preview_line_vals()
        self.preview_line_ids = [(5, 0, 0)] + [(0, 0, v) for v in line_vals]
        selected_ready_vals = [v for v in line_vals if v.get('selected') and v.get('state_preview') == 'ready']
        self.ready_count = len(selected_ready_vals)
        self.total_amount_estimated = sum(v['amount'] for v in selected_ready_vals)

    @api.onchange('select_all')
    def _onchange_select_all(self):
        line_vals = self._get_preview_line_vals(select_override=self.select_all)
        commands = [(5, 0, 0)] + [(0, 0, v) for v in line_vals]
        self.preview_line_ids = commands
        selected_ready_vals = [v for v in line_vals if v.get('selected') and v.get('state_preview') == 'ready']
        self.ready_count = len(selected_ready_vals)
        self.total_amount_estimated = sum(v['amount'] for v in selected_ready_vals)

    @api.depends('school_id', 'class_id', 'target_scope', 'bill_type', 'month', 'year', 'semester', 'academic_year_id')
    def _compute_preview_lines(self):
        PreviewLine = self.env['education.bill.generate.wizard.line']
        for wiz in self:
            line_vals = wiz._get_preview_line_vals()
            lines = PreviewLine
            for v in line_vals:
                lines |= PreviewLine.new(v)
            wiz.preview_line_ids = lines
            wiz.select_all = True

    def action_generate_bills(self):
        self.ensure_one()
        if not self.school_id:
            raise UserError(_('Silakan pilih Sekolah / Kampus terlebih dahulu.'))

        if self.target_scope == 'class' and not self.class_id:
            raise UserError(_('Silakan pilih Kelas Tertentu yang ingin ditagihkan.'))

        Student = self.env['education.student']
        Bill = self.env['education.bill']

        effective_bill_type = self.bill_type or ('ukt' if self.school_id.level == 'univ' else 'spp')

        # Ambil siswa dari preview lines yang terpilih (jika ada)
        selected_lines = self.preview_line_ids.filtered(lambda l: l.selected and l.state_preview == 'ready')
        
        if self.preview_line_ids:
            target_students = selected_lines.mapped('student_id')
        else:
            # Fallback jika dipanggil via kode/unit-test tanpa UI preview
            domain = [
                ('school_id', '=', self.school_id.id),
                ('active', '=', True)
            ]
            if self.target_scope == 'class' and self.class_id:
                domain.append(('class_id', '=', self.class_id.id))
            elif not self.target_scope and self.class_id:
                domain.append(('class_id', '=', self.class_id.id))
            target_students = Student.search(domain)

        if not target_students:
            raise UserError(_('Tidak ada siswa/mahasiswa yang dipilih untuk diterbitkan tagihannya. Pastikan opsi "Pilih" aktif pada baris siswa yang siap ditagih.'))

        created_bills = self.env['education.bill']
        skipped_count = 0

        for student in target_students:
            amount = student.effective_amount
            if amount <= 0:
                continue

            # Periksa tagihan duplikat untuk periode ini
            dup_domain = [
                ('student_id', '=', student.id),
                ('bill_type', '=', effective_bill_type),
                ('state', '!=', 'cancelled'),
            ]
            if effective_bill_type == 'spp':
                dup_domain.extend([('month', '=', self.month), ('year', '=', self.year)])
            else:
                dup_domain.extend([('semester', '=', self.semester), ('academic_year_id', '=', self.academic_year_id.id)])

            existing = Bill.search(dup_domain, limit=1)
            if existing:
                skipped_count += 1
                continue

            vals = {
                'student_id': student.id,
                'school_id': self.school_id.id,
                'class_id': student.class_id.id if student.class_id else False,
                'major_id': student.major_id.id if student.major_id else False,
                'bill_type': effective_bill_type,
                'month': self.month if effective_bill_type == 'spp' else False,
                'year': self.year,
                'semester': self.semester if effective_bill_type == 'ukt' else False,
                'academic_year_id': self.academic_year_id.id,
                'bill_date': self.bill_date,
                'due_date': self.due_date,
                'amount': amount,
                'company_id': self.school_id.company_id.id,
                'category_id': self.school_id.category_id.id if self.school_id.category_id else False,
                'state': 'unpaid' if self.target_state == 'verified' else (self.target_state or 'unpaid'),
            }

            bill = Bill.create(vals)
            if self.target_state == 'verified':
                bill.action_verify_payment()
            created_bills |= bill

        if not created_bills and skipped_count > 0:
            raise UserError(_('Semua siswa (%d) sudah memiliki tagihan untuk periode ini.') % skipped_count)

        return {
            'name': _('Hasil Generate Tagihan (%d Dibuat, %d Dilewati)') % (len(created_bills), skipped_count),
            'type': 'ir.actions.act_window',
            'res_model': 'education.bill',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_bills.ids)],
            'target': 'current',
        }


class EducationBillGenerateWizardLine(models.TransientModel):
    _name = 'education.bill.generate.wizard.line'
    _description = 'Line Preview Generate Tagihan'

    wizard_id = fields.Many2one('education.bill.generate.wizard', string='Wizard', ondelete='cascade')
    student_id = fields.Many2one('education.student', string='Siswa / Mahasiswa', required=True)
    student_name = fields.Char(string='Nama Siswa', compute='_compute_student_info', store=True, readonly=True)
    student_id_number = fields.Char(string='NISN / NIM', compute='_compute_student_info', store=True, readonly=True)
    school_id = fields.Many2one('education.school', string='Sekolah / Kampus', compute='_compute_student_info', store=True, readonly=True)
    school_name = fields.Char(string='Nama Sekolah', compute='_compute_student_info', store=True, readonly=True)
    class_id = fields.Many2one('education.class', string='Kelas / Rombel', compute='_compute_student_info', store=True, readonly=True)
    class_name = fields.Char(string='Nama Kelas', compute='_compute_student_info', store=True, readonly=True)
    major_id = fields.Many2one('education.major', string='Jurusan / Prodi', compute='_compute_student_info', store=True, readonly=True)
    major_name = fields.Char(string='Nama Jurusan', compute='_compute_student_info', store=True, readonly=True)
    parent_id = fields.Many2one('education.parent', string='Orang Tua / Wali', compute='_compute_student_info', store=True, readonly=True)
    parent_name = fields.Char(string='Nama Orang Tua', compute='_compute_student_info', store=True, readonly=True)
    parent_contact = fields.Char(string='No. WhatsApp / HP', compute='_compute_student_info', store=True, readonly=True)
    parent_whatsapp = fields.Char(string='WhatsApp Orang Tua', compute='_compute_student_info', store=True, readonly=True)
    parent_email = fields.Char(string='Email Orang Tua', compute='_compute_student_info', store=True, readonly=True)

    bill_type = fields.Selection([
        ('spp', 'SPP Bulanan (Sekolah)'),
        ('ukt', 'UKT Semesteran (Universitas)'),
    ], string='Tipe Tagihan')
    bill_type_label = fields.Char(string='Label Tipe Tagihan')
    month = fields.Selection(MONTH_SELECTIONS, string='Bulan Tagihan')
    year = fields.Integer(string='Tahun')
    semester = fields.Selection(SEMESTER_SELECTIONS, string='Semester Tagihan')
    academic_year_id = fields.Many2one('education.academic.year', string='Tahun Ajaran')
    academic_year_name = fields.Char(string='Nama Tahun Ajaran')
    bill_date = fields.Date(string='Tanggal Tagihan')
    due_date = fields.Date(string='Jatuh Tempo')
    period_label = fields.Char(string='Periode Tagihan', readonly=True)
    amount = fields.Monetary(string='Nominal Tarif', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Mata Uang', default=lambda self: self.env.company.currency_id)
    state_preview = fields.Selection([
        ('ready', 'Siap Dibuat'),
        ('already_exists', 'Sudah Ada (Akan Dilewati)'),
        ('zero_amount', 'Tarif Rp 0 (Akan Dilewati)'),
    ], string='Status Rencana', default='ready')
    selected = fields.Boolean(string='Pilih', default=True)
    notes = fields.Text(string='Catatan / Keterangan Tambahan')

    @api.onchange('state_preview')
    def _onchange_state_preview(self):
        if self.state_preview == 'ready':
            self.selected = True
        else:
            self.selected = False
        if self.wizard_id:
            self.wizard_id._compute_summary()

    @api.depends('student_id')
    def _compute_student_info(self):
        for line in self:
            st = line.student_id
            if st:
                line.student_id_number = st.student_id_number or ''
                line.school_id = st.school_id.id if st.school_id else False
                line.school_name = st.school_id.name or '' if st.school_id else ''
                line.class_id = st.class_id.id if st.class_id else False
                line.class_name = st.class_id.name or '-' if st.class_id else '-'
                line.major_id = st.major_id.id if st.major_id else False
                line.major_name = st.major_id.name or '-' if st.major_id else '-'
                line.parent_id = st.parent_id.id if st.parent_id else False
                line.parent_name = st.parent_id.name or '-' if st.parent_id else '-'
                line.parent_contact = st.parent_id.whatsapp or st.parent_id.mobile or st.parent_id.phone or '-' if st.parent_id else '-'
                line.parent_whatsapp = st.parent_id.whatsapp or st.parent_id.mobile or st.parent_id.phone or '-' if st.parent_id else '-'
                line.parent_email = st.parent_id.email or '-' if st.parent_id and st.parent_id.email else '-'
                line.student_name = st.name or ''
            else:
                line.student_id_number = ''
                line.school_id = False
                line.school_name = ''
                line.class_id = False
                line.class_name = ''
                line.major_id = False
                line.major_name = ''
                line.parent_id = False
                line.parent_name = ''
                line.parent_contact = ''
                line.parent_whatsapp = ''
                line.parent_email = ''
                line.student_name = ''

    @api.onchange('selected')
    def _onchange_selected(self):
        if self.wizard_id:
            self.wizard_id._compute_summary()

    def action_open_student_master(self):
        self.ensure_one()
        if not self.student_id:
            return False
        return {
            'name': _('Detail Profil Siswa: %s') % (self.student_name or self.student_id.name),
            'type': 'ir.actions.act_window',
            'res_model': 'education.student',
            'res_id': self.student_id.id,
            'view_mode': 'form',
            'target': 'new',
        }
