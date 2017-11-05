# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestStreetFields(TransactionCase):

    def setUp(self):
        super(TestStreetFields, self).setUp()
        self.Partner = self.env['res.partner']
        self.env.ref('base.be').write({'street_format': '%(street_name)s, %(street_number)s/%(street_number2)s'})
        self.env.ref('base.us').write({'street_format': '%(street_number)s/%(street_number2)s %(street_name)s'})
        self.env.ref('base.ch').write({'street_format': 'header %(street_name)s, %(street_number)s - %(street_number2)s trailer'})

    def create_and_assert(self, partner_name, country_id, street, street_name, street_number, street_number2):
        partner = self.Partner.create({'name': partner_name + '-1', 'street': street, 'country_id': country_id})
        self.assertEqual(partner.street_name or '', street_name, 'wrong street name for %s: %s' % (partner_name, partner.street_name))
        self.assertEqual(partner.street_number or '', street_number, 'wrong house number for %s: %s' % (partner_name, partner.street_number))
        self.assertEqual(partner.street_number2 or '', street_number2, 'wrong door number for %s: %s' % (partner_name, partner.street_number2))
        partner = self.Partner.create({
            'name': partner_name + '-2',
            'street_name': street_name,
            'street_number': street_number,
            'street_number2': street_number2,
            'country_id': country_id,
        })
        self.assertEqual(partner.street or '', street, 'wrong street for %s: %s' % (partner_name, partner.street))
        return partner

    def write_and_assert(self, partner, vals, street, street_name, street_number, street_number2):
        partner.write(vals)
        self.assertEqual(partner.street_name or '', street_name, 'wrong street name: %s' % partner.street_name)
        self.assertEqual(partner.street_number or '', street_number, 'wrong house number: %s' % partner.street_number)
        self.assertEqual(partner.street_number2 or '', street_number2, 'wrong door number: %s' % partner.street_number2)
        self.assertEqual(partner.street or '', street, 'wrong street: %s' % partner.street)

    def test_00_res_partner_name_create(self):
        self.create_and_assert('Test00', self.env.ref('base.us').id, '40/2b Chaussee de Namur', 'Chaussee de Namur', '40', '2b')
        self.create_and_assert('Test01', self.env.ref('base.us').id, '40 Chaussee de Namur', 'Chaussee de Namur', '40', '')
        self.create_and_assert('Test02', self.env.ref('base.us').id, 'Chaussee de Namur', 'de Namur', 'Chaussee', '')

    def test_01_header_trailer(self):
        self.create_and_assert('Test10', self.env.ref('base.ch').id, 'header Chaussee de Namur, 40 - 2b trailer', 'Chaussee de Namur', '40', '2b')
        self.create_and_assert('Test11', self.env.ref('base.ch').id, 'header Chaussee de Namur, 40 trailer', 'Chaussee de Namur', '40', '')
        self.create_and_assert('Test12', self.env.ref('base.ch').id, 'header Chaussee de Namur trailer', 'Chaussee de Namur', '', '')

    def test_02_res_partner_write(self):
        p1 = self.create_and_assert('Test20', self.env.ref('base.be').id, 'Chaussee de Namur, 40/2b', 'Chaussee de Namur', '40', '2b')
        self.write_and_assert(p1, {'street': 'Chaussee de Namur, 43'}, 'Chaussee de Namur, 43', 'Chaussee de Namur', '43', '')
        self.write_and_assert(p1, {'street': 'Chaussee de Namur'}, 'Chaussee de Namur', 'Chaussee de Namur', '', '')
        self.write_and_assert(p1, {'street_name': 'Chee de Namur', 'street_number': '40'}, 'Chee de Namur, 40', 'Chee de Namur', '40', '')
        self.write_and_assert(p1, {'street_number2': '4'}, 'Chee de Namur, 40/4', 'Chee de Namur', '40', '4')
        #we don't recompute the street fields when we change the country
        self.write_and_assert(p1, {'country_id': self.env.ref('base.us').id}, 'Chee de Namur, 40/4', 'Chee de Namur', '40', '4')
