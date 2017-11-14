# -*- coding: utf-8 -*-

from odoo.exceptions import ValidationError
from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


from datetime import datetime


class AccountFiscalYear(models.Model):
    _name = 'account.fiscal.year'
    _description = 'Fiscal Year'

    name = fields.Char(string='Name', required=True)
    date_from = fields.Date(string='Start Date', required=True,
        help='Start Date, included in the fiscal year.')
    date_to = fields.Date(string='End Date', required=True,
        help='Ending Date, included in the fiscal year.')
    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)

    @api.model
    def get_fiscal_year(self, date_from, date_to, company=None):
        if not company:
            company = self.env.user.company_id
        return self.search([
            ('company_id', '=', company.id),
            ('date_from', '=', date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)),
            ('date_to', '=', date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)),
        ], limit=1)


    @api.constrains('date_from', 'date_to', 'company_id')
    def _check_dates(self):
        for fy in self:
            # Starting date must be prior to the ending date
            date_from = datetime.strptime(fy.date_from, DEFAULT_SERVER_DATE_FORMAT)
            date_to = datetime.strptime(fy.date_to, DEFAULT_SERVER_DATE_FORMAT)
            if date_to < date_from:
                raise ValidationError(_('The ending date must not be prior to the starting date.'))

            domain = [
                ('id', '!=', fy.id),
                ('company_id', '=', fy.company_id.id),
                '|',
                '&', ('date_from', '<=', fy.date_from), ('date_to', '>=', fy.date_from),
                '&', ('date_from', '<=', fy.date_to), ('date_to', '>=', fy.date_to)
            ]

            if self.search_count(domain) > 0:
                raise ValidationError(_('You can not have an overlap between two fiscal years, please correct the start and/or end dates of your fiscal years.'))
