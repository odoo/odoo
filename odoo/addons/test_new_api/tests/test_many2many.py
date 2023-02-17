# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo import Command


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

    def test_commands_inactive(self):
        """
        Check the behaviour of LINK, UNLINK, and CLEAR commands for many2many fields.
        If this test is broken the optimization for load_records (see must_udpate)
        may be broken.
        """
        def create_data(linked):
            tag = self.env['test_new_api.multi.tag'].create({})
            tag.active = False
            line = self.env['test_new_api.multi.line'].create({'tags': [Command.link(tag.id)] if linked else False})
            self.assertEqual(line.tags.ids, [])
            self.assertEqual(line.with_context(active_test=False).tags.ids, [tag.id] if linked else [])
            return line, tag

        fname = 'tags'
        field = self.env['test_new_api.multi.line']._fields[fname]

        # Ensure that LINK command ADDS inactive records
        line, tag = create_data(True)
        # convert_to_cache with field values does not include inactive records
        self.assertEqual(
            field.convert_to_cache(line[fname], line),
            (),
        )
        # we can get the inactive records explicitly
        self.assertEqual(
            field.convert_to_cache(line.with_context(active_test=False)[fname], line),
            (tag.id,),
        )
        commands = [Command.link(tag.id)]
        # convert_to_cache with LINK command includes inactive records
        self.assertEqual(
            field.convert_to_cache(commands, line),
            (tag.id,),
        )
        # The right way to compare them
        self.assertEqual(
            field.convert_to_cache(line.with_context(active_test=False)[fname], line),
            field.convert_to_cache(commands, line),
        )
        # Running the commands and checking the result
        line.tags = commands
        self.assertEqual(line.tags.ids, [])
        self.assertEqual(line.with_context(active_test=False).tags.ids, [tag.id])

        # Ensure that UNLINK command REMOVES inactive records
        line, tag = create_data(False)
        commands = [Command.unlink(tag.id)]
        # convert_to_cache with UNLINK command removes inactive records
        self.assertEqual(
            field.convert_to_cache(commands, line),
            (),
        )
        # The right way to compare them
        self.assertEqual(
            field.convert_to_cache(line.with_context(active_test=False)[fname], line),
            field.convert_to_cache(commands, line),
        )
        # Running the commands and checking the result
        line.tags = commands
        self.assertEqual(line.tags.ids, [])
        self.assertEqual(line.with_context(active_test=False).tags.ids, [])

        # Ensure that CLEAR command REMOVES inactive records
        line, tag = create_data(True)
        commands = [Command.clear()]
        # convert_to_cache with CLEAR command is empty
        self.assertEqual(
            field.convert_to_cache(commands, line),
            (),
        )
        # convert_to_cache with field values does not include inactive records
        self.assertEqual(
            field.convert_to_cache(line[fname], line),
            (),
        )
        # The right way to compare them
        self.assertEqual(
            field.convert_to_cache(line[fname], line),
            field.convert_to_cache(commands, line),
        )
        # Running the commands and checking the result
        line.tags = commands
        self.assertEqual(line.tags.ids, [])
        self.assertEqual(line.with_context(active_test=False).tags.ids, [])
