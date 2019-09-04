# -*- coding: utf-8 -*-

from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase
# import ipdb; ipdb.set_trace()

# @tagged('post_install', '-at_install')    
class TestPartnerAutocompleteFields(TransactionCase):

    def setUp(self):
        super(TestPartnerAutocompleteFields, self).setUp()

        self.be = self.env.ref('base.be')
        self.state_be = self.env['res.country.state'].create(dict(
                                           name="State",
                                           code="ST",
                                           country_id=self.be.id))

        self.data = {
            'name': 'Odoo S.A.',
            'country_id': self.be.id,
            'state_id': self.state_be.id,
            'partner_gid': 1,
            'website': 'odoo.com',
            'comment': 'Comment on Odoo',
            'street': '40 Chaussée de Namur',
            'city': 'Ramillies',
            'zip': '1367',
            'phone': '+1 650-691-3277',
            'email': 'info@odoo.com',
            'vat': 'BE0477472701',
            'additional_info': '{"description": "Open Source Community version"}',
        }

        o2m_data = {
            'bank_ids': [{
                'acc_number': 'BE00000000000000',
                'acc_holder_name': 'Odoo',
            }],
            'child_ids': [{
                'name': 'Shipping address of Odoo',
                'country_id': self.be.id,
                'comment': 'Shipping address of Odoo',
                'street': '40 Chaussée de Namur',
                'city': 'Ramillies',
                'zip': '1367',
                'phone': '+1 650-691-3277',
                'email': 'info2@odoo.com',
            }, {
                'name': 'Invoicing address of Odoo',
                'country_id': self.be.id,
                'comment': 'Invoicing address of Odoo',
                'street': '40 Chaussée de Namur',
                'city': 'Ramillies',
                'zip': '1367',
                'phone': '+1 650-691-3277',
                'email': 'info3@odoo.com',
            }],
        }

        ctx = {'default_%s' % key: value for key, value in {**self.data, **o2m_data}.items()}
        self.partner_model = self.env['res.partner'].with_context(ctx)

    def test_10_test(self):

        f = Form(self.partner_model)
        self.assertEqual(0, 0)
        f.save()
