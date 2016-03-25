# -*- coding: utf-8 -*-

import time
import datetime
from dateutil.relativedelta import relativedelta

import openerp
from openerp import SUPERUSER_ID
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from openerp import api, fields, models, _
from openerp.exceptions import UserError


class AccountConfigSettings(models.TransientModel):
    _name = 'account.config.settings'
    _inherit = 'res.config.settings'

    @api.one
    @api.depends('company_id')
    def _get_currency_id(self):
        self.currency_id = self.company_id.currency_id

    @api.one
    def _set_currency_id(self):
        if self.currency_id != self.company_id.currency_id:
            self.company_id.currency_id = self.currency_id

    company_id = fields.Many2one('res.company', string='Company', required=True,
        default=lambda self: self.env.user.company_id)
    has_default_company = fields.Boolean(readonly=True,
        default=lambda self: self._default_has_default_company())
    expects_chart_of_accounts = fields.Boolean(related='company_id.expects_chart_of_accounts',
        string='This company has its own chart of accounts',
        help='Check this box if this company is a legal entity.')
    currency_id = fields.Many2one('res.currency', compute='_get_currency_id', inverse='_set_currency_id', required=True,
        string='Default company currency', help="Main currency of the company.")
    paypal_account = fields.Char(related='company_id.paypal_account', size=128, string='Paypal account',
        help="""Paypal account (email) for receiving online payments (credit card, etc.)
             If you set a paypal account, the customer  will be able to pay your invoices or quotations
             with a button \"Pay with  Paypal\" in automated emails or through the Odoo portal.""")
    company_footer = fields.Text(related='company_id.rml_footer', string='Bank accounts footer preview',
        readonly=True, help="Bank accounts as printed in the footer of each printed document")

    has_chart_of_accounts = fields.Boolean(string='Company has a chart of accounts')
    chart_template_id = fields.Many2one('account.chart.template', string='Template',
        domain="[('visible','=', True)]")
    use_anglo_saxon = fields.Boolean(string='Use Anglo-Saxon Accounting', related='company_id.anglo_saxon_accounting')
    code_digits = fields.Integer(string='# of Digits', related='company_id.accounts_code_digits', help="No. of digits to use for account code")
    tax_calculation_rounding_method = fields.Selection(
        [
        ('round_per_line', 'Round calculation of taxes per line'),
        ('round_globally', 'Round globally calculation of taxes '),
        ], related='company_id.tax_calculation_rounding_method', string='Tax calculation rounding method',
        help="""If you select 'Round per line' : for each tax, the tax amount will first be
             computed and rounded for each PO/SO/invoice line and then these rounded amounts will be summed,
             leading to the total amount for that tax. If you select 'Round globally': for each tax,
             the tax amount will be computed for each PO/SO/invoice line, then these amounts will be
             summed and eventually this total tax amount will be rounded. If you sell with tax included,
             you should choose 'Round per line' because you certainly want the sum of your tax-included line
             subtotals to be equal to the total amount with taxes.""")
    sale_tax_id = fields.Many2one('account.tax.template', string='Default sale tax', oldname="sale_tax")
    purchase_tax_id = fields.Many2one('account.tax.template', string='Default purchase tax', oldname="purchase_tax")
    sale_tax_rate = fields.Float(string='Sales tax (%)')
    purchase_tax_rate = fields.Float(string='Purchase tax (%)')
    bank_account_code_prefix = fields.Char(string='Bank Accounts Prefix', related='company_id.bank_account_code_prefix', help='Define the code prefix for the bank accounts', oldname='bank_account_code_char')
    cash_account_code_prefix = fields.Char(string='Cash Accounts Prefix', related='company_id.cash_account_code_prefix', help='Define the code prefix for the cash accounts')
    template_transfer_account_id = fields.Many2one('account.account.template', help="Intermediary account used when moving money from a liquidity account to another")
    transfer_account_id = fields.Many2one('account.account',
        related='company_id.transfer_account_id',
        domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_current_assets').id)],
        help="Intermediary account used when moving money from a liquidity account to another")
    complete_tax_set = fields.Boolean(string='Complete set of taxes',
        help='''This boolean helps you to choose if you want to propose to the user to encode
             the sales and purchase rates or use the usual m2o fields. This last choice assumes that
             the set of tax defined for the chosen template is complete''')

    fiscalyear_last_day = fields.Integer(related='company_id.fiscalyear_last_day', default=31)
    fiscalyear_last_month = fields.Selection([(1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'), (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'), (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')], related='company_id.fiscalyear_last_month', default=12)
    period_lock_date = fields.Date(string="Lock Date for Non-Advisers", related='company_id.period_lock_date', help="Only users with the 'Adviser' role can edit accounts prior to and inclusive of this date. Use it for period locking inside an open fiscal year, for example.")
    fiscalyear_lock_date = fields.Date(string="Lock Date", related='company_id.fiscalyear_lock_date', help="No users, including Advisers, can edit accounts prior to and inclusive of this date. Use it for fiscal year locking for example.")

    module_account_accountant = fields.Boolean(string='Full accounting features: journals, legal statements, chart of accounts, etc.',
        help="""If you do not check this box, you will be able to do invoicing & payments,
             but not accounting (Journal Items, Chart of  Accounts, ...)""")
    module_account_reports = fields.Boolean("Get dynamic accounting reports")
    group_multi_currency = fields.Boolean(string='Allow multi currencies',
        implied_group='base.group_multi_currency',
        help="Allows you multi currency environment")
    group_analytic_accounting = fields.Boolean(string='Analytic accounting',
        implied_group='analytic.group_analytic_accounting',
        help="Allows you to use the analytic accounting.")
    currency_exchange_journal_id = fields.Many2one('account.journal',
        related='company_id.currency_exchange_journal_id',
        string="Rate Difference Journal",)
    module_account_asset = fields.Boolean(string='Assets management',
        help='Asset management: This allows you to manage the assets owned by a company or a person. '
                 'It keeps track of the depreciation occurred on those assets, and creates account move for those depreciation lines.\n\n'
             '-This installs the module account_asset. If you do not check this box, you will be able to do invoicing & payments, '
             'but not accounting (Journal Items, Chart of Accounts, ...)')
    module_account_budget = fields.Boolean(string='Budget management',
        help='This allows accountants to manage analytic and crossovered budgets. '
             'Once the master budgets and the budgets are defined, '
             'the project managers can set the planned amount on each analytic account.\n'
             '-This installs the module account_budget.')
    module_account_tax_cash_basis = fields.Boolean(string="Allow Tax Cash Basis",
                                        help='Generate tax cash basis entrie when reconciliating entries')

    group_proforma_invoices = fields.Boolean(string='Allow pro-forma invoices',
        implied_group='account.group_proforma_invoices',
        help="Allows you to put invoices in pro-forma state.")
    module_account_reports_followup = fields.Boolean("Enable payment followup management",
        help='This allows to automate letters for unpaid invoices, with multi-level recalls.\n'
             '-This installs the module account_reports_followup.')

    default_sale_tax_id = fields.Many2one('account.tax', string="Default Sale Tax", help="This sale tax will be assigned by default on new products.", oldname="default_sale_tax")
    default_purchase_tax_id = fields.Many2one('account.tax', string="Default Purchase Tax", help="This purchase tax will be assigned by default on new products.", oldname="default_purchase_tax")

    module_l10n_us_check_printing = fields.Boolean("Allow check printing and deposits")

    module_account_batch_deposit = fields.Boolean(string='Use batch deposit',
        help='This allows you to group received checks before you deposit them to the bank.\n'
             '-This installs the module account_batch_deposit.')
    module_account_sepa = fields.Boolean(string='Use SEPA payments',
        help='If you check this box, you will be able to register your payment using SEPA.\n'
            '-This installs the module account_sepa.')

    module_account_plaid = fields.Boolean(string="Plaid Connector",
                                          help='Get your bank statements from you bank and import them through plaid.com.\n'
                                          '-that installs the module account_plaid.')
    module_account_yodlee = fields.Boolean("Bank Interface - Sync your bank feeds automatically",
        help='Get your bank statements from your bank and import them through yodlee.com.\n'
                                          '-that installs the module account_yodlee.')
    module_account_bank_statement_import_qif = fields.Boolean("Import .qif files",
        help='Get your bank statements from your bank and import them in Odoo in the .QIF format.\n'
            'This installs the module account_bank_statement_import_qif.')
    module_account_bank_statement_import_ofx = fields.Boolean("Import in .ofx format",
        help='Get your bank statements from your bank and import them in Odoo in the .OFX format.\n'
            'This installs the module account_bank_statement_import_ofx.')


    @api.model
    def _default_has_default_company(self):
        count = self.env['res.company'].search_count([])
        return bool(count == 1)


    @api.onchange('company_id')
    def onchange_company_id(self):
        # update related fields
        self.currency_id = False
        if self.company_id:
            company = self.company_id
            self.chart_template_id = company.chart_template_id
            self.has_chart_of_accounts = len(company.chart_template_id) > 0 or False
            self.expects_chart_of_accounts = company.expects_chart_of_accounts
            self.currency_id = company.currency_id
            self.transfer_account_id = company.transfer_account_id
            self.paypal_account = company.paypal_account
            self.company_footer = company.rml_footer
            self.tax_calculation_rounding_method = company.tax_calculation_rounding_method
            self.bank_account_code_prefix = company.bank_account_code_prefix
            self.cash_account_code_prefix = company.cash_account_code_prefix
            self.code_digits = company.accounts_code_digits

            # update taxes
            ir_values = self.env['ir.values']
            taxes_id = ir_values.get_default('product.template', 'taxes_id', company_id = self.company_id.id)
            supplier_taxes_id = ir_values.get_default('product.template', 'supplier_taxes_id', company_id = self.company_id.id)
            self.default_sale_tax_id = isinstance(taxes_id, list) and taxes_id[0] or taxes_id
            self.default_purchase_tax_id = isinstance(supplier_taxes_id, list) and supplier_taxes_id[0] or supplier_taxes_id
        return {}

    @api.onchange('chart_template_id')
    def onchange_chart_template_id(self):
        tax_templ_obj = self.env['account.tax.template']
        self.complete_tax_set = self.sale_tax_id = self.purchase_tax_id = False
        self.sale_tax_rate = self.purchase_tax_rate = 15
        if self.chart_template_id and not self.has_chart_of_accounts:
            # update complete_tax_set, sale_tax_id and purchase_tax_id
            self.complete_tax_set = self.chart_template_id.complete_tax_set
            if self.chart_template_id.complete_tax_set:
                ir_values_obj = self.env['ir.values']
                # default tax is given by the lowest sequence. For same sequence we will take the latest created as it will be the case for tax created while isntalling the generic chart of account
                sale_tax = tax_templ_obj.search(
                    [('chart_template_id', '=', self.chart_template_id.id), ('type_tax_use', '=', 'sale')], limit=1,
                    order="sequence, id desc")
                purchase_tax = tax_templ_obj.search(
                    [('chart_template_id', '=', self.chart_template_id.id), ('type_tax_use', '=', 'purchase')], limit=1,
                    order="sequence, id desc")
                self.sale_tax_id = sale_tax
                self.purchase_tax_id = purchase_tax
            if self.chart_template_id.code_digits:
                self.code_digits = self.chart_template_id.code_digits
            if self.chart_template_id.transfer_account_id:
                self.template_transfer_account_id = self.chart_template_id.transfer_account_id.id
            if self.chart_template_id.bank_account_code_prefix:
                self.bank_account_code_prefix = self.chart_template_id.bank_account_code_prefix
            if self.chart_template_id.cash_account_code_prefix:
                self.cash_account_code_prefix = self.chart_template_id.cash_account_code_prefix
        return {}

    @api.onchange('sale_tax_rate')
    def onchange_tax_rate(self):
        self.purchase_tax_rate = self.sale_tax_rate or False

    @api.multi
    def set_group_multi_currency(self):
        ir_model = self.env['ir.model.data']
        group_user = ir_model.get_object('base', 'group_user')
        group_product = ir_model.get_object('product', 'group_sale_pricelist')
        if self.group_multi_currency:
            group_user.write({'implied_ids': [(4, group_product.id)]})
        return True

    @api.multi
    def open_bank_accounts(self):
        action_rec = self.env['ir.model.data'].xmlid_to_object('account.action_account_bank_journal_form')
        return action_rec.read([])[0]

    @api.multi
    def set_transfer_account(self):
        if self.transfer_account_id and self.transfer_account_id != self.company_id.transfer_account_id:
            self.company_id.write({'transfer_account_id': self.transfer_account_id.id})

    @api.multi
    def set_product_taxes(self):
        """ Set the product taxes if they have changed """
        ir_values_obj = self.env['ir.values']
        ir_values_obj.sudo().set_default('product.template', "taxes_id", [self.default_sale_tax_id.id] if self.default_sale_tax_id else False, for_all_users=True, company_id=self.company_id.id)
        ir_values_obj.sudo().set_default('product.template', "supplier_taxes_id", [self.default_purchase_tax_id.id] if self.default_purchase_tax_id else False, for_all_users=True, company_id=self.company_id.id)

    @api.multi
    def set_chart_of_accounts(self):
        """ install a chart of accounts for the given company (if required) """
        if self.chart_template_id and not self.has_chart_of_accounts and self.expects_chart_of_accounts:
            if self.company_id.chart_template_id and self.chart_template_id != self.company_id.chart_template_id:
                raise UserError(_('You can not change a company chart of account once it has been installed'))
            wizard = self.env['wizard.multi.charts.accounts'].create({
                'company_id': self.company_id.id,
                'chart_template_id': self.chart_template_id.id,
                'transfer_account_id': self.template_transfer_account_id.id,
                'code_digits': self.code_digits or 6,
                'sale_tax_id': self.sale_tax_id.id,
                'purchase_tax_id': self.purchase_tax_id.id,
                'sale_tax_rate': self.sale_tax_rate,
                'purchase_tax_rate': self.purchase_tax_rate,
                'complete_tax_set': self.complete_tax_set,
                'currency_id': self.currency_id.id,
                'bank_account_code_prefix': self.bank_account_code_prefix,
                'cash_account_code_prefix': self.cash_account_code_prefix,
            })
            wizard.execute()

    @api.onchange('group_analytic_accounting')
    def onchange_analytic_accounting(self):
        if self.group_analytic_accounting:
            self.module_account_accountant = True

    @api.multi
    def open_company(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'My Company',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'res.company',
            'res_id': self.env.user.company_id.id,
            'target': 'current',
        }
