# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class Many2manyCase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.ship = self.env['test_new_api.ship'].create({'name': 'Colombus'})
        # the ship contains one prisoner
        self.env['test_new_api.prisoner'].create({
            'name': 'Brian',
            'ship_ids': self.ship.ids,
        })
        # the ship contains one pirate
        self.blackbeard = self.env['test_new_api.pirate'].create({
            'name': 'Black Beard',
            'ship_ids': self.ship.ids,
        })
        self.redbeard = self.env['test_new_api.pirate'].create({'name': 'Red Beard'})

    def test_not_in_relation(self):
        pirates = self.env['test_new_api.pirate'].search([('ship_ids', 'not in', self.ship.ids)])
        self.assertEqual(len(pirates), 1)
        self.assertEqual(pirates, self.redbeard)

    def test_not_in_relation_as_query(self):
        # ship_ids is a Query object
        ship_ids = self.env['test_new_api.ship']._search([('name', '=', 'Colombus')])
        pirates = self.env['test_new_api.pirate'].search([('ship_ids', 'not in', ship_ids)])
        self.assertEqual(len(pirates), 1)
        self.assertEqual(pirates, self.redbeard)
