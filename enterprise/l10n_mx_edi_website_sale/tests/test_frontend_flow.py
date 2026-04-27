# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, HttpCase
from odoo.addons.l10n_mx_edi.tests.common import TestMxEdiCommon

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFrontendFlow(HttpCase, TestMxEdiCommon):
    def test_validate_required_additional_fields(self):
        user_admin = self.env.ref('base.user_admin')
        user_admin.write({
            'company_id': self.env.company.id,
            'company_ids': [(4, self.env.company.id)],
            'email': 'admin@example.com',
            'phone': '+1 212-488-2705',
            'street': '53 Christopher Street',
            'city': 'New York',
            'zip': '10014',
            'state_id': self.env.ref('base.state_us_27').id,
            'country_id': self.env.ref('base.us').id,
        })
        self.env.company = self.company_data['company']
        self.env['product.product'].create({
            'name': 'Test Product',
            'sale_ok': True,
            'website_published': True,
        })
        self.env['ir.config_parameter'].set_param('sale.automatic_invoice', True)
        self.env['website'].get_current_website().company_id = self.env.company.id

        self.start_tour('/shop', 'test_validate_additional_fields', login='admin')
