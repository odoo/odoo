# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time

from odoo import fields
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


@tagged('post_install', '-at_install')
class TestTourAccountReports(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        with freeze_time('2020-01-01'):
            today = fields.Date.today()
            previous_year = fields.Date.from_string('%s-%s-01' % (today.year - 1, today.month))

            cls.out_invoice_current_year = cls.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': today,
                'date': today,
                'invoice_line_ids': [
                    (0, 0, {'name': 'line1', 'price_unit': 100.0}),
                ],
            })
            cls.out_invoice_current_year.action_post()

            cls.out_invoice_previous_year = cls.env['account.move'].create({
                'move_type': 'out_invoice',
                'partner_id': cls.partner_a.id,
                'invoice_date': previous_year,
                'date': previous_year,
                'invoice_line_ids': [
                    (0, 0, {'name': 'line1', 'price_unit': 500.0}),
                ],
            })
            cls.out_invoice_previous_year.action_post()

    @freeze_time('2020-01-01')
    def test_tour_account_reports(self):
        self.start_tour("/web", 'account_reports_widgets', login=self.env.user.login)
