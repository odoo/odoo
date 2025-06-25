# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from lxml import etree
import logging

from odoo import exceptions, Command
from odoo.tests import Form, TransactionCase, tagged

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

    # TODO: ASK DLE if this test can be removed
    def test_40_view_expected_architecture(self):
        """Tests the res.config.settings form view architecture expected by the web client.
        The res.config.settings form view is handled with a custom widget expecting a very specific
        structure. This architecture is tested extensively in Javascript unit tests.
        Here we briefly ensure the view sent by the server to the web client has the right architecture,
        the right blocks with the right classes in the right order.
        This tests is to ensure the specification/requirements are listed and tested server side, and
        if a change occurs in future development, this test will need to be adapted to specify these changes."""
        view = self.env['ir.ui.view'].create({
            'name': 'foo',
            'type': 'form',
            'model': 'res.config.settings',
            'inherit_id': self.env.ref('base.res_config_settings_view_form').id,
            'arch': """
                <xpath expr="//form" position="inside">
                    <t groups="base.group_system">
                        <app data-string="Foo" string="Foo" name="foo">
                            <h2>Foo</h2>
                        </app>
                    </t>
                </xpath>
            """,
        })
        arch = self.env['res.config.settings'].get_view(view.id)['arch']
        tree = etree.fromstring(arch)
        self.assertTrue(tree.xpath("""
            //form[@class="oe_form_configuration"]
            /app[@name="foo"]
        """), 'The res.config.settings form view architecture is not what is expected by the web client.')

    # TODO: ASK DLE if this test can be removed
    def test_50_view_expected_architecture_t_node_groups(self):
        """Tests the behavior of the res.config.settings form view postprocessing when a block `app`
        is wrapped in a `<t groups="...">`, which is used when you need to display an app settings section
        only for users part of two groups at the same time."""
        view = self.env['ir.ui.view'].create({
            'name': 'foo',
            'type': 'form',
            'model': 'res.config.settings',
            'inherit_id': self.env.ref('base.res_config_settings_view_form').id,
            'arch': """
                <xpath expr="//form" position="inside">
                    <t groups="base.group_system">
                        <app data-string="Foo"
                            string="Foo" name="foo" groups="base.group_no_one">
                            <h2>Foo</h2>
                        </app>
                    </t>
                </xpath>
            """,
        })
        with self.debug_mode():
            arch = self.env['res.config.settings'].get_view(view.id)['arch']
            tree = etree.fromstring(arch)
            # The <t> must be removed from the structure
            self.assertFalse(tree.xpath('//t'), 'The `<t groups="...">` block must not remain in the view')
            self.assertTrue(tree.xpath("""
                //form
                /app[@name="foo"]
            """), 'The `app` block must be a direct child of the `form` block')


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

        # If not enabled (like in demo data), landing on res.config will try
        # to disable module_sale_quotation_builder and raise an issue
        group_order_template = self.env.ref('sale_management.group_sale_order_template', raise_if_not_found=False)
        if group_order_template:
            self.env.ref('base.group_user').write({"implied_ids": [(4, group_order_template.id)]})

        _logger.info("Testing settings access for group %s", group_system.full_name)
        forbidden_models = self._test_user_settings_fields_access(settings_only_user)
        self._test_user_settings_view_save(settings_only_user)

        for model in forbidden_models:
            _logger.warning("Settings user doesn\'t have read access to the model %s", model)

        settings_view_conditional_groups = self.env['ir.ui.view'].search([
            ('model', '=', 'res.config.settings'),
        ]).groups_id

        # Semi hack to recover part of the coverage lost when the groups_id
        # were moved from the views records to the view nodes (with groups attributes)
        groups_data = self.env['res.groups'].get_groups_by_application()
        for group_data in groups_data:
            if group_data[1] == 'selection' and group_data[3] != (100, 'Other'):
                manager_group = group_data[2][-1]
                settings_view_conditional_groups += manager_group
        settings_view_conditional_groups -= group_system  # Already tested above

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
        # because the webclient makes a read of display_name request for all specified records
        # even if they are not shown to the user.
        settings_view_arch = etree.fromstring(settings.get_view(view_id=self.settings_view.id)['arch'])
        seen_fields = set()
        for node in settings_view_arch.iterdescendants(tag='field'):
            fname = node.get('name')
            if fname not in settings._fields:
                # fname isn't a settings fields, but the field of a model
                # linked to settings through a relational field
                continue
            seen_fields.add(fname)

        models_to_check = defaultdict(set)
        for field_name in seen_fields:
            field = settings._fields[field_name]
            if field.relational:
                models_to_check[field.comodel_name].add(field)

        forbidden_models_fields = defaultdict(set)
        for model in models_to_check:
            has_read_access = self.env[model].with_user(user).has_access('read')
            if not has_read_access:
                forbidden_models_fields[model] = models_to_check[model]

        return forbidden_models_fields

    def _test_user_settings_view_save(self, user):
        """Verify that settings user are able to save the settings form."""
        ResConfigSettings = self.env['res.config.settings'].with_user(user)

        settings_form = Form(ResConfigSettings)
        settings_form.save()
