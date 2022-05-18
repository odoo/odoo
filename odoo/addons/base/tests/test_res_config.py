# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from lxml import etree
import logging

from odoo import exceptions, Command
from odoo.tests.common import Form, TransactionCase, tagged

_logger = logging.getLogger(__name__)


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

    def test_settings_access(self):
        """Check that settings user are able to open & save settings

        Also check that user with settings rights + any one of the groups restricting
        a conditional view inheritance of res.config.settings view is also able to
        open & save the settings (considering the added conditional content)
        """
        ResUsers = self.env['res.users']
        group_system = self.env.ref('base.group_system')
        self.settings_view = self.env.ref('base.res_config_settings_view_form')
        settings_only_user = ResUsers.create({
            'name': 'Sleepy Joe',
            'login': 'sleepy',
            'groups_id': [Command.link(group_system.id)],
        })

        _logger.info("Testing settings access for group %s", group_system.full_name)
        forbidden_models = self._test_user_settings_fields_access(settings_only_user)
        self._test_user_settings_view_save(settings_only_user)

        for model in forbidden_models:
            _logger.warning("Settings user doesn\'t have read access to the model %s", model)

        settings_view_conditional_groups = self.env['ir.ui.view'].search([
            ('model', '=', 'res.config.settings'),
        ]).groups_id

        for group in settings_view_conditional_groups:
            group_name = group.full_name
            _logger.info("Testing settings access for group %s", group_name)
            create_values = {
                'name': f'Test {group_name}',
                'login': group_name,
                'groups_id': [Command.link(group_system.id), Command.link(group.id)]
            }
            user = ResUsers.create(create_values)
            self._test_user_settings_view_save(user)
            forbidden_models_fields = self._test_user_settings_fields_access(user)

            for model, fields in forbidden_models_fields.items():
                _logger.warning(
                    "Settings + %s user doesn\'t have read access to the model %s"
                    "linked to settings records by the field(s) %s",
                    group_name, model, ", ".join(str(field) for field in fields)
                )

    def _test_user_settings_fields_access(self, user):
        """Verify that settings user are able to create & save settings."""
        settings = self.env['res.config.settings'].with_user(user).create({})

        # Save the settings
        settings.set_values()

        # Check user has access to all models of relational fields in view
        # because the webclient makes a name_get request for all specified records
        # even if they are not shown to the user.
        settings_view_arch = etree.fromstring(settings.get_view(view_id=self.settings_view.id)['arch'])
        seen_fields = set()
        for node in settings_view_arch.iterdescendants(tag='field'):
            seen_fields.add(node.get('name'))

        models_to_check = defaultdict(set)
        for field_name in seen_fields:
            field = settings._fields[field_name]
            if field.relational:
                models_to_check[field.comodel_name].add(field)

        forbidden_models_fields = defaultdict(set)
        for model in models_to_check:
            has_read_access = self.env[model].with_user(user).check_access_rights(
                'read', raise_exception=False)
            if not has_read_access:
                forbidden_models_fields[model] = models_to_check[model]

        return forbidden_models_fields

    def _test_user_settings_view_save(self, user):
        """Verify that settings user are able to save the settings form."""
        ResConfigSettings = self.env['res.config.settings'].with_user(user)

        settings_form = Form(ResConfigSettings)
        settings_form.save()
