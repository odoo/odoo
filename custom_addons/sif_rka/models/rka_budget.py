from odoo import api, fields, models
from odoo.exceptions import ValidationError


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

    _account_tahun_unique = models.Constraint(
        'UNIQUE(account_id, tahun)',
        'RKA untuk Account dan Tahun tersebut sudah tersedia.'
    )

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
        records = self.env['sif.rka.budget']

        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'New':
                tahun = vals.get('tahun') or str(
                    fields.Date.today().year
                )

                last_rka = self.search(
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

            if total_bulanan > nilai_tahunan:
                raise ValidationError(
                    'Anggaran tahunan tidak boleh lebih kecil '
                    'dari total anggaran bulanan.'
                )

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

    @api.constrains('account_id', 'tahun')
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
        ], limit=1)

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
        'tahun'
    )
    def _compute_realisasi(self):
        jurnal_line = self.env['sif.jurnal.line']

        for record in self:
            record.realisasi = 0.0

            if not record.account_id or not record.tahun:
                continue

            tanggal_awal = f'{record.tahun}-01-01'
            tanggal_akhir = f'{record.tahun}-12-31'

            lines = jurnal_line.search([
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

            record.realisasi = sum(
                lines.mapped('balance')
            )

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
            'domain': [
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

        rka_model = self.env['sif.rka.budget']
        jurnal_line = self.env['sif.jurnal.line']

        current_rka = rka_model.search([
            ('tahun', '=', str(tahun)),
        ])

        previous_rka = rka_model.search([
            ('tahun', '=', str(tahun_sebelumnya)),
        ])

        current_lines = jurnal_line.search([
            ('state', '=', 'posted'),
            ('date', '>=', f'{tahun}-01-01'),
            ('date', '<=', f'{tahun}-12-31'),
        ])

        previous_lines = jurnal_line.search([
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
                + line.balance
            )

        previous_realization = {}

        for line in previous_lines:
            account_id = line.account_id.id

            previous_realization[account_id] = (
                previous_realization.get(account_id, 0.0)
                + line.balance
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

        report_record = self[:1]

        if not report_record:
            report_record = self.env[
                'sif.rka.budget'
            ].search([
                (
                    'tahun',
                    '=',
                    str(report_data['tahun'])
                )
            ], limit=1)

        if not report_record:
            raise ValidationError(
                f'Tidak terdapat RKA untuk tahun '
                f'{report_data["tahun"]}.'
            )

        return self.env.ref(
            'sif_rka.action_report_beban_usaha'
        ).report_action(
            report_record
        )

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


class SifRkaBudgetMonth(models.Model):
    _name = 'sif.rka.budget.month'
    _description = 'Anggaran RKA Bulanan'
    _order = 'tahun desc, month asc, id asc'

    rka_id = fields.Many2one(
        'sif.rka.budget',
        string='RKA',
        required=True,
        ondelete='cascade'
    )

    account_id = fields.Many2one(
        related='rka_id.account_id',
        string='Account / COA',
        store=True,
        readonly=True,
        index=True
    )

    parent_account_id = fields.Many2one(
        related='account_id.parent_id',
        string='COA Induk',
        store=True,
        readonly=True,
        index=True
    )

    tahun = fields.Selection(
        related='rka_id.tahun',
        string='Tahun',
        store=True,
        readonly=True,
        index=True
    )

    periode = fields.Integer(
        string='Periode',
        compute='_compute_periode',
        store=True,
        index=True
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
        store=True,
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

            if total_bulanan > nilai_tahunan:
                raise ValidationError(
                    'Total anggaran bulanan tidak boleh '
                    'melebihi anggaran tahunan.'
                )

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
        'month'
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

            lines = jurnal_line.search([
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

            record.realisasi = sum(
                lines.mapped('balance')
            )

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
            'domain': [
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