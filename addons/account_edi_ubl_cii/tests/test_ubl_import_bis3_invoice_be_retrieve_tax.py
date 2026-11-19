from odoo import Command
from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBERetrieveTax(TestUblImportBis3InvoiceBE):

    _test_user_groups = None  # FIXME list needed groups

    def test_partial_import_tax_manual_tax_amounts(self):
        # Fail to retrieve the tax.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_manual_tax_amounts',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': [],
                },
                {
                    'quantity': 5.0,
                    'price_unit': 100.0,
                    'tax_ids': [],
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 1000.0,
                    'amount_tax': 0.0,
                    'amount_total': 1000.0,
                },
            ],
        )

        # Lines are linked to a single tax, the tax amount has been fixed
        tax_21 = self.percent_tax(21.0)
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_manual_tax_amounts',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': tax_21.ids,
                },
                {
                    'quantity': 5.0,
                    'price_unit': 100.0,
                    'tax_ids': tax_21.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 1000.0,
                    'amount_tax': 210.01,
                    'amount_total': 1210.01,
                },
            ],
        )

    def test_partial_import_tax_reverse_charge(self):
        # Fail to retrieve the tax: no reverse charge tax configured yet.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_reverse_charge',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(invoice.line_ids, [
            {
                'balance': -500.0,
                'tax_ids': [],
            },
            {
                'balance': 500.0,
                'tax_ids': [],
            },
        ])

        # The reverse charge tax is reported as 0% in the document, but the
        # tax matching it (same category code) is not 0%.
        tax_21_reverse_charge = self.percent_tax(
            21.0,
            ubl_cii_tax_category_code='AE',
            invoice_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'tag_ids': []}),
                Command.create({'repartition_type': 'tax', 'tag_ids': [], 'factor_percent': 100}),
                Command.create({'repartition_type': 'tax', 'tag_ids': [], 'factor_percent': -100}),
            ],
            refund_repartition_line_ids=[
                Command.create({'repartition_type': 'base', 'tag_ids': []}),
                Command.create({'repartition_type': 'tax', 'tag_ids': [], 'factor_percent': 100}),
                Command.create({'repartition_type': 'tax', 'tag_ids': [], 'factor_percent': -100}),
            ],
        )
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_reverse_charge',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(invoice.line_ids, [
            {
                'balance': -500.0,
                'tax_ids': tax_21_reverse_charge.ids,
            },
            {
                'balance': -105.0,
                'tax_ids': [],
            },
            {
                'balance': 105.0,
                'tax_ids': [],
            },
            {
                'balance': 500.0,
                'tax_ids': [],
            },
        ])

    def test_partial_import_tax_charge_to_fixed_tax(self):
        tax_21 = self.percent_tax(21.0)

        # Fail to retrieve the tax.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_charge_to_fixed_tax',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 5.0,
                    'price_unit': 200.0,
                    'discount': 0.0,
                    'tax_ids': tax_21.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 1000.0,
                    'amount_tax': 210.0,
                    'amount_total': 1210.0,
                },
            ],
        )

        # Lines are linked to a single tax, the tax amount has been fixed
        recupel = self.fixed_tax(1.0, name='RECUPEL', include_base_amount=True, sequence=0)
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_charge_to_fixed_tax',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 5.0,
                    'price_unit': 199.0,
                    'discount': 0.0,
                    'tax_ids': (recupel + tax_21).ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 995.0,
                    'amount_tax': 215.0,
                    'amount_total': 1210.0,
                },
            ],
        )

    @freeze_time('2020-01-01')
    def test_partial_import_tax_manual_tax_amounts_invoice_predictive(self):
        self.ensure_installed('account_accountant')

        tax_21_1 = self.percent_tax(21.0)
        tax_21_2 = self.percent_tax(21.0)

        # First invoice to train the prediction.
        self._create_invoice(
            partner_id=self.partner_be,
            invoice_line_ids=[
                self._prepare_invoice_line(name="turlututu", price_unit=500.0, tax_ids=tax_21_1),
                self._prepare_invoice_line(name="tsointsoin", price_unit=500.0, tax_ids=tax_21_2),
            ],
            post=True,
        )

        # Check the prediction.
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_manual_tax_amounts',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': tax_21_1.ids,
                },
                {
                    'quantity': 5.0,
                    'price_unit': 100.0,
                    'tax_ids': tax_21_2.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'partner_id': self.partner_be.id,
                    'amount_untaxed': 1000.0,
                    'amount_tax': 210.01,
                    'amount_total': 1210.01,
                },
            ],
        )

    @freeze_time('2020-01-01')
    def test_partial_import_tax_reverse_charge_invoice_predictive(self):
        self.ensure_installed('account_accountant')

        reverse_charge_repartition = {
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base', 'tag_ids': []}),
                Command.create({'repartition_type': 'tax', 'tag_ids': [], 'factor_percent': 100}),
                Command.create({'repartition_type': 'tax', 'tag_ids': [], 'factor_percent': -100}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base', 'tag_ids': []}),
                Command.create({'repartition_type': 'tax', 'tag_ids': [], 'factor_percent': 100}),
                Command.create({'repartition_type': 'tax', 'tag_ids': [], 'factor_percent': -100}),
            ],
        }
        self.percent_tax(0, ubl_cii_tax_category_code='E')  # See that we prefer the reverse charge over the exempt 0% because of the code set in the XML
        tax_21_reverse_charge = self.percent_tax(21.0, ubl_cii_tax_category_code='AE', **reverse_charge_repartition)
        tax_21_reverse_charge_other = self.percent_tax(21.0, ubl_cii_tax_category_code='AE', **reverse_charge_repartition)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_reverse_charge',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(invoice.line_ids, [
            {
                'balance': -500.0,
                'tax_ids': tax_21_reverse_charge.ids,
            },
            {
                'balance': -105.0,
                'tax_ids': [],
            },
            {
                'balance': 105.0,
                'tax_ids': [],
            },
            {
                'balance': 500.0,
                'tax_ids': [],
            },
        ])
        invoice.invoice_line_ids.tax_ids = tax_21_reverse_charge_other
        invoice.action_post()

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_reverse_charge',
            journal=self.company_data['default_journal_sale'],
        )
        self.assertRecordValues(invoice.line_ids, [
            {
                'balance': -500.0,
                'tax_ids': tax_21_reverse_charge_other.ids,
            },
            {
                'balance': -105.0,
                'tax_ids': [],
            },
            {
                'balance': 105.0,
                'tax_ids': [],
            },
            {
                'balance': 500.0,
                'tax_ids': [],
            },
        ])

    def test_import_foreign_tax(self):
        domestic = self.env['account.chart.template'].ref('template_generic_domestic_fiscal_position')
        foreign_trade = self.env['account.chart.template'].ref('template_generic_export_fiscal_position')
        tax_21 = self.percent_tax(21.0, type_tax_use='sale')
        tax_21_foreign = self.percent_tax(21.0, type_tax_use='sale', fiscal_position_ids=foreign_trade)

        bill = self._import_invoice_as_attachment_on(test_name='test_partial_import_tax_manual_tax_amounts', journal=self.company_data["default_journal_sale"])
        partner = bill.partner_id
        self.assertEqual(bill.line_ids.tax_ids, tax_21_foreign)

        partner.property_account_position_id = domestic
        bill = self._import_invoice_as_attachment_on(test_name='test_partial_import_tax_manual_tax_amounts', journal=self.company_data["default_journal_sale"])
        partner = bill.partner_id
        self.assertEqual(bill.line_ids.tax_ids, tax_21)

    def test_partial_import_tax_from_predicted_account_default_tax(self):
        tax_21_1 = self.percent_tax(21.0)
        tax_21_2 = self.percent_tax(21.0)

        account_with_tax = self.env['account.account'].create({
            'name': "Default Tax Account",
            'code': "DEFTAX",
            'account_type': 'income',
            'tax_ids': [Command.set(tax_21_1.ids)],
        })

        # Use a different tax on the training invoice to ensure that, during import,
        # the tax comes from the account's default tax rather than the predicted tax.
        self._create_invoice(
            partner_id=self.partner_be,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    name="turlututu",
                    price_unit=500.0,
                    account_id=account_with_tax.id,
                    tax_ids=tax_21_2,
                ),
            ],
            post=True,
        )

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_manual_tax_amounts',
            journal=self.company_data['default_journal_sale'],
        )
        # The predicted account's default tax should be selected
        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'tax_ids': tax_21_1.ids,
                },
                {
                    'quantity': 5.0,
                    'price_unit': 100.0,
                    'tax_ids': tax_21_1.ids,
                },
            ],
        )

    def test_partial_import_tax_included_invoice(self):
        tax_21_excl = self.percent_tax(21.0)
        self.percent_tax(21.0, price_include_override='tax_included')

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_partial_import_tax_manual_tax_amounts',
            journal=self.company_data['default_journal_sale'],
        )

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 1.0,
                    'price_unit': 500.0,
                    'discount': 0.0,
                    'tax_ids': tax_21_excl.ids,
                },
                {
                    'quantity': 5.0,
                    'price_unit': 100.0,
                    'discount': 0.0,
                    'tax_ids': tax_21_excl.ids,
                },
            ],
        )
        self.assertRecordValues(
            invoice,
            [
                {
                    'amount_untaxed': 1000.0,
                    'amount_tax': 210.01,
                    'amount_total': 1210.01,
                },
            ],
        )

    def test_import_document_charge_with_different_tax(self):
        tax_21_m = self.percent_tax(21.0, type_tax_use='purchase', name='VAT 21% M')
        tax_21_s = self.percent_tax(21.0, type_tax_use='purchase', name='VAT 21% S')

        def mocked_import_retrieve_tax(self, search_plan, company, tax_values_list):
            for tax_values in tax_values_list:
                if tax_values.get('invoice_predictive'):
                    tax_values['tax'] = tax_21_m
                elif tax_values.get('_tax_key'):
                    tax_values['tax'] = tax_21_s

        self.patch(self.env.registry['account.tax'], '_import_retrieve_tax', mocked_import_retrieve_tax)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_document_charge_tax_alignment',
            journal=self.company_data['default_journal_purchase'],
        )

        self.assertRecordValues(
            invoice,
            [{
                'amount_untaxed': 67.0,
                'amount_tax': 14.07,
                'amount_total': 81.07,
            }],
        )

    def test_import_invoice_fixed_tax_fuzzy(self):
        tax_21 = self.percent_tax(21.0)

        recupel = self.fixed_tax(0.12, name='REC 0.12', include_base_amount=True, sequence=0)

        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_invoice_fixed_tax_fuzzy',
            journal=self.company_data['default_journal_sale'],
        )

        self.assertRecordValues(
            invoice.invoice_line_ids,
            [
                {
                    'quantity': 2.0,
                    'price_unit': 199.875,
                    'discount': 0.0,
                    'tax_ids': (recupel + tax_21).ids,
                },
            ],
        )

    def test_import_retrieve_tax_from_fixed_allowance_charge(self):
        """ Test fuzzy matching of fixed taxes like Recupel and Bebat """
        company = self.company_data['company']

        tax_recupel = self.env['account.tax'].create({
            'name': 'REC 0.12',
            'amount_type': 'fixed',
            'amount': 0.12,
            'type_tax_use': 'purchase',
            'company_id': company.id,
        })
        tax_bebat = self.env['account.tax'].create({
            'name': 'Bebat 0.13',
            'amount_type': 'fixed',
            'amount': 0.13,
            'type_tax_use': 'purchase',
            'company_id': company.id,
        })
        random = self.env['account.tax'].create({
            'name': 'random 0.50',
            'amount_type': 'fixed',
            'amount': 0.50,
            'type_tax_use': 'purchase',
            'company_id': company.id,
        })

        dummy_invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'company_id': company.id,
        })

        def get_search_method(amount, reason, amount_type='fixed', reason_code=None, charge_indicator='true'):
            tax_values = {
                'amount_type': amount_type,
                'type_tax_use': 'purchase',
                'amount': amount,
                'reason': reason,
                'reason_code': reason_code,
                'charge_indicator': charge_indicator,
                'invoice_predictive': {'invoice': dummy_invoice},
            }
            plan = self.env['account.tax']._import_retrieve_tax_from_fixed_allowance_charge(tax_values)
            return plan['criteria'][0]['search_method'] if plan else None

        # multiple candidate taxes matching
        search_method_recupel = get_search_method(0.125, 'REC 0.12 (Kopie)')
        search_method_bebat = get_search_method(0.125, 'BEBAT')

        self.assertEqual(search_method_recupel({}), tax_recupel)
        self.assertEqual(search_method_bebat({}), tax_bebat)

        # single candidate tax match, even if the name doesnt match
        search_method_fallback = get_search_method(0.505, 'Unknown Eco Tax')
        self.assertEqual(search_method_fallback({}), random)

        # multiple candidate taxes matching, but name doesnt match
        search_method_not_found = get_search_method(0.125, 'Unknown Eco Tax')
        self.assertFalse(search_method_not_found({}))

        # percentage tax, early exit
        search_method_ignored = get_search_method(0.125, 'REC 0.12 (Kopie)', amount_type='percent')
        self.assertIsNone(search_method_ignored)

        # Taxes with allowance/charge reason codes (only kept when the tax affects the base of subsequent taxes).
        eco_tax_vals = {
            'amount_type': 'fixed',
            'amount': 0.20,
            'type_tax_use': 'purchase',
            'include_base_amount': True,
            'company_id': company.id,
        }
        tax_aeo_other, tax_aeo, tax_cav = self.env['account.tax'].create([
            {
                **eco_tax_vals,
                'name': 'Eco A',
                'sequence': 1,
                'ubl_cii_charge_reason_code': 'AEO',
                'ubl_cii_charge_reason': 'Other',
            },
            {
                **eco_tax_vals,
                'name': 'Eco B',
                'sequence': 2,
                'ubl_cii_charge_reason_code': 'AEO',
                'ubl_cii_charge_reason': 'Recycling',
            },
            {
                **eco_tax_vals,
                'name': 'Eco C',
                'sequence': 3,
                'ubl_cii_charge_reason_code': 'CAV',
            },
        ])
        tax_rebate = self.env['account.tax'].create({
            **eco_tax_vals,
            'name': 'Rebate',
            'amount': -0.20,
            'ubl_cii_allowance_reason_code': '100',
        })

        # reason code and reason match before reason code only
        self.assertEqual(get_search_method(0.20, 'Recycling', reason_code='AEO')({}), tax_aeo)
        self.assertEqual(get_search_method(0.20, 'Unknown', reason_code='AEO')({}), tax_aeo_other)

        # reason code match before tax name match
        self.assertEqual(get_search_method(0.20, 'Eco A', reason_code='CAV')({}), tax_cav)

        # no reason code match: tax name match
        self.assertEqual(get_search_method(0.20, 'Eco C', reason_code='FC')({}), tax_cav)

        # allowances only match on the allowance fields
        self.assertEqual(get_search_method(-0.20, 'Unknown', reason_code='100', charge_indicator='false')({}), tax_rebate)

        # single candidate but a non-matching reason code: no fallback
        self.assertFalse(get_search_method(0.505, 'Freight', reason_code='FC')({}))

        # single candidate without reason code: fallback
        self.assertEqual(get_search_method(-0.20, 'Unknown', charge_indicator='false')({}), tax_rebate)

        # allowance/charge fixed taxes are not retrieved by the price include/exclude search
        self.assertIsNone(self.env['account.tax']._import_retrieve_tax_from_price_include_exclude({
            'amount_type': 'fixed',
            'amount': 0.50,
            'charge_indicator': 'true',
        }))
