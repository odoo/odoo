# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError
from odoo import api, fields, models, Command, _, osv
from odoo import SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.addons.account.models.account_tax import TYPE_TAX_USE
from odoo.addons.account.models.account_account import ACCOUNT_CODE_REGEX
from odoo.tools import html_escape

import logging
import re

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

def update_taxes_from_templates(cr, chart_template_xmlid):
    def _create_tax_from_template(company, template, old_tax=None):
        """
        Create a new tax from template with template xmlid, if there was already an old tax with that xmlid we
        remove the xmlid from it but don't modify anything else.
        """
        def _remove_xml_id(xml_id):
            module, name = xml_id.split(".", 1)
            env['ir.model.data'].search([('module', '=', module), ('name', '=', name)]).unlink()

        def _avoid_name_conflict():
            conflict_tax = env['account.tax'].search([('name', '=', template.name), ('company_id', '=', company.id),
                                                      ('type_tax_use', '=', template.type_tax_use), ('tax_scope', '=', template.tax_scope)])
            if conflict_tax:
                conflict_tax.name = "[old] " + conflict_tax.name

        template_vals = template._get_tax_vals_complete(company)
        chart_template = env["account.chart.template"].with_context(default_company_id=company.id)
        if old_tax:
            xml_id = old_tax.get_external_id().get(old_tax.id)
            if xml_id:
                _remove_xml_id(xml_id)
        _avoid_name_conflict()
        chart_template.create_record_with_xmlid(company, template, "account.tax", template_vals)

    def _update_tax_from_template(template, tax):
        # -> update the tax : we only updates tax tags
        tax_rep_lines = tax.invoice_repartition_line_ids + tax.refund_repartition_line_ids
        template_rep_lines = template.invoice_repartition_line_ids + template.refund_repartition_line_ids
        for tax_line, template_line in zip(tax_rep_lines, template_rep_lines):
            tags_to_add = template_line._get_tags_to_add()
            tags_to_unlink = tax_line.tag_ids
            if tags_to_add != tags_to_unlink:
                tax_line.write({"tag_ids": [(6, 0, tags_to_add.ids)]})
                _cleanup_tags(tags_to_unlink)

    def _get_template_to_real_xmlid_mapping(company, model):
        """
        This function uses ir_model_data to return a mapping between the templates and the data, using their xmlid
        :returns: {
            account.tax.template.id: account.tax.id
            }
        """
        env['ir.model.data'].flush_model()
        env.cr.execute(
            """
            SELECT template.res_id AS template_res_id,
                   data.res_id AS data_res_id
            FROM ir_model_data data
            JOIN ir_model_data template
            ON template.name = substr(data.name, strpos(data.name, '_') + 1)
            WHERE data.model = %s
            AND data.name LIKE %s
            -- tax.name is of the form: {company_id}_{account.tax.template.name}
            """,
            [model, r"%s\_%%" % company.id],
        )
        tuples = env.cr.fetchall()
        return dict(tuples)

    def _is_tax_and_template_same(template, tax):
        """
        This function compares account.tax and account.tax.template repartition lines.
        A tax is considered the same as the template if they have the same:
            - amount_type
            - amount
            - repartition lines percentages in the same order
        """
        tax_rep_lines = tax.invoice_repartition_line_ids + tax.refund_repartition_line_ids
        template_rep_lines = template.invoice_repartition_line_ids + template.refund_repartition_line_ids
        return (
                tax.amount_type == template.amount_type
                and tax.amount == template.amount
                and len(tax_rep_lines) == len(template_rep_lines)
                and all(
                    rep_line_tax.factor_percent == rep_line_template.factor_percent
                    for rep_line_tax, rep_line_template in zip(tax_rep_lines, template_rep_lines)
                )
        )

    def _cleanup_tags(tags):
        """
        Checks if the tags are still used in taxes or move lines. If not we delete it.
        """
        for tag in tags:
            tax_using_tag = env['account.tax.repartition.line'].sudo().search([('tag_ids', 'in', tag.id)], limit=1)
            aml_using_tag = env['account.move.line'].sudo().search([('tax_tag_ids', 'in', tag.id)], limit=1)
            report_expr_using_tag = tag._get_related_tax_report_expressions()
            if not (aml_using_tag or tax_using_tag or report_expr_using_tag):
                tag.unlink()

    def _update_fiscal_positions_from_templates(company, chart_template_id, new_taxes_template):
        chart_template = env["account.chart.template"].browse(chart_template_id)
        positions = env['account.fiscal.position.template'].search([('chart_template_id', '=', chart_template_id)])
        tax_template_ref = _get_template_to_real_xmlid_mapping(company, 'account.tax')
        fp_template_ref = _get_template_to_real_xmlid_mapping(company, 'account.fiscal.position')

        tax_template_vals = []
        for position_template in positions:
            fp = env["account.fiscal.position"].browse(fp_template_ref.get(position_template.id))
            if not fp:
                continue
            for position_tax in position_template.tax_ids:
                src_id = tax_template_ref[position_tax.tax_src_id.id]
                dest_id = position_tax.tax_dest_id and tax_template_ref[position_tax.tax_dest_id.id] or False
                position_tax_template_exist = fp.tax_ids.filtered_domain([
                    ('tax_src_id', '=', src_id),
                    ('tax_dest_id', '=', dest_id)
                ])
                if not position_tax_template_exist and (position_tax.tax_src_id in new_taxes_template or position_tax.tax_dest_id in new_taxes_template):
                    tax_template_vals.append((position_tax, {
                        'tax_src_id': src_id,
                        'tax_dest_id': dest_id,
                        'position_id': fp.id,
                    }))
        chart_template._create_records_with_xmlid('account.fiscal.position.tax', tax_template_vals, company)

    def _notify_accountant_managers(taxes_to_check):
        accountant_manager_group = env.ref("account.group_account_manager")
        partner_managers_ids = accountant_manager_group.users.mapped('partner_id')
        odoobot = env.ref('base.partner_root')
        message_body = _(
            "Please check these taxes. They might be outdated. We did not update them. "
            "Indeed, they do not exactly match the taxes of the original version of the localization module.<br/>"
            "You might want to archive or adapt them.<br/><ul>"
        )
        for account_tax in taxes_to_check:
            message_body += f"<li>{html_escape(account_tax.name)}</li>"
        message_body += "</ul>"
        env['mail.thread'].message_notify(
            subject=_('Your taxes have been updated !'),
            author_id=odoobot.id,
            body=message_body,
            partner_ids=[partner.id for partner in partner_managers_ids],
        )

    env = api.Environment(cr, SUPERUSER_ID, {})
    chart_template_id = env.ref(chart_template_xmlid).id
    companies = env['res.company'].search([('chart_template_id', 'child_of', chart_template_id)])
    outdated_taxes = []
    new_taxes_template = []
    for company in companies:
        template_to_tax = _get_template_to_real_xmlid_mapping(company, 'account.tax')
        templates = env['account.tax.template'].with_context(active_test=False).search([("chart_template_id", "=", chart_template_id)])
        for template in templates:
            tax = env["account.tax"].browse(template_to_tax.get(template.id))
            if not tax or not _is_tax_and_template_same(template, tax):
                _create_tax_from_template(company, template, old_tax=tax)
                if tax:
                    outdated_taxes.append(tax)
                else:
                    new_taxes_template.append(template)
            else:
                _update_tax_from_template(template, tax)
        _update_fiscal_positions_from_templates(company, chart_template_id, new_taxes_template)
    if outdated_taxes:
        _notify_accountant_managers(outdated_taxes)

#  ---------------------------------------------------------------
#   Account Templates: Account, Tax, Tax Code and chart. + Wizard
#  ---------------------------------------------------------------


class AccountGroupTemplate(models.Model):
    _name = "account.group.template"
    _description = 'Template for Account Groups'
    _order = 'code_prefix_start'

    parent_id = fields.Many2one('account.group.template', ondelete='cascade')
    name = fields.Char(required=True)
    code_prefix_start = fields.Char()
    code_prefix_end = fields.Char()
    chart_template_id = fields.Many2one('account.chart.template', string='Chart Template', required=True)


class AccountAccountTemplate(models.Model):
    _name = "account.account.template"
    _inherit = ['mail.thread']
    _description = 'Templates for Accounts'
    _order = "code"

    name = fields.Char(required=True)
    currency_id = fields.Many2one('res.currency', string='Account Currency', help="Forces all moves for this account to have this secondary currency.")
    code = fields.Char(size=64, required=True)
    account_type = fields.Selection(
        selection=[
            ("asset_receivable", "Receivable"),
            ("asset_cash", "Bank and Cash"),
            ("asset_current", "Current Assets"),
            ("asset_non_current", "Non-current Assets"),
            ("asset_prepayments", "Prepayments"),
            ("asset_fixed", "Fixed Assets"),
            ("liability_payable", "Payable"),
            ("liability_credit_card", "Credit Card"),
            ("liability_current", "Current Liabilities"),
            ("liability_non_current", "Non-current Liabilities"),
            ("equity", "Equity"),
            ("equity_unaffected", "Current Year Earnings"),
            ("income", "Income"),
            ("income_other", "Other Income"),
            ("expense", "Expenses"),
            ("expense_depreciation", "Depreciation"),
            ("expense_direct_cost", "Cost of Revenue"),
            ("off_balance", "Off-Balance Sheet"),
        ],
        string="Type",
        help="These types are defined according to your country. The type contains more information "\
        "about the account and its specificities."
    )
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

    @api.depends('name', 'code')
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.code:
                name = record.code + ' ' + name
            res.append((record.id, name))
        return res

    @api.constrains('code')
    def _check_account_code(self):
        for account in self:
            if not re.match(ACCOUNT_CODE_REGEX, account.code):
                raise ValidationError(_(
                    "The account code can only contain alphanumeric characters and dots."
                ))


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
    use_storno_accounting = fields.Boolean(string="Use Storno accounting", default=False)
    account_ids = fields.One2many('account.account.template', 'chart_template_id', string='Associated Account Templates')
    tax_template_ids = fields.One2many('account.tax.template', 'chart_template_id', string='Tax Template List',
        help='List of all the taxes that have to be installed by the wizard')
    bank_account_code_prefix = fields.Char(string='Prefix of the bank accounts', required=True)
    cash_account_code_prefix = fields.Char(string='Prefix of the main cash accounts', required=True)
    transfer_account_code_prefix = fields.Char(string='Prefix of the main transfer accounts', required=True)
    income_currency_exchange_account_id = fields.Many2one('account.account.template',
        string="Gain Exchange Rate Account", domain=[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card')), ('deprecated', '=', False)])
    expense_currency_exchange_account_id = fields.Many2one('account.account.template',
        string="Loss Exchange Rate Account", domain=[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card')), ('deprecated', '=', False)])
    country_id = fields.Many2one(string="Country", comodel_name='res.country', help="The country this chart of accounts belongs to. None if it's generic.")

    account_journal_suspense_account_id = fields.Many2one('account.account.template', string='Journal Suspense Account')
    account_journal_payment_debit_account_id = fields.Many2one('account.account.template', string='Journal Outstanding Receipts Account')
    account_journal_payment_credit_account_id = fields.Many2one('account.account.template', string='Journal Outstanding Payments Account')

    default_cash_difference_income_account_id = fields.Many2one('account.account.template', string="Cash Difference Income Account")
    default_cash_difference_expense_account_id = fields.Many2one('account.account.template', string="Cash Difference Expense Account")
    default_pos_receivable_account_id = fields.Many2one('account.account.template', string="PoS receivable account")

    account_journal_early_pay_discount_loss_account_id = fields.Many2one(comodel_name='account.account.template', string='Cash Discount Write-Off Loss Account', )
    account_journal_early_pay_discount_gain_account_id = fields.Many2one(comodel_name='account.account.template', string='Cash Discount Write-Off Gain Account', )

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
    property_cash_basis_base_account_id = fields.Many2one(
        comodel_name='account.account.template',
        domain=[('deprecated', '=', False)],
        string="Base Tax Received Account",
        help="Account that will be set on lines created in cash basis journal entry and used to keep track of the "
             "tax base amount.")

    @api.model
    def _prepare_transfer_account_template(self, prefix=None):
        ''' Prepare values to create the transfer account that is an intermediary account used when moving money
        from a liquidity account to another.

        :return:    A dictionary of values to create a new account.account.
        '''
        digits = self.code_digits
        prefix = prefix or self.transfer_account_code_prefix or ''
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

        return {
            'name': _('Liquidity Transfer'),
            'code': new_code,
            'account_type': 'asset_current',
            'reconcile': True,
            'chart_template_id': self.id,
        }

    @api.model
    def _create_liquidity_journal_suspense_account(self, company, code_digits):
        return self.env['account.account'].create({
            'name': _("Bank Suspense Account"),
            'code': self.env['account.account']._search_new_account_code(company, code_digits, company.bank_account_code_prefix or ''),
            'account_type': 'asset_current',
            'company_id': company.id,
        })

    @api.model
    def _create_cash_discount_loss_account(self, company, code_digits):
        return self.env['account.account'].create({
            'name': _("Cash Discount Loss"),
            'code': 999998,
            'account_type': 'expense',
            'company_id': company.id,
        })

    @api.model
    def _create_cash_discount_gain_account(self, company, code_digits):
        return self.env['account.account'].create({
            'name': _("Cash Discount Gain"),
            'code': 999997,
            'account_type': 'income_other',
            'company_id': company.id,
        })

    def try_loading(self, company=False, install_demo=True):
        """ Installs this chart of accounts for the current company if not chart
        of accounts had been created for it yet.

        :param company (Model<res.company>): the company we try to load the chart template on.
            If not provided, it is retrieved from the context.
        :param install_demo (bool): whether or not we should load demo data right after loading the
            chart template.
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
                template.with_context(default_company_id=company.id)._load(company)
            # Install the demo data when the first localization is instanciated on the company
            if install_demo and self.env.ref('base.module_account').demo:
                self.with_context(
                    default_company_id=company.id,
                    allowed_company_ids=[company.id],
                )._create_demo_data()

    def _create_demo_data(self):
        try:
            with self.env.cr.savepoint():
                demo_data = self._get_demo_data()
                for model, data in demo_data:
                    created = self.env[model]._load_records([{
                        'xml_id': "account.%s" % xml_id if '.' not in xml_id else xml_id,
                        'values': record,
                        'noupdate': True,
                    } for xml_id, record in data.items()])
                    self._post_create_demo_data(created)
        except Exception:
            # Do not rollback installation of CoA if demo data failed
            _logger.exception('Error while loading accounting demo data')

    def _load(self, company):
        """ Installs this chart of accounts on the current company, replacing
        the existing one if it had already one defined. If some accounting entries
        had already been made, this function fails instead, triggering a UserError.

        Also, note that this function can only be run by someone with administration
        rights.
        """
        self.ensure_one()
        # do not use `request.env` here, it can cause deadlocks
        # Ensure everything is translated to the company's language, not the user's one.
        self = self.with_context(lang=company.partner_id.lang).with_company(company)
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
            self.env['ir.property'].sudo().search(
                [('value_reference', 'in', prop_values)]
            ).unlink()

            # delete account, journal, tax, fiscal position and reconciliation model
            models_to_delete = ['account.reconcile.model', 'account.fiscal.position', 'account.move.line', 'account.move', 'account.journal', 'account.tax', 'account.group']
            for model in models_to_delete:
                res = self.env[model].sudo().search([('company_id', '=', company.id)])
                if len(res):
                    res.with_context(force_delete=True).unlink()
            existing_accounts.unlink()

        company.write({'currency_id': self.currency_id.id,
                       'anglo_saxon_accounting': self.use_anglo_saxon,
                       'account_storno': self.use_storno_accounting,
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

        # Set the fiscal country before generating taxes in case the company does not have a country_id set yet
        if self.country_id:
            # If this CoA is made for only one country, set it as the fiscal country of the company.
            company.account_fiscal_country_id = self.country_id
        elif not company.account_fiscal_country_id:
            company.account_fiscal_country_id = self.env.ref('base.us')

        # Install all the templates objects and generate the real objects
        acc_template_ref, taxes_ref = self._install_template(company, code_digits=self.code_digits)

        # Set default cash discount write-off accounts
        if not company.account_journal_early_pay_discount_loss_account_id:
            company.account_journal_early_pay_discount_loss_account_id = self._create_cash_discount_loss_account(
                company, self.code_digits)
        if not company.account_journal_early_pay_discount_gain_account_id:
            company.account_journal_early_pay_discount_gain_account_id = self._create_cash_discount_gain_account(
                company, self.code_digits)

        # Set default cash difference account on company
        if not company.account_journal_suspense_account_id:
            company.account_journal_suspense_account_id = self._create_liquidity_journal_suspense_account(company, self.code_digits)

        if not company.account_journal_payment_debit_account_id:
            company.account_journal_payment_debit_account_id = self.env['account.account'].create({
                'name': _("Outstanding Receipts"),
                'code': self.env['account.account']._search_new_account_code(company, self.code_digits, company.bank_account_code_prefix or ''),
                'reconcile': True,
                'account_type': 'asset_current',
                'company_id': company.id,
            })

        if not company.account_journal_payment_credit_account_id:
            company.account_journal_payment_credit_account_id = self.env['account.account'].create({
                'name': _("Outstanding Payments"),
                'code': self.env['account.account']._search_new_account_code(company, self.code_digits, company.bank_account_code_prefix or ''),
                'reconcile': True,
                'account_type': 'asset_current',
                'company_id': company.id,
            })

        if not company.default_cash_difference_expense_account_id:
            company.default_cash_difference_expense_account_id = self.env['account.account'].create({
                'name': _('Cash Difference Loss'),
                'code': self.env['account.account']._search_new_account_code(company, self.code_digits, '999'),
                'account_type': 'expense',
                'tag_ids': [(6, 0, self.env.ref('account.account_tag_investing').ids)],
                'company_id': company.id,
            })

        if not company.default_cash_difference_income_account_id:
            company.default_cash_difference_income_account_id = self.env['account.account'].create({
                'name': _('Cash Difference Gain'),
                'code': self.env['account.account']._search_new_account_code(company, self.code_digits, '999'),
                'account_type': 'income',
                'tag_ids': [(6, 0, self.env.ref('account.account_tag_investing').ids)],
                'company_id': company.id,
            })

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
        model_to_check = ['account.payment', 'account.bank.statement.line']
        for model in model_to_check:
            if self.env[model].sudo().search([('company_id', '=', company_id.id)], order="id DESC", limit=1):
                return True
        if self.env['account.move'].sudo().search([('company_id', '=', company_id.id), ('state', '!=', 'draft')], order="id DESC", limit=1):
            return True
        return False

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
                'sequence': 10,
            })

        return bank_journals

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
                default_account = acc_template_ref.get(self.property_account_income_categ_id).id
            elif journal['type'] == 'purchase':
                default_account = acc_template_ref.get(self.property_account_expense_categ_id).id

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
                'default_account_id': _get_default_account(journal),
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
            ('property_account_receivable_id', 'res.partner'),
            ('property_account_payable_id', 'res.partner'),
            ('property_account_expense_categ_id', 'product.category'),
            ('property_account_income_categ_id', 'product.category'),
            ('property_account_expense_id', 'product.template'),
            ('property_account_income_id', 'product.template'),
            ('property_tax_payable_account_id', 'account.tax.group'),
            ('property_tax_receivable_account_id', 'account.tax.group'),
            ('property_advance_tax_payment_account_id', 'account.tax.group'),
        ]
        for field, model in todo_list:
            account = self[field]
            value = acc_template_ref[account].id if account else False
            if value:
                PropertyObj._set_default(field, model, value, company=company)

        stock_properties = [
            'property_stock_account_input_categ_id',
            'property_stock_account_output_categ_id',
            'property_stock_valuation_account_id',
        ]
        for stock_property in stock_properties:
            account = getattr(self, stock_property)
            value = account and acc_template_ref[account].id or False
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

        # Generate account groups, from template
        self.generate_account_groups(company)

        # writing account values after creation of accounts
        for tax, value in generated_tax_res['account_dict']['account.tax'].items():
            if value['cash_basis_transition_account_id']:
                tax.cash_basis_transition_account_id = account_ref.get(value['cash_basis_transition_account_id'])

        for repartition_line, value in generated_tax_res['account_dict']['account.tax.repartition.line'].items():
            if value['account_id']:
                repartition_line.account_id = account_ref.get(value['account_id'])

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
            'default_cash_difference_income_account_id': self.default_cash_difference_income_account_id,
            'default_cash_difference_expense_account_id': self.default_cash_difference_expense_account_id,
            'account_journal_early_pay_discount_loss_account_id': self.account_journal_early_pay_discount_loss_account_id,
            'account_journal_early_pay_discount_gain_account_id': self.account_journal_early_pay_discount_gain_account_id,
            'account_journal_suspense_account_id': self.account_journal_suspense_account_id,
            'account_journal_payment_debit_account_id': self.account_journal_payment_debit_account_id,
            'account_journal_payment_credit_account_id': self.account_journal_payment_credit_account_id,
            'account_cash_basis_base_account_id': self.property_cash_basis_base_account_id,
            'account_default_pos_receivable_account_id': self.default_pos_receivable_account_id,
            'income_currency_exchange_account_id': self.income_currency_exchange_account_id,
            'expense_currency_exchange_account_id': self.expense_currency_exchange_account_id,
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
            tax_ids.append(tax_template_ref[tax].id)
        val = {
                'name': account_template.name,
                'currency_id': account_template.currency_id and account_template.currency_id.id or False,
                'code': code_acc,
                'account_type': account_template.account_type or False,
                'reconcile': account_template.reconcile,
                'note': account_template.note,
                'tax_ids': [(6, 0, tax_ids)],
                'company_id': company.id,
                'tag_ids': [(6, 0, [t.id for t in account_template.tag_ids])],
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
            acc_template_ref[template] = account
        return acc_template_ref

    def generate_account_groups(self, company):
        """ This method generates account groups from account groups templates.
        :param company: company to generate the account groups for
        """
        self.ensure_one()
        group_templates = self.env['account.group.template'].search([('chart_template_id', '=', self.id)])
        template_vals = []
        for group_template in group_templates:
            vals = {
                'name': group_template.name,
                'code_prefix_start': group_template.code_prefix_start,
                'code_prefix_end': group_template.code_prefix_end,
                'company_id': company.id,
            }
            template_vals.append((group_template, vals))
        groups = self._create_records_with_xmlid('account.group', template_vals, company)

    def _prepare_reconcile_model_vals(self, company, account_reconcile_model, acc_template_ref, tax_template_ref):
        """ This method generates a dictionary of all the values for the account.reconcile.model that will be created.
        """
        self.ensure_one()
        account_reconcile_model_lines = self.env['account.reconcile.model.line.template'].search([
            ('model_id', '=', account_reconcile_model.id)
        ])
        return {
            'name': account_reconcile_model.name,
            'sequence': account_reconcile_model.sequence,
            'company_id': company.id,
            'rule_type': account_reconcile_model.rule_type,
            'auto_reconcile': account_reconcile_model.auto_reconcile,
            'to_check': account_reconcile_model.to_check,
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
            'allow_payment_tolerance': account_reconcile_model.allow_payment_tolerance,
            'payment_tolerance_type': account_reconcile_model.payment_tolerance_type,
            'payment_tolerance_param': account_reconcile_model.payment_tolerance_param,
            'match_partner': account_reconcile_model.match_partner,
            'match_partner_ids': [(6, None, account_reconcile_model.match_partner_ids.ids)],
            'match_partner_category_ids': [(6, None, account_reconcile_model.match_partner_category_ids.ids)],
            'line_ids': [(0, 0, {
                'account_id': acc_template_ref[line.account_id].id,
                'label': line.label,
                'amount_type': line.amount_type,
                'force_tax_included': line.force_tax_included,
                'amount_string': line.amount_string,
                'tax_ids': [[4, tax_template_ref[tax].id, 0] for tax in line.tax_ids],
            }) for line in account_reconcile_model_lines],
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

        # Create default rules for the reconciliation widget matching invoices automatically.
        if not self.parent_id:
            self.env['account.reconcile.model'].sudo().create({
                "name": _('Invoices/Bills Perfect Match'),
                "sequence": '1',
                "rule_type": 'invoice_matching',
                "auto_reconcile": True,
                "match_nature": 'both',
                "match_same_currency": True,
                "allow_payment_tolerance": True,
                "payment_tolerance_type": 'percentage',
                "payment_tolerance_param": 0,
                "match_partner": True,
                "company_id": company.id,
            })

            self.env['account.reconcile.model'].sudo().create({
                "name": _('Invoices/Bills Partial Match if Underpaid'),
                "sequence": '2',
                "rule_type": 'invoice_matching',
                "auto_reconcile": False,
                "match_nature": 'both',
                "match_same_currency": True,
                "allow_payment_tolerance": False,
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
                    'tax_src_id': tax_template_ref[tax.tax_src_id].id,
                    'tax_dest_id': tax.tax_dest_id and tax_template_ref[tax.tax_dest_id].id or False,
                    'position_id': fp.id,
                }))
            for acc in position.account_ids:
                account_template_vals.append((acc, {
                    'account_src_id': acc_template_ref[acc.account_src_id].id,
                    'account_dest_id': acc_template_ref[acc.account_dest_id].id,
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
    type_tax_use = fields.Selection(TYPE_TAX_USE, string='Tax Type', required=True, default="sale",
        help="Determines where the tax is selectable. Note : 'None' means a tax can't be used by itself, however it can still be used in a group.")
    tax_scope = fields.Selection([('service', 'Service'), ('consu', 'Consumable')], help="Restrict the use of taxes to a type of product.")
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
        help="If set, taxes with a higher sequence than this one will be affected by it, provided they accept it.")
    is_base_affected = fields.Boolean(
        string="Base Affected by Previous Taxes",
        default=True,
        help="If set, taxes with a lower sequence might affect this one, provided they try to do it.")
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

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, type_tax_use, tax_scope, chart_template_id)', 'Tax names must be unique !'),
    ]

    @api.depends('name', 'description')
    def name_get(self):
        res = []
        for record in self:
            name = record.description and record.description or record.name
            res.append((record.id, name))
        return res

    @api.model
    def _try_instantiating_foreign_taxes(self, country, company):
        """ This function is called in multivat setup, when a company needs to submit a
        tax report in a foreign country.

        It searches for tax templates in the provided countries and instantiates the
        ones it find in the provided company.

        Tax accounts are not kept from the templates (this wouldn't make sense,
        as they don't belong to the same CoA as the one installed on the company).
        Instead, we search existing tax accounts for approximately equivalent accounts
        and use their prefix to create new accounts. Doing this gives a roughly correct suggestion
        that then needs to be reviewed by the user to ensure its consistency.
        It is intended as a shortcut to avoid hours of encoding, not as an out-of-the-box, always
        correct solution.
        """
        def create_foreign_tax_account(existing_account, additional_label):
            new_code = self.env['account.account']._search_new_account_code(existing_account.company_id, len(existing_account.code), existing_account.code[:-2])
            return self.env['account.account'].create({
                'name': f"{existing_account.name} - {additional_label}",
                'code': new_code,
                'account_type': existing_account.account_type,
                'company_id': existing_account.company_id.id,
            })

        def get_existing_tax_account(foreign_tax_rep_line, force_tax=None):
            company = foreign_tax_rep_line.company_id
            sign_comparator = '<' if foreign_tax_rep_line.factor_percent < 0 else '>'

            search_domain = [
                ('account_id', '!=', False),
                ('factor_percent', sign_comparator, 0),
                ('company_id', '=', company.id),
                '|',
                '&', ('invoice_tax_id.type_tax_use', '=', tax_rep_line.invoice_tax_id.type_tax_use),
                     ('invoice_tax_id.country_id', '=', company.account_fiscal_country_id.id),
                '&', ('refund_tax_id.type_tax_use', '=', tax_rep_line.refund_tax_id.type_tax_use),
                     ('refund_tax_id.country_id', '=', company.account_fiscal_country_id.id),
            ]

            if force_tax:
                search_domain += [
                    '|', ('invoice_tax_id', 'in', force_tax.ids),
                    ('refund_tax_id', 'in', force_tax.ids),
                ]

            return self.env['account.tax.repartition.line'].search(search_domain, limit=1).account_id


        taxes_in_country = self.env['account.tax'].search([
            ('country_id', '=', country.id),
            ('company_id', '=', company.id)
        ])

        if taxes_in_country:
            return

        templates_to_instantiate = self.env['account.tax.template'].with_context(active_test=False).search([('chart_template_id.country_id', '=', country.id)])
        default_company_taxes = company.account_sale_tax_id + company.account_purchase_tax_id
        rep_lines_accounts = templates_to_instantiate._generate_tax(company)['account_dict']

        new_accounts_map = {}

        # Handle tax repartition line accounts
        tax_rep_lines_accounts_dict = rep_lines_accounts['account.tax.repartition.line']
        for tax_rep_line, account_dict in tax_rep_lines_accounts_dict.items():
            account_template = account_dict['account_id']
            rep_account = new_accounts_map.get(account_template)

            if not rep_account:

                existing_account = get_existing_tax_account(tax_rep_line, force_tax=default_company_taxes)

                if not existing_account:
                    # If the default taxes were not enough to provide the account
                    # we need, search on all other taxes.
                    existing_account = get_existing_tax_account(tax_rep_line)

                if existing_account:
                    rep_account = create_foreign_tax_account(existing_account, _("Foreign tax account (%s)", country.code))
                    new_accounts_map[account_template] = rep_account

            tax_rep_line.account_id = rep_account

        # Handle cash basis taxes transtion account
        caba_transition_dict = rep_lines_accounts['account.tax']
        for tax, account_dict in caba_transition_dict.items():
            transition_account_template = account_dict['cash_basis_transition_account_id']

            if transition_account_template:
                transition_account = new_accounts_map.get(transition_account_template)

                if not transition_account:
                    rep_lines = tax.invoice_repartition_line_ids + tax.refund_repartition_line_ids
                    tax_accounts = rep_lines.account_id

                    if tax_accounts:
                        transition_account = create_foreign_tax_account(tax_accounts[0], _("Cash basis transition account"))

                tax.cash_basis_transition_account_id = transition_account

        # Setup tax closing accounts on foreign tax groups ; we don't want to use the domestic accounts
        groups = self.env['account.tax.group'].search([('country_id', '=', country.id)])
        group_property_fields = [
            'property_tax_payable_account_id',
            'property_tax_receivable_account_id',
            'property_advance_tax_payment_account_id'
        ]

        property_company = self.env['ir.property'].with_company(company)
        groups_company = groups.with_company(company)
        for property_field in group_property_fields:
            default_acc = property_company._get(property_field, 'account.tax.group')
            if default_acc:
                groups_company.write({
                    property_field: create_foreign_tax_account(default_acc, _("Foreign account (%s)", country.code))
                })

    def _get_tax_vals(self, company, tax_template_to_tax):
        """ This method generates a dictionary of all the values for the tax that will be created.
        """
        # Compute children tax ids
        children_ids = []
        for child_tax in self.children_tax_ids:
            if tax_template_to_tax.get(child_tax):
                children_ids.append(tax_template_to_tax[child_tax].id)
        self.ensure_one()
        val = {
            'name': self.name,
            'type_tax_use': self.type_tax_use,
            'tax_scope': self.tax_scope,
            'amount_type': self.amount_type,
            'active': self.active,
            'company_id': company.id,
            'sequence': self.sequence,
            'amount': self.amount,
            'description': self.description,
            'price_include': self.price_include,
            'include_base_amount': self.include_base_amount,
            'is_base_affected': self.is_base_affected,
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

    def _get_tax_vals_complete(self, company):
        """
        Returns a dict of values to be used to create the tax corresponding to the template, assuming the
        account.account objects were already created.
        It differs from function _get_tax_vals because here, we replace the references to account.template by their
        corresponding account.account ids ('cash_basis_transition_account_id' and 'account_id' in the invoice and
        refund repartition lines)
        (Used by upgrade/migrations/util/accounting)
        """
        vals = self._get_tax_vals(company, {})
        vals.pop("children_tax_ids", None)

        if self.cash_basis_transition_account_id.code:
            cash_basis_account_id = self.env['account.account'].search([
                ('code', '=like', self.cash_basis_transition_account_id.code + '%'),
                ('company_id', '=', company.id)
            ], limit=1)
            if cash_basis_account_id:
                vals.update({"cash_basis_transition_account_id": cash_basis_account_id.id})

        vals.update({
            "invoice_repartition_line_ids": self.invoice_repartition_line_ids._get_repartition_line_create_vals_complete(company),
            "refund_repartition_line_ids": self.refund_repartition_line_ids._get_repartition_line_create_vals_complete(company),
        })
        return vals

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
                if all(child in tax_template_to_tax for child in template.children_tax_ids):
                    vals = template._get_tax_vals(company, tax_template_to_tax)

                    if self.chart_template_id.country_id:
                        vals['country_id'] = self.chart_template_id.country_id.id
                    elif company.account_fiscal_country_id:
                        vals['country_id'] = company.account_fiscal_country_id.id
                    else:
                        # Will happen for generic CoAs such as syscohada (they are available for multiple countries, and don't have any country_id)
                        raise UserError(_("Please first define a fiscal country for company %s.", company.name))

                    tax_template_vals.append((template, vals))
                else:
                    # defer the creation of this tax to the next batch
                    templates_todo.append(template)
            taxes = ChartTemplate._create_records_with_xmlid('account.tax', tax_template_vals, company)

            # fill in tax_template_to_tax and todo_dict
            for tax, (template, vals) in zip(taxes, tax_template_vals):
                tax_template_to_tax[template] = tax
                # Since the accounts have not been created yet, we have to wait before filling these fields
                todo_dict['account.tax'][tax] = {
                    'cash_basis_transition_account_id': template.cash_basis_transition_account_id,
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
                        todo_dict['account.tax.repartition.line'][all_tax_rep_lines[i]] = {
                            'account_id': template_account,
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

    factor_percent = fields.Float(
        string="%",
        required=True,
        default=100,
        help="Factor to apply on the account move lines generated from this distribution line, in percents",
    )
    repartition_type = fields.Selection(string="Based On", selection=[('base', 'Base'), ('tax', 'of tax')], required=True, default='tax', help="Base on which the factor will be applied.")
    account_id = fields.Many2one(string="Account", comodel_name='account.account.template', help="Account on which to post the tax amount")
    invoice_tax_id = fields.Many2one(comodel_name='account.tax.template', help="The tax set to apply this distribution on invoices. Mutually exclusive with refund_tax_id")
    refund_tax_id = fields.Many2one(comodel_name='account.tax.template', help="The tax set to apply this distribution on refund invoices. Mutually exclusive with invoice_tax_id")
    tag_ids = fields.Many2many(string="Financial Tags", relation='account_tax_repartition_financial_tags', comodel_name='account.account.tag', copy=True, help="Additional tags that will be assigned by this repartition line for use in domains")
    use_in_tax_closing = fields.Boolean(string="Tax Closing Entry")


    # These last two fields are helpers used to ease the declaration of account.account.tag objects in XML.
    # They are directly linked to account.tax.report.expression objects, which create corresponding + and - tags
    # at creation. This way, we avoid declaring + and - separately every time.
    plus_report_expression_ids = fields.Many2many(string="Plus Tax Report Expressions", relation='account_tax_rep_template_plus', comodel_name='account.report.expression', copy=True, help="Tax report expressions whose '+' tag will be assigned to move lines by this repartition line")
    minus_report_expression_ids = fields.Many2many(string="Minus Report Expressions", relation='account_tax_rep_template_minus', comodel_name='account.report.expression', copy=True, help="Tax report expressions whose '-' tag will be assigned to move lines by this repartition line")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('use_in_tax_closing') is None:
                vals['use_in_tax_closing'] = False
                if vals.get('account_id'):
                    account_type = self.env['account.account.template'].browse(vals.get('account_id')).account_type
                    if account_type:
                        vals['use_in_tax_closing'] = not (account_type.startswith('income') or account_type.startswith('expense'))

        return super().create(vals_list)

    @api.constrains('invoice_tax_id', 'refund_tax_id')
    def validate_tax_template_link(self):
        for record in self:
            if record.invoice_tax_id and record.refund_tax_id:
                raise ValidationError(_("Tax distribution line templates should apply to either invoices or refunds, not both at the same time. invoice_tax_id and refund_tax_id should not be set together."))

    @api.constrains('plus_report_expression_ids', 'minus_report_expression_ids')
    def _validate_report_expressions(self):
        for record in self:
            all_engines = set((record.plus_report_expression_ids + record.minus_report_expression_ids).mapped('engine'))
            if all_engines and all_engines != {'tax_tags'}:
                raise ValidationError(_("Only 'tax_tags' expressions can be linked to a tax repartition line template."))

    def get_repartition_line_create_vals(self, company):
        rslt = [Command.clear()]
        for record in self:
            rslt.append(Command.create({
                'factor_percent': record.factor_percent,
                'repartition_type': record.repartition_type,
                'tag_ids': [Command.set(record._get_tags_to_add().ids)],
                'company_id': company.id,
                'use_in_tax_closing': record.use_in_tax_closing
            }))
        return rslt

    def _get_repartition_line_create_vals_complete(self, company):
        """
        This function returns a list of values to create the repartition lines of a tax based on
        one or several account.tax.repartition.line.template. It mimicks the function get_repartition_line_create_vals
        but adds the missing field account_id (account.account)

        Returns a list of (0,0, x) ORM commands to create the repartition lines starting with a (5,0,0)
        command to clear the repartition.
        """
        rslt = self.get_repartition_line_create_vals(company)
        for idx, template_line in zip(range(1, len(rslt)), self):  # ignore first ORM command ( (5, 0, 0) )
            account_id = False
            if template_line.account_id:
                # take the first account.account which code begins with the correct code
                account_id = self.env['account.account'].search([
                    ('code', '=like', template_line.account_id.code + '%'),
                    ('company_id', '=', company.id)
                ], limit=1).id
                if not account_id:
                    _logger.warning("The account with code '%s' was not found but is supposed to be linked to a tax",
                                    template_line.account_id.code)
            rslt[idx][2].update({
                "account_id": account_id,
            })
        return rslt

    def _get_tags_to_add(self):
        self.ensure_one()
        tags_to_add = self.tag_ids

        domains = []
        for sign, report_expressions in (('+', self.plus_report_expression_ids), ('-', self.minus_report_expression_ids)):
            for report_expression in report_expressions:
                country = report_expression.report_line_id.report_id.country_id
                domains.append(self.env['account.account.tag']._get_tax_tags_domain(report_expression.formula, country.id, sign=sign))

        if domains:
            tags_to_add |= self.env['account.account.tag'].with_context(active_test=False).search(osv.expression.OR(domains))

        return tags_to_add

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
        help="Apply only if delivery country matches.")
    country_group_id = fields.Many2one('res.country.group', string='Country Group',
        help="Apply only if delivery country matches the group.")
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
        ('writeoff_button', 'Button to generate counterpart entry'),
        ('writeoff_suggestion', 'Rule to suggest counterpart entry'),
        ('invoice_matching', 'Rule to match invoices/bills'),
    ], string='Type', default='writeoff_button', required=True)
    auto_reconcile = fields.Boolean(string='Auto-validate',
        help='Validate the statement line automatically (reconciliation based on your rule).')
    to_check = fields.Boolean(string='To Check', default=False, help='This matching rule is used when the user is not certain of all the information of the counterpart.')
    matching_order = fields.Selection(
        selection=[
            ('old_first', 'Oldest first'),
            ('new_first', 'Newest first'),
        ]
    )

    # ===== Conditions =====
    match_text_location_label = fields.Boolean(
        default=True,
        help="Search in the Statement's Label to find the Invoice/Payment's reference",
    )
    match_text_location_note = fields.Boolean(
        default=False,
        help="Search in the Statement's Note to find the Invoice/Payment's reference",
    )
    match_text_location_reference = fields.Boolean(
        default=False,
        help="Search in the Statement's Reference to find the Invoice/Payment's reference",
    )
    match_journal_ids = fields.Many2many('account.journal', string='Journals Availability',
        domain="[('type', 'in', ('bank', 'cash'))]",
        help='The reconciliation model will only be available from the selected journals.')
    match_nature = fields.Selection(selection=[
        ('amount_received', 'Amount Received'),
        ('amount_paid', 'Amount Paid'),
        ('both', 'Amount Paid/Received')
    ], string='Amount Type', required=True, default='both',
        help='''The reconciliation model will only be applied to the selected transaction type:
        * Amount Received: Only applied when receiving an amount.
        * Amount Paid: Only applied when paying an amount.
        * Amount Paid/Received: Applied in both cases.''')
    match_amount = fields.Selection(selection=[
        ('lower', 'Is Lower Than'),
        ('greater', 'Is Greater Than'),
        ('between', 'Is Between'),
    ], string='Amount Condition',
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
    match_same_currency = fields.Boolean(string='Same Currency', default=True,
        help='Restrict to propositions having the same currency as the statement line.')
    allow_payment_tolerance = fields.Boolean(
        string="Allow Payment Gap",
        default=True,
        help="Difference accepted in case of underpayment.",
    )
    payment_tolerance_param = fields.Float(
        string="Gap",
        default=0.0,
        help="The sum of total residual amount propositions matches the statement line amount under this amount/percentage.",
    )
    payment_tolerance_type = fields.Selection(
        selection=[('percentage', "in percentage"), ('fixed_amount', "in amount")],
        required=True,
        default='percentage',
        help="The sum of total residual amount propositions and the statement line amount allowed gap type.",
    )
    match_partner = fields.Boolean(string='Partner Is Set',
        help='The reconciliation model will only be applied when a customer/vendor is set.')
    match_partner_ids = fields.Many2many('res.partner', string='Restrict Partners to',
        help='The reconciliation model will only be applied to the selected customers/vendors.')
    match_partner_category_ids = fields.Many2many('res.partner.category', string='Restrict Partner Categories to',
        help='The reconciliation model will only be applied to the selected customer/vendor categories.')

    line_ids = fields.One2many('account.reconcile.model.line.template', 'model_id')
    decimal_separator = fields.Char(help="Every character that is nor a digit nor this separator will be removed from the matching string")


class AccountReconcileModelLineTemplate(models.Model):
    _name = "account.reconcile.model.line.template"
    _description = 'Reconcile Model Line Template'

    model_id = fields.Many2one('account.reconcile.model.template')
    sequence = fields.Integer(required=True, default=10)
    account_id = fields.Many2one('account.account.template', string='Account', ondelete='cascade', domain=[('deprecated', '=', False)])
    label = fields.Char(string='Journal Item Label')
    amount_type = fields.Selection([
        ('fixed', 'Fixed'),
        ('percentage', 'Percentage of balance'),
        ('regex', 'From label'),
    ], required=True, default='percentage')
    amount_string = fields.Char(string="Amount")
    force_tax_included = fields.Boolean(string='Tax Included in Price', help='Force the tax to be managed as a price included tax.')
    tax_ids = fields.Many2many('account.tax.template', string='Taxes', ondelete='restrict')
