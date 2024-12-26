# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo import fields
from odoo.fields import Command
from odoo.tests import Form, tagged
from odoo.tools import float_is_zero

from odoo.addons.sale.tests.common import TestSaleCommon


@tagged('-at_install', 'post_install')
class TestSaleToInvoice(TestSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

        # Create the SO with four order lines
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
            'order_line': [
                Command.create({
                    'product_id': cls.company_data['product_order_no'].id,
                    'product_uom_qty': 5,
                    'tax_id': False,
                }),
                Command.create({
                    'product_id': cls.company_data['product_service_delivery'].id,
                    'product_uom_qty': 4,
                    'tax_id': False,
                }),
                Command.create({
                    'product_id': cls.company_data['product_service_order'].id,
                    'product_uom_qty': 3,
                    'tax_id': False,
                }),
                Command.create({
                    'product_id': cls.company_data['product_delivery_no'].id,
                    'product_uom_qty': 2,
                    'tax_id': False,
                }),
            ]
        })

        (
            cls.sol_prod_order,
            cls.sol_serv_deliver,
            cls.sol_serv_order,
            cls.sol_prod_deliver,
        ) = cls.sale_order.order_line

        # Context
        cls.context = {
            'active_model': 'sale.order',
            'active_ids': [cls.sale_order.id],
            'active_id': cls.sale_order.id,
            'default_journal_id': cls.company_data['default_journal_sale'].id,
        }

    def _check_order_search(self, orders, domain, expected_result):
        domain += [('id', 'in', orders.ids)]
        result = self.env['sale.order'].search(domain)
        self.assertEqual(result, expected_result, "Unexpected result on search orders")

    def test_search_invoice_ids(self):
        """Test searching on computed fields invoice_ids"""

        # Make qty zero to have a line without invoices
        self.sol_prod_order.product_uom_qty = 0
        self.sale_order.action_confirm()

        # Tests before creating an invoice
        self._check_order_search(self.sale_order, [('invoice_ids', '=', False)], self.sale_order)
        self._check_order_search(self.sale_order, [('invoice_ids', '!=', False)], self.env['sale.order'])

        # Create invoice
        moves = self.sale_order._create_invoices()

        # Tests after creating the invoice
        self._check_order_search(self.sale_order, [('invoice_ids', 'in', moves.ids)], self.sale_order)
        self._check_order_search(self.sale_order, [('invoice_ids', '=', False)], self.env['sale.order'])
        self._check_order_search(self.sale_order, [('invoice_ids', '!=', False)], self.sale_order)

    def test_downpayment(self):
        """ Test invoice with a way of downpayment and check downpayment's SO line is created
            and also check a total amount of invoice is equal to a respective sale order's total amount
        """
        # Confirm the SO
        self.sale_order.action_confirm()
        self._check_order_search(self.sale_order, [('invoice_ids', '=', False)], self.sale_order)
        # Let's do an invoice for a deposit of 100
        downpayment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 50,
        })
        downpayment.create_invoices()
        downpayment2 = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 50,
        })
        downpayment2.create_invoices()
        self._check_order_search(self.sale_order, [('invoice_ids', '=', False)], self.env['sale.order'])

        self.assertEqual(len(self.sale_order.invoice_ids), 2, 'Invoice should be created for the SO')
        downpayment_line = self.sale_order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
        self.assertEqual(len(downpayment_line), 2, 'SO line downpayment should be created on SO')

        # Update delivered quantity of SO lines
        self.sol_serv_deliver.write({'qty_delivered': 4.0})
        self.sol_prod_deliver.write({'qty_delivered': 2.0})

        # Let's do an invoice with refunds
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({})
        payment.create_invoices()

        self.assertEqual(len(self.sale_order.invoice_ids), 3, 'Invoice should be created for the SO')

        invoice = max(self.sale_order.invoice_ids)
        self.assertEqual(len(invoice.invoice_line_ids.filtered(lambda l: not (l.display_type == 'line_section' and l.name == "Down Payments"))),
                         len(self.sale_order.order_line.filtered(lambda l: not (l.display_type == 'line_section' and l.name == "Down Payments"))), 'All lines should be invoiced')
        self.assertEqual(len(invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'line_section' and l.name == "Down Payments")), 1, 'A single section for downpayments should be present')
        self.assertEqual(invoice.amount_total, self.sale_order.amount_total - sum(downpayment_line.mapped('price_unit')), 'Downpayment should be applied')

    def test_downpayment_validation(self):
        """ Test invoice for downpayment and check it can be validated
        """
        # Lock the sale orders when confirmed
        self.env.user.groups_id += self.env.ref('sale.group_auto_done_setting')

        # Confirm the SO
        self.sale_order.action_confirm()
        self._check_order_search(self.sale_order, [('invoice_ids', '=', False)], self.sale_order)
        # Let's do an invoice for a deposit of 10%
        downpayment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'percentage',
            'amount': 10,
        })
        downpayment.create_invoices()
        self._check_order_search(self.sale_order, [('invoice_ids', '=', False)], self.env['sale.order'])

        # Update delivered quantity of SO lines
        self.sol_serv_deliver.write({'qty_delivered': 4.0})
        self.sol_prod_deliver.write({'qty_delivered': 2.0})

        # Validate invoice
        self.sale_order.invoice_ids.action_post()

    def test_downpayment_line_remains_on_SO(self):
        """ Test downpayment's SO line is created and remains unchanged even if everything is invoiced
        """
        # Create the SO with one line
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [Command.create({
                'product_id': self.company_data['product_order_no'].id,
                'product_uom_qty': 5,
                'tax_id': False,
            }),]
        })
        # Confirm the SO
        sale_order.action_confirm()
        # Update delivered quantity of SO line
        sale_order.order_line.write({'qty_delivered': 5.0})
        context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        # Let's do an invoice for a down payment of 50
        downpayment = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 50,
        })
        downpayment.create_invoices()
        # Let's do the invoice for the remaining amount
        payment = self.env['sale.advance.payment.inv'].with_context(context).create({})
        payment.create_invoices()

        downpayment_line = sale_order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
        self.assertEqual(downpayment_line[0].price_unit, 50, 'The down payment unit price should not change on SO')
        # Confirm all invoices
        sale_order.invoice_ids.action_post()
        self.assertEqual(downpayment_line[0].price_unit, 50, 'The down payment unit price should not change on SO')

    def test_downpayment_line_name(self):
        """ Test downpayment's SO line name is updated when invoice is posted. """
        # Create the SO with one line
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [Command.create({
                'product_id': self.company_data['product_order_no'].id,
                'product_uom_qty': 5,
                'tax_id': False,
            }),]
        })
        # Confirm the SO
        sale_order.action_confirm()
        # Update delivered quantity of SO line
        sale_order.order_line.write({'qty_delivered': 5.0})
        context = {
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        # Let's do an invoice for a down payment of 50
        self.env['sale.advance.payment.inv'].with_context(context).create({
            'sale_order_ids': [Command.set(sale_order.ids)],
            'advance_payment_method': 'fixed',
            'fixed_amount': 50,
        }).create_invoices()
        dp_line = sale_order.order_line.filtered(
            lambda sol: sol.is_downpayment and not sol.display_type
        )

        dp_line.name = 'whatever'

        # Confirm the invoice
        invoice = sale_order.invoice_ids
        invoice.action_post()

        self.assertNotEqual(
            dp_line.name, 'whatever',
            "DP lines description should be recomputed when the linked invoice is posted",
        )

    def test_downpayment_fixed_amount_with_zero_total_amount(self):
        # Create the SO with one line and amount total is zero
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [Command.create({
                'product_id': self.company_data['product_order_no'].id,
                'product_uom_qty': 5,
                'price_unit': 0,
                'tax_id': False,
            }), ]
        })
        sale_order.action_confirm()
        sale_order.order_line.write({'qty_delivered': 5.0})
        context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        # Let's do an invoice for a down payment of 50
        downpayment = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 50,
        })
        # Create invoice
        downpayment.create_invoices()
        self.assertEqual(downpayment.amount, 0.0, 'The down payment amount should be 0.0')

    def test_downpayment_percentage_tax_icl(self):
        """ Test invoice with a percentage downpayment and an included tax
            Check the total amount of invoice is correct and equal to a respective sale order's total amount
        """
        # Confirm the SO
        self.sale_order.action_confirm()
        tax_downpayment = self.company_data['default_tax_sale'].copy({
            'name': 'default price included',
            'price_include_override': 'tax_included',
        })
        # Let's do an invoice for a deposit of 100
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'percentage',
            'amount': 50,
        })
        payment.create_invoices()

        self.assertEqual(len(self.sale_order.invoice_ids), 1, 'Invoice should be created for the SO')
        downpayment_line = self.sale_order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
        self.assertEqual(len(downpayment_line), 1, 'SO line downpayment should be created on SO')
        self.assertEqual(downpayment_line.price_unit, self.sale_order.amount_total/2, 'downpayment should have the correct amount')

        invoice = self.sale_order.invoice_ids[0]
        downpayment_aml = invoice.line_ids.filtered(lambda l: not (l.display_type == 'line_section' and l.name == "Down Payments"))[0]
        self.assertEqual(downpayment_aml.price_total, self.sale_order.amount_total/2, 'downpayment should have the correct amount')
        self.assertEqual(downpayment_aml.price_unit, self.sale_order.amount_total/2, 'downpayment should have the correct amount')
        invoice.action_post()
        self.assertEqual(downpayment_line.price_unit, self.sale_order.amount_total/2, 'downpayment should have the correct amount')

    def test_downpayment_invoice_and_partial_credit_note(self):
        """This test check that the downpayment line amount on the sale order remains consistent"""
        self.sale_order.action_confirm()

        # Create an invoice for a Down payment of 100
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 100,
        })
        payment.create_invoices()

        # Ensure the downpayment line on the sale order is correctly set to 100
        downpayment_line = self.sale_order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
        self.assertEqual(downpayment_line.price_unit, 100)

        # post the downpayment invoice and ensure the downpayment_line amount is still 100
        downpayment_invoice = downpayment_line.order_id.order_line.invoice_lines.move_id
        downpayment_invoice.action_post()
        self.assertEqual(downpayment_line.price_unit, 100)

        # Create a credit note for a part of the downpayment invoice and post it
        move_reversal = self.env['account.move.reversal'].with_context(
            active_model="account.move",
            active_ids=downpayment_invoice.ids,
        ).create({
            'date': '2020-02-01',
            'reason': 'no reason',
            'journal_id': downpayment_invoice.journal_id.id,
        })
        reversal_action = move_reversal.reverse_moves()
        reverse_move = self.env['account.move'].browse(reversal_action['res_id'])
        with Form(reverse_move) as form_reverse:
            with form_reverse.invoice_line_ids.edit(0) as line_form:
                line_form.price_unit = 20.0
        reverse_move.action_post()

        self.assertEqual(downpayment_line.price_unit, 80,
                         "The downpayment line amount should be equal to the sum of the invoice and credit note amount")

    def test_invoice_with_discount(self):
        """ Test invoice with a discount and check discount applied on both SO lines and an invoice lines """
        # Update discount and delivered quantity on SO lines
        self.sol_prod_order.write({'discount': 20.0})
        self.sol_serv_deliver.write({'discount': 20.0, 'qty_delivered': 4.0})
        self.sol_serv_order.write({'discount': -10.0})
        self.sol_prod_deliver.write({'qty_delivered': 2.0})

        for line in self.sale_order.order_line.filtered(lambda l: l.discount):
            product_price = line.price_unit * line.product_uom_qty
            self.assertEqual(line.discount, (product_price - line.price_subtotal) / product_price * 100, 'Discount should be applied on order line')

        # lines are in draft
        for line in self.sale_order.order_line:
            self.assertTrue(float_is_zero(line.untaxed_amount_to_invoice, precision_digits=2), "The amount to invoice should be zero, as the line is in draf state")
            self.assertTrue(float_is_zero(line.untaxed_amount_invoiced, precision_digits=2), "The invoiced amount should be zero, as the line is in draft state")

        self.sale_order.action_confirm()

        for line in self.sale_order.order_line:
            self.assertTrue(float_is_zero(line.untaxed_amount_invoiced, precision_digits=2), "The invoiced amount should be zero, as the line is in draft state")

        self.assertEqual(
            self.sol_serv_order.untaxed_amount_to_invoice,
            297,
            "The untaxed amount to invoice is wrong")
        self.assertEqual(
            self.sol_serv_deliver.untaxed_amount_to_invoice,
            576,
            "The untaxed amount to invoice should be qty deli * price reduce, so 4 * (180 - 36)")
        # 'untaxed_amount_to_invoice' is invalid when 'sale_stock' is installed.
        # self.assertEqual(self.sol_prod_deliver.untaxed_amount_to_invoice, 140, "The untaxed amount to invoice should be qty deli * price reduce, so 4 * (180 - 36)")

        # Let's do an invoice with invoiceable lines
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        self._check_order_search(self.sale_order, [('invoice_ids', '=', False)], self.sale_order)
        payment.create_invoices()
        self._check_order_search(self.sale_order, [('invoice_ids', '=', False)], self.env['sale.order'])
        invoice = self.sale_order.invoice_ids[0]
        invoice.action_post()

        # Check discount appeared on both SO lines and invoice lines
        for line, inv_line in zip(self.sale_order.order_line, invoice.invoice_line_ids):
            self.assertEqual(line.discount, inv_line.discount, 'Discount on lines of order and invoice should be same')

    def test_invoice(self):
        """ Test create and invoice from the SO, and check qty invoice/to invoice, and the related amounts """
        # lines are in draft
        for line in self.sale_order.order_line:
            self.assertTrue(float_is_zero(line.untaxed_amount_to_invoice, precision_digits=2), "The amount to invoice should be zero, as the line is in draf state")
            self.assertTrue(float_is_zero(line.untaxed_amount_invoiced, precision_digits=2), "The invoiced amount should be zero, as the line is in draft state")

        # Confirm the SO
        self.sale_order.action_confirm()

        # Check ordered quantity, quantity to invoice and invoiced quantity of SO lines
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, 'Quantity to invoice should be same as ordered quantity')
                self.assertEqual(line.qty_invoiced, 0.0, 'Invoiced quantity should be zero as no any invoice created for SO')
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
            else:
                self.assertEqual(line.qty_to_invoice, line.product_uom_qty, 'Quantity to invoice should be same as ordered quantity')
                self.assertEqual(line.qty_invoiced, 0.0, 'Invoiced quantity should be zero as no any invoice created for SO')
                self.assertEqual(line.untaxed_amount_to_invoice, line.product_uom_qty * line.price_unit, "The amount to invoice should the total of the line, as the line is confirmed")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line is confirmed")

        # Let's do an invoice with invoiceable lines
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        payment.create_invoices()

        invoice = self.sale_order.invoice_ids[0]

        # Update quantity of an invoice lines
        move_form = Form(invoice)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 3.0
        with move_form.invoice_line_ids.edit(1) as line_form:
            line_form.quantity = 2.0
        invoice = move_form.save()

        # amount to invoice / invoiced should not have changed (amounts take only confirmed invoice into account)
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, "Quantity to invoice should be zero")
                self.assertEqual(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as delivered lines are not delivered yet")
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity (no confirmed invoice)")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as no invoice are validated for now")
            else:
                if line == self.sol_prod_order:
                    self.assertEqual(self.sol_prod_order.qty_to_invoice, 2.0, "Changing the quantity on draft invoice update the qty to invoice on SO lines")
                    self.assertEqual(self.sol_prod_order.qty_invoiced, 3.0, "Changing the quantity on draft invoice update the invoiced qty on SO lines")
                else:
                    self.assertEqual(self.sol_serv_order.qty_to_invoice, 1.0, "Changing the quantity on draft invoice update the qty to invoice on SO lines")
                    self.assertEqual(self.sol_serv_order.qty_invoiced, 2.0, "Changing the quantity on draft invoice update the invoiced qty on SO lines")
                self.assertEqual(line.untaxed_amount_to_invoice, line.product_uom_qty * line.price_unit, "The amount to invoice should the total of the line, as the line is confirmed (no confirmed invoice)")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as no invoice are validated for now")

        invoice.action_post()

        # Check quantity to invoice on SO lines
        for line in self.sale_order.order_line:
            if line.product_id.invoice_policy == 'delivery':
                self.assertEqual(line.qty_to_invoice, 0.0, "Quantity to invoice should be same as ordered quantity")
                self.assertEqual(line.qty_invoiced, 0.0, "Invoiced quantity should be zero as no any invoice created for SO")
                self.assertEqual(line.untaxed_amount_to_invoice, 0.0, "The amount to invoice should be zero, as the line based on delivered quantity")
                self.assertEqual(line.untaxed_amount_invoiced, 0.0, "The invoiced amount should be zero, as the line based on delivered quantity")
            else:
                if line == self.sol_prod_order:
                    self.assertEqual(line.qty_to_invoice, 2.0, "The ordered sale line are totally invoiced (qty to invoice is zero)")
                    self.assertEqual(line.qty_invoiced, 3.0, "The ordered (prod) sale line are totally invoiced (qty invoiced come from the invoice lines)")
                else:
                    self.assertEqual(line.qty_to_invoice, 1.0, "The ordered sale line are totally invoiced (qty to invoice is zero)")
                    self.assertEqual(line.qty_invoiced, 2.0, "The ordered (serv) sale line are totally invoiced (qty invoiced = the invoice lines)")
                self.assertEqual(line.untaxed_amount_to_invoice, line.price_unit * line.qty_to_invoice, "Amount to invoice is now set as qty to invoice * unit price since no price change on invoice, for ordered products")
                self.assertEqual(line.untaxed_amount_invoiced, line.price_unit * line.qty_invoiced, "Amount invoiced is now set as qty invoiced * unit price since no price change on invoice, for ordered products")

    def test_multiple_sale_orders_on_same_invoice(self):
        """ The model allows the association of multiple SO lines linked to the same invoice line.
            Check that the operations behave well, if a custom module creates such a situation.
        """
        self.sale_order.action_confirm()
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        payment.create_invoices()

        # create a second SO whose lines are linked to the same invoice lines
        # this is a way to create a situation where sale_line_ids has multiple items
        sale_order_data = self.sale_order.copy_data()[0]
        sale_order_data['order_line'] = [
            (0, 0, line.copy_data({
                'invoice_lines': [(6, 0, line.invoice_lines.ids)],
            })[0])
            for line in self.sale_order.order_line
        ]
        self.sale_order.create(sale_order_data)

        # we should now have at least one move line linked to several order lines
        invoice = self.sale_order.invoice_ids[0]
        self.assertTrue(any(len(move_line.sale_line_ids) > 1
                            for move_line in invoice.line_ids))

        # however these actions should not raise
        invoice.action_post()
        invoice.button_draft()
        invoice.button_cancel()

    def test_invoice_with_sections(self):
        """ Test create and invoice with sections from the SO, and check qty invoice/to invoice, and the related amounts """

        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
        })

        SaleOrderLine = self.env['sale.order.line'].with_context(tracking_disable=True)
        SaleOrderLine.create({
            'name': 'Section',
            'display_type': 'line_section',
            'order_id': sale_order.id,
        })
        sol_prod_deliver = SaleOrderLine.create({
            'product_id': self.company_data['product_order_no'].id,
            'product_uom_qty': 5,
            'order_id': sale_order.id,
            'tax_id': False,
        })

        # Confirm the SO
        sale_order.action_confirm()

        sol_prod_deliver.write({'qty_delivered': 5.0})

        # Context
        self.context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }

        # Let's do an invoice with invoiceable lines
        payment = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        payment.create_invoices()

        invoice = sale_order.invoice_ids[0]

        self.assertEqual(invoice.line_ids[0].display_type, 'line_section')

    def test_qty_invoiced(self):
        """Verify uom rounding is correctly considered during qty_invoiced compute"""
        sale_order = self.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
        })

        SaleOrderLine = self.env['sale.order.line'].with_context(tracking_disable=True)
        sol_prod_deliver = SaleOrderLine.create({
            'product_id': self.company_data['product_order_no'].id,
            'product_uom_qty': 5,
            'order_id': sale_order.id,
            'tax_id': False,
        })

        # Confirm the SO
        sale_order.action_confirm()

        sol_prod_deliver.write({'qty_delivered': 5.0})
        # Context
        self.context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }

        # Let's do an invoice with invoiceable lines
        invoicing_wizard = self.env['sale.advance.payment.inv'].with_context(self.context).create({
            'advance_payment_method': 'delivered'
        })
        invoicing_wizard.create_invoices()

        self.assertEqual(sol_prod_deliver.qty_invoiced, 5.0)
        # We would have to change the digits of the field to
        # test a greater decimal precision.
        quantity = 5.13
        move_form = Form(sale_order.invoice_ids)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = quantity
        move_form.save()

        # Default uom rounding to 0.01
        qty_invoiced_field = sol_prod_deliver._fields.get('qty_invoiced')
        sol_prod_deliver.env.add_to_compute(qty_invoiced_field, sol_prod_deliver)
        self.assertEqual(sol_prod_deliver.qty_invoiced, quantity)

        # Rounding to 0.1, should be rounded with UP (ceil) rounding_method
        # Not floor or half up rounding.
        sol_prod_deliver.product_uom.rounding *= 10
        sol_prod_deliver.product_uom.flush_recordset(['rounding'])
        expected_qty = 5.2
        qty_invoiced_field = sol_prod_deliver._fields.get('qty_invoiced')
        sol_prod_deliver.env.add_to_compute(qty_invoiced_field, sol_prod_deliver)
        self.assertEqual(sol_prod_deliver.qty_invoiced, expected_qty)

    def test_multi_company_invoice(self):
        """Checks that the company of the invoices generated in a multi company environment using the
           'sale.advance.payment.inv' wizard fit with the company of the SO and not with the current company.
        """
        so_company_id = self.sale_order.company_id.id
        yet_another_company_id = self.company_data_2['company'].id
        so_for_downpayment = self.sale_order.copy()

        self.context.update(allowed_company_ids=[yet_another_company_id, self.env.company.id], company_id=yet_another_company_id)
        context_for_downpayment = self.context.copy()
        context_for_downpayment.update(active_ids=[so_for_downpayment.id], active_id=so_for_downpayment.id)

        # Make sure the invoice is not created with a journal in the context
        # Because it makes the test always succeed (by using the journal company instead of the env company)
        no_journal_ctxt = dict(self.context)
        no_journal_ctxt.pop('default_journal_id', None)
        no_journal_ctxt.pop('journal_id', None)

        self.sale_order.with_context(self.context).action_confirm()
        payment = self.env['sale.advance.payment.inv'].with_context(no_journal_ctxt).create({
            'advance_payment_method': 'percentage',
            'amount': 50,
        })
        payment.create_invoices()
        self.assertEqual(self.sale_order.invoice_ids[0].company_id.id, so_company_id, "The company of the invoice should be the same as the one from the SO")

        so_for_downpayment.with_context(context_for_downpayment).action_confirm()
        downpayment = self.env['sale.advance.payment.inv'].with_context(context_for_downpayment).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 50,
        })
        downpayment.create_invoices()
        self.assertEqual(so_for_downpayment.invoice_ids[0].company_id.id, so_company_id, "The company of the downpayment invoice should be the same as the one from the SO")

    def test_invoice_analytic_distribution_model(self):
        """ Tests whether, when an analytic account rule is set and the so has no analytic account,
        the default analytic account is correctly computed in the invoice.
        """
        analytic_plan_default = self.env['account.analytic.plan'].create({'name': 'default'})
        analytic_account_default = self.env['account.analytic.account'].create({'name': 'default', 'plan_id': analytic_plan_default.id})

        self.env['account.analytic.distribution.model'].create({
            'analytic_distribution': {analytic_account_default.id: 100},
            'product_id': self.product_a.id,
        })

        so_form = Form(self.env['sale.order'])
        so_form.partner_id = self.partner_a

        with so_form.order_line.new() as sol:
            sol.product_id = self.product_a
            sol.product_uom_qty = 1

        so = so_form.save()
        so.action_confirm()
        so._force_lines_to_invoice_policy_order()

        so_context = {
            'active_model': 'sale.order',
            'active_ids': [so.id],
            'active_id': so.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        down_payment = self.env['sale.advance.payment.inv'].with_context(so_context).create({})
        down_payment.create_invoices()

        aml = self.env['account.move.line'].search([('move_id', 'in', so.invoice_ids.ids)])[0]
        self.assertRecordValues(aml, [{'analytic_distribution': {str(analytic_account_default.id): 100}}])

    def test_invoice_analytic_rule_with_account_prefix(self):
        """
        Test whether, when an analytic account rule is set within the scope (applicability) of invoice
        and with an account prefix set,
        the default analytic account is correctly set during the conversion from so to invoice
        """
        self.env.user.groups_id += self.env.ref('analytic.group_analytic_accounting')
        analytic_plan_default = self.env['account.analytic.plan'].create({
            'name': 'default',
            'applicability_ids': [Command.create({
                'business_domain': 'invoice',
                'applicability': 'optional',
            })]
        })
        analytic_account_default = self.env['account.analytic.account'].create({'name': 'default', 'plan_id': analytic_plan_default.id})

        analytic_distribution_model = self.env['account.analytic.distribution.model'].create({
            'account_prefix': '400000',
            'analytic_distribution': {analytic_account_default.id: 100},
            'product_id': self.product_a.id,
        })

        so = self.env['sale.order'].create({'partner_id': self.partner_a.id})
        self.env['sale.order.line'].create({
            'order_id': so.id,
            'name': 'test',
            'product_id': self.product_a.id
        })
        self.assertFalse(so.order_line.analytic_distribution, "There should be no tag set.")
        so.action_confirm()
        so.order_line.qty_delivered = 1
        aml = so._create_invoices().invoice_line_ids
        self.assertRecordValues(aml, [{'analytic_distribution': analytic_distribution_model.analytic_distribution}])

    def test_invoice_after_product_return_price_not_default(self):
        so = self.env['sale.order'].create({
            'name': 'Sale order',
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'order_line': [
                (0, 0, {'name': self.product_a.name, 'product_id': self.product_a.id, 'product_uom_qty': 1, 'price_unit': 123}),
            ]
        })
        self._check_order_search(so, [('invoice_ids', '=', False)], so)
        so.action_confirm()
        so_context = {
            'active_model': 'sale.order',
            'active_ids': [so.id],
            'active_id': so.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        invoicing_wizard = self.env['sale.advance.payment.inv'].with_context(so_context).create({})
        invoicing_wizard.create_invoices()
        self.assertTrue(so.invoice_ids, "The invoice was not created")
        # simulating return by changing product_uom_qty to 0
        so.order_line.product_uom_qty = 0
        # checking if the price_unit is the same
        self.assertEqual(so.order_line.price_unit, 123,
                         "The unit price should be the same as the one used to create the sales order line")

    def test_group_invoice(self):
        """ Test that invoicing multiple sales order for the same customer works. """
        # Create 3 SOs for the same partner, one of which that uses another currency
        eur_pricelist = self.env['product.pricelist'].create({'name': 'EUR', 'currency_id': self.env.ref('base.EUR').id})
        so1 = self.sale_order.with_context(mail_notrack=True).copy()
        so1.pricelist_id = eur_pricelist
        so2 = so1.copy()
        usd_pricelist = self.env['product.pricelist'].create({'name': 'USD', 'currency_id': self.env.ref('base.USD').id})
        so3 = so1.copy()
        so1.pricelist_id = usd_pricelist
        orders = so1 | so2 | so3
        orders.action_confirm()
        # Create the invoicing wizard and invoice all of them at once
        wiz = self.env['sale.advance.payment.inv'].with_context(active_ids=orders.ids, open_invoices=True).create({})
        res = wiz.create_invoices()
        # Check that exactly 2 invoices are generated
        self.assertEqual(
            len(res['domain'][0][2]),
            2,
            "Invoicing 3 orders for the same partner with 2 currencies"
            "should create exactly 2 invoices.")

    def test_so_note_to_invoice(self):
        """Test that notes from SO are pushed into invoices"""

        self.sale_order.order_line = [Command.create({
            'name': 'This is a note',
            'display_type': 'line_note',
            'product_id': False,
            'product_uom_qty': 0,
            'product_uom': False,
            'price_unit': 0,
            'order_id': self.sale_order.id,
            'tax_id': False,
        })]

        # confirm quotation
        self.sale_order.action_confirm()

        # create invoice
        invoice = self.sale_order._create_invoices()

        # check note from SO has been pushed in invoice
        self.assertEqual(
            len(invoice.invoice_line_ids.filtered(lambda line: line.display_type == 'line_note')),
            1,
            'Note SO line should have been pushed to the invoice')

    def test_sale_order_standard_flow_with_invoicing(self):
        """ Test the sales order flow (invoicing and quantity updates)
            - Invoice repeatedly while varrying delivered quantities and check that invoice are always what we expect
        """
        self.sale_order.order_line.product_uom_qty = 2.0
        # TODO?: validate invoice and register payments
        self.sale_order.order_line.read(['name', 'price_unit', 'product_uom_qty', 'price_total'])

        self.assertEqual(self.sale_order.amount_total, 1240.0, 'Sale: total amount is wrong')
        self.sale_order.order_line._compute_product_updatable()
        self.assertTrue(self.sale_order.order_line[0].product_updatable)
        # send quotation
        email_act = self.sale_order.action_quotation_send()
        email_ctx = email_act.get('context', {})
        self.sale_order.with_context(**email_ctx).message_post_with_source(
            self.env['mail.template'].browse(email_ctx.get('default_template_id')),
            subtype_xmlid='mail.mt_comment',
        )
        self.assertTrue(self.sale_order.state == 'sent', 'Sale: state after sending is wrong')
        self.sale_order.order_line._compute_product_updatable()
        self.assertTrue(self.sale_order.order_line[0].product_updatable)

        # confirm quotation
        self.sale_order.action_confirm()
        self.assertTrue(self.sale_order.state == 'sale')
        self.assertTrue(self.sale_order.invoice_status == 'to invoice')

        # create invoice: only 'invoice on order' products are invoiced
        invoice = self.sale_order._create_invoices()
        self.assertEqual(len(invoice.invoice_line_ids), 2, 'Sale: invoice is missing lines')
        self.assertEqual(invoice.amount_total, 740.0, 'Sale: invoice total amount is wrong')
        self.assertTrue(self.sale_order.invoice_status == 'no', 'Sale: SO status after invoicing should be "nothing to invoice"')
        self.assertTrue(len(self.sale_order.invoice_ids) == 1, 'Sale: invoice is missing')
        self.sale_order.order_line._compute_product_updatable()
        self.assertFalse(self.sale_order.order_line[0].product_updatable)

        # deliver lines except 'time and material' then invoice again
        for line in self.sale_order.order_line:
            line.qty_delivered = 2 if line.product_id.expense_policy == 'no' else 0
        self.assertTrue(self.sale_order.invoice_status == 'to invoice', 'Sale: SO status after delivery should be "to invoice"')
        invoice2 = self.sale_order._create_invoices()
        self.assertEqual(len(invoice2.invoice_line_ids), 2, 'Sale: second invoice is missing lines')
        self.assertEqual(invoice2.amount_total, 500.0, 'Sale: second invoice total amount is wrong')
        self.assertTrue(self.sale_order.invoice_status == 'invoiced', 'Sale: SO status after invoicing everything should be "invoiced"')
        self.assertTrue(len(self.sale_order.invoice_ids) == 2, 'Sale: invoice is missing')

        # go over the sold quantity
        self.sol_serv_order.write({'qty_delivered': 10})
        self.assertTrue(self.sale_order.invoice_status == 'upselling', 'Sale: SO status after increasing delivered qty higher than ordered qty should be "upselling"')

        # upsell and invoice
        self.sol_serv_order.write({'product_uom_qty': 10})

        # There is a bug with `new` and `_origin`
        # If you create a first new from a record, then change a value on the origin record, than create another new,
        # this other new wont have the updated value of the origin record, but the one from the previous new
        # Here the problem lies in the use of `new` in `move = self_ctx.new(new_vals)`,
        # and the fact this method is called multiple times in the same transaction test case.
        # Here, we update `qty_delivered` on the origin record, but the `new` records which are in cache with this order line
        # as origin are not updated, nor the fields that depends on it.
        self.env.flush_all()
        self.env.invalidate_all()

        invoice3 = self.sale_order._create_invoices()
        self.assertEqual(len(invoice3.invoice_line_ids), 1, 'Sale: third invoice is missing lines')
        self.assertEqual(invoice3.amount_total, 720.0, 'Sale: second invoice total amount is wrong')
        self.assertTrue(self.sale_order.invoice_status == 'invoiced', 'Sale: SO status after invoicing everything (including the upsel) should be "invoiced"')

    def test_so_create_multicompany(self):
        """Check that only taxes of the right company are applied on the lines."""
        # Preparing test Data
        product_shared = self.env['product.template'].create({
            'name': 'shared product',
            'invoice_policy': 'order',
            'taxes_id': [(6, False, (self.company_data['default_tax_sale'] + self.company_data_2['default_tax_sale']).ids)],
            'property_account_income_id': self.company_data['default_account_revenue'].id,
        })

        so_1 = self.env['sale.order'].with_user(self.company_data['default_user_salesman']).create({
            'partner_id': self.env['res.partner'].create({'name': 'A partner'}).id,
            'company_id': self.company_data['company'].id,
        })
        so_1.write({
            'order_line': [Command.create({'product_id': product_shared.product_variant_id.id})],
        })
        self.assertEqual(so_1.order_line.product_uom_qty, 1)

        self.assertEqual(so_1.order_line.tax_id, self.company_data['default_tax_sale'],
            'Only taxes from the right company are put by default')
        so_1.action_confirm()
        # i'm not interested in groups/acls, but in the multi-company flow only
        # the sudo is there for that and does not impact the invoice that gets created
        # the goal here is to invoice in company 1 (because the order is in company 1) while being
        # 'mainly' in company 2 (through the context), the invoice should be in company 1
        inv = so_1.sudo().with_context(
            allowed_company_ids=(self.company_data['company'] + self.company_data_2['company']).ids
        )._create_invoices()
        self.assertEqual(
            inv.company_id,
            self.company_data['company'],
            'invoices should be created in the company of the SO, not the main company of the context')

    def test_partial_invoicing_interaction_with_invoicing_switch_threshold(self):
        """ Let's say you partially invoice a SO, let's call the resuling invoice 'A'. Now if you change the
            'Invoicing Switch Threshold' such that the invoice date of 'A' is before the new threshold,
            the SO should still take invoice 'A' into account.
        """
        if not self.env['ir.module.module'].search([('name', '=', 'account_accountant'), ('state', '=', 'installed')]):
            self.skipTest("This test requires the installation of the account_account module")

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.company_data['product_delivery_no'].id,
                    'product_uom_qty': 20,
                    'price_unit': 30,
                }),
            ],
        })
        line = sale_order.order_line[0]

        sale_order.action_confirm()

        line.qty_delivered = 10

        invoice = sale_order._create_invoices()
        invoice.action_post()

        self.assertEqual(line.qty_invoiced, 10)

        self.env['res.config.settings'].create({
            'invoicing_switch_threshold': fields.Date.add(invoice.invoice_date, days=30),
        }).execute()

        invoice.invalidate_model(fnames=['payment_state'])

        self.assertEqual(line.qty_invoiced, 10)
        line.qty_delivered = 15
        self.assertEqual(line.qty_invoiced, 10)
        self.assertEqual(line.untaxed_amount_invoiced, 300)
        self.assertEqual(sale_order.amount_to_invoice, 150)

    def test_salesperson_in_invoice_followers(self):
        """
        Test if the salesperson is in the followers list of invoice created from SO
        """
        self.env = self.env(context={})
        # create a salesperson
        salesperson = self.env['res.users'].create({
            'name': 'Salesperson',
            'login': 'salesperson',
            'email': 'test@test.com',
            'groups_id': [(6, 0, [self.env.ref('sales_team.group_sale_salesman').id])]
        })

        # create a SO and generate invoice from it
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'user_id': salesperson.id,
            'order_line': [(0, 0, {
                'product_id': self.company_data['product_order_no'].id,
                'product_uom_qty': 1,
            })]
        })
        sale_order.action_confirm()
        invoice = sale_order._create_invoices(final=True)

        # check if the salesperson is in the followers list of invoice created from SO
        self.assertIn(salesperson.partner_id, invoice.message_partner_ids, 'Salesperson not in the followers list of '
                                                                           'invoice created from SO')
    def test_amount_to_invoice_multiple_so(self):
        """ Testing creating two SOs with the same customer and invoicing them together. We have to ensure
            that the amount to invoice is correct for each SO.
        """
        sale_order_1 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.company_data['product_delivery_no'].id,
                    'product_uom_qty': 10,
                }),
            ],
        })
        sale_order_2 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.company_data['product_delivery_no'].id,
                    'product_uom_qty': 20,
                }),
            ],
        })

        sale_order_1.action_confirm()
        sale_order_2.action_confirm()
        sale_order_1.order_line.qty_delivered = 10
        sale_order_2.order_line.qty_delivered = 20

        self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'delivered',
            'sale_order_ids': [Command.set((sale_order_1 + sale_order_2).ids)],
        }).create_invoices()

        sale_order_1.invoice_ids.action_post()

        self.assertEqual(sale_order_1.amount_to_invoice, 0.0)
        self.assertEqual(sale_order_2.amount_to_invoice, 0.0)

    def test_amount_to_invoice_one_line_multiple_so(self):
        """ Testing creating two SOs linked to the same invoice line. Drawback: the substracted
            amount to the amount_total will take both sale order into account.
        """
        sale_order_1 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.company_data['product_delivery_no'].id,
                    'product_uom_qty': 10,
                }),
            ],
        })
        sale_order_2 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.company_data['product_delivery_no'].id,
                    'product_uom_qty': 20,
                }),
            ],
        })

        sale_order_1.action_confirm()
        sale_order_2.action_confirm()
        sale_order_1.order_line.qty_delivered = 10
        sale_order_2.order_line.qty_delivered = 20

        self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'delivered',
            'sale_order_ids': [Command.set((sale_order_2).ids)],
        }).create_invoices()

        sale_order_1.invoice_ids = sale_order_2.invoice_ids
        sale_order_1.invoice_ids.line_ids.sale_line_ids += sale_order_1.order_line

        sale_order_1.invoice_ids.action_post()

        self.assertEqual(sale_order_1.amount_to_invoice, -700.0)
        self.assertEqual(sale_order_2.amount_to_invoice, 0.0)

    def test_amount_to_invoice_price_unit_change(self):
        """
        We check that the 'amount_to_invoice' relies only on the posted invoice quantity,
        and is not affected by price changes that occurred during invoice creation.
        """
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
        })

        sol_prod_deliver = self.env['sale.order.line'].create({
            'product_id': self.company_data['product_order_no'].id,
            'product_uom_qty': 5,
            'order_id': so.id,
            'tax_id': False,
        })

        so.action_confirm()
        sol_prod_deliver.write({'qty_delivered': 5.0})

        invoice_vals = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'delivered',
            'sale_order_ids': [Command.set(so.ids)],
        }).create_invoices()

        # Invoice is created in draft, which should impact 'qty_invoiced', but not 'amount_to_invoice'.
        self.assertEqual(sol_prod_deliver.qty_invoiced, 5.0)
        self.assertEqual(sol_prod_deliver.amount_to_invoice, sol_prod_deliver.price_total)
        self.assertEqual(sol_prod_deliver.amount_invoiced, 0.0)

        # Then we change the 'price_unit' on the invoice (keeping the quantity untouched).
        invoice = self.env[invoice_vals['res_model']].browse(invoice_vals['res_id'])
        invoice.invoice_line_ids.price_unit /= 2
        invoice.action_post()

        # In the end, the 'amount_to_invoice' should be 0.0, since all quantities have been invoiced,
        # even if the price was changed manually on the invoice.
        self.assertEqual(sol_prod_deliver.qty_invoiced, 5.0)
        self.assertEqual(sol_prod_deliver.amount_to_invoice, 0.0)
        self.assertEqual(sol_prod_deliver.amount_invoiced, sol_prod_deliver.price_total / 2)

    def test_invoice_line_name_has_product_name(self):
        """ Testing that when invoicing a sales order, the invoice line name ALWAYS contains the product name. """
        so = self.sale_order

        # Use only invoicable on order products
        so.order_line[1].product_id = so.order_line[0].product_id
        so.order_line[3].product_id = so.order_line[2].product_id

        # Adapt the SOL names to test the different cases
        so.order_line[0].name = "just a description"
        so.order_line[1].name = so.order_line[1].product_id.display_name
        so.order_line[2].name = f"{so.order_line[2].product_id.display_name} with more description"
        so.order_line[3].name = "product"

        # Invoice the sale order
        so.action_confirm()
        inv = self.sale_order._create_invoices()

        # Check the invoice line names
        self.assertEqual(inv.invoice_line_ids[0].name, f"{so.order_line[0].product_id.display_name} {so.order_line[0].name}", "When the description doesn't contain the product name, it should be added to the invoice line name")
        self.assertEqual(inv.invoice_line_ids[1].name, f"{so.order_line[1].name}", "When the description is the product name, the invoice line name should only be the description")
        self.assertEqual(inv.invoice_line_ids[2].name, f"{so.order_line[2].name}", "When description contains the product name, the invoice line name should only be the description")
        self.assertEqual(inv.invoice_line_ids[3].name, f"{so.order_line[3].product_id.display_name} {so.order_line[3].name}", "When the product name contains the description, the invoice line name should contain the product name and the description")

    def test_credit_note_automatic_matching(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.company_data['product_service_delivery'].id,
                }),
            ],
        })
        sale_order.action_confirm()

        sale_order.order_line.qty_delivered = 1

        invoice = sale_order._create_invoices()
        invoice.action_post()

        sale_order.order_line.qty_delivered = 0

        with patch.object(self.env.registry['account.move'], '_refunds_origin_required', lambda move: True):
            wizard_context = {
                'active_model': 'sale.order',
                'active_id': sale_order.id,
            }
            credit_note = self.env['sale.advance.payment.inv'].with_context(wizard_context).create({})._create_invoices(sale_order)
        credit_note.action_post()

        self.assertEqual(credit_note.reversed_entry_id.id, invoice.id)

    def test_credit_note_no_automatic_matching(self):
        product = self.company_data['product_service_delivery']

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
        })
        sale_line1 = self.env['sale.order.line'].create({
            'product_id': product.id,
            'product_uom_qty': 1,
            'price_unit': 200.0,
            'order_id': sale_order.id,
        })
        sale_line2 = self.env['sale.order.line'].create({
            'product_id': product.id,
            'product_uom_qty': 1,
            'price_unit': 100.0,
            'order_id': sale_order.id,
        })
        sale_order.action_confirm()

        sale_line1.qty_delivered = 1

        invoice = sale_order._create_invoices()
        invoice.action_post()

        sale_line2.qty_delivered = 1
        sale_line1.qty_delivered = 0

        with patch.object(self.env.registry['account.move'], '_refunds_origin_required', lambda move: True):
            wizard_context = {
                'active_model': 'sale.order',
                'active_id': sale_order.id,
            }
            credit_note = self.env['sale.advance.payment.inv'].with_context(wizard_context).create({})._create_invoices(sale_order)
        credit_note.action_post()

        # The invoice contains one invoice line
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        # the credit note contains 2
        self.assertEqual(len(credit_note.invoice_line_ids), 2)
        # so the credit note cannot be considered a reversal of the invoice
        self.assertFalse(credit_note.reversed_entry_id)
