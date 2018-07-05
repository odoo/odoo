from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    l10n_de_datev_code = fields.Char(size=2)

    def _get_tax_vals(self, company, tax_template_to_tax):
        vals = super(AccountTaxTemplate, self)._get_tax_vals(company, tax_template_to_tax)
        vals['l10n_de_datev_code'] = self.l10n_de_datev_code
        return vals

class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_de_datev_code = fields.Char(size=2, help="2 digits code use by Datev")

class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    def invoice_validate(self):
        for invoice in self:
            for line in invoice.invoice_line_ids:
                account_tax = line.account_id.tax_ids.ids
                if account_tax and invoice.company_id.country_id.code == 'DE':
                    account_name = line.account_id.name
                    for tax in line.invoice_line_tax_ids:
                        if tax.id not in account_tax:
                            raise UserError(_('Account %s does not authorize to have tax %s specified on the line. \
                                Change the tax used in this invoice or remove all taxes from the account') % (account_name, tax.name))
        return super(AccountInvoice, self).invoice_validate()