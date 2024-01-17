# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestRepair(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Partners
        cls.res_partner_1 = cls.env['res.partner'].create({'name': 'Wood Corner'})
        cls.res_partner_address_1 = cls.env['res.partner'].create({'name': 'Willie Burke', 'parent_id': cls.res_partner_1.id})
        cls.res_partner_12 = cls.env['res.partner'].create({'name': 'Partner 12'})

        # Products
        cls.product_product_3 = cls.env['product.product'].create({'name': 'Desk Combination'})
        cls.product_product_11 = cls.env['product.product'].create({'name': 'Conference Chair'})
        cls.product_product_5 = cls.env['product.product'].create({'name': 'Product 5'})
        cls.product_product_6 = cls.env['product.product'].create({'name': 'Large Cabinet'})
        cls.product_product_12 = cls.env['product.product'].create({'name': 'Office Chair Black'})
        cls.product_product_13 = cls.env['product.product'].create({'name': 'Corner Desk Left Sit'})
        cls.product_product_2 = cls.env['product.product'].create({'name': 'Virtual Home Staging'})
        cls.product_service_order_repair = cls.env['product.product'].create({
            'name': 'Repair Services',
            'type': 'service',
        })

        # Location
        cls.stock_warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.stock_location_14 = cls.env['stock.location'].create({
            'name': 'Shelf 2',
            'location_id': cls.stock_warehouse.lot_stock_id.id,
        })

        # Repair Orders
        cls.repair1 = cls.env['repair.order'].create({
            'address_id': cls.res_partner_address_1.id,
            'guarantee_limit': '2019-01-01',
            'invoice_method': 'none',
            'user_id': False,
            'product_id': cls.product_product_3.id,
            'product_uom': cls.env.ref('uom.product_uom_unit').id,
            'partner_invoice_id': cls.res_partner_address_1.id,
            'location_id': cls.stock_warehouse.lot_stock_id.id,
            'operations': [
                (0, 0, {
                    'location_dest_id': cls.product_product_11.property_stock_production.id,
                    'location_id': cls.stock_warehouse.lot_stock_id.id,
                    'name': cls.product_product_11.get_product_multiline_description_sale(),
                    'product_id': cls.product_product_11.id,
                    'product_uom': cls.env.ref('uom.product_uom_unit').id,
                    'product_uom_qty': 1.0,
                    'price_unit': 50.0,
                    'state': 'draft',
                    'type': 'add',
                    'company_id': cls.env.company.id,
                })
            ],
            'fees_lines': [
                (0, 0, {
                    'name': cls.product_service_order_repair.get_product_multiline_description_sale(),
                    'product_id': cls.product_service_order_repair.id,
                    'product_uom_qty': 1.0,
                    'product_uom': cls.env.ref('uom.product_uom_unit').id,
                    'price_unit': 50.0,
                    'company_id': cls.env.company.id,
                })
            ],
            'partner_id': cls.res_partner_12.id,
        })

        cls.repair0 = cls.env['repair.order'].create({
            'product_id': cls.product_product_5.id,
            'product_uom': cls.env.ref('uom.product_uom_unit').id,
            'address_id': cls.res_partner_address_1.id,
            'guarantee_limit': '2019-01-01',
            'invoice_method': 'after_repair',
            'user_id': False,
            'partner_invoice_id': cls.res_partner_address_1.id,
            'location_id': cls.stock_warehouse.lot_stock_id.id,
            'operations': [
                (0, 0, {
                    'location_dest_id': cls.product_product_12.property_stock_production.id,
                    'location_id': cls.stock_warehouse.lot_stock_id.id,
                    'name': cls.product_product_12.get_product_multiline_description_sale(),
                    'price_unit': 50.0,
                    'product_id': cls.product_product_12.id,
                    'product_uom': cls.env.ref('uom.product_uom_unit').id,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'type': 'add',
                    'company_id': cls.env.company.id,
                })
            ],
            'fees_lines': [
                (0, 0, {
                    'name': cls.product_service_order_repair.get_product_multiline_description_sale(),
                    'product_id': cls.product_service_order_repair.id,
                    'product_uom_qty': 1.0,
                    'product_uom': cls.env.ref('uom.product_uom_unit').id,
                    'price_unit': 50.0,
                    'company_id': cls.env.company.id,
                })
            ],
            'partner_id': cls.res_partner_12.id,
        })

        cls.repair2 = cls.env['repair.order'].create({
            'product_id': cls.product_product_6.id,
            'product_uom': cls.env.ref('uom.product_uom_unit').id,
            'address_id': cls.res_partner_address_1.id,
            'guarantee_limit': '2019-01-01',
            'invoice_method': 'b4repair',
            'user_id': False,
            'partner_invoice_id': cls.res_partner_address_1.id,
            'location_id': cls.stock_location_14.id,
            'operations': [
                (0, 0, {
                    'location_dest_id': cls.product_product_13.property_stock_production.id,
                    'location_id': cls.stock_warehouse.lot_stock_id.id,
                    'name': cls.product_product_13.get_product_multiline_description_sale(),
                    'price_unit': 50.0,
                    'product_id': cls.product_product_13.id,
                    'product_uom': cls.env.ref('uom.product_uom_unit').id,
                    'product_uom_qty': 1.0,
                    'state': 'draft',
                    'type': 'add',
                    'company_id': cls.env.company.id,
                })
            ],
            'fees_lines': [
                (0, 0, {
                    'name': cls.product_service_order_repair.get_product_multiline_description_sale(),
                    'product_id': cls.product_service_order_repair.id,
                    'product_uom_qty': 1.0,
                    'product_uom': cls.env.ref('uom.product_uom_unit').id,
                    'price_unit': 50.0,
                    'company_id': cls.env.company.id,
                })
            ],
            'partner_id': cls.res_partner_12.id,
        })

        cls.env.user.groups_id |= cls.env.ref('stock.group_stock_user')

    def _create_simple_repair_order(self, invoice_method):
        product_to_repair = self.product_product_5
        partner = self.res_partner_address_1
        return self.env['repair.order'].create({
            'product_id': product_to_repair.id,
            'product_uom': product_to_repair.uom_id.id,
            'address_id': partner.id,
            'guarantee_limit': '2019-01-01',
            'invoice_method': invoice_method,
            'partner_invoice_id': partner.id,
            'location_id': self.stock_warehouse.lot_stock_id.id,
            'partner_id': self.res_partner_12.id
        })

    def _create_simple_operation(self, repair_id=False, qty=0.0, price_unit=0.0):
        product_to_add = self.product_product_5
        return self.env['repair.line'].create({
            'name': 'Add The product',
            'type': 'add',
            'product_id': product_to_add.id,
            'product_uom_qty': qty,
            'product_uom': product_to_add.uom_id.id,
            'price_unit': price_unit,
            'repair_id': repair_id,
            'location_id': self.stock_warehouse.lot_stock_id.id,
            'location_dest_id': product_to_add.property_stock_production.id,
            'company_id': self.env.company.id,
        })

    def _create_simple_fee(self, repair_id=False, qty=0.0, price_unit=0.0):
        product_service = self.product_product_2
        return self.env['repair.fee'].create({
            'name': 'PC Assemble + Custom (PC on Demand)',
            'product_id': product_service.id,
            'product_uom_qty': qty,
            'product_uom': product_service.uom_id.id,
            'price_unit': price_unit,
            'repair_id': repair_id,
            'company_id': self.env.company.id,
        })

    def test_00_repair_afterinv(self):
        repair = self._create_simple_repair_order('after_repair')
        self._create_simple_operation(repair_id=repair.id, qty=1.0, price_unit=50.0)
        # I confirm Repair order taking Invoice Method 'After Repair'.
        repair.action_repair_confirm()

        # I check the state is in "Confirmed".
        self.assertEqual(repair.state, "confirmed", 'Repair order should be in "Confirmed" state.')
        repair.action_repair_start()

        # I check the state is in "Under Repair".
        self.assertEqual(repair.state, "under_repair", 'Repair order should be in "Under_repair" state.')

        # Repairing process for product is in Done state and I end Repair process by clicking on "End Repair" button.
        repair.action_repair_end()

        # I define Invoice Method 'After Repair' option in this Repair order.so I create invoice by clicking on "Make Invoice" wizard.
        make_invoice = self.env['repair.order.make_invoice'].create({
            'group': True})
        # I click on "Create Invoice" button of this wizard to make invoice.
        context = {
            "active_model": 'repair_order',
            "active_ids": [repair.id],
            "active_id": repair.id
        }
        make_invoice.with_context(context).make_invoices()

        # I check that invoice is created for this Repair order.
        self.assertEqual(len(repair.invoice_id), 1, "No invoice exists for this repair order")
        self.assertEqual(len(repair.move_id.move_line_ids[0].consume_line_ids), 1, "Consume lines should be set")

    def test_01_repair_b4inv(self):
        repair = self._create_simple_repair_order('b4repair')
        # I confirm Repair order for Invoice Method 'Before Repair'.
        repair.action_repair_confirm()

        # I click on "Create Invoice" button of this wizard to make invoice.
        repair.action_repair_invoice_create()

        # I check that invoice is created for this Repair order.
        self.assertEqual(len(repair.invoice_id), 1, "No invoice exists for this repair order")

    def test_02_repair_noneinv(self):
        repair = self._create_simple_repair_order('none')

        # Add a new fee line
        self._create_simple_fee(repair_id=repair.id, qty=1.0, price_unit=12.0)

        self.assertEqual(repair.amount_total, 12, "Amount_total should be 12")
        # Add new operation line
        self._create_simple_operation(repair_id=repair.id, qty=1.0, price_unit=14.0)

        self.assertEqual(repair.amount_total, 26, "Amount_total should be 26")

        # I confirm Repair order for Invoice Method 'No Invoice'.
        repair.action_repair_confirm()

        # I start the repairing process by clicking on "Start Repair" button for Invoice Method 'No Invoice'.
        repair.action_repair_start()

        # I check its state which is in "Under Repair".
        self.assertEqual(repair.state, "under_repair", 'Repair order should be in "Under_repair" state.')

        # Repairing process for product is in Done state and I end this process by clicking on "End Repair" button.
        repair.action_repair_end()

        self.assertEqual(repair.move_id.location_id.id, self.stock_warehouse.lot_stock_id.id,
                         'Repaired product was taken in the wrong location')
        self.assertEqual(repair.move_id.location_dest_id.id, self.stock_warehouse.lot_stock_id.id,
                         'Repaired product went to the wrong location')
        self.assertEqual(repair.operations.move_id.location_id.id, self.stock_warehouse.lot_stock_id.id,
                         'Consumed product was taken in the wrong location')
        self.assertEqual(repair.operations.move_id.location_dest_id.id, self.product_product_5.property_stock_production.id,
                         'Consumed product went to the wrong location')

        # I define Invoice Method 'No Invoice' option in this repair order.
        # So, I check that Invoice has not been created for this repair order.
        self.assertNotEqual(len(repair.invoice_id), 1, "Invoice should not exist for this repair order")

    def test_repair_state(self):
        repair = self._create_simple_repair_order('b4repair')
        repair.action_repair_confirm()
        repair.action_repair_invoice_create()
        repair.invoice_id.unlink()
        # Repair order state should be changed to 2binvoiced so that new invoice can be created
        self.assertEqual(repair.state, '2binvoiced', 'Repair order should be in 2binvoiced state, if invoice is deleted.')
        repair.action_repair_invoice_create()
        repair.action_repair_cancel()
        # Repair order and linked invoice both should be cancelled.
        self.assertEqual(repair.state, 'cancel', 'Repair order should be in cancel state.')
        self.assertEqual(repair.invoice_id.state, 'cancel', 'Invoice should be in cancel state.')
        repair.action_repair_cancel_draft()
        # Linked invoice should be unlinked
        self.assertEqual(len(repair.invoice_id), 0, "No invoice should be exists for this repair order")

    def test_03_repair_multicompany(self):
        """ This test ensures that the correct taxes are selected when the user fills in the RO form """

        company01 = self.env.company
        company02 = self.env['res.company'].create({
            'name': 'SuperCompany',
        })

        tax01 = self.env["account.tax"].create({
            "name": "C01 Tax",
            "amount": "0.00",
            "company_id": company01.id
        })
        tax02 = self.env["account.tax"].create({
            "name": "C02 Tax",
            "amount": "0.00",
            "company_id": company02.id
        })

        super_product = self.env['product.template'].create({
            "name": "SuperProduct",
            "taxes_id": [(4, tax01.id), (4, tax02.id)],
        })
        super_variant = super_product.product_variant_id
        self.assertEqual(super_variant.taxes_id, tax01 | tax02)

        ro_form = Form(self.env['repair.order'])
        ro_form.product_id = super_variant
        ro_form.partner_id = company01.partner_id
        with ro_form.operations.new() as ro_line:
            ro_line.product_id = super_variant
        with ro_form.fees_lines.new() as fee_line:
            fee_line.product_id = super_variant
        repair_order = ro_form.save()

        # tax02 should not be present since it belongs to the second company.
        self.assertEqual(repair_order.operations.tax_id, tax01)
        self.assertEqual(repair_order.fees_lines.tax_id, tax01)

    def test_repair_order_send_to_self(self):
        # when sender(logged in user) is also present in recipients of the mail composer,
        # user should receive mail.
        product_to_repair = self.product_product_5
        partner = self.res_partner_address_1
        repair_order = self.env['repair.order'].with_user(self.env.user).create({
            'product_id': product_to_repair.id,
            'product_uom': product_to_repair.uom_id.id,
            'address_id': partner.id,
            'guarantee_limit': '2019-01-01',
            'location_id': self.stock_warehouse.lot_stock_id.id,
            'partner_id': self.env.user.partner_id.id
        })
        email_ctx = repair_order.action_send_mail().get('context', {})
        # We need to prevent auto mail deletion, and so we copy the template and send the mail with
        # added configuration in copied template. It will allow us to check whether mail is being
        # sent to to author or not (in case author is present in 'Recipients' of composer).
        mail_template = self.env['mail.template'].browse(email_ctx.get('default_template_id')).copy({'auto_delete': False})
        # send the mail with same user as customer
        repair_order.with_context(**email_ctx).with_user(self.env.user).message_post_with_template(mail_template.id)
        mail_message = repair_order.message_ids[0]
        self.assertEqual(mail_message.author_id, repair_order.partner_id, 'Repair: author should be same as customer')
        self.assertEqual(mail_message.author_id, mail_message.partner_ids, 'Repair: author should be in composer recipients thanks to "partner_to" field set on template')
        self.assertEqual(mail_message.partner_ids, mail_message.sudo().mail_ids.recipient_ids, 'Repair: author should receive mail due to presence in composer recipients')

    def test_repair_with_product_in_package(self):
        """
        Test That a repair order can be validated when the repaired product is tracked and in a package
        """
        self.product_a.tracking = 'serial'
        self.product_a.type = 'product'
        # Create two serial numbers
        sn_1 = self.env['stock.production.lot'].create({'name': 'sn_1', 'product_id': self.product_a.id})
        sn_2 = self.env['stock.production.lot'].create({'name': 'sn_2', 'product_id': self.product_a.id})

        # Create two packages
        package_1 = self.env['stock.quant.package'].create({'name': 'Package-test-1'})
        package_2 = self.env['stock.quant.package'].create({'name': 'Package-test-2'})

        # update the quantity of the product in the stock
        self.env['stock.quant']._update_available_quantity(self.product_a, self.stock_warehouse.lot_stock_id, 1, lot_id=sn_1, package_id=package_1)
        self.env['stock.quant']._update_available_quantity(self.product_a, self.stock_warehouse.lot_stock_id, 1, lot_id=sn_2, package_id=package_2)
        self.assertEqual(self.product_a.qty_available, 2)
        # create a repair order
        repair_order = self.env['repair.order'].create({
            'product_id': self.product_a.id,
            'product_uom': self.product_a.uom_id.id,
            'guarantee_limit': '2019-01-01',
            'location_id': self.stock_warehouse.lot_stock_id.id,
            'lot_id': sn_1.id,
            'operations': [
                (0, 0, {
                    'name': 'foo',
                    'product_id': self.product_b.id,
                    'product_uom': self.product_b.uom_id.id,
                    'product_uom_qty': 1,
                    'price_unit': 50.0,
                    'location_id': self.stock_warehouse.lot_stock_id.id,
                    'location_dest_id': self.product_b.property_stock_production.id,
                })
            ],
        })
        # Validate and complete the repair order
        repair_order.action_validate()
        repair_order.action_repair_start()
        repair_order.action_repair_end()
        self.assertEqual(repair_order.state, 'done')
