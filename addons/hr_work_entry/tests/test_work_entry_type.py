# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestWorkEntryType(TransactionCase):

    def test_duplicate_work_entry_type_same_country(self):
        country_be = self.env.ref('base.be')
        self.env['hr.work.entry.type'].create({
            'code': 'test123',
            'name': "Test we type",
            'country_id': country_be.id,

        })
        with self.assertRaises(
            UserError,
            msg="It should not be possible to create two work entry types with the same code in the same country",
        ):
            self.env['hr.work.entry.type'].create({
                'code': 'test123',
                'name': "Test we type",
                'country_id': country_be.id,
            })

        with self.assertRaises(
            UserError,
            msg="It should not be possible to create two work entry types at the same time with the same code in the same country",
        ):
            self.env['hr.work.entry.type'].create([
                {
                    'code': 'test456',
                    'name': "Test we type",
                    'country_id': country_be.id,
                },
                {
                    'code': 'test456',
                    'name': "Test we type",
                    'country_id': country_be.id,
                },
            ])

    def test_duplicate_work_entry_type_all_countries(self):
        self.env['hr.work.entry.type'].create({
            'code': 'test123',
            'name': "Test we type",
            'country_id': False,

        })
        with self.assertRaises(
            UserError,
            msg="It should not be possible to create two work entry types with the same code for all countries",
        ):
            self.env['hr.work.entry.type'].create({
                'code': 'test123',
                'name': "Test we type",
                'country_id': False,
            })

        with self.assertRaises(
            UserError,
            msg="It should not be possible to create two work entry types at the same time with the same code for all countries",
        ):
            self.env['hr.work.entry.type'].create([
                {
                    'code': 'test456',
                    'name': "Test we type",
                    'country_id': False,
                },
                {
                    'code': 'test456',
                    'name': "Test we type",
                    'country_id': False,
                },
            ])

    def test_unique_work_entry_types(self):
        """
        No error should be raised if the work entry codes are unique per country_id
        """
        country_be = self.env.ref('base.be')
        country_us = self.env.ref('base.us')

        # creating them one by one. `self` should contain one record only
        self.env['hr.work.entry.type'].create({
            'code': 'test123',
            'name': "Test we type",
            'country_id': country_be.id,

        })
        self.env['hr.work.entry.type'].create({
            'code': 'test123',
            'name': "Test we type",
            'country_id': country_us.id,
        })
        self.env['hr.work.entry.type'].create({
            'code': 'test123',
            'name': "Test we type",
            'country_id': False
        })

        # creating them in batch. `self` should have multiple records at once
        self.env['hr.work.entry.type'].create([
            {
                'code': 'test456',
                'name': "Test we type",
                'country_id': False,
            },
            {
                'code': 'test456',
                'name': "Test we type",
                'country_id': country_us.id,
            },
            {
                'code': 'test456',
                'name': "Test we type",
                'country_id': country_be.id,
            },
        ])
