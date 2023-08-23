# -*- coding: utf-8 -*-
from odoo import Command
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

    def test_company_access_rights(self):
        """ Test only the records belonging to the companies you have access to are returned when accessing a many2many field. """
        company1, company2 = self.env['res.company'].create([
            {'name': "turlututu"},
            {'name': "tsointsoin"},
        ])

        record = self.env['test_new_api.m2m_access_rights_model2'].create({
            'm2m_ids': [
                Command.create({'company_id': company1.id}),
                Command.create({'company_id': company2.id}),
            ],
        })

        # Create a new user having only access to company1.
        user = self.env['res.users'].create({
            'name': "test_company_access_rights",
            'login': 'test_company_access_rights',
            'password': 'test_company_access_rights',
            'groups_id': [Command.set(self.env.ref('base.group_user').ids)],
            'company_ids': [Command.set(company1.ids)],
            'company_id': company1.id,
        })
        new_env = self.env(user=user)
        record = new_env['test_new_api.m2m_access_rights_model2'].browse(record.id)

        # Clear the cache for model1.
        # At this point, model2 has model1 cached for both companies but the 'active' field in
        # not in cache.
        self.env['test_new_api.m2m_access_rights_model1'].invalidate_model()

        # The orm is not fetching the 'active' field so no access error.
        record.with_context(active_test=False).m2m_ids

        # The orm tries to fetch the 'active' field but since the user doesn't have access to all
        # cached records, it leads to an access error.
        record.m2m_ids
