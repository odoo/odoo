# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tools import mute_logger
import odoo.tests.common as common


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
            'model_id': self.res_partner_model.id,
            'state': 'code',
            'code': 'record.write({"comment": "MyComment"})',
        })


class TestServerActions(TestServerActionsBase):

    def test_00_action(self):
        self.action.with_context(self.context).run()
        self.assertEqual(self.test_partner.comment, 'MyComment', 'ir_actions_server: invalid condition check')
        self.test_partner.write({'comment': False})

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
            'code': ("partner_name = record.name + '_code'\n"
                     "record.env['res.partner'].create({'name': partner_name})"),
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: code server action correctly finished should return False')

        partners = self.test_partner.search([('name', 'ilike', 'TestingPartner_code')])
        self.assertEqual(len(partners), 1, 'ir_actions_server: 1 new partner should have been created')

    def test_20_crud_create(self):
        _city = 'TestCity'
        _name = 'TestNew'

        # Do: create a new record in the same model and link it
        self.action.write({
            'state': 'object_create',
            'crud_model_id': self.action.model_id.id,
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

        # Do: create a new record in another model
        self.action.write({
            'state': 'object_create',
            'crud_model_id': self.res_country_model.id,
            'link_field_id': False,
            'fields_lines': [(5,),
                             (0, 0, {'col1': self.res_country_name_field.id, 'value': 'record.name', 'type': 'equation'}),
                             (0, 0, {'col1': self.res_country_code_field.id, 'value': 'record.name[0:2]', 'type': 'equation'})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new country created
        country = self.test_country.search([('name', 'ilike', 'TestingPartner')])
        self.assertEqual(len(country), 1, 'ir_actions_server: TODO')
        self.assertEqual(country.code, 'TE', 'ir_actions_server: TODO')

    def test_30_crud_write(self):
        _name = 'TestNew'

        # Do: update partner name
        self.action.write({
            'state': 'object_write',
            'fields_lines': [(0, 0, {'col1': self.res_partner_name_field.id, 'value': _name})],
        })
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: partner updated
        partner = self.test_partner.search([('name', 'ilike', _name)])
        self.assertEqual(len(partner), 1, 'ir_actions_server: TODO')
        self.assertEqual(partner.city, 'OrigCity', 'ir_actions_server: TODO')

    @mute_logger('odoo.addons.base.ir.ir_model', 'odoo.models')
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
            'fields_lines': [(0, 0, {'col1': self.res_partner_name_field.id, 'value': 'RaoulettePoiluchette'}),
                             (0, 0, {'col1': self.res_partner_city_field.id, 'value': 'TestingCity'})],
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
        partner = self.test_partner.search([('name', 'ilike', 'RaoulettePoiluchette')])
        self.assertEqual(len(partner), 1)
        # Test: action returned
        self.assertEqual(res.get('type'), 'ir.actions.act_url')

        # Test loops
        with self.assertRaises(ValidationError):
            self.action.write({
                'child_ids': [(6, 0, [self.action.id])]
            })
