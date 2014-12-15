from openerp.tests.common import TransactionCase
from datetime import date
from openerp import workflow


class TestPaymentTerm(TransactionCase):
    def setUp(self):
        super(TestPaymentTerm, self).setUp()
        self.account_invoice_model = self.registry('account.invoice')
        self.account_invoice_line_model = self.registry('account.invoice.line')

        self.payment_term_model = self.registry('account.payment.term')
        self.payment_term_line_model = self.registry('account.payment.term.line')
        self.partner_agrolait_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "base", "res_partner_2")[1]
        self.currency_swiss_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "base", "CHF")[1]
        self.account_rcv_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "account", "a_recv")[1]
        self.product_id = self.registry("ir.model.data").get_object_reference(self.cr, self.uid, "product", "product_product_4")[1]

    def test_free_month(self):
        today = date(year=2014, month=12, day=15)
        payment_term = self.payment_term_model.create(self.cr, self.uid, {'name' : 'free month + 30',
                                                                    'active' : True,
                                                                    'line_ids' : [(0, 0, {'days' : 45,
                                                                                          'value' : 'balance',
                                                                                          'days2' : 0,
                                                                                          'count_from_next_month' : True,
                                                                                          'value_amount' : 0.0})]
        })

        invoice_id = self.account_invoice_model.create(self.cr, self.uid, {'partner_id': self.partner_agrolait_id,
            'reference_type': 'none',
            'currency_id': self.currency_swiss_id,
            'name': 'invoice to client',
            'account_id': self.account_rcv_id,
            'type': 'out_invoice',
            'date_invoice' : today,
            'payment_term' : payment_term
            })
        self.account_invoice_line_model.create(self.cr, self.uid, {'product_id': self.product_id,
            'quantity': 1,
            'price_unit': 100,
            'invoice_id': invoice_id,
            'name': 'product that cost 100',})


        workflow.trg_validate(self.uid, 'account.invoice', invoice_id, 'invoice_open', self.cr)
        due_date = self.account_invoice_model.read(self.cr, self.uid, [invoice_id], ['date_due'])[0]

        self.assertEquals('2015-02-15', due_date['date_due'])


