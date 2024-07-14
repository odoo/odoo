# -*- coding: utf-8 -*-
from odoo import fields
from odoo.addons.account_reports.tests.common import TestAccountReportsCommon


class AccountSalesReportCommon(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.partner_a = cls.env['res.partner'].create({
            'name': 'Partner A',
            'country_id': cls.env.ref('base.fr').id,
            "vat": "FR23334175221",
        })
        cls.partner_b = cls.env['res.partner'].create({
            'name': 'Partner B',
            'country_id': cls.env.ref('base.be').id,
            "vat": "BE0477472701",
        })

    def _create_invoices(self, data, is_refund=False):
        move_vals_list = []
        for partner, tax, price_unit in data:
            move_vals_list.append({
                'move_type': 'out_refund' if is_refund else 'out_invoice',
                'partner_id': partner.id,
                'invoice_date': fields.Date.from_string('2019-12-01'),
                'invoice_line_ids': [
                    (0, 0, {
                        'name': 'line_1',
                        'price_unit': price_unit,
                        'quantity': 1.0,
                        'account_id': self.company_data['default_account_revenue'].id,
                        'tax_ids': [(6, 0, tax.ids)],
                    }),
                ],
            })
        moves = self.env['account.move'].create(move_vals_list)
        moves.action_post()
