from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.l10n_ro_edi_stock.tests.test_etransport_flows import TestETransportFlows


@tagged("post_install_l10n", "post_install", "-at_install")
class TestBatchStockETransport(TestETransportFlows):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sale_orders = cls.env['sale.order']
        for _ in range(2):
            cls.sale_orders |= cls._create_sale_order({'partner_id': cls.customer.id, 'warehouse_id': cls.warehouse.id})

    def test_multistep_delivery_validation_constraints(self):
        """
        Verify that in a multi-step flow:
        1. Internal steps (PICK and/or PACK) are excluded from E-Transport constraints
        2. Outgoing steps (SHIP) correctly enforce E-Transport mandatory fields
        """
        self.warehouse.delivery_steps = 'pick_ship'

        sale_order = self._create_sale_order({'partner_id': self.customer.id, 'warehouse_id': self.warehouse.id})

        pick_picking = sale_order.picking_ids
        pick_picking.button_validate()
        self.assertFalse(pick_picking.l10n_ro_edi_stock_enable, "An internal transfer should not be eligible for E-Transport.")
        ship_picking = pick_picking._get_next_transfers()

        with self.assertRaisesRegex(UserError, f'The picking {ship_picking.name} is missing a delivery carrier.'):
            ship_picking.button_validate()
        ship_picking.carrier_id = self.carrier

        with self.assertRaisesRegex(UserError, f'The delivery carrier of {ship_picking.name} is missing the partner field value.'):
            ship_picking.button_validate()
        ship_picking.carrier_id.l10n_ro_edi_stock_partner_id = self.shipping_partner

        ship_picking.button_validate()
        self.assertEqual(ship_picking.state, 'done')

    def test_batch_validation_with_missing_carrier(self):
        """
        Ensure that E-Transport validation constraints are enforced during batch validation.
        If one picking in the batch is missing a carrier, the whole batch validation should fail.
        """
        pickings = self.sale_orders.picking_ids
        pickings[0].carrier_id = self.carrier
        pickings[0].carrier_id.l10n_ro_edi_stock_partner_id = self.shipping_partner

        batch = self.env['stock.picking.batch'].create({
            'picking_ids': [Command.set(pickings.ids)],
            'picking_type_id': self.warehouse.out_type_id.id,
        })
        batch.action_confirm()

        self.assertRecordValues(pickings.sorted('sale_id'), [
            {'sale_id': self.sale_orders[0].id, 'l10n_ro_edi_stock_enable': True, 'l10n_ro_edi_stock_enable_send': False, 'picking_type_code': 'outgoing'},
            {'sale_id': self.sale_orders[1].id, 'l10n_ro_edi_stock_enable': True, 'l10n_ro_edi_stock_enable_send': False, 'picking_type_code': 'outgoing'},
        ])
        self.assertRecordValues(batch, [
            {'l10n_ro_edi_stock_enable': True, 'l10n_ro_edi_stock_enable_send': True, 'picking_ids': pickings.ids},
        ])

        with self.assertRaisesRegex(UserError, f'The picking {pickings[1].name} is missing a delivery carrier.'):
            batch.action_done()
        pickings[1].carrier_id = self.carrier
        pickings[1].carrier_id.l10n_ro_edi_stock_partner_id = self.shipping_partner

        batch.action_done()
        self.assertEqual(batch.state, 'done')

    def test_etransport_send_button_visibility_logic(self):
        """
        Test the logic determining where the 'Send to E-Transport' action is available.
        - Should be on the Batch if the picking is grouped.
        - Should move back to the Picking if it is removed from the batch (e.g., validated separately).
        """
        pickings = self.sale_orders.picking_ids
        pickings.carrier_id = self.carrier
        pickings.carrier_id.l10n_ro_edi_stock_partner_id = self.shipping_partner

        self.assertFalse(pickings.batch_id)
        batch = self.env['stock.picking.batch'].create({
            'picking_ids': [Command.set(pickings.ids)],
            'picking_type_id': self.warehouse.out_type_id.id,
        })
        batch.action_confirm()

        # Can send the batch but not the individual pickings
        self.assertRecordValues(pickings.sorted('sale_id'), [
            {'sale_id': self.sale_orders[0].id, 'l10n_ro_edi_stock_enable': True, 'l10n_ro_edi_stock_enable_send': False, 'picking_type_code': 'outgoing'},
            {'sale_id': self.sale_orders[1].id, 'l10n_ro_edi_stock_enable': True, 'l10n_ro_edi_stock_enable_send': False, 'picking_type_code': 'outgoing'},
        ])
        self.assertRecordValues(batch, [
            {'l10n_ro_edi_stock_enable': True, 'l10n_ro_edi_stock_enable_send': True, 'picking_ids': pickings.ids},
        ])

        pickings[0].button_validate()
        self.assertEqual(pickings[0].state, 'done')
        self.assertRecordValues(pickings.sorted('sale_id'), [
            # Can send as Done and not in the batch anymore
            {'sale_id': self.sale_orders[0].id, 'l10n_ro_edi_stock_enable': True, 'l10n_ro_edi_stock_enable_send': True, 'picking_type_code': 'outgoing'},
            # In the batch so should be sent in the batch
            {'sale_id': self.sale_orders[1].id, 'l10n_ro_edi_stock_enable': True, 'l10n_ro_edi_stock_enable_send': False, 'picking_type_code': 'outgoing'},
        ])
        self.assertRecordValues(batch, [
            {'l10n_ro_edi_stock_enable': True, 'l10n_ro_edi_stock_enable_send': True, 'picking_ids': pickings[1].ids},
        ])

        batch.action_done()
        self.assertEqual(batch.state, 'done')
