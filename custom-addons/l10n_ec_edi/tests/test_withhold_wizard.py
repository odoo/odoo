# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged, Form

from .common import TestEcEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEcEdiWithholdWizard(TestEcEdiCommon):

    # ===== TEST METHODS =====

    def test_out_withhold_basic_computes(self):
        wizard, out_invoice = self.get_wizard_and_invoice()
        self.assertFalse(wizard.withhold_line_ids)  # out_withhold has no default withhold lines

        self.env['l10n_ec.wizard.account.withhold.line'].create({
            'invoice_id': out_invoice.id,
            'wizard_id': wizard.id,
            'tax_id': self._get_tax_by_xml_id('tax_sale_withhold_vat_10').ids[0],
        })
        # creating a withhold line yields the expected values
        self.assertEqual(len(wizard.withhold_line_ids), 1)
        withhold_line = wizard.withhold_line_ids[0]
        self.assertEqual(withhold_line.taxsupport_code, False)
        self.assertEqual(withhold_line.base, 48)
        self.assertEqual(withhold_line.amount, 4.8)

    def test_out_withhold_basic_checks(self):
        wizard, out_invoice = self.get_wizard_and_invoice()

        with self.assertRaises(ValidationError):
            wizard.action_create_and_post_withhold()  # empty withhold can't be posted

        with self.assertRaises(ValidationError):
            self.env['l10n_ec.wizard.account.withhold.line'].create({
                'invoice_id': out_invoice.id,
                'wizard_id': wizard.id,
                'tax_id': self._get_tax_by_xml_id('tax_sale_withhold_vat_10').ids[0],
                'amount': -10,  # no negative amount in withhold lines
            })

    def test_purchase_invoice_withhold(self, custom_taxpayer=False):
        """Creates a purchase invoice and checks that when adding a withhold
        - the suggested taxes match the product default taxes
        - the tax supports are a subset of the invoice's tax supports
        - the withhold is successfully posted
        - it is not allowed to add another withhold
        """

        # Create purchase invoice and withhold wizard
        wizard, purchase_invoice = self.get_wizard_and_purchase_invoice()

        # Validate if the withholding tax established in the product is in the field default line creation wizard
        if not custom_taxpayer:
            wizard_tax_ids = wizard.withhold_line_ids.mapped('tax_id')
            product_invoice_tax_ids = purchase_invoice.invoice_line_ids.mapped('product_id.l10n_ec_withhold_tax_id')
            self.assertTrue(all(p_tax.id in wizard_tax_ids.ids for p_tax in product_invoice_tax_ids))

        # Validation: wizard's tax supports is subset of invoice's tax supports
        wizard_tax_support = set(wizard.withhold_line_ids.mapped('taxsupport_code'))
        invoice_tax_support = set(purchase_invoice._l10n_ec_get_inv_taxsupports_and_amounts().keys())
        self.assertTrue(wizard_tax_support.issubset(invoice_tax_support))

        with freeze_time(self.frozen_today):
            withhold = wizard.action_create_and_post_withhold()
        self.assertEqual(withhold.state, 'posted')

        purchase_invoice._compute_l10n_ec_withhold_inv_fields()
        with self.assertRaises(ValidationError, msg="Multiple invoices are only supported in customer withholds"):
            with freeze_time(self.frozen_today):
                wizard = self.env['l10n_ec.wizard.account.withhold'].with_context(active_ids=purchase_invoice.id, active_model='account.move').create({})

    def test_multiple_purchase_invoice_withhold(self, custom_taxpayer=False):
        """
        Test creation of single withholds from multiple bills is blocked
        """
        purchase_invoices = self.env['account.move']
        for partner in (self.partner_a, self.partner_b):
            with freeze_time(self.frozen_today):
                purchase_invoices |= self.get_invoice({
                    'move_type': 'in_invoice',
                    'partner_id': partner.id,
                    'journal_id': self.company_data['default_journal_purchase'].id,
                    'l10n_ec_sri_payment_id': self.env.ref('l10n_ec.P1').id,
                    'invoice_line_ids': self.get_custom_purchase_invoice_line_vals(),
                })
        purchase_invoices.action_post()
        with self.assertRaises(ValidationError, msg="Multiple invoices are only supported in customer withholds"):
            with freeze_time(self.frozen_today):
                wizard = self.env['l10n_ec.wizard.account.withhold'].with_context(active_ids=purchase_invoices.ids, active_model='account.move').create({})
                wizard.document_number = '001-001-000000001'
                wizard.action_create_and_post_withhold()

    def test_custom_taxpayer_type_partner_on_purchase_invoice(self):
        """Tests test_purchase_invoice_withhold with a custom taxpayer as a partner."""
        self.set_custom_taxpayer_type_on_partner_a()
        self.test_purchase_invoice_withhold(custom_taxpayer=True)

    def test_withold_invoice_partially_paid(self):
        """
        Tests that a withhold can be created on a partially paid invoice
        """
        wizard, invoice = self.get_wizard_and_invoice({
            'invoice_payment_term_id': self.env.ref('account.account_payment_term_advance_60days').id,
        })
        line_to_reco = invoice.line_ids.filtered(lambda l: l.display_type
                                                 and invoice.currency_id.is_zero(l.balance - invoice.amount_total * 0.3))
        self.env['account.payment.register'].with_context(active_model='account.move', active_ids=invoice.ids).create({
            'amount': line_to_reco.balance,
        })._create_payments()

        self.assertEqual(invoice.payment_state, 'partial')

        wizard.withhold_line_ids.create({
            'wizard_id': wizard.id,
            'invoice_id': invoice.id,
            'tax_id': self._get_tax_by_xml_id('tax_sale_withhold_vat_10').id,
        })

        with freeze_time(self.frozen_today):
            withhold = wizard.action_create_and_post_withhold()

        expected_withhold = self.env['account.move.line'].search([('l10n_ec_withhold_invoice_id', '=', invoice.id)]).mapped('move_id')

        self.assertEqual(withhold, expected_withhold)

    def test_out_withhold_with_two_invoices(self):
        """
        Test that when creating a batch withold for two invoices,
        the withhold lines are well reconciled with their respective
        invoices.
        """

        # Create two customer invoices
        inv_1 = self.get_invoice({'move_type': 'out_invoice', 'partner_id': self.partner_a.id})
        inv_2 = self.get_invoice({'move_type': 'out_invoice', 'partner_id': self.partner_a.id, 'l10n_latam_document_number': '001-001-000000002'})
        (inv_1 + inv_2).action_post()

        # Create the withhold wizard with three withhold lines, to be sure that each line is reconciled with the right invoice
        wizard = self.env['l10n_ec.wizard.account.withhold'].with_context(active_ids=(inv_1 + inv_2).ids, active_model='account.move').create({
            'withhold_line_ids': [
                Command.create({
                    'invoice_id': inv_1.id,
                    'tax_id': self._get_tax_by_xml_id('tax_sale_withhold_vat_10').id,
                }),
                Command.create({
                    'invoice_id': inv_1.id,
                    'tax_id': self._get_tax_by_xml_id('tax_withhold_profit_sale_1x100').id,
                }),
                Command.create({
                    'invoice_id': inv_2.id,
                    'tax_id': self._get_tax_by_xml_id('tax_sale_withhold_vat_10').id,
                })
            ]
        })

        with freeze_time(self.frozen_today):
            withhold = wizard.action_create_and_post_withhold()

        # The two invoices lines should be reconciled with the withhold
        for invoice in (inv_1, inv_2):
            with self.subTest(invoice=invoice):
                self.assertEqual(invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').matched_credit_ids.credit_move_id.move_id, withhold)

    def test_computed_base_of_withhold_lines_1(self):
        """Test that the base amount of the withhold lines is still correct after triggering its computed method."""
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'name': 'BILL/01',
            'invoice_date': self.frozen_today,
            'date': self.frozen_today,
            'l10n_ec_sri_payment_id': self.env['l10n_ec.sri.payment'].search([('code', '=', 20)], limit=1).id,  # Otros con utilización del sistema financiero (see l10n_ec.sri.payment.csv)
            'l10n_latam_document_number': '001-001-000000001',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [Command.set(self._get_tax_by_xml_id('tax_vat_510_sup_01').ids)],
                }),
                Command.create({
                    'name': 'No product line',
                    'quantity': 1,
                    'price_unit': 50,
                    'tax_ids': [Command.set(self._get_tax_by_xml_id('tax_vat_510_sup_01').ids)],
                }),
            ],
        })
        invoice.action_post()
        wizard = self.env['l10n_ec.wizard.account.withhold'].with_context(active_ids=invoice.id, active_model='account.move').new({})
        default_base = wizard.withhold_line_ids.mapped('base')
        wizard.withhold_line_ids._compute_base()
        computed_base = wizard.withhold_line_ids.mapped('base')
        self.assertEqual(computed_base, default_base)

    def test_computed_base_of_withhold_lines_2(self):
        """Test that the base amount of withholding lines correctly assigned"""
        self.set_custom_taxpayer_type_on_partner_a()
        l10n_ec_sri_payment_id = self.env['l10n_ec.sri.payment'].search([('code', '=', 20)], limit=1)
        tax_vat_510_sup_01_id = self._get_tax_by_xml_id('tax_vat_510_sup_01')
        tax_vat_510_sup_05_id = self._get_tax_by_xml_id('tax_vat_510_sup_05')
        tax_withhold_vat_20 = self._get_tax_by_xml_id('tax_withhold_vat_20')
        bill_1 = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'name': 'BILL/01',
            'invoice_date': self.frozen_today,
            'date': self.frozen_today,
            'l10n_ec_sri_payment_id': l10n_ec_sri_payment_id.id,
            'l10n_latam_document_number': '001-001-000000001',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [Command.set(tax_vat_510_sup_01_id.ids)],
                }),
            ],
        })
        bill_1.action_post()
        Wizard = self.env['l10n_ec.wizard.account.withhold'].with_context(active_ids=bill_1.id, active_model='account.move')
        wizard_form = Form(Wizard)
        wizard_form.document_number = '001-001-000000001'

        # Initial Wizard data
        # Tax Support | Tax     | Base  | Amount |
        # 01          | 10% 303 | 100.0 | 10.0   |
        # 01          | 10% WH  | 12.0  | 1.2    |
        with wizard_form.withhold_line_ids.edit(0) as wizard_line_form:
            self.assertEqual(wizard_line_form.base, 100.0, 'base should be the subtotal from bill line')
            self.assertEqual(wizard_line_form.amount, 10.0, 'amount should be the tax amount from bill line')

        # Edit WH tax amount
        # Tax Support | Tax      | Base  | Amount |
        # 01          | 10% 303  | 100.0 | 10.0   |
        # 01          | 10% WH   | 10.0  | 1.0    |
        with wizard_form.withhold_line_ids.edit(1) as wizard_line_form:
            self.assertEqual(wizard_line_form.base, 12.0, 'base should be calculated on tax amount')
            self.assertEqual(wizard_line_form.amount, 1.2)
            wizard_line_form.base = 10.0

        # Add another line with no available remaining amount
        # Tax Support | Tax     | Base  | Amount |
        # 01          | 10% 303 | 100.0 | 10.0   |
        # 01          | 10% WH  | 10.0  | 1.0    |
        # 01          | 10% 303 | 0.0   | 0.0    |
        with wizard_form.withhold_line_ids.new() as wizard_line_form:
            wizard_line_form.taxsupport_code = '01'
            wizard_line_form.tax_id = bill_1.commercial_partner_id.l10n_ec_taxpayer_type_id.profit_withhold_tax_id
            self.assertEqual(wizard_line_form.base, 0.0, 'base should be 0')

        # Change last line tax to 20%, remaining base should recompute accordingly
        # Tax Support | Tax     | Base  | Amount |
        # 01          | 10% 303 | 100.0 | 10.0   |
        # 01          | 10% WH  | 10.0  | 1.0    |
        # 01          | 20% WH  | 2.0   | 0.4    |
        with wizard_form.withhold_line_ids.edit(2) as wizard_line_form:
            wizard_line_form.tax_id = tax_withhold_vat_20
            self.assertEqual(wizard_line_form.base, 2.0, 'base should be the remaining amount (2.0)')

        # Add another tax line 20%, with no remaining base amounts should be 0
        # Tax Support | Tax     | Base  | Amount |
        # 01          | 10% 303 | 100.0 | 10.0   |
        # 01          | 10% WH  | 10.0  | 1.0    |
        # 01          | 20% WH  | 2.0   | 0.4    |
        # 01          | 20% WH  | 0.0   | 0.0    |
        with wizard_form.withhold_line_ids.new() as wizard_line_form:
            wizard_line_form.taxsupport_code = '01'
            wizard_line_form.tax_id = tax_withhold_vat_20
            self.assertEqual(wizard_line_form.base, 0.0, 'base should be 0')

        # Remove last line before saving
        wizard_form.withhold_line_ids.remove(3)

        wizard = wizard_form.save()

        expected_values = [{
            'taxsupport_code': '01',
            'tax_id': bill_1.commercial_partner_id.l10n_ec_taxpayer_type_id.profit_withhold_tax_id.id,
            'base': 100.0,
            'amount': 10.0,
        }, {
            'taxsupport_code': '01',
            'tax_id': bill_1.commercial_partner_id.l10n_ec_taxpayer_type_id.vat_goods_withhold_tax_id.id,
            'base': 10.0,
            'amount': 1.0,
        }, {
            'taxsupport_code': '01',
            'tax_id': tax_withhold_vat_20.id,
            'base': 2.0,
            'amount': 0.4,
        }]
        self.assertRecordValues(wizard.withhold_line_ids, expected_values)

        bill_2 = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'name': 'BILL/01',
            'invoice_date': self.frozen_today,
            'date': self.frozen_today,
            'l10n_ec_sri_payment_id': l10n_ec_sri_payment_id.id,
            'l10n_latam_document_number': '001-001-000000002',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [Command.set(tax_vat_510_sup_01_id.ids)],
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'quantity': 1,
                    'price_unit': 10,
                    'tax_ids': [Command.set(tax_vat_510_sup_05_id.ids)],
                }),
            ],
        })
        bill_2.action_post()
        wizard = self.env['l10n_ec.wizard.account.withhold'].with_context(active_ids=bill_2.id, active_model='account.move').create({})
        expected_values = [{
            'taxsupport_code': '01',
            'tax_id': bill_2.commercial_partner_id.l10n_ec_taxpayer_type_id.profit_withhold_tax_id.id,
            'base': 100.0,
            'amount': 10.0,
        }, {
            'taxsupport_code': '05',
            'tax_id': bill_2.commercial_partner_id.l10n_ec_taxpayer_type_id.profit_withhold_tax_id.id,
            'base': 10.0,
            'amount': 1.0,
        }, {
            'taxsupport_code': '01',
            'tax_id': bill_2.commercial_partner_id.l10n_ec_taxpayer_type_id.vat_goods_withhold_tax_id.id,
            'base': 12.0,
            'amount': 1.2,
        }, {
            'taxsupport_code': '05',
            'tax_id': bill_2.commercial_partner_id.l10n_ec_taxpayer_type_id.vat_goods_withhold_tax_id.id,
            'base': 1.2,
            'amount': 0.12,
        }]
        self.assertRecordValues(wizard.withhold_line_ids, expected_values)

    # ===== HELPER METHODS =====

    def get_wizard_and_invoice(self, invoice_args=None):
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
        }
        if invoice_args:
            invoice_vals.update(invoice_args)
        invoice = self.get_invoice(invoice_vals)
        invoice.action_post()
        wizard = self.env['l10n_ec.wizard.account.withhold'].with_context(active_ids=invoice.id, active_model='account.move')
        return wizard.create({}), invoice
