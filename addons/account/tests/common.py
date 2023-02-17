# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.tests.common import TransactionCase, HttpCase, tagged, Form

import json
import time
import base64
from lxml import etree

from odoo.addons.product.tests.common import ProductCommon


class AccountTestInvoicingCommon(ProductCommon):

    @classmethod
    def setUpClass(cls, **kwargs):
        assert 'post_install' in cls.test_tags, 'This test requires a CoA to be installed, it should be tagged "post_install"'

        super().setUpClass()
        # TODO LAS: check if necessary
        cls.cr = cls.env.cr  # NOTE: LAS confusing and unnecessary variable, should not be in the BaseCommon

        cls.company_data = cls.collect_company_accounting_data(cls.env.company)

        # ==== Taxes ====
        cls.tax_sale_a = cls.company_data['default_tax_sale']
        cls.tax_sale_b = cls.company_data['default_tax_sale'] and cls.company_data['default_tax_sale'].copy()
        cls.tax_purchase_a = cls.company_data['default_tax_purchase']
        cls.tax_purchase_b = cls.company_data['default_tax_purchase'] and cls.company_data['default_tax_purchase'].copy()
        cls.tax_armageddon = cls.setup_armageddon_tax('complex_tax', cls.company_data)

        # ==== Products ====
        cls.product_a = cls._create_product(
            name='product_a',
            list_price=1000.0,
            standard_price=800.0,
            supplier_taxes_id=[(6, 0, cls.tax_purchase_a.ids)],
        )
        cls.product_b = cls._create_product(
            name='product_b',
            uom_id=cls.uom_dozen.id,
            lst_price=200.0,
            standard_price=160.0,
            property_account_income_id=cls.copy_account(cls.company_data['default_account_revenue']).id,
            property_account_expense_id=cls.copy_account(cls.company_data['default_account_expense']).id,
            taxes_id=[(6, 0, (cls.tax_sale_a + cls.tax_sale_b).ids)],
            supplier_taxes_id=[(6, 0, (cls.tax_purchase_a + cls.tax_purchase_b).ids)],
        )

        # ==== Fiscal positions ====
        cls.fiscal_pos_a = cls.env['account.fiscal.position'].create({
            'name': 'fiscal_pos_a',
            'tax_ids': ([(0, None, {
                    'tax_src_id': cls.tax_sale_a.id,
                    'tax_dest_id': cls.tax_sale_b.id,
            })] if cls.tax_sale_b else []) + ([(0, None, {
                    'tax_src_id': cls.tax_purchase_a.id,
                    'tax_dest_id': cls.tax_purchase_b.id,
            })] if cls.tax_purchase_b else []),
            'account_ids': [
                (0, None, {
                    'account_src_id': cls.product_a.property_account_income_id.id,
                    'account_dest_id': cls.product_b.property_account_income_id.id,
                }),
                (0, None, {
                    'account_src_id': cls.product_a.property_account_expense_id.id,
                    'account_dest_id': cls.product_b.property_account_expense_id.id,
                }),
            ],
        })

        # ==== Payment terms ====
        cls.pay_terms_a = cls.env.ref('account.account_payment_term_immediate')
        cls.pay_terms_b = cls.env['account.payment.term'].create({
            'name': '30% Advance End of Following Month',
            'note': 'Payment terms: 30% Advance End of Following Month',
            'line_ids': [
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 30.0,
                    'days': 0,
                }),
                (0, 0, {
                    'value': 'balance',
                    'value_amount': 0.0,
                    'months': 1,
                    'end_month': True,
                }),
            ],
        })

        # ==== Partners ====
        cls.partner_a = cls._create_partner(name="partner_a")
        cls.partner_b = cls._create_partner(
            property_payment_term_id=cls.pay_terms_b.id,
            property_supplier_payment_term_id=cls.pay_terms_b.id,
            property_account_position_id=cls.fiscal_pos_a.id,
            property_account_receivable_id=cls.company_data['default_account_receivable'].copy().id,
            property_account_payable_id=cls.company_data['default_account_payable'].copy().id,
        )

        # ==== Cash rounding ====
        cls.cash_rounding_a = cls.env['account.cash.rounding'].create({
            'name': 'add_invoice_line',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': cls.company_data['default_account_revenue'].copy().id,
            'loss_account_id': cls.company_data['default_account_expense'].copy().id,
            'rounding_method': 'UP',
        })
        cls.cash_rounding_b = cls.env['account.cash.rounding'].create({
            'name': 'biggest_tax',
            'rounding': 0.05,
            'strategy': 'biggest_tax',
            'rounding_method': 'DOWN',
        })

        # ==== Payment methods ====
        bank_journal = cls.company_data['default_journal_bank']

        cls.inbound_payment_method_line = bank_journal.inbound_payment_method_line_ids[0]
        cls.outbound_payment_method_line = bank_journal.outbound_payment_method_line_ids[0]

    @classmethod
    def setup_independant_company(cls, chart_template_ref="l10n_generic_coa.configurable_chart_template"):
        # OVERRIDE
        company = cls.env['res.company'].create({'name': "account"})
        cls._use_chart_template(company, chart_template_ref=chart_template_ref)
        return company

    @classmethod
    def setup_independant_user(cls):
        # OVERRIDE
        independant_user = super().setup_independant_user()
        # TODO LAS: this makes the test depend on installed modules
        # groups given should be fully specified, and not take the superadmin groups.
        independant_user.groups_id = cls.env.user.groups_id
        return independant_user

    @classmethod
    def _create_product(cls, **create_values):
        # OVERRIDE
        create_values.setdefault('property_account_income_id', cls.company_data['default_account_revenue'].id)
        create_values.setdefault('property_account_expense_id', cls.company_data['default_account_expense'].id)
        create_values.setdefault('taxes_id', [(6, 0, cls.tax_sale_a.ids)])
        return super()._create_product(**create_values)

    @classmethod
    def _use_chart_template(cls, company, chart_template_ref="l10n_generic_coa.configurable_chart_template"):
        chart_template = cls.env.ref(chart_template_ref, raise_if_not_found=False)
        if not chart_template:
            cls.tearDownClass()
            # skipTest raises exception
            cls.skipTest(cls, "Accounting Tests skipped because the user's company has no chart of accounts.")

        # Install the chart template.
        currency = company.currency_id
        chart_template.try_loading(company=company, install_demo=False)

        # The currency could be different after the installation of the chart template.
        if currency != company.currency_id:
            company.currency_id = currency

    @classmethod
    def collect_company_accounting_data(cls, company):

        def search_account_by_property(property_name, domain):
            template_code = company.chart_template_id[property_name].code
            domain = [('company_id', '=', company.id)] + domain

            account = None
            if template_code:
                account = cls.env['account.account'].search(domain + [('code', '=like', template_code + '%')], limit=1)

            if not account:
                account = cls.env['account.account'].search(domain, limit=1)
            return account

        return {
            'company': company,
            'currency': company.currency_id,
            'default_account_revenue': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('account_type', '=', 'income'),
                    ('id', '!=', company.account_journal_early_pay_discount_gain_account_id.id)
                ], limit=1),
            'default_account_expense': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('account_type', '=', 'expense'),
                    ('id', '!=', company.account_journal_early_pay_discount_loss_account_id.id)
                ], limit=1),
            'default_account_receivable': search_account_by_property(
                    'property_account_receivable_id',
                    [('account_type', '=', 'asset_receivable')],
                ),
            'default_account_payable': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('account_type', '=', 'liability_payable')
                ], limit=1),
            'default_account_assets': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('account_type', '=', 'asset_current')
                ], limit=1),
            'default_account_tax_sale': company.account_sale_tax_id.mapped('invoice_repartition_line_ids.account_id'),
            'default_account_tax_purchase': company.account_purchase_tax_id.mapped('invoice_repartition_line_ids.account_id'),
            'default_journal_misc': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'general')
                ], limit=1),
            'default_journal_sale': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'sale')
                ], limit=1),
            'default_journal_purchase': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'purchase')
                ], limit=1),
            'default_journal_bank': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'bank')
                ], limit=1),
            'default_journal_cash': cls.env['account.journal'].search([
                    ('company_id', '=', company.id),
                    ('type', '=', 'cash')
                ], limit=1),
            'default_tax_sale': company.account_sale_tax_id,
            'default_tax_purchase': company.account_purchase_tax_id,
        }

    @classmethod
    def setup_multi_currency_data(cls, rates, **kwargs):
        currency = cls.env['res.currency'].create({
            'rounding': 0.01,
            'position': 'after',
            **kwargs,
        })
        rates = cls.env['res.currency.rate'].create([
            {
                'name': rate_date,
                'rate': rate,
                'currency_id': currency.id,
                'company_id': cls.env.company.id,
            }
            for rate_date, rate in rates
        ])
        return {
            'currency': currency,
            'rates': rates,
        }

    @classmethod
    def setup_gold_currency(cls):
        return cls.setup_multi_currency_data(
            [('2016-01-01', 3.0), ('2017-01-01', 2.0)],
            name="Gold Coin",
            symbol='☺',
            currency_unit_label='Gold',
            currency_subunit_label='Silver',
        )

    @classmethod
    def copy_account(cls, account, default=None):
        suffix_nb = 1
        while True:
            new_code = '%s.%s' % (account.code, suffix_nb)
            if account.search_count([('company_id', '=', account.company_id.id), ('code', '=', new_code)]):
                suffix_nb += 1
            else:
                return account.copy(default={**(default or {}), 'code': new_code})

    @classmethod
    def setup_armageddon_tax(cls, tax_name, company_data):
        cash_basis_transition_account = company_data['default_account_tax_sale'] \
                                        and company_data['default_account_tax_sale'].copy()
        return cls.env['account.tax'].create({
            'name': '%s (group)' % tax_name,
            'amount_type': 'group',
            'amount': 0.0,
            'country_id': company_data['company'].account_fiscal_country_id.id,
            'children_tax_ids': [
                (0, 0, {
                    'name': '%s (child 1)' % tax_name,
                    'amount_type': 'percent',
                    'amount': 20.0,
                    'country_id': company_data['company'].account_fiscal_country_id.id,
                    'price_include': True,
                    'include_base_amount': True,
                    'tax_exigibility': 'on_invoice',
                    'invoice_repartition_line_ids': [
                        (0, 0, {
                            'repartition_type': 'base',
                        }),
                        (0, 0, {
                            'factor_percent': 40,
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                        (0, 0, {
                            'factor_percent': 60,
                            'repartition_type': 'tax',
                            # /!\ No account set.
                        }),
                    ],
                    'refund_repartition_line_ids': [
                        (0, 0, {
                            'repartition_type': 'base',
                        }),
                        (0, 0, {
                            'factor_percent': 40,
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                        (0, 0, {
                            'factor_percent': 60,
                            'repartition_type': 'tax',
                            # /!\ No account set.
                        }),
                    ],
                }),
                (0, 0, {
                    'name': '%s (child 2)' % tax_name,
                    'amount_type': 'percent',
                    'amount': 10.0,
                    'country_id': company_data['company'].account_fiscal_country_id.id,
                    'tax_exigibility': 'on_payment',
                    'cash_basis_transition_account_id': cash_basis_transition_account.id,
                    'invoice_repartition_line_ids': [
                        (0, 0, {
                            'repartition_type': 'base',
                        }),
                        (0, 0, {
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                    ],
                    'refund_repartition_line_ids': [
                        (0, 0, {
                            'repartition_type': 'base',
                        }),

                        (0, 0, {
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                    ],
                }),
            ],
        })

    @classmethod
    def init_invoice(cls, move_type, partner=None, invoice_date=None, post=False, products=None, amounts=None, taxes=None, company=False):
        move_form = Form(cls.env['account.move'] \
                    .with_company(company or cls.env.company) \
                    .with_context(default_move_type=move_type))
        move_form.invoice_date = invoice_date or fields.Date.from_string('2019-01-01')
        # According to the state or type of the invoice, the date field is sometimes visible or not
        # Besides, the date field can be put multiple times in the view
        # "invisible": "['|', ('state', '!=', 'draft'), ('auto_post', '!=', 'at_date')]"
        # "invisible": ['|', '|', ('state', '!=', 'draft'), ('auto_post', '=', 'no'), ('auto_post', '=', 'at_date')]
        # "invisible": "['&', ('move_type', 'in', ['out_invoice', 'out_refund', 'out_receipt']), ('quick_edit_mode', '=', False)]"
        # :TestAccountMoveOutInvoiceOnchanges, :TestAccountMoveOutRefundOnchanges, .test_00_debit_note_out_invoice, :TestAccountEdi
        if not move_form._get_modifier('date', 'invisible'):
            move_form.date = move_form.invoice_date
        move_form.partner_id = partner or cls.partner_a

        for product in (products or []):
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = product
                if taxes:
                    line_form.tax_ids.clear()
                    for tax in taxes:
                        line_form.tax_ids.add(tax)

        for amount in (amounts or []):
            with move_form.invoice_line_ids.new() as line_form:
                line_form.name = "test line"
                line_form.price_unit = amount
                if taxes:
                    line_form.tax_ids.clear()
                    for tax in taxes:
                        line_form.tax_ids.add(tax)

        rslt = move_form.save()

        if post:
            rslt.action_post()

        return rslt

    def assertInvoiceValues(self, move, expected_lines_values, expected_move_values):
        def sort_lines(lines):
            return lines.sorted(lambda line: (line.sequence, not bool(line.tax_line_id), line.name or '', line.balance))
        self.assertRecordValues(sort_lines(move.line_ids.sorted()), expected_lines_values)
        self.assertRecordValues(move, [expected_move_values])

    def assert_invoice_outstanding_to_reconcile_widget(self, invoice, expected_amounts):
        """ Check the outstanding widget before the reconciliation.
        :param invoice:             An invoice.
        :param expected_amounts:    A map <move_id> -> <amount>
        """
        invoice.invalidate_recordset(['invoice_outstanding_credits_debits_widget'])
        widget_vals = invoice.invoice_outstanding_credits_debits_widget

        if widget_vals:
            current_amounts = {vals['move_id']: vals['amount'] for vals in widget_vals['content']}
        else:
            current_amounts = {}
        self.assertDictEqual(current_amounts, expected_amounts)

    def assert_invoice_outstanding_reconciled_widget(self, invoice, expected_amounts):
        """ Check the outstanding widget after the reconciliation.
        :param invoice:             An invoice.
        :param expected_amounts:    A map <move_id> -> <amount>
        """
        invoice.invalidate_recordset(['invoice_payments_widget'])
        widget_vals = invoice.invoice_payments_widget

        if widget_vals:
            current_amounts = {vals['move_id']: vals['amount'] for vals in widget_vals['content']}
        else:
            current_amounts = {}
        self.assertDictEqual(current_amounts, expected_amounts)

    ####################################################
    # Xml Comparison
    ####################################################

    def _turn_node_as_dict_hierarchy(self, node):
        ''' Turn the node as a python dictionary to be compared later with another one.
        Allow to ignore the management of namespaces.
        :param node:    A node inside an xml tree.
        :return:        A python dictionary.
        '''
        tag_split = node.tag.split('}')
        tag_wo_ns = tag_split[-1]
        attrib_wo_ns = {k: v for k, v in node.attrib.items() if '}' not in k}
        return {
            'tag': tag_wo_ns,
            'namespace': None if len(tag_split) < 2 else tag_split[0],
            'text': (node.text or '').strip(),
            'attrib': attrib_wo_ns,
            'children': [self._turn_node_as_dict_hierarchy(child_node) for child_node in node.getchildren()],
        }

    def assertXmlTreeEqual(self, xml_tree, expected_xml_tree):
        ''' Compare two lxml.etree.
        :param xml_tree:            The current tree.
        :param expected_xml_tree:   The expected tree.
        '''

        def assertNodeDictEqual(node_dict, expected_node_dict):
            ''' Compare nodes created by the `_turn_node_as_dict_hierarchy` method.
            :param node_dict:           The node to compare with.
            :param expected_node_dict:  The expected node.
            '''
            # Check tag.
            self.assertEqual(node_dict['tag'], expected_node_dict['tag'])

            # Check attributes.
            node_dict_attrib = {k: '___ignore___' if expected_node_dict['attrib'].get(k) == '___ignore___' else v
                                for k, v in node_dict['attrib'].items()}
            expected_node_dict_attrib = {k: v for k, v in expected_node_dict['attrib'].items() if v != '___remove___'}
            self.assertDictEqual(
                node_dict_attrib,
                expected_node_dict_attrib,
                "Element attributes are different for node %s" % node_dict['tag'],
            )

            # Check text.
            if expected_node_dict['text'] != '___ignore___':
                self.assertEqual(
                    node_dict['text'],
                    expected_node_dict['text'],
                    "Element text are different for node %s" % node_dict['tag'],
                )

            # Check children.
            self.assertEqual(
                [child['tag'] for child in node_dict['children']],
                [child['tag'] for child in expected_node_dict['children']],
                "Number of children elements for node %s is different." % node_dict['tag'],
            )

            for child_node_dict, expected_child_node_dict in zip(node_dict['children'], expected_node_dict['children']):
                assertNodeDictEqual(child_node_dict, expected_child_node_dict)

        assertNodeDictEqual(
            self._turn_node_as_dict_hierarchy(xml_tree),
            self._turn_node_as_dict_hierarchy(expected_xml_tree),
        )

    def with_applied_xpath(self, xml_tree, xpath):
        ''' Applies the xpath to the xml_tree passed as parameter.
        :param xml_tree:    An instance of etree.
        :param xpath:       The xpath to apply as a string.
        :return:            The resulting etree after applying the xpaths.
        '''
        diff_xml_tree = etree.fromstring('<data>%s</data>' % xpath)
        return self.env['ir.ui.view'].apply_inheritance_specs(xml_tree, diff_xml_tree)

    def get_xml_tree_from_attachment(self, attachment):
        ''' Extract an instance of etree from an ir.attachment.
        :param attachment:  An ir.attachment.
        :return:            An instance of etree.
        '''
        return etree.fromstring(base64.b64decode(attachment.with_context(bin_size=False).datas))

    def get_xml_tree_from_string(self, xml_tree_str):
        ''' Convert the string passed as parameter to an instance of etree.
        :param xml_tree_str:    A string representing an xml.
        :return:                An instance of etree.
        '''
        return etree.fromstring(xml_tree_str)


class AccountTestInvoicingHttpCommon(AccountTestInvoicingCommon, HttpCase):
    pass
