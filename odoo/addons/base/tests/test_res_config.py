# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import exceptions
from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)


class TestResConfig(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ResConfig = cls.env['res.config.settings']

        # Define the test values
        cls.menu_xml_id = 'base.menu_action_res_users'
        cls.full_field_name = 'res.partner.lang'
        cls.error_msg = "WarningRedirect test string: %(field:res.partner.lang)s - %(menu:base.menu_action_res_users)s."
        cls.error_msg_wo_menu = "WarningRedirect test string: %(field:res.partner.lang)s."
        # Note: see the get_config_warning() doc for a better example

        # Fetch the expected values
        menu = cls.env.ref(cls.menu_xml_id)

        model_name, field_name = cls.full_field_name.rsplit('.', 1)

        cls.expected_path = menu.complete_name
        cls.expected_action_id = menu.action.id
        cls.expected_name = cls.env[model_name].fields_get([field_name])[field_name]['string']
        cls.expected_final_error_msg = cls.error_msg % {
            'field:res.partner.lang': cls.expected_name,
            'menu:base.menu_action_res_users': cls.expected_path
        }
        cls.expected_final_error_msg_wo_menu = cls.error_msg_wo_menu % {
            'field:res.partner.lang': cls.expected_name,
        }

    def test_00_get_option_path(self):
        """ The get_option_path() method should return a tuple containing a string and an integer """
        res = self.ResConfig.get_option_path(self.menu_xml_id)

        # Check types
        self.assertIsInstance(res, tuple)
        self.assertEqual(len(res), 2, "The result should contain 2 elements")
        self.assertIsInstance(res[0], str)
        self.assertIsInstance(res[1], int)

        # Check returned values
        self.assertEqual(res[0], self.expected_path)
        self.assertEqual(res[1], self.expected_action_id)

    def test_10_get_option_name(self):
        """ The get_option_name() method should return a string """
        res = self.ResConfig.get_option_name(self.full_field_name)

        # Check type
        self.assertIsInstance(res, str)

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
        self.assertIsInstance(res, exceptions.UserError)

        # Check returned value
        self.assertEqual(res.args[0], self.expected_final_error_msg_wo_menu)


@tagged('post_install', '-at_install')
class TestResConfigExecute(TransactionCase):

    def test_01_execute_res_config(self):
        """
        Try to create and execute all res_config models. Target settings that can't be
        loaded or saved and avoid remaining methods `get_default_foo` or `set_foo` that
        won't be executed is foo != `fields`
        """
        all_config_settings = self.env['ir.model'].search([('name', 'like', 'config.settings')])
        for config_settings in all_config_settings:
            _logger.info("Testing %s" % (config_settings.name))
            self.env[config_settings.name].create({}).execute()
