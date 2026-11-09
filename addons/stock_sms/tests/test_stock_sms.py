# Part of Odoo. See LICENSE file for full copyright and licensing details.

import threading
from unittest.mock import patch

from odoo.addons.stock.tests.common import TestStockCommon
from odoo.modules.registry import Registry


class TestStockSms(TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.stock_move_sms_validation = True
        cls.env.company.has_received_warning_stock_sms = False
        cls.partner_1.phone = '+32456001122'
        cls.transit_location = cls.env['stock.location'].create({'name': 'Transit', 'usage': 'transit'})

    def _create_picking(self, location_dest_id):
        return self.PickingObj.create({
            'picking_type_id': self.picking_type_out,
            'location_id': self.stock_location,
            'location_dest_id': location_dest_id,
            'partner_id': self.partner_1.id,
        })

    def test_confirmation_sms_only_for_customer_destination(self):
        customer_picking = self._create_picking(self.customer_location)
        supplier_picking = self._create_picking(self.supplier_location)
        transit_picking = self._create_picking(self.transit_location.id)
        pickings = customer_picking | supplier_picking | transit_picking
        with patch.object(threading.current_thread(), 'testing', False), \
                patch.object(Registry, 'in_test_mode', return_value=False), \
                patch.object(self.registry['stock.picking'], '_message_sms_with_template') as mock_sms:
            pickings._send_confirmation_email()
            self.assertEqual(mock_sms.call_count, 1)
            self.assertEqual(mock_sms.call_args.kwargs['partner_ids'], self.partner_1.ids)
            warn_pickings = pickings._check_warn_sms()
        self.assertEqual(warn_pickings, customer_picking)
