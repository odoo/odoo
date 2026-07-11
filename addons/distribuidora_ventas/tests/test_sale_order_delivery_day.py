from datetime import datetime

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSaleOrderDeliveryDay(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Cliente Test'})

    def test_monday_is_accepted(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'commitment_date': datetime(2026, 7, 13, 8, 0, 0),  # lunes
        })
        self.assertTrue(order)

    def test_wednesday_is_accepted(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'commitment_date': datetime(2026, 7, 15, 8, 0, 0),  # miercoles
        })
        self.assertTrue(order)

    def test_friday_is_accepted(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'commitment_date': datetime(2026, 7, 17, 8, 0, 0),  # viernes
        })
        self.assertTrue(order)

    def test_tuesday_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'commitment_date': datetime(2026, 7, 14, 8, 0, 0),  # martes
            })

    def test_sunday_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.env['sale.order'].create({
                'partner_id': self.partner.id,
                'commitment_date': datetime(2026, 7, 19, 8, 0, 0),  # domingo
            })

    def test_monday_evening_local_is_accepted_despite_utc_rollover(self):
        # 2026-07-14 02:00 UTC == 2026-07-13 20:00 America/Costa_Rica (lunes noche).
        # The old UTC-naive check saw "martes" here and wrongly rejected it.
        order = self.env['sale.order'].with_context(tz='America/Costa_Rica').create({
            'partner_id': self.partner.id,
            'commitment_date': datetime(2026, 7, 14, 2, 0, 0),
        })
        self.assertTrue(order)

    def test_sunday_evening_local_is_rejected_despite_utc_showing_monday(self):
        # 2026-07-13 02:00 UTC == 2026-07-12 20:00 America/Costa_Rica (domingo noche).
        # The old UTC-naive check saw "lunes" here and wrongly accepted it.
        with self.assertRaises(ValidationError):
            self.env['sale.order'].with_context(tz='America/Costa_Rica').create({
                'partner_id': self.partner.id,
                'commitment_date': datetime(2026, 7, 13, 2, 0, 0),
            })
