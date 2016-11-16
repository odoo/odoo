from openerp.tests.common import TransactionCase
import time


class TestInvoiceAnalysis(TransactionCase):
    def setUp(self):
        super(TestInvoiceAnalysis, self).setUp()
        self.account_invoice_model = self.env['account.invoice']
        self.account_invoice_line_model = self.env['account.invoice.line']
        self.mediapole_partner_id = self.ref('base.res_partner_8')
        self.currency_swiss_id = self.ref('base.CHF')
        self.currency_eur_id = self.ref('base.EUR')
        self.account_rcv_id = self.ref('account.a_recv')
        self.product_id = self.ref('product.product_product_4')
        self.invoice_report_model = self.env['account.invoice.report']

    def test_chf(self):
        # CHF company currency
        self.env.user.company_id.write({'currency_id': self.currency_swiss_id})

        # we create an invoice in CHF
        date_invoice = time.strftime('%Y')+'-07-01'
        invoice = self.account_invoice_model.create({
            'partner_id': self.mediapole_partner_id,
            'currency_id': self.currency_swiss_id,
            'name': 'invoice to client',
            'account_id': self.account_rcv_id,
            'type': 'out_invoice',
            'date_invoice': date_invoice,
            })
        self.account_invoice_line_model.create({
            'product_id': self.product_id,
            'quantity': 1,
            'price_unit': 100,
            'invoice_id': invoice.id,
            'name': 'product that cost 100',
            })
        invoice.signal_workflow('invoice_open')
        invoice_report_line = self.invoice_report_model.search([
            ('partner_id', '=', self.mediapole_partner_id),
            ('date', '=', time.strftime('%Y')+'-07-01'),
            ('currency_id', '=', self.currency_swiss_id)])
        # CHF total
        self.assertEqual(invoice_report_line.user_currency_price_total, 100)
        # CHF total
        self.assertEqual(invoice_report_line.price_total, 100)

        # we create an invoice in EUR
        date_invoice = time.strftime('%Y')+'-07-02'
        invoice = self.account_invoice_model.create({
            'partner_id': self.mediapole_partner_id,
            'currency_id': self.currency_eur_id,
            'name': 'invoice to client',
            'account_id': self.account_rcv_id,
            'type': 'out_invoice',
            'date_invoice': date_invoice,
            })
        self.account_invoice_line_model.create({
            'product_id': self.product_id,
            'quantity': 1,
            'price_unit': 100,
            'invoice_id': invoice.id,
            'name': 'product that cost 100',
            })
        invoice.signal_workflow('invoice_open')
        invoice_report_line = self.invoice_report_model.search([
            ('partner_id', '=', self.mediapole_partner_id),
            ('date', '=', time.strftime('%Y')+'-07-02'),
            ('currency_id', '=', self.currency_eur_id)])
        # CHF total
        self.assertEqual(invoice_report_line.user_currency_price_total, 130.86)
        # EUR total
        self.assertEqual(invoice_report_line.price_total, 100)

    def test_eur(self):
        # EUR company currency
        self.env.user.company_id.write({'currency_id': self.currency_eur_id})

        # we create an invoice in EUR
        date_invoice = time.strftime('%Y')+'-07-01'
        invoice = self.account_invoice_model.create({
            'partner_id': self.mediapole_partner_id,
            'currency_id': self.currency_eur_id,
            'name': 'invoice to client',
            'account_id': self.account_rcv_id,
            'type': 'out_invoice',
            'date_invoice': date_invoice,
            })
        self.account_invoice_line_model.create({
            'product_id': self.product_id,
            'quantity': 1,
            'price_unit': 100,
            'invoice_id': invoice.id,
            'name': 'product that cost 100',
            })
        invoice.signal_workflow('invoice_open')
        invoice_report_line = self.invoice_report_model.search([
            ('partner_id', '=', self.mediapole_partner_id),
            ('date', '=', time.strftime('%Y')+'-07-01'),
            ('currency_id', '=', self.currency_eur_id)])
        # EUR total
        self.assertEqual(invoice_report_line.user_currency_price_total, 100)
        # EUR total
        self.assertEqual(invoice_report_line.price_total, 100)

        # we create an invoice in CHF
        date_invoice = time.strftime('%Y')+'-07-02'
        invoice = self.account_invoice_model.create({
            'partner_id': self.mediapole_partner_id,
            'currency_id': self.currency_swiss_id,
            'name': 'invoice to client',
            'account_id': self.account_rcv_id,
            'type': 'out_invoice',
            'date_invoice': date_invoice,
            })
        self.account_invoice_line_model.create({
            'product_id': self.product_id,
            'quantity': 1,
            'price_unit': 100,
            'invoice_id': invoice.id,
            'name': 'product that cost 100',
            })
        invoice.signal_workflow('invoice_open')
        invoice_report_line = self.invoice_report_model.search([
            ('partner_id', '=', self.mediapole_partner_id),
            ('date', '=', time.strftime('%Y')+'-07-02'),
            ('currency_id', '=', self.currency_swiss_id)])
        # EUR total
        self.assertEqual(invoice_report_line.user_currency_price_total, 76.42)
        # CHF total
        self.assertEqual(invoice_report_line.price_total, 100)
        self.assertEqual(
            self.env.ref('base.res_partner_8').total_invoiced, 200)

