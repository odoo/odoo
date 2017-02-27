# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.exceptions import UserError


class AccountConfigSettings(models.TransientModel):
    _name = 'account.config.settings'
    _inherit = 'res.config.settings'

    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', related="company_id.currency_id", required=True,
        string='Currency', help="Main currency of the company.")
    has_chart_of_accounts = fields.Boolean(compute='_compute_has_chart_of_accounts', string='Company has a chart of accounts')
    chart_template_id = fields.Many2one('account.chart.template', string='Template',
        domain="[('visible','=', True)]")
    code_digits = fields.Integer(string='# of Digits *', related='company_id.accounts_code_digits', help="No. of digits to use for account code")
    tax_calculation_rounding_method = fields.Selection([
        ('round_per_line', 'Round calculation of taxes per line'),
        ('round_globally', 'Round globally calculation of taxes '),
        ], related='company_id.tax_calculation_rounding_method', string='Tax calculation rounding method')
    module_account_accountant = fields.Boolean(string='Accounting')
    group_multi_currency = fields.Boolean(string='Allow multi currencies',
        implied_group='base.group_multi_currency')
    group_analytic_accounting = fields.Boolean(string='Analytic Accounting',
        implied_group='analytic.group_analytic_accounting')
    group_warning_account = fields.Boolean(string="Warnings", implied_group='account.group_warning_account')
    module_account_asset = fields.Boolean(string='Assets Management')
    module_account_deferred_revenue = fields.Boolean(string="Revenue Recognition")
    module_account_budget = fields.Boolean(string='Budget Management')
    module_account_reports = fields.Boolean("Dynamic Reports")
    module_account_reports_followup = fields.Boolean("Enable payment followup management")
    default_sale_tax_id = fields.Many2one('account.tax', string="Default Sale Tax",
        default_model="account.config.settings", company_dependent=True, oldname="default_sale_tax")
    default_purchase_tax_id = fields.Many2one('account.tax', string="Default Purchase Tax",
        default_model="account.config.settings", company_dependent=True, oldname="default_purchase_tax")
    module_l10n_us_check_printing = fields.Boolean("Allow check printing and deposits")
    module_account_batch_deposit = fields.Boolean(string='Use batch deposit',
        help='This allows you to group received checks before you deposit them to the bank.\n'
             '-This installs the module account_batch_deposit.')
    module_account_sepa = fields.Boolean(string='Use SEPA payments')
    module_account_plaid = fields.Boolean(string="Plaid Connector")
    module_account_yodlee = fields.Boolean("Bank Interface - Sync your bank feeds automatically")
    module_account_bank_statement_import_qif = fields.Boolean("Import .qif files")
    module_account_bank_statement_import_ofx = fields.Boolean("Import in .ofx format")
    module_account_bank_statement_import_csv = fields.Boolean("Import in .csv format")
    module_account_bank_statement_import_camt = fields.Boolean("Import in CAMT.053 format")
    module_currency_rate_live = fields.Boolean(string="Allow Currency Rate Live")
    module_print_docsaway = fields.Boolean(string="Docsaway")
    module_product_margin = fields.Boolean(string="Allow Product Margin")
    module_l10n_eu_service = fields.Boolean(string="EU Digital Goods VAT")

    @api.depends('company_id')
    def _compute_has_chart_of_accounts(self):
        # import pdb; pdb.set_trace()
        self.has_chart_of_accounts = bool(self.company_id.chart_template_id)

    def set_group_multi_currency(self):
        if self.group_multi_currency:
            self.env.ref('base.group_user').write({'implied_ids': [(4, self.env.ref('product.group_sale_pricelist').id)]})
        return True

    def set_default_product_taxes(self):
        """ Set the product taxes if they have changed """
        # import pdb; pdb.set_trace()
        ir_values_obj = self.env['ir.values']
        if self.default_sale_tax_id:
            ir_values_obj.sudo().set_default('product.template', "taxes_id", [self.default_sale_tax_id.id], for_all_users=True, company_id=self.company_id.id)
        if self.default_purchase_tax_id:
            ir_values_obj.sudo().set_default('product.template', "supplier_taxes_id", [self.default_purchase_tax_id.id], for_all_users=True, company_id=self.company_id.id)

    def set_chart_of_accounts(self):
        """ install a chart of accounts for the given company (if required) """
        if self.chart_template_id and not self.has_chart_of_accounts and self.company_id.expects_chart_of_accounts:
            if self.company_id.chart_template_id and self.chart_template_id != self.company_id.chart_template_id:
                raise UserError(_('You can not change a company chart of account once it has been installed'))
            wizard = self.env['wizard.multi.charts.accounts'].create({
                'company_id': self.company_id.id,
                'chart_template_id': self.chart_template_id.id,
                'transfer_account_id': self.chart_template_id.transfer_account_id.id,
                'code_digits': self.code_digits or 6,
                'sale_tax_id': self.default_sale_tax_id.id,
                'purchase_tax_id': self.default_purchase_tax_id.id,
                'sale_tax_rate': 15.0,
                'purchase_tax_rate': 15.0,
                'complete_tax_set': self.chart_template_id.complete_tax_set,
                'currency_id': self.currency_id.id,
                'bank_account_code_prefix': self.chart_template_id.bank_account_code_prefix,
                'cash_account_code_prefix': self.chart_template_id.cash_account_code_prefix,
            })
            wizard.execute()

    @api.onchange('group_analytic_accounting')
    def onchange_analytic_accounting(self):
        if self.group_analytic_accounting:
            self.module_account_accountant = True

    @api.onchange('module_account_budget')
    def onchange_module_account_budget(self):
        if self.module_account_budget:
            self.group_analytic_accounting = True

    @api.onchange('module_account_yodlee')
    def onchange_account_yodlee(self):
        if self.module_account_yodlee:
            self.module_account_plaid = True
