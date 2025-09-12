# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from collections import namedtuple

from odoo import fields
from odoo.tests import tagged
from odoo.exceptions import ValidationError
from odoo.addons.l10n_it_edi.tests.common import TestItEdi


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestWithholdingAndPensionFundTaxes(TestItEdi):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        def find_tax_by_ref(ref_name):
            return cls.env['account.chart.template'].with_company(cls.company).ref(ref_name)

        cls.withholding_sale_tax = find_tax_by_ref('20vwc')
        cls.withholding_purchase_tax = find_tax_by_ref('20awc')
        cls.withholding_sale_tax_23 = find_tax_by_ref('23vwo')
        cls.pension_fund_sale_tax = find_tax_by_ref('4vcp')
        cls.enasarco_sale_tax = find_tax_by_ref('enasarcov')
        cls.withholding_purchase_tax_23 = find_tax_by_ref('23awo')
        cls.enasarco_purchase_tax = find_tax_by_ref('enasarcoa')
        cls.inps_tax = find_tax_by_ref('4vinps')
        cls.inps_purchase_tax = find_tax_by_ref('4ainps')

        cls.zero_tax = cls.env['account.tax'].with_company(cls.company).create({
            'name': 'ZeroTax',
            'sequence': 31,
            'type_tax_use': 'sale',
            'amount': 0.0,
            'amount_type': 'percent',
            'l10n_it_exempt_reason': 'N2.2',
            'l10n_it_law_reference': 'Fatture emesse o ricevute da contribuenti forfettari o minimi',
        })

        cls.withholding_sale_line = {
            'name': 'withholding_line',
            'quantity': 1,
            'tax_ids': [(6, 0, [
                cls.withholding_sale_tax.id,
                cls.company.account_sale_tax_id.id,
            ])]
        }

        cls.pension_fund_sale_line = {
            'name': 'pension_fund_line',
            'quantity': 1,
            'tax_ids': [(6, 0, [
                cls.withholding_sale_tax.id,
                cls.pension_fund_sale_tax.id,
                cls.company.account_sale_tax_id.id,
            ])]
        }

        cls.enasarco_sale_line = {
            'name': 'enasarco_line',
            'quantity': 1,
            'tax_ids': [(6, 0, [
                cls.enasarco_sale_tax.id,
                cls.withholding_sale_tax_23.id,
                cls.company.account_sale_tax_id.id,
            ])]
        }

        cls.inps_sale_line = {
            'name': 'inps_line',
            'quantity': 1,
            'tax_ids': [(6, 0, [cls.inps_tax.id, cls.zero_tax.id])]
        }

        invoice_data = cls.get_real_client_invoice_data()

        cls.withholding_tax_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'company_id': cls.company.id,
            'partner_id': cls.italian_partner_a.id,
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'invoice_line_ids': [
                (0, 0, {
                    **cls.withholding_sale_line,
                    'name': name,
                    'price_unit': price,
                }) for (name, price) in invoice_data.lines
            ],
        })

        cls.pension_fund_tax_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'company_id': cls.company.id,
            'partner_id': cls.italian_partner_a.id,
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'invoice_line_ids': [
                (0, 0, {
                    **cls.pension_fund_sale_line,
                    'name': name,
                    'price_unit': price,
                }) for (name, price) in invoice_data.lines
            ]
        })

        cls.enasarco_tax_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'company_id': cls.company.id,
            'partner_id': cls.italian_partner_a.id,
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'invoice_line_ids': [
                (0, 0, {
                    **cls.enasarco_sale_line,
                    'name': name,
                    'price_unit': price,
                }) for (name, price) in invoice_data.lines
            ]
        })

        cls.inps_tax_invoice = cls.env['account.move'].with_company(cls.company).create({
            'move_type': 'out_invoice',
            'company_id': cls.company.id,
            'partner_id': cls.italian_partner_a.id,
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'invoice_line_ids': [
                (0, 0, {
                    **cls.inps_sale_line,
                    'name': name,
                    'price_unit': price,
                }) for (name, price) in invoice_data.lines
            ]
        })

        cls.withholding_tax_invoice._post()
        cls.pension_fund_tax_invoice._post()
        cls.enasarco_tax_invoice._post()
        cls.inps_tax_invoice._post()

        cls.module = 'l10n_it_edi_withholding'

    @classmethod
    def get_real_client_invoice_data(cls):
        data = {
            'lines': [
                ('Ordinary accounting service for the year', 350.0),
                ('Balance deposit for the past year', 300.0),
                ('Ordinary accounting service for the trimester', 50.0),
                ('Electronic invoices management', 50.0),
            ],
            'base': 750.0,
            'tax_amount': 165.0,
            'with_tax': 915.0,
            'withholding_amount': 150.0,
            'with_withholding': 765.0,
            'pension_fund_amount': 30.0,
            'with_pension_fund': 951.6,
            'tax_amount_with_pension_fund': 171.6,
            'payment_amount': 801.6,
        }
        return namedtuple('ClientInvoice', data.keys())(**data)

    def test_withholding_tax_constraints(self):
        with self.assertRaises(ValidationError):
            self.withholding_sale_tax.amount = 10
        with self.assertRaises(ValidationError):
            self.withholding_sale_tax.l10n_it_withholding_type = False
        with self.assertRaises(ValidationError):
            self.withholding_sale_tax.l10n_it_withholding_reason = False
        with self.assertRaises(ValidationError):
            self.company.account_sale_tax_id.l10n_it_withholding_type = "RT02"

    ####################################################
    # WITHHOLDING TAX
    ####################################################

    def test_withholding_taxes_export(self):
        """
            Invoice
            -------------------------------------------------------------
            Ordinary accounting service for the year               350.00
            Balance deposit for the past year                      300.00
            Ordinary accounting service for the trimester           50.00
            Electronic invoices management                          50.00
            -------------------------------------------------------------
            Total untaxed:                                         750.00
            Withholding:     20% of Untaxed Amount                -150.00
            VAT:             22% of Untaxed Amount                 165.00
            Document total:  Untaxed Amount + VAT                  915.00
            Payment amount:  Document total - Withholding          765.00
        """
        self._assert_export_invoice(self.withholding_tax_invoice, 'withholding_tax_invoice.xml')

    def test_withholding_taxes_import(self):
        invoice = self._assert_import_invoice('IT00470550013_withh.xml', [{
            'invoice_date': fields.Date.from_string('2022-03-24'),
            'amount_untaxed': 750.0,
            'amount_total': 765.00,
            'amount_tax': 15.0,
            'invoice_line_ids': [{
                'name': name,
                'price_unit': price_unit,
            } for name, price_unit in self.get_real_client_invoice_data().lines]
        }])

        invoice_data = self.get_real_client_invoice_data()
        for line in invoice.line_ids.filtered(lambda x: x.name in [data[0] for data in invoice_data.lines]):
            withholding_taxes = line.tax_ids.filtered(lambda x: x.l10n_it_withholding_type)
            pension_fund_taxes = line.tax_ids.filtered(lambda x: x.l10n_it_pension_fund_type)
            vat_taxes = line.tax_ids - withholding_taxes - pension_fund_taxes
            self.assertEqual([1, 1, 0], [len(x) for x in (vat_taxes, withholding_taxes, pension_fund_taxes)])

    ####################################################
    # PENSION FUND TAX
    ####################################################

    def test_pension_fund_taxes_export(self):
        """
            Invoice
            -------------------------------------------------------------
            Ordinary accounting service for the year               350.00
            Balance deposit for the past year                      300.00
            Ordinary accounting service for the trimester           50.00
            Electronic invoices management                          50.00
            -------------------------------------------------------------
            Total untaxed:                                         750.00
            Pension fund:    4% of Untaxed Amount                   30.00
            Withholding:     20% of Untaxed Amount                -150.00
            VAT:             22% of Untaxed Amount + Pension fund  171.60
            Document total:  Taxed Amount                          951.60
            Payment amount:  Document total - Withholding          801.60
        """
        self._assert_export_invoice(self.pension_fund_tax_invoice, 'pension_fund_tax_invoice.xml')

    def test_pension_fund_taxes_import_assosoftware_tag(self):
        invoice = self._assert_import_invoice('IT00470550013_pfund.xml', [{
            'invoice_date': fields.Date.from_string('2022-03-24'),
            'amount_untaxed': 750.0,
            'amount_total': 795.6,
            'amount_tax': 45.6,
            'invoice_line_ids': [{
                'name': name,
                'price_unit': price_unit,
            } for name, price_unit in self.get_real_client_invoice_data().lines]
        }])
        for line in invoice.line_ids.filtered(lambda x: x.display_type == 'product'):
            self.assertEqual(line.tax_ids, (
                self.inps_purchase_tax
                | self.withholding_purchase_tax
                | self.company.account_purchase_tax_id
            ))

    def test_pension_fund_taxes_import(self):
        invoice_data = self.get_real_client_invoice_data()
        invoice = self._assert_import_invoice('IT00470550013_pfun2.xml', [{
            'invoice_date': datetime.date(2022, 3, 24),
            'invoice_date_due': datetime.date(2022, 3, 24),
            'invoice_line_ids': [{
                'name': name,
                'price_unit': price,
            } for name, price in invoice_data.lines]
        }])
        for line in invoice.line_ids.filtered(lambda x: x.display_type == 'product'):
            self.assertEqual(line.tax_ids, (
                self.inps_purchase_tax
                | self.withholding_purchase_tax
                | self.company.account_purchase_tax_id
            ))

    ####################################################
    # ENASARCO TAX
    ####################################################

    def test_enasarco_tax_export(self):
        """
            Invoice
            -----------------------------------------------------------------
            Ordinary accounting service for the year                   350.00
            Balance deposit for the past year                          300.00
            Ordinary accounting service for the trimester               50.00
            Electronic invoices management                              50.00
            -----------------------------------------------------------------
            Total untaxed:                                             750.00
            VAT:             22% of Untaxed Amount                     165.00
            ENASARCO:        8.5% of Untaxed Amount                    -63.75
            Withholding Tax: 23% on 50% of Untaxed Amount              -86.25
            Document total:  Taxed Amount                              915.00
            Payment amount:  Document total - Withholding - Enasarco   765.00
        """
        self._assert_export_invoice(self.enasarco_tax_invoice, 'enasarco_tax_invoice.xml')

    def test_enasarco_tax_import(self):
        invoice = self._assert_import_invoice('IT00470550013_enasa.xml', [{
            'invoice_date': fields.Date.from_string('2022-03-24'),
            'amount_untaxed': 750.0,
            'amount_total': 765.0,
            'amount_tax': 15.0,
            'invoice_line_ids': [{
                'name': name,
                'price_unit': price_unit,
            } for name, price_unit in self.get_real_client_invoice_data().lines]
        }])

        invoice_data = self.get_real_client_invoice_data()
        for line in invoice.line_ids.filtered(lambda x: x.name in [data[0] for data in invoice_data.lines]):
            enasarco_imported_tax = line.tax_ids.filtered(lambda x: x.l10n_it_pension_fund_type == 'TC07')
            self.assertEqual(self.enasarco_purchase_tax, enasarco_imported_tax)
            self.assertEqual(-8.5, enasarco_imported_tax.amount)
            self.assertEqual(self.withholding_purchase_tax_23 | enasarco_imported_tax, line.tax_ids.filtered(lambda x: x.l10n_it_withholding_reason == 'ZO'))

    def test_enasarco_tax_import_global(self):
        """Test that if we have a unique ENASARCO line with a price of 0.0,
        the pension fund contribution will be applied on the total amount of
        the invoice instead of the line amount because it's considered as global.
        """
        applied_xml = """
            <xpath expr="//DettaglioLinee[NumeroLinea=1]/AltriDatiGestionali" position="replace"/>
            <xpath expr="//DettaglioLinee[NumeroLinea=2]/AltriDatiGestionali" position="replace"/>
            <xpath expr="//DettaglioLinee[NumeroLinea=3]/AltriDatiGestionali" position="replace"/>
            <xpath expr="//DettaglioLinee[NumeroLinea=4]/AltriDatiGestionali" position="replace"/>

            <xpath expr="//DettaglioLinee[NumeroLinea=4]" position="after">
                <DettaglioLinee>
                    <NumeroLinea>5</NumeroLinea>
                    <Descrizione>Contributo ENASARCO</Descrizione>
                    <PrezzoUnitario>0.00</PrezzoUnitario>
                    <PrezzoTotale>0.00</PrezzoTotale>
                    <AliquotaIVA>22.00</AliquotaIVA>
                    <AltriDatiGestionali>
                    <TipoDato>CASSA-PREV</TipoDato>
                    <RiferimentoTesto>TC07 - ENASARCO</RiferimentoTesto>
                    <RiferimentoNumero>63.75</RiferimentoNumero>
                    </AltriDatiGestionali>
                </DettaglioLinee>
            </xpath>
        """

        invoice = self._assert_import_invoice('IT00470550013_enasa.xml', [{
            'invoice_date': fields.Date.from_string('2022-03-24'),
            'amount_untaxed': 750.0,
            'amount_total': 765.0,
            'amount_tax': 15.0,
            'invoice_line_ids': [{
                'name': name,
                'price_unit': price_unit,
            } for name, price_unit in self.get_real_client_invoice_data().lines]
        }], applied_xml)

        invoice_data = self.get_real_client_invoice_data()
        for line in invoice.line_ids.filtered(lambda x: x.name in [data[0] for data in invoice_data.lines]):
            enasarco_imported_tax = line.tax_ids.filtered(lambda x: x.l10n_it_pension_fund_type == 'TC07')
            self.assertEqual(self.enasarco_purchase_tax, enasarco_imported_tax)
            self.assertEqual(-8.5, enasarco_imported_tax.amount)
            self.assertEqual(self.withholding_purchase_tax_23 | enasarco_imported_tax, line.tax_ids.filtered(lambda x: x.l10n_it_withholding_reason == 'ZO'))

    def test_inps_tax_export(self):
        """
            Invoice
            -----------------------------------------------------------------
            Ordinary accounting service for the year                   350.00
            Balance deposit for the past year                          300.00
            Ordinary accounting service for the trimester               50.00
            Electronic invoices management                              50.00
            -----------------------------------------------------------------
            Total untaxed:                                             750.00
            VAT:             0% of Untaxed Amount                        0.00
            INPS:            4% of Untaxed Amount                       30.00
            Document total:  Taxed Amount                              780.00
            Payment amount:  Document total                            780.00
        """
        self._assert_export_invoice(self.inps_tax_invoice, 'inps_tax_invoice.xml')
