# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo.addons.event_sale.tests.common import TestEventSaleCommon
from odoo.tests import tagged


@tagged('event_flow')
class TestEventSaleReport(TestEventSaleCommon):

    def test_event_date_begin_timezone(self):
        """ event_date_begin/end must reflect the event's own local day
        (date_tz), not the UTC day the datetime happens to fall on. """
        event = self.env['event.event'].create({
            'name': 'Test TZ Event',
            'date_begin': '2026-08-01 00:00:00',  # 31/07 14:00 in Pacific/Tahiti
            'date_end': '2026-08-02 00:00:00',
            'date_tz': 'Pacific/Tahiti',
        })
        self.env['event.registration'].create({'event_id': event.id})

        report_line = self.env['event.sale.report'].search([('event_id', '=', event.id)])
        self.assertEqual(report_line.event_date_begin, date(2026, 7, 31))
