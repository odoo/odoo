# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields
from odoo.tests.common import SavepointCase, HttpSavepointCase, tagged, Form

import time
import base64
from lxml import etree

@tagged('post_install', '-at_install')
class AccountTestInvoicingCommon(SavepointCase):

    @classmethod
    def copy_account(cls, account):
        suffix_nb = 1
        while True:
            new_code = '%s (%s)' % (account.code, suffix_nb)
            if account.search_count([('company_id', '=', account.company_id.id), ('code', '=', new_code)]):
                suffix_nb += 1
            else:
                return account.copy(default={'code': new_code})

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super(AccountTestInvoicingCommon, cls).setUpClass()

        if chart_template_ref:
            chart_template = cls.env.ref(chart_template_ref)
        else:
            chart_template = cls.env.ref('l10n_generic_coa.configurable_chart_template', raise_if_not_found=False)
        if not chart_template:
            cls.tearDownClass()
            # skipTest raises exception
            cls.skipTest(cls, "Accounting Tests skipped because the user's company has no chart of accounts.")

        # Create user.
        user = cls.env['res.users'].create({
            'name': 'Because I am accountman!',
            'login': 'accountman',
            'password': 'accountman',
            'groups_id': [(6, 0, cls.env.user.groups_id.ids), (4, cls.env.ref('account.group_account_user').id)],
        })
        user.partner_id.email = 'accountman@test.com'

        # Shadow the current environment/cursor with one having the report user.
        # This is mandatory to test access rights.
        cls.env = cls.env(user=user)
        cls.cr = cls.env.cr

        cls.company_data_2 = cls.setup_company_data('company_2_data', chart_template=chart_template)
        cls.company_data = cls.setup_company_data('company_1_data', chart_template=chart_template)

        user.write({
            'company_ids': [(6, 0, (cls.company_data['company'] + cls.company_data_2['company']).ids)],
            'company_id': cls.company_data['company'].id,
        })

        cls.currency_data = cls.setup_multi_currency_data()

        # ==== Taxes ====
        cls.tax_sale_a = cls.company_data['default_tax_sale']
        cls.tax_sale_b = cls.company_data['default_tax_sale'].copy()
        cls.tax_purchase_a = cls.company_data['default_tax_purchase']
        cls.tax_purchase_b = cls.company_data['default_tax_purchase'].copy()
        cls.tax_armageddon = cls.setup_armageddon_tax('complex_tax', cls.company_data)

        # ==== Products ====
        cls.product_a = cls.env['product.product'].create({
            'name': 'product_a',
            'uom_id': cls.env.ref('uom.product_uom_unit').id,
            'lst_price': 1000.0,
            'standard_price': 800.0,
            'property_account_income_id': cls.company_data['default_account_revenue'].id,
            'property_account_expense_id': cls.company_data['default_account_expense'].id,
            'taxes_id': [(6, 0, cls.tax_sale_a.ids)],
            'supplier_taxes_id': [(6, 0, cls.tax_purchase_a.ids)],
        })
        cls.product_b = cls.env['product.product'].create({
            'name': 'product_b',
            'uom_id': cls.env.ref('uom.product_uom_dozen').id,
            'lst_price': 200.0,
            'standard_price': 160.0,
            'property_account_income_id': cls.copy_account(cls.company_data['default_account_revenue']).id,
            'property_account_expense_id': cls.copy_account(cls.company_data['default_account_expense']).id,
            'taxes_id': [(6, 0, (cls.tax_sale_a + cls.tax_sale_b).ids)],
            'supplier_taxes_id': [(6, 0, (cls.tax_purchase_a + cls.tax_purchase_b).ids)],
        })

        # ==== Fiscal positions ====
        cls.fiscal_pos_a = cls.env['account.fiscal.position'].create({
            'name': 'fiscal_pos_a',
            'tax_ids': [
                (0, None, {
                    'tax_src_id': cls.tax_sale_a.id,
                    'tax_dest_id': cls.tax_sale_b.id,
                }),
                (0, None, {
                    'tax_src_id': cls.tax_purchase_a.id,
                    'tax_dest_id': cls.tax_purchase_b.id,
                }),
            ],
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
                    'sequence': 400,
                    'days': 0,
                    'option': 'day_after_invoice_date',
                }),
                (0, 0, {
                    'value': 'balance',
                    'value_amount': 0.0,
                    'sequence': 500,
                    'days': 31,
                    'option': 'day_following_month',
                }),
            ],
        })

        # ==== Partners ====
        cls.partner_a = cls.env['res.partner'].create({
            'name': 'partner_a',
            'property_payment_term_id': cls.pay_terms_a.id,
            'property_supplier_payment_term_id': cls.pay_terms_a.id,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'company_id': False,
        })
        cls.partner_b = cls.env['res.partner'].create({
            'name': 'partner_b',
            'property_payment_term_id': cls.pay_terms_b.id,
            'property_supplier_payment_term_id': cls.pay_terms_b.id,
            'property_account_position_id': cls.fiscal_pos_a.id,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].copy().id,
            'property_account_payable_id': cls.company_data['default_account_payable'].copy().id,
            'company_id': False,
        })

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

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        ''' Create a new company having the name passed as parameter.
        A chart of accounts will be installed to this company: the same as the current company one.
        The current user will get access to this company.

        :param chart_template: The chart template to be used on this new company.
        :param company_name: The name of the company.
        :return: A dictionary will be returned containing all relevant accounting data for testing.
        '''
        def search_account(company, chart_template, field_name, domain):
            template_code = chart_template[field_name].code
            domain = [('company_id', '=', company.id)] + domain

            account = None
            if template_code:
                account = cls.env['account.account'].search(domain + [('code', '=like', template_code + '%')], limit=1)

            if not account:
                account = cls.env['account.account'].search(domain, limit=1)
            return account

        chart_template = chart_template or cls.env.company.chart_template_id
        company = cls.env['res.company'].create({
            'name': company_name,
            **kwargs,
        })
        cls.env.user.company_ids |= company

        chart_template.try_loading(company=company)

        # The currency could be different after the installation of the chart template.
        if kwargs.get('currency_id'):
            company.write({'currency_id': kwargs['currency_id']})

        return {
            'company': company,
            'currency': company.currency_id,
            'default_account_revenue': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('user_type_id', '=', cls.env.ref('account.data_account_type_revenue').id)
                ], limit=1),
            'default_account_expense': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('user_type_id', '=', cls.env.ref('account.data_account_type_expenses').id)
                ], limit=1),
            'default_account_receivable': search_account(company, chart_template, 'property_account_receivable_id', [
                ('user_type_id.type', '=', 'receivable')
            ]),
            'default_account_payable': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('user_type_id.type', '=', 'payable')
                ], limit=1),
            'default_account_assets': cls.env['account.account'].search([
                    ('company_id', '=', company.id),
                    ('user_type_id', '=', cls.env.ref('account.data_account_type_current_assets').id)
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
    def setup_multi_currency_data(cls, default_values={}, rate2016=3.0, rate2017=2.0):
        foreign_currency = cls.env['res.currency'].create({
            'name': 'Gold Coin',
            'symbol': '☺',
            'rounding': 0.001,
            'position': 'after',
            'currency_unit_label': 'Gold',
            'currency_subunit_label': 'Silver',
            **default_values,
        })
        rate1 = cls.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': rate2016,
            'currency_id': foreign_currency.id,
            'company_id': cls.env.company.id,
        })
        rate2 = cls.env['res.currency.rate'].create({
            'name': '2017-01-01',
            'rate': rate2017,
            'currency_id': foreign_currency.id,
            'company_id': cls.env.company.id,
        })
        return {
            'currency': foreign_currency,
            'rates': rate1 + rate2,
        }

    @classmethod
    def setup_armageddon_tax(cls, tax_name, company_data):
        return cls.env['account.tax'].create({
            'name': '%s (group)' % tax_name,
            'amount_type': 'group',
            'amount': 0.0,
            'children_tax_ids': [
                (0, 0, {
                    'name': '%s (child 1)' % tax_name,
                    'amount_type': 'percent',
                    'amount': 20.0,
                    'price_include': True,
                    'include_base_amount': True,
                    'tax_exigibility': 'on_invoice',
                    'invoice_repartition_line_ids': [
                        (0, 0, {
                            'factor_percent': 100,
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
                            'factor_percent': 100,
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
                    'tax_exigibility': 'on_payment',
                    'cash_basis_transition_account_id': company_data['default_account_tax_sale'].copy().id,
                    'invoice_repartition_line_ids': [
                        (0, 0, {
                            'factor_percent': 100,
                            'repartition_type': 'base',
                        }),
                        (0, 0, {
                            'factor_percent': 100,
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                    ],
                    'refund_repartition_line_ids': [
                        (0, 0, {
                            'factor_percent': 100,
                            'repartition_type': 'base',
                        }),

                        (0, 0, {
                            'factor_percent': 100,
                            'repartition_type': 'tax',
                            'account_id': company_data['default_account_tax_sale'].id,
                        }),
                    ],
                }),
            ],
        })

    @classmethod
    def init_invoice(cls, move_type, partner=None, invoice_date=None, post=False, products=[], amounts=[], taxes=None):
        move_form = Form(cls.env['account.move'].with_context(default_move_type=move_type))
        move_form.invoice_date = invoice_date or fields.Date.from_string('2019-01-01')
        move_form.partner_id = partner or cls.partner_a

        for product in products:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.product_id = product
                if taxes:
                    line_form.tax_ids.clear()
                    line_form.tax_ids.add(taxes)

        for amount in amounts:
            with move_form.invoice_line_ids.new() as line_form:
                line_form.price_unit = amount
                if taxes:
                    line_form.tax_ids.clear()
                    line_form.tax_ids.add(taxes)

        rslt = move_form.save()

        if post:
            rslt.action_post()

        return rslt

    def assertInvoiceValues(self, move, expected_lines_values, expected_move_values):
        def sort_lines(lines):
            return lines.sorted(lambda line: (line.exclude_from_invoice_tab, not bool(line.tax_line_id), line.name or '', line.balance))
        self.assertRecordValues(sort_lines(move.line_ids.sorted()), expected_lines_values)
        self.assertRecordValues(sort_lines(move.invoice_line_ids.sorted()), expected_lines_values[:len(move.invoice_line_ids)])
        self.assertRecordValues(move, [expected_move_values])

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


@tagged('post_install', '-at_install')
class AccountTestInvoicingHttpCommon(AccountTestInvoicingCommon, HttpSavepointCase):
    pass


class TestAccountReconciliationCommon(AccountTestInvoicingCommon):

    """Tests for reconciliation (account.tax)

    Test used to check that when doing a sale or purchase invoice in a different currency,
    the result will be balanced.
    """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company = cls.company_data['company']
        cls.company.currency_id = cls.env.ref('base.EUR')

        cls.partner_agrolait = cls.env['res.partner'].create({
            'name': 'Deco Addict',
            'is_company': True,
            'country_id': cls.env.ref('base.us').id,
        })
        cls.partner_agrolait_id = cls.partner_agrolait.id
        cls.currency_swiss_id = cls.env.ref("base.CHF").id
        cls.currency_usd_id = cls.env.ref("base.USD").id
        cls.currency_euro_id = cls.env.ref("base.EUR").id
        cls.account_rcv = cls.company_data['default_account_receivable']
        cls.account_rsa = cls.company_data['default_account_payable']
        cls.product = cls.env['product.product'].create({
            'name': 'Product Product 4',
            'standard_price': 500.0,
            'list_price': 750.0,
            'type': 'consu',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })

        cls.bank_journal_euro = cls.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'BNK67'})
        cls.account_euro = cls.bank_journal_euro.default_account_id

        cls.bank_journal_usd = cls.env['account.journal'].create({'name': 'Bank US', 'type': 'bank', 'code': 'BNK68', 'currency_id': cls.currency_usd_id})
        cls.account_usd = cls.bank_journal_usd.default_account_id

        cls.fx_journal = cls.company.currency_exchange_journal_id
        cls.diff_income_account = cls.company.income_currency_exchange_account_id
        cls.diff_expense_account = cls.company.expense_currency_exchange_account_id

        cls.inbound_payment_method = cls.env['account.payment.method'].create({
            'name': 'inbound',
            'code': 'IN',
            'payment_type': 'inbound',
        })

        cls.expense_account = cls.company_data['default_account_expense']
        # cash basis intermediary account
        cls.tax_waiting_account = cls.env['account.account'].create({
            'name': 'TAX_WAIT',
            'code': 'TWAIT',
            'user_type_id': cls.env.ref('account.data_account_type_current_liabilities').id,
            'reconcile': True,
            'company_id': cls.company.id,
        })
        # cash basis final account
        cls.tax_final_account = cls.env['account.account'].create({
            'name': 'TAX_TO_DEDUCT',
            'code': 'TDEDUCT',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
            'company_id': cls.company.id,
        })
        cls.tax_base_amount_account = cls.env['account.account'].create({
            'name': 'TAX_BASE',
            'code': 'TBASE',
            'user_type_id': cls.env.ref('account.data_account_type_current_assets').id,
            'company_id': cls.company.id,
        })
        cls.company.account_cash_basis_base_account_id = cls.tax_base_amount_account.id


        # Journals
        cls.purchase_journal = cls.company_data['default_journal_purchase']
        cls.cash_basis_journal = cls.env['account.journal'].create({
            'name': 'CABA',
            'code': 'CABA',
            'type': 'general',
        })
        cls.general_journal = cls.company_data['default_journal_misc']

        # Tax Cash Basis
        cls.tax_cash_basis = cls.env['account.tax'].create({
            'name': 'cash basis 20%',
            'type_tax_use': 'purchase',
            'company_id': cls.company.id,
            'amount': 20,
            'tax_exigibility': 'on_payment',
            'cash_basis_transition_account_id': cls.tax_waiting_account.id,
            'invoice_repartition_line_ids': [
                    (0,0, {
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),

                    (0,0, {
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': cls.tax_final_account.id,
                    }),
                ],
            'refund_repartition_line_ids': [
                    (0,0, {
                        'factor_percent': 100,
                        'repartition_type': 'base',
                    }),

                    (0,0, {
                        'factor_percent': 100,
                        'repartition_type': 'tax',
                        'account_id': cls.tax_final_account.id,
                    }),
                ],
        })
        cls.env['res.currency.rate'].create([
            {
                'currency_id': cls.env.ref('base.EUR').id,
                'name': '2010-01-02',
                'rate': 1.0,
            }, {
                'currency_id': cls.env.ref('base.USD').id,
                'name': '2010-01-02',
                'rate': 1.2834,
            }, {
                'currency_id': cls.env.ref('base.USD').id,
                'name': time.strftime('%Y-06-05'),
                'rate': 1.5289,
            }
        ])

    def _create_invoice(self, move_type='out_invoice', invoice_amount=50, currency_id=None, partner_id=None, date_invoice=None, payment_term_id=False, auto_validate=False):
        date_invoice = date_invoice or time.strftime('%Y') + '-07-01'

        invoice_vals = {
            'move_type': move_type,
            'partner_id': partner_id or self.partner_agrolait_id,
            'invoice_date': date_invoice,
            'date': date_invoice,
            'invoice_line_ids': [(0, 0, {
                'name': 'product that cost %s' % invoice_amount,
                'quantity': 1,
                'price_unit': invoice_amount,
                'tax_ids': [(6, 0, [])],
            })]
        }

        if payment_term_id:
            invoice_vals['invoice_payment_term_id'] = payment_term_id

        if currency_id:
            invoice_vals['currency_id'] = currency_id

        invoice = self.env['account.move'].with_context(default_move_type=type).create(invoice_vals)
        if auto_validate:
            invoice.action_post()
        return invoice

    def create_invoice(self, move_type='out_invoice', invoice_amount=50, currency_id=None):
        return self._create_invoice(move_type=move_type, invoice_amount=invoice_amount, currency_id=currency_id, auto_validate=True)

    def create_invoice_partner(self, move_type='out_invoice', invoice_amount=50, currency_id=None, partner_id=False, payment_term_id=False):
        return self._create_invoice(
            move_type=move_type,
            invoice_amount=invoice_amount,
            currency_id=currency_id,
            partner_id=partner_id,
            payment_term_id=payment_term_id,
            auto_validate=True
        )

    def make_payment(self, invoice_record, bank_journal, amount=0.0, amount_currency=0.0, currency_id=None, reconcile_param=[]):
        bank_stmt = self.env['account.bank.statement'].create({
            'journal_id': bank_journal.id,
            'date': time.strftime('%Y') + '-07-15',
            'name': 'payment' + invoice_record.name,
            'line_ids': [(0, 0, {
                'payment_ref': 'payment',
                'partner_id': self.partner_agrolait_id,
                'amount': amount,
                'amount_currency': amount_currency,
                'foreign_currency_id': currency_id,
            })],
        })
        bank_stmt.button_post()

        bank_stmt.line_ids[0].reconcile(reconcile_param)
        return bank_stmt

    def make_customer_and_supplier_flows(self, invoice_currency_id, invoice_amount, bank_journal, amount, amount_currency, transaction_currency_id):
        #we create an invoice in given invoice_currency
        invoice_record = self.create_invoice(move_type='out_invoice', invoice_amount=invoice_amount, currency_id=invoice_currency_id)
        #we encode a payment on it, on the given bank_journal with amount, amount_currency and transaction_currency given
        line = invoice_record.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        bank_stmt = self.make_payment(invoice_record, bank_journal, amount=amount, amount_currency=amount_currency, currency_id=transaction_currency_id, reconcile_param=[{'id': line.id}])
        customer_move_lines = bank_stmt.line_ids.line_ids

        #we create a supplier bill in given invoice_currency
        invoice_record = self.create_invoice(move_type='in_invoice', invoice_amount=invoice_amount, currency_id=invoice_currency_id)
        #we encode a payment on it, on the given bank_journal with amount, amount_currency and transaction_currency given
        line = invoice_record.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        bank_stmt = self.make_payment(invoice_record, bank_journal, amount=-amount, amount_currency=-amount_currency, currency_id=transaction_currency_id, reconcile_param=[{'id': line.id}])
        supplier_move_lines = bank_stmt.line_ids.line_ids
        return customer_move_lines, supplier_move_lines
