# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_event.tests.common import TestEventOnlineCommon


class TestEventExhibitorCommon(TestEventOnlineCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventExhibitorCommon, cls).setUpClass()

        # Sponsorship data
        cls.sponsor_type_0 = cls.env['event.sponsor.type'].create({
            'name': 'GigaTop',
            'sequence': 1,
        })
        cls.sponsor_0_partner = cls.env['res.partner'].create({
            'name': 'EventSponsor',
            'country_id': cls.env.ref('base.be').id,
            'email': 'event.sponsor@example.com',
            'phone': '04856112233',
        })

        cls.sponsor_0 = cls.env['event.sponsor'].create({
            'partner_id': cls.sponsor_0_partner.id,
            'event_id': cls.event_0.id,
            'sponsor_type_id': cls.sponsor_type_0.id,
            'hour_from': 8.0,
            'hour_to': 18.0,
        })
