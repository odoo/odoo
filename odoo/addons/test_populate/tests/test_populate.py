# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import collections
import logging
from odoo.tests import common
from odoo.cli.populate import Populate
from odoo.tools import mute_logger, populate
from unittest.mock import patch


_logger = logging.getLogger(__name__)

# todo patch cursor commit
class TestPopulate(common.TransactionCase):
    def setUp(self):
        super(TestPopulate, self).setUp()
        patcher = patch.object(self.cr, 'commit')
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_dependency(self):
        ordered_models = Populate._get_ordered_models(self.env, ['test.populate'])
        ordered_models_names = [model._name for model in ordered_models]
        self.assertEqual(ordered_models_names, ['test.populate.category', 'test.populate'])

    @mute_logger('odoo.cli.populate')
    def test_no_populate(self):
        """ Check that model with no populate method are not populated"""
        model = 'test.no.populate'
        populated = Populate.populate(self.env, 'small', [model])
        new = populated[model]
        self.assertFalse(new)

    @mute_logger('odoo.cli.populate')
    def test_populate(self):
        """ Check that model with populate methods are correctly populated"""
        model = 'test.populate'
        populated = Populate.populate(self.env, 'small', [model])
        records = self.check_test_populate_values(populated, model)

        # pseudo random after cartesian with ~ 1/4 False, 3/4 True
        # seed is model dependant
        self.assertEqual(records.mapped('active')[6:20], [
            True, True, True, True, True, True, False, False, True, True, True, True, False, True
        ])
        # pseudo random after iterate
        self.assertEqual(records.mapped('some_ref')[5:20], [
            1, 0, 2, 4, 4, 3, 4, 1, 2, 2, 2, 4, 4, 1, 2
        ])
        self.assertEqual(records.mapped('sequence')[:20], [6, 10, 1, 1, 1, 3, 8, 9, 1, 5, 9, 5, 7, 3, 5, 3, 6, 4, 9, 2])  # Test randint

    @mute_logger('odoo.cli.populate')
    def test_populate_inherit(self):
        """ Check that model with populate methods are correctly populated"""
        model = 'test.populate.inherit'
        populated = Populate.populate(self.env, 'small', [model])
        records = self.check_test_populate_values(populated, model)  # should be same values as base class
        # and additionnal_field has own values set
        # iterate then pseudo random
        self.assertEqual(records.mapped('additionnal_field')[:20], [
            'V1', 'V2', 'V3',  # iterate
            'V3', 'V1', 'V2', 'V1', 'V2', 'V1', 'V2', 'V2', 'V2', 'V1', 'V1', 'V3', 'V1', 'V2', 'V2', 'V3', 'V2'  # pseudorandom
        ])

    def check_test_populate_values(self, populated, model):
        new = populated[model]
        self.assertTrue(new)
        records = self.env[model].browse(new)
            # main cartesian product
        self.assertEqual(records.mapped('active')[:6], [
            True, True, True,
            False, False, False,
        ])
        self.assertEqual(records.mapped('state')[:6], [
            False, 'a', 'b',
            False, 'a', 'b',
        ])

        # custom name call
        self.assertEqual(records.mapped('name')[:6], [
            'active_corner_0', 'active_corner_1', 'active_corner_2',
            'inactive_corner_3', 'inactive_corner_4', 'inactive_corner_5',
        ])
        self.assertIn('filling', records.mapped('name')[6]) # filling when cartesian and iterate are done
        # iterate then pseudo random
        self.assertEqual(records.mapped('some_ref')[:5], [
            0, 1, 2, 3, 4 # iterate
        ])

        # some custom multi field generator (as cartesian product in this example)
        self.assertEqual(records.mapped('dependant_field_1')[:6], [
            'd1_1', 'd1_1', 'd1_1',
            'd1_2', 'd1_2', 'd1_2'
        ])
        self.assertEqual(records.mapped('dependant_field_2')[:6], [
            'd2_1', 'd2_2', 'd2_3_0',
            'd2_1', 'd2_2', 'd2_3_1'
        ])
        used_category_ids = set(records.mapped('category_id').ids[:20])
        self.assertEqual(len(used_category_ids), 6) # event if id may change, with given seed, the 6 category are used
        generated_category_ids = set(populated['test.populate.category'])
        self.assertFalse(used_category_ids-generated_category_ids) # all category are the generated one
        self.assertFalse(hasattr(self.env.registry, 'populated_models'), 'populated_models flag has been removed from registry')

        return records


@common.tagged('-at_install', 'post_install')
class TestPopulateValidation(common.TransactionCase):
    """ check that all fields in _populate_factories exists """
    def setUp(self):
        super(TestPopulateValidation, self).setUp()
        self.env.registry.populated_models = collections.defaultdict(list)
        self.addCleanup(delattr, self.env.registry, 'populated_models')

    def test_populate_factories(self):
        for model in self.env.values():
            factories = model._populate_factories() or []
            factories_fields = set([field_name for field_name, factory in factories if not field_name.startswith('_')])
            missing = factories_fields - model._fields.keys()
            self.assertFalse(missing, 'Fields %s not found in model %s' % (missing, model._name))


@common.tagged('-standard', '-at_install', 'post_install', 'missing_populate')
class TestPopulateMissing(common.TransactionCase):
    """ check that all fields in _populate_factories exists """
    def setUp(self):
        super(TestPopulateMissing, self).setUp()
        self.env.registry.populated_models = collections.defaultdict(list)
        self.addCleanup(delattr, self.env.registry, 'populated_models')

    def test_populate_missing_factories(self):
        no_factory_models = []
        for model in self.env.values():
            factories = model._populate_factories()
            if not factories:
                if model._transient or model._abstract:
                    continue
                ir_model = self.env['ir.model'].search([('model', '=', model._name)])
                if all(module.startswith('test_') for module in ir_model.modules.split(',')):
                    continue
                no_factory_models.append(model._name)
            else:
                factories_fields = next(populate.chain_factories(factories, model._name)).keys()
                def is_electable(field):
                    return not field.compute \
                        and field.store \
                        and field.name not in ('create_uid', 'write_uid', 'write_date', 'create_date', 'id') \
                        and field.type not in ('many2many', 'one2many')
                electable_fields = set([key for key, field in model._fields.items() if is_electable(field)])
                no_factory_fields = set(electable_fields - factories_fields)
                if no_factory_fields:
                    _logger.info('Model %s has some undefined field: %s', model._name, no_factory_fields)

        _logger.info('No populate factories defiend for %s', no_factory_models)
