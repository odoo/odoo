# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestUi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        service_category_id = cls.env['product.category'].create({
            'name': 'Services',
            'parent_id': cls.env.ref('product.product_category_1').id,
        }).id

        uom_hour_id = cls.env.ref('uom.product_uom_hour').id
        cls.prepaid_service_product = cls.env['product.product'].create({
            'name': 'Service Product (Prepaid Hours)',
            'categ_id': service_category_id,
            'type': 'service',
            'list_price': 250.00,
            'standard_price': 190.00,
            'uom_id': uom_hour_id,
            'uom_po_id': uom_hour_id,
            'service_policy': 'ordered_prepaid',
            'service_tracking': 'no',
        })

        # Enable the "Milestones" feature to be able to create milestones on this tour.
        cls.env['res.config.settings'] \
            .create({'group_project_milestone': True}) \
            .execute()

    def test_ui(self):
        import unittest; raise unittest.SkipTest("skipWOWL")
        self.start_tour('/web', 'sale_timesheet_tour', login='admin', timeout=100)
