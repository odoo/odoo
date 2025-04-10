# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import standalone
from odoo.tools import sql


@standalone('inherit_uninstall')
def test_inherited_fields_after_uninstall(env):
    """
    =================================
    module: test_inherit

    class TestInheritAnimal
        _name = 'test.inherit.animal'

    =================================
    module: test_inherit_depends
    depends: test_inherit

    class TestInheritAnimal(models.Model):
        _inherit = ['test.inherit.animal']

        name = fields.Char(default='Animal')
        height = fields.Integer()

    =================================
    module: test_inherit_inherits_depends
    depends: test_inherit

    class TestInheritBird(models.Model):
        _name = 'test.inherit.bird'
        _inherit = ['test.inherit.animal']

        name = fields.Char(default='Bird')


    class TestInheritOwl(models.Model):
        _name = 'test.inherit.owl'
        _inherit = ['test.inherit.bird]


    class TestInheritPet(models.Model):
        _name = 'test.inherit.pet'
        _inherits = {'animal_id': 'test.inherit.animal'}

        name = fields.Char(default='Pet')
        animal_id = fields.Many2one('test.inherit.animal')

    """

    def test_fields(expected, ignore=None):
        ignore = ignore or {}
        for (model_name, field_name), exist in expected.items():
            table_name = model_name.replace('.', '_')

            if 'registry' not in ignore.get((model_name, field_name), ()):
                assert (model_name in env and field_name in env[model_name]._fields) == exist

            if 'column' not in ignore.get((model_name, field_name), ()):
                assert bool(sql.column_exists(env.cr, table_name, field_name)) == exist

            if 'ir.model.fields' not in ignore.get((model_name, field_name), ()):
                assert bool(env['ir.model.fields'].search([('model', '=', model_name), ('name', '=', field_name)])) == exist

            if 'ir.model.data' not in ignore.get((model_name, field_name), ()):
                assert bool(env['ir.model.data'].search([('name', '=', f"field_{table_name}__{field_name}")])) == exist

    module_test_inherit_depends, module_test_inherit_inherits_depends = env['ir.module.module'].sudo().search([('name', 'in', ('test_inherit_depends', 'test_inherit_inherits_depends'))], order='name')

    # {('field_name', 'field_name'): if_field_should_exist
    initial_expected = {
        ('test.inherit.animal', 'name'): False,
        ('test.inherit.animal', 'height'): False,
        ('test.inherit.bird', 'name'): False,
        ('test.inherit.bird', 'height'): False,
        ('test.inherit.owl', 'name'): False,
        ('test.inherit.owl', 'height'): False,
        ('test.inherit.pet', 'name'): False,
        ('test.inherit.pet', 'height'): False,
    }

    test_fields(initial_expected)
    module_test_inherit_depends.button_immediate_install()
    module_test_inherit_inherits_depends.button_immediate_install()
    module_test_inherit_depends.button_immediate_uninstall()
    test_fields({
        ('test.inherit.animal', 'name'): False,
        ('test.inherit.animal', 'height'): False,
        ('test.inherit.bird', 'name'): True,
        ('test.inherit.bird', 'height'): False,
        ('test.inherit.owl', 'name'): True,
        ('test.inherit.owl', 'height'): False,
        ('test.inherit.pet', 'name'): True,
        ('test.inherit.pet', 'height'): False,
    })
    module_test_inherit_inherits_depends.button_immediate_uninstall()

    test_fields(initial_expected)

    module_test_inherit_inherits_depends.button_immediate_install()
    module_test_inherit_depends.button_immediate_install()
    module_test_inherit_depends.button_immediate_uninstall()
    test_fields({
        ('test.inherit.animal', 'name'): False,
        ('test.inherit.animal', 'height'): False,
        ('test.inherit.bird', 'name'): True,
        ('test.inherit.bird', 'height'): False,
        ('test.inherit.owl', 'name'): True,
        ('test.inherit.owl', 'height'): False,
        ('test.inherit.pet', 'name'): True,
        ('test.inherit.pet', 'height'): False,
    })
    module_test_inherit_inherits_depends.button_immediate_uninstall()

    test_fields(initial_expected)

    module_test_inherit_depends.button_immediate_install()
    module_test_inherit_inherits_depends.button_immediate_install()
    module_test_inherit_inherits_depends.button_immediate_uninstall()
    test_fields({
        ('test.inherit.animal', 'name'): True,
        ('test.inherit.animal', 'height'): True,
        ('test.inherit.bird', 'name'): False,
        ('test.inherit.bird', 'height'): False,
        ('test.inherit.owl', 'name'): False,
        ('test.inherit.owl', 'height'): False,
        ('test.inherit.pet', 'name'): False,
        ('test.inherit.pet', 'height'): False,
    })
    module_test_inherit_depends.button_immediate_uninstall()

    test_fields(initial_expected)

    module_test_inherit_inherits_depends.button_immediate_install()
    module_test_inherit_depends.button_immediate_install()
    module_test_inherit_inherits_depends.button_immediate_uninstall()
    test_fields({
        ('test.inherit.animal', 'name'): True,
        ('test.inherit.animal', 'height'): True,
        ('test.inherit.bird', 'name'): False,
        ('test.inherit.bird', 'height'): False,
        ('test.inherit.owl', 'name'): False,
        ('test.inherit.owl', 'height'): False,
        ('test.inherit.pet', 'name'): False,
        ('test.inherit.pet', 'height'): False,
    })
    module_test_inherit_depends.button_immediate_uninstall()

    test_fields(initial_expected)
    module_test_inherit_depends.button_immediate_install()
    module_test_inherit_inherits_depends.button_immediate_install()
    # special case when upgrade a third party module cannot be loaded while uninstalling
    # assume the third party module also extends test.inherit.animal.height
    env['ir.module.module'].create({'name': 'third_party_module', 'state': 'to upgrade'})
    # assume the third party module was installed before the test_inherit_inherits_depends module
    # so all fields created by model inheritance and delegation belongs to module test_inherit_inherits_depends
    env['ir.model.data'].create({
        'model': 'ir.model.fields',
        'res_id': env['ir.model.fields'].search([('model', '=', 'test.inherit.animal'), ('name', '=', 'height')]).id,
        'name': "field_test_inherit_animal__height",
        'module': 'third_party_module',
    })
    module_test_inherit_depends.button_immediate_uninstall()
    test_fields({
        ('test.inherit.animal', 'name'): False,
        ('test.inherit.animal', 'height'): True,
        ('test.inherit.bird', 'name'): True,
        ('test.inherit.bird', 'height'): True,
        ('test.inherit.owl', 'name'): True,
        ('test.inherit.owl', 'height'): True,
        ('test.inherit.pet', 'name'): True,
        ('test.inherit.pet', 'height'): True,
    }, ignore={
        ('test.inherit.animal', 'height'): ('registry',),
        ('test.inherit.bird', 'height'): ('registry',),
        ('test.inherit.owl', 'height'): ('registry',),
        ('test.inherit.pet', 'height'): ('registry', 'column'),  # ignore column is not ideal but acceptable
    })
    module_test_inherit_inherits_depends.button_immediate_uninstall()

    module_test_inherit_depends.button_immediate_install()
    module_test_inherit_inherits_depends.button_immediate_install()
    # assume the third party module is installed after the test_inherit_inherits_depends module
    # so all fields created by model inheritance and delegation belongs to module third_party_module
    height_fields = env['ir.model.fields'].search([('model', 'in', ('test.inherit.bird', 'test.inherit.owl', 'test.inherit.pet')), ('name', '=', 'height')])
    env['ir.model.data'].search([('model', '=', 'ir.model.fields'), ('res_id', 'in', height_fields.ids)]).module = 'third_party_module'
    module_test_inherit_depends.button_immediate_uninstall()
    test_fields({
        ('test.inherit.animal', 'name'): False,
        ('test.inherit.animal', 'height'): True,
        ('test.inherit.bird', 'name'): True,
        ('test.inherit.bird', 'height'): True,
        ('test.inherit.owl', 'name'): True,
        ('test.inherit.owl', 'height'): True,
        ('test.inherit.pet', 'name'): True,
        ('test.inherit.pet', 'height'): True,
    }, ignore={
        ('test.inherit.animal', 'height'): ('registry',),
        ('test.inherit.bird', 'height'): ('registry',),
        ('test.inherit.owl', 'height'): ('registry',),
        ('test.inherit.pet', 'height'): ('registry', 'column'),  # ignore column is not ideal but acceptable
    })
