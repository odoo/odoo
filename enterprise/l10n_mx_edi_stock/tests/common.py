from odoo import Command
from odoo.addons.l10n_mx_edi_extended.tests.common import TestMxExtendedEdiCommon


class TestMXEdiStockCommon(TestMxExtendedEdiCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.customer_location = cls.env.ref('stock.stock_location_customers')

        cls.custom_regime_imd = cls.env.ref('l10n_mx_edi_stock.l10n_mx_edi_customs_regime_imd')
        cls.custom_regime_exd = cls.env.ref('l10n_mx_edi_stock.l10n_mx_edi_customs_regime_exd')

        cls.product.write({
            'is_storable': True,
            'unspsc_code_id': cls.env.ref('product_unspsc.unspsc_code_56101500').id,
            'weight': 1,
        })

        cls.operator_pedro = cls.env['res.partner'].create({
            'name': 'Amigo Pedro',
            'vat': 'VAAM130719H60',
            'street': 'JESUS VALDES SANCHEZ',
            'city': 'Arteaga',
            'country_id': cls.env.ref('base.mx').id,
            'state_id': cls.env.ref('base.state_mx_coah').id,
            'zip': '25350',
            'l10n_mx_edi_operator_licence': 'a234567890',
        })

        cls.vehicle_pedro = cls.env['l10n_mx_edi.vehicle'].create({
            'name': 'DEMOPERMIT',
            'transport_insurer': 'DEMO INSURER',
            'transport_insurance_policy': 'DEMO POLICY',
            'transport_perm_sct': 'TPAF10',
            'vehicle_model': '2020',
            'vehicle_config': 'T3S1',
            'vehicle_licence': 'ABC123',
            'trailer_ids': [Command.create({'name': 'trail1', 'sub_type': 'CTR003'})],
            'environment_insurer': 'DEMO INSURER',
            'environment_insurance_policy': 'DEMO INSURER POLICY',
            'figure_ids': [
                Command.create({
                    'type': '01',
                    'operator_id': cls.operator_pedro.id,
                }),
                Command.create({
                    'type': '02',
                    'operator_id': cls.env.company.partner_id.id,
                    'part_ids': [(4, cls.env.ref('l10n_mx_edi_stock.l10n_mx_edi_part_05').id)],
                }),
            ],
        })

    def _create_warehouse(self, **kwargs):
        return self.env['stock.warehouse'].create({
            'name': 'New Warehouse',
            'reception_steps': 'one_step',
            'delivery_steps': 'ship_only',
            'code': 'NWH',
            **kwargs,
        })

    def _create_picking(self, warehouse, outgoing=True, picking_vals=None, move_vals=None):
        picking_vals = picking_vals or {}
        picking = self.env['stock.picking'].create({
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.customer_location.id,
            'picking_type_id': warehouse.out_type_id.id if outgoing else warehouse.in_type_id.id,
            'partner_id': self.partner_mx.id,
            'l10n_mx_edi_transport_type': '01',
            'l10n_mx_edi_vehicle_id': self.vehicle_pedro.id,
            'l10n_mx_edi_gross_vehicle_weight': 2.0,
            'l10n_mx_edi_distance': 120,
            'state': 'draft',
            **picking_vals,
        })

        move_vals = move_vals or {}
        self.env['stock.move'].create({
            'name': self.product.name,
            'product_id': self.product.id,
            'product_uom_qty': 10,
            'product_uom': self.product.uom_id.id,
            'picking_id': picking.id,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': self.customer_location.id,
            'state': 'confirmed',
            'description_picking': self.product.name,
            'company_id': warehouse.company_id.id,
            **move_vals,
        })

        self.env['stock.quant']._update_available_quantity(self.product, warehouse.lot_stock_id, 10.0)
        picking.action_confirm()
        picking.action_assign()
        picking.move_ids[0].move_line_ids[0].quantity = 10
        picking.move_ids[0].picked = True
        picking._action_done()
        return picking

    def _assert_picking_cfdi(self, picking, filename):
        document = picking.l10n_mx_edi_document_ids.filtered(lambda x: x.state == 'picking_sent')[:1]
        self.assertTrue(document)
        self._assert_document_cfdi(document, filename)
