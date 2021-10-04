from odoo import api, fields, models, _

from odoo.exceptions import ValidationError


class AccountTaxCarryoverLine(models.Model):
    _name = 'account.tax.carryover.line'
    _description = 'Tax carryover line'

    name = fields.Char(required=True)
    amount = fields.Float(required=True, default=0.0)
    date = fields.Date(required=True, default=fields.Date.context_today)
    tax_report_line_id = fields.Many2one(
        comodel_name='account.tax.report.line',
        string="Tax report line",
    )
    tax_report_id = fields.Many2one(related='tax_report_line_id.report_id')
    tax_report_country_id = fields.Many2one(related='tax_report_id.country_id')
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    foreign_vat_fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position',
        string="Fiscal position",
        help="The foreign fiscal position for which this carryover is made.",
        domain="[('company_id', '=', company_id), "
               "('country_id', '=', tax_report_country_id), "
               "('foreign_vat', '!=', False)]",
    )

    @api.constrains('foreign_vat_fiscal_position_id')
    def _check_fiscal_position(self):
        if self.foreign_vat_fiscal_position_id and not self.foreign_vat_fiscal_position_id.country_id == self.tax_report_country_id:
            raise ValidationError(_("The country of the fiscal position must be this report line's report country."))
