from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.tests import tagged
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon


@tagged('post_install', '-at_install')
class TestUi(HttpCaseWithUserDemo, TestWebsiteEventSaleCommon):

    def test_check_conversion_website_sale_event(self):
        # Assign the currency rate modified above to EUR relative to USD
        eur_cur = self.env.ref('base.EUR')
        eur_cur.rate_ids = [Command.create({
            'name': '2025-07-25',
            'rate': 3,
            'currency_id': eur_cur.id,
            'company_id': self.env.company.id,
        })]
        self.assertEqual(len(eur_cur.rate_ids), 1, "SafetyNet")

        # Create new company with different currency (Eur)
        c1 = self.env['res.company'].create({
            'name': 'test_company_different_currency',
            'currency_id': eur_cur.id,
        })
        c2 = self.env.company
        # Make product of type event from company FR and company US
        product_1, product_2 = self.env['product.product'].create([{
            'name': 'Ticket 1',
            'detailed_type': 'event',
            'list_price': 100,
            'standard_price': 30.0,
            'company_id': c1.id,
        }, {
            'name': 'Ticket 2',
            'detailed_type': 'event',
            'list_price': 100,
            'standard_price': 30.0,
            'company_id': c2.id,
        }])

        # Create event with company US and include two tickets from products created above
        event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': datetime.now() + relativedelta(days=-1),
            'date_end': datetime.now() + relativedelta(days=1),
            'event_ticket_ids': [
                Command.create({
                    'name': 'FR ticket',
                    'product_id': product_1.id,
                }),
                Command.create({
                    'name': 'US ticket',
                    'product_id': product_2.id,
                }),
            ],
        })
        self.start_tour("/event/TestEvent-%d/register" % event.id, "view_ticket_price", login="admin")
