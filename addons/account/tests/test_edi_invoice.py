# -*- coding: utf-8 -*-
import time
import json
from openerp.addons.account.tests.account_test_users import AccountTestUsers
from openerp.tools import float_compare


class TestEdiInvoice(AccountTestUsers):

    """ In order to test the EDI export features of Invoices. """

    def test_edi_invoice(self):
        # First I create a draft customer invoice
        self.account_invice_obj = self.env['account.invoice']
        self.partner2_id = self.env.ref('base.res_partner_2')
        self.currency_id = self.env.ref('base.EUR')
        self.account_id = self.env.ref('account.a_pay')
        self.invoice_line_obj = self.env['account.invoice.line']
        tax_obj = self.env['account.invoice.tax']
        edi_obj = self.env['edi.edi']

        self.invoice_edi_1 = self.account_invice_obj.create(dict(
            journal_id=1,
            partner_id=self.partner2_id.id,
            currency_id=self.currency_id.id,
            company_id=1,
            account_id=self.account_id.id,
            date_invoice=time.strftime('%Y-%m-%d'),
            name='selling product',
            type='out_invoice',
        ))

        # create invoice tax line
        tax_obj.create(dict(
            name='sale tax',
            account_id=self.account_id.id,
            manual=True,
            amount=1000.00,
            invoice_id=self.invoice_edi_1.id
        ))

        # create invoice line
        self.invoice_line_obj.create(dict(
            product_id=self.env.ref('product.product_product_3').id,
            uos_id=1,
            quantity=1.0,
            price_unit=10.0,
            name='basic pc',
            account_id=self.account_id.id,
            invoice_id=self.invoice_edi_1.id
        ))

        self.invoice_line_obj.create(dict(
            product_id=self.env.ref('product.product_product_5').id,
            uos_id=1,
            quantity=5.0,
            price_unit=100.0,
            name='PC on Demand',
            account_id=self.account_id.id,
            invoice_id=self.invoice_edi_1.id
        ))

        # I confirm and open the invoice
        self.invoice_edi_1.signal_workflow('invoice_open')

        # Then I export the customer invoice
        edi_doc = edi_obj.generate_edi([self.invoice_edi_1])
        assert isinstance(json.loads(edi_doc)[0], dict), 'EDI doc should be a JSON dict'

        edi_document = {
            "__id": "account:b33adf8a-decd-11f0-a4de-702a04e25700.random_invoice_763jsms",
            "__module": "account",
            "__model": "account.invoice",
            "__version": [7, 0, 0],
            "internal_number": time.strftime("SAJ/%Y/070"),
            "company_address": {
                "__id": "base:b33adf8a-decd-11f0-a4de-702a04e25700.main_address",
                "__module": "base",
                "__model": "res.partner",
                "city": "Gerompont",
                "name": "Company main address",
                "zip": "1367",
                "country_id": ["base:b33adf8a-decd-11f0-a4de-702a04e25700.be", "Belgium"],
                "phone": "(+32).81.81.37.00",
                "street": "Chaussee de Namur 40",
                "bank_ids": [
                    ["base:b33adf8a-decd-11f0-a4de-702a04e25700.res_partner_bank-ZrTWzesfsdDJzGbp", "Sample bank: 70-123465789-156113"]
                ],
            },
            "company_id": ["account:b33adf8a-decd-11f0-a4de-702a04e25700.res_company_test11", "Thomson pvt. ltd."],
            "currency": {
                "__id": "base:b33adf8a-decd-11f0-a4de-702a04e25700.EUR",
                "__module": "base",
                "__model": "res.currency",
                "code": "EUR",
                "symbol": "€",
            },
            "partner_id": ["account:b33adf8a-decd-11f0-a4de-702a04e25700.res_partner_test20", "Junjun wala"],
            "partner_address": {
                "__id": "base:5af1272e-dd26-11e0-b65e-701a04e25543.res_partner_address_7wdsjasdjh",
                "__module": "base",
                "__model": "res.partner",
                "name": "Default Address",
                "phone": "(+32).81.81.37.00",
                "street": "Chaussee de Namur 40",
                "city": "Gerompont",
                "zip": "1367",
                "country_id": ["base:5af1272e-dd26-11e0-b65e-701a04e25543.be", "Belgium"],
            },
            "date_invoice": time.strftime('%Y-%m-%d'),
            "name": "sample invoice",
            "tax_line": [{
                "__id": "account:b33adf8a-decd-11f0-a4de-702a04e25700.account_invoice_tax-4g4EutbiEMVl",
                "__module": "account",
                "__model": "account.invoice.tax",
                "amount": 1000.0,
                "manual": True,
                "name": "sale tax",
            }],
            "type": "out_invoice",
            "invoice_line": [{
                "__module": "account",
                "__model": "account.invoice.line",
                "__id": "account:b33adf8a-decd-11f0-a4de-702a04e25700.account_invoice_line-1RP3so",
                "uos_id": ["product:b33adf8a-decd-11f0-a4de-702a04e25700.product_uom_unit", "Unit"],
                "name": "PC Assemble SC234",
                "price_unit": 10.0,
                "product_id": ["product:b33adf8a-decd-11f0-a4de-702a04e25700.product_product_3", "[PCSC234] PC Assemble SC234"],
                "quantity": 1.0
            },
            {
                "__module": "account",
                "__model": "account.invoice.line",
                "__id": "account:b33adf8a-decd-11f0-a4de-702a04e25700.account_invoice_line-u2XV5",
                "uos_id": ["product:b33adf8a-decd-11f0-a4de-702a04e25700.product_uom_unit", "Unit"],
                "name": "PC on Demand",
                "price_unit": 100.0,
                "product_id": ["product:b33adf8a-decd-11f0-a4de-702a04e25700.product_product_5", "[PC-DEM] PC on Demand"],
                "quantity": 5.0
            }]
        }

        # invoice_id = edi_obj.import_edi(edi_document)
        # assert invoice_id, 'EDI import failed'
