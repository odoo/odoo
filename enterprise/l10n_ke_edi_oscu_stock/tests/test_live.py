# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import fields, Command
from odoo.tests import tagged
from odoo.addons.l10n_ke_edi_oscu.tests.common import TestKeEdiCommon


class TestKeEdiStock(TestKeEdiCommon):
    @classmethod
    @TestKeEdiCommon.setup_country("ke")
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_import = cls.env['res.partner'].create([{
            'name': 'OPW Fluid Transfer Group EU B.V',
            'street': 'Roggestraat 38',
            'city': 'Nieuw-Vennep',
            'zip': '2153 GC',
            'country_id': cls.env.ref('base.nl').id,
            'vat': 'NL800672835B01',
        }])

        # Set up products
        cls.product_a.write({
            'name': 'Zaxxon machine',
            'type': 'consu',
            'is_storable': True,
            'taxes_id': [Command.set(cls.standard_rate_sales_tax.ids)],
            'supplier_taxes_id': [Command.set(cls.standard_rate_purchase_tax.ids)],
            'standard_price': 30,
            'l10n_ke_product_type_code': '2',
            'l10n_ke_origin_country_id': cls.env.ref('base.be').id,
            'unspsc_code_id': cls.env['product.unspsc.code'].search([
                ('code', '=', '52161557'),
            ], limit=1).id,
            'l10n_ke_packaging_unit_id': cls.env.ref('l10n_ke_edi_oscu.code_17_SK').id,
            'l10n_ke_packaging_quantity': 5,
        })
        cls.product_b.write({
            'name': 'Windowpane',
            'type': 'consu',
            'is_storable': True,
            'taxes_id': [Command.set(cls.reduced_rate_sales_tax.ids)],
            'supplier_taxes_id': [Command.set(cls.reduced_rate_purchase_tax.ids)],
            'standard_price': 30,
            'l10n_ke_product_type_code': '1',
            'l10n_ke_origin_country_id': cls.env.ref('base.be').id,
            'unspsc_code_id': cls.env['product.unspsc.code'].search([
                ('code', '=', '30171613'),
            ], limit=1).id,
            'l10n_ke_packaging_unit_id': cls.env.ref('l10n_ke_edi_oscu.code_17_CR').id,
            'l10n_ke_packaging_quantity': 1,
        })
        cls.product_import = cls.env['product.product'].create([{
            'name': 'Bottom loading adaptor AL handle',
            'type': 'consu',
            'is_storable': True,
            'taxes_id': [Command.set(cls.standard_rate_sales_tax.ids)],
            'supplier_taxes_id': [Command.set(cls.standard_rate_purchase_tax.ids)],
            'standard_price': 500,
            'l10n_ke_product_type_code': '1',
            'l10n_ke_origin_country_id': cls.env.ref('base.nl').id,
            'unspsc_code_id': cls.env['product.unspsc.code'].search([
                ('code', '=', '25181700'),
            ], limit=1).id,
            'l10n_ke_packaging_unit_id': cls.env.ref('l10n_ke_edi_oscu.code_17_CR').id,
            'l10n_ke_packaging_quantity': 1,
        }])

        # Create initial quants
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_data['company'].id)], limit=1)
        cls.stock_location = cls.warehouse.lot_stock_id

        cls.env['stock.quant'].create({
            'product_id': cls.product_a.id,
            'location_id': cls.stock_location.id,
            'quantity': 20.0,
        })

        cls.env['stock.quant'].create({
            'product_id': cls.product_b.id,
            'location_id': cls.stock_location.id,
            'quantity': 20.0,
        })

    def _test_send_invoice_and_credit_note_stock(self):
        """ Send an invoice and a credit note.
            We do this sequentially (first the invoice, its stock IO and stock master,
            then the credit note, its stock IO and stock master).
        """
        self.env.user.groups_id |= self.env.ref('sales_team.group_sale_salesman')
        # Step 1: create invoice
        invoice = self.init_invoice(
            'out_invoice',
            partner=self.partner_a,
            invoice_date='2024-01-28',
            products=[self.product_a, self.product_b]
        )
        invoice.invoice_line_ids[0].discount = 10

        # Step 2: create sale order from invoice
        action = invoice.action_l10n_ke_create_sale_order()
        so = self.env['sale.order'].browse(action['res_id'])
        so.action_confirm()

        # Step 3: validate picking
        picking = so.picking_ids
        picking.button_validate()

        # Step 4: send invoice
        self.assertFalse(invoice.l10n_ke_validation_message)
        invoice.action_post()
        send_and_print = self.create_send_and_print(invoice)
        self.assertTrue(send_and_print.extra_edi_checkboxes.get('ke_oscu', {}).get('checked'))
        with self.set_invoice_number(invoice), self.patch_cron_trigger() as mocked_trigger:
            send_and_print.action_send_and_print()

        self.assertTrue(invoice.l10n_ke_oscu_invoice_number)
        self.assertTrue(invoice.l10n_ke_oscu_receipt_number)
        self.assertTrue(invoice.l10n_ke_oscu_internal_data)

        # Step 5: picking cron should get called.
        mocked_trigger.assert_called()

        # Step 6: create and validate return pickings
        wizard_return = self.env['stock.return.picking'].with_context(active_id=picking.id, active_model='stock.picking').create({})
        for line in wizard_return.product_return_moves:
            line.quantity = line.move_id.quantity
        action = wizard_return.action_create_returns()
        return_pickings = self.env['stock.picking'].browse(action['res_id'])
        return_pickings.button_validate()

        # Step 7: create credit note
        credit_note = self.create_reversal(invoice)
        self.assertFalse(credit_note.l10n_ke_validation_message)
        credit_note.action_post()

        # Step 8: send credit note
        send_and_print = self.create_send_and_print(credit_note)
        self.assertTrue(send_and_print.extra_edi_checkboxes.get('ke_oscu', {}).get('checked'))
        with self.set_invoice_number(credit_note), self.patch_cron_trigger() as mocked_trigger:
            send_and_print.action_send_and_print()

        self.assertTrue(credit_note.l10n_ke_oscu_invoice_number)
        self.assertTrue(credit_note.l10n_ke_oscu_receipt_number)
        self.assertTrue(credit_note.l10n_ke_oscu_internal_data)

        # Step 9: picking cron should get called.
        mocked_trigger.assert_called()

    def _test_send_invoiced_stock_moves(self):
        """ This test ensures that the Stock IO and Stock Master reflect the invoices that have been sent.
            1) Create Sale Order & Invoice n.1, with 2 of each product, receive the products but don't send the invoice.
            2) Create Sale Order & Invoice n.2, with 1 of each product, receive the products and send the invoice.
            3) Stock IO and Stock Master should be sent with the quantities in Sale Order n.2.
            4) Now send Invoice n.1.
            5) Stock IO and Stock Master should be sent with the quantities in Sale Order n.1.
        """
        self.env.user.groups_id |= self.env.ref('sales_team.group_sale_salesman')
        # Step 1: create invoice 1 and sale order, and validate picking.
        invoice_1 = self.init_invoice(
            'out_invoice',
            partner=self.partner_a,
            invoice_date='2024-01-28',
            products=[self.product_a, self.product_b],
        )
        invoice_1.invoice_line_ids.write({
            'quantity': 2,
            'discount': 10,
        })
        action = invoice_1.action_l10n_ke_create_sale_order()
        so_1 = self.env['sale.order'].browse(action['res_id'])
        so_1.action_confirm()
        picking_1 = so_1.picking_ids
        picking_1.button_validate()
        self.assertFalse(invoice_1.l10n_ke_validation_message)

        # Step 2: create invoice 2 and sale order, and validate picking.
        invoice_2 = self.init_invoice(
            'out_invoice',
            partner=self.partner_a,
            invoice_date='2024-01-28',
            products=[self.product_a, self.product_b],
        )
        invoice_2.invoice_line_ids[0].discount = 10
        action = invoice_2.action_l10n_ke_create_sale_order()
        so_2 = self.env['sale.order'].browse(action['res_id'])
        so_2.action_confirm()
        picking_2 = so_2.picking_ids
        picking_2.button_validate()
        self.assertFalse(invoice_2.l10n_ke_validation_message)

        # Step 3: Send invoice 2.
        invoice_2.action_post()
        send_and_print = self.create_send_and_print(invoice_2)
        self.assertTrue(send_and_print.extra_edi_checkboxes.get('ke_oscu', {}).get('checked'))
        with self.set_invoice_number(invoice_2), self.patch_cron_trigger() as mocked_trigger:
            send_and_print.action_send_and_print()

        self.assertTrue(invoice_2.l10n_ke_oscu_invoice_number)
        self.assertTrue(invoice_2.l10n_ke_oscu_receipt_number)
        self.assertTrue(invoice_2.l10n_ke_oscu_internal_data)

        # Step 4: Picking cron should get called for (and only for) the stock move related to invoice 2.
        mocked_trigger.assert_called()

        # Step 5: Send invoice 1.
        invoice_1.action_post()
        send_and_print = self.create_send_and_print(invoice_1)
        self.assertTrue(send_and_print.extra_edi_checkboxes.get('ke_oscu', {}).get('checked'))
        with self.set_invoice_number(invoice_1), self.patch_cron_trigger() as mocked_trigger:
            send_and_print.action_send_and_print()

        self.assertTrue(invoice_1.l10n_ke_oscu_invoice_number)
        self.assertTrue(invoice_1.l10n_ke_oscu_receipt_number)
        self.assertTrue(invoice_1.l10n_ke_oscu_internal_data)

        # Step 6: Picking cron should get called for (and only for) the stock move related to invoice 1.
        mocked_trigger.assert_called()

    def _test_get_vendor_bill(self):
        # Step 1: Retrieve vendor bill
        vendor_bill = self.env['account.move']._l10n_ke_oscu_fetch_purchases(self.company_data['company'])

        expected_vendor_bill = {
                'partner_id': self.partner_a.id,
                'move_type': 'in_invoice',
                'invoice_date': fields.Date.from_string('2023-12-12'),
            }
        expected_vendor_bill_lines = [
            {
                'name': 'Zaxxon machine',
                'product_id': self.product_a.id,
                'product_uom_id': self.env.ref('uom.product_uom_unit').id,
                'quantity': 1,
                'tax_ids': [self.standard_rate_purchase_tax.id],
                'balance': 17499,
            }, {
                'name': 'window pane',
                'product_id': self.product_b.id,
                # In this case, the UoM in the JSON is unrecognized, so we take the product's default UoM.
                # In general, that should be a good guess. However, because in this test we deliberately configured product_b
                # to use dozens (in order to test conversions in other tests) it gives this nonsensical '12 dozens' result here.
                'product_uom_id': self.env.ref('uom.product_uom_dozen').id,
                'quantity': 12,
                'tax_ids': [self.reduced_rate_purchase_tax.id],
                'balance': 54000,
            }, {
                'name': '16%',
                'product_id': None,
                'product_uom_id': False,
                'quantity': 0,
                'tax_ids': [],
                'balance': 2799.84,
            }, {
                'name': '8%',
                'product_id': None,
                'product_uom_id': False,
                'quantity': 0,
                'tax_ids': [],
                'balance': 4320.00,
            }, {
                'name': False,
                'product_id': None,
                'product_uom_id': False,
                'quantity': 0,
                'tax_ids': [],
                'balance': -78618.84,
            }
        ]
        self.assertInvoiceValues(vendor_bill, expected_vendor_bill_lines, expected_vendor_bill)

        # Manually adjust the quantity and UoM of the 'Window Pane' line to 12 units.
        vendor_bill.invoice_line_ids.filtered(lambda l: l.product_id == self.product_b).write({
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            'quantity': 12,
        })

        return vendor_bill

    def _test_confirm_vendor_bill(self, vendor_bill):
        # Step 2: create purchase order from vendor bill
        action = vendor_bill.action_l10n_ke_create_purchase_order()
        po = self.env['purchase.order'].browse(action['res_id'])
        po.button_confirm()

        # Step 3: validate picking
        po.picking_ids.button_validate()

        # Step 4: send vendor bill confirmation
        vendor_bill.l10n_ke_payment_method_id = self.env.ref('l10n_ke_edi_oscu.code_07_05')
        self.assertFalse(vendor_bill.l10n_ke_validation_message)
        vendor_bill.action_post()
        with self.patch_cron_trigger() as mocked_trigger:
            vendor_bill.action_l10n_ke_oscu_confirm_vendor_bill()

        # Step 5: picking cron should get called
        mocked_trigger.assert_called()

    def _test_get_custom_import(self):
        # Step 1: Retrieve custom import
        self.env['l10n_ke_edi.customs.import'].sudo()._receive_customs_import(self.company_data['company'])
        custom_import = self.env['l10n_ke_edi.customs.import'].search([('company_id', '=', self.company_data['company'].id)])

        expected_import_values = [{
            'declaration_date': datetime.date(2023, 2, 1),
            'declaration_number': '23NBOIM401172243',
            'task_code': '20230208667984',
            'item_seq': 1,
            'supplier_name': 'OPW FLUID TRANSFER GROUP EUROPE B.V',
            'item_name': 'TANKER TRAILER PARTS & ACCESSORIES API BOTTOM LOADING ADAPTOR AL HANDLE',
            'number_packages': 17,
            'package_unit_code_id': self.env.ref('l10n_ke_edi_oscu.code_17_CR').id,
            'quantity': 2,
            'uom_code_id': self.env.ref('l10n_ke_edi_oscu.code_10_U').id,
            'hs_code': '87169000',
            'origin_country_id': self.env.ref('base.nl').id,
            'export_country_id': self.env.ref('base.nl').id,
        }]

        self.assertRecordValues(custom_import, expected_import_values)
        return custom_import

    def _test_confirm_custom_import(self, custom_import):
        # Step 2: Add partner and product on custom import
        custom_import.write({
            'product_id': self.product_import.id,
            'partner_id': self.partner_import.id,
        })
        self.assertRecordValues(custom_import, [{'warning_msg': False}])

        # Step 3: create purchase order from custom import
        action = custom_import.action_create_purchase_order()
        po = self.env['purchase.order'].browse(action['res_id'])
        po.button_confirm()

        # Step 4: validate picking
        po.picking_ids.button_validate()

        # Step 5: match and approve custom import
        custom_import.button_approve()

        # Step 6: create vendor bill and send confirmation
        po.action_create_invoice()
        vendor_bill = po.invoice_ids
        vendor_bill.write({
            'invoice_date': fields.Date.today(),
            'l10n_ke_payment_method_id': self.env.ref('l10n_ke_edi_oscu.code_07_05'),
        })
        self.assertFalse(vendor_bill.l10n_ke_validation_message)
        vendor_bill.action_post()
        with self.patch_cron_trigger() as mocked_trigger:
            vendor_bill.action_l10n_ke_oscu_confirm_vendor_bill()

        # Step 7: picking cron should get called
        mocked_trigger.assert_called()

    def _test_send_picking_between_branches(self):
        # Step 1: Create Kakamega branch
        self._test_create_branches()
        branch = self.env['res.company'].search([('parent_id', '=', self.company_data['company'].id), ('name', '=like', 'KAKAMEGA%')])
        branch.write({
            'l10n_ke_oscu_cmc_key': self.branch_cmc_key,
            'l10n_ke_oscu_user_agreement': True,
        })

        # Step 2: Create transfer from HQ to Kakamega
        parent_delivery_type = self.env['stock.picking.type'].search([('company_id', '=', self.company_data['company'].id), ('code', '=', 'outgoing')], limit=1)
        out_picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'partner_id': branch.partner_id.id,
            'picking_type_id': parent_delivery_type.id,
            'move_ids': [
                Command.create({
                    'name': self.product_a.name,
                    'location_id': self.stock_location.id,
                    'location_dest_id': self.customer_location.id,
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1,
                    'product_uom': self.product_a.uom_id.id,
                    'description_picking': self.product_a.name,
                })
            ]
        })
        out_picking.button_validate()

        # Step 3: Run picking cron as superuser
        self.env.ref('l10n_ke_edi_oscu_stock.ir_cron_send_stock_moves').method_direct_trigger()

        # Step 4: Create receipt in Kakamega
        branch_receipt_type = self.env['stock.picking.type'].search([('company_id', '=', branch.id), ('code', '=', 'incoming')], limit=1)
        branch_stock_location = self.env['stock.warehouse'].search([('company_id', '=', branch.id)], limit=1).lot_stock_id
        in_picking = self.env['stock.picking'].with_company(branch).create({
            'location_id': branch_stock_location.id,
            'location_dest_id': self.supplier_location.id,
            'partner_id': self.company_data['company'].partner_id.id,
            'picking_type_id': branch_receipt_type.id,
            'move_ids': [
                Command.create({
                    'name': self.product_a.name,
                    'location_id': self.supplier_location.id,
                    'location_dest_id': branch_stock_location.id,
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1,
                    'product_uom': self.product_a.uom_id.id,
                    'description_picking': self.product_a.name,
                })
            ]
        })
        in_picking.button_validate()

        # Step 5: Run picking cron as superuser
        self.env.ref('l10n_ke_edi_oscu_stock.ir_cron_send_stock_moves').method_direct_trigger()

    def _test_send_inventory_adjustment(self):
        self.user.write({'groups_id': [Command.link(self.env.ref('stock.group_stock_user').id)]})
        self.product_a.action_l10n_ke_oscu_save_item()

        # Step 1: Create inventory adjustment
        with self.patch_cron_trigger() as mocked_trigger:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': self.product_a.id,
                'location_id': self.stock_location.id,
                'inventory_quantity_auto_apply': 21.0,
            })

        # Step 2: Check values of the created stock move
        stock_move = self.env['stock.move'].search([
            ('company_id', '=', self.env.company.id),
            ('is_inventory', '=', True),
        ])
        inventory_adjustment_location = self.env['product.template']._fields['property_stock_inventory'].get_company_dependent_fallback(self.env['product.template'])
        expected_stock_move_vals = [{
            'product_id': self.product_a.id,
            'product_uom': self.product_a.uom_id.id,
            'product_uom_qty': 1.0,
            'location_id': inventory_adjustment_location.id,
            'location_dest_id': self.stock_location.id,
        }]
        expected_stock_move_line_vals = [{
            'product_id': self.product_a.id,
            'product_uom_id': self.product_a.uom_id.id,
            'quantity': 1.0,
            'location_id': inventory_adjustment_location.id,
            'location_dest_id': self.stock_location.id,
        }]
        self.assertRecordValues(stock_move, expected_stock_move_vals)
        self.assertRecordValues(stock_move.move_line_ids, expected_stock_move_line_vals)

        # Step 3: Check that the cron was called.
        mocked_trigger.assert_called()


@tagged('external', 'external_l10n', 'post_install', '-post_install_l10n', '-at_install', '-standard')
class TestKeEdiStockLive(TestKeEdiStock):
    @classmethod
    @TestKeEdiCommon.setup_country("ke")
    def setUpClass(cls):
        super().setUpClass()
        cls.is_live_test = True

    def test_send_invoice_and_credit_note_stock(self):
        self._test_send_invoice_and_credit_note_stock()

    def test_send_invoiced_stock_moves(self):
        self._test_send_invoiced_stock_moves()

    def test_confirm_vendor_bill(self):
        # This is mocked because there are no purchases on the test server to retrieve.
        with self.patch_session([
            ('selectTrnsPurchaseSalesList', 'get_purchases', 'get_purchases_2'),
        ]):
            vendor_bill = self._test_get_vendor_bill()
        self._test_confirm_vendor_bill(vendor_bill)

    def test_confirm_custom_import(self):
        # This is mocked because there are no custom imports on the test server to retrieve.
        with self.patch_session([
            ('selectImportItemList', 'get_imports', 'get_imports_1'),
        ]):
            custom_import = self._test_get_custom_import()
        self._test_confirm_custom_import(custom_import)

    def test_send_picking_between_branches(self):
        self._test_send_picking_between_branches()

    def test_send_inventory_adjustment(self):
        self._test_send_inventory_adjustment()
