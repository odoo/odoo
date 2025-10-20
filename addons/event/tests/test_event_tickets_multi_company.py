from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.event.tests.common import EventCase
from odoo.exceptions import ValidationError


class TestEventTicketsMultiCompany(EventCase):

    def test_event_tickets_multi_company(self):
        eur_cur = self.env.ref('base.EUR')
        company_eur = self.env['res.company'].create({
            'name': 'EUR Company',
            'currency_id': eur_cur.id,
        })
        company_us = self.env.company
        product_us, product_eur = self.env['product.product'].create([{
            'name': 'Ticket US',
            'type': 'service',
            'service_tracking': 'event',
            'list_price': 10,
            'company_id': company_us.id,
        }, {
            'name': 'Ticket EUR',
            'type': 'service',
            'service_tracking': 'event',
            'list_price': 10,
            'company_id': company_eur.id,
        }])
        test_event = self.env['event.event'].create({
            'date_begin': datetime.now() + relativedelta(days=-1),
            'date_end': datetime.now() + relativedelta(days=1),
            'name': 'Test Event',
            'company_id': company_us.id,
        })
        self.env['event.event.ticket'].create({
            'name': 'US ticket',
            'event_id': test_event.id,
            'product_id': product_us.id,
        })
        # include a eur ticket on us company
        with self.assertRaises(ValidationError):
            self.env['event.event.ticket'].create({
                'name': 'EUR ticket',
                'event_id': test_event.id,
                'product_id': product_eur.id,
            })
        # attempt to change the company of the event to eur - should raise an error due to a us ticket already included on the event
        with self.assertRaises(ValidationError):
            test_event.write({'company_id': company_eur})
        # attempt to change the company of the us product
        with self.assertRaises(ValidationError):
            product_us.write({'company_id': company_eur.id})
