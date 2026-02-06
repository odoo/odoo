# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class L10nCoEdiUvt(models.Model):
    _name = 'l10n_co_edi.uvt'
    _description = 'Colombian Tax Value Unit (UVT)'
    _order = 'year desc'
    _rec_name = 'year'

    year = fields.Integer(
        string='Tax Year',
        required=True,
        help='The fiscal year this UVT value applies to.',
    )
    value = fields.Float(
        string='UVT Value (COP)',
        required=True,
        digits=(12, 0),
        help='Value in Colombian Pesos of one UVT for this year. '
             'Set by DIAN resolution each year.',
    )
    resolution = fields.Char(
        string='DIAN Resolution',
        help='The DIAN resolution number that established this UVT value.',
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    _unique_year_company = models.Constraint(
        'UNIQUE(year, company_id)',
        'Only one UVT value per year per company is allowed.',
    )

    @api.constrains('value')
    def _check_value_positive(self):
        for record in self:
            if record.value <= 0:
                raise ValidationError(_('UVT value must be greater than zero.'))

    @api.constrains('year')
    def _check_year_reasonable(self):
        for record in self:
            if record.year < 2000 or record.year > 2100:
                raise ValidationError(_('Year must be between 2000 and 2100.'))

    @api.model
    def get_uvt_value(self, year=None, company=None):
        """Get the UVT value for a given year and company.

        :param year: The fiscal year (defaults to current year)
        :param company: The company (defaults to current company)
        :return: UVT value in COP, or 0.0 if not configured
        """
        if year is None:
            year = fields.Date.context_today(self).year
        if company is None:
            company = self.env.company

        uvt = self.search([
            ('year', '=', year),
            ('company_id', '=', company.id),
        ], limit=1)
        return uvt.value if uvt else 0.0

    @api.model
    def convert_uvt_to_cop(self, uvt_amount, year=None, company=None):
        """Convert a UVT amount to COP for the given year.

        :param uvt_amount: Number of UVTs
        :param year: The fiscal year (defaults to current year)
        :param company: The company (defaults to current company)
        :return: Amount in COP
        """
        uvt_value = self.get_uvt_value(year=year, company=company)
        return uvt_amount * uvt_value

    @api.model
    def convert_cop_to_uvt(self, cop_amount, year=None, company=None):
        """Convert a COP amount to UVTs for the given year.

        :param cop_amount: Amount in Colombian Pesos
        :param year: The fiscal year (defaults to current year)
        :param company: The company (defaults to current company)
        :return: Number of UVTs (float)
        """
        uvt_value = self.get_uvt_value(year=year, company=company)
        if not uvt_value:
            return 0.0
        return cop_amount / uvt_value
