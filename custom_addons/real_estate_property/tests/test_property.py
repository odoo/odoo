from odoo.tests.common import TransactionCase
from odoo import fields

class TestProperty(TransactionCase):

    def setUp(self, *args, **kwargs):
        super(TestProperty,self).setUp()

        self.property_01_record = self.env['property'].create({
            'ref': 'PRT1000',
            'name': 'Property 1000',
            'description': 'Description for Property 01',
            'postcode': '215123',
            'date_availability': fields.Date.today(),
            'bedrooms': 3,
            'expected_price': 2500
        })

    def test_01_property_values(self):
        property_id = self.property_01_record

        self.assertRecordValues(property_id, [{
            'ref': 'PRT1001',
            'name': 'Property 1000',
            'description': 'Description for Property 01',
            'postcode': '215123',
            'date_availability': fields.Date.today(),
            'bedrooms': 3,
            'expected_price': 2500
        }])