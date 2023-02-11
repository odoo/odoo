# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event.tests.common import TestEventCommon


class TestEventBoothCommon(TestEventCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventBoothCommon, cls).setUpClass()

        cls.event_booth_category_1 = cls.env['event.booth.category'].create({
            'name': 'Standard',
            'description': '<p>Standard</p>',
        })
        cls.event_booth_category_2 = cls.env['event.booth.category'].create({
            'name': 'Premium',
            'description': '<p>Premium</p>',
        })

        cls.event_type_complex.write({
            'event_type_booth_ids': [
                (5, 0),
                (0, 0,
                 {'name': 'Standard 1', 'booth_category_id': cls.event_booth_category_1.id}),
                (0, 0,
                 {'name': 'Premium 1', 'booth_category_id': cls.event_booth_category_2.id}),
            ],
        })
