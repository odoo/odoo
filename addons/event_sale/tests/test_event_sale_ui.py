# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo.fields import Datetime
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestUi(HttpCase):

    def test_event_configurator(self):
        # self.env["account.chart.template"].try_loading('generic_coa', self.env.company)

        self.env['account.tax.group'].create(
            {'name': 'Test Account Tax Group', 'company_id': self.env.company.id}
        )

        self.tax_10 = self.env['account.tax'].sudo().create({
            'name': 'Tax 10',
            'amount': 10,
        })

        self.product_event = self.env.ref('event_product.product_product_event')
        self.product_event.taxes_id = [(6, 0, self.tax_10.ids)]

        event = self.env['event.event'].create({
            'name': 'Design Fair Los Angeles',
            'date_begin': Datetime.now() + timedelta(days=1),
            'date_end': Datetime.now() + timedelta(days=5),
        })

        self.env['event.event.ticket'].create([{
            'name': 'Standard',
            'event_id': event.id,
            'product_id': self.product_event.id,
        }, {
            'name': 'VIP',
            'event_id': event.id,
            'product_id': self.product_event.id,
        }])
        self.start_tour("/odoo", 'event_configurator_tour', login="admin")
