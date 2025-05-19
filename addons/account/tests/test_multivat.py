
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.models.chart_template import AccountChartTemplate
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


def _get_chart_template_mapping(self, get_all=False):
    return {
        'local': {
            'name': 'local',
            'country_id': self.env.ref("base.be").id,
            'country_code': 'be',
            'modules': ['account'],
            'parent': None,
            'installed': True,
        },
        'foreign': {
            'name': 'foreign',
            'country_id': self.env.ref("base.fr").id,
            'country_code': 'fr',
            'modules': ['account'],
            'parent': None,
            'installed': True,
        },
    }


def data_method_provider(chart_template_name, country_code):
    country = f"base.{country_code}"
    # this is used to simulated differences between xml_ids
    external_id_prefix = '' if chart_template_name == 'local' else f"{chart_template_name}_"

    def test_data_getter(self, template_code):
        return {
            'template_data': {
                'code_digits': 6,
                'currency_id': 'base.EUR',
                'property_account_income_categ_id': f'{external_id_prefix}test_account_income_template',
                'property_account_expense_categ_id': f'{external_id_prefix}test_account_expense_template',
            },
            'res.company': {
                self.env.company.id: {
                    'bank_account_code_prefix': '1000',
                    'cash_account_code_prefix': '2000',
                    'transfer_account_code_prefix': '3000',
                },
            },
            'account.account': {
                f'{external_id_prefix}test_account_tax_recoverable_template': {
                    'name': f'{external_id_prefix}tax recoverable',
                    'code': '411000',
                    'account_type': 'asset_current',
                },
                f'{external_id_prefix}test_account_tax_receivable_template': {
                    'name': f'{external_id_prefix}tax recoverable',
                    'code': '411200',
                    'account_type': 'asset_current',
                },
                f'{external_id_prefix}test_account_advance_payment_tax_template': {
                    'name': f'{external_id_prefix}advance tax payment',
                    'code': '411900',
                    'account_type': 'asset_current',
                },
                f'{external_id_prefix}test_account_tax_payable_template': {
                    'name': f'{external_id_prefix}tax recoverable',
                    'code': '451200',
                    'account_type': 'liability_current',
                },
                f'{external_id_prefix}test_account_cash_basis_transition_account_id': {
                    'name': f'{external_id_prefix}cash basis transition account',
                    'code': '451500',
                    'account_type': 'liability_current',
                },
                f'{external_id_prefix}test_account_income_template': {
                    'name': f'{external_id_prefix}income',
                    'code': '600000',
                    'account_type': 'income',
                },
                f'{external_id_prefix}test_account_expense_template': {
                    'name': f'{external_id_prefix}expense',
                    'code': '700000',
                    'account_type': 'expense',
                },
            },
            'account.journal': self._get_account_journal(template_code),
            'account.tax.group': {
                'tax_group_taxes': {
                    'name': f"{external_id_prefix}Taxes",
                    'sequence': 0,
                    'country_id': country,
                    'tax_payable_account_id': f'{external_id_prefix}test_account_tax_payable_template',
                    'tax_receivable_account_id': f'{external_id_prefix}test_account_tax_receivable_template',
                    'advance_tax_payment_account_id': f'{external_id_prefix}test_account_advance_payment_tax_template',
                },
            },
            'account.tax': {
                **{
                    xmlid: _tax_vals(name, amount, external_id_prefix)
                    for name, xmlid, amount in (
                        ('Tax 1', 'test_tax_1_template', 15),
                        ('Tax 2', 'test_tax_2_template', 0),
                    )
                },
                'test_composite_tax_template': {
                    'name': 'Tax Grouped',
                    'amount_type': 'group',
                    'type_tax_use': 'purchase',
                    'tax_group_id': 'tax_group_taxes',
                    'children_tax_ids': 'test_tax_1_template,test_tax_2_template',
                }
            },
        }
    return test_data_getter


def _tax_vals(name, amount, external_id_prefix, cash_basis=False, account_on_repartition=True):
    return {
        'name': name,
        'amount': amount,
        'type_tax_use': 'purchase',
        'tax_group_id': 'tax_group_taxes',
        'cash_basis_transition_account_id': f'{external_id_prefix}test_account_cash_basis_transition_account_id' if cash_basis else False,
        'tax_exigibility': 'on_payment' if cash_basis else 'on_invoice',
        'repartition_line_ids': [
            Command.create({'document_type': 'invoice', 'factor_percent': 100, 'repartition_type': 'base'}),
            Command.create({'document_type': 'invoice', 'factor_percent': 100, 'repartition_type': 'tax',
                           'account_id': f'{external_id_prefix}test_account_tax_recoverable_template' if account_on_repartition else False}),
            Command.create({'document_type': 'refund', 'factor_percent': 100, 'repartition_type': 'base'}),
            Command.create({'document_type': 'refund', 'factor_percent': 100, 'repartition_type': 'tax',
                           'account_id': f'{external_id_prefix}test_account_tax_recoverable_template' if account_on_repartition else False}),
        ]
    }


@tagged('post_install', '-at_install')
@patch.object(AccountChartTemplate, '_get_chart_template_mapping', _get_chart_template_mapping)
class TestMultiVAT(AccountTestInvoicingCommon):

    @classmethod
    def _use_chart_template(cls, company, chart_template_ref=None):
        test_get_data = data_method_provider("local", "be")
        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=test_get_data, autospec=True):
            cls.env['account.chart.template'].try_loading('local', company=company, install_demo=False)

    @classmethod
    @AccountTestInvoicingCommon.setup_country('be')
    @patch.object(AccountChartTemplate, '_get_chart_template_mapping', _get_chart_template_mapping)
    def setUpClass(cls):
        """
            Setups a company with a custom chart template, containing a tax and a fiscal position.
            We need to add xml_ids to the templates because they are loaded from their xml_ids
        """
        # Avoid creating data from AccountTestInvoicingCommon setUpClass
        # just use the override of the functions it provides
        super(AccountTestInvoicingCommon, cls).setUpClass()

        foreign_country = cls.env.ref("base.fr")
        cls.foreign_vat_fpos = cls.env["account.fiscal.position"].create({
            "name": "FR foreign VAT",
            "auto_apply": True,
            "country_id": foreign_country.id,
            "foreign_vat": "FR23334175221",
        })

        test_get_data = data_method_provider("foreign", "fr")
        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=test_get_data, autospec=True):
            cls.foreign_vat_fpos.action_create_foreign_taxes()

    def test_tax_and_tax_group_should_be_reachable_using_standard_api(self):
        # Ensure local and foreign tax is reachable using the custom ref api
        for xml_id in (
                # tax group
                'tax_group_taxes',
                'foreign_tax_group_taxes',
                # tax
                'test_tax_1_template',
                'test_tax_2_template',
                'test_composite_tax_template',
                'foreign_test_tax_1_template',
                'foreign_test_tax_2_template',
                'foreign_test_composite_tax_template'
        ):
            with self.subTest(xml_id=xml_id):
                record = self.env["account.chart.template"].ref(xml_id, raise_if_not_found=False)
                self.assertTrue(record, "We should be able to retrieve the record")

    def test_tax_group_data(self):
        # Ensure the correct country is set on tax group
        for xml_id, country_code in (('tax_group_taxes', 'BE'), ('foreign_tax_group_taxes', 'FR')):
            tax_group = self.env["account.chart.template"].ref(xml_id)
            with self.subTest(xml_id=xml_id, country_code=country_code):
                self.assertEqual(tax_group.country_id.code, country_code)

        local_tax_group = self.env["account.chart.template"].ref('tax_group_taxes')
        foreign_tax_group = self.env["account.chart.template"].ref('foreign_tax_group_taxes')
        for field in ('tax_payable_account_id', 'tax_receivable_account_id', 'advance_tax_payment_account_id'):
            with self.subTest(field=field):
                self.assertTrue(foreign_tax_group[field], "This account should have been set")
                self.assertNotEqual(foreign_tax_group[field], local_tax_group[field],
                                    "A copy of the local tax group account should have been created and set")

    def test_tax_data_should_be_consistent(self):
        # Ensure the correct country is set
        for xml_id, country_code in (
                # tax
                ('test_tax_1_template', 'BE'),
                ('test_tax_2_template', 'BE'),
                ('foreign_test_tax_1_template', 'FR'),
                ('foreign_test_tax_2_template', 'FR'),
        ):
            model = self.env["account.chart.template"].ref(xml_id)
            with self.subTest(xml_id=xml_id, country_code=country_code):
                self.assertEqual(model.country_id.code, country_code)

        tax = self.env["account.chart.template"].ref('foreign_test_tax_1_template')
        self.assertEqual(tax.country_id.code, 'FR')
        _base_line, tax_line = tax.invoice_repartition_line_ids
        self.assertEqual(tax_line.account_id.code, '411001',
                         "The foreign tax account should be a new account with a code close to the local tax account code")

        tax = self.env["account.chart.template"].ref('foreign_test_tax_2_template')
        self.assertEqual(tax.country_id.code, 'FR')
        _base_line, tax_line = tax.invoice_repartition_line_ids
        self.assertEqual(tax_line.account_id.code, '411001',
                         "The previously created tax account should be reused for similar tax")

    def test_children_taxes(self):
        # Ensure that group-type taxes are correctly linked to their children
        composite_taxes = ['test_composite_tax_template', 'foreign_test_composite_tax_template']
        children_taxes = {
            'test_composite_tax_template': ['test_tax_1_template', 'test_tax_2_template'],
            'foreign_test_composite_tax_template': ['foreign_test_tax_1_template', 'foreign_test_tax_2_template'],
        }
        for xml_id in composite_taxes:
            with self.subTest(xml_id=xml_id):
                record = self.env["account.chart.template"].ref(xml_id, raise_if_not_found=False)
                for i, child in enumerate(record.children_tax_ids):
                    child_tax = self.env["account.chart.template"].ref(children_taxes[xml_id][i], raise_if_not_found=False)
                    self.assertEqual(child.id, child_tax.id)

    def test_multivat_cash_basis(self):
        def wrap_data_getter_for_caba(data_getter):
            def caba_data_getter(self, template_code):
                rslt = data_getter(self, template_code)

                rslt['account.tax']['es.caba_0_tax'] = _tax_vals("Dudu 0", 0, 'es', cash_basis=True, account_on_repartition=False)
                rslt['account.tax']['es.caba_42_tax'] = _tax_vals("Dudu 42", 42, 'es', cash_basis=True)

                return rslt

            return caba_data_getter

        foreign_country = self.env.ref("base.es")
        foreign_vat_fpos = self.env["account.fiscal.position"].create({
            "name": "ES foreign VAT",
            "auto_apply": True,
            "country_id": foreign_country.id,
            "foreign_vat": "ESA12345674",
        })

        test_get_data = wrap_data_getter_for_caba(data_method_provider("foreign", "es"))
        with patch.object(AccountChartTemplate, '_get_chart_template_data', side_effect=test_get_data, autospec=True):
            foreign_vat_fpos.action_create_foreign_taxes()

        created_taxes = self.env.ref('local_es.caba_0_tax') + self.env.ref('local_es.caba_42_tax')
        for tax in created_taxes:
            self.assertEqual(tax.tax_exigibility, 'on_payment')
            self.assertEqual(tax.cash_basis_transition_account_id.code, '411005')

        self.assertTrue(self.env.company.tax_exigibility, "Creating foreign cash basis taxes should enable the cash basis setting on the company.")
