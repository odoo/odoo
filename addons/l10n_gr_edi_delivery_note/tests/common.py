from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestMyDATADeliveryNoteCommon(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('gr')
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.write({
            'name': 'Ελληνική Εταιρεία',
            'vat': 'EL047747270',
            'street': 'Akti Miaouli 10',
            'zip': '18538',
            'city': 'Πειραιάς',
            'l10n_gr_edi_test_env': True,
            'l10n_gr_edi_aade_id': 'odoo_test_mydata',
            'l10n_gr_edi_aade_key': 'test_key',
        })
        cls.partner_a.write({
            'name': 'Πελάτης Α.Ε.',
            'country_id': cls.env.ref('base.gr').id,
            'vat': '047747210',
            'street': 'Othonos 2',
            'zip': '10557',
            'city': 'Athens',
        })
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1) \
            or cls.env['stock.warehouse'].create({
                'name': 'Greek Warehouse',
                'code': 'GWH',
                'company_id': cls.env.company.id,
            })
        cls.customer_location = cls.env.ref('stock.stock_location_customers')

    def _create_picking(self, validate=True, uom=None, **kwargs):
        product = self.product_a
        if uom:
            product = self.env['product.product'].create({
                'name': f'Product in {uom.name}',
                'uom_id': uom.id,
                'uom_po_id': uom.id,
            })
        picking = self.env['stock.picking'].create({
            'partner_id': self.partner_a.id,
            'picking_type_id': self.warehouse.out_type_id.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'location_dest_id': self.customer_location.id,
            'move_ids': [Command.create({
                'name': product.name,
                'product_id': product.id,
                'product_uom_qty': 2.0,
                'product_uom': product.uom_id.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'location_dest_id': self.customer_location.id,
            })],
            **kwargs,
        })
        # Fill the myDATA addresses the same way the form view does
        picking._onchange_l10n_gr_edi_loading_address()
        picking._onchange_l10n_gr_edi_delivery_address()
        if validate:
            picking.action_confirm()
            picking.move_ids.quantity = 2.0
            picking.move_ids.picked = True
            picking.button_validate()
        return picking
