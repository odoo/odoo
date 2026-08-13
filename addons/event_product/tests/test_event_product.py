from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from odoo.addons.event_product.tests.common import TestEventProductCommon


@tagged('post_install', '-at_install')
class TestEventProduct(TestEventProductCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_event = cls.env['event.event'].create({
            'name': "TestEventProduct",
            'event_type_id': cls.event_type_tickets.id,
        })

    def test_ensure_event_service_tracking(self):
        with self.assertRaises(ValidationError):
            self.event_product.service_tracking = 'no'
        with self.assertRaises(ValidationError):
            with Form(self.event_product) as product_form:
                product_form.type = 'consu'
