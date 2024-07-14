
from unittest.mock import patch

import odoo

from odoo.tests.common import TransactionCase
from odoo.addons.web_studio.controllers.export import MODELS_TO_EXPORT, FIELDS_TO_EXPORT, \
     FIELDS_NOT_TO_EXPORT, CDATA_FIELDS, XML_FIELDS
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
        self.assertIn((self.partner_elon.id, '"Elon Tusk" <elon@spacex.com>', None, 'Contact', {}),
                      mail_suggested_recipients.get(bfr.id),
                      'custom partner field should be suggested in mail communications')
        sms_suggested_recipients = bfr._mail_get_partner_fields(introspect_fields=False)
        self.assertIn('x_studio_partner_id', sms_suggested_recipients,
                      'custom partner field should be included in sms communications')

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
        self.assertEqual(action.view_mode, 'tree,form', 'tree and form should be set as a default view mode on window action')

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

    def test_23_export_hardcoded_models_and_fields(self):
        """Test that all models and fields from hardcoded lists exist in the data model"""

        for model in MODELS_TO_EXPORT:
            self.assertIn(model, self.env)

        for model, fields in FIELDS_TO_EXPORT.items():
            for field in fields:
                self.assertIn(field, self.env[model]._fields)

        for model, fields in FIELDS_NOT_TO_EXPORT.items():
            for field in fields:
                self.assertIn(field, self.env[model]._fields)

        for model, field in CDATA_FIELDS:
            self.assertIn(field, self.env[model]._fields)

        for model, field in XML_FIELDS:
            self.assertIn(field, self.env[model]._fields)

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
