# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event.tests.common import EventCase


class TestEventProductCommon(EventCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.event_product = cls.env['product.product'].create({
            'name': 'Test Registration Product',
            'description_sale': 'Mighty Description',
            'list_price': 10,
            'standard_price': 30.0,
            'type': 'service',
            'service_tracking': 'event',
        })

        cls.event_type_tickets = cls.env['event.type'].create({
            'name': 'Update Type',
            'has_seats_limitation': True,
            'seats_max': 30,
            'default_timezone': 'Europe/Paris',
            'event_type_ticket_ids': [
                (0, 0, {'name': 'First Ticket',
                        'product_id': cls.event_product.id,
                        'seats_max': 5,
                       })
            ],
            'event_type_mail_ids': [],
        })
