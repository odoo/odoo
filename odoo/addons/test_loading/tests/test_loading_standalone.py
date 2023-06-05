# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.modules.registry import Registry
from odoo.modules import get_manifest
from odoo.tools import make_index_name, table_exists
from odoo.tests import standalone

# +----------------+
# |      base      |
# +----------------+
#   ^
#   |
#   |
# +----------------+
# |  test_loading  |
# +----------------+
#   ^
#   |
#   |
# +----------------+
# | test_loading_1 | <-----+
# +----------------+       |
#   ^                      |
#   |                      |
#   |                      |
# +----------------+     +----------------+
# | test_loading_2 |     | test_loading_3 |
# +----------------+     +----------------+
#

def _check_database_registry_consistency(env, model_name):
    """ check the consistency between the database and the registry """
    # check model
    Model = env[model_name]
    Model.invalidate_model()
    model_record = env['ir.model'].search([('model', '=', model_name)], limit=1)
    assert model_record.name == Model._description

    # check fields
    Fields = env['ir.model.fields']
    Fields.invalidate_model()
    fields = Model._fields
    field_records = Fields.search([('model', '=', model_name)])
    for field_record in field_records:
        assert field_record.name in fields
        field = fields[field_record.name]
        assert field_record.field_description == field.string
        assert field_record.translate == bool(field.translate)
        assert field_record.required == field.required

    # check not null
    env.cr.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
          AND is_nullable = 'NO'
          AND column_name != 'id'
    """, (Model._table,))
    not_null_columns = {r[0] for r in env.cr.fetchall()}
    assert set(field_records.filtered('required').mapped('name')) == not_null_columns

    # check index
    # since field indexes are not removed automatically, and their definitions are not updated automatically
    # we only check indexes marked in registry exist in database
    env.cr.execute("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = %s;
    """, (Model._table,))
    index_names = {r[0] for r in env.cr.fetchall()}
    assert set(field_records.filtered('index').mapped(lambda f: make_index_name(Model._table, f.name))) < index_names

    # check sql constraints
    env.cr.execute("""
        SELECT conname
        FROM pg_constraint
        WHERE conrelid = %s::regclass
        AND contype != 'p'
    """, (Model._table,))
    constraint_names = {r[0] for r in env.cr.fetchall()}
    Constraints = env['ir.model.constraint']
    Constraints.invalidate_model()
    constraint_records = Constraints.search([('model', '=', model_name)])
    assert set(constraint_records.mapped('name')) == constraint_names
    # since overriden ir_model_constraint recordsets are kept in database, we only compare the final one
    _sql_constraints = tuple((f'{Model._table}_{c[0]}', c[1].replace(' ', '').lower(), c[2]) for c in Model._sql_constraints)
    constraint_definition = {
        c.name: c.definition
        for c in constraint_records.filtered('definition')
        if (c.name, c.definition, c.message) in _sql_constraints
    }
    assert len(constraint_definition) == len(Model._sql_constraints)
    env.cr.execute("""
        SELECT conname, pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conname IN %s
    """, (tuple(constraint_definition.keys()),))
    for name, definition in env.cr.fetchall():
        assert constraint_definition[name].replace(" ", "").lower() == definition.replace(" ", "").lower()

@standalone('loading_standalone')
def test_00_cleanup(env):
    env['ir.module.module'].search([('name', 'ilike', 'test_loading_'), ('state', '!=', 'uninstalled')]).button_immediate_uninstall()
    env.reset()  # clear the set of environments
    env = env()  # get an environment that refers to the new registry
    assert 'test_loading_1.model' not in env
    assert not table_exists(env.cr, 'test_loading_1_model')

@standalone('loading_standalone')
def test_01_install_test_loading_3(env):
    env.ref('base.module_test_loading_1').button_immediate_install()
    # test_loading_1 has been installed, check if the env of pre_init_hook for test_loading_3 is ready while installing
    env.ref('base.module_test_loading_3').button_immediate_install()

    env.reset()
    env = env()
    assert env['test_loading_1.model']._description == 'Testing Loading Model 3'
    _check_database_registry_consistency(env, 'test_loading_1.model')

    # reload the registry to check that the database is still consistent
    Registry.new(env.registry.db_name)
    env.reset()
    env = env()
    assert env['test_loading_1.model']._description == 'Testing Loading Model 3'
    _check_database_registry_consistency(env, 'test_loading_1.model')

@standalone('loading_standalone')
def test_02_install_test_loading_2(env):
    env.ref('base.module_test_loading_2').button_immediate_install()

    env.reset()
    env = env()
    assert env['test_loading_1.model']._description == 'Testing Loading Model 3'
    _check_database_registry_consistency(env, 'test_loading_1.model')

    # reload the registry to check that the database is still consistent
    Registry.new(env.registry.db_name)
    env.reset()
    env = env()
    assert env['test_loading_1.model']._description == 'Testing Loading Model 3'
    _check_database_registry_consistency(env, 'test_loading_1.model')

@standalone('loading_standalone')
def test_02_upgrade_test_loading_1(env):
    env['res.lang']._activate_lang('fr_FR')
    record_1 = env.ref('test_loading_1.test_loading_1_record_1')

    record_1.with_context(lang='fr_FR').name_y = 'ValueY 1 FR'

    env.ref('base.module_test_loading_1').button_immediate_upgrade()
    env.reset()
    env = env()
    assert env['test_loading_1.model']._description == 'Testing Loading Model 3'
    _check_database_registry_consistency(env, 'test_loading_1.model')

    # reload the registry to check that the database is still consistent
    Registry.new(env.registry.db_name)
    env.reset()
    env = env()
    assert env['test_loading_1.model']._description == 'Testing Loading Model 3'
    _check_database_registry_consistency(env, 'test_loading_1.model')

    # translations shouldn't be lost after upgrade
    assert record_1.with_context(lang='fr_FR').name_y == 'ValueY 1 FR'
    assert record_1.with_context(lang='en_US').name_y == 'ValueY 1'

@standalone('loading_standalone')
def test_03_uninstall_test_loading_3(env):
    env.ref('base.module_test_loading_3').button_immediate_uninstall()

    env.reset()
    env = env()
    assert env['test_loading_1.model']._description == 'Testing Loading Model 2'
    _check_database_registry_consistency(env, 'test_loading_1.model')

    # reload the registry to check that the database is still consistent
    Registry.new(env.registry.db_name)
    env.reset()
    env = env()
    assert env['test_loading_1.model']._description == 'Testing Loading Model 2'
    _check_database_registry_consistency(env, 'test_loading_1.model')

@standalone('loading_standalone')
def test_04_auto_install(env):
    test_00_cleanup(env)
    env.reset()
    env = env()
    manifest_test_loading_2 = get_manifest('test_loading_2')
    # hack the lru_cache value to simulate the auto_install
    manifest_test_loading_2['auto_install'] = set(manifest_test_loading_2['depends'])

    # populate the auto_install from the manifest to the database
    env['ir.module.module'].update_list()
    env.ref('base.module_test_loading_3').button_immediate_install()

    env.reset()
    env = env()
    assert env.ref('base.module_test_loading_2').state == 'installed'
    assert env['test_loading_1.model']._description == 'Testing Loading Model 3'
    _check_database_registry_consistency(env, 'test_loading_1.model')

    # reload the registry to check that the database is still consistent
    Registry.new(env.registry.db_name)
    env.reset()
    env = env()
    assert env['test_loading_1.model']._description == 'Testing Loading Model 3'
    _check_database_registry_consistency(env, 'test_loading_1.model')

    # reset the lru_cache to revert the hack
    get_manifest.cache_clear()
    env['ir.module.module'].update_list()

@standalone('loading_standalone')
def test_05_install_hook(env):
    test_00_cleanup(env)
    env.reset()
    env = env()
    get_manifest.cache_clear()
    manifest_test_loading_3 = get_manifest('test_loading_3')
    manifest_test_loading_3['post_init_hook'] = 'post_init_hook'

    env.ref('base.module_test_loading_3').button_immediate_install()

    env.reset()
    env = env()
    assert env.ref('base.module_test_loading_2').state == 'installed'
    assert env['test_loading_1.model']._description == 'Testing Loading Model 3'
    _check_database_registry_consistency(env, 'test_loading_1.model')

    # reload the registry to check that the database is still consistent
    Registry.new(env.registry.db_name)
    env.reset()
    env = env()
    assert env['test_loading_1.model']._description == 'Testing Loading Model 3'
    _check_database_registry_consistency(env, 'test_loading_1.model')

    get_manifest.cache_clear()
