# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import Command
from odoo.addons.l10n_it_edi_doi.tests.common import TestItEdiDoi
from odoo.tests import tagged, Form


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestItEdiDoiRemaining(TestItEdiDoi):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id |= cls.env.ref('sales_team.group_sale_salesman')

    def create_invoice(self, declaration, invoice_line_vals):
        return self.env['account.move'].create({
            'move_type': 'out_invoice',
            'company_id': self.company.id,
            'partner_id': declaration.partner_id.id,
            'invoice_date': declaration.start_date,
            'l10n_it_edi_doi_id': declaration.id,
            'invoice_line_ids': invoice_line_vals,
        })

    def get_sale_order_vals(self, declaration, order_line_vals):
        return {
            'company_id': self.company.id,
            'partner_id': declaration.partner_id.id,
            'date_order': declaration.start_date,
            'pricelist_id': self.pricelist.id,
            'l10n_it_edi_doi_id': declaration.id,
            'order_line': order_line_vals,
        }

    def create_sale_order(self, declaration, order_line_vals):
        sale_order_vals = self.get_sale_order_vals(declaration, order_line_vals)
        return self.env['sale.order'].create(sale_order_vals)

    def test_invoice_line_edit(self):
        """
        Ensure the warnings are computed correctly when editing line values on an invoice.
        """
        declaration = self.declaration_1000
        declaration_tax = declaration.company_id.l10n_it_edi_doi_tax_id

        self.assertRecordValues(declaration, [{
            'invoiced': 0.0,
            'not_yet_invoiced': 0.0,
            'remaining': 1000.0,
        }])

        invoice = self.create_invoice(declaration, [
            Command.create({
                'name': 'declaration line',
                'quantity': 2,
                'price_unit': 1000.0,  # == declaration.threshold
                'tax_ids': [Command.set(declaration_tax.ids)],
            }),
        ])

        with Form(invoice) as invoice_form:
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                line_form.price_unit = 2000
                line_form.save()
                self.assertEqual(
                    invoice_form.l10n_it_edi_doi_warning,
                    "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 3,000.00\xa0€, this document included.\n"
                    "Invoiced: 4,000.00\xa0€; Not Yet Invoiced: 0.00\xa0€"
                )
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                line_form.quantity = 1
                line_form.save()
                self.assertEqual(
                    invoice_form.l10n_it_edi_doi_warning,
                    "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 1,000.00\xa0€, this document included.\n"
                    "Invoiced: 2,000.00\xa0€; Not Yet Invoiced: 0.00\xa0€"
                )

    def test_sale_order_line_edit(self):
        """
        Ensure the warnings are computed correctly when editing line values on a quotation or sale order.
        """
        declaration = self.declaration_1000
        declaration_tax = declaration.company_id.l10n_it_edi_doi_tax_id

        self.assertRecordValues(declaration, [{
            'invoiced': 0.0,
            'not_yet_invoiced': 0.0,
            'remaining': 1000.0,
        }])

        order = self.create_sale_order(declaration, [
            Command.create({
                'name': 'declaration line',
                'product_id': self.product_1.id,
                'price_unit': 1000.0,  # == declaration.threshold
                'product_uom_qty': 2,
                'tax_id': [Command.set(declaration_tax.ids)],
            }),
        ])

        with Form(order) as order_form:
            with order_form.order_line.edit(0) as line_form:
                line_form.price_unit = 2000
                line_form.save()
                self.assertEqual(
                    order_form.l10n_it_edi_doi_warning,
                    "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 3,000.00\xa0€, this document included.\n"
                    "Invoiced: 0.00\xa0€; Not Yet Invoiced: 4,000.00\xa0€"
                )
            with order_form.order_line.edit(0) as line_form:
                line_form.product_uom_qty = 1
                line_form.price_unit = 2000
                line_form.save()
                self.assertEqual(
                    order_form.l10n_it_edi_doi_warning,
                    "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 1,000.00\xa0€, this document included.\n"
                    "Invoiced: 0.00\xa0€; Not Yet Invoiced: 2,000.00\xa0€"
                )
            order_form.save()

            order.action_confirm()
            # unchanged warning
            self.assertEqual(
                order.l10n_it_edi_doi_warning,
                "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 1,000.00\xa0€, this document included.\n"
                "Invoiced: 0.00\xa0€; Not Yet Invoiced: 2,000.00\xa0€"
            )
            with order_form.order_line.edit(0) as line_form:
                line_form.price_unit = 3000
                line_form.save()
                self.assertEqual(
                    order_form.l10n_it_edi_doi_warning,
                    "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 2,000.00\xa0€, this document included.\n"
                    "Invoiced: 0.00\xa0€; Not Yet Invoiced: 3,000.00\xa0€"
                )
            with order_form.order_line.edit(0) as line_form:
                line_form.product_uom_qty = 2
                line_form.price_unit = 3000
                line_form.save()
                self.assertEqual(
                    order_form.l10n_it_edi_doi_warning,
                    "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 5,000.00\xa0€, this document included.\n"
                    "Invoiced: 0.00\xa0€; Not Yet Invoiced: 6,000.00\xa0€"
                )

    def test_invoice(self):
        """
        Ensure the amounts and warnings are computed correctly in the following flow:
        We create a single invoice and post it.
        """
        declaration = self.declaration_1000
        declaration_tax = declaration.company_id.l10n_it_edi_doi_tax_id

        self.assertRecordValues(declaration, [{
            'invoiced': 0.0,
            'not_yet_invoiced': 0.0,
            'remaining': 1000.0,
        }])

        invoice = self.create_invoice(declaration, [
                Command.create({
                    'name': 'declaration line',
                    'quantity': 1,
                    'price_unit': 1000.0,  # == declaration.threshold
                    'tax_ids': [Command.set(declaration_tax.ids)],
                }),
                Command.create({
                    # The line should be ignored since it does not use the special tax
                    'name': 'not a declaration line',
                    'quantity': 1,
                    'price_unit': 2000.0,  # > declaration.threshold; not counted
                    'tax_ids': False,
                }),
        ])
        # The amounts have not changed since the invoice has not been posted yet.
        self.assertRecordValues(declaration, [{
            'invoiced': 0.0,
            'not_yet_invoiced': 0.0,
            'remaining': 1000.0,
        }])
        # There is no warning since posting the invoice would not exceed the threshold.
        # (only lines with the special tax are counted)
        self.assertEqual(invoice.l10n_it_edi_doi_warning, "")

        # Update the declaration part of the invoice to exceed the threshold
        invoice.invoice_line_ids[0].price_unit = 2000  # > declaration.threshold
        # The amounts in the warning are the same as the amounts on the declaration after posting the invoice.
        self.assertEqual(
            invoice.l10n_it_edi_doi_warning,
            "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 1,000.00\xa0€, this document included.\n"
            "Invoiced: 2,000.00\xa0€; Not Yet Invoiced: 0.00\xa0€"
        )

        invoice.action_post()
        self.assertRecordValues(declaration, [{
            'invoiced': 2000.0,
            'not_yet_invoiced': 0.0,
            'remaining': -1000.0,
        }])
        self.assertEqual(
            invoice.l10n_it_edi_doi_warning,
            "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 1,000.00\xa0€, this document included.\n"
            "Invoiced: 2,000.00\xa0€; Not Yet Invoiced: 0.00\xa0€"
        )

    def test_sale_order_and_independent_invoice(self):
        """
        Ensure the amounts and warnings are computed correctly in the following flow:
          * We create a quotation and confirm it to sales order.
          * Then we create a single invoice independent of the sales order and post it.
            I.e. the invoice should not influence the Not Yet Invoiced amount of the declaration.
        """
        declaration = self.declaration_1000
        declaration_tax = declaration.company_id.l10n_it_edi_doi_tax_id

        order = self.create_sale_order(declaration, [
            Command.create({
                'name': 'declaration line',
                'product_id': self.product_1.id,
                'price_unit': 1000.0,  # == declaration.threshold
                'tax_id': [Command.set(declaration_tax.ids)],
            }),
            Command.create({
                'name': 'not a declaration line',
                'product_id': self.product_1.id,
                'price_unit': 2000.0,  # > declaration.threshold; not counted
                'tax_id': False,
            }),
        ])

        # There is no warning since confirming the sale order would not exceed the threshold.
        # (only lines with the special tax are counted)
        self.assertEqual(order.l10n_it_edi_doi_warning, "")

        # We only count sales orders not quotations
        self.assertRecordValues(declaration, [{
            'invoiced': 0.0,
            'not_yet_invoiced': 0.0,
            'remaining': 1000.0,
        }])

        # Update the declaration part of `order` to exceed the threshold
        order.order_line[0].price_unit = 2000  # > declaration.threshold
        # Now we show the warning
        self.assertEqual(
            order.l10n_it_edi_doi_warning,
            "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 1,000.00\xa0€, this document included.\n"
            "Invoiced: 0.00\xa0€; Not Yet Invoiced: 2,000.00\xa0€"
        )

        order.action_confirm()
        self.assertRecordValues(declaration, [{
            'invoiced': 0.0,
            'not_yet_invoiced': 2000.0,
            'remaining': -1000.0,
        }])

        invoice = self.create_invoice(declaration, [
            Command.create({
                'name': 'declaration line',
                'quantity': 1,
                'price_unit': 1000.0,
                'tax_ids': [Command.set(declaration_tax.ids)],
            }),
            Command.create({
                # The line should be ignored since it does not use the special tax
                'name': 'none declaration line',
                'quantity': 1,
                'price_unit': 2000.0,  # > declaration.threshold; not counted
                'tax_ids': False,
            }),
        ])
        # The amounts have not changed since the invoice has not been posted yet.
        self.assertRecordValues(declaration, [{
            'invoiced': 0.0,
            'not_yet_invoiced': 2000.0,
            'remaining': -1000.0,
        }])

        # The warning has the updated values though
        self.assertEqual(
            invoice.l10n_it_edi_doi_warning,
            "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 2,000.00\xa0€, this document included.\n"
            "Invoiced: 1,000.00\xa0€; Not Yet Invoiced: 2,000.00\xa0€"
        )

        invoice.action_post()
        self.assertRecordValues(declaration, [{
            'invoiced': 1000.0,
            'not_yet_invoiced': 2000.0,
            'remaining': -2000.0,
        }])

    @freeze_time('2019-12-31')  # declaration.end_date
    def test_overinvoiced_sale_order_and_credit_note(self):
        """
        Ensure the amounts and warnings are computed correctly in the following flow:
          * We create a quotation and confirm it to sales order.
          * Then we invoice the sales order in 2 downpayment invoices of 50% each.
            I.e. the Invoiced amount should be transferred correctly from Not Yet Invoiced to Invoiced
          * We increase the amount on one of the invoices s.t. it exceeds the sales order amount.
            I.e. the Invoiced amount increases more than the Not Yet Invoiced amount is lowered
          * We reverse the invoice exceeding the sales order amount by creating a credit note.
            I.e. check the amounts are computed correctly on the warning.
        """

        declaration = self.declaration_1000
        declaration_tax = declaration.company_id.l10n_it_edi_doi_tax_id

        # Add an order that is not used in the rest of this test.
        # This way we can always show the warning and that this amount will not be removed from Not Yet Invoiced.
        independent_order = self.create_sale_order(declaration, [
            Command.create({
                'name': 'declaration line',
                'product_id': self.product_1.id,
                'price_unit': 2000.0,  # > declaration.threshold
                'tax_id': [Command.set(declaration_tax.ids)],
            }),
            Command.create({
                'name': 'not a declaration line',
                'product_id': self.product_1.id,
                'price_unit': 2000.0,  # > declaration.threshold; not counted
                'tax_id': False,
            }),
        ])
        independent_order.action_confirm()
        self.assertRecordValues(declaration, [{
            'invoiced': 0.0,
            'not_yet_invoiced': 2000.0,  # 2000 "base" from independent_order
            'remaining': -1000.0,
        }])

        order = self.create_sale_order(declaration, [
            Command.create({
                'name': 'declaration line',
                'product_id': self.product_1.id,
                'price_unit': 1000.0,  # == declaration.threshold
                'tax_id': [Command.set(declaration_tax.ids)],
            }),
            Command.create({
                'name': 'not a declaration line',
                'product_id': self.product_1.id,
                'price_unit': 2000.0,  # > declaration.threshold; not counted
                'tax_id': False,
            }),
        ])
        order.action_confirm()
        self.assertRecordValues(declaration, [{
            'invoiced': 0.0,
            'not_yet_invoiced': 3000.0,  # 2000 "base" + 1000 from `order`
            'remaining': -2000.0,
        }])

        for i in range(2):
            self.env['sale.advance.payment.inv'].with_context({
                   'active_model': 'sale.order',
                   'active_ids': [order.id],
                   'active_id': order.id,
                   'default_journal_id': self.company_data_2['default_journal_sale'].id,
               }).create({
                   'advance_payment_method': 'percentage',
                   'amount': 50,
               }).create_invoices()

        invoice = order.invoice_ids[0]

        # The invoice just moves amount from `not_invoiced_yet` to `invoiced`.
        # It does not lower the remaining ammount.
        self.assertEqual(
            invoice.l10n_it_edi_doi_warning,
            "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 2,000.00\xa0€, this document included.\n"
            "Invoiced: 500.00\xa0€; Not Yet Invoiced: 2,500.00\xa0€"
        )

        invoice.invoice_line_ids[0].price_unit = 2000  # 1000 more than the sales order declaration amount
        # Changing an invoice line does not affect the not yet invoiced amount of sale order lines not linked to that line
        self.assertEqual(
            invoice.l10n_it_edi_doi_warning,
            "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 3,500.00\xa0€, this document included.\n"
            "Invoiced: 2,000.00\xa0€; Not Yet Invoiced: 2,500.00\xa0€"
        )
        invoice.action_post()
        self.assertRecordValues(declaration, [{
            'invoiced': 2000.0,  # 2000 from invoice
            'not_yet_invoiced': 2000.0,  # 2000 "base"
            'remaining': -3000.0,
        }])

        invoice2 = order.invoice_ids[1]
        invoice2.action_post()
        self.assertEqual(
            invoice2.l10n_it_edi_doi_warning,
            "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 3,500.00\xa0€, this document included.\n"
            "Invoiced: 2,500.00\xa0€; Not Yet Invoiced: 2,000.00\xa0€"
        )
        self.assertRecordValues(declaration, [{
            'invoiced': 2500.0,  # 2000 + 500 from the 2 downpayment invoices
            'not_yet_invoiced': 2000.0,  # 2000 "base"
            'remaining': -3500.0,
        }])

        # Reverse the invoice via a credit note
        self.env['account.move.reversal'].with_company(self.company).create(
            {
                'move_ids': [Command.set((invoice.id,))],
                'date': '2019-12-31',
                'journal_id': invoice.journal_id.id,
            }
        ).reverse_moves()

        # The invoice we reversed invoiced more than the sales order amount.
        credit_note = invoice.reversal_move_ids
        self.assertEqual(
            credit_note.l10n_it_edi_doi_warning,
            "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 2,000.00\xa0€, this document included.\n"
            "Invoiced: 500.00\xa0€; Not Yet Invoiced: 2,500.00\xa0€"
        )

        credit_note.action_post()
        self.assertRecordValues(declaration, [{
            'invoiced': 500,  # 1 downpayment of 50% on 1000 sale order
            'not_yet_invoiced': 2500,  # 2000 ("base") + 500 (left on sale order)
            'remaining': -2000,
        }])

    @freeze_time('2019-12-31')  # declaration.end_date
    def test_consolidated_billing(self):
        """
        Ensure the amounts and warnings are computed correctly in the following flow:
          1. We create multiple quotations with 1 line each with qty 2 and confirm them all to sales order.
          2. We create a single invoice for the SOs from the previous step.
             There is one line per SO.
          3. We change the amount on the one of the invoice lines without changing the qty.
          4. We increase the qty on one line.
          5. We decrease the qty on another line (not from step 4)
        I.e. we check that:
          * The not yet invoiced amount on the SO linked to the line from step (3) is still 0.
          * The lines from step (4) and (5) do not affect each other
          * Increasing the qty on line (5) to be higher than the SO amount does not lead to a negative amount on the linked SO.
        """

        declaration = self.declaration_1000
        declaration_tax = declaration.company_id.l10n_it_edi_doi_tax_id

        orders = self.env['sale.order'].create([
            self.get_sale_order_vals(declaration, [
                Command.create({
                    'name': 'declaration line',
                    'product_id': self.product_1.id,
                    'product_uom_qty': 2,
                    'price_unit': 2000.0,  # > declaration.threshold
                    'tax_id': [Command.set(declaration_tax.ids)],
                }),
            ]) for dummy in range(3)
        ])
        orders.action_confirm()
        self.assertRecordValues(declaration, [{
            'invoiced': 0.0,
            'not_yet_invoiced': 12000.0,
            'remaining': -11000.0,
        }])

        invoice = orders._create_invoices()
        self.assertRecordValues(declaration, [{
            'invoiced': 0.0,
            'not_yet_invoiced': 12000.0,
            'remaining': -11000.0,
        }])
        self.assertEqual(
            invoice.l10n_it_edi_doi_warning,
            "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 11,000.00\xa0€, this document included.\n"
            "Invoiced: 12,000.00\xa0€; Not Yet Invoiced: 0.00\xa0€"
        )

        invoice.invoice_line_ids[0].price_unit = 1000
        # in the warning:
        #   * invoiced amount decreases by 2000 (since we reduced the price_unit by 1000)
        #   * not yet invoiced amount stays the same (all quantities still invoiced)
        self.assertEqual(
            invoice.l10n_it_edi_doi_warning,
            "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 9,000.00\xa0€, this document included.\n"
            "Invoiced: 10,000.00\xa0€; Not Yet Invoiced: 0.00\xa0€"
        )
        self.assertRecordValues(declaration, [{
            'invoiced': 0.0,
            'not_yet_invoiced': 12000.0,
            'remaining': -11000.0,
        }])

        invoice.invoice_line_ids[1].quantity = 1
        # in the warning: 1 qty (2000 €) moves from invoiced to net yet invoiced
        self.assertEqual(
            invoice.l10n_it_edi_doi_warning,
            "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 9,000.00\xa0€, this document included.\n"
            "Invoiced: 8,000.00\xa0€; Not Yet Invoiced: 2,000.00\xa0€"
        )
        self.assertRecordValues(declaration, [{
            'invoiced': 0.0,
            'not_yet_invoiced': 12000.0,
            'remaining': -11000.0,
        }])

        invoice.invoice_line_ids[2].quantity = 3
        # in the warning:
        #   * invoiced amount increases by 2000 (since we increase the quantity by 1)
        #   * not yet invoiced amount stays the same (all quantities still invoiced)
        self.assertEqual(
            invoice.l10n_it_edi_doi_warning,
            "Pay attention, the threshold of your Declaration of Intent test 2019-threshold 1000 of 1,000.00\xa0€ is exceeded by 11,000.00\xa0€, this document included.\n"
            "Invoiced: 10,000.00\xa0€; Not Yet Invoiced: 2,000.00\xa0€"
        )
        self.assertRecordValues(declaration, [{
            'invoiced': 0.0,
            'not_yet_invoiced': 12000.0,
            'remaining': -11000.0,
        }])

        invoice.action_post()
        # Same values as in the last warning
        self.assertRecordValues(declaration, [{
            'invoiced': 10000.0,
            'not_yet_invoiced': 2000.0,
            'remaining': -11000.0,
        }])
