# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import Command

from odoo.addons.sale_project.tests.test_project_profitability import TestProjectProfitabilityCommon


class TestIndustryFsmSaleProjectProfitability(TestProjectProfitabilityCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.additional_quotation = cls.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': cls.partner.id,
            'partner_invoice_id': cls.partner.id,
            'partner_shipping_id': cls.partner.id,
            'task_id': cls.task.id,  # means the quotation is created via this task.
            'order_line': [Command.create({
                'product_id': cls.material_product.id,
                'product_uom_qty': 10,
            })],
        })

    def test_profitability_of_non_billable_project(self):
        """ Test no data is found for the project profitability when the project is non billable
            even if a task of that prooject has an additional quotations confirmed.
        """
        self.assertFalse(self.project.allow_billable)
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
        )
        self.additional_quotation.action_confirm()

        self.assertFalse(self.project.allow_quotations)
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
        )

    def test_get_profitability_items(self):
        self.project.write({
            'allow_billable': True,
            'allow_quotations': True,
        })
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'No data should be found since no SO is linked to the project.'
        )
        self.additional_quotation.action_confirm()
        self.env.flush_all()
        sequence_per_invoice_type = self.project._get_profitability_sequence_per_invoice_type()
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'costs': {'data': [], 'total': {'to_bill': 0.0, 'billed': 0.0}},
                'revenues': {
                    'data': [{
                        'id': 'materials',
                        'sequence': sequence_per_invoice_type['materials'],
                        'to_invoice': self.additional_quotation.order_line.untaxed_amount_to_invoice,
                        'invoiced': 0.0,
                    }],
                    'total': {
                        'to_invoice': self.additional_quotation.order_line.untaxed_amount_to_invoice,
                        'invoiced': 0.0,
                    },
                },
            },
            'The SOL of the additional sale order should be found'
        )
