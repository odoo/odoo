from odoo import fields, models

class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    datev_correction_code = fields.Char(size=2)

    def _get_tax_vals(self, company, tax_template_to_tax):
    	vals = super(AccountTaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)
    	vals['datev_correction_code'] = self.datev_correction_code
    	return vals

class AccountTax(models.Model):
	_inherit = "account.tax"

	datev_correction_code = fields.Char(size=2, help="2 digits code use by Datev")
