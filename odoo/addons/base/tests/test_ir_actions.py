# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from datetime import date
from unittest.mock import patch

import requests
from markupsafe import Markup

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


class TestServerActionsBase(TransactionCaseWithUserDemo):

    def setUp(self):
        super().setUp()

        # Data on which we will run the server action
        self.test_country = self.env['res.country'].create({
            'name': 'TestingCountry',
            'code': 'TY',
            'address_format': 'SuperFormat',
            'name_position': 'before',
        })
        self.test_partner = self.env['res.partner'].create({
            'city': 'OrigCity',
            'country_id': self.test_country.id,
            'email': 'test.partner@test.example.com',
            'name': 'TestingPartner',
        })
        self.context = {
            'active_model': 'res.partner',
            'active_id': self.test_partner.id,
        }

        # Model data
        Model = self.env['ir.model']
        Fields = self.env['ir.model.fields']
        self.comment_html = '<p>MyComment</p>'
        self.res_partner_model = Model.search([('model', '=', 'res.partner')])
        self.res_partner_name_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'name')])
        self.res_partner_city_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'city')])
        self.res_partner_country_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'country_id')])
        self.res_partner_parent_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'parent_id')])
        self.res_partner_children_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'child_ids')])
        self.res_partner_category_field = Fields.search([('model', '=', 'res.partner'), ('name', '=', 'category_id')])
        self.res_country_model = Model.search([('model', '=', 'res.country')])
        self.res_country_name_field = Fields.search([('model', '=', 'res.country'), ('name', '=', 'name')])
        self.res_country_code_field = Fields.search([('model', '=', 'res.country'), ('name', '=', 'code')])
        self.res_country_name_position_field = Fields.search([('model', '=', 'res.country'), ('name', '=', 'name_position')])
        self.res_partner_category_model = Model.search([('model', '=', 'res.partner.category')])
        self.res_partner_category_name_field = Fields.search([('model', '=', 'res.partner.category'), ('name', '=', 'name')])

        # create server action to
        self.action = self.env['ir.actions.server'].create({
            'name': 'TestAction',
            'model_id': self.res_partner_model.id,
            'model_name': 'res.partner',
            'state': 'code',
            'code': 'record.write({"comment": "%s"})' % self.comment_html,
        })

        server_action_model = Model.search([('model', '=', 'ir.actions.server')])
        self.test_server_action = self.env['ir.actions.server'].create({
            'name': 'TestDummyServerAction',
            'model_id': server_action_model.id,
            'state': 'code',
            'code':
"""
_logger.log(10, "This is a %s debug %s", "test", "log")
_logger.info("This is a %s info %s", "test", "log")
_logger.warning("This is a %s warning %s", "test", "log")
_logger.error("This is a %s error %s", "test", "log")
try:
    0/0
except:
    _logger.exception("This is a %s exception %s", "test", "log")
""",
        })


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestServerActions(TestServerActionsBase):
    def test_00_server_action(self):
        with self.assertLogs('odoo.addons.base.models.ir_actions.server_action_safe_eval',
                             level='DEBUG') as log_catcher:
            self.test_server_action.run()
            self.assertEqual(log_catcher.output, [
                'DEBUG:odoo.addons.base.models.ir_actions.server_action_safe_eval:This is a test debug log',
                'INFO:odoo.addons.base.models.ir_actions.server_action_safe_eval:This is a test info log',
                'WARNING:odoo.addons.base.models.ir_actions.server_action_safe_eval:This is a test warning log',
                'ERROR:odoo.addons.base.models.ir_actions.server_action_safe_eval:This is a test error log',
"""ERROR:odoo.addons.base.models.ir_actions.server_action_safe_eval:This is a test exception log
Traceback (most recent call last):
  File "ir.actions.server(%d,)", line 6, in <module>
ZeroDivisionError: division by zero""" % self.test_server_action.id
            ])

    def test_00_action(self):
        self.action.with_context(self.context).run()
        self.assertEqual(self.test_partner.comment, self.comment_html, 'ir_actions_server: invalid condition check')
        self.test_partner.write({'comment': False})

        # Do: create contextual action
        self.action.create_action()
        self.assertEqual(self.action.binding_model_id.model, 'res.partner')

        # Do: remove contextual action
        self.action.unlink_action()
        self.assertFalse(self.action.binding_model_id)

    def test_10_code(self):
        self.action.write({
            'state': 'code',
            'code': ("partner_name = record.name + '_code'\n"
                     "record.env['res.partner'].create({'name': partner_name})"),
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: code server action correctly finished should return False')

        partners = self.test_partner.search([('name', 'ilike', 'TestingPartner_code')])
        self.assertEqual(len(partners), 1, 'ir_actions_server: 1 new partner should have been created')

    def test_20_crud_create(self):
        # Do: create a new record in another model
        self.action.write({
            'state': 'object_create',
            'crud_model_id': self.res_partner_model.id,
            'link_field_id': False,
            'value': 'TestingPartner2'
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new partner created
        partner = self.test_partner.search([('name', 'ilike', 'TestingPartner2')])
        self.assertEqual(len(partner), 1, 'ir_actions_server: TODO')

    def test_20_crud_create_link_many2one(self):

        # Do: create a new record in the same model and link it with a many2one
        self.action.write({
            'state': 'object_create',
            'crud_model_id': self.res_partner_model.id,
            'link_field_id': self.res_partner_parent_field.id,
            'value': "TestNew"
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new partner created
        partner = self.test_partner.search([('name', 'ilike', 'TestNew')])
        self.assertEqual(len(partner), 1, 'ir_actions_server: TODO')
        # Test: new partner linked
        self.assertEqual(self.test_partner.parent_id, partner, 'ir_actions_server: TODO')

    def test_20_crud_create_link_one2many(self):

        # Do: create a new record in the same model and link it with a one2many
        self.action.write({
            'state': 'object_create',
            'crud_model_id': self.res_partner_model.id,
            'link_field_id': self.res_partner_children_field.id,
            'value': 'TestNew',
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new partner created
        partner = self.test_partner.search([('name', 'ilike', 'TestNew')])
        self.assertEqual(len(partner), 1, 'ir_actions_server: TODO')
        self.assertEqual(partner.name, 'TestNew', 'ir_actions_server: TODO')
        # Test: new partner linked
        self.assertIn(partner, self.test_partner.child_ids, 'ir_actions_server: TODO')

    def test_20_crud_create_link_many2many(self):
        # Do: create a new record in another model
        self.action.write({
            'state': 'object_create',
            'crud_model_id': self.res_partner_category_model.id,
            'link_field_id': self.res_partner_category_field.id,
            'value': 'TestingPartner'
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new category created
        category = self.env['res.partner.category'].search([('name', 'ilike', 'TestingPartner')])
        self.assertEqual(len(category), 1, 'ir_actions_server: TODO')
        self.assertIn(category, self.test_partner.category_id)

    def test_25_crud_copy(self):
        self.action.write({
            'state': 'object_copy',
            'crud_model_id': self.res_partner_model.id,
            'resource_ref': self.test_partner,
        })
        partner = self.env['res.partner'].search([('name', 'ilike', self.test_partner.name)])
        self.assertEqual(len(partner), 1)
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: duplicate record action correctly finished should return False')
        partner = self.env['res.partner'].search([('name', 'ilike', self.test_partner.name)])
        self.assertEqual(len(partner), 2)

    def test_25_crud_copy_link_many2one(self):
        self.action.write({
            'state': 'object_copy',
            'crud_model_id': self.res_partner_model.id,
            'resource_ref': self.test_partner,
            'link_field_id': self.res_partner_parent_field.id,
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: duplicate record action correctly finished should return False')
        dupe = self.test_partner.search([('name', 'ilike', self.test_partner.name), ('id', '!=', self.test_partner.id)])
        self.assertEqual(len(dupe), 1)
        self.assertEqual(self.test_partner.parent_id, dupe)

    def test_25_crud_copy_link_one2many(self):
        self.action.write({
            'state': 'object_copy',
            'crud_model_id': self.res_partner_model.id,
            'resource_ref': self.test_partner,
            'link_field_id': self.res_partner_children_field.id,
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: duplicate record action correctly finished should return False')
        dupe = self.test_partner.search([('name', 'ilike', self.test_partner.name), ('id', '!=', self.test_partner.id)])
        self.assertEqual(len(dupe), 1)
        self.assertIn(dupe, self.test_partner.child_ids)

    def test_25_crud_copy_link_many2many(self):
        category_id = self.env['res.partner.category'].name_create("CategoryToDuplicate")[0]
        self.action.write({
            'state': 'object_copy',
            'crud_model_id': self.res_partner_category_model.id,
            'link_field_id': self.res_partner_category_field.id,
            'resource_ref': f'res.partner.category,{category_id}',
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: duplicate record action correctly finished should return False')
        dupe = self.env['res.partner.category'].search([('name', 'ilike', 'CategoryToDuplicate'), ('id', '!=', category_id)])
        self.assertEqual(len(dupe), 1)
        self.assertIn(dupe, self.test_partner.category_id)

    def test_30_crud_write(self):
        # Do: update partner name
        self.action.write({
            'state': 'object_write',
            'update_path': 'name',
            'value': 'TestNew',
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: partner updated
        partner = self.test_partner.search([('name', 'ilike', 'TestNew')])
        self.assertEqual(len(partner), 1, 'ir_actions_server: TODO')
        self.assertEqual(partner.city, 'OrigCity', 'ir_actions_server: TODO')

    def test_31_crud_write_html(self):
        self.assertEqual(self.action.value, False)
        self.action.write({
            'state': 'object_write',
            'update_path': 'comment',
            'html_value': '<p>MyComment</p>',
        })
        self.assertEqual(self.action.html_value, Markup('<p>MyComment</p>'))
        # Test run
        self.assertEqual(self.test_partner.comment, False)
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        self.assertEqual(self.test_partner.comment, Markup('<p>MyComment</p>'))

    def test_object_write_equation(self):
        # Do: update partners city
        self.action.write({
            'state': 'object_write',
            'update_path': 'city',
            'evaluation_type': 'equation',
            'value': 'record.id',
        })
        partners = self.test_partner + self.test_partner.copy()
        self.action.with_context(self.context, active_ids=partners.ids).run()
        # Test: partners updated
        self.assertEqual(partners[0].city, str(partners[0].id))
        self.assertEqual(partners[1].city, str(partners[1].id))

    def test_35_crud_write_selection(self):
        # Don't want to use res.partner because no 'normal selection field' exists there
        # we'll use a speficic action for this test instead of the one from the test setup
        # Do: update country name_position field
        selection_value = self.res_country_name_position_field.selection_ids.filtered(lambda s: s.value == 'after')
        action = self.env['ir.actions.server'].create({
            'name': 'TestAction',
            'model_id': self.res_country_model.id,
            'model_name': 'res.country',
            'state': 'object_write',
            'update_path': 'name_position',
            'selection_value': selection_value.id,
        })
        action._set_selection_value()  # manual onchange
        self.assertEqual(action.value, selection_value.value)
        context = {
            'active_model': 'res.country',
            'active_id': self.test_country.id,
        }
        run_res = action.with_context(context).run()
        self.assertFalse(run_res, 'ir_actions_server: update record action correctly finished should return False')
        # Test: country updated
        self.assertEqual(self.test_country.name_position, 'after')

    def test_36_crud_write_m2m_ops(self):
        """ Test that m2m operations work as expected """
        categ_1 = self.env['res.partner.category'].create({'name': 'TestCateg1'})
        categ_2 = self.env['res.partner.category'].create({'name': 'TestCateg2'})
        # set partner category
        self.action.write({
            'state': 'object_write',
            'update_path': 'category_id',
            'update_m2m_operation': 'set',
            'resource_ref': categ_1,
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: update record action correctly finished should return False')
        # Test: partner updated
        self.assertIn(categ_1, self.test_partner.category_id, 'ir_actions_server: tag should have been set')

        # add partner category
        self.action.write({
            'state': 'object_write',
            'update_path': 'category_id',
            'update_m2m_operation': 'add',
            'resource_ref': categ_2,
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: update record action correctly finished should return False')
        # Test: partner updated
        self.assertIn(categ_2, self.test_partner.category_id, 'ir_actions_server: new tag should have been added')
        self.assertIn(categ_1, self.test_partner.category_id, 'ir_actions_server: old tag should still be there')

        # remove partner category
        self.action.write({
            'state': 'object_write',
            'update_path': 'category_id',
            'update_m2m_operation': 'remove',
            'resource_ref': categ_1,
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: update record action correctly finished should return False')
        # Test: partner updated
        self.assertNotIn(categ_1, self.test_partner.category_id, 'ir_actions_server: tag should have been removed')
        self.assertIn(categ_2, self.test_partner.category_id, 'ir_actions_server: tag should still be there')

        # clear partner category
        self.action.write({
            'state': 'object_write',
            'update_path': 'category_id',
            'update_m2m_operation': 'clear',
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: update record action correctly finished should return False')
        # Test: partner updated
        self.assertFalse(self.test_partner.category_id, 'ir_actions_server: tags should have been cleared')

    def test_37_field_path_traversal(self):
        """ Test the update_path field traversal - allowing records to be updated along relational links """
        # update the country's name via the partner
        self.action.write({
            'state': 'object_write',
            'update_path': 'country_id.name',
            'value': 'TestUpdatedCountry',
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: update record action correctly finished should return False')
        # Test: partner updated
        self.assertEqual(self.test_partner.country_id.name, 'TestUpdatedCountry', 'ir_actions_server: country name should have been updated through relation')

        # update a readonly field
        self.action.write({
            'state': 'object_write',
            'update_path': 'country_id.image_url',
            'value': "/base/static/img/country_flags/be.png",
        })
        self.assertEqual(self.test_partner.country_id.image_url, "/base/static/img/country_flags/ty.png", 'ir_actions_server: country flag has this value before the update')
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: update record action correctly finished should return False')
        # Test: partner updated
        self.assertEqual(self.test_partner.country_id.image_url, "/base/static/img/country_flags/be.png", 'ir_actions_server: country should have been updated through a readonly field')
        self.assertEqual(self.test_partner.country_id.code, "TY", 'ir_actions_server: country code is still TY')

        # input an invalid path
        with self.assertRaises(ValidationError):
            self.action.write({
                'state': 'object_write',
                'update_path': 'country_id.name.foo',
                'value': 'DoesNotMatter',
            })
            self.action.flush_recordset(['update_path', 'update_field_id'])

    def test_39_boolean_update(self):
        """ Test that boolean fields can be updated """
        # update the country's name via the partner
        self.action.write({
            'state': 'object_write',
            'update_path': 'active',
            'update_boolean_value': 'false',
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: update record action correctly finished should return False')
        # Test: partner updated
        self.assertFalse(self.test_partner.active, 'ir_actions_server: partner should have been deactivated')
        self.action.write({
            'state': 'object_write',
            'update_path': 'active',
            'update_boolean_value': 'true',
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: update record action correctly finished should return False')
        # Test: partner updated
        self.assertTrue(self.test_partner.active, 'ir_actions_server: partner should have been reactivated')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_40_multi(self):
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
            'crud_model_id': self.res_partner_model.id,
            'state': 'object_create',
            'value': 'RaoulettePoiluchette',
        })
        action3 = self.action.create({
            'name': 'Subaction2',
            'sequence': 3,
            'model_id': self.res_partner_model.id,
            'state': 'object_write',
            'update_path': 'city',
            'value': 'RaoulettePoiluchette',
        })
        action4 = self.action.create({
            'name': 'Subaction3',
            'sequence': 4,
            'model_id': self.res_partner_model.id,
            'state': 'code',
            'code': 'action = {"type": "ir.actions.act_url"}',
        })
        self.action.write({
            'state': 'multi',
            'child_ids': [Command.set([action1.id, action2.id, action3.id, action4.id])],
        })

        # Do: run the action
        res = self.action.with_context(self.context).run()

        # Test: new partner created
        # currently res_partner overrides default['name'] whatever its value
        partner = self.test_partner.search([('name', 'ilike', 'RaoulettePoiluchette')])
        self.assertEqual(len(partner), 1)
        # Test: action returned
        self.assertEqual(res.get('type'), 'ir.actions.act_url')

        # Test loops
        with self.assertRaises(ValidationError):
            self.action.write({
                'child_ids': [Command.set([self.action.id])]
            })

    def test_50_groups(self):
        """ check the action is returned only for groups dedicated to user """
        Actions = self.env['ir.actions.actions']

        group0 = self.env['res.groups'].create({'name': 'country group'})

        self.context = {
            'active_model': 'res.country',
            'active_id': self.test_country.id,
        }

        # Do: update model and group
        self.action.write({
            'model_id': self.res_country_model.id,
            'binding_model_id': self.res_country_model.id,
            'group_ids': [Command.link(group0.id)],
            'code': 'record.write({"vat_label": "VatFromTest"})',
        })

        # Test: action is not returned
        bindings = Actions.get_bindings('res.country')
        self.assertFalse(bindings)

        with self.assertRaises(AccessError):
            self.action.with_context(self.context).run()
        self.assertFalse(self.test_country.vat_label)

        # add group to the user, and test again
        self.env.user.write({'group_ids': [Command.link(group0.id)]})

        bindings = Actions.get_bindings('res.country')
        self.assertItemsEqual(bindings.get('action'), self.action.read(['name', 'sequence', 'binding_view_types']))

        self.action.with_context(self.context).run()
        self.assertEqual(self.test_country.vat_label, 'VatFromTest', 'vat label should be changed to VatFromTest')

    def test_60_sort(self):
        """ check the actions sorted by sequence """
        Actions = self.env['ir.actions.actions']

        # Do: update model
        self.action.write({
            'model_id': self.res_country_model.id,
            'binding_model_id': self.res_country_model.id,
        })
        self.action2 = self.action.copy({'name': 'TestAction2', 'sequence': 1})

        # Test: action returned by sequence
        bindings = Actions.get_bindings('res.country')
        self.assertEqual([vals.get('name') for vals in bindings['action']], ['TestAction2', 'TestAction'])
        self.assertEqual([vals.get('sequence') for vals in bindings['action']], [1, 5])

    def test_70_copy_action(self):
        # first check that the base case (reset state) works normally
        r = self.env['ir.actions.todo'].create({
            'action_id': self.action.id,
            'state': 'done',
        })
        self.assertEqual(r.state, 'done')
        self.assertEqual(
            r.copy().state, 'open',
            "by default state should be reset by copy"
        )

        # then check that on server action we've changed that
        self.assertEqual(
            self.action.copy().state, 'code',
            "copying a server action should not reset the state"
        )

    def test_80_permission(self):
        self.action.write({
            'state': 'code',
            'code': """record.write({'name': str(datetime.date.today())})""",
        })

        user_demo = self.user_demo
        self_demo = self.action.with_user(user_demo.id)

        # can write on contact partner
        self.test_partner.type = "contact"
        self.test_partner.with_user(user_demo.id).check_access("write")

        self_demo.with_context(self.context).run()
        self.assertEqual(self.test_partner.name, str(date.today()))

    def test_90_webhook(self):
        self.action.write({
            'state': 'webhook',
            'webhook_field_ids': [
                Command.link(self.res_partner_name_field.id),
                Command.link(self.res_partner_city_field.id),
                Command.link(self.res_partner_country_field.id),
                ],
            'webhook_url': 'http://example.com/webhook',
        })
        # write a mock for the requests.post method that checks the data
        # and returns a 200 response
        num_requests = 0
        def _patched_post(*args, **kwargs):
            nonlocal num_requests
            response = requests.Response()
            response.status_code = 200 if num_requests == 0 else 400
            self.assertEqual(args[0], 'http://example.com/webhook')
            self.assertEqual(kwargs['data'], json.dumps({
                '_action': "%s(#%s)" % (self.action.name, self.action.id),
                '_id': self.test_partner.id,
                '_model': self.test_partner._name,
                'city': self.test_partner.city,
                'country_id': self.test_partner.country_id.id,
                'id': self.test_partner.id,
                'name': self.test_partner.name,
            }))
            num_requests += 1
            return response

        with patch.object(requests, 'post', _patched_post), mute_logger('odoo.addons.base.models.ir_actions'):
            # first run: 200
            self.action.with_context(self.context).run()
            self.env.cr.postcommit.run()  # webhooks run in postcommit
            # second run: 400, should *not* raise but
            # should warn in logs (hence mute_logger)
            self.action.with_context(self.context).run()
            self.env.cr.postcommit.run()  # webhooks run in postcommit
        self.assertEqual(num_requests, 2)

    def test_90_convert_to_float(self):
        # make sure eval_value convert the value into float for float-type fields
        self.action.write({
            'state': 'object_write',
            'update_path': 'partner_latitude',
            'value': '20.99',
        })
        self.assertEqual(self.action._eval_value()[self.action.id], 20.99)
