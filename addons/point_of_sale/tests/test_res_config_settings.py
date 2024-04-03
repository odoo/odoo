# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.tests.common import Form


@odoo.tests.tagged('post_install', '-at_install')
class TestConfigureShops(TestPoSCommon):
    """ Shops are now configured from the general settings.
        This test suite ensures that changes made in the general settings
        should reflect to the pos.config record pointed by the
        pos_config_id field.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # If not enabled (like in demo data), landing on res.config will try
        # to disable module_sale_quotation_builder and raise an issue
        group_order_template = cls.env.ref('sale_management.group_sale_order_template', raise_if_not_found=False)
        if group_order_template:
            cls.env.ref('base.group_user').write({"implied_ids": [(4, group_order_template.id)]})

    def _remove_on_payment_taxes(self):
        """ Call this when testing the res.config.settings with Form.
            The `on_payment` taxes need to be removed, otherwise, a warning will show in the log.
        """
        self.env['account.tax'].search([
            ('company_id', '=', self.env.company.id), ('tax_exigibility', '=', 'on_payment')
        ]).unlink()

    def test_should_not_affect_other_pos_config(self):
        """ Change in one pos.config should not reflect to the other.
        """
        self._remove_on_payment_taxes()

        pos_config1 = self.env['pos.config'].create({'name': 'Shop 1'})
        pos_config2 = self.env['pos.config'].create({'name': 'Shop 2'})
        self.assertEqual(pos_config1.receipt_header, False)
        self.assertEqual(pos_config2.receipt_header, False)

        # Modify Shop 1.
        with Form(self.env['res.config.settings']) as form:
            form.pos_config_id = pos_config1
            form.pos_is_header_or_footer = True
            form.pos_receipt_header = 'xxxxx'

        self.assertEqual(pos_config1.receipt_header, 'xxxxx')
        self.assertEqual(pos_config2.receipt_header, False)

        # Modify Shop 2.
        with Form(self.env['res.config.settings']) as form:
            form.pos_config_id = pos_config2
            form.pos_is_header_or_footer = True
            form.pos_receipt_header = 'yyyyy'

        self.assertEqual(pos_config1.receipt_header, 'xxxxx')
        self.assertEqual(pos_config2.receipt_header, 'yyyyy')

    def test_is_header_or_footer_to_false(self):
        self._remove_on_payment_taxes()

        pos_config = self.env['pos.config'].create({
            'name': 'Shop',
            'is_header_or_footer': True,
            'receipt_header': 'header val',
            'receipt_footer': 'footer val',
        })

        with Form(self.env['res.config.settings']) as form:
            form.pos_config_id = pos_config
            form.pos_is_header_or_footer = False

        self.assertEqual(pos_config.receipt_header, False)
        self.assertEqual(pos_config.receipt_footer, False)
