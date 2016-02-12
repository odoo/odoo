# -*- coding: utf-8 -*-

import time
import math

from openerp.osv import expression
from openerp.tools.float_utils import float_round as round
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import AccessError, UserError, ValidationError
import openerp.addons.decimal_precision as dp
from openerp import api, fields, models, _
from openerp import SUPERUSER_ID

import logging
_logger = logging.getLogger(__name__)

def migrate_set_tags_and_taxes_updatable(cr, registry, module):
    ''' This is a utility function used to manually set the flag noupdate to False on tags and account tax templates on localization modules
    that need migration (for example in case of VAT report improvements)
    '''
    xml_record_ids = registry['ir.model.data'].search(cr, SUPERUSER_ID, [('model', 'in', ['account.tax.template', 'account.account.tag']), ('module', 'like', module)])
    if xml_record_ids:
        cr.execute("update ir_model_data set noupdate = 'f' where id in %s", (tuple(xml_record_ids),))

def migrate_tags_on_taxes(cr, registry):
    ''' This is a utiliy function to help migrate the tags of taxes when the localization has been modified on stable version. If
    called accordingly in a post_init_hooked function, it will reset the tags set on taxes as per their equivalent template.

    Note: This unusual decision has been made in order to help the improvement of VAT reports on version 9.0, to have them more flexible
    and working out of the box when people are creating/using new taxes.
    '''
    xml_record_ids = registry['ir.model.data'].search(cr, SUPERUSER_ID, [('model', '=', 'account.tax.template'), ('module', 'like', 'l10n_%')])
    tax_template_ids = [x['res_id'] for x in registry['ir.model.data'].read(cr, SUPERUSER_ID, xml_record_ids, ['res_id'])]
    for tax_template in registry['account.tax.template'].browse(cr, SUPERUSER_ID, tax_template_ids):
        tax_id = registry['account.tax'].search(cr, SUPERUSER_ID, [('name', '=', tax_template.name), ('type_tax_use', '=', tax_template.type_tax_use), ('description', '=', tax_template.description)])
        if len(tax_id) == 1:
            registry['account.tax'].write(cr, SUPERUSER_ID, tax_id, {'tag_ids': [(6,0,[x.id for x in tax_template.tag_ids])]})

#  ---------------------------------------------------------------
#   Account Templates: Account, Tax, Tax Code and chart. + Wizard
#  ---------------------------------------------------------------


class AccountAccountTemplate(models.Model):
    _name = "account.account.template"
    _description = 'Templates for Accounts'
    _order = "code"

    name = fields.Char(required=True, index=True)
    currency_id = fields.Many2one('res.currency', string='Account Currency', help="Forces all moves for this account to have this secondary currency.")
    code = fields.Char(size=64, required=True, index=True)
    user_type_id = fields.Many2one('account.account.type', string='Type', required=True, oldname='user_type',
        help="These types are defined according to your country. The type contains more information "\
        "about the account and its specificities.")
    reconcile = fields.Boolean(string='Allow Invoices & payments Matching', default=False,
        help="Check this option if you want the user to reconcile entries in this account.")
    note = fields.Text()
    tax_ids = fields.Many2many('account.tax.template', 'account_account_template_tax_rel', 'account_id', 'tax_id', string='Default Taxes')
    nocreate = fields.Boolean(string='Optional Create', default=False,
        help="If checked, the new chart of accounts will not contain this by default.")
    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template',
        help="This optional field allow you to link an account template to a specific chart template that may differ from the one its root parent belongs to. This allow you "
            "to define chart templates that extend another and complete it with few new accounts (You don't need to define the whole structure that is common to both several times).")
    tag_ids = fields.Many2many('account.account.tag', 'account_account_template_account_tag', string='Account tag', help="Optional tags you may want to assign for custom reporting")

    @api.multi
    @api.depends('name', 'code')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.code:
                name = record.code + ' ' + name
            res.append((record.id, name))
        return res


class AccountChartTemplate(models.Model):
    _name = "account.chart.template"
    _description = "Templates for Account Chart"

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', string='Company')
    parent_id = fields.Many2one('account.chart.template', string='Parent Chart Template')
    code_digits = fields.Integer(string='# of Digits', required=True, default=6, help="No. of Digits to use for account code")
    visible = fields.Boolean(string='Can be Visible?', default=True,
        help="Set this to False if you don't want this template to be used actively in the wizard that generate Chart of Accounts from "
            "templates, this is useful when you want to generate accounts of this template only when loading its child template.")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)
    use_anglo_saxon = fields.Boolean(string="Use Anglo-Saxon accounting", default=False)
    complete_tax_set = fields.Boolean(string='Complete Set of Taxes', default=True,
        help="This boolean helps you to choose if you want to propose to the user to encode the sale and purchase rates or choose from list "
            "of taxes. This last choice assumes that the set of tax defined on this template is complete")
    account_ids = fields.One2many('account.account.template', 'chart_template_id', string='Associated Account Templates')
    tax_template_ids = fields.One2many('account.tax.template', 'chart_template_id', string='Tax Template List',
        help='List of all the taxes that have to be installed by the wizard')
    bank_account_code_prefix = fields.Char(string='Prefix of the bank accounts', oldname="bank_account_code_char")
    cash_account_code_prefix = fields.Char(string='Prefix of the main cash accounts')
    transfer_account_id = fields.Many2one('account.account.template', string='Transfer Account', required=True,
        domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_current_assets').id)],
        help="Intermediary account used when moving money from a liquidity account to another")
    income_currency_exchange_account_id = fields.Many2one('account.account.template',
        string="Gain Exchange Rate Account", domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)])
    expense_currency_exchange_account_id = fields.Many2one('account.account.template',
        string="Loss Exchange Rate Account", domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)])
    property_account_receivable_id = fields.Many2one('account.account.template', string='Receivable Account', oldname="property_account_receivable")
    property_account_payable_id = fields.Many2one('account.account.template', string='Payable Account', oldname="property_account_payable")
    property_account_expense_categ_id = fields.Many2one('account.account.template', string='Category of Expense Account', oldname="property_account_expense_categ")
    property_account_income_categ_id = fields.Many2one('account.account.template', string='Category of Income Account', oldname="property_account_income_categ")
    property_account_expense_id = fields.Many2one('account.account.template', string='Expense Account on Product Template', oldname="property_account_expense")
    property_account_income_id = fields.Many2one('account.account.template', string='Income Account on Product Template', oldname="property_account_income")
    property_stock_account_input_categ_id = fields.Many2one('account.account.template', string="Input Account for Stock Valuation", oldname="property_stock_account_input_categ")
    property_stock_account_output_categ_id = fields.Many2one('account.account.template', string="Output Account for Stock Valuation", oldname="property_stock_account_output_categ")
    property_stock_valuation_account_id = fields.Many2one('account.account.template', string="Account Template for Stock Valuation")

    @api.one
    def try_loading_for_current_company(self):
        self.ensure_one()
        company = self.env.user.company_id
        # If we don't have any chart of account on this company, install this chart of account
        if not company.chart_template_id:
            wizard = self.env['wizard.multi.charts.accounts'].create({
                'company_id': self.env.user.company_id.id,
                'chart_template_id': self.id,
                'code_digits': self.code_digits,
                'transfer_account_id': self.transfer_account_id.id,
                'currency_id': self.currency_id.id,
                'bank_account_code_prefix': self.bank_account_code_prefix,
                'cash_account_code_prefix': self.cash_account_code_prefix,
            })
            wizard.onchange_chart_template_id()
            wizard.execute()

    @api.multi
    def open_select_template_wizard(self):
        # Add action to open wizard to select between several templates
        if not self.company_id.chart_template_id:
            todo = self.env['ir.actions.todo']
            action_rec = self.env['ir.model.data'].xmlid_to_object('account.action_wizard_multi_chart')
            if action_rec:
                todo.create({'action_id': action_rec.id, 'name': _('Choose Accounting Template'), 'type': 'automatic'})
        return True

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        """
        This method is used for creating journals.

        :param chart_temp_id: Chart Template Id.
        :param acc_template_ref: Account templates reference.
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        JournalObj = self.env['account.journal']
        for vals_journal in self._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict):
            journal = JournalObj.create(vals_journal)
            if vals_journal['type'] == 'general' and vals_journal['code'] == _('EXCH'):
                company.write({'currency_exchange_journal_id': journal.id})
        return True

    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        def _get_default_account(journal_vals, type='debit'):
            # Get the default accounts
            default_account = False
            if journal['type'] == 'sale':
                default_account = acc_template_ref.get(self.property_account_income_categ_id.id)
            elif journal['type'] == 'purchase':
                default_account = acc_template_ref.get(self.property_account_expense_categ_id.id)
            elif journal['type'] == 'general' and journal['code'] == _('EXCH'):
                if type=='credit':
                    default_account = acc_template_ref.get(self.income_currency_exchange_account_id.id)
                else:
                    default_account = acc_template_ref.get(self.expense_currency_exchange_account_id.id)
            return default_account

        journals = [{'name': _('Customer Invoices'), 'type': 'sale', 'code': _('INV'), 'favorite': True, 'sequence': 5},
                    {'name': _('Vendor Bills'), 'type': 'purchase', 'code': _('BILL'), 'favorite': True, 'sequence': 6},
                    {'name': _('Miscellaneous Operations'), 'type': 'general', 'code': _('MISC'), 'favorite': False, 'sequence': 7},
                    {'name': _('Exchange Difference'), 'type': 'general', 'code': _('EXCH'), 'favorite': False, 'sequence': 9},]
        if journals_dict != None:
            journals.extend(journals_dict)

        self.ensure_one()
        journal_data = []
        for journal in journals:
            vals = {
                'type': journal['type'],
                'name': journal['name'],
                'code': journal['code'],
                'company_id': company.id,
                'default_credit_account_id': _get_default_account(journal, 'credit'),
                'default_debit_account_id': _get_default_account(journal, 'debit'),
                'show_on_dashboard': journal['favorite'],
            }
            journal_data.append(vals)
        return journal_data

    @api.multi
    def generate_properties(self, acc_template_ref, company):
        """
        This method used for creating properties.

        :param self: chart templates for which we need to create properties
        :param acc_template_ref: Mapping between ids of account templates and real accounts created from them
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        self.ensure_one()
        PropertyObj = self.env['ir.property']
        todo_list = [
            ('property_account_receivable_id', 'res.partner', 'account.account'),
            ('property_account_payable_id', 'res.partner', 'account.account'),
            ('property_account_expense_categ_id', 'product.category', 'account.account'),
            ('property_account_income_categ_id', 'product.category', 'account.account'),
            ('property_account_expense_id', 'product.template', 'account.account'),
            ('property_account_income_id', 'product.template', 'account.account'),
        ]
        for record in todo_list:
            account = getattr(self, record[0])
            value = account and 'account.account,' + str(acc_template_ref[account.id]) or False
            if value:
                field = self.env['ir.model.fields'].search([('name', '=', record[0]), ('model', '=', record[1]), ('relation', '=', record[2])], limit=1)
                vals = {
                    'name': record[0],
                    'company_id': company.id,
                    'fields_id': field.id,
                    'value': value,
                }
                properties = PropertyObj.search([('name', '=', record[0]), ('company_id', '=', company.id)])
                if properties:
                    #the property exist: modify it
                    properties.write(vals)
                else:
                    #create the property
                    PropertyObj.create(vals)
        stock_properties = [
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
            'property_stock_valuation_account_id',
        ]
        for stock_property in stock_properties:
            account = getattr(self, stock_property)
            value = account and acc_template_ref[account.id] or False
            if value:
                company.write({stock_property: value})
        return True

    @api.multi
    def _install_template(self, company, code_digits=None, transfer_account_id=None, obj_wizard=None, acc_ref=None, taxes_ref=None):
        """ Recursively load the template objects and create the real objects from them.

            :param company: company the wizard is running for
            :param code_digits: number of digits the accounts code should have in the COA
            :param transfer_account_id: reference to the account template that will be used as intermediary account for transfers between 2 liquidity accounts
            :param obj_wizard: the current wizard for generating the COA from the templates
            :param acc_ref: Mapping between ids of account templates and real accounts created from them
            :param taxes_ref: Mapping between ids of tax templates and real taxes created from them
            :returns: tuple with a dictionary containing
                * the mapping between the account template ids and the ids of the real accounts that have been generated
                  from them, as first item,
                * a similar dictionary for mapping the tax templates and taxes, as second item,
            :rtype: tuple(dict, dict, dict)
        """
        self.ensure_one()
        if acc_ref is None:
            acc_ref = {}
        if taxes_ref is None:
            taxes_ref = {}
        if self.parent_id:
            tmp1, tmp2 = self.parent_id._install_template(company, code_digits=code_digits, transfer_account_id=transfer_account_id, acc_ref=acc_ref, taxes_ref=taxes_ref)
            acc_ref.update(tmp1)
            taxes_ref.update(tmp2)
        tmp1, tmp2 = self._load_template(company, code_digits=code_digits, transfer_account_id=transfer_account_id, account_ref=acc_ref, taxes_ref=taxes_ref)
        acc_ref.update(tmp1)
        taxes_ref.update(tmp2)
        return acc_ref, taxes_ref

    @api.multi
    def _load_template(self, company, code_digits=None, transfer_account_id=None, account_ref=None, taxes_ref=None):
        """ Generate all the objects from the templates

            :param company: company the wizard is running for
            :param code_digits: number of digits the accounts code should have in the COA
            :param transfer_account_id: reference to the account template that will be used as intermediary account for transfers between 2 liquidity accounts
            :param acc_ref: Mapping between ids of account templates and real accounts created from them
            :param taxes_ref: Mapping between ids of tax templates and real taxes created from them
            :returns: tuple with a dictionary containing
                * the mapping between the account template ids and the ids of the real accounts that have been generated
                  from them, as first item,
                * a similar dictionary for mapping the tax templates and taxes, as second item,
            :rtype: tuple(dict, dict, dict)
        """
        self.ensure_one()
        if account_ref is None:
            account_ref = {}
        if taxes_ref is None:
            taxes_ref = {}
        if not code_digits:
            code_digits = self.code_digits
        if not transfer_account_id:
            transfer_account_id = self.transfer_account_id
        AccountTaxObj = self.env['account.tax']

        # Generate taxes from templates.
        generated_tax_res = self.tax_template_ids._generate_tax(company)
        taxes_ref.update(generated_tax_res['tax_template_to_tax'])

        # Generating Accounts from templates.
        account_template_ref = self.generate_account(taxes_ref, account_ref, code_digits, company)
        account_ref.update(account_template_ref)

        # writing account values after creation of accounts
        company.transfer_account_id = account_template_ref[transfer_account_id.id]
        for key, value in generated_tax_res['account_dict'].items():
            if value['refund_account_id'] or value['account_id']:
                AccountTaxObj.browse(key).write({
                    'refund_account_id': account_ref.get(value['refund_account_id'], False),
                    'account_id': account_ref.get(value['account_id'], False),
                })

        # Create Journals
        self.generate_journals(account_ref, company)

        # generate properties function
        self.generate_properties(account_ref, company)

        # Generate Fiscal Position , Fiscal Position Accounts and Fiscal Position Taxes from templates
        self.generate_fiscal_position(taxes_ref, account_ref, company)

        return account_ref, taxes_ref

    @api.multi
    def generate_account(self, tax_template_ref, acc_template_ref, code_digits, company):
        """ This method for generating accounts from templates.

            :param tax_template_ref: Taxes templates reference for write taxes_id in account_account.
            :param acc_template_ref: dictionary with the mappping between the account templates and the real accounts.
            :param code_digits: number of digits got from wizard.multi.charts.accounts, this is use for account code.
            :param company_id: company_id selected from wizard.multi.charts.accounts.
            :returns: return acc_template_ref for reference purpose.
            :rtype: dict
        """
        self.ensure_one()
        account_tmpl_obj = self.env['account.account.template']
        acc_template = account_tmpl_obj.search([('nocreate', '!=', True), ('chart_template_id', '=', self.id)], order='id')
        for account_template in acc_template:
            tax_ids = []
            for tax in account_template.tax_ids:
                tax_ids.append(tax_template_ref[tax.id])

            code_main = account_template.code and len(account_template.code) or 0
            code_acc = account_template.code or ''
            if code_main > 0 and code_main <= code_digits:
                code_acc = str(code_acc) + (str('0'*(code_digits-code_main)))
            vals = {
                'name': account_template.name,
                'currency_id': account_template.currency_id and account_template.currency_id.id or False,
                'code': code_acc,
                'user_type_id': account_template.user_type_id and account_template.user_type_id.id or False,
                'reconcile': account_template.reconcile,
                'note': account_template.note,
                'tax_ids': [(6, 0, tax_ids)],
                'company_id': company.id,
                'tag_ids': [(6, 0, [t.id for t in account_template.tag_ids])],
            }
            new_account = self.env['account.account'].create(vals)
            acc_template_ref[account_template.id] = new_account.id
        return acc_template_ref

    @api.multi
    def generate_fiscal_position(self, tax_template_ref, acc_template_ref, company):
        """ This method generate Fiscal Position, Fiscal Position Accounts and Fiscal Position Taxes from templates.

            :param chart_temp_id: Chart Template Id.
            :param taxes_ids: Taxes templates reference for generating account.fiscal.position.tax.
            :param acc_template_ref: Account templates reference for generating account.fiscal.position.account.
            :param company_id: company_id selected from wizard.multi.charts.accounts.
            :returns: True
        """
        self.ensure_one()
        positions = self.env['account.fiscal.position.template'].search([('chart_template_id', '=', self.id)])
        for position in positions:
            new_fp = self.env['account.fiscal.position'].create({'company_id': company.id, 'name': position.name, 'note': position.note})
            for tax in position.tax_ids:
                self.env['account.fiscal.position.tax'].create({
                    'tax_src_id': tax_template_ref[tax.tax_src_id.id],
                    'tax_dest_id': tax.tax_dest_id and tax_template_ref[tax.tax_dest_id.id] or False,
                    'position_id': new_fp.id
                })
            for acc in position.account_ids:
                self.env['account.fiscal.position.account'].create({
                    'account_src_id': acc_template_ref[acc.account_src_id.id],
                    'account_dest_id': acc_template_ref[acc.account_dest_id.id],
                    'position_id': new_fp.id
                })
        return True


class AccountTaxTemplate(models.Model):
    _name = 'account.tax.template'
    _description = 'Templates for Taxes'
    _order = 'id'

    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)

    name = fields.Char(string='Tax Name', required=True)
    type_tax_use = fields.Selection([('sale', 'Sales'), ('purchase', 'Purchases'), ('none', 'None')], string='Tax Scope', required=True, default="sale",
        help="Determines where the tax is selectable. Note : 'None' means a tax can't be used by itself, however it can still be used in a group.")
    amount_type = fields.Selection(default='percent', string="Tax Computation", required=True,
        selection=[('group', 'Group of Taxes'), ('fixed', 'Fixed'), ('percent', 'Percentage of Price'), ('division', 'Percentage of Price Tax Included')])
    active = fields.Boolean(default=True, help="Set active to false to hide the tax without removing it.")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    children_tax_ids = fields.Many2many('account.tax.template', 'account_tax_template_filiation_rel', 'parent_tax', 'child_tax', string='Children Taxes')
    sequence = fields.Integer(required=True, default=1,
        help="The sequence field is used to define order in which the tax lines are applied.")
    amount = fields.Float(required=True, digits=(16, 4))
    account_id = fields.Many2one('account.account.template', string='Tax Account', ondelete='restrict',
        help="Account that will be set on invoice tax lines for invoices. Leave empty to use the expense account.", oldname='account_collected_id')
    refund_account_id = fields.Many2one('account.account.template', string='Tax Account on Refunds', ondelete='restrict',
        help="Account that will be set on invoice tax lines for refunds. Leave empty to use the expense account.", oldname='account_paid_id')
    description = fields.Char(string='Display on Invoices')
    price_include = fields.Boolean(string='Included in Price', default=False,
        help="Check this if the price you use on the product and invoices includes this tax.")
    include_base_amount = fields.Boolean(string='Affect Subsequent Taxes', default=False,
        help="If set, taxes which are computed after this one will be computed based on the price tax included.")
    analytic = fields.Boolean(string="Analytic Cost", help="If set, the amount computed by this tax will be assigned to the same analytic account as the invoice line (if any)")
    tag_ids = fields.Many2many('account.account.tag', string='Account tag', help="Optional tags you may want to assign for custom reporting")

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id, type_tax_use)', 'Tax names must be unique !'),
    ]

    @api.multi
    @api.depends('name', 'description')
    def name_get(self):
        res = []
        for record in self:
            name = record.description and record.description or record.name
            res.append((record.id, name))
        return res

    def _get_tax_vals(self, company):
        """ This method generates a dictionnary of all the values for the tax that will be created.
        """
        self.ensure_one()
        return {
            'name': self.name,
            'type_tax_use': self.type_tax_use,
            'amount_type': self.amount_type,
            'active': self.active,
            'company_id': company.id,
            'sequence': self.sequence,
            'amount': self.amount,
            'description': self.description,
            'price_include': self.price_include,
            'include_base_amount': self.include_base_amount,
            'analytic': self.analytic,
            'tag_ids': [(6, 0, [t.id for t in self.tag_ids])],
        }

    @api.multi
    def _generate_tax(self, company):
        """ This method generate taxes from templates.

            :param company: the company for which the taxes should be created from templates in self
            :returns: {
                'tax_template_to_tax': mapping between tax template and the newly generated taxes corresponding,
                'account_dict': dictionary containing a to-do list with all the accounts to assign on new taxes
            }
        """
        todo_dict = {}
        tax_template_to_tax = {}
        for tax in self:
            # Compute children tax ids
            children_ids = []
            for child_tax in tax.children_tax_ids:
                if tax_template_to_tax.get(child_tax.id):
                    children_ids.append(tax_template_to_tax[child_tax.id])
            vals_tax = tax._get_tax_vals(company)
            vals_tax['children_tax_ids'] = children_ids and [(6, 0, children_ids)] or []
            new_tax = self.env['account.tax'].create(vals_tax)
            tax_template_to_tax[tax.id] = new_tax.id
            # Since the accounts have not been created yet, we have to wait before filling these fields
            todo_dict[new_tax.id] = {
                'account_id': tax.account_id.id,
                'refund_account_id': tax.refund_account_id.id,
            }

        return {
            'tax_template_to_tax': tax_template_to_tax,
            'account_dict': todo_dict
        }


# Fiscal Position Templates

class AccountFiscalPositionTemplate(models.Model):
    _name = 'account.fiscal.position.template'
    _description = 'Template for Fiscal Position'

    name = fields.Char(string='Fiscal Position Template', required=True)
    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)
    account_ids = fields.One2many('account.fiscal.position.account.template', 'position_id', string='Account Mapping')
    tax_ids = fields.One2many('account.fiscal.position.tax.template', 'position_id', string='Tax Mapping')
    note = fields.Text(string='Notes')


class AccountFiscalPositionTaxTemplate(models.Model):
    _name = 'account.fiscal.position.tax.template'
    _description = 'Template Tax Fiscal Position'
    _rec_name = 'position_id'

    position_id = fields.Many2one('account.fiscal.position.template', string='Fiscal Position', required=True, ondelete='cascade')
    tax_src_id = fields.Many2one('account.tax.template', string='Tax Source', required=True)
    tax_dest_id = fields.Many2one('account.tax.template', string='Replacement Tax')


class AccountFiscalPositionAccountTemplate(models.Model):
    _name = 'account.fiscal.position.account.template'
    _description = 'Template Account Fiscal Mapping'
    _rec_name = 'position_id'

    position_id = fields.Many2one('account.fiscal.position.template', string='Fiscal Mapping', required=True, ondelete='cascade')
    account_src_id = fields.Many2one('account.account.template', string='Account Source', required=True)
    account_dest_id = fields.Many2one('account.account.template', string='Account Destination', required=True)

# ---------------------------------------------------------
# Account generation from template wizards
# ---------------------------------------------------------


class WizardMultiChartsAccounts(models.TransientModel):
    """
    Create a new account chart for a company.
    Wizards ask for:
        * a company
        * an account chart template
        * a number of digits for formatting code of non-view accounts
        * a list of bank accounts owned by the company
    Then, the wizard:
        * generates all accounts from the template and assigns them to the right company
        * generates all taxes and tax codes, changing account assignations
        * generates all accounting properties and assigns them correctly
    """

    _name = 'wizard.multi.charts.accounts'
    _inherit = 'res.config'

    company_id = fields.Many2one('res.company', string='Company', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', help="Currency as per company's country.", required=True)
    only_one_chart_template = fields.Boolean(string='Only One Chart Template Available')
    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)
    bank_account_ids = fields.One2many('account.bank.accounts.wizard', 'bank_account_id', string='Cash and Banks', required=True, oldname="bank_accounts_id")
    bank_account_code_prefix = fields.Char('Bank Accounts Prefix', oldname="bank_account_code_char")
    cash_account_code_prefix = fields.Char('Cash Accounts Prefix')
    code_digits = fields.Integer(string='# of Digits', required=True, help="No. of Digits to use for account code")
    sale_tax_id = fields.Many2one('account.tax.template', string='Default Sales Tax', oldname="sale_tax")
    purchase_tax_id = fields.Many2one('account.tax.template', string='Default Purchase Tax', oldname="purchase_tax")
    sale_tax_rate = fields.Float(string='Sales Tax(%)')
    use_anglo_saxon = fields.Boolean(string='Use Anglo-Saxon Accounting', related='chart_template_id.use_anglo_saxon')
    transfer_account_id = fields.Many2one('account.account.template', required=True, string='Transfer Account',
        domain=lambda self: [('reconcile', '=', True), ('user_type_id.id', '=', self.env.ref('account.data_account_type_current_assets').id)],
        help="Intermediary account used when moving money from a liquidity account to another")
    purchase_tax_rate = fields.Float(string='Purchase Tax(%)')
    complete_tax_set = fields.Boolean('Complete Set of Taxes',
        help="This boolean helps you to choose if you want to propose to the user to encode the sales and purchase rates or use "
            "the usual m2o fields. This last choice assumes that the set of tax defined for the chosen template is complete")

    @api.model
    def _get_chart_parent_ids(self, chart_template):
        """ Returns the IDs of all ancestor charts, including the chart itself.
            (inverse of child_of operator)

            :param browse_record chart_template: the account.chart.template record
            :return: the IDS of all ancestor charts, including the chart itself.
        """
        result = [chart_template.id]
        while chart_template.parent_id:
            chart_template = chart_template.parent_id
            result.append(chart_template.id)
        return result

    @api.onchange('sale_tax_rate')
    def onchange_tax_rate(self):
        self.purchase_tax_rate = self.sale_tax_rate or False

    @api.onchange('chart_template_id')
    def onchange_chart_template_id(self):
        res = {}
        tax_templ_obj = self.env['account.tax.template']
        if self.chart_template_id:
            currency_id = self.chart_template_id.currency_id and self.chart_template_id.currency_id.id or self.env.user.company_id.currency_id.id
            self.complete_tax_set = self.chart_template_id.complete_tax_set
            self.currency_id = currency_id
            if self.chart_template_id.complete_tax_set:
            # default tax is given by the lowest sequence. For same sequence we will take the latest created as it will be the case for tax created while isntalling the generic chart of account
                chart_ids = self._get_chart_parent_ids(self.chart_template_id)
                base_tax_domain = [('chart_template_id', 'in', chart_ids)]
                sale_tax_domain = base_tax_domain + [('type_tax_use', '=', 'sale')]
                purchase_tax_domain = base_tax_domain + [('type_tax_use', '=', 'purchase')]
                sale_tax = tax_templ_obj.search(sale_tax_domain, order="sequence, id desc", limit=1)
                purchase_tax = tax_templ_obj.search(purchase_tax_domain, order="sequence, id desc", limit=1)
                self.sale_tax_id = sale_tax.id
                self.purchase_tax_id = purchase_tax.id
                res.setdefault('domain', {})
                res['domain']['sale_tax_id'] = repr(sale_tax_domain)
                res['domain']['purchase_tax_id'] = repr(purchase_tax_domain)
            if self.chart_template_id.transfer_account_id:
                self.transfer_account_id = self.chart_template_id.transfer_account_id.id
            if self.chart_template_id.code_digits:
                self.code_digits = self.chart_template_id.code_digits
            if self.chart_template_id.bank_account_code_prefix:
                self.bank_account_code_prefix = self.chart_template_id.bank_account_code_prefix
            if self.chart_template_id.cash_account_code_prefix:
                self.cash_account_code_prefix = self.chart_template_id.cash_account_code_prefix
        return res

    @api.model
    def default_get(self, fields):
        context = self._context or {}
        res = super(WizardMultiChartsAccounts, self).default_get(fields)
        tax_templ_obj = self.env['account.tax.template']
        account_chart_template = self.env['account.chart.template']

        if 'bank_account_ids' in fields:
            res.update({'bank_account_ids': [{'acc_name': _('Cash'), 'account_type': 'cash'}, {'acc_name': _('Bank'), 'account_type': 'bank'}]})
        if 'company_id' in fields:
            res.update({'company_id': self.env.user.company_id.id})
        if 'currency_id' in fields:
            company_id = res.get('company_id') or False
            if company_id:
                company = self.env['res.company'].browse(company_id)
                currency_id = company.on_change_country(company.country_id.id)['value']['currency_id']
                res.update({'currency_id': currency_id})

        chart_templates = account_chart_template.search([('visible', '=', True)])
        if chart_templates:
            #in order to set default chart which was last created set max of ids.
            chart_id = max(chart_templates.ids)
            if context.get("default_charts"):
                model_data = self.env['ir.model.data'].search_read([('model', '=', 'account.chart.template'), ('module', '=', context.get("default_charts"))], ['res_id'])
                if model_data:
                    chart_id = model_data[0]['res_id']
            chart = account_chart_template.browse(chart_id)
            chart_hierarchy_ids = self._get_chart_parent_ids(chart)
            if 'chart_template_id' in fields:
                res.update({'only_one_chart_template': len(chart_templates) == 1,
                            'chart_template_id': chart_id})
            if 'sale_tax_id' in fields:
                sale_tax = tax_templ_obj.search([('chart_template_id', 'in', chart_hierarchy_ids),
                                                              ('type_tax_use', '=', 'sale')], limit=1, order='sequence')
                res.update({'sale_tax_id': sale_tax and sale_tax.id or False})
            if 'purchase_tax_id' in fields:
                purchase_tax = tax_templ_obj.search([('chart_template_id', 'in', chart_hierarchy_ids),
                                                                  ('type_tax_use', '=', 'purchase')], limit=1, order='sequence')
                res.update({'purchase_tax_id': purchase_tax and purchase_tax.id or False})
        res.update({
            'purchase_tax_rate': 15.0,
            'sale_tax_rate': 15.0,
        })
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        context = self._context or {}
        res = super(WizardMultiChartsAccounts, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=False)
        cmp_select = []
        CompanyObj = self.env['res.company']

        companies = CompanyObj.search([])
        #display in the widget selection of companies, only the companies that haven't been configured yet (but don't care about the demo chart of accounts)
        self._cr.execute("SELECT company_id FROM account_account WHERE deprecated = 'f' AND name != 'Chart For Automated Tests' AND name NOT LIKE '%(test)'")
        configured_cmp = [r[0] for r in self._cr.fetchall()]
        unconfigured_cmp = list(set(companies.ids) - set(configured_cmp))
        for field in res['fields']:
            if field == 'company_id':
                res['fields'][field]['domain'] = [('id', 'in', unconfigured_cmp)]
                res['fields'][field]['selection'] = [('', '')]
                if unconfigured_cmp:
                    cmp_select = [(line.id, line.name) for line in CompanyObj.browse(unconfigured_cmp)]
                    res['fields'][field]['selection'] = cmp_select
        return res

    @api.one
    def _create_tax_templates_from_rates(self, company_id):
        '''
        This function checks if the chosen chart template is configured as containing a full set of taxes, and if
        it's not the case, it creates the templates for account.tax object accordingly to the provided sale/purchase rates.
        Then it saves the new tax templates as default taxes to use for this chart template.

        :param company_id: id of the company for wich the wizard is running
        :return: True
        '''
        obj_tax_temp = self.env['account.tax.template']
        all_parents = self._get_chart_parent_ids(self.chart_template_id)
        # create tax templates from purchase_tax_rate and sale_tax_rate fields
        if not self.chart_template_id.complete_tax_set:
            value = self.sale_tax_rate
            ref_taxs = obj_tax_temp.search([('type_tax_use', '=', 'sale'), ('chart_template_id', 'in', all_parents)], order="sequence, id desc", limit=1)
            ref_taxs.write({'amount': value, 'name': _('Tax %.2f%%') % value, 'description': '%.2f%%' % value})
            value = self.purchase_tax_rate
            ref_taxs = obj_tax_temp.search([('type_tax_use', '=', 'purchase'), ('chart_template_id', 'in', all_parents)], order="sequence, id desc", limit=1)
            ref_taxs.write({'amount': value, 'name': _('Tax %.2f%%') % value, 'description': '%.2f%%' % value})
        return True

    @api.multi
    def execute(self):
        '''
        This function is called at the confirmation of the wizard to generate the COA from the templates. It will read
        all the provided information to create the accounts, the banks, the journals, the taxes, the
        accounting properties... accordingly for the chosen company.
        '''
        if len(self.env['account.account'].search([('company_id', '=', self.company_id.id)])) > 0:
            # We are in a case where we already have some accounts existing, meaning that user has probably
            # created its own accounts and does not need a coa, so skip installation of coa.
            _logger.info('Could not install chart of account since some accounts already exists for the company (%s)', (self.company_id.id,))
            return {}
        if not self.env.user._is_admin():
            raise AccessError(_("Only administrators can change the settings"))
        ir_values_obj = self.env['ir.values']
        company = self.company_id
        self.company_id.write({'currency_id': self.currency_id.id,
                               'accounts_code_digits': self.code_digits,
                               'anglo_saxon_accounting': self.use_anglo_saxon,
                               'bank_account_code_prefix': self.bank_account_code_prefix,
                               'cash_account_code_prefix': self.cash_account_code_prefix,
                               'chart_template_id': self.chart_template_id.id})

        #set the coa currency to active
        self.currency_id.write({'active': True})

        # When we install the CoA of first company, set the currency to price types and pricelists
        if company.id == 1:
            for reference in ['product.list_price', 'product.standard_price', 'product.list0']:
                try:
                    tmp2 = self.env.ref(reference).write({'currency_id': self.currency_id.id})
                except ValueError:
                    pass

        # If the floats for sale/purchase rates have been filled, create templates from them
        self._create_tax_templates_from_rates(company.id)

        # Install all the templates objects and generate the real objects
        acc_template_ref, taxes_ref = self.chart_template_id._install_template(company, code_digits=self.code_digits, transfer_account_id=self.transfer_account_id)

        # write values of default taxes for product as super user
        if self.sale_tax_id and taxes_ref:
            ir_values_obj.sudo().set_default('product.template', "taxes_id", [taxes_ref[self.sale_tax_id.id]], for_all_users=True, company_id=company.id)
        if self.purchase_tax_id and taxes_ref:
            ir_values_obj.sudo().set_default('product.template', "supplier_taxes_id", [taxes_ref[self.purchase_tax_id.id]], for_all_users=True, company_id=company.id)

        # Create Bank journals
        self._create_bank_journals_from_o2m(company, acc_template_ref)

        # Create the current year earning account (outside of the CoA)
        self.env['account.account'].create({
            'code': '999999',
            'name': _('Undistributed Profits/Losses'),
            'user_type_id': self.env.ref("account.data_unaffected_earnings").id,
            'company_id': company.id,})
        return {}

    @api.multi
    def _create_bank_journals_from_o2m(self, company, acc_template_ref):
        '''
        This function creates bank journals and its accounts for each line encoded in the field bank_account_ids of the
        wizard (which is currently only used to create a default bank and cash journal when the CoA is installed).

        :param company: the company for which the wizard is running.
        :param acc_template_ref: the dictionary containing the mapping between the ids of account templates and the ids
            of the accounts that have been generated from them.
        '''
        self.ensure_one()
        # Create the journals that will trigger the account.account creation
        for acc in self.bank_account_ids:
            self.env['account.journal'].create({
                'name': acc.acc_name,
                'type': acc.account_type,
                'company_id': company.id,
                'currency_id': acc.currency_id.id,
            })


class AccountBankAccountsWizard(models.TransientModel):
    _name = 'account.bank.accounts.wizard'

    acc_name = fields.Char(string='Account Name.', required=True)
    bank_account_id = fields.Many2one('wizard.multi.charts.accounts', string='Bank Account', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', string='Account Currency',
        help="Forces all moves for this account to have this secondary currency.")
    account_type = fields.Selection([('cash', 'Cash'), ('bank', 'Bank')])
