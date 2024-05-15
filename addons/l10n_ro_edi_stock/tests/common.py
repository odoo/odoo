from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon


class TestL10nRoEdiStockCommon(ValuationReconciliationTestCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('ro')
    def setUpClass(cls):
        super().setUpClass()

        cls.warehouse = cls.company_data['default_warehouse']
        cls.customer_location = cls.env.ref('stock.stock_location_customers').id
        cls.stock_location = cls.warehouse.lot_stock_id.id

        # Disable auto-batching
        cls.warehouse.out_type_id.auto_batch = False
        cls.warehouse.in_type_id.auto_batch = False

    @classmethod
    def create_stock_picking(cls, partner, name=False, location_id=None, location_dest_id=None, picking_type=None, product_data=None):
        picking = cls.env['stock.picking'].create({
            'name': name or f'{cls.env.company.name} picking',
            'partner_id': partner.id,
            'location_id': location_id if location_id else cls.stock_location,
            'location_dest_id': location_dest_id if location_dest_id else cls.customer_location,
            'picking_type_id': picking_type.id if picking_type else cls.warehouse.out_type_id.id,
        })

        for data in product_data or []:
            product = data['product_id']
            cls.env['stock.move'].create({
                'name': product.name,
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'product_uom_qty': data['product_uom_qty'],
                'quantity': data['quantity'],
                'procure_method': data.get('procure_method', 'make_to_stock'),
                'picking_id': picking.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'company_id': cls.env.company.id
            })

        return picking

    def change_product_qty(self, product, new_quantity, product_tmpl=None):
        self.env['stock.change.product.qty'].create({
            'product_id': product.id,
            'product_tmpl_id': product_tmpl.id if product_tmpl else product.product_tmpl_id.id,
            'new_quantity': new_quantity,
        }).change_product_qty()
