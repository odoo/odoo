# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SifAgingReportLine(models.TransientModel):
    _name = 'sif.aging.report.line'
    _description = 'Detail Baris Laporan Umur Utang Dagang'

    wizard_id = fields.Many2one(
        'sif.aging.report.wizard',
        ondelete='cascade'
    )

    vendor_id = fields.Many2one(
        'sif.vendor',
        string='Rekanan / Vendor'
    )

    vendor_name = fields.Char(string='Rekanan')
    ppl_name = fields.Char(string='No PPL / Faktur')
    invoice_date = fields.Date(string='Tanggal Faktur')
    due_date = fields.Date(string='Batas Waktu')
    overdue_days = fields.Integer(string='Umur (Hari)')

    # Nominal untuk perhitungan total aging
    current_amount = fields.Monetary(string='Pada Tanggal')
    days_1_30 = fields.Monetary(string='1-30')
    days_31_60 = fields.Monetary(string='31-60')
    days_61_90 = fields.Monetary(string='61-90')
    days_91_120 = fields.Monetary(string='91-120')
    days_older = fields.Monetary(string='Lebih Tua')

    total_amount = fields.Monetary(string='Total')

    # Umur dalam hari untuk ditampilkan pada tabel detail
    age_1_30 = fields.Integer(string='1-30 Hari')
    age_31_60 = fields.Integer(string='31-60 Hari')
    age_61_90 = fields.Integer(string='61-90 Hari')
    age_91_120 = fields.Integer(string='91-120 Hari')
    age_older = fields.Integer(string='Lebih Tua')

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )


class SifAgingReportWizard(models.TransientModel):
    _name = 'sif.aging.report.wizard'
    _description = 'Laporan Umur Utang Dagang'

    as_of_date = fields.Date(
        string='Sejak Tanggal',
        default=fields.Date.context_today,
        required=True
    )

    vendor_id = fields.Many2one(
        'sif.vendor',
        string='Rekanan / Vendor'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        default=lambda self: self.env.company
    )

    line_ids = fields.One2many(
        'sif.aging.report.line',
        'wizard_id',
        string='Rincian Utang'
    )

    total_current = fields.Monetary(
        compute='_compute_totals',
        string='Total Pada Tanggal'
    )

    total_1_30 = fields.Monetary(
        compute='_compute_totals',
        string='Total 1-30'
    )

    total_31_60 = fields.Monetary(
        compute='_compute_totals',
        string='Total 31-60'
    )

    total_61_90 = fields.Monetary(
        compute='_compute_totals',
        string='Total 61-90'
    )

    total_91_120 = fields.Monetary(
        compute='_compute_totals',
        string='Total 91-120'
    )

    total_older = fields.Monetary(
        compute='_compute_totals',
        string='Total Lebih Tua'
    )

    total_grand = fields.Monetary(
        compute='_compute_totals',
        string='Total Umur Utang Dagang'
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    @api.depends('line_ids')
    def _compute_totals(self):
        for rec in self:
            rec.total_current = sum(
                rec.line_ids.mapped('current_amount')
            )
            rec.total_1_30 = sum(
                rec.line_ids.mapped('days_1_30')
            )
            rec.total_31_60 = sum(
                rec.line_ids.mapped('days_31_60')
            )
            rec.total_61_90 = sum(
                rec.line_ids.mapped('days_61_90')
            )
            rec.total_91_120 = sum(
                rec.line_ids.mapped('days_91_120')
            )
            rec.total_older = sum(
                rec.line_ids.mapped('days_older')
            )
            rec.total_grand = sum(
                rec.line_ids.mapped('total_amount')
            )

    def action_generate_report(self):
        self.ensure_one()

        self.line_ids.unlink()

        domain = [
            ('payment_term', '=', 'jatuh_tempo'),
            ('state', '=', 'approved'),
            ('company_id', '=', self.company_id.id),
        ]

        if self.vendor_id:
            domain.append(
                ('vendor_id', '=', self.vendor_id.id)
            )

        ppls = self.env['sifnext.ppl'].search(
            domain,
            order='vendor_id, request_date asc'
        )

        as_of = self.as_of_date or fields.Date.today()

        lines = []

        for ppl in ppls:
            due = ppl.due_date or ppl.request_date
            days = (as_of - due).days if due else 0
            amt = ppl.total_amount

            # Nominal untuk ringkasan
            c_amt = amt if days <= 0 else 0.0
            d1_30 = amt if 1 <= days <= 30 else 0.0
            d31_60 = amt if 31 <= days <= 60 else 0.0
            d61_90 = amt if 61 <= days <= 90 else 0.0
            d91_120 = amt if 91 <= days <= 120 else 0.0
            d_older = amt if days > 120 else 0.0

            # Umur hari untuk tabel detail
            age_1_30 = days if 1 <= days <= 30 else 0
            age_31_60 = days if 31 <= days <= 60 else 0
            age_61_90 = days if 61 <= days <= 90 else 0
            age_91_120 = days if 91 <= days <= 120 else 0
            age_older = days if days > 120 else 0

            lines.append((0, 0, {
                'ppl_name': ppl.name,
                'vendor_id': (
                    ppl.vendor_id.id
                    if ppl.vendor_id else False
                ),
                'vendor_name': (
                    ppl.vendor_id.name
                    if ppl.vendor_id else 'Tanpa Rekanan'
                ),
                'invoice_date': ppl.request_date,
                'due_date': due,
                'overdue_days': days,

                # Nominal
                'current_amount': c_amt,
                'days_1_30': d1_30,
                'days_31_60': d31_60,
                'days_61_90': d61_90,
                'days_91_120': d91_120,
                'days_older': d_older,
                'total_amount': amt,

                # Umur hari
                'age_1_30': age_1_30,
                'age_31_60': age_31_60,
                'age_61_90': age_61_90,
                'age_91_120': age_91_120,
                'age_older': age_older,
            }))

        self.write({
            'line_ids': lines
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sif.aging.report.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }