from odoo.addons.base.tests.common import TransactionCaseWithUserDemo
from odoo.tests.common import tagged


@tagged('res_partner')
class TestMapView(TransactionCaseWithUserDemo):
    def test_address_change_latitude_longitude_reset(self):
        res_partner = self.env['res.partner']
        parent = res_partner.create({
            'name': 'Parent',
            'is_company': True,
            'street': 'test',
            'type': 'contact',
        })
        child = res_partner.browse(res_partner.name_create('Child <child@ghoststep.com>')[0])
        self.assertEqual(child.type, 'contact', 'Default type must be "contact"')
        child.write({'parent_id': parent.id})
        self.assertEqual(child.street, parent.street, 'Address fields must be synced')

        def set_latitude_longitude():
            parent.write({
                'partner_latitude': 10.0,
                'partner_longitude': 10.0,
            })

            child.write({
                'partner_latitude': 10.0,
                'partner_longitude': 10.0,
            })

        set_latitude_longitude()

        self.assertEqual(parent.partner_latitude, 10.0)
        self.assertEqual(parent.partner_longitude, 10.0)
        self.assertEqual(child.partner_latitude, 10.0)
        self.assertEqual(child.partner_longitude, 10.0)

        parent.write({'street': 'street'})
        self.assertEqual(child.street, parent.street, 'Address fields must be synced')

        self.assertEqual(parent.partner_latitude, 0.0)
        self.assertEqual(parent.partner_longitude, 0.0)
        self.assertEqual(child.partner_latitude, 0.0)
        self.assertEqual(child.partner_longitude, 0.0)

        set_latitude_longitude()

        child.write({'street': 'other street'})
        self.assertEqual(parent.partner_latitude, 10.0)
        self.assertEqual(parent.partner_longitude, 10.0)
        self.assertEqual(child.partner_latitude, 0.0)
        self.assertEqual(child.partner_longitude, 0.0)
