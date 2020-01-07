# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tests.common import SavepointCase


class TestStreetFields(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestStreetFields, cls).setUpClass()
        cls.Partner = cls.env['res.partner']
        cls.env.ref('base.be').write({'street_format': '%(street_name)s, %(street_number)s/%(street_number2)s'})
        cls.env.ref('base.us').write({'street_format': '%(street_number)s/%(street_number2)s %(street_name)s'})
        cls.env.ref('base.ch').write({'street_format': 'header %(street_name)s, %(street_number)s - %(street_number2)s trailer'})
        cls.env.ref('base.mx').write({'street_format': '%(street_name)s %(street_number)s/%(street_number2)s'})

    def assertStreetVals(self, record, street_data):
        for key, val in street_data.items():
            if key not in ['street', 'street_name', 'street_number', 'street_number2', 'name', 'city', 'country_id']:
                continue
            if isinstance(record[key], models.BaseModel):
                self.assertEqual(record[key].id, val, 'Wrongly formatted street field %s: expected %s, received %s' % (key, val, record[key]))
            else:
                self.assertEqual(record[key], val, 'Wrongly formatted street field %s: expected %s, received %s' % (key, val, record[key]))

    def test_company_create(self):
        """ Will test the compute and inverse methods of street fields when creating partner records. """
        us_id = self.env.ref('base.us').id
        mx_id = self.env.ref('base.mx').id
        ch_id = self.env.ref('base.ch').id
        input_values = [
            {'country_id': us_id, 'street': '40/2b Chaussee de Namur'},
            {'country_id': us_id, 'street': '40 Chaussee de Namur'},
            {'country_id': us_id, 'street': 'Chaussee de Namur'},
            {'country_id': mx_id, 'street': 'Av. Miguel Hidalgo y Costilla 601'},
            {'country_id': ch_id, 'street': 'header Chaussee de Namur, 40 - 2b trailer'},
            {'country_id': ch_id, 'street': 'header Chaussee de Namur, 40 trailer'},
            {'country_id': ch_id, 'street': 'header Chaussee de Namur trailer'},
        ]
        expected = [
            {'street_name': 'Chaussee de Namur', 'street_number': '40', 'street_number2': '2b'},
            {'street_name': 'Chaussee de Namur', 'street_number': '40', 'street_number2': False},
            {'street_name': 'de Namur', 'street_number': 'Chaussee', 'street_number2': False},
            {'street_name': 'Av.', 'street_number': 'Miguel Hidalgo y Costilla 601', 'street_number2': False},
            {'street_name': 'Chaussee de Namur', 'street_number': '40', 'street_number2': '2b'},
            {'street_name': 'Chaussee de Namur', 'street_number': '40', 'street_number2': False},
            {'street_name': 'Chaussee de Namur', 'street_number': False, 'street_number2': False}
        ]

        # test street -> street values (compute)
        for idx, (company_values, expected_vals) in enumerate(zip(input_values, expected)):
            company_values['name'] = 'Test-%2d' % idx
            company = self.env['res.company'].create(company_values)
            self.assertStreetVals(company, expected_vals)
            self.assertStreetVals(company.partner_id, expected_vals)

        # test street_values -> street (inverse)
        for idx, (company_values, expected_vals) in enumerate(zip(input_values, expected)):
            company_values['name'] = 'TestNew-%2d' % idx
            expected_street = company_values.pop('street')
            company_values.update(expected_vals)
            company = self.env['res.company'].create(company_values)
            self.assertEqual(company.street, expected_street)
            self.assertStreetVals(company, company_values)
            self.assertEqual(company.partner_id.street, expected_street)
            self.assertStreetVals(company.partner_id, company_values)

    def test_company_write(self):
        """ Will test the compute and inverse methods of street fields when updating partner records. """
        be_id = self.env.ref('base.be').id
        company = self.env['res.company'].create({
            'name': 'Test',
            'country_id': be_id,
            'street': 'Chaussee de Namur, 40/2b'
        })
        self.assertStreetVals(company, {'street_name': 'Chaussee de Namur', 'street_number': '40', 'street_number2': '2b'})

        input_values = [
            {'street': 'Chaussee de Namur, 43'},
            {'street': 'Chaussee de Namur'},
            {'street_name': 'Chee de Namur', 'street_number': '40'},
            {'street_number2': '4'},
            {'country_id': self.env.ref('base.us').id},
        ]
        expected = [
            {'street_name': 'Chaussee de Namur', 'street_number': '43', 'street_number2': False},
            {'street_name': 'Chaussee de Namur', 'street_number': False, 'street_number2': False},
            {'street_name': 'Chee de Namur', 'street_number': '40', 'street_number2': False, 'street': 'Chee de Namur, 40'},
            {'street_name': 'Chee de Namur', 'street_number': '40', 'street_number2': '4', 'street': 'Chee de Namur, 40/4'},
            {'street_name': 'Chee de Namur', 'street_number': '40', 'street_number2': '4', 'street': '40/4 Chee de Namur'},
        ]

        # test both compute and inverse (could probably be pimp)
        for write_values, expected_vals in zip(input_values, expected):
            company.write(write_values)
            self.assertStreetVals(company, expected_vals)
            self.assertStreetVals(company.partner_id, expected_vals)

    def test_partner_create(self):
        """ Will test the compute and inverse methods of street fields when creating partner records. """
        us_id = self.env.ref('base.us').id
        mx_id = self.env.ref('base.mx').id
        ch_id = self.env.ref('base.ch').id
        input_values = [
            {'country_id': us_id, 'street': '40/2b Chaussee de Namur'},
            {'country_id': us_id, 'street': '40 Chaussee de Namur'},
            {'country_id': us_id, 'street': 'Chaussee de Namur'},
            {'country_id': mx_id, 'street': 'Av. Miguel Hidalgo y Costilla 601'},
            {'country_id': ch_id, 'street': 'header Chaussee de Namur, 40 - 2b trailer'},
            {'country_id': ch_id, 'street': 'header Chaussee de Namur, 40 trailer'},
            {'country_id': ch_id, 'street': 'header Chaussee de Namur trailer'},
        ]
        expected = [
            {'street_name': 'Chaussee de Namur', 'street_number': '40', 'street_number2': '2b'},
            {'street_name': 'Chaussee de Namur', 'street_number': '40', 'street_number2': False},
            {'street_name': 'de Namur', 'street_number': 'Chaussee', 'street_number2': False},
            {'street_name': 'Av.', 'street_number': 'Miguel Hidalgo y Costilla 601', 'street_number2': False},
            {'street_name': 'Chaussee de Namur', 'street_number': '40', 'street_number2': '2b'},
            {'street_name': 'Chaussee de Namur', 'street_number': '40', 'street_number2': False},
            {'street_name': 'Chaussee de Namur', 'street_number': False, 'street_number2': False}
        ]

        # test street -> street values (compute)
        for partner_values, expected_vals in zip(input_values, expected):
            partner_values['name'] = 'Test'
            partner = self.env['res.partner'].create(partner_values)
            self.assertStreetVals(partner, expected_vals)

        # test street_values -> street (inverse)
        for partner_values, expected_vals in zip(input_values, expected):
            partner_values['name'] = 'Test'
            expected_street = partner_values.pop('street')
            partner_values.update(expected_vals)
            partner = self.env['res.partner'].create(partner_values)
            self.assertEqual(partner.street, expected_street)
            self.assertStreetVals(partner, partner_values)

    def test_partner_write(self):
        """ Will test the compute and inverse methods of street fields when updating partner records. """
        be_id = self.env.ref('base.be').id
        partner = self.env['res.partner'].create({
            'name': 'Test',
            'country_id': be_id,
            'street': 'Chaussee de Namur, 40/2b'
        })
        self.assertStreetVals(partner, {'street_name': 'Chaussee de Namur', 'street_number': '40', 'street_number2': '2b'})

        input_values = [
            {'street': 'Chaussee de Namur, 43'},
            {'street': 'Chaussee de Namur'},
            {'street_name': 'Chee de Namur', 'street_number': '40'},
            {'street_number2': '4'},
            {'country_id': self.env.ref('base.us').id},
        ]
        expected = [
            {'street_name': 'Chaussee de Namur', 'street_number': '43', 'street_number2': False},
            {'street_name': 'Chaussee de Namur', 'street_number': False, 'street_number2': False},
            {'street_name': 'Chee de Namur', 'street_number': '40', 'street_number2': False, 'street': 'Chee de Namur, 40'},
            {'street_name': 'Chee de Namur', 'street_number': '40', 'street_number2': '4', 'street': 'Chee de Namur, 40/4'},
            {'street_name': 'Chee de Namur', 'street_number': '40', 'street_number2': '4', 'street': '40/4 Chee de Namur'},
        ]

        # test both compute and inverse (could probably be pimp)
        for write_values, expected_vals in zip(input_values, expected):
            partner.write(write_values)
            self.assertStreetVals(partner, expected_vals)
