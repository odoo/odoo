from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon

SINGLE_ORDER_MESSAGE = (
    "Taxable and non-taxable items cannot be combined in the same invoice for a registered customer."
    " Please create a separate invoice for the non-taxable items."
)
MULTI_ORDER_MESSAGE = (
    "Some of the selected orders contain both taxable and non-taxable items. Please create separate invoices"
    " for the non-taxable items."
)


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nInSaleMixedTaxWarning(L10nInTestInvoicingCommon):

    @classmethod
    def get_default_groups(cls):
        return super().get_default_groups() | cls.quick_ref('sales_team.group_sale_salesman')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tcs = cls.env['account.chart.template'].ref('tcs_1_us_394_1_1_liq')
        cls.service_delivered, cls.service_ordered = cls.env['product.product'].create([
            {'name': "Service on delivered quantities", 'type': 'service', 'invoice_policy': 'delivery'},
            {'name': "Service on ordered quantities", 'type': 'service', 'invoice_policy': 'order'},
        ])

    def _line(self, taxes, product=None):
        return Command.create({
            'product_id': (product or self.product_a).id,
            'price_unit': 100.0,
            'tax_ids': [Command.set(taxes.ids)],
        })

    def _create_order(self, *lines, partner=None, **values):
        order = self.env['sale.order'].create({
            'partner_id': (partner or self.partner_a).id,
            'order_line': list(lines),
            **values,
        })
        order.action_confirm()
        return order

    def _wizard_form(self, orders):
        return Form(self.env['sale.advance.payment.inv'].with_context(
            active_model='sale.order',
            active_ids=orders.ids,
        ))

    def test_mixed_order_warning(self):
        order = self._create_order(self._line(self.igst_sale_18), self._line(self.exempt))
        wizard_form = self._wizard_form(order)
        self.assertEqual(wizard_form.l10n_in_warning, {
            'l10n_in_mixed_tax_supply': {'message': SINGLE_ORDER_MESSAGE, 'level': 'warning'},
        })
        # The warning does not block the invoice creation.
        wizard_form.save().create_invoices()
        self.assertEqual(order.invoice_ids.invoice_line_ids.tax_ids, self.igst_sale_18 + self.exempt)

    def test_no_warning(self):
        consumer = self.env['res.partner'].create({'name': "Consumer", 'country_id': self.country_in.id})
        for label, order in (
            ("taxable lines only", self._create_order(self._line(self.igst_sale_18), self._line(self.sgst_sale_5))),
            ("unregistered customer", self._create_order(
                self._line(self.igst_sale_18), self._line(self.exempt), partner=consumer,
            )),
            # A TCS line is not a GST supply: it does not count as taxable.
            ("TCS only line", self._create_order(self._line(self.exempt), self._line(self.tcs))),
        ):
            with self.subTest(case=label):
                self.assertEqual(self._wizard_form(order).l10n_in_warning, {})
        with self.subTest(case="company not under the regular GST scheme"):
            order = self._create_order(self._line(self.igst_sale_18), self._line(self.exempt))
            order.company_id.sudo().l10n_in_gst_registration_type = 'composition'
            self.assertEqual(self._wizard_form(order).l10n_in_warning, {})

    def test_consolidated_billing(self):
        orders = self._create_order(self._line(self.igst_sale_18)) + self._create_order(self._line(self.exempt))
        wizard_form = self._wizard_form(orders)
        # Both orders are merged into one mixed invoice.
        warning = wizard_form.l10n_in_warning['l10n_in_mixed_tax_supply']
        self.assertEqual(warning['message'], MULTI_ORDER_MESSAGE)
        self.assertEqual(warning['action']['domain'], [['id', 'in', orders.ids]])
        wizard_form.consolidated_billing = False
        self.assertEqual(wizard_form.l10n_in_warning, {})

        with self.subTest(case="different delivery address: separate invoices"):
            delivery_address = self.env['res.partner'].create({
                'name': "Warehouse",
                'type': 'delivery',
                'parent_id': self.partner_a.id,
            })
            taxable_order = self._create_order(self._line(self.igst_sale_18), partner_shipping_id=self.partner_a.id)
            exempt_order = self._create_order(self._line(self.exempt), partner_shipping_id=delivery_address.id)
            self.assertEqual(self._wizard_form(taxable_order + exempt_order).l10n_in_warning, {})
        with self.subTest(case="not consolidated: only the mixed order is listed"):
            mixed_order = self._create_order(self._line(self.igst_sale_18), self._line(self.exempt))
            wizard_form = self._wizard_form(mixed_order + orders)
            wizard_form.consolidated_billing = False
            warning = wizard_form.l10n_in_warning['l10n_in_mixed_tax_supply']
            self.assertEqual(warning['action']['domain'], [['id', 'in', mixed_order.ids]])

    def test_down_payment(self):
        # The taxable service is not delivered yet: only the exempt line can be invoiced, but a down payment
        # is computed on all the lines.
        order = self._create_order(
            self._line(self.igst_sale_18, product=self.service_delivered),
            self._line(self.exempt),
        )
        wizard_form = self._wizard_form(order)
        self.assertEqual(wizard_form.l10n_in_warning, {})
        wizard_form.advance_payment_method = 'downpayment'
        self.assertEqual(wizard_form.l10n_in_warning['l10n_in_mixed_tax_supply']['message'], SINGLE_ORDER_MESSAGE)

        with self.subTest(case="fixed amount tax, not on the down payment"):
            fixed_tax = self.igst_sale_18.copy({'name': "Fixed cess", 'amount_type': 'fixed', 'amount': 5.0})
            order = self._create_order(self._line(fixed_tax), self._line(self.exempt))
            wizard_form = self._wizard_form(order)
            wizard_form.advance_payment_method = 'downpayment'
            self.assertEqual(wizard_form.l10n_in_warning, {})

    def test_invoice_overages(self):
        # 1 exempt unit delivered over the ordered quantity: invoiced only with the "Invoice overages" option.
        order = self._create_order(
            self._line(self.igst_sale_18),
            self._line(self.exempt, product=self.service_ordered),
        )
        taxable_line, exempt_line = order.order_line
        exempt_line.qty_delivered = 1.0
        order._create_invoices()
        taxable_line.product_uom_qty = 2.0
        exempt_line.qty_delivered = 2.0
        # The option is only written on the order when the dialog is saved.
        wizard_form = self._wizard_form(order)
        self.assertTrue(wizard_form.invoice_overages)
        self.assertFalse(order.invoice_overages)
        self.assertEqual(wizard_form.l10n_in_warning['l10n_in_mixed_tax_supply']['message'], SINGLE_ORDER_MESSAGE)
        wizard_form.invoice_overages = False
        self.assertEqual(wizard_form.l10n_in_warning, {})
