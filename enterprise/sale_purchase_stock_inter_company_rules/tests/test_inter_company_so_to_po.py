# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged
from .common import TestInterCompanyRulesCommonStock


@tagged('post_install', '-at_install')
class TestInterCompanySaleToPurchaseWithStock(TestInterCompanyRulesCommonStock):

    def test_01_inter_company_confirm_purchase_after_delivery(self):
        """ Checks that if inter-company Purchase Orders are generated in a draft state, they can still
            reserve on Inter-Company transit location as if it was an internal location, so that serial delivered
            before the PO validation can still be fetched.
        """
        self.company_b.write({
            'intercompany_generate_purchase_orders': True,
            'intercompany_sync_delivery_receipt': True,
            'intercompany_document_state': 'draft',
        })
        product = self.env['product.product'].create({
            'is_storable': True,
            'tracking': 'serial',
            'name': 'Cross Serial',
            'company_id': False,
        })
        serial = self.env['stock.lot'].create({'name': 'serial', 'product_id': product.id})
        warehouse_a = self.env['stock.warehouse'].search([('company_id', '=', self.company_a.id)], limit=1)
        self.env['stock.quant']._update_available_quantity(product, warehouse_a.lot_stock_id, quantity=1, lot_id=serial)

        # Create a sale order from Company A to Company B
        with Form(self.env['sale.order'].with_company(self.company_a)) as sale_form:
            sale_form.partner_id = self.company_b.partner_id
            with sale_form.order_line.new() as line:
                line.product_id = product
                line.product_uom_qty = 1
            sale_to_b = sale_form.save()
        sale_to_b.with_company(self.company_a).action_confirm()
        self.assertEqual(len(sale_to_b.picking_ids), 1)

        # Verify that PO is created in company B in draft.
        purchase_from_a = self.env['purchase.order'].with_company(self.company_b).search([('partner_ref', '=', sale_to_b.name)])
        self.assertEqual(purchase_from_a.state, 'draft')

        # Do the delivery of Company A
        interco_location = self.env.ref('stock.stock_location_inter_company')
        delivery = sale_to_b.picking_ids
        self.assertEqual(delivery.location_dest_id, interco_location)
        with Form(delivery) as delivery_form:
            with delivery_form.move_ids_without_package.edit(0) as move_form:
                move_form.lot_ids = serial
                move_form.quantity = 1
                move_form.picked = True
            delivery = delivery_form.save()
        delivery.with_company(self.company_a).button_validate()

        # Confirm the PO and check that reservation could be done
        purchase_from_a.with_company(self.company_b).button_confirm()
        self.assertRecordValues(purchase_from_a.picking_ids.move_ids, [{
            'state': 'assigned',
            'quantity': 1,
            'lot_ids': serial.ids,
            'location_id': interco_location.id,
        }])
