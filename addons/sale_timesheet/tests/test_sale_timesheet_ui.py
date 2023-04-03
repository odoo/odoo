# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestUi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['product.category'].create({
            'name': 'Services',
            'parent_id': cls.env.ref('product.product_category_1').id,
        })

        # Enable the "Milestones" feature to be able to create milestones on this tour.
        cls.env['res.config.settings'] \
            .create({'group_project_milestone': True}) \
            .execute()

    def test_ui(self):
        self.start_tour('/web', 'sale_timesheet_tour', login='admin', timeout=100)
