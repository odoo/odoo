# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.tests.common import TransactionCase


class TestResConfig(TransactionCase):

    def setUp(self):
        super(TestResConfig, self).setUp()
        self.ResConfig = self.env['res.config.settings']

        # Define the test values
        self.menu_xml_id = 'base.menu_action_res_users'
        self.full_field_name = 'res.partner.lang'
        self.error_msg = "WarningRedirect test string: %(field:res.partner.lang)s - %(menu:base.menu_action_res_users)s."
        self.error_msg_wo_menu = "WarningRedirect test string: %(field:res.partner.lang)s."
        # Note: see the get_config_warning() doc for a better example

        # Fetch the expected values
        menu = self.env.ref(self.menu_xml_id)

        model_name, field_name = self.full_field_name.rsplit('.', 1)

        self.expected_path = menu.complete_name
        self.expected_action_id = menu.action.id
        self.expected_name = self.env[model_name].fields_get([field_name])[field_name]['string']
        self.expected_final_error_msg = self.error_msg % {
            'field:res.partner.lang': self.expected_name,
            'menu:base.menu_action_res_users': self.expected_path
        }
        self.expected_final_error_msg_wo_menu = self.error_msg_wo_menu % {
            'field:res.partner.lang': self.expected_name,
        }

    def test_00_get_option_path(self):
        """ The get_option_path() method should return a tuple containing a string and an integer """
        res = self.ResConfig.get_option_path(self.menu_xml_id)

        # Check types
        self.assertIsInstance(res, tuple)
        self.assertEqual(len(res), 2, "The result should contain 2 elements")
        self.assertIsInstance(res[0], basestring)
        self.assertIsInstance(res[1], (int, long))

        # Check returned values
        self.assertEqual(res[0], self.expected_path)
        self.assertEqual(res[1], self.expected_action_id)

    def test_10_get_option_name(self):
        """ The get_option_name() method should return a string """
        res = self.ResConfig.get_option_name(self.full_field_name)

        # Check type
        self.assertIsInstance(res, basestring)

        # Check returned value
        self.assertEqual(res, self.expected_name)

    def test_20_get_config_warning(self):
        """ The get_config_warning() method should return a RedirectWarning """
        res = self.ResConfig.get_config_warning(self.error_msg)

        # Check type
        self.assertIsInstance(res, exceptions.RedirectWarning)

        # Check returned value
        self.assertEqual(res.args[0], self.expected_final_error_msg)
        self.assertEqual(res.args[1], self.expected_action_id)

    def test_30_get_config_warning_wo_menu(self):
        """ The get_config_warning() method should return a Warning exception """
        res = self.ResConfig.get_config_warning(self.error_msg_wo_menu)

        # Check type
        self.assertIsInstance(res, exceptions.Warning)

        # Check returned value
        self.assertEqual(res.args[0], self.expected_final_error_msg_wo_menu)
