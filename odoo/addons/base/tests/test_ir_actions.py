# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tools import mute_logger
import odoo.tests.common as common
import odoo.workflow


class TestServerActionsBase(common.TransactionCase):

    def setUp(self):
        super(TestServerActionsBase, self).setUp()

        # Data on which we will run the server action
        self.test_country = self.env['res.country'].create({
            'name': 'TestingCountry',
            'code': 'TY',
            'address_format': 'SuperFormat',
        })
        self.test_partner = self.env['res.partner'].create({
            'name': 'TestingPartner',
            'city': 'OrigCity',
            'country_id': self.test_country.id,
        })
        self.context = {
            'active_model': 'res.partner',
            'active_id': self.test_partner.id,
        }

        # Model data
        Model = self.env['ir.model']
        Fields = self.env['ir.model.fields']
        self.res_partner_model = Model.search([('model', '=', 'res.partner')])
        self.res_partner_name_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'name')])
        self.res_partner_city_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'city')])
        self.res_partner_country_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'country_id')])
        self.res_partner_parent_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'parent_id')])
        self.res_country_model = Model.search([('model', '=', 'res.country')])
        self.res_country_name_field = Fields.search([('model', '=', 'res.country'), ('name', '=', 'name')])
        self.res_country_code_field = Fields.search([('model', '=', 'res.country'), ('name', '=', 'code')])

        # create server action to
        self.action = self.env['ir.actions.server'].create({
            'name': 'TestAction',
            'condition': 'True',
            'model_id': self.res_partner_model.id,
            'state': 'code',
            'code': 'obj.write({"comment": "MyComment"})',
        })


class TestServerActions(TestServerActionsBase):

    def test_00_action(self):
        # Do: eval 'True' condition
        self.action.with_context(self.context).run()
        self.assertEqual(self.test_partner.comment, 'MyComment', 'ir_actions_server: invalid condition check')
        self.test_partner.write({'comment': False})

        # Do: eval False condition, that should be considered as True (void = True)
        self.action.write({'condition': False})
        self.action.with_context(self.context).run()
        self.assertEqual(self.test_partner.comment, 'MyComment', 'ir_actions_server: invalid condition check')

        # Do: create contextual action
        self.action.create_action()

        # Test: ir_values created
        ir_values = self.env['ir.values'].search([('name', '=', 'Run TestAction')])
        self.assertEqual(len(ir_values), 1, 'ir_actions_server: create_action should have created an entry in ir_values')
        self.assertEqual(ir_values.value, 'ir.actions.server,%s' % self.action.id, 'ir_actions_server: created ir_values should reference the server action')
        self.assertEqual(ir_values.model, 'res.partner', 'ir_actions_server: created ir_values should be linked to the action base model')

        # Do: remove contextual action
        self.action.unlink_action()

        # Test: ir_values removed
        ir_values = self.env['ir.values'].search([('name', '=', 'Run TestAction')])
        self.assertEqual(len(ir_values), 0, 'ir_actions_server: unlink_action should remove the ir_values record')

    def test_10_code(self):
        self.action.write({
            'state': 'code',
            'code': ("partner_name = obj.name + '_code'\n"
                     "obj.env['res.partner'].create({'name': partner_name})\n"
                     "workflow"),
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: code server action correctly finished should return False')

        partners = self.test_partner.search([('name', 'ilike', 'TestingPartner_code')])
        self.assertEqual(len(partners), 1, 'ir_actions_server: 1 new partner should have been created')

    def test_20_trigger(self):
        Workflow = self.env['workflow']
        WorkflowActivity = self.env['workflow.activity']
        WorkflowTransition = self.env['workflow.transition']

        # Data: code server action (at this point code-based actions should work)
        action2 = self.action.create({
            'name': 'TestAction2',
            'type': 'ir.actions.server',
            'condition': 'True',
            'model_id': self.res_partner_model.id,
            'state': 'code',
            'code': 'obj.write({"comment": "MyComment"})',
        })
        action3 = self.action.create({
            'name': 'TestAction3',
            'type': 'ir.actions.server',
            'condition': 'True',
            'model_id': self.res_country_model.id,
            'state': 'code',
            'code': 'obj.write({"code": "ZZ"})',
        })

        # Data: create workflows
        partner_workflow = Workflow.create({
            'name': 'TestWorkflow',
            'osv': 'res.partner',
            'on_create': True,
        })
        partner_activity1 = WorkflowActivity.create({
            'name': 'PartnerStart',
            'wkf_id': partner_workflow.id,
            'flow_start': True,
        })
        partner_activity2 = WorkflowActivity.create({
            'name': 'PartnerTwo',
            'wkf_id': partner_workflow.id,
            'kind': 'function',
            'action': 'True',
            'action_id': action2.id,
        })
        partner_transition1 = WorkflowTransition.create({
            'signal': 'partner_trans',
            'act_from': partner_activity1.id,
            'act_to': partner_activity2.id,
        })
        country_workflow = Workflow.create({
            'name': 'TestWorkflow',
            'osv': 'res.country',
            'on_create': True,
        })
        country_activity1 = WorkflowActivity.create({
            'name': 'CountryStart',
            'wkf_id': country_workflow.id,
            'flow_start': True,
        })
        country_activity2 = WorkflowActivity.create({
            'name': 'CountryTwo',
            'wkf_id': country_workflow.id,
            'kind': 'function',
            'action': 'True',
            'action_id': action3.id,
        })
        country_transition1 = WorkflowTransition.create({
            'signal': 'country_trans',
            'act_from': country_activity1.id,
            'act_to': country_activity2.id,
        })

        # Data: re-create country and partner to benefit from the workflows
        country = self.test_country.create({
            'name': 'TestingCountry2',
            'code': 'T2',
        })
        partner = self.test_partner.create({
            'name': 'TestingPartner2',
            'country_id': country.id,
        })
        context = dict(self.context, active_id=partner.id)

        # Run the action on partner object itself ('base')
        self.action.write({
            'state': 'trigger',
            'use_relational_model': 'base',
            'wkf_model_id': self.res_partner_model.id,
            'wkf_transition_id': partner_transition1.id,
        })
        self.action.with_context(context).run()
        self.assertEqual(partner.comment, 'MyComment', 'ir_actions_server: incorrect signal trigger')

        # Run the action on related country object ('relational')
        self.action.write({
            'use_relational_model': 'relational',
            'wkf_model_id': self.res_country_model.id,
            'wkf_field_id': self.res_partner_country_field.id,
            'wkf_transition_id': country_transition1.id,
        })
        self.action.with_context(context).run()
        self.assertEqual(country.code, 'ZZ', 'ir_actions_server: incorrect signal trigger')

        # Clear workflow cache, otherwise odoo will try to create workflows even if it has been deleted
        odoo.workflow.clear_cache(self.cr, self.uid)

    def test_30_client(self):
        client_action = self.env['ir.actions.client'].create({
            'name': 'TestAction2',
            'tag': 'Test',
        })
        self.action.write({
            'state': 'client_action',
            'action_id': client_action.id,
        })
        res = self.action.with_context(self.context).run()
        self.assertEqual(res['name'], 'TestAction2', 'ir_actions_server: incorrect return result for a client action')

    def test_40_crud_create(self):
        _city = 'TestCity'
        _name = 'TestNew'

        # Do: create a new record in the same model and link it
        self.action.write({
            'state': 'object_create',
            'use_create': 'new',
            'link_new_record': True,
            'link_field_id': self.res_partner_parent_field.id,
            'fields_lines': [(0, 0, {'col1': self.res_partner_name_field.id, 'value': _name}),
                             (0, 0, {'col1': self.res_partner_city_field.id, 'value': _city})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new partner created
        partner = self.test_partner.search([('name', 'ilike', _name)])
        self.assertEqual(len(partner), 1, 'ir_actions_server: TODO')
        self.assertEqual(partner.city, _city, 'ir_actions_server: TODO')
        # Test: new partner linked
        self.assertEqual(self.test_partner.parent_id, partner, 'ir_actions_server: TODO')

        # Do: copy current record
        self.action.write({
            'state': 'object_create',
            'use_create': 'copy_current',
            'link_new_record': False,
            'fields_lines': [(5,),
                             (0, 0, {'col1': self.res_partner_name_field.id, 'value': 'TestCopyCurrent'}),
                             (0, 0, {'col1': self.res_partner_city_field.id, 'value': 'TestCity'})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new partner created
        partner = self.test_partner.search([('name', 'ilike', 'TestingPartner (copy)')])  # currently res_partner overrides default['name'] whatever its value
        self.assertEqual(len(partner), 1, 'ir_actions_server: TODO')
        self.assertEqual(partner.city, 'TestCity', 'ir_actions_server: TODO')
        self.assertEqual(partner.country_id, self.test_partner.country_id, 'ir_actions_server: TODO')

        # Do: create a new record in another model
        self.action.write({
            'state': 'object_create',
            'use_create': 'new_other',
            'crud_model_id': self.res_country_model.id,
            'link_new_record': False,
            'fields_lines': [(5,),
                             (0, 0, {'col1': self.res_country_name_field.id, 'value': 'obj.name', 'type': 'equation'}),
                             (0, 0, {'col1': self.res_country_code_field.id, 'value': 'obj.name[0:2]', 'type': 'equation'})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new country created
        country = self.test_country.search([('name', 'ilike', 'TestingPartner')])
        self.assertEqual(len(country), 1, 'ir_actions_server: TODO')
        self.assertEqual(country.code, 'TE', 'ir_actions_server: TODO')

        # Do: copy a record in another model
        self.action.write({
            'state': 'object_create',
            'use_create': 'copy_other',
            'crud_model_id': self.res_country_model.id,
            'link_new_record': False,
            'ref_object': 'res.country,%s' % self.test_country.id,
            'fields_lines': [(5,),
                             (0, 0, {'col1': self.res_country_name_field.id, 'value': 'NewCountry', 'type': 'value'}),
                             (0, 0, {'col1': self.res_country_code_field.id, 'value': 'NY', 'type': 'value'})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new country created
        country = self.test_country.search([('name', 'ilike', 'NewCountry')])
        self.assertEqual(len(country), 1, 'ir_actions_server: TODO')
        self.assertEqual(country.code, 'NY', 'ir_actions_server: TODO')
        self.assertEqual(country.address_format, 'SuperFormat', 'ir_actions_server: TODO')

    def test_50_crud_write(self):
        _name = 'TestNew'

        # Do: create a new record in the same model and link it
        self.action.write({
            'state': 'object_write',
            'use_write': 'current',
            'fields_lines': [(0, 0, {'col1': self.res_partner_name_field.id, 'value': _name})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new partner created
        partner = self.test_partner.search([('name', 'ilike', _name)])
        self.assertEqual(len(partner), 1, 'ir_actions_server: TODO')
        self.assertEqual(partner.city, 'OrigCity', 'ir_actions_server: TODO')

        # Do: copy current record
        self.action.write({
            'use_write': 'other',
            'crud_model_id': self.res_country_model.id,
            'ref_object': 'res.country,%s' % self.test_country.id,
            'fields_lines': [(5,), (0, 0, {'col1': self.res_country_name_field.id, 'value': 'obj.name', 'type': 'equation'})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new country created
        country = self.test_country.search([('name', 'ilike', 'TestNew')])
        self.assertEqual(len(country), 1, 'ir_actions_server: TODO')

        # Do: copy a record in another model
        self.action.write({
            'use_write': 'expression',
            'crud_model_id': self.res_country_model.id,
            'write_expression': 'object.country_id',
            'fields_lines': [(5,), (0, 0, {'col1': self.res_country_name_field.id, 'value': 'NewCountry', 'type': 'value'})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new country created
        country = self.test_country.search([('name', 'ilike', 'NewCountry')])
        self.assertEqual(len(country), 1, 'ir_actions_server: TODO')

    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
    def test_60_multi(self):
        # Data: 2 server actions that will be nested
        action1 = self.action.create({
            'name': 'Subaction1',
            'sequence': 1,
            'model_id': self.res_partner_model.id,
            'state': 'code',
            'code': 'action = {"type": "ir.actions.act_window"}',
        })
        action2 = self.action.create({
            'name': 'Subaction2',
            'sequence': 2,
            'model_id': self.res_partner_model.id,
            'state': 'object_create',
            'use_create': 'copy_current',
        })
        action3 = self.action.create({
            'name': 'Subaction3',
            'sequence': 3,
            'model_id': self.res_partner_model.id,
            'state': 'code',
            'code': 'action = {"type": "ir.actions.act_url"}',
        })
        self.action.write({
            'state': 'multi',
            'child_ids': [(6, 0, [action1.id, action2.id, action3.id])],
        })

        # Do: run the action
        res = self.action.with_context(self.context).run()

        # Test: new partner created
        # currently res_partner overrides default['name'] whatever its value
        partner = self.test_partner.search([('name', 'ilike', 'TestingPartner (copy)')])
        self.assertEqual(len(partner), 1, 'ir_actions_server: TODO')
        # Test: action returned
        self.assertEqual(res.get('type'), 'ir.actions.act_url')

        # Test loops
        with self.assertRaises(ValidationError):
            self.action.write({
                'child_ids': [(6, 0, [self.action.id])]
            })


class TestCustomFields(common.TransactionCase):
    MODEL = 'res.partner'

    def setUp(self):
        # use a test cursor instead of a real cursor
        registry = odoo.registry()
        registry.enter_test_mode()
        fnames = set(registry[self.MODEL]._fields)

        @self.addCleanup
        def callback():
            registry.leave_test_mode()
            # the tests may have modified the registry, reset it
            with registry.cursor() as cr:
                registry.clear_manual_fields()
                registry.setup_models(cr)
                assert set(registry[self.MODEL]._fields) == fnames

        super(TestCustomFields, self).setUp()

    def create_field(self, name):
        """ create a custom field and return it """
        model = self.env['ir.model'].search([('model', '=', self.MODEL)])
        field = self.env['ir.model.fields'].create({
            'model_id': model.id,
            'name': name,
            'field_description': name,
            'ttype': 'char',
        })
        self.assertIn(name, self.env[self.MODEL]._fields)
        return field

    def test_create_custom(self):
        """ custom field names must be start with 'x_' """
        with self.assertRaises(ValidationError):
            self.create_field('foo')

    def test_rename_custom(self):
        """ custom field names must be start with 'x_' """
        field = self.create_field('x_foo')
        with self.assertRaises(ValidationError):
            field.name = 'foo'

    def test_create_valid(self):
        """ field names must be valid pg identifiers """
        with self.assertRaises(ValidationError):
            self.create_field('x_foo bar')

    def test_rename_valid(self):
        """ field names must be valid pg identifiers """
        field = self.create_field('x_foo')
        with self.assertRaises(ValidationError):
            field.name = 'x_foo bar'
