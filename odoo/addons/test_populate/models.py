# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

from odoo.tools import populate, pycompat


class TestPopulateModel(models.Model):
    _name = 'test.populate'
    _description = 'Test Populate'

    name = fields.Char(default='Foo')
    state = fields.Selection([('a', 'A'), ('b', 'B')], default='a')
    active = fields.Boolean('Active', default=True)
    category_id = fields.Many2one('test.populate.category', 'Category')
    some_ref = fields.Integer('Reference')
    dependant_field_1 = fields.Char('Dependant 1')
    dependant_field_2 = fields.Char('Dependant 2')
    sequence = fields.Integer("Sequence")

    _populate_dependencies = ['test.populate.category']

    _populate_sizes = {
        'small': 20,
        'medium': 30,
        'large': 100,
    }

    def _populate_factories(self):

        # cross dependant field in a sub generator, cartesian product of two fields
        dependant_factories = [
            ('dependant_field_1', populate.cartesian(['d1_1', 'd1_2'])),
            ('dependant_field_2', populate.cartesian(['d2_1', 'd2_2', 'd2_3_{counter}'])),
        ]
        def generate_dependant(iterator, *args):
            dependants_generator = populate.chain_factories(dependant_factories, self._name)
            for values in dependants_generator:
                dependant_values = next(iterator)
                yield {**values, **dependant_values, '__complete': values['__complete'] and dependant_values['__complete']}

        def get_name(values=None, counter=0, **kwargs):
            active = 'active' if values['active'] else 'inactive'
            cat = 'filling' if values['__complete'] else 'corner'
            return '%s_%s_%s' % (active, cat, counter)

        category_ids = self.env.registry.populated_models['test.populate.category']

        return [
            ('active', populate.cartesian([True, False], [3, 1])),
            ('state', populate.cartesian([False] + self.env['test.populate']._fields['state'].get_values(self.env))),
            ('some_ref', populate.iterate([False, 1, 2, 3, 4])),
            ('_dependant', generate_dependant),
            ('name', populate.compute(get_name)),
            ('category_id', populate.randomize([False] + category_ids)),
            ('sequence', populate.randint(1, 10))
        ]

class TestPopulateDependencyModel(models.Model):
    _name = 'test.populate.category'
    _description = 'Test Populate Category'

    _populate_sizes = {
        'small': 3,
        'medium': 10,
        'large': 20,
    }
    name = fields.Char('Name', required=True, default='Cat1')
    active = fields.Boolean('Active', default=True)

    def _populate_factories(self):
        return [
            ('active', populate.cartesian([True, False], [9, 1])),
            ('name', populate.cartesian(['Cat1', 'Cat2', 'Cat3'])),
        ]

class TestNoPopulateModelInherit(models.Model):
    _name = 'test.populate.inherit'
    _inherit = 'test.populate'

    _description = 'Test populate inherit'

    additionnal_field = fields.Char(required=True)

    def _populate_factories(self):
        return super()._populate_factories() + [
            ('additionnal_field', populate.iterate(['V1', 'V2', 'V3'])),
        ]


class TestNoPopulateModel(models.Model):
    _name = 'test.no.populate'
    _description = 'A model with no populate method and a required field, should not crash'

    name = fields.Char(required=True)
