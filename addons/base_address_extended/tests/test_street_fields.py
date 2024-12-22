# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tests.common import TransactionCase


class TestStreetFields(TransactionCase):

    def test_partner_create(self):
        """ Will test the compute and inverse methods of street fields when creating partner records. """
        mx_id = self.env.ref('base.mx').id
        partner = self.env['res.partner'].create({'name': 'Test Address', 'country_id': mx_id})

        values = [
            ['', '', '', ''],
            ['Place Royale', 'Place Royale', '', ''],
            ['Chaussee de Namur 40a - 2b', 'Chaussee de Namur', '40a', '2b'],
            ['Chaussee de Namur 1', 'Chaussee de Namur', '1', ''],
            ['40 Chaussee de Namur', '40 Chaussee de Namur', '', ''],
            ['Chaussee de Namur, 40 - Apt 2b', 'Chaussee de Namur,', '40', 'Apt 2b'],
            ['header Chaussee de Namur, 40 trailer ', 'header Chaussee de Namur, 40 trailer', '', ''],
            ['\nCl 53\n # 43 - 81', 'Cl 53\n #', '43', '81'],
            ['Street Line 1\nNumber Line 2 44 76', 'Street Line 1\nNumber Line 2 44', '76', ''],
        ]

        for street, name, number, number2 in values:
            # test street -> street values (compute)
            partner.street = street
            self.assertEqual(partner.street_name, name, 'Wrongly formatted street name: expected %s, received %s' % (name, partner.street_name))
            self.assertEqual(partner.street_number, number, 'Wrongly formatted street number: expected %s, received %s' % (number, partner.street_number))
            self.assertEqual(partner.street_number2, number2, 'Wrongly formatted street number2: expected %s, received %s' % (number2, partner.street_number2))

        for street, name, number, number2 in values:
            partner.street_number2 = number2
            partner.street_number = number
            partner.street_name = name
            self.assertEqual(partner.street, street.strip(), 'Wrongly formatted street: expected %s, received %s' % (street, partner.street))

    def test_child_sync(self):
        """ Test that city_id is propagated to (contact-type) children contacts. """
        usa = self.env.ref('base.us')
        new_york_city = self.env['res.city'].create({
            'name': 'New York',
            'country_id': usa.id,
        })
        parent = self.env['res.partner'].create({
            'name': 'Parent Company',
            'country_id': usa.id,
            'city_id': new_york_city.id,
        })
        child = self.env['res.partner'].create({
            'name': 'Child Contact',
            'type': 'contact',
            'parent_id': parent.id,
        })
        self.assertRecordValues(child, [{
            'name': 'Child Contact',
            'country_id': usa.id,
            'city_id': new_york_city.id,
        }])
