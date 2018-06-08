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

class AccountInvoiceLine(models.Model):
    _inherit = "account.invoice.line"

    def write(self, vals):
        if (vals.get('account_id') or vals.get('invoice_line_tax_ids')):
            account_id = vals.get('account_id', False)
            account = account_id and self.env['account.account'].browse(account_id) or self.account_id
            account_name = account.name
            account_tax = account.tax_ids.ids
            if account_tax:
                if vals.get('invoice_line_tax_ids'):
                    invoice_line_tax = vals.get('invoice_line_tax_ids')[0][2]
                else:
                    invoice_line_tax = self.invoice_line_tax_ids
                for tax in invoice_line_tax:
                    if tax not in account_tax:
                        tax_name = self.env['account.tax'].browse(tax).name
                        raise UserError(_('Account %s does not authorize to have tax %s specified on the line.') % (tax_name, account_name))
        return super(AccountInvoiceLine, self).write(vals)

    @api.model
    def create(self, vals):
        if vals.get('invoice_line_tax_ids'):
            account = self.env['account.account'].browse(vals.get('account_id'))
            account_name = account.name
            account_tax = account.tax_ids.ids
            if account_tax:
                for tax in vals.get('invoice_line_tax_ids')[0][2]:
                    if tax not in account_tax:
                        tax_name = self.env['account.tax'].browse(tax).name
                        raise UserError(_('Account %s does not authorize to have tax %s specified on the line.') % (tax_name, account_name))
        return super(AccountInvoiceLine, self).create(vals)