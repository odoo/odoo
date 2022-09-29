# -*- coding: utf-8 -*-
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class AccountingTestTemplConsistency(TransactionCase):
    '''Test the templates consistency between some objects like account.account when account.account.template.
    '''

    def get_model_fields(self, model, extra_domain=None):
        # Retrieve fields to compare
        domain = [
            ('model', '=', model),
            ('state', '=', 'base'),
            ('related', '=', False),
            ('compute', '=', False),
            ('store', '=', True),
        ]
        if extra_domain:
            domain += extra_domain
        return self.env['ir.model.fields'].search(domain)

    def check_fields_consistency(self, model_from, model_to, exceptions=None):
        '''Check the consistency of fields from one model to another by comparing if all fields
        in the model_from are present in the model_to.
        :param model_from: The model to compare.
        :param model_to: The compared model.
        :param exceptions: Not copied model's fields.
        '''
        extra_domain = [('name', 'not in', exceptions)] if exceptions else []
        from_fields = self.get_model_fields(model_from, extra_domain=extra_domain).filtered_domain([('modules', '=', 'account')])

        to_fields_set = set([f.name for f in self.get_model_fields(model_to)])
        for field in from_fields:
            assert field.name in to_fields_set,\
                'Missing field "%s" from "%s" in model "%s".' % (field.name, model_from, model_to)

    def test_account_account_fields(self):
        '''Test fields consistency for ('account.account', 'account.account.template')
        '''
        self.check_fields_consistency(
            'account.account.template', 'account.account', exceptions=['chart_template_id', 'nocreate'])
        self.check_fields_consistency(
            'account.account', 'account.account.template', exceptions=['company_id', 'deprecated', 'opening_debit', 'opening_credit', 'allowed_journal_ids', 'group_id', 'root_id', 'is_off_balance', 'non_trade', 'include_initial_balance', 'internal_group'])

    def test_account_tax_fields(self):
        '''Test fields consistency for ('account.tax', 'account.tax.template')
        '''
        self.check_fields_consistency('account.tax.template', 'account.tax', exceptions=['chart_template_id'])
        self.check_fields_consistency('account.tax', 'account.tax.template', exceptions=['company_id', 'country_id', 'real_amount'])
        self.check_fields_consistency('account.tax.repartition.line.template', 'account.tax.repartition.line', exceptions=['plus_report_expression_ids', 'minus_report_expression_ids'])
        self.check_fields_consistency('account.tax.repartition.line', 'account.tax.repartition.line.template', exceptions=['tag_ids', 'country_id', 'company_id', 'sequence'])

    def test_fiscal_position_fields(self):
        '''Test fields consistency for ('account.fiscal.position', 'account.fiscal.position.template')
        '''
        #main
        self.check_fields_consistency('account.fiscal.position.template', 'account.fiscal.position', exceptions=['chart_template_id'])
        self.check_fields_consistency('account.fiscal.position', 'account.fiscal.position.template', exceptions=['active', 'company_id', 'states_count', 'foreign_vat'])
        #taxes
        self.check_fields_consistency('account.fiscal.position.tax.template', 'account.fiscal.position.tax')
        self.check_fields_consistency('account.fiscal.position.tax', 'account.fiscal.position.tax.template')
        #accounts
        self.check_fields_consistency('account.fiscal.position.account.template', 'account.fiscal.position.account')
        self.check_fields_consistency('account.fiscal.position.account', 'account.fiscal.position.account.template')

    def test_reconcile_model_fields(self):
        '''Test fields consistency for ('account.reconcile.model', 'account.reconcile.model.template')
        '''
        self.check_fields_consistency('account.reconcile.model.template', 'account.reconcile.model', exceptions=['chart_template_id'])
        # exclude fields from inherited 'mail.thread'
        mail_thread_fields = [field.name for field in self.get_model_fields('mail.thread')]
        self.check_fields_consistency(
            'account.reconcile.model',
            'account.reconcile.model.template',
            exceptions=mail_thread_fields + ['active', 'company_id', 'past_months_limit', 'partner_mapping_line_ids'],
        )
        # lines
        self.check_fields_consistency('account.reconcile.model.line.template', 'account.reconcile.model.line', exceptions=['chart_template_id'])
        self.check_fields_consistency('account.reconcile.model.line', 'account.reconcile.model.line.template', exceptions=['company_id', 'journal_id', 'analytic_distribution', 'amount'])

    def test_account_group_fields(self):
        '''Test fields consistency for ('account.group', 'account.group.template')
        '''
        self.check_fields_consistency('account.group', 'account.group.template', exceptions=['company_id', 'parent_path'])
        self.check_fields_consistency('account.group.template', 'account.group', exceptions=['chart_template_id'])
