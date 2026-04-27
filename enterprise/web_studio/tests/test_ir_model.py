
from unittest.mock import patch
from lxml import etree

import odoo

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.addons.web_studio.wizard.studio_export_wizard import DEFAULT_MODELS_TO_EXPORT, FIELDS_TO_EXPORT, MODELS_WITH_NOUPDATE, RELATIONS_NOT_TO_EXPORT
from odoo.addons.web_studio.models.studio_export_model import PRESET_MODELS_DEFAULTS, \
    DEFAULT_FIELDS_TO_EXCLUDE, ABSTRACT_MODEL_FIELDS_TO_EXCLUDE, RELATED_MODELS_TO_EXCLUDE
from odoo.addons.web_studio.controllers.export import XML_FIELDS
from odoo.addons.web_studio.models.ir_model import OPTIONS_WL
from odoo.exceptions import ValidationError
from odoo import Command

class TestStudioIrModel(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # The test mode is necessary in this case.  After each test, we call
        # registry.reset_changes(), which opens a new cursor to retrieve custom
        # models and fields.  A regular cursor would correspond to the state of
        # the database before setUpClass(), which is not correct.  Instead, a
        # test cursor will correspond to the state of the database of cls.cr at
        # that point, i.e., before the call to setUp().
        cls.registry.enter_test_mode(cls.cr)
        cls.addClassCleanup(cls.registry.leave_test_mode)
        cls.partner_elon = cls.env['res.partner'].create({
            'name': 'Elon Tusk',  # 🐗
            'email': 'elon@spacex.com',
        })
        # custom m2m field between two models which don't have one yet
        cls.source_model = cls.env["ir.model"].search([("model", "=", "res.currency")])
        cls.destination_model = cls.env["ir.model"].search(
            [("model", "=", "res.country.state")]
        )
        cls.m2m = cls.env["ir.model.fields"].create(
            {
                "ttype": "many2many",
                "model_id": cls.source_model.id,
                "relation": cls.destination_model.model,
                "name": "x_state_ids",
            }
        )

    def test_00_model_creation(self):
        """Test that a model gets created with the selected options."""
        model_options = ['use_partner', 'use_stages', 'use_image',
                         'use_responsible', 'lines']
        (model, extra_models) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        self.assertEqual(extra_models.mapped('name'), ['Rockets Stages'], 'Only stages should be returned')

        line_model = self.env['ir.model'].search([('model', 'like', model.model + '_line')])
        self.assertEqual(len(line_model), 1, 'one extra model should have been created for lines')

        created_fields = self.env[model.model]._fields.keys()
        expected_fields = ['x_studio_partner_id', 'x_studio_stage_id', 'x_studio_image',
                           'x_studio_user_id', model.model + '_line_ids']

        self.assertTrue(all(list(filter(lambda x: item in x, created_fields)) for item in expected_fields),
                      'some expected fields have not been created automatically')

    def test_01_mail_inheritance(self):
        """Test that the mail inheritance behaves as expected on custom models."""
        model_options = ['use_partner', 'use_mail']
        (model, extra_models) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        self.assertEqual(len(extra_models), 0, 'no extra model should have been created')
        self.assertTrue(model.is_mail_thread,
                      'model should inherit from mail.thread')
        # create a record
        bfr = self.env[model.model].create({
            'x_name': 'Big Fucking Rocket',
            'x_studio_partner_id': self.partner_elon.id,
        })
        # ensure the partner is suggested in email and sms communication
        mail_suggested_recipients = bfr._message_get_suggested_recipients()
        self.assertItemsEqual(
            {
                'partner_id': self.partner_elon.id,
                'name': 'Elon Tusk',
                'email': 'elon@spacex.com',
                'display_name': 'Elon Tusk',
                'lang': None,
                'reason': 'Contact',
            },
            mail_suggested_recipients[0],
            'custom partner field should be suggested in mail communications',
        )
        sms_suggested_recipients = bfr._mail_get_partner_fields(introspect_fields=False)
        self.assertIn('x_studio_partner_id', sms_suggested_recipients,
                      'custom partner field should be included in sms communications')

        self.assertTrue(model.is_mail_activity)
        # resist to field name changes across versions
        self.assertTrue("activity_user_id" in self.env[model.model]._fields)
        got_views = self.env[model.model].get_views([(False, "search")])
        search_view = etree.fromstring(got_views["views"]["search"]["arch"])

        expected_filters = {
            'activities_overdue': "[('my_activity_date_deadline', '<', context_today().strftime('%Y-%m-%d'))]",
            'activities_today': "[('my_activity_date_deadline', '=', context_today().strftime('%Y-%m-%d'))]",
            'activities_upcoming_all': "[('my_activity_date_deadline', '>', context_today().strftime('%Y-%m-%d'))]"
        }

        for filter_name, expected_domain in expected_filters.items():
            filter_element = search_view.xpath(f"//filter[@name='{filter_name}']")[0]
            self.assertEqual(filter_element.get("domain"), expected_domain)

    def test_02_model_option_active(self):
        """Test that the `active` behaviour is set up correctly."""
        model_options = ['use_active', 'use_mail']
        (model, extra_models) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        self.assertEqual(len(extra_models), 0, 'no extra model should have been created')
        fields = self.env[model.model]._fields
        self.assertIn('x_active', fields, 'a custom active field should be set up')
        default = self.env['ir.default']._get(model.model, 'x_active')
        self.assertTrue(default, 'the default value for the x_active field should be True')
        active_field = self.env['ir.model.fields'].search([('name', '=', 'x_active'), ('model_id', '=', model.id)])
        self.assertTrue(active_field.tracking, 'the x_active field should be tracked')

    def test_03_model_option_sequence(self):
        """Test that the `sequence` behaviour is set up correctly."""
        model_options = ['use_sequence', 'use_mail']
        (model, extra_models) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        self.assertEqual(len(extra_models), 0, 'no extra model should have been created')
        fields = self.env[model.model]._fields
        self.assertIn('x_studio_sequence', fields, 'a custom sequence field should be set up')
        default = self.env['ir.default']._get(model.model, 'x_studio_sequence')
        self.assertEqual(default, 10, 'the default value for the x_studio_sequence field should be 10')

    def test_04_model_option_responsible(self):
        """Test that the `responsible` behaviour is set up correctly."""
        model_options = ['use_responsible', 'use_mail']
        (model, extra_models) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        self.assertEqual(len(extra_models), 0, 'no extra model should have been created')
        fields = self.env[model.model]._fields
        self.assertIn('x_studio_user_id', fields, 'a custom responsible (res.users) field should be set up')
        resp_field = self.env['ir.model.fields'].search([('name', '=', 'x_studio_user_id'), ('model_id', '=', model.id)])
        self.assertTrue(resp_field.tracking, 'the x_studio_user_id field should be tracked')

    def test_05_model_option_partner(self):
        """Test that the `partner` behaviour is set up correctly."""
        model_options = ['use_partner', 'use_mail']
        (model, extra_models) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        self.assertEqual(len(extra_models), 0, 'no extra model should have been created')
        fields = self.env[model.model]._fields
        self.assertIn('x_studio_partner_id', fields, 'a custom partner field should be set up')
        self.assertIn('x_studio_partner_phone', fields, 'a related field x_studio_partner_phone should be set up')
        self.assertIn('x_studio_partner_email', fields, 'a related field x_studio_partner_email should be set up')
        partner_field = self.env['ir.model.fields'].search([('name', '=', 'x_studio_partner_id'), ('model_id', '=', model.id)])
        self.assertTrue(partner_field.tracking, 'the x_studio_partner_id field should be tracked')

    def test_06_model_option_company(self):
        """Test that the `company` behaviour is set up correctly."""
        model_options = ['use_company', 'use_mail']
        (model, extra_models) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        self.assertEqual(len(extra_models), 0, 'no extra model should have been created')
        fields = self.env[model.model]._fields
        self.assertIn('x_studio_company_id', fields, 'a custom company field should be set up')
        mc_rule = self.env['ir.rule'].search([
            ('model_id', '=', model.id),
            ('domain_force', 'like', 'x_studio_company_id')
        ])
        self.assertEqual(len(mc_rule), 1, 'there should be a multi-company rule for the model')
        comp_field = self.env['ir.model.fields'].search([('name', '=', 'x_studio_company_id'), ('model_id', '=', model.id)])
        self.assertTrue(comp_field.tracking, 'the x_studio_company_id field should be tracked')
        main_company = self.env.ref('base.main_company')
        default = self.env['ir.default']._get(model.model, 'x_studio_company_id', company_id=main_company.id)
        self.assertEqual(default, main_company.id, 'the default value for the x_studio_company_id should be set')
        new_company = self.env['res.company'].create({'name': 'SpaceY'})
        new_default = self.env['ir.default']._get(model.model, 'x_studio_company_id', company_id=new_company.id)
        self.assertEqual(new_default, new_company.id, 'default values for new companies should be created with the company')

    def test_07_model_option_notes(self):
        """Test that the `notes` behaviour is set up correctly."""
        model_options = ['use_notes', 'use_mail']
        (model, extra_models) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        self.assertEqual(len(extra_models), 0, 'no extra model should have been created')
        fields = self.env[model.model]._fields
        self.assertIn('x_studio_notes', fields, 'a custom notes field should be set up')

    def test_08_model_option_date(self):
        """Test that the `date` behaviour is set up correctly."""
        model_options = ['use_date', 'use_mail']
        (model, extra_models) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        self.assertEqual(len(extra_models), 0, 'no extra model should have been created')
        fields = self.env[model.model]._fields
        self.assertIn('x_studio_date', fields, 'a custom date field should be set up')
        date_field = self.env['ir.model.fields'].search([('name', '=', 'x_studio_date'), ('model_id', '=', model.id)])
        self.assertFalse(date_field.tracking, 'the x_studio_date field should not be tracked')

    def test_09_model_option_double_dates(self):
        """Test that the `double date` behaviour is set up correctly."""
        model_options = ['use_double_dates', 'use_mail']
        (model, extra_models) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        self.assertEqual(len(extra_models), 0, 'no extra model should have been created')
        fields = self.env[model.model]._fields
        self.assertIn('x_studio_date_start', fields, 'a custom start date field should be set up')
        self.assertIn('x_studio_date_stop', fields, 'a custom stop date field should be set up')
        date_fields = self.env['ir.model.fields'].search([('name', 'like', 'x_studio_date'), ('model_id', '=', model.id)])
        for date_field in date_fields:
            self.assertFalse(date_field.tracking, 'start/stop date fields should not be tracked')

    def test_10_model_option_value(self):
        """Test that the `value` behaviour is set up correctly."""
        model_options = ['use_value', 'use_mail']
        (model, extra_models) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        self.assertEqual(len(extra_models), 0, 'no extra model should have been created')
        fields = self.env[model.model]._fields
        self.assertIn('x_studio_currency_id', fields, 'a custom currency field should be set up')
        self.assertIn('x_studio_currency_id', fields, 'a custom value field should be set up')
        value_field = self.env['ir.model.fields'].search([('name', '=', 'x_studio_value'), ('model_id', '=', model.id)])
        self.assertTrue(value_field.tracking, 'the x_studio_value field should be tracked')
        main_company = self.env.ref('base.main_company')
        default = self.env['ir.default']._get(model.model, 'x_studio_currency_id', company_id=main_company.id)
        self.assertEqual(default, main_company.currency_id.id, 'the default value for the x_studio_currency_id should be set')
        new_company = self.env['res.company'].create({'name': 'SpaceY', 'currency_id': self.env.ref('base.INR').id})
        new_default = self.env['ir.default']._get(model.model, 'x_studio_currency_id', company_id=new_company.id)
        self.assertEqual(new_default, new_company.currency_id.id, 'default currency for new companies should be create with the company')

    def test_11_model_option_image(self):
        """Test that the `image` behaviour is set up correctly."""
        model_options = ['use_image', 'use_mail']
        (model, extra_models) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        self.assertEqual(len(extra_models), 0, 'no extra model should have been created')
        fields = self.env[model.model]._fields
        self.assertIn('x_studio_image', fields, 'a custom image field should be set up')

    def test_12_model_option_stages(self):
        """Test that the `stage` behaviour is set up correctly."""
        model_options = ['use_stages', 'use_mail']
        (model, extra_model) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        self.assertEqual(len(extra_model), 1, 'an extra model should have been created for stages')
        stage_fields = self.env[extra_model.model]._fields
        self.assertIn('x_studio_sequence', stage_fields, 'stages should have a sequence')
        fields = self.env[model.model]._fields
        self.assertIn('x_studio_stage_id', fields, 'a custom stage field should be set up')
        self.assertIn('x_studio_priority', fields, 'a custom priority field should be set up')
        self.assertIn('x_color', fields, 'a custom color field should be set up')
        self.assertIn('x_studio_kanban_state', fields, 'a custom kanban state field should be set up')
        auto_stage = self.env[extra_model.model].search([])
        default = self.env['ir.default']._get(model.model, 'x_studio_stage_id')
        self.assertEqual(default, auto_stage.ids[0], 'the default stage should be set')
        stage_field = self.env['ir.model.fields'].search([('name', '=', 'x_studio_stage_id'), ('model_id', '=', model.id)])
        self.assertTrue(stage_field.tracking, 'the x_studio_stage_id field should be tracked')

    def test_13_model_option_tags(self):
        """Test that the `tags` behaviour is set up correctly."""
        model_options = ['use_tags']
        (model, extra_model) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        self.assertEqual(len(extra_model), 1, 'an extra model should have been created for tags')
        stage_fields = self.env[extra_model.model]._fields
        self.assertIn('x_color', stage_fields, 'tags should have a color')
        fields = self.env[model.model]._fields
        self.assertIn('x_studio_tag_ids', fields, 'a custom tags field should be set up')
    
    def test_14_all_options(self):
        """Test auto-view generation for custom models with all options enabled."""
        # Enable ALL THE OPTIONS
        (model, extra_model) = self.env['ir.model'].studio_model_create('Rockets', options=OPTIONS_WL)
        # I'm just checking it doesn't crash for now 👐

    def test_15_custom_model_security(self):
        """Test that ACLs are created for a custom model."""
        model_options = []
        (model, _) = self.env['ir.model'].studio_model_create('Rockets', options=model_options)
        acl_admin = self.env['ir.model.access'].search([
            ('model_id', '=', model.id),
            ('group_id', '=', self.env.ref('base.group_system').id)
        ])
        self.assertTrue(acl_admin.perm_read, 'admin should have read access on custom models')
        self.assertTrue(acl_admin.perm_write, 'admin should have write access on custom models')
        self.assertTrue(acl_admin.perm_create, 'admin should have create access on custom models')
        self.assertTrue(acl_admin.perm_unlink, 'admin should have unlink access on custom models')
        acl_user = self.env['ir.model.access'].search([
            ('model_id', '=', model.id),
            ('group_id', '=', self.env.ref('base.group_user').id)
        ])
        self.assertTrue(acl_user.perm_read, 'user should have read access on custom models')
        self.assertTrue(acl_user.perm_write, 'user should have write access on custom models')
        self.assertTrue(acl_user.perm_create, 'user should have create access on custom models')
        self.assertFalse(acl_user.perm_unlink, 'user should not have unlink access on custom models')

    def test_16_next_relation(self):
        """Check that creating the same m2m will result in a new relation table."""
        IrModelFields = self.env["ir.model.fields"].with_context(studio=True)
        current_table = IrModelFields._custom_many2many_names(
            "res.currency", "res.country.state"
        )[0]
        new_m2m = IrModelFields.create(
            {
                "ttype": "many2many",
                "model_id": self.source_model.id,
                "relation": self.destination_model.model,
                "name": "x_state_ids_2",
                "relation_table": IrModelFields._get_next_relation(
                    self.source_model.model, self.destination_model.model
                ),
            }
        )
        self.assertNotEqual(
            new_m2m.relation_table,
            current_table,
            "the second m2m should have its own relation table",
        )

    def test_17_reverse_relation(self):
        IrModelFields = self.env["ir.model.fields"].with_context(studio=True)
        reverse_m2m = IrModelFields.create(
            {
                "ttype": "many2many",
                "model_id": self.destination_model.id,
                "relation": self.source_model.model,
                "name": "x_currency_ids",
                "relation_table": IrModelFields._get_next_relation(
                    self.destination_model.model, self.source_model.model
                ),
            }
        )
        self.assertEqual(
            self.m2m.relation_table,
            reverse_m2m.relation_table,
            "the second m2m should have the same relation table as the first m2m of the source model",
        )
        new_m2m = IrModelFields.create(
            {
                "ttype": "many2many",
                "model_id": self.source_model.id,
                "relation": self.destination_model.model,
                "name": "x_state_ids_2",
                "relation_table": IrModelFields._get_next_relation(
                    self.source_model.model, self.destination_model.model
                ),
            }
        )
        reverse_new_m2m = IrModelFields.create(
            {
                "ttype": "many2many",
                "model_id": self.destination_model.id,
                "relation": self.source_model.model,
                "name": "x_currency_ids_2",
                "relation_table": IrModelFields._get_next_relation(
                    self.destination_model.model, self.source_model.model
                ),
            }
        )
        self.assertEqual(
            new_m2m.relation_table,
            reverse_new_m2m.relation_table,
            "the second reverse m2m should have the same relation table as the second m2m of the source model",
        )

    def test_18_lots_of_relations(self):
        IrModelFields = self.env["ir.model.fields"].with_context(studio=True)
        NUM_TEST = 10  # because some people are just that stupid
        attempt = 0
        while attempt < NUM_TEST:
            attempt += 1
            IrModelFields.create(
                {
                    "ttype": "many2many",
                    "model_id": self.source_model.id,
                    "relation": self.destination_model.model,
                    "name": "x_currency_ids_%s" % attempt,
                    "relation_table": IrModelFields._get_next_relation(
                        self.source_model.model, self.destination_model.model
                    ),
                }
            )
        latest_relation = IrModelFields.search_read(
            [
                ("ttype", "=", "many2many"),
                ("model_id", "=", self.source_model.id),
                ("relation", "=", self.destination_model.model),
            ],
            fields=["relation_table"],
            order="id desc",
            limit=1,
        )
        default = IrModelFields._custom_many2many_names(
            self.source_model.model, self.destination_model.model
        )[0]
        self.assertEqual(
            latest_relation[0]["relation_table"], "%s_%s" % (default, NUM_TEST)
        )

    def test_19_custom_model_security(self):
        """Test that ACLs are created for a custom model using name create."""

        model_id, name = self.env['ir.model'].with_context(studio=True).name_create('X_Rockets')
        acl_admin = self.env['ir.model.access'].search([
            ('model_id', '=', model_id),
            ('group_id', '=', self.env.ref('base.group_system').id)
        ])
        self.assertTrue(acl_admin.perm_read, 'admin should have read access on custom models')
        self.assertTrue(acl_admin.perm_write, 'admin should have write access on custom models')
        self.assertTrue(acl_admin.perm_create, 'admin should have create access on custom models')
        self.assertTrue(acl_admin.perm_unlink, 'admin should have unlink access on custom models')
        acl_user = self.env['ir.model.access'].search([
            ('model_id', '=', model_id),
            ('group_id', '=', self.env.ref('base.group_user').id)
        ])
        self.assertTrue(acl_user.perm_read, 'user should have read access on custom models')
        self.assertTrue(acl_user.perm_write, 'user should have write access on custom models')
        self.assertTrue(acl_user.perm_create, 'user should have create access on custom models')
        self.assertFalse(acl_user.perm_unlink, 'user should not have unlink access on custom models')

    def test_20_prevent_double_underscore(self):
        IrModelFields = self.env["ir.model.fields"]
        with self.assertRaises(ValidationError, msg="Custom field names cannot contain double underscores."):
            IrModelFields.create(
                {
                    "ttype": "char",
                    "model_id": self.source_model.id,
                    "name": "x_studio_hello___hap",
                }
            )

    def test_21_set_view_mode_new_window_action(self):
        """Test that the `view_mode` for window action is set correctly."""

        model = self.env['ir.model'].create({
            'name': 'Rockets',
            'model': 'x_rockets',
            'field_id': [
                Command.create({'name': 'x_name', 'ttype': 'char', 'field_description': 'Name'}),
            ]
        })
        action = model._create_default_action('x_rockets')
        self.assertEqual(action.view_mode, 'list,form', 'list and form should be set as a default view mode on window action')

    def test_22_rename_window_action(self):
        """ Test renaming a menu will rename the windows action."""

        model = self.env['ir.model'].create({
            'name': 'Rockets',
            'model': 'x_rockets',
            'field_id': [
                Command.create({'name': 'x_name', 'ttype': 'char', 'field_description': 'Name'}),
            ]
        })
        action = model._create_default_action('Rockets')
        action_ref = 'ir.actions.act_window,' + str(action.id)
        new_menu = self.env['ir.ui.menu'].with_context(studio=True).create({
            'name': 'Rockets',
            'action': action_ref,
        })
        self.assertEqual(action.name, new_menu.name, 'action and menu name should be same')
        # rename the menu name
        new_menu.name = 'new Rockets'
        self.assertEqual(action.name, new_menu.name, 'rename the menu name should rename the window action name')

    def test_performance_01_fields_batch(self):
        """Test number of call to setup_models when creating a model with multiple"""
        count_setup_models = 0
        orig_setup_models = odoo.modules.registry.Registry.setup_models
        def setup_models(registry, cr):
            nonlocal count_setup_models
            count_setup_models += 1
            orig_setup_models(registry, cr)
        with patch('odoo.modules.registry.Registry.setup_models', new=setup_models):
            # not: using a specific model (PerformanceIssues and not Rockets) is important since after the rollback of the test,
            # the model will be missing but x_rockets is still in the pool, breaking some optimizations
            self.env['ir.model'].with_context(studio=True).studio_model_create('PerformanceIssues', options=OPTIONS_WL)
        self.assertEqual(count_setup_models, 1)

    def test_update_xmlid(self):
        record = self.env['ir.model.data'].search([], limit=1)
        with self.assertQueryCount(1):
            self.env['ir.model.data'].with_context(studio=True)._update_xmlids([
                {'xml_id': 'web_studio.xmlid', 'record': record}
            ])

    def test_ir_default_company_fields(self):
        model = self.env['ir.model'].create({
            'name': 'Rockets',
            'model': 'x_rockets',
            'field_id': [
                Command.create({'name': 'x_studio_company_id', 'ttype': 'many2one', 'relation': 'res.company'}),
                Command.create({'name': 'x_company_id', 'ttype': 'many2one', 'relation': 'res.company'}),
            ]
        })
        self.env["res.company"].create({"name": "new company test"})
        defaults = self.env["ir.default"].search([("field_id", "in", model.field_id.ids)])
        self.assertEqual(len(defaults), 2)
        self.assertEqual(defaults.mapped("field_id"), model.field_id.filtered(lambda f: f.relation == "res.company"))


@tagged("-at_install", "post_install")
class TestStudioIrModelHardcoded(TransactionCase):
    def test_23_export_hardcoded_models_and_fields(self):
        """ Test that all models and fields from hardcoded lists exist in the data model.
            Should be executed at post install time because obviously the models should all
            have a chance to get up to date.
        """
        needed_modules = {
            "account",
            "account_edi",
            "account_edi_ubl_cii",
            "analytic",
            "appointment",
            "auth_signup",
            "base",
            "base_automation",
            "calendar",
            "crm",
            "documents",
            "event",
            "helpdesk",
            "hr",
            "hr_recruitment",
            "knowledge",
            "loyalty",
            "mail",
            "mail_mobile",
            "maintenance",
            "mrp",
            "phone_validation",
            "planning",
            "point_of_sale",
            "portal",
            "pos_loyalty",
            "pos_preparation_display",
            "pos_restaurant",
            "product",
            "project",
            "purchase",
            "purchase_stock",
            "quality",
            "repair",
            "resource",
            "sale",
            "sale_management",
            "sale_planning",
            "sale_project",
            "sale_stock",
            "sale_subscription",
            "sales_team",
            "sign",
            "stock",
            "survey",
            "uom",
            "web_editor",
            "web_map",
            "web_studio",
            "website",
            "website_sale",
            "worksheet",
        }
        modules = self.env["ir.module.module"].search([('name', 'in', list(needed_modules))])
        self.assertEqual(len(needed_modules), len(modules))

        if ms := [m.name for m in modules if m.state != 'installed']:
            # At least one needed module is not installed, so we would not be able
            # to assert the hardcoded lists, so we skip the rest of the test.
            self.skipTest(f"Missing required modules {', '.join(ms)}")

        def check_ownership(model: str, field_name: str | None = None) -> None:
            self.assertIn(model, self.env, f"Unknown model {model}")
            if field_name:
                field = self.env[model]._fields.get(field_name)
                self.assertIsNotNone(field, f"Unknown field {model}.{field_name}")
                # sadly Field._module returns the module which last overrode
                # the field, and Field._modules has unstable ordering, so if
                # the field was overridden walk the MRO from the top
                module = field._module if len(field._modules) == 1 else next(
                    cls
                    for cls in reversed(self.registry[model].mro())
                    if hasattr(cls, field_name)
                )._module
                seen_modules.add(module)
                self.assertIn(
                    module,
                    needed_modules,
                    f"{model}.{field_name} was not added by a listed module",
                )
            else:
                seen_modules.add(self.env[model]._original_module)
                self.assertIn(
                    self.env[model]._original_module,
                    needed_modules,
                    f"{model} was not added by a listed module",
                )

        seen_modules = set()

        for model, defaults in PRESET_MODELS_DEFAULTS:
            check_ownership(model)
            for field in defaults:
                self.assertIn(field, self.env["studio.export.model"]._fields)

        for model, fields in DEFAULT_FIELDS_TO_EXCLUDE.items():
            for field in fields:
                check_ownership(model, field)

        for model, fields in ABSTRACT_MODEL_FIELDS_TO_EXCLUDE.items():
            for field in fields:
                check_ownership(model, field)

        for model, fields in FIELDS_TO_EXPORT.items():
            for field in fields:
                check_ownership(model, field)

        for model in DEFAULT_MODELS_TO_EXPORT:
            check_ownership(model)

        for model in RELATED_MODELS_TO_EXCLUDE:
            check_ownership(model)

        for model in MODELS_WITH_NOUPDATE:
            check_ownership(model)

        for model, fields in RELATIONS_NOT_TO_EXPORT.items():
            for field in fields:
                check_ownership(model, field)

        for model, field in XML_FIELDS:
            check_ownership(model, field)

        self.assertEqual(needed_modules, seen_modules)

    def test_24_export_all_required_fields(self):
        """Test that all required fields are exported"""

        for model, fields in FIELDS_TO_EXPORT.items():
            required_fields = [
                field_name
                for field_name, field_obj
                in self.env[model]._fields.items()
                if field_obj.required
                and field_obj.default is None
            ]
            for field in required_fields:
                self.assertIn(field, fields, f"required field {field} is not exported for model {model}")
