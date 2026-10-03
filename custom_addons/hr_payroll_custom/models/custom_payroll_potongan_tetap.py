from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class CustomPayrollPotonganTetap(models.Model):
    _name = 'custom.payroll.potongan.tetap'
    _description = 'Fixed Deduction Master Data'
    _order = 'employee_id, start_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Deduction Name', required=True)
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='restrict',
        index=True,
    )
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        default=0.0,
        required=True,
    )
    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=fields.Date.today,
    )
    end_date = fields.Date(string='End Date')
    description = fields.Text(string='Description')
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_(
                    "End Date (%(end)s) must be greater than or equal to Start Date (%(start)s)."
                ) % {'end': rec.end_date, 'start': rec.start_date})
