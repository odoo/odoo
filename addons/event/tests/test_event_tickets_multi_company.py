from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.event.tests.common import EventCase
# from odoo.exceptions import UserError


class TestEventTicketsMultiCompany(EventCase):

    def test_event_tickets_multi_company(self):
        eur_cur = self.env.ref('base.EUR')
        company_fr = self.env['res.company'].create({
            'name': 'FR Company',
            'currency_id': eur_cur.id,
        })
        company_us = self.env.company
        ticket_us, ticket_fr = self.env['product.template'].create([{
            'name': 'Ticket US',
            'type': 'service',
            'service_tracking': 'event',
            'list_price': 10,
            'company_id': company_us,
        }, {
            'name': 'Ticket FR',
            'type': 'service',
            'service_tracking': 'event',
            'list_price': 10,
            'company_id': company_fr,
        }])
        test_event = self.env['event.event'].create({
            'date_begin': datetime.now() + relativedelta(days=-1),
            'date_end': datetime.now() + relativedelta(days=1),
            'name': 'Test Event',
            'company_id': self.company_id,
        })
        test_event.write({
            'ticket_event_ids': [ticket_us, ticket_fr]
        })
        # try:
        #     test_event.write({
        #         'ticket_event_ids': [ticket_us, ticket_fr]
        #     })
        # except UserError:
        #     raise UserError("User Error: You can't include tickets belonging to a different company than the company of the event")
