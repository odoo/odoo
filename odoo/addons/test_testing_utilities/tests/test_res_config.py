# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


class TestResConfig(TransactionCase):

    def test_00_add_parameter_with_default_value(self):
        """ Check if parameters with a default value are saved in the ir_config_parameter table """

        self.env['res.config.test'].create({}).execute()
        self.assertEqual(self.env['ir.config_parameter'].sudo().get_param('resConfigTest.parameter1'), str(1000),
            "The parameter is not saved with its default value")

        with patch('odoo.addons.base.models.ir_config_parameter.IrConfigParameter.set_param') as set_param_mock:
            self.env['res.config.test'].create({}).execute()

        set_param_mock.assert_not_called()


@tagged('post_install', '-at_install')
class TestResConfigPost(TransactionCase):
    def test_default_setting(self):
        other_company = self.env['res.company'].create({'name': "Other company"})
        us = self.env.ref('base.us')

        # Change default values from first company
        config = self.env['res.config.test'].create({})
        config.default_name = "Why would I do that?"
        config.default_country_id = us
        config.execute()

        # The default values are taken into account
        partner = self.env['res.partner'].create({})
        self.assertEqual(partner.name, "Why would I do that?")
        self.assertEqual(partner.country_id, us)

        # Only global fields are affecting other companies
        partner = self.env['res.partner'].with_company(other_company).create({})
        self.assertEqual(partner.name, "NAME")
        self.assertEqual(partner.country_id, us)

        # Reset to default value on main company
        config = self.env['res.config.test'].create({})
        self.assertEqual(config.default_name, "Why would I do that?")
        config.default_name = ''
        config.execute()
        self.assertEqual(partner.name, "NAME")
