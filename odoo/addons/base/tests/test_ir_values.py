# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestIrValues(TransactionCase):

    def test_defaults(self):
        # Create some default value for some model, for all users.
        ir_values = self.env['ir.values']
        ir_values.set_default('res.partner', 'ref', 'X11')
        ir_values.set_default('res.partner.title', 'shortcut', 'Mr', condition='name=Mister')

        # Retrieve them: ds is a list of triplets (id, name, value)
        ds = ir_values.get_defaults('res.partner')
        d = next((d for d in ds if d[1] == 'ref'), None)
        self.assertTrue(d, "At least one value should be retrieved for this model.")
        self.assertEqual(d[2], 'X11', "Can't retrieve the created default value.")

        ds = ir_values.get_defaults('res.partner.title')
        d = next((d for d in ds if d[1] == 'shortcut'), None)
        self.assertFalse(d, "No value should be retrieved, the condition is not met.")

        ds = ir_values.get_defaults('res.partner.title', condition="name=Miss")
        d = next((d for d in ds if d[1] == 'shortcut'), None)
        self.assertFalse(d, "No value should be retrieved, the condition is not met.")

        ds = ir_values.get_defaults('res.partner.title', condition="name=Mister")
        d = next((d for d in ds if d[1] == 'shortcut'), None)
        self.assertTrue(d, "At least one value should be retrieved.")
        self.assertEqual(d[2], 'Mr', "Can't retrieve the created default value.")

        # Do it again but for a specific user.
        ir_values.set_default('res.partner', 'ref', '007', for_all_users=False)

        # Retrieve it and check it is the one for the current user.
        ds = ir_values.get_defaults('res.partner')
        d = next((d for d in ds if d[1] == 'ref'), None)
        self.assertTrue(d, "At least one value should be retrieved for this model.")
        self.assertEqual(d[2], '007', "Can't retrieve the created default value.")

        # create valid but unusable defaults, a ValidationError should not be thrown
        with tools.mute_logger('odoo.addons.base.ir.ir_values'):
            ir_values.set_default('unknown_model', 'unknown_field', 42)
            ir_values.set_default('res.partner', 'unknown_field', 42)

        # create invalid defaults
        with self.assertRaises(ValidationError):
            ir_values.set_default('res.partner', 'lang', 'some_LANG')
        with self.assertRaises(ValidationError):
            ir_values.set_default('res.partner', 'credit_limit', 'foo')

    def test_actions(self):
        # Create some action bindings for a model.
        act_id_1 = self.ref('base.act_values_form_action')
        act_id_2 = self.ref('base.act_values_form_defaults')
        act_id_3 = self.ref('base.action_res_company_form')
        ir_values = self.env['ir.values']
        ir_values.set_action('OnDblClick Action', action_slot='tree_but_open', model='res.partner', action='ir.actions.act_window,%d' % act_id_1, res_id=False)
        ir_values.set_action('OnDblClick Action 2', action_slot='tree_but_open', model='res.partner', action='ir.actions.act_window,%d' % act_id_2, res_id=False)
        ir_values.set_action('Side Wizard', action_slot='client_action_multi', model='res.partner', action='ir.actions.act_window,%d' % act_id_3, res_id=False)

        reports = self.env['ir.actions.report.xml'].search([])
        report_id = next(report.id for report in reports if not report.groups_id)
        ir_values.set_action('Nice Report', action_slot='client_print_multi', model='res.partner', action='ir.actions.report.xml,%d' % report_id, res_id=False)

        # Replace one action binding to set a new name.
        ir_values.set_action('OnDblClick Action New', action_slot='tree_but_open', model='res.partner', action='ir.actions.act_window,%d' % act_id_1, res_id=False)

        # Retrieve the action bindings and check they're correct
        actions = ir_values.get_actions(action_slot='tree_but_open', model='res.partner', res_id=False)
        self.assertEqual(len(actions), 2, "Mismatching number of bound actions")
        # first action
        self.assertEqual(len(actions[0]), 3, "Malformed action definition")
        self.assertEqual(actions[0][1], 'OnDblClick Action 2', 'Bound action does not match definition')
        self.assertTrue(isinstance(actions[0][2], dict) and actions[0][2]['id'] == act_id_2,
                        'Bound action does not match definition')
        # second action - this ones comes last because it was re-created with a different name
        self.assertEqual(len(actions[1]), 3, "Malformed action definition")
        self.assertEqual(actions[1][1], 'OnDblClick Action New', 'Re-Registering an action should replace it')
        self.assertTrue(isinstance(actions[1][2], dict) and actions[1][2]['id'] == act_id_1,
                        'Bound action does not match definition')

        actions = ir_values.get_actions(action_slot='client_action_multi', model='res.partner', res_id=False)
        self.assertEqual(len(actions), 1, "Mismatching number of bound actions")
        self.assertEqual(len(actions[0]), 3, "Malformed action definition")
        self.assertEqual(actions[0][1], 'Side Wizard', 'Bound action does not match definition')
        self.assertTrue(isinstance(actions[0][2], dict) and actions[0][2]['id'] == act_id_3,
                        'Bound action does not match definition')

        actions = ir_values.get_actions(action_slot='client_print_multi', model='res.partner', res_id=False)
        self.assertEqual(len(actions), 1, "Mismatching number of bound actions")
        self.assertEqual(len(actions[0]), 3, "Malformed action definition")
        self.assertEqual(actions[0][1], 'Nice Report', 'Bound action does not match definition')
        self.assertTrue(isinstance(actions[0][2], dict) and actions[0][2]['id'] == report_id,
                        'Bound action does not match definition')

    def test_orders(self):
        ir_values = self.env['ir.values']

        # create a global rule for all
        ir_values.set_default(
            'res.partner', 'ref', 'value_global',
            for_all_users=True, company_id=False, condition=False)
        self.assertEqual(
            ir_values.get_defaults_dict('res.partner')['ref'],
            'value_global',
            "Can't retrieve the created default value for all.")

        # set a default value for current company (behavior of 'set default' from debug mode)
        ir_values.set_default(
            'res.partner', 'ref', 'value_company',
            for_all_users=True, company_id=True, condition=False)
        self.assertEqual(
            ir_values.get_defaults_dict('res.partner')['ref'],
            'value_company',
            "Can't retrieve the created default value for company.")

        # set a default value for current user (behavior of 'set default' from debug mode)
        ir_values.set_default(
            'res.partner', 'ref', 'value_user',
            for_all_users=False, company_id=True, condition=False)
        self.assertEqual(
            ir_values.get_defaults_dict('res.partner')['ref'],
            'value_user',
            "Can't retrieve the created default value for user.")
