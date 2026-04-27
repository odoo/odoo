# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_ke_edi_oscu_stock.tests.test_live import TestKeEdiStock


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestKeEdiStockMocked(TestKeEdiStock):
    @classmethod
    @TestKeEdiStock.setup_country('ke')
    def setUpClass(cls):
        cls.startClassPatcher(freeze_time('2024-04-15'))
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('l10n_ke.start_stock_date', '2024-04-14')

    # === Valid flows === #

    def test_send_invoice_and_credit_note_stock(self):
        with self.patch_session([
            ('saveItem', 'save_item_1', 'success'),
            ('saveItem', 'save_item_2', 'success'),
            ('saveTrnsSalesOsdc', 'save_sale_2', 'save_sale_success'),
            ('insertStockIO', 'save_stock_io_sale_1', 'success'),
            ('saveStockMaster', 'save_stock_master_19', 'success'),
            ('saveStockMaster', 'save_stock_master_19', 'success'),
            ('selectInvoiceDetails', 'get_invoice_details_1', 'get_invoice_details_success'),
            ('saveTrnsSalesOsdc', 'save_refund_2', 'save_sale_success'),
            ('insertStockIO', 'save_stock_io_refund', 'success'),
            ('saveStockMaster', 'save_stock_master_20', 'success'),
            ('saveStockMaster', 'save_stock_master_20', 'success'),
        ]):
            self._test_send_invoice_and_credit_note_stock()

    def test_send_invoiced_stock_moves(self):
        with self.patch_session([
            ('saveItem', 'save_item_1', 'success'),
            ('saveItem', 'save_item_2', 'success'),
            ('saveTrnsSalesOsdc', 'save_sale_2', 'save_sale_success'),
            ('insertStockIO', 'save_stock_io_sale_1', 'success'),
            ('saveStockMaster', 'save_stock_master_19', 'success'),
            ('saveStockMaster', 'save_stock_master_19', 'success'),
            ('saveTrnsSalesOsdc', 'save_sale_3', 'save_sale_success'),
            ('insertStockIO', 'save_stock_io_sale_2', 'success'),
            ('saveStockMaster', 'save_stock_master_17', 'success'),
            ('saveStockMaster', 'save_stock_master_17', 'success'),
        ]):
            self._test_send_invoiced_stock_moves()

    def test_confirm_vendor_bill(self):
        with self.patch_session([
            ('selectTrnsPurchaseSalesList', 'get_purchases', 'get_purchases_2'),
            ('saveItem', 'save_item_1', 'success'),
            ('saveItem', 'save_item_2', 'success'),
            ('insertTrnsPurchase', 'save_purchase_2', 'success'),
            ('insertStockIO', 'save_stock_io_purchase_1', 'success'),
            ('saveStockMaster', 'save_stock_master_21', 'success'),
            ('saveStockMaster', 'save_stock_master_21', 'success'),
        ]):
            vendor_bill = self._test_get_vendor_bill()
            self._test_confirm_vendor_bill(vendor_bill)

    def test_confirm_custom_import(self):
        with self.patch_session([
            ('selectImportItemList', 'get_imports', 'get_imports_1'),
            ('saveItem', 'save_item_3', 'success'),
            ('updateImportItem', 'save_import_1', 'success'),
            ('insertTrnsPurchase', 'save_purchase_3', 'success'),
            ('insertStockIO', 'save_stock_io_purchase_2', 'success'),
            ('saveStockMaster', 'save_stock_master_2', 'success'),
        ]):
            custom_import = self._test_get_custom_import()
            self._test_confirm_custom_import(custom_import)

    def test_send_picking_between_branches(self):
        with self.patch_session([
            ('selectBhfList', 'get_branches', 'get_branches'),
            ('saveItem', 'save_item_1', 'success'),
            ('insertStockIO', 'save_stock_io_transfer_out', 'success'),
            ('saveStockMaster', 'save_stock_master_19', 'success'),
            ('insertStockIO', 'save_stock_io_transfer_in', 'success'),
            ('saveStockMaster', 'save_stock_master_1', 'success'),
        ]):
            self._test_send_picking_between_branches()

    def test_send_inventory_adjustment(self):
        with self.patch_session([
            ('saveItem', 'save_item_1', 'success'),
            ('insertStockIO', 'save_stock_io_adjustment_in', 'success'),
            ('saveStockMaster', 'save_stock_master_21', 'success'),
        ]):
            self._test_send_inventory_adjustment()

    # === Error handling === #

    def test_cannot_send_invoice_without_picking(self):
        # Step 1: create invoice
        invoice = self.init_invoice(
            'out_invoice',
            partner=self.partner_a,
            invoice_date='2024-01-28',
            products=[self.product_a],
        )
        invoice.invoice_line_ids[0].discount = 10
        invoice.action_post()

        send_and_print = self.create_send_and_print(invoice)
        self.assertTrue(send_and_print.extra_edi_checkboxes.get('ke_oscu', {}).get('checked'))
        with self.assertRaises(UserError):
            send_and_print.action_send_and_print()

    def test_cannot_send_picking_without_invoice(self):
        picking = self.env['stock.picking'].create({
            'location_id': self.stock_location.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'partner_id': self.partner_a.id,
            'state': 'draft',
            'move_ids': [Command.create({
                'name': self.product_a.name,
                'location_id': self.stock_location.id,
                'location_dest_id': self.customer_location.id,
                'product_id': self.product_a.id,
                'product_uom_qty': 1,
                'product_uom': self.product_a.uom_id.id,
                'description_picking': self.product_a.name,
            })]
        })

        picking.button_validate()

        self.assertTrue(picking.l10n_ke_validation_msg)

    def test_constrain_product_quantity(self):
        """
        Test that a negative quantity can be created in a location without a warehouse in a Kenyan company.
        """
        location_without_warehouse = self.env['stock.location'].create({
            'name': 'location_without_warehouse',
            'usage': 'internal',
        })
        quant = self.env['stock.quant'].create({
            'product_id': self.product_a.id,
            'quantity': -1,
            'location_id': location_without_warehouse.id,
        })
        self.assertEqual(quant.quantity, -1)
