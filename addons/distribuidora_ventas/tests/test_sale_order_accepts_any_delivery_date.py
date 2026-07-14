from datetime import datetime

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSaleOrderAcceptsAnyDeliveryDate(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Cliente Test'})

    def test_tuesday_is_accepted(self):
        # 2026-07-14 es martes: antes de este cambio, la restriccion de
        # distribuidora_ventas lo rechazaba.
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'commitment_date': datetime(2026, 7, 14, 8, 0, 0),
        })
        self.assertTrue(order)

    def test_sunday_is_accepted(self):
        # 2026-07-19 es domingo: antes de este cambio, tambien se rechazaba.
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'commitment_date': datetime(2026, 7, 19, 8, 0, 0),
        })
        self.assertTrue(order)
