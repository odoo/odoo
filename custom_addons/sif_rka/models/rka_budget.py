from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


MONTHS = [
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


class RkaBudget(models.Model):
    _name = 'sif.rka.budget'
    _description = 'Rencana Kerja dan Anggaran'
    _order = 'tahun desc, id desc'

    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        default=lambda self: self.env.company,
        index=True,
        ondelete='restrict',
    )

    name = fields.Char(
        string='Nomor RKA',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    account_id = fields.Many2one(
        'sif.coa',
        string='Account / COA',
        required=True,
        ondelete='restrict'
    )

    tahun = fields.Selection(
        selection=lambda self: [
            (str(year), str(year))
            for year in range(2020, 2031)
        ],
        string='Tahun',
        required=True,
        default=lambda self: str(fields.Date.today().year)
    )

    nilai = fields.Monetary(
        string='Anggaran Tahunan',
        required=True,
        default=0.0,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        required=True,
        default=lambda self: self.env.company.currency_id
    )

    dashboard_year = fields.Boolean(
        string='Tahun Dashboard',
        search='_search_dashboard_year'
    )

    realisasi = fields.Monetary(
        string='Realisasi Tahunan',
        compute='_compute_realisasi',
        currency_field='currency_id'
    )

    sisa_anggaran = fields.Monetary(
        string='Sisa Anggaran',
        compute='_compute_sisa_anggaran',
        currency_field='currency_id'
    )

    persentase_realisasi = fields.Float(
        string='% Realisasi',
        compute='_compute_persentase_realisasi'
    )

    status = fields.Selection(
        [
            ('draft', 'Draft'),
            ('submitted', 'Diajukan'),
            ('approved', 'Disetujui'),
            ('rejected', 'Ditolak'),
        ],
        string='Status',
        default='draft',
        required=True
    )

    tanggal_pengajuan = fields.Datetime(
        string='Tanggal Pengajuan',
        readonly=True
    )

    tanggal_approval = fields.Datetime(
        string='Tanggal Approval',
        readonly=True
    )

    catatan_approval = fields.Text(
        string='Catatan Approval'
    )

    monthly_budget_ids = fields.One2many(
        'sif.rka.budget.month',
        'rka_id',
        string='Anggaran Bulanan',
        copy=False
    )

    total_anggaran_bulanan = fields.Monetary(
        string='Total Anggaran Bulanan',
        compute='_compute_total_anggaran_bulanan',
        currency_field='currency_id'
    )

    sisa_alokasi_bulanan = fields.Monetary(
        string='Sisa Alokasi',
        compute='_compute_total_anggaran_bulanan',
        currency_field='currency_id'
    )

    _company_account_tahun_unique = models.Constraint(
        'UNIQUE(company_id, account_id, tahun)',
        'RKA untuk perusahaan, account, dan tahun tersebut sudah tersedia.'
    )

    @api.model
    def _journal_company_scope_domain(self, company):
        main_company = self.env.ref('base.main_company')
        if company == main_company:
            return ['|', ('company_id', '=', False), ('company_id', '=', company.id)]
        return [('company_id', '=', company.id)]

    def _check_finance_central_readonly(self):
        if self.env.user.has_group('sif_keuangan.group_sif_keuangan_central_readonly'):
            raise AccessError('Finance pusat memiliki akses baca saja pada RKA.')

    @api.model
    def _search_dashboard_year(self, operator, value):
        tahun_sekarang = fields.Date.today().year
        tahun_sebelumnya = tahun_sekarang - 1

        tahun_dashboard = [
            str(tahun_sekarang),
            str(tahun_sebelumnya)
        ]

        if operator == '=':
            if value:
                return [
                    ('tahun', 'in', tahun_dashboard)
                ]

            return [
                ('tahun', 'not in', tahun_dashboard)
            ]

        if operator == '!=':
            if value:
                return [
                    ('tahun', 'not in', tahun_dashboard)
                ]

            return [
                ('tahun', 'in', tahun_dashboard)
            ]

        return []

    @api.model_create_multi
    def create(self, vals_list):
        self._check_finance_central_readonly()
        records = self.env['sif.rka.budget']

        for vals in vals_list:
            company = self.env['res.company'].browse(vals.get('company_id') or self.env.company.id).exists()
            if not company or company not in self.env.companies:
                raise ValidationError('Perusahaan/cabang RKA tidak valid atau tidak diizinkan.')
            vals['company_id'] = company.id
            existing = self.sudo().search([
                ('company_id', '=', company.id),
                ('account_id', '=', vals.get('account_id')),
                ('tahun', '=', vals.get('tahun') or str(fields.Date.today().year)),
            ], limit=1)
            if existing:
                raise ValidationError('RKA untuk perusahaan, account, dan tahun tersebut sudah tersedia.')
            if not vals.get('name') or vals.get('name') == 'New':
                tahun = vals.get('tahun') or str(
                    fields.Date.today().year
                )

                # Keep document numbers unique across branches while budget rows are company-specific.
                last_rka = self.sudo().search(
                    [('tahun', '=', tahun)],
                    order='id desc',
                    limit=1
                )

                if last_rka:
                    try:
                        last_number = int(
                            last_rka.name.split('/')[-1]
                        )
                    except (ValueError, AttributeError):
                        last_number = 0
                else:
                    last_number = 0

                vals['name'] = (
                    f'RKA/{tahun}/{last_number + 1:03d}'
                )

        records = super().create(vals_list)

        for record in records:
            record._create_default_monthly_budget()

        return records

    def write(self, vals):
        self._check_finance_central_readonly()
        for record in self:
            company = self.env['res.company'].browse(vals.get('company_id') or record.company_id.id).exists()
            if not company or company not in self.env.companies:
                raise ValidationError('Perusahaan/cabang RKA tidak valid atau tidak diizinkan.')
            if 'company_id' in vals and record.status != 'draft' and company != record.company_id:
                raise ValidationError('Perusahaan/cabang RKA tidak dapat diubah setelah diajukan.')
        return super().write(vals)

    def unlink(self):
        self._check_finance_central_readonly()
        return super().unlink()

    def action_view_monthly_budget(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': (
                f'Anggaran Bulanan - '
                f'{self.account_id.display_name} '
                f'{self.tahun}'
            ),
            'res_model': 'sif.rka.budget.month',
            'view_mode': 'list,form',
        'views': [
            (
                self.env.ref(
                    'sif_rka.view_sif_rka_dashboard_month_list'
                ).id,
                'list'
            ),
            (
                self.env.ref(
                    'sif_rka.view_sif_rka_dashboard_form'
                ).id,
                'form'
            ),
        ],
        'search_view_id': self.env.ref(
            'sif_rka.view_sif_rka_dashboard_month_search'
        ).id,
        'domain': [
            ('rka_id', '=', self.id)
        ],
        'context': {
            'default_rka_id': self.id
        },
        'target': 'current',
    }

    def _create_default_monthly_budget(self):
        self.ensure_one()

        existing_months = set(
            self.monthly_budget_ids.mapped('month')
        )

        months_to_create = [
            month
            for month, label in MONTHS
            if month not in existing_months
        ]

        if not months_to_create:
            return

        annual_budget = self.nilai
        currency = self.currency_id

        if currency:
            monthly_amount = currency.round(
                annual_budget / 12
            )
        else:
            monthly_amount = annual_budget / 12

        monthly_values = []

        for month in months_to_create:
            budget_amount = monthly_amount

            if month == '12':
                eleven_months = monthly_amount * 11

                if currency:
                    budget_amount = currency.round(
                        annual_budget - eleven_months
                    )
                else:
                    budget_amount = (
                        annual_budget - eleven_months
                    )

            monthly_values.append({
                'rka_id': self.id,
                'month': month,
                'budget_amount': budget_amount,
            })

        self.env['sif.rka.budget.month'].create(
            monthly_values
        )

    @api.constrains('nilai')
    def _check_nilai(self):
        for record in self:
            if record.nilai < 0:
                raise ValidationError(
                    'Nilai anggaran tidak boleh negatif.'
                )

            currency = record.currency_id

            total_bulanan = sum(
                record.monthly_budget_ids.mapped(
                    'budget_amount'
                )
            )

            if currency:
                total_bulanan = currency.round(
                    total_bulanan
                )
                nilai_tahunan = currency.round(
                    record.nilai
                )
            else:
                nilai_tahunan = record.nilai

            parent_rka = record._get_parent_rka()

            if parent_rka:
                if currency:
                    parent_budget = currency.round(
                        parent_rka.nilai
                    )
                else:
                    parent_budget = parent_rka.nilai

                if nilai_tahunan > parent_budget:
                    raise ValidationError(
                        'Anggaran tahunan COA ini tidak boleh '
                        'melebihi anggaran tahunan COA induknya.'
                    )

    @api.constrains('tahun')
    def _check_tahun(self):
        for record in self:
            if record.tahun:
                tahun = int(record.tahun)

                if tahun < 2000 or tahun > 2100:
                    raise ValidationError(
                        'Tahun anggaran tidak valid.'
                    )

    @api.constrains('company_id', 'account_id', 'tahun')
    def _check_parent_rka(self):
        for record in self:
            parent_rka = record._get_parent_rka()

            if not parent_rka:
                continue

            currency = record.currency_id

            if currency:
                nilai_tahunan = currency.round(
                    record.nilai
                )
                parent_budget = currency.round(
                    parent_rka.nilai
                )
            else:
                nilai_tahunan = record.nilai
                parent_budget = parent_rka.nilai

            if nilai_tahunan > parent_budget:
                raise ValidationError(
                    'Anggaran COA tidak boleh melebihi '
                    'anggaran COA induknya.'
                )

    def _get_parent_rka(self):
        self.ensure_one()

        if not self.account_id:
            return self.env['sif.rka.budget']

        parent_coa = self.account_id.parent_id

        if not parent_coa:
            return self.env['sif.rka.budget']

        return self.search([
            ('account_id', '=', parent_coa.id),
            ('tahun', '=', self.tahun),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

    @api.onchange('monthly_budget_ids', 'nilai')
    def _onchange_check_budget_exceeds(self):
        for record in self:
            total_bulanan = sum(line.budget_amount for line in record.monthly_budget_ids)
            if record.currency_id:
                total_bulanan = record.currency_id.round(total_bulanan)
                nilai_tahunan = record.currency_id.round(record.nilai)
            else:
                nilai_tahunan = record.nilai
                
            if total_bulanan > nilai_tahunan:
                return {
                    'warning': {
                        'title': 'Peringatan Anggaran',
                        'message': 'Total anggaran bulanan melebihi anggaran tahunan yang ditetapkan!'
                    }
                }

    @api.depends(
        'monthly_budget_ids.budget_amount',
        'nilai'
    )
    def _compute_total_anggaran_bulanan(self):
        for record in self:
            total = sum(
                record.monthly_budget_ids.mapped(
                    'budget_amount'
                )
            )

            if record.currency_id:
                total = record.currency_id.round(total)
                nilai = record.currency_id.round(
                    record.nilai
                )
            else:
                nilai = record.nilai

            record.total_anggaran_bulanan = total
            record.sisa_alokasi_bulanan = (
                nilai - total
            )

    @api.depends(
        'account_id',
        'tahun',
        'company_id'
    )
    def _compute_realisasi(self):
        jurnal_line = self.env['sif.jurnal.line']

        for record in self:
            record.realisasi = 0.0

            if not record.account_id or not record.tahun:
                continue

            tanggal_awal = f'{record.tahun}-01-01'
            tanggal_akhir = f'{record.tahun}-12-31'

            lines = jurnal_line.search(self._journal_company_scope_domain(record.company_id) + [
                (
                    'account_id',
                    '=',
                    record.account_id.id
                ),
                (
                    'date',
                    '>=',
                    tanggal_awal
                ),
                (
                    'date',
                    '<=',
                    tanggal_akhir
                ),
                (
                    'state',
                    '=',
                    'posted'
                ),
            ])

            record.realisasi = abs(sum(
                (line.debit or 0.0) - (line.credit or 0.0)
                for line in lines
            ))

    @api.depends(
        'nilai',
        'realisasi'
    )
    def _compute_sisa_anggaran(self):
        for record in self:
            if record.currency_id:
                nilai = record.currency_id.round(
                    record.nilai
                )
                realisasi = record.currency_id.round(
                    record.realisasi
                )
            else:
                nilai = record.nilai
                realisasi = record.realisasi

            record.sisa_anggaran = (
                nilai - realisasi
            )

    @api.depends(
        'nilai',
        'realisasi'
    )
    def _compute_persentase_realisasi(self):
        for record in self:
            if record.nilai:
                record.persentase_realisasi = (
                    record.realisasi / record.nilai
                )
            else:
                record.persentase_realisasi = 0.0

    def action_submit(self):
        for record in self:
            record.write({
                'status': 'submitted',
                'tanggal_pengajuan': fields.Datetime.now()
            })

    def action_approve(self):
        for record in self:
            record.write({
                'status': 'approved',
                'tanggal_approval': fields.Datetime.now()
            })

    def action_reject(self):
        for record in self:
            record.write({
                'status': 'rejected',
                'tanggal_approval': fields.Datetime.now()
            })

    def action_reset_to_draft(self):
        for record in self:
            record.write({
                'status': 'draft',
                'tanggal_pengajuan': False,
                'tanggal_approval': False,
                'catatan_approval': False
            })

    def action_view_realisasi(self):
        self.ensure_one()

        tanggal_awal = f'{self.tahun}-01-01'
        tanggal_akhir = f'{self.tahun}-12-31'

        return {
            'type': 'ir.actions.act_window',
            'name': 'Detail Realisasi Tahunan',
            'res_model': 'sif.jurnal.line',
            'view_mode': 'list,form',
            'domain': self._journal_company_scope_domain(self.company_id) + [
                (
                    'account_id',
                    '=',
                    self.account_id.id
                ),
                (
                    'date',
                    '>=',
                    tanggal_awal
                ),
                (
                    'date',
                    '<=',
                    tanggal_akhir
                ),
                (
                    'state',
                    '=',
                    'posted'
                ),
            ],
            'target': 'current',
        }

    def _get_beban_usaha_report_data(self, tahun=None):
        if tahun is None:
            if self:
                tahun_set = set(
                    self.mapped('tahun')
                )

                if len(tahun_set) > 1:
                    raise ValidationError(
                        'Pilih RKA dari tahun yang sama '
                        'untuk mencetak laporan.'
                    )

                tahun = next(iter(tahun_set))

            else:
                tahun = str(
                    fields.Date.today().year
                )

        if not tahun:
            raise ValidationError(
                'Tahun laporan belum ditentukan.'
            )

        tahun = int(tahun)
        tahun_sebelumnya = tahun - 1
        company = self[:1].company_id if self else self.env.company
        journal_company_domain = self._journal_company_scope_domain(company)

        rka_model = self.env['sif.rka.budget']
        jurnal_line = self.env['sif.jurnal.line']

        current_rka = rka_model.search([
            ('company_id', '=', company.id),
            ('tahun', '=', str(tahun)),
        ])

        previous_rka = rka_model.search([
            ('company_id', '=', company.id),
            ('tahun', '=', str(tahun_sebelumnya)),
        ])

        current_lines = jurnal_line.search(journal_company_domain + [
            ('state', '=', 'posted'),
            ('date', '>=', f'{tahun}-01-01'),
            ('date', '<=', f'{tahun}-12-31'),
        ])

        previous_lines = jurnal_line.search(journal_company_domain + [
            ('state', '=', 'posted'),
            ('date', '>=', f'{tahun_sebelumnya}-01-01'),
            ('date', '<=', f'{tahun_sebelumnya}-12-31'),
        ])

        accounts = (
            current_rka.mapped('account_id')
            | previous_rka.mapped('account_id')
        ).sorted(
            key=lambda account: account.code
        )

        current_rka_by_coa = {
            record.account_id.id: record
            for record in current_rka
        }

        previous_rka_by_coa = {
            record.account_id.id: record
            for record in previous_rka
        }

        current_realization = {}

        for line in current_lines:
            account_id = line.account_id.id

            current_realization[account_id] = (
                current_realization.get(account_id, 0.0)
                + (line.debit or 0.0) - (line.credit or 0.0)
            )

        previous_realization = {}

        for line in previous_lines:
            account_id = line.account_id.id

            previous_realization[account_id] = (
                previous_realization.get(account_id, 0.0)
                + (line.debit or 0.0) - (line.credit or 0.0)
            )

        rows = []

        total_current_budget = 0.0
        total_current_realization = 0.0
        total_previous_budget = 0.0
        total_previous_realization = 0.0

        for account in accounts:
            current_rka_record = current_rka_by_coa.get(
                account.id
            )

            previous_rka_record = previous_rka_by_coa.get(
                account.id
            )

            current_budget = (
                current_rka_record.nilai
                if current_rka_record
                else 0.0
            )

            previous_budget = (
                previous_rka_record.nilai
                if previous_rka_record
                else 0.0
            )

            current_amount = current_realization.get(
                account.id,
                0.0
            )

            previous_amount = previous_realization.get(
                account.id,
                0.0
            )

            current_remaining = (
                current_budget - current_amount
            )

            previous_remaining = (
                previous_budget - previous_amount
            )

            current_percentage = (
                current_amount / current_budget
                if current_budget
                else 0.0
            )

            previous_percentage = (
                previous_amount / previous_budget
                if previous_budget
                else 0.0
            )

            total_current_budget += current_budget
            total_current_realization += current_amount
            total_previous_budget += previous_budget
            total_previous_realization += previous_amount

            rows.append({
                'code': account.code,
                'name': account.name,
                'current_budget': current_budget,
                'current_amount': current_amount,
                'current_remaining': current_remaining,
                'current_percentage': current_percentage,
                'previous_budget': previous_budget,
                'previous_amount': previous_amount,
                'previous_remaining': previous_remaining,
                'previous_percentage': previous_percentage,
            })

        total_current_remaining = (
            total_current_budget
            - total_current_realization
        )

        total_previous_remaining = (
            total_previous_budget
            - total_previous_realization
        )

        total_current_percentage = (
            total_current_realization
            / total_current_budget
            if total_current_budget
            else 0.0
        )

        total_previous_percentage = (
            total_previous_realization
            / total_previous_budget
            if total_previous_budget
            else 0.0
        )

        return {
            'tahun': tahun,
            'tahun_sebelumnya': tahun_sebelumnya,
            'rows': rows,
            'total_current_budget': total_current_budget,
            'total_current_realization': total_current_realization,
            'total_current_remaining': total_current_remaining,
            'total_current_percentage': total_current_percentage,
            'total_previous_budget': total_previous_budget,
            'total_previous_realization': total_previous_realization,
            'total_previous_remaining': total_previous_remaining,
            'total_previous_percentage': total_previous_percentage,
        }

    def action_print_beban_usaha(self):
        tahun = None

        if self:
            tahun_set = set(
                self.mapped('tahun')
            )

            if len(tahun_set) > 1:
                raise ValidationError(
                    'Pilih RKA dari tahun yang sama '
                    'untuk mencetak laporan.'
                )

            tahun = next(iter(tahun_set))

        report_data = self._get_beban_usaha_report_data(
            tahun=tahun
        )

        if not report_data['rows']:
            raise ValidationError(
                f'Tidak terdapat data beban usaha '
                f'untuk tahun {report_data["tahun"]}.'
            )

        record = self[:1]

        if not record:
            company = self[:1].company_id if self else self.env.company
            record = self.env[
                'sif.rka.budget'
            ].search([
                ('company_id', '=', company.id),
                (
                    'tahun',
                    '=',
                    str(report_data['tahun'])
                )
            ], limit=1)

        if not record:
            raise ValidationError(
                f'Tidak terdapat RKA untuk tahun '
                f'{report_data["tahun"]}.'
            )

        # Redirect ke custom controller yang render HTML langsung
        # tanpa wkhtmltopdf. Bisa dicetak via Ctrl+P -> Save as PDF.
        return {
            'type': 'ir.actions.act_url',
            'url': f'/sif_rka/print_beban_usaha/{record.id}',
            'target': 'new',
        }

    def action_edit_record(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Edit RKA',
            'res_model': 'sif.rka.budget',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current'
        }

    def action_delete_record(self):
        self.ensure_one()
        self.unlink()

        return {
            'type': 'ir.actions.act_window_close'
        }

    def action_view_diagram_bulanan(self):
        tahun = str(fields.Date.today().year)
        return {
            'type': 'ir.actions.act_window',
            'name': f'Diagram Bulanan {tahun}',
            'res_model': 'sif.rka.budget.month',
            'view_mode': 'graph,list',
            'views': [
                (self.env.ref('sif_rka.view_sif_rka_dashboard_month_graph').id, 'graph'),
                (self.env.ref('sif_rka.view_sif_rka_dashboard_month_list').id, 'list'),
            ],
            'search_view_id': self.env.ref('sif_rka.view_sif_rka_dashboard_month_search').id,
            'domain': [
                ('rka_id.company_id', '=', self.env.company.id),
                ('rka_id.tahun', '=', tahun),
            ],
            'target': 'current',
        }

    def action_open_monthly_diagram_by_coa(self):
        """Buka diagram bulanan yang difilter berdasarkan COA."""
        self.ensure_one()
        tahun = str(self.tahun or fields.Date.today().year)
        return {
            'type': 'ir.actions.act_window',
            'name': f'Diagram Anggaran vs Realisasi - {self.account_id.display_name} {tahun}',
            'res_model': 'sif.rka.budget.month',
            'view_mode': 'graph,list',
            'domain': [
                ('rka_id', '=', self.id),
                ('rka_id.tahun', '=', tahun),
            ],
            'views': [
                (self.env.ref('sif_rka.view_sif_rka_month_graph_coa').id, 'graph'),
                (self.env.ref('sif_rka.view_sif_rka_dashboard_month_list').id, 'list'),
            ],
            'search_view_id': self.env.ref('sif_rka.view_sif_rka_diagram_bulanan_search').id,
            'target': 'new',
        }

    def action_view_monthly_detail(self):
        """
        Menampilkan detail bulanan per COA.
        Dipanggil saat user mengklik tombol 'Detail Bulanan' pada baris RKA.
        """
        self.ensure_one()
        tahun = str(self.tahun or fields.Date.today().year)
        coa = self.account_id
        domain = [
            ('rka_id.company_id', '=', self.company_id.id),
            ('rka_id.tahun', '=', tahun),
        ]
        if coa:
            domain.append(('rka_id.account_id', '=', coa.id))
        return {
            'type': 'ir.actions.act_window',
            'name': f'Detail Bulanan - {coa.display_name} - {tahun}',
            'res_model': 'sif.rka.budget.month',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'new',
            'context': {
                'search_default_group_account': 1,
                'default_tahun': tahun,
            },
        }

    def action_view_top_3_pengeluaran(self):
        tahun = str(fields.Date.today().year)
        all_rka = self.search([
            ('company_id', '=', self.env.company.id),
            ('tahun', '=', tahun),
        ])
        sorted_rka = all_rka.sorted(
            key=lambda r: r.realisasi, reverse=True
        )
        top3 = sorted_rka[:3]
        return {
            'type': 'ir.actions.act_window',
            'name': f'Top 3 Pengeluaran {tahun}',
            'res_model': 'sif.rka.budget',
            'view_mode': 'list,form',
            'domain': [('id', 'in', top3.ids)],
            'target': 'current',
        }

    @api.model
    def action_open_integrated_dashboard(self):
        tahun = str(fields.Date.today().year)
        all_rka = self.search([
            ('company_id', '=', self.env.company.id),
            ('tahun', '=', tahun),
        ])
        sorted_rka = all_rka.sorted(
            key=lambda r: r.realisasi, reverse=True
        )
        top3 = sorted_rka[:3]
        dashboard = self.env['sif.rka.dashboard.view'].create({
            'tahun': tahun,
            'display_mode': 'tahunan',
            'top3_ids': [(6, 0, top3.ids)],
            'rka_ids': [(6, 0, all_rka.ids)],
        })
        return {
            'type': 'ir.actions.act_window',
            'name': f'Dashboard RKA {tahun}',
            'res_model': 'sif.rka.dashboard.view',
            'view_mode': 'form',
            'res_id': dashboard.id,
            'target': 'current',
        }


class SifRkaBudgetMonth(models.Model):
    _name = 'sif.rka.budget.month'
    _description = 'Anggaran RKA Bulanan'
    _order = 'month asc, id asc'

    rka_id = fields.Many2one(
        'sif.rka.budget',
        string='RKA',
        required=True,
        ondelete='cascade'
    )
    company_id = fields.Many2one(
        related='rka_id.company_id',
        string='Perusahaan',
        store=True,
        index=True,
    )

    def _check_finance_central_readonly(self):
        if self.env.user.has_group('sif_keuangan.group_sif_keuangan_central_readonly'):
            raise AccessError('Finance pusat memiliki akses baca saja pada anggaran bulanan RKA.')

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

    account_id = fields.Many2one(
        related='rka_id.account_id',
        string='Account / COA',
        store=False,
        readonly=True,
    )

    parent_account_id = fields.Many2one(
        related='account_id.parent_id',
        string='COA Induk',
        store=False,
        readonly=True,
    )

    tahun = fields.Selection(
        related='rka_id.tahun',
        string='Tahun',
        store=False,
        readonly=True,
    )

    periode = fields.Integer(
        string='Periode',
        compute='_compute_periode',
        store=False,
    )

    month = fields.Selection(
        MONTHS,
        string='Bulan',
        required=True,
        index=True
    )

    name = fields.Char(
        string='Nama Bulan',
        compute='_compute_name',
        store=True
    )

    budget_amount = fields.Monetary(
        string='Anggaran Bulanan',
        required=True,
        default=0.0,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        related='rka_id.currency_id',
        store=False,
        readonly=True
    )

    realisasi = fields.Monetary(
        string='Realisasi',
        compute='_compute_realisasi',
        currency_field='currency_id'
    )

    sisa_anggaran = fields.Monetary(
        string='Sisa Anggaran',
        compute='_compute_sisa_anggaran',
        currency_field='currency_id'
    )

    persentase_realisasi = fields.Float(
        string='% Realisasi',
        compute='_compute_persentase_realisasi'
    )

    @api.depends('tahun', 'month')
    def _compute_periode(self):
        for record in self:
            if record.tahun and record.month:
                record.periode = int(
                    f'{record.tahun}{record.month}'
                )
            else:
                record.periode = 0

    @api.depends('month')
    def _compute_name(self):
        month_dict = dict(MONTHS)

        for record in self:
            record.name = month_dict.get(
                record.month,
                ''
            )

    @api.constrains(
        'budget_amount',
        'rka_id',
        'month'
    )
    def _check_budget_amount(self):
        for record in self:
            if record.budget_amount < 0:
                raise ValidationError(
                    'Anggaran bulanan tidak boleh negatif.'
                )

            if not record.rka_id:
                continue

            currency = record.rka_id.currency_id

            total_bulanan = sum(
                record.rka_id.monthly_budget_ids.mapped(
                    'budget_amount'
                )
            )

            if currency:
                total_bulanan = currency.round(
                    total_bulanan
                )
                nilai_tahunan = currency.round(
                    record.rka_id.nilai
                )
                budget_bulanan = currency.round(
                    record.budget_amount
                )
            else:
                nilai_tahunan = record.rka_id.nilai
                budget_bulanan = record.budget_amount

            parent_rka = record.rka_id._get_parent_rka()

            if not parent_rka:
                continue

            parent_month = parent_rka.monthly_budget_ids.filtered(
                lambda month: month.month == record.month
            )

            if parent_month:
                parent_amount = parent_month[0].budget_amount

                if currency:
                    parent_amount = currency.round(
                        parent_amount
                    )

                if budget_bulanan > parent_amount:
                    raise ValidationError(
                        'Anggaran bulanan COA ini tidak boleh '
                        'melebihi anggaran bulanan COA induknya.'
                    )

    @api.depends(
        'account_id',
        'tahun',
        'month',
        'rka_id.company_id'
    )
    def _compute_realisasi(self):
        jurnal_line = self.env['sif.jurnal.line']

        for record in self:
            record.realisasi = 0.0

            if (
                not record.account_id
                or not record.tahun
                or not record.month
            ):
                continue

            tahun = int(record.tahun)
            bulan = int(record.month)

            tanggal_awal = (
                f'{tahun}-{bulan:02d}-01'
            )

            import calendar

            last_day = calendar.monthrange(
                tahun,
                bulan
            )[1]

            tanggal_akhir = (
                f'{tahun}-{bulan:02d}-{last_day}'
            )

            company_domain = self.env['sif.rka.budget']._journal_company_scope_domain(
                record.rka_id.company_id,
            )
            lines = jurnal_line.search(company_domain + [
                (
                    'account_id',
                    '=',
                    record.account_id.id
                ),
                (
                    'date',
                    '>=',
                    tanggal_awal
                ),
                (
                    'date',
                    '<=',
                    tanggal_akhir
                ),
                (
                    'state',
                    '=',
                    'posted'
                ),
            ])

            record.realisasi = abs(sum(
                (line.debit or 0.0) - (line.credit or 0.0)
                for line in lines
            ))

    @api.depends(
        'budget_amount',
        'realisasi'
    )
    def _compute_sisa_anggaran(self):
        for record in self:
            if record.currency_id:
                budget = record.currency_id.round(
                    record.budget_amount
                )
                realisasi = record.currency_id.round(
                    record.realisasi
                )
            else:
                budget = record.budget_amount
                realisasi = record.realisasi

            record.sisa_anggaran = (
                budget - realisasi
            )

    @api.depends(
        'budget_amount',
        'realisasi'
    )
    def _compute_persentase_realisasi(self):
        for record in self:
            if record.budget_amount:
                record.persentase_realisasi = (
                    record.realisasi /
                    record.budget_amount
                )
            else:
                record.persentase_realisasi = 0.0

    def action_view_transactions(self):
        self.ensure_one()

        tahun = int(self.tahun)
        bulan = int(self.month)

        import calendar

        last_day = calendar.monthrange(
            tahun,
            bulan
        )[1]

        tanggal_awal = (
            f'{tahun}-{bulan:02d}-01'
        )

        tanggal_akhir = (
            f'{tahun}-{bulan:02d}-{last_day}'
        )

        return {
            'type': 'ir.actions.act_window',
            'name': (
                f'Detail Transaksi - '
                f'{self.name} {tahun}'
            ),
            'res_model': 'sif.jurnal.line',
            'view_mode': 'list,form',
            'domain': self.env['sif.rka.budget']._journal_company_scope_domain(
                self.rka_id.company_id,
            ) + [
                (
                    'account_id',
                    '=',
                    self.account_id.id
                ),
                (
                    'date',
                    '>=',
                    tanggal_awal
                ),
                (
                    'date',
                    '<=',
                    tanggal_akhir
                ),
                (
                    'state',
                    '=',
                    'posted'
                ),
            ],
            'target': 'current',
        }

    def action_edit_record(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': (
                f'Edit Anggaran '
                f'{self.name} {self.tahun}'
            ),
            'res_model': 'sif.rka.budget.month',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }


class SifJurnalLine(models.Model):
    _inherit = 'sif.jurnal.line'

    keperluan_rka = fields.Char(
        string='Keperluan',
        related='entry_id.ref',
        readonly=True
    )

class SifJurnalEntry(models.Model):
    _inherit = 'sif.jurnal.entry'

    reference = fields.Char(
        string='Reference',
        related='ref',
        readonly=True
    )

    source_document = fields.Char(
        string='Source Document'
    )

    unit_dept = fields.Selection(
        [
            ('tpa', 'TPA'),
            ('sd', 'SD'),
            ('smp', 'SMP'),
            ('sma', 'SMA'),
            ('univ', 'Universitas'),
            ('pusat', 'Yayasan / Kantor Pusat'),
        ],
        string='Unit / Department',
        default='pusat',
    )


class SifRkaDashboardView(models.TransientModel):
    _name = 'sif.rka.dashboard.view'
    _description = 'Dashboard RKA Terintegrasi'

    name = fields.Char(
        string='Nama',
        compute='_compute_name',
        store=False
    )

    tahun = fields.Char(
        string='Tahun',
        default=lambda self: str(fields.Date.today().year)
    )

    top3_ids = fields.Many2many(
        'sif.rka.budget',
        'sif_rka_dash_top3_rel',
        'dashboard_id',
        'rka_id',
        string='Top 3 Pengeluaran'
    )

    rka_ids = fields.Many2many(
        'sif.rka.budget',
        'sif_rka_dash_rka_rel',
        'dashboard_id',
        'rka_id',
        string='RKA Tahunan'
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('tahun')
    def _compute_name(self):
        for rec in self:
            rec.name = f"Dashboard RKA Tahun {rec.tahun}" if rec.tahun else "Dashboard RKA"

    @api.depends('rka_ids')
    def _compute_totals(self):
        for rec in self:
            rec.total_anggaran = sum(
                r.nilai for r in rec.rka_ids
            )
            rec.total_realisasi = sum(
                r.realisasi for r in rec.rka_ids
            )

    total_anggaran = fields.Monetary(
        string='Total Anggaran',
        currency_field='currency_id',
        compute='_compute_totals'
    )

    total_realisasi = fields.Monetary(
        string='Total Realisasi',
        currency_field='currency_id',
        compute='_compute_totals'
    )

    def action_open_monthly_diagram(self):
        """Buka Chart.js diagram batang interaktif."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'sif_rka.bar_chart_action',
            'name': '📊 Diagram Anggaran vs Realisasi',
            'target': 'current',
            'params': {
                'tahun': self.tahun or str(fields.Date.today().year),
            },
        }

    def action_open_monthly_diagram_by_coa(self):
        """Buka Chart.js diagram batang interaktif (sama seperti action_open_monthly_diagram,
           karena filtering COA sudah ada di dalam client action)."""
        self.ensure_one()
        return self.action_open_monthly_diagram()

    def action_refresh_realisasi(self):
        """Refresh data realisasi — data sudah live (tidak stored)."""
        self.ensure_one()
        tahun = self.tahun or str(fields.Date.today().year)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Berhasil',
                'message': f'Data realisasi tahun {tahun} sudah live dan otomatis terbarui.',
                'type': 'success',
                'sticky': False,
            },
        }
