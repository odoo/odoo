# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Guewen Baconnier
#    Copyright 2013 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import mock

import openerp.tests.common as common


class TestInvoiceEvent(common.TransactionCase):
    """ Test if the events on the invoice are fired correctly """

    def setUp(self):
        super(TestInvoiceEvent, self).setUp()
        self.invoice_model = self.env['account.invoice']
        partner_model = self.env['res.partner']
        partner = partner_model.create({'name': 'Hodor'})
        product = self.env.ref('product.product_product_6')
        invoice_vals = {'partner_id': partner.id,
                        'type': 'out_invoice',
                        'invoice_line': [(0, 0, {'name': "LCD Screen",
                                                 'product_id': product.id,
                                                 'quantity': 5,
                                                 'price_unit': 200})],
                        }
        onchange_res = self.invoice_model.onchange_partner_id('out_invoice',
                                                              partner.id)
        invoice_vals.update(onchange_res['value'])
        self.invoice = self.invoice_model.create(invoice_vals)

    def test_event_validated(self):
        """ Test if the ``on_invoice_validated`` event is fired
        when an invoice is validated """
        assert self.invoice, "The invoice has not been created"
        event = ('openerp.addons.connector_ecommerce.'
                 'invoice.on_invoice_validated')
        with mock.patch(event) as event_mock:
            self.invoice.signal_workflow('invoice_open')
            self.assertEqual(self.invoice.state, 'open')
            event_mock.fire.assert_called_with(mock.ANY,
                                               'account.invoice',
                                               self.invoice.id)

    def test_event_paid(self):
        """ Test if the ``on_invoice_paid`` event is fired
        when an invoice is paid """
        assert self.invoice, "The invoice has not been created"
        self.invoice.signal_workflow('invoice_open')
        self.assertEqual(self.invoice.state, 'open')
        journal = self.env.ref('account.bank_journal')
        pay_account = self.env.ref('account.cash')
        period = self.env.ref('account.period_10')
        event = 'openerp.addons.connector_ecommerce.invoice.on_invoice_paid'
        with mock.patch(event) as event_mock:
            self.invoice.pay_and_reconcile(
                pay_amount=self.invoice.amount_total,
                pay_account_id=pay_account.id,
                period_id=period.id,
                pay_journal_id=journal.id,
                writeoff_acc_id=pay_account.id,
                writeoff_period_id=period.id,
                writeoff_journal_id=journal.id,
                name="Payment for test of the event on_invoice_paid")
            self.assertEqual(self.invoice.state, 'paid')
            event_mock.fire.assert_called_with(mock.ANY,
                                               'account.invoice',
                                               self.invoice.id)
