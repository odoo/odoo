import unittest2

from openerp.osv.orm import except_orm
import openerp.tests.common as common
from openerp.tools import mute_logger


class TestServerActionsBase(common.TransactionCase):

    def setUp(self):
        super(TestServerActionsBase, self).setUp()
        cr, uid = self.cr, self.uid

        # Models
        self.ir_actions_server = self.registry('ir.actions.server')
        self.ir_actions_client = self.registry('ir.actions.client')
        self.ir_values = self.registry('ir.values')
        self.ir_model = self.registry('ir.model')
        self.ir_model_fields = self.registry('ir.model.fields')
        self.res_partner = self.registry('res.partner')
        self.res_country = self.registry('res.country')

        # Data on which we will run the server action
        self.test_country_id = self.res_country.create(cr, uid, {
            'name': 'TestingCountry',
            'code': 'TY',
            'address_format': 'SuperFormat',
        })
        self.test_country = self.res_country.browse(cr, uid, self.test_country_id)
        self.test_partner_id = self.res_partner.create(cr, uid, {
            'name': 'TestingPartner',
            'city': 'OrigCity',
            'country_id': self.test_country_id,
        })
        self.test_partner = self.res_partner.browse(cr, uid, self.test_partner_id)
        self.context = {
            'active_id': self.test_partner_id,
            'active_model': 'res.partner',
        }

        # Model data
        self.res_partner_model_id = self.ir_model.search(cr, uid, [('model', '=', 'res.partner')])[0]
        self.res_partner_name_field_id = self.ir_model_fields.search(cr, uid, [('model', '=', 'res.partner'), ('name', '=', 'name')])[0]
        self.res_partner_city_field_id = self.ir_model_fields.search(cr, uid, [('model', '=', 'res.partner'), ('name', '=', 'city')])[0]
        self.res_partner_country_field_id = self.ir_model_fields.search(cr, uid, [('model', '=', 'res.partner'), ('name', '=', 'country_id')])[0]
        self.res_partner_parent_field_id = self.ir_model_fields.search(cr, uid, [('model', '=', 'res.partner'), ('name', '=', 'parent_id')])[0]
        self.res_country_model_id = self.ir_model.search(cr, uid, [('model', '=', 'res.country')])[0]
        self.res_country_name_field_id = self.ir_model_fields.search(cr, uid, [('model', '=', 'res.country'), ('name', '=', 'name')])[0]
        self.res_country_code_field_id = self.ir_model_fields.search(cr, uid, [('model', '=', 'res.country'), ('name', '=', 'code')])[0]

        # create server action to
        self.act_id = self.ir_actions_server.create(cr, uid, {
            'name': 'TestAction',
            'condition': 'True',
            'model_id': self.res_partner_model_id,
            'state': 'code',
            'code': 'obj.write({"comment": "MyComment"})',
        })


class TestServerActions(TestServerActionsBase):

    def test_00_action(self):
        cr, uid = self.cr, self.uid

        # Do: eval 'True' condition
        self.ir_actions_server.run(cr, uid, [self.act_id], self.context)
        self.test_partner.refresh()
        self.assertEqual(self.test_partner.comment, 'MyComment', 'ir_actions_server: invalid condition check')
        self.test_partner.write({'comment': False})

        # Do: eval False condition, that should be considered as True (void = True)
        self.ir_actions_server.write(cr, uid, [self.act_id], {'condition': False})
        self.ir_actions_server.run(cr, uid, [self.act_id], self.context)
        self.test_partner.refresh()
        self.assertEqual(self.test_partner.comment, 'MyComment', 'ir_actions_server: invalid condition check')

        # Do: create contextual action
        self.ir_actions_server.create_action(cr, uid, [self.act_id])

        # Test: ir_values created
        ir_values_ids = self.ir_values.search(cr, uid, [('name', '=', 'Run TestAction')])
        self.assertEqual(len(ir_values_ids), 1, 'ir_actions_server: create_action should have created an entry in ir_values')
        ir_value = self.ir_values.browse(cr, uid, ir_values_ids[0])
        self.assertEqual(ir_value.value, 'ir.actions.server,%s' % self.act_id, 'ir_actions_server: created ir_values should reference the server action')
        self.assertEqual(ir_value.model, 'res.partner', 'ir_actions_server: created ir_values should be linked to the action base model')

        # Do: remove contextual action
        self.ir_actions_server.unlink_action(cr, uid, [self.act_id])

        # Test: ir_values removed
        ir_values_ids = self.ir_values.search(cr, uid, [('name', '=', 'Run TestAction')])
        self.assertEqual(len(ir_values_ids), 0, 'ir_actions_server: unlink_action should remove the ir_values record')

    def test_10_code(self):
        cr, uid = self.cr, self.uid
        self.ir_actions_server.write(cr, uid, self.act_id, {
            'state': 'code',
            'code': """partner_name = obj.name + '_code'
self.pool["res.partner"].create(cr, uid, {"name": partner_name}, context=context)
workflow"""
        })
        run_res = self.ir_actions_server.run(cr, uid, [self.act_id], context=self.context)
        self.assertFalse(run_res, 'ir_actions_server: code server action correctly finished should return False')

        pids = self.res_partner.search(cr, uid, [('name', 'ilike', 'TestingPartner_code')])
        self.assertEqual(len(pids), 1, 'ir_actions_server: 1 new partner should have been created')

    def test_20_trigger(self):
        cr, uid = self.cr, self.uid

        # Data: code server action (at this point code-based actions should work)
        act_id2 = self.ir_actions_server.create(cr, uid, {
            'name': 'TestAction2',
            'type': 'ir.actions.server',
            'condition': 'True',
            'model_id': self.res_partner_model_id,
            'state': 'code',
            'code': 'obj.write({"comment": "MyComment"})',
        })
        act_id3 = self.ir_actions_server.create(cr, uid, {
            'name': 'TestAction3',
            'type': 'ir.actions.server',
            'condition': 'True',
            'model_id': self.res_country_model_id,
            'state': 'code',
            'code': 'obj.write({"code": "ZZ"})',
        })

        # Data: create workflows
        partner_wf_id = self.registry('workflow').create(cr, uid, {
            'name': 'TestWorkflow',
            'osv': 'res.partner',
            'on_create': True,
        })
        partner_act1_id = self.registry('workflow.activity').create(cr, uid, {
            'name': 'PartnerStart',
            'wkf_id': partner_wf_id,
            'flow_start': True
        })
        partner_act2_id = self.registry('workflow.activity').create(cr, uid, {
            'name': 'PartnerTwo',
            'wkf_id': partner_wf_id,
            'kind': 'function',
            'action': 'True',
            'action_id': act_id2,
        })
        partner_trs1_id = self.registry('workflow.transition').create(cr, uid, {
            'signal': 'partner_trans',
            'act_from': partner_act1_id,
            'act_to': partner_act2_id
        })
        country_wf_id = self.registry('workflow').create(cr, uid, {
            'name': 'TestWorkflow',
            'osv': 'res.country',
            'on_create': True,
        })
        country_act1_id = self.registry('workflow.activity').create(cr, uid, {
            'name': 'CountryStart',
            'wkf_id': country_wf_id,
            'flow_start': True
        })
        country_act2_id = self.registry('workflow.activity').create(cr, uid, {
            'name': 'CountryTwo',
            'wkf_id': country_wf_id,
            'kind': 'function',
            'action': 'True',
            'action_id': act_id3,
        })
        country_trs1_id = self.registry('workflow.transition').create(cr, uid, {
            'signal': 'country_trans',
            'act_from': country_act1_id,
            'act_to': country_act2_id
        })

        # Data: re-create country and partner to benefit from the workflows
        self.test_country_id = self.res_country.create(cr, uid, {
            'name': 'TestingCountry2',
            'code': 'T2',
        })
        self.test_country = self.res_country.browse(cr, uid, self.test_country_id)
        self.test_partner_id = self.res_partner.create(cr, uid, {
            'name': 'TestingPartner2',
            'country_id': self.test_country_id,
        })
        self.test_partner = self.res_partner.browse(cr, uid, self.test_partner_id)
        self.context = {
            'active_id': self.test_partner_id,
            'active_model': 'res.partner',
        }

        # Run the action on partner object itself ('base')
        self.ir_actions_server.write(cr, uid, [self.act_id], {
            'state': 'trigger',
            'use_relational_model': 'base',
            'wkf_model_id': self.res_partner_model_id,
            'wkf_model_name': 'res.partner',
            'wkf_transition_id': partner_trs1_id,
        })
        self.ir_actions_server.run(cr, uid, [self.act_id], self.context)
        self.test_partner.refresh()
        self.assertEqual(self.test_partner.comment, 'MyComment', 'ir_actions_server: incorrect signal trigger')

        # Run the action on related country object ('relational')
        self.ir_actions_server.write(cr, uid, [self.act_id], {
            'use_relational_model': 'relational',
            'wkf_model_id': self.res_country_model_id,
            'wkf_model_name': 'res.country',
            'wkf_field_id': self.res_partner_country_field_id,
            'wkf_transition_id': country_trs1_id,
        })
        self.ir_actions_server.run(cr, uid, [self.act_id], self.context)
        self.test_country.refresh()
        self.assertEqual(self.test_country.code, 'ZZ', 'ir_actions_server: incorrect signal trigger')

        # Clear workflow cache, otherwise openerp will try to create workflows even if it has been deleted
        from openerp.workflow import clear_cache
        clear_cache(cr, uid)

    def test_30_client(self):
        cr, uid = self.cr, self.uid
        client_action_id = self.registry('ir.actions.client').create(cr, uid, {
            'name': 'TestAction2',
            'tag': 'Test',
        })
        self.ir_actions_server.write(cr, uid, [self.act_id], {
            'state': 'client_action',
            'action_id': client_action_id,
        })
        res = self.ir_actions_server.run(cr, uid, [self.act_id], context=self.context)
        self.assertEqual(res['name'], 'TestAction2', 'ir_actions_server: incorrect return result for a client action')

    def test_40_crud_create(self):
        cr, uid = self.cr, self.uid
        _city = 'TestCity'
        _name = 'TestNew'

        # Do: create a new record in the same model and link it
        self.ir_actions_server.write(cr, uid, [self.act_id], {
            'state': 'object_create',
            'use_create': 'new',
            'link_new_record': True,
            'link_field_id': self.res_partner_parent_field_id,
            'fields_lines': [(0, 0, {'col1': self.res_partner_name_field_id, 'value': _name}),
                             (0, 0, {'col1': self.res_partner_city_field_id, 'value': _city})],
        })
        run_res = self.ir_actions_server.run(cr, uid, [self.act_id], context=self.context)
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new partner created
        pids = self.res_partner.search(cr, uid, [('name', 'ilike', _name)])
        self.assertEqual(len(pids), 1, 'ir_actions_server: TODO')
        partner = self.res_partner.browse(cr, uid, pids[0])
        self.assertEqual(partner.city, _city, 'ir_actions_server: TODO')
        # Test: new partner linked
        self.test_partner.refresh()
        self.assertEqual(self.test_partner.parent_id.id, pids[0], 'ir_actions_server: TODO')

        # Do: copy current record
        self.ir_actions_server.write(cr, uid, [self.act_id], {'fields_lines': [[5]]})
        self.ir_actions_server.write(cr, uid, [self.act_id], {
            'state': 'object_create',
            'use_create': 'copy_current',
            'link_new_record': False,
            'fields_lines': [(0, 0, {'col1': self.res_partner_name_field_id, 'value': 'TestCopyCurrent'}),
                             (0, 0, {'col1': self.res_partner_city_field_id, 'value': 'TestCity'})],
        })
        run_res = self.ir_actions_server.run(cr, uid, [self.act_id], context=self.context)
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new partner created
        pids = self.res_partner.search(cr, uid, [('name', 'ilike', 'TestingPartner (copy)')])  # currently res_partner overrides default['name'] whatever its value
        self.assertEqual(len(pids), 1, 'ir_actions_server: TODO')
        partner = self.res_partner.browse(cr, uid, pids[0])
        self.assertEqual(partner.city, 'TestCity', 'ir_actions_server: TODO')
        self.assertEqual(partner.country_id.id, self.test_partner.country_id.id, 'ir_actions_server: TODO')

        # Do: create a new record in another model
        self.ir_actions_server.write(cr, uid, [self.act_id], {'fields_lines': [[5]]})
        self.ir_actions_server.write(cr, uid, [self.act_id], {
            'state': 'object_create',
            'use_create': 'new_other',
            'crud_model_id': self.res_country_model_id,
            'link_new_record': False,
            'fields_lines': [(0, 0, {'col1': self.res_country_name_field_id, 'value': 'obj.name', 'type': 'equation'}),
                             (0, 0, {'col1': self.res_country_code_field_id, 'value': 'obj.name[0:2]', 'type': 'equation'})],
        })
        run_res = self.ir_actions_server.run(cr, uid, [self.act_id], context=self.context)
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new country created
        cids = self.res_country.search(cr, uid, [('name', 'ilike', 'TestingPartner')])
        self.assertEqual(len(cids), 1, 'ir_actions_server: TODO')
        country = self.res_country.browse(cr, uid, cids[0])
        self.assertEqual(country.code, 'TE', 'ir_actions_server: TODO')

        # Do: copy a record in another model
        self.ir_actions_server.write(cr, uid, [self.act_id], {'fields_lines': [[5]]})
        self.ir_actions_server.write(cr, uid, [self.act_id], {
            'state': 'object_create',
            'use_create': 'copy_other',
            'crud_model_id': self.res_country_model_id,
            'link_new_record': False,
            'ref_object': 'res.country,%s' % self.test_country_id,
            'fields_lines': [(0, 0, {'col1': self.res_country_name_field_id, 'value': 'NewCountry', 'type': 'value'}),
                             (0, 0, {'col1': self.res_country_code_field_id, 'value': 'NY', 'type': 'value'})],
        })
        run_res = self.ir_actions_server.run(cr, uid, [self.act_id], context=self.context)
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new country created
        cids = self.res_country.search(cr, uid, [('name', 'ilike', 'NewCountry')])
        self.assertEqual(len(cids), 1, 'ir_actions_server: TODO')
        country = self.res_country.browse(cr, uid, cids[0])
        self.assertEqual(country.code, 'NY', 'ir_actions_server: TODO')
        self.assertEqual(country.address_format, 'SuperFormat', 'ir_actions_server: TODO')

    def test_50_crud_write(self):
        cr, uid = self.cr, self.uid
        _name = 'TestNew'

        # Do: create a new record in the same model and link it
        self.ir_actions_server.write(cr, uid, [self.act_id], {
            'state': 'object_write',
            'use_write': 'current',
            'fields_lines': [(0, 0, {'col1': self.res_partner_name_field_id, 'value': _name})],
        })
        run_res = self.ir_actions_server.run(cr, uid, [self.act_id], context=self.context)
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new partner created
        pids = self.res_partner.search(cr, uid, [('name', 'ilike', _name)])
        self.assertEqual(len(pids), 1, 'ir_actions_server: TODO')
        partner = self.res_partner.browse(cr, uid, pids[0])
        self.assertEqual(partner.city, 'OrigCity', 'ir_actions_server: TODO')

        # Do: copy current record
        self.ir_actions_server.write(cr, uid, [self.act_id], {'fields_lines': [[5]]})
        self.ir_actions_server.write(cr, uid, [self.act_id], {
            'use_write': 'other',
            'crud_model_id': self.res_country_model_id,
            'ref_object': 'res.country,%s' % self.test_country_id,
            'fields_lines': [(0, 0, {'col1': self.res_country_name_field_id, 'value': 'obj.name', 'type': 'equation'})],
        })
        run_res = self.ir_actions_server.run(cr, uid, [self.act_id], context=self.context)
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new country created
        cids = self.res_country.search(cr, uid, [('name', 'ilike', 'TestNew')])
        self.assertEqual(len(cids), 1, 'ir_actions_server: TODO')

        # Do: copy a record in another model
        self.ir_actions_server.write(cr, uid, [self.act_id], {'fields_lines': [[5]]})
        self.ir_actions_server.write(cr, uid, [self.act_id], {
            'use_write': 'expression',
            'crud_model_id': self.res_country_model_id,
            'write_expression': 'object.country_id',
            'fields_lines': [(0, 0, {'col1': self.res_country_name_field_id, 'value': 'NewCountry', 'type': 'value'})],
        })
        run_res = self.ir_actions_server.run(cr, uid, [self.act_id], context=self.context)
        self.assertFalse(run_res, 'ir_actions_server: create record action correctly finished should return False')
        # Test: new country created
        cids = self.res_country.search(cr, uid, [('name', 'ilike', 'NewCountry')])
        self.assertEqual(len(cids), 1, 'ir_actions_server: TODO')

    @mute_logger('openerp.addons.base.ir.ir_model', 'openerp.models')
    def test_60_multi(self):
        cr, uid = self.cr, self.uid

        # Data: 2 server actions that will be nested
        act1_id = self.ir_actions_server.create(cr, uid, {
            'name': 'Subaction1',
            'sequence': 1,
            'model_id': self.res_partner_model_id,
            'state': 'code',
            'code': 'action = {"type": "ir.actions.act_window"}',
        })
        act2_id = self.ir_actions_server.create(cr, uid, {
            'name': 'Subaction2',
            'sequence': 2,
            'model_id': self.res_partner_model_id,
            'state': 'object_create',
            'use_create': 'copy_current',
        })
        act3_id = self.ir_actions_server.create(cr, uid, {
            'name': 'Subaction3',
            'sequence': 3,
            'model_id': self.res_partner_model_id,
            'state': 'code',
            'code': 'action = {"type": "ir.actions.act_url"}',
        })
        self.ir_actions_server.write(cr, uid, [self.act_id], {
            'state': 'multi',
            'child_ids': [(6, 0, [act1_id, act2_id, act3_id])],
        })

        # Do: run the action
        res = self.ir_actions_server.run(cr, uid, [self.act_id], context=self.context)

        # Test: new partner created
        pids = self.res_partner.search(cr, uid, [('name', 'ilike', 'TestingPartner (copy)')])  # currently res_partner overrides default['name'] whatever its value
        self.assertEqual(len(pids), 1, 'ir_actions_server: TODO')
        # Test: action returned
        self.assertEqual(res.get('type'), 'ir.actions.act_url')

        # Test loops
        with self.assertRaises(except_orm):
            self.ir_actions_server.write(cr, uid, [self.act_id], {
                'child_ids': [(6, 0, [self.act_id])]
            })


if __name__ == '__main__':
    unittest2.main()
