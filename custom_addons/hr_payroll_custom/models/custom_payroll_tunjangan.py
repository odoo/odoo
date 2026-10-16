from odoo import fields, models


class CustomPayrollTunjangan(models.Model):
    _name = 'custom.payroll.tunjangan'
    _description = 'Allowance Master Data'
    _order = 'name'

    name = fields.Char(string='Allowance Name', required=True)
    type = fields.Selection(
        selection=[
            ('tetap', 'Fixed'),
            ('variable', 'Variable'),
            ('proprietary', 'Proprietary'),
        ],
        string='Type',
        required=True,
        default='tetap',
    )
    nilai = fields.Monetary(string='Amount', currency_field='currency_id', default=0.0)
    status_aktif = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
