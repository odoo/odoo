# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError
from odoo import api, fields, models, _
from odoo import SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.addons.account.models.account import TYPE_TAX_USE

import logging

_logger = logging.getLogger(__name__)

def migrate_set_tags_and_taxes_updatable(cr, registry, module):
    ''' This is a utility function used to manually set the flag noupdate to False on tags and account tax templates on localization modules
    that need migration (for example in case of VAT report improvements)
    '''
    env = api.Environment(cr, SUPERUSER_ID, {})
    xml_record_ids = env['ir.model.data'].search([
        ('model', 'in', ['account.tax.template', 'account.account.tag']),
        ('module', 'like', module)
    ]).ids
    if xml_record_ids:
        cr.execute("update ir_model_data set noupdate = 'f' where id in %s", (tuple(xml_record_ids),))

def preserve_existing_tags_on_taxes(cr, registry, module):
    ''' This is a utility function used to preserve existing previous tags during upgrade of the module.'''
    env = api.Environment(cr, SUPERUSER_ID, {})
    xml_records = env['ir.model.data'].search([('model', '=', 'account.account.tag'), ('module', 'like', module)])
    if xml_records:
        cr.execute("update ir_model_data set noupdate = 't' where id in %s", [tuple(xml_records.ids)])

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
    user_type_id = fields.Many2one('account.account.type', string='Type', required=True,
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
    group_id = fields.Many2one('account.group')
    root_id = fields.Many2one('account.root')

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
    _description = "Account Chart Template"

    name = fields.Char(required=True)
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
    bank_account_code_prefix = fields.Char(string='Prefix of the bank accounts', required=True)
    cash_account_code_prefix = fields.Char(string='Prefix of the main cash accounts', required=True)
    transfer_account_code_prefix = fields.Char(string='Prefix of the main transfer accounts', required=True)
    income_currency_exchange_account_id = fields.Many2one('account.account.template',
        string="Gain Exchange Rate Account", domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)])
    expense_currency_exchange_account_id = fields.Many2one('account.account.template',
        string="Loss Exchange Rate Account", domain=[('internal_type', '=', 'other'), ('deprecated', '=', False)])
    default_cash_difference_income_account_id = fields.Many2one('account.account.template', string="Cash Difference Income Account")
    default_cash_difference_expense_account_id = fields.Many2one('account.account.template', string="Cash Difference Expense Account")
    default_pos_receivable_account_id = fields.Many2one('account.account.template', string="PoS receivable account")
    property_account_receivable_id = fields.Many2one('account.account.template', string='Receivable Account')
    property_account_payable_id = fields.Many2one('account.account.template', string='Payable Account')
    property_account_expense_categ_id = fields.Many2one('account.account.template', string='Category of Expense Account')
    property_account_income_categ_id = fields.Many2one('account.account.template', string='Category of Income Account')
    property_account_expense_id = fields.Many2one('account.account.template', string='Expense Account on Product Template')
    property_account_income_id = fields.Many2one('account.account.template', string='Income Account on Product Template')
    property_stock_account_input_categ_id = fields.Many2one('account.account.template', string="Input Account for Stock Valuation")
    property_stock_account_output_categ_id = fields.Many2one('account.account.template', string="Output Account for Stock Valuation")
    property_stock_valuation_account_id = fields.Many2one('account.account.template', string="Account Template for Stock Valuation")
    property_tax_payable_account_id = fields.Many2one('account.account.template', string="Tax current account (payable)")
    property_tax_receivable_account_id = fields.Many2one('account.account.template', string="Tax current account (receivable)")
    property_advance_tax_payment_account_id = fields.Many2one('account.account.template', string="Advance tax payment account")

    @api.model
    def _prepare_transfer_account_template(self):
        ''' Prepare values to create the transfer account that is an intermediary account used when moving money
        from a liquidity account to another.

        :return:    A dictionary of values to create a new account.account.
        '''
        digits = self.code_digits
        prefix = self.transfer_account_code_prefix or ''
        # Flatten the hierarchy of chart templates.
        chart_template = self
        chart_templates = self
        while chart_template.parent_id:
            chart_templates += chart_template.parent_id
            chart_template = chart_template.parent_id
        new_code = ''
        for num in range(1, 100):
            new_code = str(prefix.ljust(digits - 1, '0')) + str(num)
            rec = self.env['account.account.template'].search(
                [('code', '=', new_code), ('chart_template_id', 'in', chart_templates.ids)], limit=1)
            if not rec:
                break
        else:
            raise UserError(_('Cannot generate an unused account code.'))
        current_assets_type = self.env.ref('account.data_account_type_current_assets', raise_if_not_found=False)
        return {
            'name': _('Liquidity Transfer'),
            'code': new_code,
            'user_type_id': current_assets_type and current_assets_type.id or False,
            'reconcile': True,
            'chart_template_id': self.id,
        }

    def try_loading(self, company=False):
        """ Installs this chart of accounts for the current company if not chart
        of accounts had been created for it yet.
        """
        # do not use `request.env` here, it can cause deadlocks
        if not company:
            if request and hasattr(request, 'allowed_company_ids'):
                company = self.env['res.company'].browse(request.allowed_company_ids[0])
            else:
                company = self.env.company
        # If we don't have any chart of account on this company, install this chart of account
        if not company.chart_template_id and not self.existing_accounting(company):
            for template in self:
                template.with_context(default_company_id=company.id)._load(15.0, 15.0, company)

    try_loading_for_current_company = try_loading

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        """ Installs this chart of accounts on the current company, replacing
        the existing one if it had already one defined. If some accounting entries
        had already been made, this function fails instead, triggering a UserError.

        Also, note that this function can only be run by someone with administration
        rights.
        """
        self.ensure_one()
        # do not use `request.env` here, it can cause deadlocks
        # Ensure everything is translated to the company's language, not the user's one.
        self = self.with_context(lang=company.partner_id.lang, company=company)
        if not self.env.is_admin():
            raise AccessError(_("Only administrators can load a chart of accounts"))

        existing_accounts = self.env['account.account'].search([('company_id', '=', company.id)])
        if existing_accounts:
            # we tolerate switching from accounting package (localization module) as long as there isn't yet any accounting
            # entries created for the company.
            if self.existing_accounting(company):
                raise UserError(_('Could not install new chart of account as there are already accounting entries existing.'))

            # delete accounting properties
            prop_values = ['account.account,%s' % (account_id,) for account_id in existing_accounts.ids]
            existing_journals = self.env['account.journal'].search([('company_id', '=', company.id)])
            if existing_journals:
                prop_values.extend(['account.journal,%s' % (journal_id,) for journal_id in existing_journals.ids])
            accounting_props = self.env['ir.property'].search([('value_reference', 'in', prop_values)])
            if accounting_props:
                accounting_props.sudo().unlink()

            # delete account, journal, tax, fiscal position and reconciliation model
            models_to_delete = ['account.reconcile.model', 'account.fiscal.position', 'account.tax', 'account.move', 'account.journal']
            for model in models_to_delete:
                res = self.env[model].sudo().search([('company_id', '=', company.id)])
                if len(res):
                    res.unlink()
            existing_accounts.unlink()

        company.write({'currency_id': self.currency_id.id,
                       'anglo_saxon_accounting': self.use_anglo_saxon,
                       'bank_account_code_prefix': self.bank_account_code_prefix,
                       'cash_account_code_prefix': self.cash_account_code_prefix,
                       'transfer_account_code_prefix': self.transfer_account_code_prefix,
                       'chart_template_id': self.id
        })

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
        self._create_tax_templates_from_rates(company.id, sale_tax_rate, purchase_tax_rate)

        # Install all the templates objects and generate the real objects
        acc_template_ref, taxes_ref = self._install_template(company, code_digits=self.code_digits)

        # Set the transfer account on the company
        company.transfer_account_id = self.env['account.account'].search([
            ('code', '=like', self.transfer_account_code_prefix + '%'), ('company_id', '=', company.id)], limit=1)

        # Create Bank journals
        self._create_bank_journals(company, acc_template_ref)

        # Create the current year earning account if it wasn't present in the CoA
        company.get_unaffected_earnings_account()

        # set the default taxes on the company
        company.account_sale_tax_id = self.env['account.tax'].search([('type_tax_use', 'in', ('sale', 'all')), ('company_id', '=', company.id)], limit=1).id
        company.account_purchase_tax_id = self.env['account.tax'].search([('type_tax_use', 'in', ('purchase', 'all')), ('company_id', '=', company.id)], limit=1).id

        return {}

    @api.model
    def existing_accounting(self, company_id):
        """ Returns True iff some accounting entries have already been made for
        the provided company (meaning hence that its chart of accounts cannot
        be changed anymore).
        """
        model_to_check = ['account.move.line', 'account.payment', 'account.bank.statement']
        for model in model_to_check:
            if self.env[model].sudo().search([('company_id', '=', company_id.id)], limit=1):
                return True
        if self.env['account.move'].sudo().search([('company_id', '=', company_id.id), ('name', '!=', '/')], limit=1):
            return True
        return False

    def _create_tax_templates_from_rates(self, company_id, sale_tax_rate, purchase_tax_rate):
        '''
        This function checks if this chart template is configured as containing a full set of taxes, and if
        it's not the case, it creates the templates for account.tax object accordingly to the provided sale/purchase rates.
        Then it saves the new tax templates as default taxes to use for this chart template.

        :param company_id: id of the company for which the wizard is running
        :param sale_tax_rate: the rate to use for created sales tax
        :param purchase_tax_rate: the rate to use for created purchase tax
        :return: True
        '''
        self.ensure_one()
        obj_tax_temp = self.env['account.tax.template']
        all_parents = self._get_chart_parent_ids()
        # create tax templates from purchase_tax_rate and sale_tax_rate fields
        if not self.complete_tax_set:
            ref_taxs = obj_tax_temp.search([('type_tax_use', '=', 'sale'), ('chart_template_id', 'in', all_parents)], order="sequence, id desc", limit=1)
            ref_taxs.write({'amount': sale_tax_rate, 'name': _('Tax %.2f%%') % sale_tax_rate, 'description': '%.2f%%' % sale_tax_rate})
            ref_taxs = obj_tax_temp.search([('type_tax_use', '=', 'purchase'), ('chart_template_id', 'in', all_parents)], order="sequence, id desc", limit=1)
            ref_taxs.write({'amount': purchase_tax_rate, 'name': _('Tax %.2f%%') % purchase_tax_rate, 'description': '%.2f%%' % purchase_tax_rate})
        return True

    def _get_chart_parent_ids(self):
        """ Returns the IDs of all ancestor charts, including the chart itself.
            (inverse of child_of operator)

            :return: the IDS of all ancestor charts, including the chart itself.
        """
        chart_template = self
        result = [chart_template.id]
        while chart_template.parent_id:
            chart_template = chart_template.parent_id
            result.append(chart_template.id)
        return result

    def _create_bank_journals(self, company, acc_template_ref):
        '''
        This function creates bank journals and their account for each line
        data returned by the function _get_default_bank_journals_data.

        :param company: the company for which the wizard is running.
        :param acc_template_ref: the dictionary containing the mapping between the ids of account templates and the ids
            of the accounts that have been generated from them.
        '''
        self.ensure_one()
        bank_journals = self.env['account.journal']
        # Create the journals that will trigger the account.account creation
        for acc in self._get_default_bank_journals_data():
            bank_journals += self.env['account.journal'].create({
                'name': acc['acc_name'],
                'type': acc['account_type'],
                'company_id': company.id,
                'currency_id': acc.get('currency_id', self.env['res.currency']).id,
                'sequence': 10
            })

        return bank_journals

    def get_countries_posting_at_bank_rec(self):
        """ Returns the list of the country codes of the countries for which, by default,
        payments made on bank journals should be creating draft account.move objects,
        which get in turn posted when their payment gets reconciled with a bank statement line.
        This function is an extension hook for localization modules.
        """
        return []

    @api.model
    def _get_default_bank_journals_data(self):
        """ Returns the data needed to create the default bank journals when
        installing this chart of accounts, in the form of a list of dictionaries.
        The allowed keys in these dictionaries are:
            - acc_name: string (mandatory)
            - account_type: 'cash' or 'bank' (mandatory)
            - currency_id (optional, only to be specified if != company.currency_id)
        """
        return [{'acc_name': _('Cash'), 'account_type': 'cash'}, {'acc_name': _('Bank'), 'account_type': 'bank'}]

    def open_select_template_wizard(self):
        # Add action to open wizard to select between several templates
        if not self.company_id.chart_template_id:
            todo = self.env['ir.actions.todo']
            action_rec = self.env['ir.model.data'].xmlid_to_object('account.action_wizard_multi_chart')
            if action_rec:
                todo.create({'action_id': action_rec.id, 'name': _('Choose Accounting Template')})
        return True

    @api.model
    def _prepare_transfer_account_for_direct_creation(self, name, company):
        """ Prepare values to create a transfer account directly, based on the
        method _prepare_transfer_account_template().

        This is needed when dealing with installation of payment modules
        that requires the creation of their own transfer account.

        :param name:        The transfer account name.
        :param company:     The company owning this account.
        :return:            A dictionary of values to create a new account.account.
        """
        vals = self._prepare_transfer_account_template()
        digits = self.code_digits or 6
        prefix = self.transfer_account_code_prefix or ''
        vals.update({
            'code': self.env['account.account']._search_new_account_code(company, digits, prefix),
            'name': name,
            'company_id': company.id,
        })
        del(vals['chart_template_id'])
        return vals

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        """
        This method is used for creating journals.

        :param acc_template_ref: Account templates reference.
        :param company_id: company to generate journals for.
        :returns: True
        """
        JournalObj = self.env['account.journal']
        for vals_journal in self._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict):
            journal = JournalObj.create(vals_journal)
            if vals_journal['type'] == 'general' and vals_journal['code'] == _('EXCH'):
                company.write({'currency_exchange_journal_id': journal.id})
            if vals_journal['type'] == 'general' and vals_journal['code'] == _('CABA'):
                company.write({'tax_cash_basis_journal_id': journal.id})
        return True

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

        journals = [{'name': _('Customer Invoices'), 'type': 'sale', 'code': _('INV'), 'favorite': True, 'color': 11, 'sequence': 5},
                    {'name': _('Vendor Bills'), 'type': 'purchase', 'code': _('BILL'), 'favorite': True, 'color': 11, 'sequence': 6},
                    {'name': _('Miscellaneous Operations'), 'type': 'general', 'code': _('MISC'), 'favorite': True, 'sequence': 7},
                    {'name': _('Exchange Difference'), 'type': 'general', 'code': _('EXCH'), 'favorite': False, 'sequence': 9},
                    {'name': _('Cash Basis Taxes'), 'type': 'general', 'code': _('CABA'), 'favorite': False, 'sequence': 10}]
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
                'color': journal.get('color', False),
                'sequence': journal['sequence']
            }
            journal_data.append(vals)
        return journal_data

    def generate_properties(self, acc_template_ref, company):
        """
        This method used for creating properties.

        :param acc_template_ref: Mapping between ids of account templates and real accounts created from them
        :param company_id: company to generate properties for.
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
            ('property_tax_payable_account_id', 'account.tax.group', 'account.account'),
            ('property_tax_receivable_account_id', 'account.tax.group', 'account.account'),
            ('property_advance_tax_payment_account_id', 'account.tax.group', 'account.account'),
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

    def _install_template(self, company, code_digits=None, obj_wizard=None, acc_ref=None, taxes_ref=None):
        """ Recursively load the template objects and create the real objects from them.

            :param company: company the wizard is running for
            :param code_digits: number of digits the accounts code should have in the COA
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
            tmp1, tmp2 = self.parent_id._install_template(company, code_digits=code_digits, acc_ref=acc_ref, taxes_ref=taxes_ref)
            acc_ref.update(tmp1)
            taxes_ref.update(tmp2)
        # Ensure, even if individually, that everything is translated according to the company's language.
        tmp1, tmp2 = self.with_context(lang=company.partner_id.lang)._load_template(company, code_digits=code_digits, account_ref=acc_ref, taxes_ref=taxes_ref)
        acc_ref.update(tmp1)
        taxes_ref.update(tmp2)
        return acc_ref, taxes_ref

    def _load_template(self, company, code_digits=None, account_ref=None, taxes_ref=None):
        """ Generate all the objects from the templates

            :param company: company the wizard is running for
            :param code_digits: number of digits the accounts code should have in the COA
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
        AccountTaxObj = self.env['account.tax']

        # Generate taxes from templates.
        generated_tax_res = self.with_context(active_test=False).tax_template_ids._generate_tax(company)
        taxes_ref.update(generated_tax_res['tax_template_to_tax'])

        # Generating Accounts from templates.
        account_template_ref = self.generate_account(taxes_ref, account_ref, code_digits, company)
        account_ref.update(account_template_ref)

        # writing account values after creation of accounts
        for key, value in generated_tax_res['account_dict']['account.tax'].items():
            if value['cash_basis_transition_account_id'] or value['cash_basis_base_account_id']:
                AccountTaxObj.browse(key).write({
                    'cash_basis_transition_account_id': account_ref.get(value['cash_basis_transition_account_id'], False),
                    'cash_basis_base_account_id': account_ref.get(value['cash_basis_base_account_id'], False),
                })

        AccountTaxRepartitionLineObj = self.env['account.tax.repartition.line']
        for key, value in generated_tax_res['account_dict']['account.tax.repartition.line'].items():
            if value['account_id']:
                AccountTaxRepartitionLineObj.browse(key).write({
                    'account_id': account_ref.get(value['account_id']),
                })

        # Set the company accounts
        self._load_company_accounts(account_ref, company)

        # Create Journals - Only done for root chart template
        if not self.parent_id:
            self.generate_journals(account_ref, company)

        # generate properties function
        self.generate_properties(account_ref, company)

        # Generate Fiscal Position , Fiscal Position Accounts and Fiscal Position Taxes from templates
        self.generate_fiscal_position(taxes_ref, account_ref, company)

        # Generate account operation template templates
        self.generate_account_reconcile_model(taxes_ref, account_ref, company)

        return account_ref, taxes_ref

    def _load_company_accounts(self, account_ref, company):
        # Set the default accounts on the company
        accounts = {
            'default_cash_difference_income_account_id': self.default_cash_difference_income_account_id.id,
            'default_cash_difference_expense_account_id': self.default_cash_difference_expense_account_id.id,
            'account_default_pos_receivable_account_id': self.default_pos_receivable_account_id.id,
        }

        values = {}

        # The loop is to avoid writing when we have no values, thus avoiding erasing the account from the parent
        for key, account in accounts.items():
            if account_ref.get(account):
                values[key] = account_ref.get(account)

        company.write(values)

    def create_record_with_xmlid(self, company, template, model, vals):
        return self._create_records_with_xmlid(model, [(template, vals)], company).id

    def _create_records_with_xmlid(self, model, template_vals, company):
        """ Create records for the given model name with the given vals, and
            create xml ids based on each record's template and company id.
        """
        if not template_vals:
            return self.env[model]
        template_model = template_vals[0][0]
        template_ids = [template.id for template, vals in template_vals]
        template_xmlids = template_model.browse(template_ids).get_external_id()
        data_list = []
        for template, vals in template_vals:
            module, name = template_xmlids[template.id].split('.', 1)
            xml_id = "%s.%s_%s" % (module, company.id, name)
            data_list.append(dict(xml_id=xml_id, values=vals, noupdate=True))
        return self.env[model]._load_records(data_list)

    @api.model
    def _load_records(self, data_list, update=False):
        # When creating a chart template create, for the liquidity transfer account
        #  - an account.account.template: this allow to define account.reconcile.model.template objects refering that liquidity transfer
        #    account although it's not existing in any xml file
        #  - an entry in ir_model_data: this allow to still use the method create_record_with_xmlid() and don't make any difference between
        #    regular accounts created and that liquidity transfer account
        records = super(AccountChartTemplate, self)._load_records(data_list, update)
        account_data_list = []
        for data, record in zip(data_list, records):
            # Create the transfer account only for leaf chart template in the hierarchy.
            if record.parent_id:
                continue
            if data.get('xml_id'):
                account_xml_id = data['xml_id'] + '_liquidity_transfer'
                if not self.env.ref(account_xml_id, raise_if_not_found=False):
                    account_vals = record._prepare_transfer_account_template()
                    account_data_list.append(dict(
                        xml_id=account_xml_id,
                        values=account_vals,
                        noupdate=data.get('noupdate'),
                    ))
        self.env['account.account.template']._load_records(account_data_list, update)
        return records

    def _get_account_vals(self, company, account_template, code_acc, tax_template_ref):
        """ This method generates a dictionary of all the values for the account that will be created.
        """
        self.ensure_one()
        tax_ids = []
        for tax in account_template.tax_ids:
            tax_ids.append(tax_template_ref[tax.id])
        val = {
                'name': account_template.name,
                'currency_id': account_template.currency_id and account_template.currency_id.id or False,
                'code': code_acc,
                'user_type_id': account_template.user_type_id and account_template.user_type_id.id or False,
                'reconcile': account_template.reconcile,
                'note': account_template.note,
                'tax_ids': [(6, 0, tax_ids)],
                'company_id': company.id,
                'tag_ids': [(6, 0, [t.id for t in account_template.tag_ids])],
                'group_id': account_template.group_id.id,
            }
        return val

    def generate_account(self, tax_template_ref, acc_template_ref, code_digits, company):
        """ This method generates accounts from account templates.

        :param tax_template_ref: Taxes templates reference for write taxes_id in account_account.
        :param acc_template_ref: dictionary containing the mapping between the account templates and generated accounts (will be populated)
        :param code_digits: number of digits to use for account code.
        :param company_id: company to generate accounts for.
        :returns: return acc_template_ref for reference purpose.
        :rtype: dict
        """
        self.ensure_one()
        account_tmpl_obj = self.env['account.account.template']
        acc_template = account_tmpl_obj.search([('nocreate', '!=', True), ('chart_template_id', '=', self.id)], order='id')
        template_vals = []
        for account_template in acc_template:
            code_main = account_template.code and len(account_template.code) or 0
            code_acc = account_template.code or ''
            if code_main > 0 and code_main <= code_digits:
                code_acc = str(code_acc) + (str('0'*(code_digits-code_main)))
            vals = self._get_account_vals(company, account_template, code_acc, tax_template_ref)
            template_vals.append((account_template, vals))
        accounts = self._create_records_with_xmlid('account.account', template_vals, company)
        for template, account in zip(acc_template, accounts):
            acc_template_ref[template.id] = account.id
        return acc_template_ref

    def _prepare_reconcile_model_vals(self, company, account_reconcile_model, acc_template_ref, tax_template_ref):
        """ This method generates a dictionary of all the values for the account.reconcile.model that will be created.
        """
        self.ensure_one()
        return {
                'name': account_reconcile_model.name,
                'sequence': account_reconcile_model.sequence,
                'has_second_line': account_reconcile_model.has_second_line,
                'company_id': company.id,
                'account_id': acc_template_ref[account_reconcile_model.account_id.id],
                'label': account_reconcile_model.label,
                'to_check': account_reconcile_model.to_check,
                'amount_type': account_reconcile_model.amount_type,
                'force_tax_included': account_reconcile_model.force_tax_included,
                'amount': account_reconcile_model.amount,
                'tax_ids': [[4, tax_template_ref[tax.id], 0] for tax in account_reconcile_model.tax_ids],
                'second_account_id': account_reconcile_model.second_account_id and acc_template_ref[account_reconcile_model.second_account_id.id] or False,
                'second_label': account_reconcile_model.second_label,
                'second_amount_type': account_reconcile_model.second_amount_type,
                'force_second_tax_included': account_reconcile_model.force_second_tax_included,
                'second_amount': account_reconcile_model.second_amount,
                'rule_type': account_reconcile_model.rule_type,
                'auto_reconcile': account_reconcile_model.auto_reconcile,
                'match_journal_ids': [(6, None, account_reconcile_model.match_journal_ids.ids)],
                'match_nature': account_reconcile_model.match_nature,
                'match_amount': account_reconcile_model.match_amount,
                'match_amount_min': account_reconcile_model.match_amount_min,
                'match_amount_max': account_reconcile_model.match_amount_max,
                'match_label': account_reconcile_model.match_label,
                'match_label_param': account_reconcile_model.match_label_param,
                'match_note': account_reconcile_model.match_note,
                'match_note_param': account_reconcile_model.match_note_param,
                'match_transaction_type': account_reconcile_model.match_transaction_type,
                'match_transaction_type_param': account_reconcile_model.match_transaction_type_param,
                'match_same_currency': account_reconcile_model.match_same_currency,
                'match_total_amount': account_reconcile_model.match_total_amount,
                'match_total_amount_param': account_reconcile_model.match_total_amount_param,
                'match_partner': account_reconcile_model.match_partner,
                'match_partner_ids': [(6, None, account_reconcile_model.match_partner_ids.ids)],
                'match_partner_category_ids': [(6, None, account_reconcile_model.match_partner_category_ids.ids)],
                'second_tax_ids': [[4, tax_template_ref[tax.id], 0] for tax in account_reconcile_model.second_tax_ids],
            }

    def generate_account_reconcile_model(self, tax_template_ref, acc_template_ref, company):
        """ This method creates account reconcile models

        :param tax_template_ref: Taxes templates reference for write taxes_id in account_account.
        :param acc_template_ref: dictionary with the mapping between the account templates and the real accounts.
        :param company_id: company to create models for
        :returns: return new_account_reconcile_model for reference purpose.
        :rtype: dict
        """
        self.ensure_one()
        account_reconcile_models = self.env['account.reconcile.model.template'].search([
            ('chart_template_id', '=', self.id)
        ])
        for account_reconcile_model in account_reconcile_models:
            vals = self._prepare_reconcile_model_vals(company, account_reconcile_model, acc_template_ref, tax_template_ref)
            self.create_record_with_xmlid(company, account_reconcile_model, 'account.reconcile.model', vals)
        # Create a default rule for the reconciliation widget matching invoices automatically.
        self.env['account.reconcile.model'].sudo().create({
            "name": _('Invoices Matching Rule'),
            "sequence": '1',
            "rule_type": 'invoice_matching',
            "auto_reconcile": False,
            "match_nature": 'both',
            "match_same_currency": True,
            "match_total_amount": True,
            "match_total_amount_param": 100,
            "match_partner": True,
            "company_id": company.id,
        })
        return True

    def _get_fp_vals(self, company, position):
        return {
            'company_id': company.id,
            'sequence': position.sequence,
            'name': position.name,
            'note': position.note,
            'auto_apply': position.auto_apply,
            'vat_required': position.vat_required,
            'country_id': position.country_id.id,
            'country_group_id': position.country_group_id.id,
            'state_ids': position.state_ids and [(6,0, position.state_ids.ids)] or [],
            'zip_from': position.zip_from,
            'zip_to': position.zip_to,
        }

    def generate_fiscal_position(self, tax_template_ref, acc_template_ref, company):
        """ This method generates Fiscal Position, Fiscal Position Accounts
        and Fiscal Position Taxes from templates.

        :param taxes_ids: Taxes templates reference for generating account.fiscal.position.tax.
        :param acc_template_ref: Account templates reference for generating account.fiscal.position.account.
        :param company_id: the company to generate fiscal position data for
        :returns: True
        """
        self.ensure_one()
        positions = self.env['account.fiscal.position.template'].search([('chart_template_id', '=', self.id)])

        # first create fiscal positions in batch
        template_vals = []
        for position in positions:
            fp_vals = self._get_fp_vals(company, position)
            template_vals.append((position, fp_vals))
        fps = self._create_records_with_xmlid('account.fiscal.position', template_vals, company)

        # then create fiscal position taxes and accounts
        tax_template_vals = []
        account_template_vals = []
        for position, fp in zip(positions, fps):
            for tax in position.tax_ids:
                tax_template_vals.append((tax, {
                    'tax_src_id': tax_template_ref[tax.tax_src_id.id],
                    'tax_dest_id': tax.tax_dest_id and tax_template_ref[tax.tax_dest_id.id] or False,
                    'position_id': fp.id,
                }))
            for acc in position.account_ids:
                account_template_vals.append((acc, {
                    'account_src_id': acc_template_ref[acc.account_src_id.id],
                    'account_dest_id': acc_template_ref[acc.account_dest_id.id],
                    'position_id': fp.id,
                }))
        self._create_records_with_xmlid('account.fiscal.position.tax', tax_template_vals, company)
        self._create_records_with_xmlid('account.fiscal.position.account', account_template_vals, company)

        return True


class AccountTaxTemplate(models.Model):
    _name = 'account.tax.template'
    _description = 'Templates for Taxes'
    _order = 'id'

    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)

    name = fields.Char(string='Tax Name', required=True)
    type_tax_use = fields.Selection(TYPE_TAX_USE, string='Tax Scope', required=True, default="sale",
        help="Determines where the tax is selectable. Note : 'None' means a tax can't be used by itself, however it can still be used in a group.")
    amount_type = fields.Selection(default='percent', string="Tax Computation", required=True,
        selection=[('group', 'Group of Taxes'), ('fixed', 'Fixed'), ('percent', 'Percentage of Price'), ('division', 'Percentage of Price Tax Included')])
    active = fields.Boolean(default=True, help="Set active to false to hide the tax without removing it.")
    children_tax_ids = fields.Many2many('account.tax.template', 'account_tax_template_filiation_rel', 'parent_tax', 'child_tax', string='Children Taxes')
    sequence = fields.Integer(required=True, default=1,
        help="The sequence field is used to define order in which the tax lines are applied.")
    amount = fields.Float(required=True, digits=(16, 4), default=0)
    description = fields.Char(string='Display on Invoices')
    price_include = fields.Boolean(string='Included in Price', default=False,
        help="Check this if the price you use on the product and invoices includes this tax.")
    include_base_amount = fields.Boolean(string='Affect Subsequent Taxes', default=False,
        help="If set, taxes which are computed after this one will be computed based on the price tax included.")
    analytic = fields.Boolean(string="Analytic Cost", help="If set, the amount computed by this tax will be assigned to the same analytic account as the invoice line (if any)")
    invoice_repartition_line_ids = fields.One2many(string="Repartition for Invoices", comodel_name="account.tax.repartition.line.template", inverse_name="invoice_tax_id", copy=True, help="Repartition when the tax is used on an invoice")
    refund_repartition_line_ids = fields.One2many(string="Repartition for Refund Invoices", comodel_name="account.tax.repartition.line.template", inverse_name="refund_tax_id", copy=True, help="Repartition when the tax is used on a refund")
    tax_group_id = fields.Many2one('account.tax.group', string="Tax Group")
    tax_exigibility = fields.Selection(
        [('on_invoice', 'Based on Invoice'),
         ('on_payment', 'Based on Payment'),
        ], string='Tax Due', default='on_invoice',
        help="Based on Invoice: the tax is due as soon as the invoice is validated.\n"
        "Based on Payment: the tax is due as soon as the payment of the invoice is received.")
    cash_basis_transition_account_id = fields.Many2one(
        comodel_name='account.account.template',
        string="Cash Basis Transition Account",
        domain=[('deprecated', '=', False)],
        help="Account used to transition the tax amount for cash basis taxes. It will contain the tax amount as long as the original invoice has not been reconciled ; at reconciliation, this amount cancelled on this account and put on the regular tax account.")
    cash_basis_base_account_id = fields.Many2one(
        'account.account.template',
        domain=[('deprecated', '=', False)],
        string='Base Tax Received Account',
        help='Account that will be set on lines created in cash basis journal entry and used to keep track of the tax base amount.')

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, type_tax_use, chart_template_id)', 'Tax names must be unique !'),
    ]

    @api.depends('name', 'description')
    def name_get(self):
        res = []
        for record in self:
            name = record.description and record.description or record.name
            res.append((record.id, name))
        return res

    def _get_tax_vals(self, company, tax_template_to_tax):
        """ This method generates a dictionary of all the values for the tax that will be created.
        """
        # Compute children tax ids
        children_ids = []
        for child_tax in self.children_tax_ids:
            if tax_template_to_tax.get(child_tax.id):
                children_ids.append(tax_template_to_tax[child_tax.id])
        self.ensure_one()
        val = {
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
            'children_tax_ids': [(6, 0, children_ids)],
            'tax_exigibility': self.tax_exigibility,
        }

        # We add repartition lines if there are some, so that if there are none,
        # default_get is called and creates the default ones properly.
        if self.invoice_repartition_line_ids:
            val['invoice_repartition_line_ids'] = self.invoice_repartition_line_ids.get_repartition_line_create_vals(company)
        if self.refund_repartition_line_ids:
            val['refund_repartition_line_ids'] = self.refund_repartition_line_ids.get_repartition_line_create_vals(company)

        if self.tax_group_id:
            val['tax_group_id'] = self.tax_group_id.id
        return val

    def _generate_tax(self, company):
        """ This method generate taxes from templates.

            :param company: the company for which the taxes should be created from templates in self
            :returns: {
                'tax_template_to_tax': mapping between tax template and the newly generated taxes corresponding,
                'account_dict': dictionary containing a to-do list with all the accounts to assign on new taxes
            }
        """
        # default_company_id is needed in context to allow creation of default
        # repartition lines on taxes
        ChartTemplate = self.env['account.chart.template'].with_context(default_company_id=company.id)
        todo_dict = {'account.tax': {}, 'account.tax.repartition.line': {}}
        tax_template_to_tax = {}

        templates_todo = list(self)
        while templates_todo:
            templates = templates_todo
            templates_todo = []

            # create taxes in batch
            tax_template_vals = []
            for template in templates:
                if all(child.id in tax_template_to_tax for child in template.children_tax_ids):
                    vals = template._get_tax_vals(company, tax_template_to_tax)
                    tax_template_vals.append((template, vals))
                else:
                    # defer the creation of this tax to the next batch
                    templates_todo.append(template)
            taxes = ChartTemplate._create_records_with_xmlid('account.tax', tax_template_vals, company)

            # fill in tax_template_to_tax and todo_dict
            for tax, (template, vals) in zip(taxes, tax_template_vals):
                tax_template_to_tax[template.id] = tax.id
                # Since the accounts have not been created yet, we have to wait before filling these fields
                todo_dict['account.tax'][tax.id] = {
                    'cash_basis_transition_account_id': template.cash_basis_transition_account_id.id,
                    'cash_basis_base_account_id': template.cash_basis_base_account_id.id,
                }

                # We also have to delay the assignation of accounts to repartition lines
                # The below code assigns the account_id to the repartition lines according
                # to the corresponding repartition line in the template, based on the order.
                # As we just created the repartition lines, tax.invoice_repartition_line_ids is not well sorted.
                # But we can force the sort by calling sort()
                all_tax_rep_lines = tax.invoice_repartition_line_ids.sorted() + tax.refund_repartition_line_ids.sorted()
                all_template_rep_lines = template.invoice_repartition_line_ids + template.refund_repartition_line_ids
                for i in range(0, len(all_template_rep_lines)):
                    # We assume template and tax repartition lines are in the same order
                    template_account = all_template_rep_lines[i].account_id
                    if template_account:
                        todo_dict['account.tax.repartition.line'][all_tax_rep_lines[i].id] = {
                            'account_id': template_account.id,
                        }

        if any(template.tax_exigibility == 'on_payment' for template in self):
            # When a CoA is being installed automatically and if it is creating account tax(es) whose field `Use Cash Basis`(tax_exigibility) is set to True by default
            # (example of such CoA's are l10n_fr and l10n_mx) then in the `Accounting Settings` the option `Cash Basis` should be checked by default.
            company.tax_exigibility = True

        return {
            'tax_template_to_tax': tax_template_to_tax,
            'account_dict': todo_dict
        }

# Tax Repartition Line Template

class AccountTaxRepartitionLineTemplate(models.Model):
    _name = "account.tax.repartition.line.template"
    _description = "Tax Repartition Line Template"

    factor_percent = fields.Float(string="%", required=True, help="Factor to apply on the account move lines generated from this repartition line, in percents")
    repartition_type = fields.Selection(string="Based On", selection=[('base', 'Base'), ('tax', 'of tax')], required=True, default='tax', help="Base on which the factor will be applied.")
    account_id = fields.Many2one(string="Account", comodel_name='account.account.template', help="Account on which to post the tax amount")
    invoice_tax_id = fields.Many2one(comodel_name='account.tax.template', help="The tax set to apply this repartition on invoices. Mutually exclusive with refund_tax_id")
    refund_tax_id = fields.Many2one(comodel_name='account.tax.template', help="The tax set to apply this repartition on refund invoices. Mutually exclusive with invoice_tax_id")
    tag_ids = fields.Many2many(string="Financial Tags", relation='account_tax_repartition_financial_tags', comodel_name='account.account.tag', copy=True, help="Additional tags that will be assigned by this repartition line for use in financial reports")

    # These last two fields are helpers used to ease the declaration of account.account.tag objects in XML.
    # They are directly linked to account.tax.report.line objects, which create corresponding + and - tags
    # at creation. This way, we avoid declaring + and - separately every time.
    plus_report_line_ids = fields.Many2many(string="Plus Tax Report Lines", relation='account_tax_repartition_plus_report_line', comodel_name='account.tax.report.line', copy=True, help="Tax report lines whose '+' tag will be assigned to move lines by this repartition line")
    minus_report_line_ids = fields.Many2many(string="Minus Report Lines", relation='account_tax_repartition_minus_report_line', comodel_name='account.tax.report.line', copy=True, help="Tax report lines whose '-' tag will be assigned to move lines by this repartition line")

    @api.model
    def create(self, vals):
        if vals.get('plus_report_line_ids'):
            vals['plus_report_line_ids'] =  self._convert_tag_syntax_to_orm(vals['plus_report_line_ids'])

        if vals.get('minus_report_line_ids'):
            vals['minus_report_line_ids'] = self._convert_tag_syntax_to_orm(vals['minus_report_line_ids'])

        if vals.get('tag_ids'):
            vals['tag_ids'] = self._convert_tag_syntax_to_orm(vals['tag_ids'])

        return super(AccountTaxRepartitionLineTemplate, self).create(vals)

    @api.model
    def _convert_tag_syntax_to_orm(self, tags_list):
        """ Repartition lines give the possibility to directly give
        a list of ids to create for tags instead of a list of ORM commands.

        This function checks that tags_list uses this syntactic sugar and returns
        an ORM-compliant version of it if it does.
        """
        if tags_list and all(isinstance(elem, int) for elem in tags_list):
            return [(6, False, tags_list)]
        return tags_list

    @api.constrains('invoice_tax_id', 'refund_tax_id')
    def validate_tax_template_link(self):
        for record in self:
            if record.invoice_tax_id and record.refund_tax_id:
                raise ValidationError(_("Tax repartition line templates should apply to either invoices or refunds, not both at the same time. invoice_tax_id and refund_tax_id should not be set together."))

    @api.constrains('plus_report_line_ids', 'minus_report_line_ids')
    def validate_tags(self):
        all_tax_rep_lines = self.mapped('plus_report_line_ids') + self.mapped('minus_report_line_ids')
        lines_without_tag = all_tax_rep_lines.filtered(lambda x: not x.tag_name)
        if lines_without_tag:
            raise ValidationError(_("The following tax report lines are used in some tax repartition template though they don't generate any tag: %s . This probably means you forgot to set a tag_name on these lines.") % str(lines_without_tag.mapped('name')))

    def get_repartition_line_create_vals(self, company):
        rslt = [(5, 0, 0)]
        for record in self:
            tags_to_add = self.env['account.account.tag']
            tags_to_add += record.plus_report_line_ids.mapped('tag_ids').filtered(lambda x: not x.tax_negate)
            tags_to_add += record.minus_report_line_ids.mapped('tag_ids').filtered(lambda x: x.tax_negate)
            tags_to_add += record.tag_ids

            rslt.append((0, 0, {
                'factor_percent': record.factor_percent,
                'repartition_type': record.repartition_type,
                'tag_ids': [(6, 0, tags_to_add.ids)],
                'company_id': company.id,
            }))
        return rslt

# Fiscal Position Templates

class AccountFiscalPositionTemplate(models.Model):
    _name = 'account.fiscal.position.template'
    _description = 'Template for Fiscal Position'

    sequence = fields.Integer()
    name = fields.Char(string='Fiscal Position Template', required=True)
    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)
    account_ids = fields.One2many('account.fiscal.position.account.template', 'position_id', string='Account Mapping')
    tax_ids = fields.One2many('account.fiscal.position.tax.template', 'position_id', string='Tax Mapping')
    note = fields.Text(string='Notes')
    auto_apply = fields.Boolean(string='Detect Automatically', help="Apply automatically this fiscal position.")
    vat_required = fields.Boolean(string='VAT required', help="Apply only if partner has a VAT number.")
    country_id = fields.Many2one('res.country', string='Country',
        help="Apply only if delivery or invoicing country match.")
    country_group_id = fields.Many2one('res.country.group', string='Country Group',
        help="Apply only if delivery or invoicing country match the group.")
    state_ids = fields.Many2many('res.country.state', string='Federal States')
    zip_from = fields.Char(string='Zip Range From')
    zip_to = fields.Char(string='Zip Range To')


class AccountFiscalPositionTaxTemplate(models.Model):
    _name = 'account.fiscal.position.tax.template'
    _description = 'Tax Mapping Template of Fiscal Position'
    _rec_name = 'position_id'

    position_id = fields.Many2one('account.fiscal.position.template', string='Fiscal Position', required=True, ondelete='cascade')
    tax_src_id = fields.Many2one('account.tax.template', string='Tax Source', required=True)
    tax_dest_id = fields.Many2one('account.tax.template', string='Replacement Tax')


class AccountFiscalPositionAccountTemplate(models.Model):
    _name = 'account.fiscal.position.account.template'
    _description = 'Accounts Mapping Template of Fiscal Position'
    _rec_name = 'position_id'

    position_id = fields.Many2one('account.fiscal.position.template', string='Fiscal Mapping', required=True, ondelete='cascade')
    account_src_id = fields.Many2one('account.account.template', string='Account Source', required=True)
    account_dest_id = fields.Many2one('account.account.template', string='Account Destination', required=True)


class AccountReconcileModelTemplate(models.Model):
    _name = "account.reconcile.model.template"
    _description = 'Reconcile Model Template'

    # Base fields.
    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)
    name = fields.Char(string='Button Label', required=True)
    sequence = fields.Integer(required=True, default=10)

    rule_type = fields.Selection(selection=[
        ('writeoff_button', 'Manually create a write-off on clicked button.'),
        ('writeoff_suggestion', 'Suggest a write-off.'),
        ('invoice_matching', 'Match existing invoices/bills.')
    ], string='Type', default='writeoff_button', required=True)
    auto_reconcile = fields.Boolean(string='Auto-validate',
        help='Validate the statement line automatically (reconciliation based on your rule).')
    to_check = fields.Boolean(string='To Check', default=False, help='This matching rule is used when the user is not certain of all the informations of the counterpart.')

    # ===== Conditions =====
    match_journal_ids = fields.Many2many('account.journal', string='Journals',
        domain="[('type', 'in', ('bank', 'cash'))]",
        help='The reconciliation model will only be available from the selected journals.')
    match_nature = fields.Selection(selection=[
        ('amount_received', 'Amount Received'),
        ('amount_paid', 'Amount Paid'),
        ('both', 'Amount Paid/Received')
    ], string='Amount Nature', required=True, default='both',
        help='''The reconciliation model will only be applied to the selected transaction type:
        * Amount Received: Only applied when receiving an amount.
        * Amount Paid: Only applied when paying an amount.
        * Amount Paid/Received: Applied in both cases.''')
    match_amount = fields.Selection(selection=[
        ('lower', 'Is Lower Than'),
        ('greater', 'Is Greater Than'),
        ('between', 'Is Between'),
    ], string='Amount',
        help='The reconciliation model will only be applied when the amount being lower than, greater than or between specified amount(s).')
    match_amount_min = fields.Float(string='Amount Min Parameter')
    match_amount_max = fields.Float(string='Amount Max Parameter')
    match_label = fields.Selection(selection=[
        ('contains', 'Contains'),
        ('not_contains', 'Not Contains'),
        ('match_regex', 'Match Regex'),
    ], string='Label', help='''The reconciliation model will only be applied when the label:
        * Contains: The proposition label must contains this string (case insensitive).
        * Not Contains: Negation of "Contains".
        * Match Regex: Define your own regular expression.''')
    match_label_param = fields.Char(string='Label Parameter')
    match_note = fields.Selection(selection=[
        ('contains', 'Contains'),
        ('not_contains', 'Not Contains'),
        ('match_regex', 'Match Regex'),
    ], string='Note', help='''The reconciliation model will only be applied when the note:
        * Contains: The proposition note must contains this string (case insensitive).
        * Not Contains: Negation of "Contains".
        * Match Regex: Define your own regular expression.''')
    match_note_param = fields.Char(string='Note Parameter')
    match_transaction_type = fields.Selection(selection=[
        ('contains', 'Contains'),
        ('not_contains', 'Not Contains'),
        ('match_regex', 'Match Regex'),
    ], string='Transaction Type', help='''The reconciliation model will only be applied when the transaction type:
        * Contains: The proposition transaction type must contains this string (case insensitive).
        * Not Contains: Negation of "Contains".
        * Match Regex: Define your own regular expression.''')
    match_transaction_type_param = fields.Char(string='Transaction Type Parameter')
    match_same_currency = fields.Boolean(string='Same Currency Matching', default=True,
        help='Restrict to propositions having the same currency as the statement line.')
    match_total_amount = fields.Boolean(string='Amount Matching', default=True,
        help='The sum of total residual amount propositions matches the statement line amount.')
    match_total_amount_param = fields.Float(string='Amount Matching %', default=100,
        help='The sum of total residual amount propositions matches the statement line amount under this percentage.')
    match_partner = fields.Boolean(string='Partner Is Set',
        help='The reconciliation model will only be applied when a customer/vendor is set.')
    match_partner_ids = fields.Many2many('res.partner', string='Restrict Partners to',
        help='The reconciliation model will only be applied to the selected customers/vendors.')
    match_partner_category_ids = fields.Many2many('res.partner.category', string='Restrict Partner Categories to',
        help='The reconciliation model will only be applied to the selected customer/vendor categories.')

    # First part fields.
    account_id = fields.Many2one('account.account.template', string='Account', ondelete='cascade', domain=[('deprecated', '=', False)])
    label = fields.Char(string='Journal Item Label')
    amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of balance'),
        ('regex', 'From label'),
        ], required=True, default='percentage')
    amount = fields.Float(string='Write-off Amount', digits=0, required=True, default=100.0, help="Fixed amount will count as a debit if it is negative, as a credit if it is positive.")
    amount_from_label_regex = fields.Char(string="Amount from Label (regex)", default=r"([\d\.,]+)")
    decimal_separator = fields.Char(help="Every character that is nor a digit nor this separator will be removed from the matching string")
    force_tax_included = fields.Boolean(string='Tax Included in Price',
        help='Force the tax to be managed as a price included tax.')
    # Second part fields.
    has_second_line = fields.Boolean(string='Add a second line', default=False)
    tax_ids = fields.Many2many('account.tax.template', string='Taxes', ondelete='restrict')
    second_account_id = fields.Many2one('account.account.template', string='Second Account', ondelete='cascade', domain=[('deprecated', '=', False)])
    second_label = fields.Char(string='Second Journal Item Label')
    second_amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of amount'),
        ('regex', 'From label'),
        ], string="Second Amount type",required=True, default='percentage')
    second_amount = fields.Float(string='Second Write-off Amount', digits=0, required=True, default=100.0, help="Fixed amount will count as a debit if it is negative, as a credit if it is positive.")
    second_amount_from_label_regex = fields.Char(string="Second Amount from Label (regex)", default=r"([\d\.,]+)")
    force_second_tax_included = fields.Boolean(string='Second Tax Included in Price',
        help='Force the second tax to be managed as a price included tax.')
    second_tax_ids = fields.Many2many('account.tax.template', relation='account_reconcile_model_tmpl_account_tax_bis_rel', string='Second Taxes', ondelete='restrict')
