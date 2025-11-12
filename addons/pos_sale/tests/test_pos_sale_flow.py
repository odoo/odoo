# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.fields import Command
from odoo.tests import tagged
from odoo.tools import format_date
from odoo.addons.payment.tests.common import PaymentCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
import uuid


class PoSSaleSyncCommon:
    """Helpers syncing the PoS orders that the frontend creates from a sale order."""

    def _prepare_pos_order_data(self, lines, partner=False, payment_method=False, to_invoice=False, paid=True, **order_values):
        """Build the values of the PoS order selling LINES, as the frontend sends them.

        Each line is described by a dict: the ``product`` it sells, optionally its
        ``qty``, ``price_unit``, ``discount``, ``taxes`` and any ``extra_values``
        to set on the pos.order.line (e.g. the settled sale order line).
        """
        self.main_pos_config.open_ui()
        session = self.main_pos_config.current_session_id
        currency = session.currency_id
        payment_method = payment_method or self.main_pos_config.payment_method_ids[0]
        order_uuid = str(uuid.uuid4())
        amount_total = 0
        amount_tax = 0
        order_lines = []

        for line in lines:
            product = line['product']
            qty = line.get('qty', 1)
            price_unit = line.get('price_unit', product.lst_price)
            discount = line.get('discount', 0)
            taxes = line.get(
                'taxes',
                product.taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(self.env.company))
            )
            tax_values = taxes.compute_all(
                price_unit * (1 - discount / 100),
                currency,
                qty,
                product=product,
                partner=partner,
            ) if taxes else {
                'total_excluded': price_unit * qty,
                'total_included': price_unit * qty,
            }
            amount_total += tax_values['total_included']
            amount_tax += tax_values['total_included'] - tax_values['total_excluded']
            order_lines.append(Command.create({
                'discount': discount,
                'price_unit': price_unit,
                'product_id': product.id,
                'price_subtotal': tax_values['total_excluded'],
                'price_subtotal_incl': tax_values['total_included'],
                'qty': qty,
                'tax_ids': [Command.set(taxes.ids)],
                **line.get('extra_values', {}),
            }))

        return {
            'amount_paid': amount_total if paid else 0,
            'amount_return': 0,
            'amount_tax': amount_tax,
            'amount_total': amount_total,
            'company_id': self.env.company.id,
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'fiscal_position_id': False,
            'lines': order_lines,
            'name': 'Order %s' % order_uuid,
            'partner_id': partner and partner.id,
            'payment_ids': [Command.create({
                'amount': amount_total,
                'name': fields.Datetime.now(),
                'payment_method_id': payment_method.id,
            })] if paid else [],
            'pricelist_id': self.main_pos_config.available_pricelist_ids[0].id,
            'session_id': session.id,
            'to_invoice': to_invoice,
            'user_id': self.env.uid,
            'uuid': order_uuid,
            **order_values,
        }

    def _create_pos_order(self, lines, **kwargs):
        """Create the unpaid PoS order selling LINES, as the backend does."""
        return self.env['pos.order'].create(self._prepare_pos_order_data(lines, paid=False, **kwargs))

    def _sync_paid_pos_order(self, lines, **kwargs):
        """Sync a paid PoS order, as the frontend does once an order is validated."""
        order_data = self._prepare_pos_order_data(lines, **kwargs)
        self.env['pos.order'].sync_from_ui([order_data])
        return self.env['pos.order'].search([('uuid', '=', order_data['uuid'])]).id

    def _sync_paid_pos_downpayment(self, sale_order, lines, percentage=0, to_invoice=False):
        """Sync the paid PoS order that applying a down payment on SALE_ORDER creates.

        The frontend adds one down payment line per set of taxes used by the sale
        order lines, so each line is described by its ``price_unit`` and its
        ``taxes``. The sale order lines sharing those taxes are the ones detailed
        on the down payment line.
        """
        down_payment_lines = []
        for line in lines:
            taxes = line.get('taxes') or self.env['account.tax']
            detailed_so_lines = sale_order.order_line.filtered(
                lambda l: not l.display_type and not l.is_downpayment and l.tax_ids == taxes
            )
            down_payment_lines.append({
                'product': self.main_pos_config.down_payment_product_id,
                'qty': 1,
                'price_unit': line['price_unit'],
                'taxes': taxes,
                'extra_values': {
                    'sale_order_origin_id': sale_order.id,
                    'down_payment_details': str([{
                        'product_name': so_line.product_id.display_name,
                        'product_uom_qty': so_line.product_uom_qty,
                        'price_unit': so_line.price_unit,
                        'total': so_line.price_total,
                        'percentage_value': percentage,
                    } for so_line in detailed_so_lines]),
                    'extra_tax_data': {'computation_key': 'down_payment'},
                },
            })
        return self._sync_paid_pos_order(
            down_payment_lines, partner=sale_order.partner_id, to_invoice=to_invoice)


class TestPoSSale(PoSSaleSyncCommon, TestPointOfSaleHttpCommon):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pos_user.write({
            'group_ids': [
                (4, cls.env.ref('sales_team.group_sale_salesman_all_leads').id),
            ]
        })

    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        return groups | cls.quick_ref('sales_team.group_sale_salesman_all_leads')

    def test_downpayment_refund(self):
        #create a sale order
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_uom_qty': 1,
                'price_unit': 100,
                'tax_ids': False,
            })],
        })
        sale_order.action_confirm()
        #set downpayment product in pos config
        self.downpayment_product = self.env['product.product'].create({
            'name': 'Down Payment',
            'available_in_pos': True,
            'type': 'service',
            'taxes_id': [],
        })
        self.main_pos_config.write({
            'down_payment_product_id': self.downpayment_product.id,
        })
        # Apply a 10% down payment, then refund it: the refund line only carries
        # the refunded PoS line, as the ticket screen creates it.
        order_id = self._sync_paid_pos_downpayment(sale_order, [{'price_unit': 10}], percentage=10)
        self._sync_paid_pos_order([{
            'product': self.downpayment_product,
            'qty': -1,
            'price_unit': 10,
            'taxes': self.env['account.tax'],
            'extra_values': {
                'refunded_orderline_id': self.env['pos.order'].browse(order_id).lines.id,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            },
        }], partner=sale_order.partner_id)

        self.assertEqual(len(sale_order.order_line), 3)
        self.assertEqual(sale_order.order_line[2].qty_invoiced, 0)
        self.assertEqual(sale_order.order_line[2].price_unit, 0)
        self.assertEqual(sale_order.amount_invoiced, 0)
        payment = self.env['sale.advance.payment.inv'].with_context(
            active_model='sale.order',
            active_ids=sale_order.ids,
            active_id=sale_order.id,
        ).create({
            'advance_payment_method': 'delivered',
        })
        payment.create_invoices()
        self.assertEqual(sale_order.invoice_ids.amount_untaxed, 100)

    def test_pos_not_groupable_product(self):
        #Create a UoM Category that is not pos_groupable
        uom = self.env['uom.uom'].create({
            'name': 'Test',
        })
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
            'uom_id': uom.id,
        })
        #create a sale order with product_a
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 3.5,
                'price_unit': 8,  # manually set a different price than the lst_price
                'discount': 10,
            })],
        })
        self.assertEqual(sale_order.amount_total, 28.98)  # 3.5 * 8 * 1.15 * 90%

    def test_order_sales_count(self):
        partner_1 = self.env['res.partner'].create({'name': 'Test Partner'})
        order = self._create_pos_order([{
            'product': self.desk_pad.product_variant_id,
            'taxes': self.env['account.tax'],
            'extra_values': {'name': "OL/0001"},
        }], partner=partner_1)
        current_session = order.session_id
        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': order.amount_total,
            'payment_method_id': current_session.payment_method_ids[0].id,
        })
        order_payment.with_context(**payment_context).check()

        current_session.close_session_from_ui()
        self.env.flush_all()
        self.env.user.group_ids += self.quick_ref('sales_team.group_sale_salesman')
        self.assertEqual(self.desk_pad.sales_count, 1)

    def test_untaxed_invoiced_amount(self):
        """Make sure that orders invoiced in the pos gets their untaxed invoiced
           amount updated accordingly"""

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 10.0,
            'taxes_id': [],
        })

        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'available_in_pos': True,
            'lst_price': 5.0,
            'taxes_id': [],
        })

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            }), (0, 0, {
                'product_id': product_b.id,
                'name': product_b.name,
                'product_uom_qty': 1,
                'price_unit': product_b.lst_price,
            })],
        })
        sale_order.action_confirm()
        self._sync_paid_pos_order([{
            'product': product_a,
            'price_unit': 10,
            'taxes': self.env['account.tax'],
            'extra_values': {
                'sale_order_line_id': sale_order.order_line[0].id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=partner_test, to_invoice=True)
        self.assertEqual(sale_order.order_line[0].untaxed_amount_invoiced, 10, "Untaxed invoiced amount should be 10")
        self.assertEqual(sale_order.order_line[1].untaxed_amount_invoiced, 0, "Untaxed invoiced amount should be 0")

    def test_order_does_not_remain_in_list(self):
        """Verify that a paid order is not proposed anymore in the orders list"""

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.whiteboard_pen.product_variant_id.id,
                'name': self.whiteboard_pen.name,
                'product_uom_qty': 1,
                'price_unit': 100,
            })],
        })

        sale_order.action_confirm()

        self._sync_paid_pos_order([{
            'product': self.whiteboard_pen.product_variant_id,
            'qty': 1,
            'price_unit': 100,
            'extra_values': {
                'sale_order_line_id': sale_order.order_line.id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=sale_order.partner_id, to_invoice=True)

        # The orders list only shows sale orders with an unpaid amount.
        self.assertEqual(sale_order.amount_unpaid, 0.0)

    def test_settle_draft_order_service_product(self):
        """
        Checks that, when settling a draft order (quotation), the quantity set on the corresponding
        PoS order, for service products, is set correctly.
        """

        product_a = self.env['product.product'].create({
            'name': 'Test service product',
            'available_in_pos': True,
            'type': 'service',
            'invoice_policy': 'order',
            'lst_price': 50.0,
            'taxes_id': [],
        })

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })],
        })

        self.assertEqual(sale_order.state, 'draft')

        self._sync_paid_pos_order([{
            'product': product_a,
            'qty': 1,
            'price_unit': product_a.lst_price,
            'extra_values': {
                'sale_order_line_id': sale_order.order_line.id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=partner_test)
        self.assertEqual(sale_order.state, 'sale')

    def test_so_with_downpayment(self):
        self.product_a.available_in_pos = True
        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_a.name,
                    'product_id': self.product_a.id,
                    'product_uom_qty': 10.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()

        self.env['sale.advance.payment.inv'].sudo().create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 20,
            'sale_order_ids': so.ids,
        }).create_invoices()
        # Invoice the delivered part from the down payment
        down_payment_invoices = so.invoice_ids
        down_payment_invoices.action_post()
        self.main_pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")
        self.main_pos_config.down_payment_product_id.write({'active': True})

        # The PoS settles the down payment as a negative line, which is covered
        # by the HOOT scenario.
        self.assertEqual(so.amount_unpaid, 980)
        down_payment_line = so.order_line.filtered(lambda line: line.is_downpayment and not line.display_type)
        self.assertEqual(down_payment_line.price_unit, 20)
        self.assertEqual(down_payment_line.qty_to_invoice, -1)

    def test_downpayment_with_taxed_product(self):
        tax_1 = self.env['account.tax'].create({
            'name': '10',
            'amount': 10,
        })

        tax_2 = self.env['account.tax'].create({
            'name': '5 incl',
            'amount': 5,
            'price_include_override': 'tax_included',
        })

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 10.0,
            'taxes_id': [tax_1.id],
        })

        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'available_in_pos': True,
            'lst_price': 5.0,
            'taxes_id': [tax_2.id],
        })

        product_c = self.env['product.product'].create({
            'name': 'Product C',
            'available_in_pos': True,
            'lst_price': 15.0,
            'taxes_id': [],
        })
        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            }), (0, 0, {
                'product_id': product_b.id,
                'name': product_b.name,
                'product_uom_qty': 1,
                'price_unit': product_b.lst_price,
            }), (0, 0, {
                'product_id': product_c.id,
                'name': product_c.name,
                'product_uom_qty': 1,
                'price_unit': product_c.lst_price,
            })],
        })
        sale_order.action_confirm()

        self.downpayment_product = self.env['product.product'].create({
            'name': 'Down Payment',
            'available_in_pos': True,
            'type': 'service',
            'taxes_id': [],
        })
        self.main_pos_config.write({
            'down_payment_product_id': self.downpayment_product.id,
        })
        # A 20% down payment is split in one line per tax: 20% of the 11, 5 and 15
        # tax included totals of the sale order lines.
        self._sync_paid_pos_downpayment(sale_order, [
            {'price_unit': 2.0, 'taxes': tax_1},
            {'price_unit': 1.0, 'taxes': tax_2},
            {'price_unit': 3.0},
        ], percentage=20, to_invoice=True)

        # We check the content of the invoice to make sure Product A/B/C only appears only once
        legal_documents = self.env['pos.order'].search([]).account_move._get_invoice_legal_documents('pdf', allow_fallback=True)
        self.assertEqual(len(legal_documents), 1)
        invoice_pdf_content = legal_documents[0]['content'].decode()
        self.assertEqual(invoice_pdf_content.count('Down Payment of 20%'), 3)

        downpayment_lines = sale_order.order_line.filtered(lambda l: l.product_id == self.downpayment_product)
        self.assertEqual(len(downpayment_lines), 3)
        for order_line in downpayment_lines:
            order_line = order_line.with_context(lang=partner_test.lang)
            self.assertIn(format_date(order_line.env, order_line.order_id.date_order), order_line.name)

    def test_settle_so_with_pos_downpayment(self):
        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_a.name,
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()

        # Apply a 10 down payment
        self.main_pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")
        self._sync_paid_pos_order([{
            'product': self.main_pos_config.down_payment_product_id,
            'qty': 1,
            'price_unit': 10,
            'taxes': self.env['account.tax'],
            'extra_values': {
                'sale_order_origin_id': so.id,
                'down_payment_details': str([{
                    'product_name': self.product_a.display_name,
                    'product_uom_qty': 1.0,
                    'price_unit': 100,
                    'total': 100,
                    'percentage_value': 10,
                }]),
                'extra_tax_data': {'computation_key': 'down_payment'},
            },
        }], partner=so.partner_id)

        invoice = so._create_invoices(final=True)
        invoice.action_post()
        self.assertEqual(invoice.amount_total, 90)

    def test_downpayment_invoice_line_name(self):
        """When a down payment is invoiced straight from the POS, the invoice is
        generated inside super().sync_from_ui, before the down-payment POS line
        gets linked to a sale order line. At that point sale_order_line_id is
        empty, so the invoice line name must not fall back to False (a False name
        breaks the UBL/e-invoice export)."""
        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_a.name,
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()

        self.main_pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")
        self._sync_paid_pos_downpayment(so, [{'price_unit': 10}], percentage=10, to_invoice=True)

        pos_order = so.pos_order_line_ids.order_id
        invoice_line = pos_order.account_move.invoice_line_ids.filtered(
            lambda l: l.product_id == self.main_pos_config.down_payment_product_id)
        self.assertTrue(invoice_line, "The down payment should have been invoiced")
        self.assertTrue(invoice_line.name, "The down-payment invoice line must have a name")

    def test_order_sale_team(self):
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'available_in_pos': True,
            'lst_price': 100.0,
            'taxes_id': False,
        })
        sale_team = self.env['crm.team'].create({'name': 'Test team'})
        self.main_pos_config.write({'crm_team_id': sale_team})
        order_id = self._sync_paid_pos_order([{'product': product}])
        order = self.env['pos.order'].browse(order_id)
        self.assertEqual(order.crm_team_id, sale_team)

    def test_downpayment_amount_to_invoice(self):
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 100.0,
            'taxes_id': [],
        })
        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.main_pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")
        self._sync_paid_pos_order([{
            'product': self.main_pos_config.down_payment_product_id,
            'qty': 1,
            'price_unit': 20,
            'taxes': self.env['account.tax'],
            'extra_values': {
                'sale_order_origin_id': sale_order.id,
                'down_payment_details': str([{
                    'product_name': product_a.display_name,
                    'product_uom_qty': 1,
                    'price_unit': 100,
                    'total': 100,
                    'percentage_value': 0,
                }]),
                'extra_tax_data': {'computation_key': 'down_payment'},
            },
        }], partner=partner_test)
        self.assertEqual(sale_order.amount_to_invoice, 80.0, "Downpayment amount not considered!")
        self.assertEqual(sale_order.amount_invoiced, 20.0, "Downpayment amount not considered!")

        self.assertEqual(sale_order.order_line[2].price_unit, 20)

        # Update delivered quantity of SO line
        sale_order.order_line[0].write({'qty_delivered': 1.0})

        # Let's do the invoice for the remaining amount
        self.env['sale.advance.payment.inv'].sudo().with_context({
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }).create({}).create_invoices()

        # Confirm all invoices
        sale_order.invoice_ids.action_post()
        self.assertEqual(sale_order.order_line[2].price_unit, 20)

    def test_downpayment_invoice(self):
        """This test check that users that don't have the pos user group can invoice downpayments"""
        self.env['res.partner'].create({'name': 'Test Partner AAA'})

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner BBB'}).id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_uom_qty': 1,
                'price_unit': 100,
                'tax_ids': False,
            })],
        })
        sale_order.action_confirm()

        self.env['sale.advance.payment.inv'].sudo().with_context({
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 100,
        }).create_invoices()

        selected_groups = self.user.group_ids
        self.user.group_ids = self.env.ref('account.group_account_manager') + self.env.ref('sales_team.group_sale_salesman_all_leads')

        downpayment_line = sale_order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
        downpayment_invoice = downpayment_line.order_id.order_line.invoice_lines.move_id
        downpayment_invoice.action_post()
        self.user.group_ids = selected_groups
        self.assertEqual(downpayment_line.price_unit, 100)

    def test_downpayment_invoice_link(self):
        # Test to check if the final invoice generated from an SO is correctly linked to the downpayment invoice.

        tax = self.env['account.tax'].create({
            'name': 'Base Tax',
            'amount': 15,
        })
        customer = self.env['res.partner'].create({'name': 'Test Partner A'})
        sale_orders = self.env['sale.order'].create([{
            'partner_id': customer.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_uom_qty': 1,
                'price_unit': 100,
                'tax_ids': [tax.id],
            })],
        } for _ in range(2)])

        sale_orders.action_confirm()

        # CASE 1: downpayment generated in POS, invoice settled in backend
        sale_order = sale_orders[1]
        self.main_pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")
        # 10% of the 115 tax included total of the sale order
        self._sync_paid_pos_downpayment(
            sale_order, [{'price_unit': 10, 'taxes': tax}], percentage=10, to_invoice=True)

        downpayment_invoice = sale_order.pos_order_line_ids.order_id.account_move
        self.assertTrue(downpayment_invoice._is_downpayment())

        self.env['sale.advance.payment.inv'].with_context({
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }).create({}).create_invoices()

        final_invoice_downpayment_line = sale_order.invoice_ids.invoice_line_ids.filtered(lambda r: r.quantity < 0)

        self.assertEqual(
            final_invoice_downpayment_line._get_downpayment_lines(),
            downpayment_invoice.invoice_line_ids,
        )

        final_invoice_downpayment_line.move_id.action_post()
        self.assertEqual(sale_order.amount_to_invoice, 0.0)

        # CASE 2: downpayment generated in POS, invoice settled in POS
        sale_order = sale_orders[0]
        self._sync_paid_pos_downpayment(
            sale_order, [{'price_unit': 10, 'taxes': tax}], percentage=10, to_invoice=True)

        downpayment_invoice = sale_order.pos_order_line_ids.order_id.account_move
        self.assertTrue(downpayment_invoice._is_downpayment())

        # Settling the sale order in the PoS loads its product line and deducts
        # the down payment that was applied on it.
        downpayment_so_line = sale_order.order_line.filtered(
            lambda l: l.is_downpayment and not l.display_type)
        self._sync_paid_pos_order([{
            'product': self.product_a,
            'qty': 1,
            'price_unit': 100,
            'taxes': tax,
            'extra_values': {
                'sale_order_line_id': sale_order.order_line[0].id,
                'sale_order_origin_id': sale_order.id,
            },
        }, {
            'product': self.main_pos_config.down_payment_product_id,
            'qty': -1,
            'price_unit': 10,
            'taxes': tax,
            'extra_values': {
                'sale_order_line_id': downpayment_so_line.id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=customer, to_invoice=True)

        final_invoice_downpayment_line = sale_order.pos_order_line_ids[-1].order_id.account_move.invoice_line_ids

        self.assertEqual(
            final_invoice_downpayment_line._get_downpayment_lines(),
            downpayment_invoice.invoice_line_ids,
        )
        for line in downpayment_invoice.invoice_line_ids.filtered(self.main_pos_config.down_payment_product_id.id == "product_id"):
            self.assertTrue(line.is_downpayment)

    def test_draft_pos_order_linked_sale_order(self):
        """This test create an order and settle it in the PoS. It will let the PoS order in draft state.
           As the order is still in draft state it shouldn't have impact on invoiced qty of the linked sale order.
        """

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
        })

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner BBB'}).id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()
        self._create_pos_order([{
            'product': product_a,
            'taxes': self.env['account.tax'],
            'extra_values': {
                'sale_order_line_id': sale_order.order_line.id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=sale_order.partner_id)
        self.assertEqual(sale_order.order_line.qty_invoiced, 0)
        self.assertEqual(sale_order.order_line.qty_delivered, 0)

    def test_edit_invoice_with_pos_order(self):
        partner_1 = self.env['res.partner'].create({'name': 'Test Partner'})

        pos_order = self._create_pos_order([{
            'product': self.desk_pad.product_variant_id,
            'taxes': self.env['account.tax'],
            'extra_values': {'name': "OL/0001"},
        }], partner=partner_1)

        # generate an invoice for pos order
        res = pos_order.action_pos_order_invoice()
        self.assertIn('res_id', res, "Invoice should be created")
        self.assertEqual(res['res_id'], pos_order.account_move.id)

        invoice = pos_order.account_move
        self.assertEqual(invoice.state, 'posted')

        # when clicking on draft button, it must keep posted because if the pos is open
        # we cannot cancel the invoice.
        invoice.button_draft()
        self.assertEqual(invoice.state, 'posted')

    def test_pos_order_and_invoice_amounts(self):
        payment_term = self.env['account.payment.term'].create({
            'name': "early_payment_term",
            'discount_percentage': 10,
            'discount_days': 10,
            'early_discount': True,
            'early_pay_discount_computation': 'mixed',
            'line_ids': [Command.create({
                'value': 'percent',
                'nb_days': 0,
                'value_amount': 100,
            })]
        })
        partner_test = self.env['res.partner'].create({
            'name': 'AAA - Test Partner invoice',
            'property_payment_term_id': payment_term.id,
        })

        tax = self.env['account.tax'].create({
            'name': 'Tax 10%',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        test_product = self.env['product.product'].create({
            'name': 'Product Test',
            'available_in_pos': True,
            'list_price': 1000,
            'taxes_id': [(6, 0, [tax.id])],
        })

        self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [
                Command.create({
                    'product_id': test_product.id,
                    'price_unit': test_product.lst_price,
                }),
            ],
        })

        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'POSSalePaymentScreenInvoiceOrder', login="accountman")

        order = self.env['pos.order'].search([('partner_id', '=', partner_test.id)], limit=1)
        self.assertTrue(order)
        self.assertEqual(order.partner_id, partner_test)

        invoice = self.env['account.move'].search([('invoice_origin', '=', order.pos_reference)], limit=1)
        self.assertTrue(invoice)
        self.assertFalse(invoice.invoice_payment_term_id)

        self.assertAlmostEqual(order.amount_total, invoice.amount_total, places=2, msg="Order and Invoice amounts do not match.")

    def test_amount_to_invoice(self):
        """
        Checks that the amount to invoice is updated correctly when paying an order in the PoS
        """

        product_a = self.env["product.product"].create(
            {
                "name": "Test service product",
                "available_in_pos": True,
                "type": "service",
                "invoice_policy": "order",
                "lst_price": 100.0,
                "taxes_id": [],
            }
        )

        partner_test = self.env["res.partner"].create({"name": "Test Partner"})

        sale_order = self.env["sale.order"].sudo().create(
            {
                "partner_id": partner_test.id,
                "order_line": [Command.create(
                        {
                            "product_id": product_a.id,
                            "name": product_a.name,
                            "product_uom_qty": 1,
                            "price_unit": product_a.lst_price,
                        },
                    )
                ],
            }
        )
        self.main_pos_config.open_ui()
        self.assertEqual(sale_order.amount_to_invoice, 100.0, "Amount to invoice should be 100.0")
        self._sync_paid_pos_order([{
            'product': self.product_a,
            'price_unit': 100.0,
            'taxes': self.env['account.tax'],
            'extra_values': {
                'sale_order_line_id': sale_order.order_line[0].id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=self.partner_a, to_invoice=True)
        self.assertEqual(sale_order.amount_to_invoice, 0.0, "Amount to invoice should be 0.0")

    def test_payment_terms_with_early_discount(self):
        """Make sure that orders invoiced in the pos do not use payment terms with early discount"""

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
            'taxes_id': [],
        })

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        payment_terms = self.env['account.payment.term'].create({
            'name': "Test Payment Term",
            'early_discount': True,
            'line_ids': [(0, 0, {
                'value': 'percent',
                'value_amount': 100,
                'nb_days': 45,
            })]
        })

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'payment_term_id': payment_terms.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()
        pos_order_id = self._sync_paid_pos_order([{
            'product': product_a,
            'price_unit': 10,
            'taxes': self.env['account.tax'],
            'extra_values': {
                'sale_order_line_id': sale_order.order_line[0].id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=partner_test, to_invoice=True)
        pos_order = self.env['pos.order'].browse(pos_order_id)
        self.assertFalse(pos_order.account_move.invoice_payment_term_id)

    def test_sale_order_fp_different_from_partner_one(self):
        """
        Tests that the fiscal position of the sale order is not the same as the partner's fiscal position.
        The PoS should always use the fiscal position of the sale order when settling it.
        """
        self.env.user.group_ids += self.quick_ref('sales_team.group_sale_salesman')
        tax = self.env['account.tax'].create({
            'name': 'Base Tax',
            'amount': 15,
        })
        fp_1 = self.env['account.fiscal.position'].create({
            'name': "Partner FP",
        })
        fp_2 = self.env['account.fiscal.position'].create({
            'name': "Sale Order FP",
        })
        tax_override_1 = self.env['account.tax'].create({
            'name': 'Tax Override 1',
            'amount': 100,
            'amount_type': 'percent',
            'fiscal_position_ids': [fp_1.id],
            'original_tax_ids': [tax.id],
        })
        tax_override_2 = self.env['account.tax'].create({
            'name': 'Tax Override 2',
            'amount': 0,
            'amount_type': 'percent',
            'fiscal_position_ids': [fp_2.id],
            'original_tax_ids': [tax.id],
        })
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 10.0,
            'taxes_id': [tax.id],
        })
        partner_test = self.env['res.partner'].create({
            'name': 'Test Partner',
            'property_account_position_id': fp_1.id,
        })
        sale_a = self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })]
        })
        sale_b = self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'fiscal_position_id': fp_2.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })]
        })
        self.main_pos_config.write({
            'tax_regime_selection': True,
            'default_fiscal_position_id': False,
        })
        self.assertEqual(sale_a.fiscal_position_id, fp_1, "Sale order should have the fiscal position of the partner")
        self.assertEqual(sale_a.amount_total, 20, "Sale order amount should be 20 with the tax override 1")
        self.assertEqual(sale_a.amount_untaxed, 10, "Sale order untaxed amount should be 10 with the tax override 1")
        self.assertEqual(sale_b.fiscal_position_id, fp_2, "Sale order should have the fiscal position set on the sale order")
        self.assertEqual(sale_b.amount_total, 10, "Sale order amount should be 10 with the tax override 2")
        self.assertEqual(sale_b.amount_untaxed, 10, "Sale order untaxed amount should be 10 with the tax override 2")
        self.start_pos_tour("test_sale_order_fp_different_from_partner_one", login="accountman")

        pos_order_a = self.env['pos.order'].search([('fiscal_position_id', '=', fp_1.id)], limit=1, order='id desc')
        pos_order_b = self.env['pos.order'].search([('fiscal_position_id', '=', fp_2.id)], limit=1, order='id desc')
        self.assertEqual(pos_order_a.amount_total, 20, "PoS order amount should be 20 with the tax override 1")
        self.assertEqual(pos_order_a.amount_tax, 10, "PoS order untaxed amount should be 10 with the tax override 1")
        self.assertEqual(pos_order_a.lines[0].tax_ids, tax_override_1, "PoS order should have the tax override 1")
        self.assertEqual(pos_order_b.amount_total, 10, "PoS order amount should be 10 with the tax override 2")
        self.assertEqual(pos_order_b.amount_tax, 0, "PoS order untaxed amount should be 10 with the tax override 2")
        self.assertEqual(pos_order_b.lines[0].tax_ids, tax_override_2, "PoS order should have the tax override 2")

    def test_settle_order_with_different_uom(self):
        """Verify that a qty has changed according to UOM"""
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
        })
        test_partner = self.env['res.partner'].create({'name': 'Test Partner'})
        # Create a sale order
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': test_partner.id,
            'order_line': [Command.create({
                    'product_id': product_a.id,
                    'name': product_a.name,
                    'product_uom_qty': 1,
                    'product_uom_id':  self.env.ref('uom.product_uom_dozen').id,
                    'price_unit': product_a.lst_price,
                })]
        })
        sale_order.action_confirm()

        # The PoS loads the sale order line converted in the unit of the product.
        converted_line = sale_order.order_line.read_converted()[0]
        self.assertEqual(converted_line['product_uom_qty'], 12.0, "quantity should be 12.0")
        self.assertEqual(round(converted_line['price_unit'], 2), 0.83, "price of product should be 0.83")

        self._sync_paid_pos_order([{
            'product': product_a,
            'qty': converted_line['product_uom_qty'],
            'price_unit': 0.83,
            'extra_values': {
                'sale_order_line_id': sale_order.order_line.id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=test_partner)

        # The quantity sold in the PoS is converted back in the unit of the sale order line.
        self.assertEqual(sale_order.order_line.qty_invoiced, 1.0, "1 dozen should be invoiced")

    def test_ecommerce_paid_order_is_hidden_in_pos(self):
        """
        Tests that a Sale Order fully paid via a payment.transaction (eCommerce)
        has no unpaid amount left, so that it is filtered out of the orders list
        of the Point of Sale.
        """
        self.env.user.group_ids += self.quick_ref('sales_team.group_sale_salesman')
        partner_1 = self.env['res.partner'].create({'name': 'A Test Partner 1'})
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 10.0,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': partner_1.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'product_uom_qty': 2,
                'price_unit': product_a.lst_price
            })]
        })
        provider = self.env['payment.provider'].create({
            'name': 'Test',
            'code': 'none',
        })
        payment_method = self.env["payment.method"].create({
            "name": "Payment method",
            "code": "unknown",
            "provider_id": provider.id,
        })
        self.env['payment.transaction'].create({
            'provider_id': provider.id,
            'payment_method_id': payment_method.id,
            'amount': sale_order.amount_total,
            'currency_id': sale_order.currency_id.id,
            'partner_id': sale_order.partner_id.id,
            'state': 'done',
            'sale_order_ids': [(6, 0, [sale_order.id])],
        })
        sale_order.invalidate_recordset(['transaction_ids'])

        self.assertEqual(
            sale_order.amount_unpaid, 0.0,
            "The amount_unpaid for the SO should be 0 after a successful transaction."
        )

    def test_ecommerce_unpaid_order_is_shown_in_pos(self):
        """
        Tests that a Sale Order fully paid via a payment.transaction (eCommerce)
        does not appear in the list of orders fetched by the Point of Sale.
        """
        self.env.user.group_ids += self.quick_ref('sales_team.group_sale_salesman')
        partner_1 = self.env['res.partner'].create({'name': 'A Test Partner 1'})
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 10.0,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': partner_1.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'product_uom_qty': 2,
                'price_unit': product_a.lst_price
            })]
        })
        self.assertEqual(
            sale_order.amount_unpaid, sale_order.amount_total,
            "The amount_unpaid for the SO should not be 0 if there are no transactions."
        )

    def test_backend_settle_refund(self):
        """Make sure that sale orders settled in PoS and refunded in the backend get their invoiced quantity updated correctly."""

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'lst_price': 10.0,
            'taxes_id': [],
        })

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()
        pos_order_id = self._sync_paid_pos_order([{
            'product': product_a,
            'price_unit': 10,
            'taxes': self.env['account.tax'],
            'extra_values': {
                'sale_order_line_id': sale_order.order_line[0].id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=partner_test, to_invoice=True)
        self.assertEqual(sale_order.order_line.qty_invoiced, 1)
        pos_order_record = self.env['pos.order'].browse(pos_order_id)
        refund_action = pos_order_record.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])
        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': refund.amount_total,
            'payment_method_id': self.bank_payment_method.id,
        })

        self.env.flush_all()
        refund_payment.with_context(**payment_context).check()
        self.assertEqual(sale_order.order_line.qty_invoiced, 0)
        self.assertEqual(sale_order.order_line.qty_delivered, 0)

    def test_amount_unpaid_with_downpayment_and_credit_note(self):
        """ Test that amount_unpaid is well calculated when a downpayment is not made in the PoS """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_uom_qty': 1,
                'price_unit': 500,
                'tax_ids': False,
            })],
        })
        sale_order.action_confirm()

        context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }

        payment = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 300,
        })
        res = payment.create_invoices()
        invoice = self.env['account.move'].browse(res['res_id'])
        invoice.action_post()

        self.assertEqual(sale_order.amount_unpaid, 200.0)

        credit_note = invoice._reverse_moves()
        credit_note.action_post()

        self.assertEqual(sale_order.amount_unpaid, 500.0)

        payment = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'delivered',
        })
        res = payment.create_invoices()
        invoice = self.env['account.move'].browse(res['res_id'])
        invoice.action_post()

        self.assertEqual(sale_order.amount_unpaid, 0.0)

    def test_advance_payment_with_extra_lines(self):
        so = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_a.name,
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()
        self.product_a.write({'available_in_pos': True})

        # Apply 10% down payment and add a product to the PoS order
        self.main_pos_config.open_ui()
        self.main_pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PoSApplyDownpaymentWithExtraLine', login="accountman")
        self.assertEqual(so.amount_unpaid, 90)

    def test_ensure_downpayment_product_in_multiple_company(self):
        if self.env['ir.module.module']._get('pos_hr').state != 'installed':
            self.skipTest("pos_hr module is required for this test")

        branch = self.env['res.company'].create({
            'name': 'Branch 1',
            'parent_id': self.env.company.id,
            'chart_template': self.env.company.chart_template,
        })
        self.env["pos.config"].with_company(branch).create({
            "name": "Branch Point of Sale"
        })
        self.env['pos.config']._ensure_default_products()

    def test_amount_unpaid_with_refund_pos_order(self):
        product = self.env['product.product'].create({
            'name': 'Refund Test Product',
            'available_in_pos': True,
            'lst_price': 100.0,
            'taxes_id': [],
        })
        partner = self.env['res.partner'].create({'name': 'Refund Test Partner'})

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': partner.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': product.name,
                'product_uom_qty': 1,
                'price_unit': product.lst_price,
                'tax_ids': [],
            })],
        })
        sale_order.action_confirm()

        pos_order_id = self._sync_paid_pos_order([{
            'product': product,
            'price_unit': 100.0,
            'taxes': self.env['account.tax'],
            'extra_values': {
                'sale_order_line_id': sale_order.order_line[0].id,
                'sale_order_origin_id': sale_order.id,
            },
        }], partner=partner)
        pos_order_record = self.env['pos.order'].browse(pos_order_id)

        self.assertEqual(
            sale_order.amount_unpaid, 0.0,
            "amount_unpaid should be 0 after the sale order is fully paid through POS",
        )

        # Backend refund: _prepare_refund_values sets is_refund=True and
        # _compute_amount_line_all produces a positive price_subtotal_incl.
        refund_action = pos_order_record.refund()
        refund_order = self.env['pos.order'].browse(refund_action['res_id'])

        self.assertTrue(
            refund_order.is_refund,
            "Refund order created via refund() must have is_refund=True",
        )
        self.assertAlmostEqual(
            refund_order.lines[0].price_subtotal_incl, 100.0,
            msg="Refund line price_subtotal_incl is positive (sign is absorbed into qty by is_refund logic)",
        )

        payment_context = {'active_ids': refund_order.ids, 'active_id': refund_order.id}
        self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': refund_order.amount_total,
            'payment_method_id': self.bank_payment_method.id,
        }).with_context(**payment_context).check()

        self.assertEqual(
            sale_order.amount_unpaid, 100.0,
            "amount_unpaid must equal amount_total after a full POS refund; "
            "a positive refund line must be treated as negative in the computation",
        )


@tagged('post_install', '-at_install')
class TestPoSSalePayment(PoSSaleSyncCommon, TestPointOfSaleHttpCommon, PaymentCommon):

    _test_user_groups = None  # FIXME list needed groups

    def test_pos_settle_so_with_downpayment(self):
        """Ensure that the POS correctly handles Sale Orders where a down payment was processed
        via a payment transaction with the automatic invoicing setting enabled.
        """
        self.product_a.available_in_pos = True
        self.env.company.sale_automatic_invoice = True
        self.partner_a.email = "test.customer@example.com"
        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'product_uom_qty': 1,
                'price_unit': self.product_a.lst_price,
            })],
            'require_signature': False,
            'prepayment_percent': 0.3,
        })
        # Manual downpayment invoice
        down_payment = self.env['sale.advance.payment.inv'].sudo().create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 50,
            'sale_order_ids': sale_order.ids,
        })
        down_payment.create_invoices()
        down_payment_invoices = sale_order.invoice_ids
        down_payment_invoices.action_post()
        # Online payment transaction for 30% downpayment
        tx = self._create_transaction(
                flow='direct',
                amount=sale_order.amount_total * sale_order.prepayment_percent,
                sale_order_ids=[sale_order.id],
                state='done',
                reference='Test Transaction',
            )
        self._run_post_processing(tx)
        self.main_pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")

        # Both down payments are deducted when settling the order, which is
        # covered by the HOOT scenario.
        self.assertEqual(sale_order.amount_unpaid, 755)
        down_payment_lines = sale_order.order_line.filtered(lambda line: line.is_downpayment and not line.display_type)
        self.assertEqual(len(down_payment_lines), 2)
        self.assertEqual(down_payment_lines.mapped('qty_to_invoice'), [-1, -1])

    def test_pos_downpayment_sale_invoice_creation(self):
        account = self.env['account.account'].create({'name': 'Test Downpayment Income Account',
                                                      'code': '12345',
                                                      'account_type': "income"})
        downpayment_product = self.env['product.product'].create({'name': 'Test Down Payment (POS)',
                                                                  "available_in_pos": False,
                                                                  'standard_price': 0.00,
                                                                  'list_price': 0.00,
                                                                  'weight': 0.00,
                                                                  'type': 'service',
                                                                  'purchase_ok': False,
                                                                  'property_account_income_id': account.id
                                                                  })

        sale_order = self.env['sale.order'].sudo().create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.product_a.name,
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        sale_order.action_confirm()
        self.main_pos_config.down_payment_product_id = downpayment_product
        self._sync_paid_pos_downpayment(sale_order, [{'price_unit': 10}], percentage=10, to_invoice=True)
        invoice = sale_order._create_invoices(final=True)
        invoice.action_post()

        downpayment_invoice = sale_order.pos_order_line_ids.order_id.account_move
        self.assertTrue(downpayment_invoice._is_downpayment())

        final_invoice_downpayment_line = sale_order.invoice_ids.invoice_line_ids.filtered(lambda r: r.quantity < 0)

        self.assertEqual(
            final_invoice_downpayment_line._get_downpayment_lines(),
            downpayment_invoice.invoice_line_ids,
        )

        downpayment_invoice_lines = downpayment_invoice.invoice_line_ids.filtered(self.main_pos_config.down_payment_product_id.id == "product_id")
        self.assertTrue(downpayment_invoice_lines.is_downpayment)
        self.assertEqual(downpayment_invoice_lines.account_id.id, account.id)

        so_downpayment_lines = invoice.invoice_line_ids.filtered('is_downpayment')
        self.assertTrue(so_downpayment_lines.is_downpayment)
        self.assertEqual(so_downpayment_lines.account_id.id, account.id)
