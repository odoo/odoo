# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestReleaseToPayInvoice(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({'name': 'Zizizapartner'})
        cls.product = cls.env['product.product'].create({
            'name': 'VR Computer',
            'standard_price': 2500.0,
            'list_price': 2899.0,
            'type': 'service',
            'default_code': 'VR-01',
            'weight': 1.0,
            'purchase_method': 'receive',
        })
        cls.other_currency = cls.setup_other_currency('HRK', rounding=0.001)

    def check_release_to_pay_scenario(self, ordered_qty, scenario, invoicing_policy='receive', order_price=500.0):
        """ Generic test function to check that each use scenario behaves properly.
        """
        self.product.purchase_method = invoicing_policy

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                (0, 0, {
                    'name': self.product.name,
                    'product_id': self.product.id,
                    'product_qty': ordered_qty,
                    'product_uom': self.product.uom_po_id.id,
                    'price_unit': order_price,
                    'date_planned': fields.Datetime.now(),
                })]
        })
        purchase_order.button_confirm()

        invoices_list = []
        purchase_line = purchase_order.order_line[-1]
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for (action, params) in scenario:
            if action == 'invoice':
                # <field name="purchase_id" invisible="1"/>
                move_form = Form(AccountMove.with_context(default_purchase_id=purchase_order.id))
                with move_form.invoice_line_ids.edit(0) as line_form:
                    if 'price' in params:
                        line_form.price_unit = params['price']
                    if 'qty' in params:
                        line_form.quantity = params['qty']
                new_invoice = move_form.save()
                new_invoice.write({'invoice_line_ids': [
                    Command.create({'display_type': 'line_section', 'name': 'Section'}),
                    Command.create({'display_type': 'line_note', 'name': 'Note'}),
                ]})
                invoices_list.append(new_invoice)

                self.assertEqual(new_invoice.release_to_pay, params['rslt'], "Wrong invoice release to pay status for scenario " + str(scenario))

            elif action == 'receive':
                purchase_line.write({'qty_received': params['qty']})  # as the product is a service, its recieved quantity is set manually

                if 'rslt' in params:
                    for (invoice_index, status) in params['rslt']:
                        self.assertEqual(invoices_list[invoice_index].release_to_pay, status, "Wrong invoice release to pay status for scenario " + str(scenario))

    def test_3_way_match(self):
        self.check_release_to_pay_scenario(10, [('receive',{'qty': 5}), ('invoice', {'qty': 5, 'rslt': 'yes'})], invoicing_policy='purchase')
        self.check_release_to_pay_scenario(10, [('receive',{'qty': 5}), ('invoice', {'qty': 10, 'rslt': 'yes'})], invoicing_policy='purchase')
        self.check_release_to_pay_scenario(10, [('invoice', {'qty': 10, 'rslt': 'yes'})], invoicing_policy='purchase')
        self.check_release_to_pay_scenario(10, [('invoice', {'qty': 5, 'rslt': 'yes'}), ('receive',{'qty': 5}), ('invoice', {'qty': 6, 'rslt': 'exception'})], invoicing_policy='purchase')
        self.check_release_to_pay_scenario(10, [('invoice', {'qty': 10, 'rslt': 'yes'}), ('invoice', {'qty': 10, 'rslt': 'no'})], invoicing_policy='purchase')
        self.check_release_to_pay_scenario(10, [('receive',{'qty': 5}), ('invoice', {'qty': 5, 'rslt': 'yes'})])
        self.check_release_to_pay_scenario(10, [('receive',{'qty': 5}), ('invoice', {'qty': 10, 'rslt': 'exception'})])
        self.check_release_to_pay_scenario(10, [('invoice', {'qty': 5, 'rslt': 'no'})])
        self.check_release_to_pay_scenario(10, [('invoice', {'qty': 5, 'rslt': 'no'}), ('receive', {'qty': 5, 'rslt': [(-1, 'yes')]})])
        self.check_release_to_pay_scenario(10, [('invoice', {'qty': 5, 'rslt': 'no'}), ('receive', {'qty': 3, 'rslt': [(-1, 'exception')]})])
        self.check_release_to_pay_scenario(10, [('invoice', {'qty': 5, 'rslt': 'no'}), ('receive', {'qty': 10, 'rslt': [(-1, 'yes')]})])

        # Special use case : a price change between order and invoice should always put the bill in exception
        self.check_release_to_pay_scenario(10, [('receive',{'qty': 5}), ('invoice', {'qty': 5, 'rslt': 'exception', 'price':42})])
        self.check_release_to_pay_scenario(10, [('receive',{'qty': 5}), ('invoice', {'qty': 5, 'rslt': 'exception', 'price':42})], invoicing_policy='purchase')

    def test_amount_currency_edit(self):
        """
        Ensure that editing the `amount_currency` of a journal item on an invoice is possible.
        In 17.0 changes to Binary fields and web_save were made (related to context key 'bin_size').
        They led to tracebacks in the flow tested here.
        """
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.invoice_date = fields.Date.from_string('2023-01-01')
        move_form.partner_id = self.partner_a
        move_form.currency_id = self.other_currency
        with move_form.invoice_line_ids.new() as line_form:
            line_form.quantity = 1
            line_form.price_unit = 10
        move_form.save()
        with move_form.line_ids.edit(0) as line_form:
            line_form.amount_currency = -30
        move_form.save()
        self.assertEqual(move_form.line_ids.edit(0).amount_currency, -30)
