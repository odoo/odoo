# -*- coding: utf-8 -*-
from odoo.tests.common import HttpCase


class AccountingTestTemplConsistency(HttpCase):
    '''Test the templates consistency between some objects like account.account when account.account.template.
    '''

    def check_fields_consistency(self, model_from, model_to, exceptions=[]):
        '''Check the consistency of fields from one model to another by comparing if all fields
        in the model_from are present in the model_to.
        :param model_from: The model to compare.
        :param model_to: The compared model.
        :param exceptions: Not copied model's fields.
        '''

        def get_fields(model, add_domain):
            # Retrieve fields to compare
            domain = [('model', '=', model), ('state', '=', 'base'), ('related', '=', False),
                      ('compute', '=', False), add_domain]
            return self.env['ir.model.fields'].search(domain)

        from_fields = get_fields(model_from, ('name', 'not in', exceptions))
        for field in from_fields:
            child_field = get_fields(model_to, ('name', '=', field.name))
            assert child_field.name is not False,\
                'Missing field "%s" from "%s" in model "%s".' % (field.name, model_from, model_to)

    def test_account_account_fields(self):
        '''Test fields consistency for ('account.account', 'account.account.template')
        '''
        self.check_fields_consistency(
            'account.account.template', 'account.account', ['chart_template_id', 'nocreate'])
        self.check_fields_consistency(
            'account.account', 'account.account.template', ['company_id', 'deprecated', 'last_time_entries_checked'])

    def test_account_tax_fields(self):
        '''Test fields consistency for ('account.tax', 'account.tax.template')
        '''
        self.check_fields_consistency(
            'account.tax.template', 'account.tax', ['chart_template_id'])
        self.check_fields_consistency(
            'account.tax', 'account.tax.template')
