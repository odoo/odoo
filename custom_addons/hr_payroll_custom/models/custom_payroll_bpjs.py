from odoo import fields, models


class CustomPayrollBpjs(models.Model):
    _name = 'custom.payroll.bpjs'
    _description = 'BPJS Master Data'
    _order = 'name'

    name = fields.Char(string='Name', required=True)
    jenis = fields.Selection(
        selection=[
            ('kesehatan', 'Health (BPJS Kesehatan)'),
            ('ketenagakerjaan', 'Employment (BPJS Ketenagakerjaan)'),
        ],
        string='Type',
        required=True,
    )
    persen = fields.Float(
        string='Percentage (%)',
        default=0.0,
        help='Persentase BPJS yang akan dihitung dari gaji pokok karyawan. '
             'Contoh: 5 berarti 5% dari gaji pokok. '
             'Jika diisi > 0, field "Amount" akan diabaikan.',
    )
    nominal = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        default=0.0,
        help='Nilai flat BPJS (fallback jika Percentage kosong). '
             'Digunakan untuk tarif BPJS yang tidak berbasis persentase '
             '(misal: JKK by risk class, JKM flat).',
    )
    status_aktif = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
