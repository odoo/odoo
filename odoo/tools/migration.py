# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import imp
import json
import logging
import lxml
import os
import re
import sys
import time

from collections import namedtuple
from contextlib import contextmanager
from docutils.core import publish_string
from inspect import currentframe
from itertools import chain, islice
from functools import reduce
from operator import itemgetter
from textwrap import dedent

import markdown
import psycopg2

import odoo
from odoo import release, SUPERUSER_ID
from odoo.addons.base.models.ir_module import MyWriter
from odoo.modules.module import get_module_path
from odoo.modules.registry import Registry
from odoo.sql_db import db_connect
from odoo.tools.func import frame_codeinfo
from odoo.tools.mail import html_sanitize
from odoo.tools import UnquoteEvalContext
from odoo.tools.parse_version import parse_version

from odoo.api import Environment

_logger = logging.getLogger(__name__)

_INSTALLED_MODULE_STATES = ('installed', 'to install', 'to upgrade')
IMD_FIELD_PATTERN = 'field_%s__%s'

DROP_DEPRECATED_CUSTOM = os.getenv('OE_DROP_DEPRECATED_CUSTOM')

# migration environ, used to share data between scripts
ENVIRON = {}


class MigrationError(Exception):
    pass

# Modules utilities


def modules_installed(cr, *modules):
    """Check if the provided modules are installed (or about to be)."""
    assert modules
    cr.execute("""SELECT count(1)
                    FROM ir_module_module
                   WHERE name IN %s
                     AND state IN %s
               """, [modules, _INSTALLED_MODULE_STATES])
    return cr.fetchone()[0] == len(modules)


def module_installed(cr, module):
    """Check if the provided module is installed (or about to be)."""
    return modules_installed(cr, module)


def remove_module(cr, module):
    """Uninstall the module and delete all its xmlid entries.

    Make sure to reassign records before calling this method.
    """
    # NOTE: we cannot use the uninstall of module because the given
    # module need to be currenctly installed and running as deletions
    # are made using orm.

    cr.execute("SELECT id FROM ir_module_module WHERE name=%s", (module,))
    mod_id, = cr.fetchone() or [None]
    if not mod_id:
        return

    # delete constraints only owned by this module
    cr.execute("""SELECT name
                    FROM ir_model_constraint
                GROUP BY name
                  HAVING array_agg(module) = %s""", ([mod_id],))

    constraints = tuple(vals[0] for vals in cr.fetchall())
    if constraints:
        cr.execute("""SELECT table_name, constraint_name
                        FROM information_schema.table_constraints
                       WHERE constraint_name IN %s""", (constraints,))
        for table, constraint in cr.fetchall():
            cr.execute('ALTER TABLE "{0}" DROP CONSTRAINT "{1}"'
                       .format(table, constraint))

    cr.execute("""DELETE FROM ir_model_constraint
                        WHERE module=%s
               """, (mod_id,))

    # delete data
    model_ids, field_ids, view_ids, menu_ids = (), (), (), ()
    cr.execute("""SELECT model, array_agg(res_id)
                    FROM ir_model_data d
                   WHERE NOT EXISTS (SELECT 1
                                       FROM ir_model_data
                                      WHERE id != d.id
                                        AND res_id = d.res_id
                                        AND model = d.model
                                        AND module != d.module)
                     AND module={}
                     AND model != 'ir.module.module'
                GROUP BY model
               """.format(module))
    for model, res_ids in cr.fetchall():
        if model == 'ir.model':
            model_ids = tuple(res_ids)
        elif model == 'ir.model.fields':
            field_ids = tuple(res_ids)
        elif model == 'ir.ui.view':
            view_ids = tuple(res_ids)
        elif model == 'ir.ui.menu':
            menu_ids = tuple(res_ids)
        else:
            table = table_of_model(cr, model)
            if table_exists(cr, table):
                cr.execute('DELETE FROM "{0}" WHERE id IN {1}s'
                           .format(table, [tuple(res_ids)]))

    for view_id in view_ids:
        remove_view(cr, view_id=view_id, deactivate_custom=True, silent=True)

    if menu_ids:
        remove_menus(cr, menu_ids)

    # remove relations
    cr.execute("""SELECT name
                    FROM ir_model_relation
                GROUP BY name
                  HAVING array_agg(module) = %s""", ([mod_id],))
    relations = tuple(vals[0] for vals in cr.fetchall())
    cr.execute("DELETE FROM ir_model_relation WHERE module=%s", (mod_id,))
    if relations:
        cr.execute("""SELECT table_name
                      FROM information_schema.tables
                      WHERE table_name IN {}"""
                   .format(relations))
        for rel, in cr.fetchall():
            cr.execute('DROP TABLE "{}" CASCADE'.format(rel))

    if model_ids:
        cr.execute("SELECT model FROM ir_model WHERE id IN %s", [model_ids])
        for model, in cr.fetchall():
            remove_model(cr, model)

    if field_ids:
        cr.execute("SELECT model, name FROM ir_model_fields WHERE id IN %s",
                   [field_ids])
        for model, name in cr.fetchall():
            remove_field(cr, model, name)

    cr.execute("""DELETE FROM ir_model_data
                  WHERE model='ir.module.module'
                  AND res_id={}""".format(mod_id))
    cr.execute("DELETE FROM ir_model_data WHERE module={}".format(module))
    cr.execute("DELETE FROM ir_module_module WHERE name={}".format(module))
    cr.execute("DELETE FROM ir_module_module_dependency WHERE name={}"
               .format(module))


def rename_module(cr, old, new):
    """Rename a module. Yes, really."""
    cr.execute("UPDATE ir_module_module SET name={} WHERE name={}"
               .format(new, old))
    cr.execute("UPDATE ir_module_module_dependency SET name={} WHERE name={}"
               .format(new, old))
    _update_view_key(cr, old, new)
    cr.execute("UPDATE ir_model_data SET module={} WHERE module={}"
               .format(new, old))
    mod_old = 'module_' + old
    mod_new = 'module_' + new
    cr.execute("""UPDATE ir_model_data
                     SET name = {}
                   WHERE name = {}
                     AND module = {}
                     AND model = {}
               """.format(mod_new, mod_old, 'base', 'ir.module.module'))


def merge_module(cr, old, into, tolerant=False):
    """Move all references of module `old` into module `into`.

        :param str old: source module to merge
        :param str into: destination module to merge into
        :tolerant bool: if True, the merge will be skipped if the database
                        does not have the `old` module in its ir_module_module
                        table (e.g. if the module was released after the
                        creation of the database)
    """
    cr.execute(
        "SELECT name, id FROM ir_module_module WHERE name IN %s", [(old, into)])
    mod_ids = dict(cr.fetchall())

    if tolerant and old not in mod_ids:
        # this can happen in case of temp modules added after a release if the database does not
        # know about this module, i.e: account_full_reconcile in 9.0
        # `into` should be known; let it crash if not
        _logger.warning('Unknow module %s. Skip merging into %s.', old, into)
        return

    def _update(table, old, new):
        cr.execute("""UPDATE ir_model_{0} x
                         SET module=%s
                       WHERE module=%s
                         AND NOT EXISTS(SELECT 1
                                          FROM ir_model_{0} y
                                         WHERE y.name = x.name
                                           AND y.module = %s)
                   """.format(table),
                   [new, old, new])

        if table == 'data':
            cr.execute("""
                SELECT model, array_agg(res_id)
                  FROM ir_model_data
                 WHERE module=%s
                   AND model NOT LIKE 'ir.model%%'
              GROUP BY model
            """, [old])
            for model, res_ids in cr.fetchall():
                # we can assume other records have been moved to xml files of the new module
                # remove the unnecessary data and let the module update do its job
                if model == 'ir.ui.view':
                    for v in res_ids:
                        remove_view(cr, view_id=v,
                                    deactivate_custom=True, silent=True)
                elif model == 'ir.ui.menu':
                    remove_menus(cr, tuple(res_ids))
                else:
                    for r in res_ids:
                        remove_record(cr, (model, r))

        cr.execute(
            "DELETE FROM ir_model_{0} WHERE module=%s".format(table), [old])

    _update('constraint', mod_ids[old], mod_ids[into])
    _update('relation', mod_ids[old], mod_ids[into])
    _update_view_key(cr, old, into)
    _update('data', old, into)

    # update dependencies
    cr.execute("""
        INSERT INTO ir_module_module_dependency(module_id, name)
        SELECT module_id, %s
          FROM ir_module_module_dependency d
         WHERE name=%s
           AND NOT EXISTS(SELECT 1
                            FROM ir_module_module_dependency o
                           WHERE o.module_id = d.module_id
                             AND o.name=%s)
    """, [into, old, into])

    cr.execute("DELETE FROM ir_module_module WHERE name=%s", [old])
    cr.execute("DELETE FROM ir_module_module_dependency WHERE name=%s", [old])


def force_install_module(cr, module, deps=None):
    """Force a module to be installed during the upgrade process.

        :param str module: technical name of the module to install
        :param list deps: if set, the module will be installed only if any of
                          module of this list is already installed
                          (or about to be)
    """
    subquery = ""
    subparams = ()
    if deps:
        subquery = """AND EXISTS(SELECT 1 FROM ir_module_module
                                  WHERE name IN %s
                                    AND state IN %s)"""
        subparams = (tuple(deps), _INSTALLED_MODULE_STATES)

    cr.execute("""
        WITH RECURSIVE deps (mod_id, dep_name) AS (
              SELECT m.id, d.name from ir_module_module_dependency d
              JOIN ir_module_module m on (d.module_id = m.id)
              WHERE m.name = %s
            UNION
              SELECT m.id, d.name from ir_module_module m
              JOIN deps ON deps.dep_name = m.name
              JOIN ir_module_module_dependency d on (d.module_id = m.id)
        )
        UPDATE ir_module_module m
           SET state = CASE WHEN state = 'to remove' THEN 'to upgrade'
                            WHEN state = 'uninstalled' THEN 'to install'
                            ELSE state
                       END,
               demo=(select demo from ir_module_module where name='base')
          FROM deps d
         WHERE m.id = d.mod_id
           {0}
     RETURNING m.name, m.state
    """.format(subquery), (module,) + subparams)

    state = dict(cr.fetchall()).get(module)
    return state


def new_module_dep(cr, module, new_dep):
    """Add a new dependency to a module."""
    # One new dep at a time
    cr.execute("""INSERT INTO ir_module_module_dependency(name, module_id)
                       SELECT %s, id
                         FROM ir_module_module m
                        WHERE name=%s
                          AND NOT EXISTS(SELECT 1
                                           FROM ir_module_module_dependency
                                          WHERE module_id = m.id
                                            AND name=%s)
                """, (new_dep, module, new_dep))

    # Update new_dep state depending on module state
    cr.execute("""SELECT state from ir_module_module
                  WHERE name = %s""", [module])
    mod_state = (cr.fetchone() or ['n/a'])[0]
    if mod_state in _INSTALLED_MODULE_STATES:
        # Module was installed, need to install all its deps, recursively,
        # to make sure the new dep is installed
        force_install_module(cr, module)


def remove_module_deps(cr, module, old_deps):
    """Remove a dependencies from a module.
        :param str module: name of the module whose dependencies are removed
        :param tuple old_deps: list of dependencies to be removed
    """
    assert isinstance(old_deps, tuple)
    cr.execute("""DELETE FROM ir_module_module_dependency
                        WHERE module_id = (SELECT id
                                             FROM ir_module_module
                                            WHERE name=%s)
                          AND name IN %s
               """, (module, old_deps))


def module_deps_diff(cr, module, add=(), remove=()):
    """Change the dependencies of a module (adding and removing).

        :param str module: technical name of the module with dependency changes
        :param list add: modules to add as dependencies
        :param list remove: modules to remove as dependencies
    """
    for new_dep in add:
        new_module_dep(cr, module, new_dep)
    if remove:
        remove_module_deps(cr, module, tuple(remove))


def new_module(cr, module, deps=(), auto_install=False):
    """Make a new module known to the database.

        :param str module: technical name of the new module
        :param list deps: modules to add as dependencies
        :param bool auto_install: whether the module will auto install if all
                                  its dependencies are installed
    """
    cr.execute(
        "SELECT count(1) FROM ir_module_module WHERE name = %s", [module])
    if cr.fetchone()[0]:
        # Avoid duplicate entries for module which is already installed,
        # even before it has become standard module in new version
        # Also happen for modules added afterward, which should be added by multiple series.
        return

    if deps and auto_install:
        state = 'to install' if modules_installed(cr, *deps) else 'uninstalled'
    else:
        state = 'uninstalled'
    cr.execute("""\
        INSERT INTO ir_module_module (
            name, state, demo
        ) VALUES (
            %s, %s, (select demo from ir_module_module where name='base'))
        RETURNING id""", (module, state))
    new_id, = cr.fetchone()

    cr.execute("""\
        INSERT INTO ir_model_data (
            name, module, noupdate, model, res_id
        ) VALUES (
            'module_'||%s, 'base', 't', 'ir.module.module', %s
        )""", (module, new_id))

    for dep in deps:
        new_module_dep(cr, module, dep)


def force_migration_of_fresh_module(cr, module):
    """Force migration scripts to be executed for new modules.

    In some cases, new (or forced installed) modules need a migration script to grab data
    form other modules. In that case, forcing its state to be 'to upgrade' will allow
    migration scripts to be run even if the module was not installed before the migration.
    """
    filename, _ = frame_codeinfo(currentframe(), 1)
    version = '.'.join(filename.split(os.path.sep)[-2].split('.')[:2])

    # Force module state to be in `to upgrade`.
    # Needed for migration script execution. See http://git.io/vnF7f
    cr.execute("""UPDATE ir_module_module
                     SET state='to upgrade',
                         latest_version=%s
                   WHERE name=%s
                     AND state='to install'
               RETURNING id""", [version, module])
    if cr.rowcount:
        # Force module in `init` mode beside its state is forced to `to upgrade`
        # See http://git.io/vnF7O
        odoo.tools.config['init'][module] = "oh yeah!"


def split_group(cr, from_groups, to_group):
    """Make users members of all `from_groups` members of `to_group`"""

    def check_group(g):
        if isinstance(g, str):
            gid = ref(cr, g)
            if not gid:
                _logger.warning('split_group(): Unknow group: %r', g)
            return gid
        return g

    if not isinstance(from_groups, (list, tuple, set)):
        from_groups = [from_groups]

    from_groups = [g for g in map(check_group, from_groups) if g]
    if not from_groups:
        return

    if isinstance(to_group, str):
        to_group = ref(cr, to_group)

    assert to_group

    cr.execute("""
        INSERT INTO res_groups_users_rel(uid, gid)
             SELECT uid, %s
               FROM res_groups_users_rel
           GROUP BY uid
             HAVING array_agg(gid) @> %s
             EXCEPT
             SELECT uid, gid
               FROM res_groups_users_rel
              WHERE gid = %s
    """, [to_group, from_groups, to_group])

# Models & Fields utilities


def create_m2m(cr, m2m, fk1, fk2, col1=None, col2=None):
    """Create a many2many relation table.

        :param str m2m: relation table name
        :param str fk1: table referenced by first column
        :param str fk2: table referenced by second column
        :param str col1: first column name
        :param str col2: second column name
    """
    if col1 is None:
        col1 = '%s_id' % fk1
    if col2 is None:
        col2 = '%s_id' % fk2

    cr.execute("""
        CREATE TABLE {m2m}(
            {col1} integer NOT NULL REFERENCES {fk1}(id) ON DELETE CASCADE,
            {col2} integer NOT NULL REFERENCES {fk2}(id) ON DELETE CASCADE,
            UNIQUE ({col1}, {col2})
        );
        CREATE INDEX ON {m2m}({col1});
        CREATE INDEX ON {m2m}({col2});
    """.format(**locals()))


def ensure_m2o_func_field_data(cr, src_table, column, dst_table):
    """Fix broken many2one relations.

        If any `column` not present in `dst_table`, remove column from `src_table` in
        order to force recomputation of the function field

        WARN: only call this method on m2o function/related fields!!
    """
    if not column_exists(cr, src_table, column):
        return
    cr.execute("""SELECT count(1)
                    FROM "{src_table}"
                   WHERE "{column}" NOT IN (SELECT id FROM "{dst_table}")
               """.format(src_table=src_table, column=column, dst_table=dst_table))
    if cr.fetchone()[0]:
        remove_column(cr, src_table, column, cascade=True)


def uniq_tags(cr, model, uniq_column='name', order='id'):
    """Deduplicate "tag" models entries.

        Should only be referenced as many2many

        By using `uniq_column=lower(name)` and `order=name`
        you can prioritize tags in CamelCase/UPPERCASE.
    """
    table = table_of_model(cr, model)
    upds = []
    for ft, fc, _, da in get_fk(cr, table):
        assert da == 'c'    # should be a ondelete=cascade fk
        cols = get_columns(cr, ft, ignore=(fc,))[0]
        assert len(cols) == 1   # it's a m2, should have only 2 columns

        upds.append("""
            INSERT INTO {rel}({c1}, {c2})
                 SELECT r.{c1}, d.id
                   FROM {rel} r
                   JOIN dups d ON (r.{c2} = ANY(d.others))
                 EXCEPT
                 SELECT r.{c1}, r.{c2}
                   FROM {rel} r
                   JOIN dups d ON (r.{c2} = d.id)
        """.format(rel=ft, c1=cols[0], c2=fc))

    assert upds         # if not m2m found, there is something wrong...

    updates = ','.join('_upd_%s AS (%s)' % x for x in enumerate(upds))
    query = """
        WITH dups AS (
            SELECT (array_agg(id order by {order}))[1] as id,
                   (array_agg(id order by {order}))[2:array_length(array_agg(id), 1)] as others
              FROM {table}
          GROUP BY {uniq_column}
            HAVING count(id) > 1
        ),
        _upd_imd AS (
            UPDATE ir_model_data x
               SET res_id = d.id
              FROM dups d
             WHERE x.model = %s
               AND x.res_id = ANY(d.others)
        ),
        {updates}
        DELETE FROM {table} WHERE id IN (SELECT unnest(others) FROM dups)
    """.format(**locals())

    cr.execute(query, [model])


def remove_field(cr, model, fieldname, cascade=False):
    """Remove a field.

        :param str model: name of the field's model
        :param str fieldname: name of the field (...)
        :param bool cascade: if True, all records having a FKEY pointing to this field
                             will be cascade-deleted (default: False)
    """
    if fieldname == 'id':
        # called by `remove_module`. May happen when a model defined in a removed module was
        # overwritten by another module in previous versions.
        return remove_model(cr, model)

    # clean dashboards' `group_by`
    cr.execute("""
        SELECT      array_agg(f.name), array_agg(aw.id)
        FROM        ir_model_fields f
            JOIN    ir_act_window aw
            ON      aw.res_model = f.model
        WHERE       f.model = %s AND f.name = %s
        GROUP BY    f.model
        """, [model, fieldname])
    for fields, actions in cr.fetchall():
        cr.execute("""\
            SELECT  id, arch
            FROM    ir_ui_view_custom
            WHERE   arch ~ %s
            """, ["name=[\"'](%s)[\"']" % '|'.join(map(str, actions))])
        for id, arch in ((x, lxml.etree.fromstring(y))
                         for x, y in cr.fetchall()):
            for action in arch.iterfind('.//action'):
                context = eval(action.get('context', '{}'),
                               UnquoteEvalContext())
                if context.get('group_by'):
                    context['group_by'] = list(
                        set(context['group_by']) - set(fields))
                    action.set('context', str(context))
            cr.execute("""\
                UPDATE  ir_ui_view_custom
                SET     arch = %s
                WHERE   id = %s
                """, [lxml.etree.tostring(arch, encoding='unicode'), id])

    cr.execute(
        "DELETE FROM ir_model_fields WHERE model=%s AND name=%s RETURNING id", (model, fieldname))
    fids = tuple(vals[0] for vals in cr.fetchall())
    if fids:
        cr.execute("DELETE FROM ir_model_data WHERE model=%s AND res_id IN %s",
                   ('ir.model.fields', fids))

    # cleanup translations
    cr.execute("""
       DELETE FROM ir_translation
        WHERE name=%s
          AND type in ('field', 'help', 'model', 'selection')   -- ignore wizard_* translations
    """, ['%s,%s' % (model, fieldname)])

    table = table_of_model(cr, model)
    remove_column(cr, table, fieldname, cascade=cascade)


def move_field_to_module(cr, model, fieldname, old_module, new_module):
    """Move a field to another module."""
    name = IMD_FIELD_PATTERN % (model.replace('.', '_'), fieldname)
    cr.execute("""UPDATE ir_model_data
                     SET module=%s
                   WHERE model=%s
                     AND name=%s
                     AND module=%s
               """, (new_module, 'ir.model.fields', name, old_module))


def rename_field(cr, model, old, new, update_references=True):
    """Rename a module. Yes, really.

        :param bool update_references: if True, references to that field in
                                       filters, saved exports, etc. will be
                                       adapted (default: True)
    """
    cr.execute(
        "UPDATE ir_model_fields SET name=%s WHERE model=%s AND name=%s RETURNING id", (new, model, old))
    [fid] = cr.fetchone() or [None]
    if fid:
        name = IMD_FIELD_PATTERN % (model.replace('.', '_'), new)
        cr.execute("UPDATE ir_model_data SET name=%s WHERE model=%s AND res_id=%s",
                   (name, 'ir.model.fields', fid))
        cr.execute(
            "UPDATE ir_property SET name=%s WHERE fields_id=%s", [new, fid])

    cr.execute("""
       UPDATE ir_translation
          SET name=%s
        WHERE name=%s
          AND type in ('field', 'help', 'model', 'selection')   -- ignore wizard_* translations
    """, ['%s,%s' % (model, new), '%s,%s' % (model, old)])

    table = table_of_model(cr, model)
    # NOTE table_exists is needed to avoid altering views
    if table_exists(cr, table) and column_exists(cr, table, old):
        cr.execute(
            'ALTER TABLE "{0}" RENAME COLUMN "{1}" TO "{2}"'.format(table, old, new))

    if update_references:
        update_field_references(cr, old, new, only_models=(model,))


def make_field_company_dependent(cr, model, field, field_type,
                                 target_model=None,
                                 default_value=None, default_value_ref=None,
                                 company_field='company_id'):
    """Convert a field to be company dependent (old `property` field attributes).

    Notes:
        `target_model` is only use when `type` is "many2one".
        The `company_field` can be an sql expression.
        You may use `t` to refer the model's table.
    """
    type2field = {
        'char': 'value_text',
        'float': 'value_float',
        'boolean': 'value_integer',
        'integer': 'value_integer',
        'text': 'value_text',
        'binary': 'value_binary',
        'many2one': 'value_reference',
        'date': 'value_datetime',
        'datetime': 'value_datetime',
        'selection': 'value_text',
    }

    assert field_type in type2field
    value_field = type2field[field_type]

    cr.execute(
        "SELECT id FROM ir_model_fields WHERE model=%s AND name=%s", (model, field))
    [fields_id] = cr.fetchone()

    table = table_of_model(cr, model)

    if default_value is None:
        where_clause = '{field} IS NOT NULL'.format(field=field)
    else:
        where_clause = '{field} != %(default_value)s'.format(field=field)

    if field_type != 'many2one':
        value_select = field
    else:
        # for m2o, the store value is a reference field, so in format `model,id`
        value_select = "CONCAT('{target_model},', {field})".format(**locals())

    # TODO: remove me when anonimization module is removed
    if is_field_anonymized(cr, model, field):
        # if field is anonymized, we need to create a property for each record
        where_clause = 'true'
        # and we need to unanonymize its values
        ano_default_value = cr.mogrify('%s', [default_value])
        if field_type != 'many2one':
            ano_value_select = '%(value)s'
        else:
            ano_value_select = "CONCAT('{0},', %(value)s)".format(target_model)

        register_unanonymization_query(
            cr, model, field,
            """
            UPDATE ir_property
               SET {value_field} = CASE WHEN %(value)s IS NULL THEN {ano_default_value}
                                        ELSE {ano_value_select} END
             WHERE res_id = CONCAT('{model},', %(id)s)
               AND name='{field}'
               AND type='{field_type}'
               AND fields_id={fields_id}
            """.format(**locals())
        )

    cr.execute("""
        WITH cte AS (
            SELECT CONCAT('{model},', id) as res_id, {value_select} as value,
                   ({company_field})::integer as company
              FROM {table} t
             WHERE {where_clause}
        )
        INSERT INTO ir_property(name, type, fields_id, company_id, res_id, {value_field})
            SELECT %(field)s, %(field_type)s, %(fields_id)s, cte.company, cte.res_id, cte.value
              FROM cte
             WHERE NOT EXISTS(SELECT 1
                                FROM ir_property
                               WHERE fields_id=%(fields_id)s
                                 AND COALESCE(company_id, 0) = COALESCE(cte.company, 0)
                                 AND res_id=cte.res_id)
    """.format(**locals()), locals())
    # default property
    if default_value:
        cr.execute("""INSERT INTO ir_property(name, type, fields_id, {value_field})
                           VALUES (%s, %s, %s, %s)
                        RETURNING id
                   """.format(value_field=value_field),
                   (field, field_type, fields_id, default_value)
                   )
        [prop_id] = cr.fetchone()
        if default_value_ref:
            module, _, xid = default_value_ref.partition('.')
            cr.execute("""INSERT INTO ir_model_data
                                      (module, name, model, res_id, noupdate)
                               VALUES (%s, %s, %s, %s, %s)
                       """, (module, xid, 'ir.property', prop_id, True))

    remove_column(cr, table, field, cascade=True)


def is_field_anonymized(cr, model, field):
    """Check if a field has been anonymized prior to the migration."""
    if not module_installed(cr, 'anonymization'):
        return False
    cr.execute("""SELECT id
                    FROM ir_model_fields_anonymization
                   WHERE model_name = %s
                     AND field_name = %s
                     AND state = 'anonymized'
               """, [model, field])
    return bool(cr.rowcount)


def update_field_references(cr, old, new, only_models=None):
    """Replaces references to a field in several crash-prone places.

    Replace all references to field `old` to `new` in:
        - ir_filters
        - ir_exports_line
        - ir_act_server
        - ir_rule
        - mail.mass_mailing

        :param list only_models: list of models affected by the fieldname change
    """
    p = {
        'old': '\y%s\y' % (old,),
        'new': new,
        'def_old': '\ydefault_%s\y' % (old,),
        'def_new': 'default_%s' % (new,),
        'models': tuple(only_models) if only_models else (),
    }

    q = """
        UPDATE ir_filters
           SET domain = regexp_replace(domain, %(old)s, %(new)s, 'g'),
               context = regexp_replace(regexp_replace(context,
                                                       %(old)s, %(new)s, 'g'),
                                                       %(def_old)s, %(def_new)s, 'g')
    """
    if column_exists(cr, 'ir_filters', 'sort'):
        q += ", sort = regexp_replace(sort, %(old)s, %(new)s, 'g')"

    if only_models:
        q += " WHERE model_id IN %(models)s"

    cr.execute(q, p)

    # ir.exports.line
    q = """
        UPDATE ir_exports_line l
           SET name = regexp_replace(l.name, %(old)s, %(new)s, 'g')
    """
    if only_models:
        q += """
          FROM ir_exports e
         WHERE e.id = l.export_id
           AND e.resource IN %(models)s
    """
    cr.execute(q, p)

    # ir.action.server
    col_prefix = ""
    if not column_exists(cr, 'ir_act_server', 'condition'):
        col_prefix = '--'     # sql comment the line
    q = """
        UPDATE ir_act_server s
           SET {col_prefix} condition = regexp_replace(condition, %(old)s, %(new)s, 'g'),
               code = regexp_replace(code, %(old)s, %(new)s, 'g')
    """.format(col_prefix=col_prefix)
    if only_models:
        q += """
          FROM ir_model m
         WHERE m.id = s.model_id
           AND m.model IN %(models)s
           AND
        """
    else:
        q += " WHERE "

    q += "s.state = 'code'"
    cr.execute(q, p)

    # ir.rule
    q = """
        UPDATE ir_rule r
           SET domain_force = regexp_replace(domain_force, %(old)s, %(new)s, 'g')
    """
    if only_models:
        q += """
          FROM ir_model m
         WHERE m.id = r.model_id
           AND m.model IN %(models)s
        """
    cr.execute(q, p)

    # mass mailing
    if column_exists(cr, 'mail_mass_mailing', 'mailing_domain'):
        q = """
            UPDATE mail_mass_mailing u
               SET mailing_domain = regexp_replace(u.mailing_domain, %(old)s, %(new)s, 'g')
        """
        if only_models:
            if column_exists(cr, 'mail_mass_mailing', 'mailing_model_id'):
                q += """
                  FROM ir_model m
                 WHERE m.id = u.mailing_model_id
                   AND m.model IN %(models)s
                """
            else:
                q += "WHERE u.mailing_model IN %(models)s"
        cr.execute(q, p)


def recompute_fields(cr, model, fields, ids=None, logger=_logger, chunk_size=256):
    """Recompute fields using the ORM.

        :param str model:
        :param list fields:
        :param list ids: list of ids of records on which the recompute will be done;
                         if not set, will recompute for all records
        :param logger: logger used during the processing (default: current logger)
        :param integer chunk_size: batch size for recomputing (default: 256)
    """
    if ids is None:
        cr.execute('SELECT id FROM "%s"' % table_of_model(cr, model))
        ids = tuple(map(itemgetter(0), cr.fetchall()))

    Model = env(cr)[model]
    size = (len(ids) + chunk_size - 1) / chunk_size
    qual = '%s %d-bucket' % (model, chunk_size) if chunk_size != 1 else model
    for subids in log_progress(chunks(ids, chunk_size, list), qualifier=qual, logger=logger, size=size):
        records = Model.browse(subids)
        for field in fields:
            records._recompute_todo(records._fields[field])
        records.recompute()
        records.invalidate_cache()


def fix_wrong_m2o(cr, table, column, target, value=None):
    """Fix missing foreign keys references.

        :param str table: table to correct
        :param str column: column to correct
        :param str target: destination table of the FKEY
        :param value: value to set instead of the missing foreign key reference
                      that will be parsed by psycopg2 (variable type)
                      (default: None - NULL)
    """
    cr.execute("""
        WITH wrongs_m2o AS (
            SELECT s.id
              FROM {table} s
         LEFT JOIN {target} t
                ON s.{column} = t.id
             WHERE s.{column} IS NOT NULL
               AND t.id IS NULL
        )
        UPDATE {table} s
           SET {column}=%s
          FROM wrongs_m2o w
         WHERE s.id = w.id
    """.format(table=table, column=column, target=target), [value])


def remove_model(cr, model, drop_table=True):
    """Remove a model 😉."""
    model_underscore = model.replace('.', '_')

    # remove references
    for ir in indirect_references(cr):
        if ir.table == 'ir_model':
            continue
        query = 'DELETE FROM "{0}" WHERE {1} RETURNING id'.format(
            ir.table, ir.model_filter())
        cr.execute(query, [model])
        ids = tuple(vals[0] for vals in cr.fetchall())
        remove_refs(cr, model_of_table(cr, ir.table), ids)

    remove_refs(cr, model)

    cr.execute("SELECT id FROM ir_model WHERE model=%s", (model,))
    [mod_id] = cr.fetchone() or [None]
    if mod_id:
        # some required fk are "ON DELETE SET NULL".
        for tbl in 'base_action_rule google_drive_config'.split():
            if column_exists(cr, tbl, 'model_id'):
                cr.execute(
                    "DELETE FROM {0} WHERE model_id=%s".format(tbl), [mod_id])
        cr.execute("DELETE FROM ir_model_constraint WHERE model=%s", (mod_id,))
        cr.execute("DELETE FROM ir_model_relation WHERE model=%s", (mod_id,))

        # Drop XML IDs of ir.rule and ir.model.access records that will be cascade-dropped,
        # when the ir.model record is dropped - just in case they need to be re-created
        cr.execute("""DELETE FROM ir_model_data x
                            USING ir_rule a
                            WHERE x.res_id = a.id AND x.model='ir.rule' AND
                                  a.model_id = %s; """, (mod_id,))
        cr.execute("""DELETE FROM ir_model_data x
                            USING ir_model_access a
                            WHERE x.res_id = a.id AND x.model='ir.model.access' AND
                                  a.model_id = %s; """, (mod_id,))

        cr.execute("DELETE FROM ir_model WHERE id=%s", (mod_id,))

    cr.execute("DELETE FROM ir_model_data WHERE model=%s AND name=%s",
               ('ir.model', 'model_%s' % model_underscore))
    cr.execute("DELETE FROM ir_model_data WHERE model='ir.model.fields' AND name LIKE %s",
               [(IMD_FIELD_PATTERN % (model_underscore, '%')).replace('_', r'\_')])

    table = table_of_model(cr, model)
    if drop_table:
        if table_exists(cr, table):
            cr.execute('DROP TABLE "{0}" CASCADE'.format(table))
        elif view_exists(cr, table):
            # For auto=False models...
            cr.execute('DROP VIEW "{0}" CASCADE'.format(table))


def remove_refs(cr, model, ids=None):
    """Remove non-sql enforced references pointing to the specified model.

    e.g. reference fields, translations, ...
    """
    if ids is None:
        match = 'like %s'
        needle = model + ',%'
    else:
        if not ids:
            return
        match = 'in %s'
        needle = tuple('{0},{1}'.format(model, i) for i in ids)

    # "model-comma" fields
    cr.execute("""
        SELECT model, name
          FROM ir_model_fields
         WHERE ttype='reference'
         UNION
        SELECT 'ir.translation', 'name'
    """)

    for ref_model, ref_column in cr.fetchall():
        table = table_of_model(cr, ref_model)
        # NOTE table_exists is needed to avoid deleting from views
        if table_exists(cr, table) and column_exists(cr, table, ref_column):
            query_tail = ' FROM "{0}" WHERE "{1}" {2}'.format(
                table, ref_column, match)
            if ref_model == 'ir.ui.view':
                cr.execute('SELECT id' + query_tail, [needle])
                for view_id, in cr.fetchall():
                    remove_view(cr, view_id=view_id,
                                deactivate_custom=True, silent=True)
            elif ref_model == 'ir.ui.menu':
                cr.execute('SELECT id' + query_tail, [needle])
                menu_ids = tuple(m[0] for m in cr.fetchall())
                remove_menus(cr, menu_ids)
            else:
                cr.execute('DELETE' + query_tail, [needle])
                # TODO make it recursive?

    if table_exists(cr, 'ir_values'):
        column, _ = _ir_values_value(cr)
        query = 'DELETE FROM ir_values WHERE {0} {1}'.format(column, match)
        cr.execute(query, [needle])

    if ids is None:
        cr.execute("""
            DELETE FROM ir_translation
             WHERE name=%s
               AND type IN ('constraint', 'sql_constraint', 'view', 'report', 'rml', 'xsl')
        """, [model])


def move_model(cr, model, from_module, to_module, move_data=False, delete=False):
    """Move model `model` from `from_module` to `to_module`.

        :param bool move_data: reassign all xmlids from the `from_module`
                               referencing `model` records to `to_module`
                               (default: False)
        :param bool delete: if True and `to_module` is not installed,
                            delete the model (default: False)
    """
    if delete and not module_installed(cr, to_module):
        remove_model(cr, model)
        return

    model_u = model.replace('.', '_')
    cr.execute("UPDATE ir_model_data SET module=%s WHERE module=%s AND model=%s AND name=%s",
               (to_module, from_module, 'ir.model', 'model_%s' % model_u))

    cr.execute("""UPDATE ir_model_data
                     SET module=%s
                   WHERE module=%s
                     AND model='ir.model.fields'
                     AND name LIKE %s
               """, [to_module, from_module,
                     (IMD_FIELD_PATTERN % (model_u, '%')).replace('_', r'\_')])

    if move_data:
        cr.execute("""UPDATE ir_model_data
                         SET module=%s
                       WHERE module=%s
                         AND model=%s
                   """, (to_module, from_module, model))


def rename_model(cr, old, new, rename_table=True):
    """Rename a model.

        :param bool rename_table: if True, the table will be renamed according
                                  to the Odoo ORM (e.g. `ir.rule` -> `ir_rule`)
    """
    if rename_table:
        old_table = table_of_model(cr, old)
        new_table = table_of_model(cr, new)
        cr.execute('ALTER TABLE "{0}" RENAME TO "{1}"'.format(
            old_table, new_table))
        cr.execute('ALTER SEQUENCE "{0}_id_seq" RENAME TO "{1}_id_seq"'.format(
            old_table, new_table))
        # find & rename primary key, may still use an old name from a former migration
        cr.execute("""
            SELECT  conname
            FROM    pg_index, pg_constraint
            WHERE   indrelid = %s::regclass
            AND     indisprimary
            AND     conrelid = indrelid
            AND     conindid = indexrelid
            AND     confrelid = 0;
            """, [new_table])
        primary_key, = cr.fetchone()
        cr.execute('ALTER INDEX "{0}" RENAME TO "{1}_pkey"'.format(
            primary_key, new_table))

        # DELETE all constraints and indexes (ignore the PK), ORM will recreate them.
        cr.execute("""SELECT constraint_name
                        FROM information_schema.table_constraints
                       WHERE table_name=%s
                         AND constraint_type!=%s
                         AND constraint_name !~ '^[0-9_]+_not_null$'
                   """, (new_table, 'PRIMARY KEY'))
        for const, in cr.fetchall():
            cr.execute(
                "DELETE FROM ir_model_constraint WHERE name=%s", (const,))
            cr.execute('ALTER TABLE "{0}" DROP CONSTRAINT "{1}"'.format(
                new_table, const))

    updates = [r[:2] for r in res_model_res_id(cr)]

    for model, column in updates:
        table = table_of_model(cr, model)
        query = 'UPDATE {t} SET {c}=%s WHERE {c}=%s'.format(t=table, c=column)
        cr.execute(query, (new, old))

    # "model-comma" fields
    cr.execute("""
        SELECT model, name
          FROM ir_model_fields
         WHERE ttype='reference'
         UNION
        SELECT 'ir.translation', 'name'
    """)
    for model, column in cr.fetchall():
        table = table_of_model(cr, model)
        if column_exists(cr, table, column):
            cr.execute("""UPDATE "{table}"
                             SET {column}='{new}' || substring({column} FROM '%#",%#"' FOR '#')
                           WHERE {column} LIKE '{old},%'
                       """.format(table=table, column=column, new=new, old=old))

    if table_exists(cr, 'ir_values'):
        column_read, cast_write = _ir_values_value(cr)
        query = """
            UPDATE ir_values
               SET value = {cast[0]}'{new}' || substring({column} FROM '%#",%#"' FOR '#'){cast[2]}
             WHERE {column} LIKE '{old},%'
        """.format(column=column_read, new=new, old=old, cast=cast_write.partition('%s'))
        cr.execute(query)

    cr.execute("""
        UPDATE ir_translation
           SET name=%s
         WHERE name=%s
           AND type IN ('constraint', 'sql_constraint', 'view', 'report', 'rml', 'xsl')
    """, [new, old])
    old_u = old.replace('.', '_')
    new_u = new.replace('.', '_')

    cr.execute("UPDATE ir_model_data SET name=%s WHERE model=%s AND name=%s",
               ('model_%s' % new_u, 'ir.model', 'model_%s' % old_u))

    cr.execute("""UPDATE ir_model_data
                     SET name=%s || substring(name from %s)
                   WHERE model='ir.model.fields'
                     AND name LIKE %s
               """, ['field_%s' % new_u, len(old_u) + 6,
                     (IMD_FIELD_PATTERN % (old_u, '%')).replace('_', r'\_')])

    col_prefix = ""
    if not column_exists(cr, 'ir_act_server', 'condition'):
        col_prefix = '--'     # sql comment the line

    cr.execute(r"""
        UPDATE ir_act_server
           SET {col_prefix} condition=regexp_replace(condition, '([''"]){old}\1', '\1{new}\1', 'g'),
               code=regexp_replace(code, '([''"]){old}\1', '\1{new}\1', 'g')
    """.format(col_prefix=col_prefix, old=old.replace('.', r'\.'), new=new))


def replace_record_references(cr, old, new, replace_xmlid=True):
    """Replace all (in)direct references of a record by another"""
    assert isinstance(old, tuple) and len(old) == 2
    assert isinstance(new, tuple) and len(new) == 2

    if not old[1]:
        return

    return replace_record_references_batch(cr, {old[1]: new[1]}, old[0], new[0], replace_xmlid)


def replace_record_references_batch(cr, id_mapping, model_src, model_dst=None, replace_xmlid=True):
    assert id_mapping
    assert all(isinstance(v, int) and isinstance(k, int)
               for k, v in id_mapping.items())

    if model_dst is None:
        model_dst = model_src

    old = tuple(id_mapping.keys())
    new = tuple(id_mapping.values())
    jmap = json.dumps(id_mapping)

    def genmap(fmt_k, fmt_v=None):
        # generate map using given format
        fmt_v = fmt_k if fmt_v is None else fmt_v
        m = {fmt_k % k: fmt_v % v for k, v in id_mapping.items()}
        return json.dumps(m), tuple(m.keys())

    if model_src == model_dst:
        # 7 time faster than using pickle.dumps
        pmap, pmap_keys = genmap('I%d\n.')
        smap, smap_keys = genmap("%d")

        column_read, cast_write = _ir_values_value(cr)

        for table, fk, _, _ in get_fk(cr, table_of_model(cr, model_src)):
            query = """
                UPDATE {table} t
                   SET {fk} = ('{jmap}'::json->>{fk}::varchar)::int4
                 WHERE {fk} IN %(old)s
            """

            col2 = None
            if not column_exists(cr, table, 'id'):
                # seems to be a m2m table. Avoid duplicated entries
                cols = get_columns(cr, table, ignore=(fk,))[0]
                assert len(cols) == 1   # it's a m2, should have only 2 columns
                col2 = cols[0]
                query = """
                    WITH _existing AS (
                        SELECT {col2} FROM {table} WHERE {fk} IN %%(new)s
                    )
                    %s
                    AND NOT EXISTS(SELECT 1 FROM _existing WHERE {col2}=t.{col2});
                    DELETE FROM {table} WHERE {fk} IN %%(old)s;
                """ % query

            cr.execute(query.format(table=table, fk=fk, jmap=jmap, col2=col2),
                       dict(new=new, old=old))

            if not col2:    # it's a model
                # update default values
                # TODO? update all defaults using 1 query (using `WHERE (model, name) IN ...`)
                model = model_of_table(cr, table)
                if table_exists(cr, 'ir_values'):
                    query = """
                         UPDATE ir_values
                            SET value = {cast[0]} '{pmap}'::json->>({col}) {cast[2]}
                          WHERE key='default'
                            AND model=%s
                            AND name=%s
                            AND {col} IN %s
                    """.format(col=column_read, cast=cast_write.partition('%s'), pmap=pmap)
                    cr.execute(query, [model, fk, pmap_keys])
                else:
                    cr.execute("""
                        UPDATE ir_default d
                           SET json_value = '{smap}'::json->>json_value
                          FROM ir_model_fields f
                         WHERE f.id = d.field_id
                           AND f.model = %s
                           AND f.name = %s
                           AND d.json_value IN %s
                    """.format(smap=smap), [model, fk, smap_keys])

    # indirect references
    for ir in indirect_references(cr, bound_only=True):
        if ir.table == 'ir_model_data' and not replace_xmlid:
            continue
        upd = ""
        if ir.res_model:
            upd += '"{ir.res_model}" = %(model_dst)s,'
        if ir.res_model_id:
            upd += '"{ir.res_model_id}" = (SELECT id FROM ir_model WHERE model=%(model_dst)s),'
        upd = upd.format(ir=ir)
        where = ir.model_filter(placeholder="%(model_src)s")

        query = """
            UPDATE "{ir.table}"
               SET {upd}
                   "{ir.res_id}" = ('{jmap}'::json->>{ir.res_id}::varchar)::int4
             WHERE {where}
               AND {ir.res_id} IN %(old)s
        """.format(**locals())

        cr.execute(query, locals())

    # reference fields
    cmap, cmap_keys = genmap("%s,%%d" % model_src, "%s,%%d" % model_dst)
    cr.execute("SELECT model, name FROM ir_model_fields WHERE ttype='reference'")
    for model, column in cr.fetchall():
        table = table_of_model(cr, model)
        if column_exists(cr, table, column):
            cr.execute("""UPDATE "{table}"
                             SET "{column}" = '{cmap}'::json->>"{column}"
                           WHERE "{column}" IN %s
                       """.format(table=table, column=column, cmap=cmap),
                       [cmap_keys])


# ---------- UI Utilities (Views, Menus) ----------
def _update_view_key(cr, old, new):
    """Update the key of a view."""
    if not column_exists(cr, 'ir_ui_view', 'key'):
        return
    cr.execute("""
        UPDATE ir_ui_view v
           SET key = CONCAT(%s, '.', x.name)
          FROM ir_model_data x
         WHERE x.model = 'ir.ui.view'
           AND x.res_id = v.id
           AND x.module = %s
           AND v.key = CONCAT(x.module, '.', x.name)
    """, [new, old])


def remove_view(cr, xml_id=None, view_id=None, deactivate_custom=DROP_DEPRECATED_CUSTOM, silent=False):
    """
    Recursively delete the given view and its inherited views.

    Delete the view and its inherited views as long as they are part of a module.
    Will crash as soon as a custom view exists anywhere
    in the hierarchy.

        :param xml_id=None: fully qualified xmlid of the view
        :param view_id=None: id of the view
        :param deactivate_custom=False: if set, any custom view inheriting from
                                        any of the deleted views will be
                                        deactivated, otherwise a MigrationError
                                        will be raised if a custom view exists;
                                        can be set by the system environment
                                        variable OE_DROP_DEPRECATED_CUSTOM
        :param silent=False: if True, no log output will be generated

    Note that you can either provide an xml_id or view_id but not both.
    """
    assert bool(xml_id) ^ bool(
        view_id), "You Must specify either xmlid or view_id"
    if xml_id:
        view_id = ref(cr, xml_id)
        if not view_id:
            return

        module, _, name = xml_id.partition('.')
        cr.execute("""SELECT model
                      FROM ir_model_data
                      WHERE module={} AND
                            name={}
                   """.format(module, name))

        [model] = cr.fetchone()
        if model != 'ir.ui.view':
            raise ValueError("{!r} should point to a 'ir.ui.view', not a {!r}"
                             .format(xml_id, model))
    elif not silent or deactivate_custom:
        # search matching xmlid for logging or renaming of custom views
        cr.execute("""SELECT module, name
                      FROM ir_model_data
                      WHERE model='ir.ui.view' AND
                            res_id={}
                   """.format(view_id))
        if cr.rowcount:
            xml_id = "%s.%s" % cr.fetchone()
        else:
            xml_id = '?'

    cr.execute("""
        SELECT v.id, x.module || '.' || x.name
        FROM ir_ui_view v LEFT JOIN
           ir_model_data x
           ON (
               v.id = x.res_id AND
               x.model = 'ir.ui.view' AND
               x.module !~ '^_'
            )
        WHERE v.inherit_id = {};
    """.format(view_id))
    for child_id, child_xml_id in cr.fetchall():
        if child_xml_id:
            if not silent:
                _logger.info('Dropping deprecated built-in view %s (ID %s), '
                             'as parent %s (ID %s) is going to be removed',
                             child_xml_id, child_id, xml_id, view_id)
            remove_view(cr, child_xml_id, deactivate_custom=deactivate_custom,
                        silent=True)
        else:
            if deactivate_custom:
                if not silent:
                    _logger.warning('Deactivating deprecated custom view with '
                                    'ID %s, as parent %s (ID %s) was removed',
                                    child_id, xml_id, view_id)
                disable_view_query = """
                    UPDATE ir_ui_view
                    SET name = (name || ' - old view, inherited from ' || %s),
                        model = (model || '.disabled'),
                        inherit_id = NULL
                        WHERE id = %s
                """
                cr.execute(disable_view_query, (xml_id, child_id))
            else:
                raise MigrationError('Deprecated custom view with ID %s needs migration, '
                                     'as parent %s (ID %s) is going to be removed' %
                                     (child_id, xml_id, view_id))
    if not silent:
        _logger.info('Dropping deprecated built-in view %s (ID %s).',
                     xml_id, view_id)
    remove_record(cr, ('ir.ui.view', view_id))


@contextmanager
def edit_view(cr, xmlid=None, view_id=None, skip_if_noupdate=False):
    """Contextmanager that may yield etree arch of a view.

    As it may not yield, you must use `skippable_cm`:

    with migration.skippable_cm(), migration.edit_view(cr, 'xmlid') as arch:
        arch.attrib['string'] = 'My Form'

        :param xml_id=None: fully qualified xmlid of the view
        :param view_id=None: id of the view
        :param skip_if_noupdate=False: if True, will not yield if the view is
                                       set to be non-updatable

    Note that you can either provide an xml_id or view_id but not both.
    """
    assert bool(xmlid) ^ bool(
        view_id), "You Must specify either xmlid or view_id"
    noupdate = True
    if xmlid:
        if '.' not in xmlid:
            raise ValueError('Please use fully qualified name <module>.<name>')

        module, _, name = xmlid.partition('.')
        cr.execute("""SELECT res_id, noupdate
                        FROM ir_model_data
                       WHERE module = %s
                         AND name = %s
                   """, (module, name))
        data = cr.fetchone()
        if data:
            view_id, noupdate = data

    if view_id and not (skip_if_noupdate and noupdate):
        cr.execute("""SELECT arch_db
                        FROM ir_ui_view
                       WHERE id={}
                   """.format(view_id))
        [arch] = cr.fetchone() or [None]
        if arch:
            arch = lxml.etree.fromstring(arch)
            yield arch
            cr.execute("UPDATE ir_ui_view SET arch_db={} WHERE id={}"
                       .format(lxml.etree.tostring(arch, encoding='unicode'),
                               view_id))


def remove_menus(cr, menu_ids):
    """Remove ir.ui.menu records with the provided ids (and their children)."""
    if not menu_ids:
        return
    cr.execute("""
        WITH RECURSIVE tree(id) AS (
            SELECT id
              FROM ir_ui_menu
             WHERE id IN %s
             UNION
            SELECT m.id
              FROM ir_ui_menu m
              JOIN tree t ON (m.parent_id = t.id)
        )
        DELETE FROM ir_ui_menu m
              USING tree t
              WHERE m.id = t.id
          RETURNING m.id
    """, [tuple(menu_ids)])
    ids = tuple(x[0] for x in cr.fetchall())
    if ids:
        cr.execute(
            "DELETE FROM ir_model_data WHERE model='ir.ui.menu' AND res_id IN %s", [ids])

# ---------- Database/Postgres Utilities ----------


def dbuuid(cr):
    """Get the uuid of the current database.

    In the case of a duplicated database, return the original uuid."""
    cr.execute("""
        SELECT value
          FROM ir_config_parameter
         WHERE key IN ('database.uuid', 'origin.database.uuid')
      ORDER BY key DESC
         LIMIT 1
    """)
    return cr.fetchone()[0]


def has_enterprise():
    """Check if the current installation has enterprise addons availables or not."""
    return bool(get_module_path('web_enterprise', downloaded=False, display_warning=False))


def model_of_table(cr, table):
    """Return the model name for the provided table."""
    return {
        # could also be ir.actions.act_window_close, but we have yet
        # to encounter a case where we need it
        'ir_actions':         'ir.actions.actions',
        'ir_act_url':         'ir.actions.act_url',
        'ir_act_window':      'ir.actions.act_window',
        'ir_act_window_view': 'ir.actions.act_window.view',
        'ir_act_client':      'ir.actions.client',
        'ir_act_report_xml':  'ir.actions.report',
        'ir_act_server':      'ir.actions.server',
        'ir_act_wizard':      'ir.actions.wizard',

        'ir_config_parameter':  'ir.config_parameter',

    }.get(table, table.replace('_', '.'))


def table_of_model(cr, model):
    """Return the table for the provided model name."""
    return {
        'ir.actions.actions':          'ir_actions',
        'ir.actions.act_url':          'ir_act_url',
        'ir.actions.act_window':       'ir_act_window',
        'ir.actions.act_window_close': 'ir_actions',
        'ir.actions.act_window.view':  'ir_act_window_view',
        'ir.actions.client':           'ir_act_client',
        'ir.actions.report.xml':       'ir_act_report_xml',
        'ir.actions.report':           'ir_act_report_xml',
        'ir.actions.server':           'ir_act_server',
        'ir.actions.wizard':           'ir_act_wizard',
    }.get(model, model.replace('.', '_'))


def table_exists(cr, table):
    """Check if the specified table exists."""
    cr.execute("""SELECT 1
                    FROM information_schema.tables
                   WHERE table_name = %s
                     AND table_type = 'BASE TABLE'
               """, (table,))
    return cr.fetchone() is not None


def column_exists(cr, table, column):
    """Check if the column exist on the specified table."""
    return column_type(cr, table, column) is not None


def column_type(cr, table, column):
    """Get the type of the column on the specified table."""
    cr.execute("""SELECT udt_name
                    FROM information_schema.columns
                   WHERE table_name = %s
                     AND column_name = %s
               """, (table, column))
    r = cr.fetchone()
    return r[0] if r else None


def create_column(cr, table, column, definition):
    """Create a column on the specified table.

        :param str table: name of the table on which the column will be created
        :param str column: name of the new column
        :param str definition: SQL-style definition of the table type
                               e.g. `boolean` or `varchar(256)`
    """
    curtype = column_type(cr, table, column)
    if curtype:
        # TODO compare with definition
        pass
    else:
        cr.execute("""ALTER TABLE "%s" ADD COLUMN "%s" %s""" %
                   (table, column, definition))


def remove_column(cr, table, column, cascade=False):
    """Remove a column.

        :param str table: name of the table on which the column will be dropped
        :param str column: name of the column to drop
        :param bool cascade: if True, all records having a FKEY pointing to this column
                             will be cascade-deleted (default: False)
    """
    if column_exists(cr, table, column):
        drop_depending_views(cr, table, column)
        drop_cascade = " CASCADE" if cascade else ""
        cr.execute('ALTER TABLE "{0}" DROP COLUMN "{1}"{2}'.format(
            table, column, drop_cascade))


def get_columns(cr, table, ignore=('id',), extra_prefixes=None):
    """
    Get the list of column in a table, minus ignored ones.

    Can also returns the list multiple times with different prefixes.
    This can be used to duplicating records (INSERT SELECT from the same table)

        :param table: table toinspect
        :param ignore=('id'): tuple of column names to ignore
    """
    select = 'quote_ident(column_name)'
    params = []
    if extra_prefixes:
        select = ','.join([select] + ["concat(%%s, '.', %s)" %
                                      select] * len(extra_prefixes))
        params = list(extra_prefixes)

    cr.execute("""SELECT {select}
                   FROM information_schema.columns
                  WHERE table_name=%s
                    AND column_name NOT IN %s
               """.format(select=select), params + [table, ignore])
    return list(zip(*cr.fetchall()))


def get_depending_views(cr, table, column):
    """Get the list of SQL views depending on the specified column."""
    # http://stackoverflow.com/a/11773226/75349
    q = """
        SELECT distinct quote_ident(dependee.relname)
        FROM pg_depend
        JOIN pg_rewrite ON pg_depend.objid = pg_rewrite.oid
        JOIN pg_class as dependee ON pg_rewrite.ev_class = dependee.oid
        JOIN pg_class as dependent ON pg_depend.refobjid = dependent.oid
        JOIN pg_attribute ON pg_depend.refobjid = pg_attribute.attrelid
            AND pg_depend.refobjsubid = pg_attribute.attnum
        WHERE dependent.relname = %s
        AND pg_attribute.attnum > 0
        AND pg_attribute.attname = %s
        AND dependee.relkind='v'
    """
    cr.execute(q, [table, column])
    return map(itemgetter(0), cr.fetchall())


def drop_depending_views(cr, table, column):
    """Drop views depending on a column.

    This is usually used to ensure that modifying fields will not make
    SQL views (auto=False models) crash after the upgrade, forcing them
    to be regenerated during the uprade.
    """
    for v in get_depending_views(cr, table, column):
        cr.execute("DROP VIEW IF EXISTS {0} CASCADE".format(v))


def get_fk(cr, table):
    """Get the list of foreign keys pointing to `table`

        :rtype: list(tuple)
        :return: [(foreign_table, foreign_column, constraint_name, on_delete_action)]
                 where on_delete_action if one of the following:
                 - a: no action
                 - r: restrict
                 - c: cascade
                 - n: set null
                 - d: set default
    """
    q = """SELECT quote_ident(cl1.relname) as table,
                  quote_ident(att1.attname) as column,
                  quote_ident(con.conname) as conname,
                  con.confdeltype
             FROM pg_constraint as con, pg_class as cl1, pg_class as cl2,
                  pg_attribute as att1, pg_attribute as att2
            WHERE con.conrelid = cl1.oid
              AND con.confrelid = cl2.oid
              AND array_lower(con.conkey, 1) = 1
              AND con.conkey[1] = att1.attnum
              AND att1.attrelid = cl1.oid
              AND cl2.relname = %s
              AND att2.attname = 'id'
              AND array_lower(con.confkey, 1) = 1
              AND con.confkey[1] = att2.attnum
              AND att2.attrelid = cl2.oid
              AND con.contype = 'f'
    """
    cr.execute(q, (table,))
    return cr.fetchall()


def delete_unused(cr, table, xmlids, set_noupdate=True):
    """
    Delete all records in the provided list not being referenced in any FKEY.

    Note that the xmlids themselves are not removed.

        :param table: target table for the deletion
        :param xmlids: list of xmlids to be checked and potentially deleted
        :param set_noupdate=True: if set, the noupdate field of all the provided
                                  xmlids will be set to True
    """
    sub = ' UNION '.join(['SELECT 1 FROM "{}" x WHERE x."{}"=t.id'.format(f[0], f[1])
                          for f in get_fk(cr, table)])
    idmap = {ref(cr, x): x for x in xmlids}
    idmap.pop(None, None)
    if not sub or not idmap:
        return
    cr.execute("""
        SELECT id
          FROM "{}" t
         WHERE id=ANY(%s)
           AND NOT EXISTS({})
    """.format(table, sub), [list(idmap)])

    for tid, in cr.fetchall():
        remove_record(cr, idmap.pop(tid))

    if set_noupdate:
        for xid in idmap.values():
            force_noupdate(cr, xid, True)


def get_index_on(cr, table, *columns):
    """Get the list of indexes on the provided column names.

        :rtype: list(tuple)
        :return:a [(index_name, unique, pk)]
    """
    cr.execute("""
        select name, indisunique, indisprimary
          from (select quote_ident(i.relname) as name,
                       x.indisunique, x.indisprimary,
                       array_agg(a.attname::text order by a.attname) as attrs
                  FROM (select *, unnest(indkey) as unnest_indkey from pg_index) x
                  JOIN pg_class c ON c.oid = x.indrelid
                  JOIN pg_class i ON i.oid = x.indexrelid
                  JOIN pg_attribute a ON (a.attrelid=c.oid AND a.attnum=x.unnest_indkey)
                 WHERE (c.relkind = ANY (ARRAY['r'::"char", 'm'::"char"]))
                   AND i.relkind = 'i'::"char"
                   AND c.relname = %s
              group by 1, 2, 3
          ) idx
         where attrs = %s
    """, [table, sorted(columns)])
    return cr.fetchone()


def pg_array_uniq(a, drop_null=False):
    """???"""
    dn = "WHERE x IS NOT NULL" if drop_null else ""
    return "ARRAY(SELECT x FROM unnest({0}) x {1} GROUP BY x)".format(a, dn)


def pg_html_escape(s, quote=True):
    """SQL version of html.escape"""
    replacements = [
        ("&", "&amp;"),   # Must be done first!
        ("<", "&lt;"),
        (">", "&gt;"),
    ]
    if quote:
        replacements += [
            ('"', "&quot;"),
            ('\'', "&#x27;"),
        ]

    def q(s): return psycopg2.extensions.QuotedString(s).getquoted().decode('utf-8')     # noqa: E731
    return reduce(lambda s, r: "replace({}, {}, {})".format(s, q(r[0]), q(r[1])), replacements, s)


def pg_text2html(s):
    return r"CONCAT('<p>', replace({0}, E'\n', '<br>'), '</p>')".format(pg_html_escape(s))


def view_exists(cr, view):
    """Check if the specified SQL view exists."""
    cr.execute(
        "SELECT 1 FROM information_schema.views WHERE table_name=%s", [view])
    return bool(cr.rowcount)

# ----------------- Utils -----------------


def remove_record(cr, name, deactivate=False, active_field='active'):
    """
    Remove a record from the database by xmlid.

        :param str name: fully qualified xmlid (<module>.<name>)
        :param boolean deactivate: if True, the record may be archived if
                                   deletion is impossible (eg FKEY constraint)
        :param str active_field: name of the field to use for deactivation,
                                 'active' by default
    """
    if '.' not in name:
        raise ValueError('Please use fully qualified name <module>.<name>')
    module, name = name.split('.')
    cr.execute("""DELETE FROM ir_model_data
                        WHERE module = %s
                            AND name = %s
                    RETURNING model, res_id
                """, (module, name))
    data = cr.fetchone()
    if not data:
        return
    model, res_id = data
    table = table_of_model(cr, model)
    try:
        with savepoint(cr):
            cr.execute('DELETE FROM "%s" WHERE id=%%s' % table, (res_id,))
    except Exception:
        if not deactivate or not active_field:
            raise
        cr.execute('UPDATE "%s" SET "%s"=%%s WHERE id=%%s' %
                   (table, active_field), (False, res_id))
    else:
        # delete all indirect references to the record (e.g. mail_message entries, etc.)
        for ir in indirect_references(cr, bound_only=True):
            query = 'DELETE FROM "{}" WHERE {} AND "{}"=%s'.format(
                ir.table, ir.model_filter(), ir.res_id)
            cr.execute(query, [model, res_id])


def splitlines(s):
    """Yield stripped lines of `s`.

    Skip empty lines & remove comments (starts with `#`).
    """
    return (sl for l in s.splitlines() for sl in [l.split('#', 1)[0].strip()] if sl)


def expand_braces(s):
    """Expand braces (a la bash).

    Only handle one expension of a 2 parts (because we don't need more).
    """
    r = re.compile(r'(.*){([^},]*?,[^},]*?)}(.*)')
    m = r.search(s)
    if not m:
        raise ValueError('No braces to expand')
    head, match, tail = m.groups()
    a, b = match.split(',')
    return [head + a + tail, head + b + tail]


class IndirectReference(namedtuple('IndirectReference', 'table res_model res_id res_model_id')):
    def model_filter(self, prefix="", placeholder="%s"):
        if prefix and prefix[-1] != '.':
            prefix += '.'
        if self.res_model_id:
            placeholder = '(SELECT id FROM ir_model WHERE model={})'.format(
                placeholder)
            column = self.res_model_id
        else:
            column = self.res_model

        return '{}"{}"={}'.format(prefix, column, placeholder)


# allow the class to handle defaults implicitely
IndirectReference.__new__.__defaults__ = (
    None, None)   # https://stackoverflow.com/a/18348004


def indirect_references(cr, bound_only=False):
    IR = IndirectReference
    each = [
        IR('ir_attachment', 'res_model', 'res_id'),
        IR('ir_cron', 'model', None),
        IR('ir_act_report_xml', 'model', None),
        IR('ir_act_window', 'res_model', 'res_id'),
        IR('ir_act_window', 'src_model', None),
        IR('ir_act_server', 'wkf_model_name', None),
        IR('ir_act_server', 'crud_model_name', None),
        IR('ir_act_client', 'res_model', None),
        IR('ir_model', 'model', None),
        IR('ir_model_fields', 'model', None),
        # destination of a relation field
        IR('ir_model_fields', 'relation', None),
        IR('ir_model_data', 'model', 'res_id'),
        IR('ir_filters', 'model_id', None),     # YUCK!, not an id
        IR('ir_exports', 'resource', None),
        IR('ir_ui_view', 'model', None),
        IR('ir_values', 'model', 'res_id'),
        IR('wkf_transition', 'trigger_model', None),
        IR('wkf_triggers', 'model', None),
        IR('ir_model_fields_anonymization', 'model_name', None),
        IR('ir_model_fields_anonymization_migration_fix', 'model_name', None),
        IR('base_import_import', 'res_model', None),
        IR('calendar_event', 'res_model', 'res_id'),      # new in saas~18
        IR('mail_template', 'model', None),
        IR('mail_activity', 'res_model', 'res_id', 'res_model_id'),
        IR('mail_alias', None, 'alias_force_thread_id', 'alias_model_id'),
        IR('mail_alias', None, 'alias_parent_thread_id', 'alias_parent_model_id'),
        IR('mail_followers', 'res_model', 'res_id'),
        IR('mail_message_subtype', 'res_model', None),
        IR('mail_message', 'model', 'res_id'),
        IR('mail_compose_message', 'model', 'res_id'),
        IR('mail_wizard_invite', 'res_model', 'res_id'),
        IR('mail_mail_statistics', 'model', 'res_id'),
        IR('mail_mass_mailing', 'mailing_model', None),
        IR('project_project', 'alias_model', None),
        IR('rating_rating', 'res_model', 'res_id', 'res_model_id'),
        IR('rating_rating', 'parent_res_model',
           'parent_res_id', 'parent_res_model_id'),
    ]

    for ir in each:
        if bound_only and not ir.res_id:
            continue
        if ir.res_id and not column_exists(cr, ir.table, ir.res_id):
            continue

        # some `res_model/res_model_id` combination may change between
        # versions (i.e. rating_rating.res_model_id was added in saas~15).
        # we need to verify existance of columns before using them.
        if ir.res_model and not column_exists(cr, ir.table, ir.res_model):
            ir = ir._replace(res_model=None)
        if ir.res_model_id and not column_exists(cr, ir.table, ir.res_model_id):
            ir = ir._replace(res_model_id=None)
        if not ir.res_model and not ir.res_model_id:
            continue

        yield ir


def res_model_res_id(cr):
    """Iterate on base models having a field that references records by model/id.

    Allow iterating on all models that reference records by using a
    res_model/res_id field combiination of similar reference system;
    usually used to quickly iterate over basic ORM models (views, crons, etc.)
    that references other models in an indirect way (without FKEY).

        :rtype tuple:
        :return: tuple containing the model, model reference field name
                 and id reference field name
    """
    for ir in indirect_references(cr):
        if ir.res_model:
            yield model_of_table(cr, ir.table), ir.res_model, ir.res_id


@contextmanager
def skippable_cm():
    """Allow a contextmanager to not yield."""
    if not hasattr(skippable_cm, '_msg'):
        @contextmanager
        def _():
            if 0:
                yield
        try:
            with _():
                pass
        except RuntimeError as r:
            skippable_cm._msg = str(r)
    try:
        yield
    except RuntimeError as r:
        if str(r) != skippable_cm._msg:
            raise


@contextmanager
def savepoint(cr):
    """Provide a savepoint context.

    If a query executed in this context fails, the operation is rollbacked,
    otherwise it success silently.
    """
    name = hex(int(time.time() * 1000))[1:]
    cr.execute("SAVEPOINT %s" % (name,))
    try:
        yield
        cr.execute('RELEASE SAVEPOINT %s' % (name,))
    except Exception:
        cr.execute('ROLLBACK TO SAVEPOINT %s' % (name,))
        raise


def log_progress(it, qualifier='elements', logger=_logger, size=None):
    if size is None:
        size = len(it)
    size = float(size)
    t0 = t1 = datetime.datetime.now()
    for i, e in enumerate(it, 1):
        yield e
        t2 = datetime.datetime.now()
        if (t2 - t1).total_seconds() > 60:
            t1 = datetime.datetime.now()
            tdiff = t2 - t0
            logger.info("[%.02f%%] %d/%d %s processed in %s (TOTAL estimated time: %s)",
                        (i / size * 100.0), i, size, qualifier, tdiff,
                        datetime.timedelta(seconds=tdiff.total_seconds() * size / i))


def env(cr):
    """Get an environment for the SUPERUSER ('admin')."""
    from odoo.api import Environment
    return Environment(cr, SUPERUSER_ID, {})


def import_script(path):
    """Import a script from another module.

    This can be used if some changes have been applied across the whole
    codebase but would need module-specific changes; e.g. a generic script
    can be defined in the `base` module and called by any relevant module
    who might want to use it to adapt something depending on values depending
    from that module.

        :param path: relative path to the script
                     <module>/<versions>/<script>
                     e.g. base/12.0.1.3/do_stuff.py
    """
    name, _ = os.path.splitext(os.path.basename(path))
    full_path = os.path.join(os.path.dirname(__file__), path)
    with open(full_path) as fp:
        return imp.load_source(name, full_path, fp)


def dispatch_by_dbuuid(cr, version, callbacks):
    """Apply dbuuid-specific migrations.

    Allow defining custom migration functions that can be applied on a
    single database identified by its uuid, e.g.:

    _db_callback(cr, version):
        # do stuff specific to that db

    def migrate(cr, version):
        migration.dispatch_by_dbuuid(cr, version, {
            '88ef269b-f6de-4f76-b9c8-868fc5569136': _db_callback,
        })

    The callback function _db_callback should have the same signature as a
    `migrate` function, taking the cursor `cr` and `version` as args.

        :param version: target version for this upgrade
        :param callbacks: dict where each key is a uuid and value is a
                          reference to the callback function
    """
    uuid = dbuuid(cr)
    if uuid in callbacks:
        func = callbacks[uuid]
        _logger.info('calling dbuuid-specific function `%s`', func.__name__)
        func(cr, version)


def register_unanonymization_query(cr, model, field, query, query_type='sql', sequence=10):
    """
    Generate an unanonymization query.

    Allow newly created fields, values, etc. to be deanonymzed even though they
    were not present during anonymization (e.g. when values are moved/copied).

        :param model:
        :param field:
        :param query:
        :param query_type='sql':
        :param sequence=10:
    """
    cr.execute("""INSERT INTO ir_model_fields_anonymization_migration_fix(
                    target_version, sequence, query_type, model_name, field_name, query
                  ) VALUES (%s, %s, %s, %s, %s, %s)
               """, [release.major_version, sequence, query_type, model, field, query])


def _rst2html(rst):
    """Convert rst to html."""
    overrides = dict(embed_stylesheet=False, doctitle_xform=False,
                     output_encoding='unicode', xml_declaration=False)
    html = publish_string(source=dedent(
        rst), settings_overrides=overrides, writer=MyWriter())
    return html_sanitize(html, silent=False)


def _md2html(md):
    """Convert markdown to html."""
    extensions = [
        'markdown.extensions.smart_strong',
        'markdown.extensions.nl2br',
        'markdown.extensions.sane_lists',
    ]
    return markdown.markdown(md, extensions=extensions)

# ---------- xmlid utilities ----------


def ref(cr, xmlid):
    """Get the id of an xmlid entry."""
    if '.' not in xmlid:
        raise ValueError('Please use fully qualified name <module>.<name>')

    module, name = xmlid.split('.')
    cr.execute("""SELECT res_id
                    FROM ir_model_data
                   WHERE module = %s
                     AND name = %s
                """, (module, name))
    data = cr.fetchone()
    if data:
        return data[0]
    return None


def rename_xmlid(cr, old, new, noupdate=None):
    """Rename an xmlid.

    In the case of a view xmlid, the key if the view is updated as well.
    """
    if '.' not in old or '.' not in new:
        raise ValueError('Please use fully qualified name <module>.<name>')

    old_module, old_name = old.split('.')
    new_module, new_name = new.split('.')
    nu = '' if noupdate is None else (
        ', noupdate=' + str(bool(noupdate)).lower())
    cr.execute("""UPDATE ir_model_data
                     SET module=%s, name=%s
                         {}
                   WHERE module=%s AND name=%s
               RETURNING model, res_id
               """.format(nu), (new_module, new_name, old_module, old_name))
    data = cr.fetchone()
    if data:
        model, rid = data
        if model == 'ir.ui.view':
            _update_view_key(cr, old, new)
            cr.execute("UPDATE ir_ui_view SET key=%s WHERE id=%s AND key=%s", [
                       new, rid, old])
        return rid
    return None


def force_noupdate(cr, xmlid, noupdate=True, warn=False):
    """Force the noupdate value of an xmlid."""
    if '.' not in xmlid:
        raise ValueError('Please use fully qualified name <module>.<name>')

    module, name = xmlid.split('.')
    cr.execute("""UPDATE ir_model_data
                     SET noupdate = %s
                   WHERE module = %s
                     AND name = %s
                     AND noupdate != %s
                """, (noupdate, module, name, noupdate))
    if noupdate is False and cr.rowcount and warn:
        _logger.warning('Customizations on `%s` might be lost!', xmlid)
    return cr.rowcount


def ensure_xmlid_match_record(cr, xmlid, model, values):
    """Ensure the provided values matches the provided xmlid.

    Check the provided model table for the presence of a record matching
    the given xmlid. If the record is not found, searches the table for
    any record matching the provided values and associate it to the xmlid.

        :param str xmlid: fully qualified xmlid (<module>.<name>)
        :param str model: name of the model to check (Odoo model name)
        :param tuple values: column name and value to check if the record needs
                             to be found in the table (will be used in a WHERE
                             query)
        :rtype: integer
        :return: ID of the record
    """
    if '.' not in xmlid:
        raise ValueError('Please use fully qualified name <module>.<name>')

    module, name = xmlid.split('.')
    cr.execute("""SELECT id, res_id
                    FROM ir_model_data
                   WHERE module = %s
                     AND name = %s
                """, (module, name))

    table = table_of_model(cr, model)
    data = cr.fetchone()
    if data:
        data_id, res_id = data
        # check that record still exists
        cr.execute("SELECT id FROM %s WHERE id=%%s" % table, (res_id,))
        if cr.fetchone():
            return res_id
    else:
        data_id = None

    # search for existing record marching values
    where = []
    data = ()
    for field, value in values.items():
        if value:
            where += ['%s = %%s' % (field,)]
            data += (value,)
        else:
            where += ['%s IS NULL' % (field,)]
            data += ()

    query = ("SELECT id FROM %s WHERE " % table) + ' AND '.join(where)
    cr.execute(query, data)
    record = cr.fetchone()
    if not record:
        return None

    res_id = record[0]

    # update xmlid table
    if data_id:
        cr.execute("""UPDATE ir_model_data
                         SET res_id=%s
                       WHERE id=%s
                   """, (res_id, data_id))
    else:
        cr.execute("""INSERT INTO ir_model_data
                                  (module, name, model, res_id, noupdate)
                           VALUES (%s, %s, %s, %s, %s)
                   """, (module, name, model, res_id, True))

    return res_id

# -------- Announcement Message --------


_DEFAULT_HEADER = """
<p>{module} has been upgraded to version {version}.</p>
<h2>What's new in this upgrade?</h2>
"""

_DEFAULT_FOOTER = "<p>Enjoy this new version of {module}!</p>"

_DEFAULT_RECIPIENT = 'mail.channel_all_employees'


def announce(cr, module, version, msg, format='rst',
             recipient=_DEFAULT_RECIPIENT, header=_DEFAULT_HEADER, footer=_DEFAULT_FOOTER,
             pluses_for_enterprise=None):
    """
    Post an upgrade message in the selected channel detailing the upgrade.

        :param module: nmae of the upgraded module
        :param version: target upgrade version
        :param msg: message regarding the upgrade
        :param format='rst': format of the message
                             ('rst' for ReStructured Text or 'md' for markdown)
        :param recipient: xmlid of the channel where the message will be posted
        :param header: header of the message (set False for no header)
        :param footer: footer of the message (set False for no footer)
        :param pluses_for_enterprise=None: if True, list elements in your message
                                           prefixed with a '+ ' string will be
                                           filtered out if the upgraded database
                                           does not have the Enterprise edition
    """
    if pluses_for_enterprise:
        plus_re = r'^(\s*)\+ (.+)\n'
        replacement = r'\1- \2\n' if has_enterprise() else ''
        msg = re.sub(plus_re, replacement, msg, flags=re.M)

    # do not notify early, in case the migration fails halfway through
    ctx = {'mail_notify_force_send': False, 'mail_notify_author': True}

    try:
        registry = env(cr)
        user = registry['res.users'].browse(
            [SUPERUSER_ID])[0].with_context(ctx)

        def ref(xid):
            return registry.ref(xid).with_context(ctx)

    except MigrationError:
        registry = Registry.get(cr.dbname)
        user = registry['res.users'].browse(
            cr, SUPERUSER_ID, SUPERUSER_ID, context=ctx)

        def ref(xid):
            rmod, _, rxid = recipient.partition('.')
            return registry['ir.model.data'].get_object(cr, SUPERUSER_ID, rmod, rxid, context=ctx)

    # default recipient
    poster = user.message_post

    if recipient:
        try:
            poster = ref(recipient).message_post
        except (ValueError, AttributeError):
            # Cannot find record, post the message on the wall of the admin
            pass

    if format == 'rst':
        msg = _rst2html(msg)
    elif format == 'md':
        msg = _md2html(msg)

    message = ((header or "") + msg + (footer or "")
               ).format(module=module or 'Odoo', version=version)
    _logger.debug(message)

    type_field = 'message_type'
    kw = {type_field: 'notification'}

    try:
        poster(body=message, partner_ids=[
               user.partner_id.id], subtype='mail.mt_comment', **kw)
    except Exception:
        _logger.warning('Cannot announce message', exc_info=True)


#### NOT SURE IF STILL NEEDED ??? ####

def main(func, version=None):
    """a main() function for scripts"""
    # NOTE: this is not recommanded when the func callback use the ORM as the addon-path is
    # incomplete. Please pipe your script into `odoo shell`.
    # Do not forget to commit the cursor at the end.
    if len(sys.argv) != 2:
        sys.exit("Usage: %s <dbname>" % (sys.argv[0],))
    dbname = sys.argv[1]
    with db_connect(dbname).cursor() as cr, Environment.manage():
        func(cr, version)


def _ir_values_value(cr):
    # returns the casting from bytea to text needed in saas~17 for column `value` of `ir_values`
    # returns tuple(column_read, cast_write)
    result = getattr(_ir_values_value, 'result', None)

    if result is None:
        if column_type(cr, 'ir_values', 'value') == 'bytea':
            cr.execute(
                "SELECT character_set_name FROM information_schema.character_sets")
            charset, = cr.fetchone()
            column_read = "convert_from(value, '%s')" % charset
            cast_write = "convert_to(%%s, '%s')" % charset
        else:
            column_read = 'value'
            cast_write = '%s'
        _ir_values_value.result = result = (column_read, cast_write)

    return result


def chunks(iterable, size, fmt=None):
    """
    Split `iterable` into chunks of `size` and wrap each chunk
    using function 'fmt' (`iter` by default; join strings)

    >>> list(chunks(range(10), 4, fmt=tuple))
    [(0, 1, 2, 3), (4, 5, 6, 7), (8, 9)]
    >>> ' '.join(chunks('abcdefghijklm', 3))
    'abc def ghi jkl m'
    >>>

    """
    if fmt is None:
        fmt = ''.join

    it = iter(iterable)
    try:
        while True:
            yield fmt(chain((next(it),), islice(it, size - 1)))
    except StopIteration:
        return


def iter_browse(model, *args, **kw):
    """
    Iterate and browse through record without filling the cache.
    `args` can be `cr, uid, ids` or just `ids` depending on kind of `model` (old/new api)
    """
    assert len(args) in [1, 3]      # either (cr, uid, ids) or (ids,)
    cr_uid = args[:-1]
    ids = args[-1]
    chunk_size = kw.pop('chunk_size', 200)      # keyword-only argument
    logger = kw.pop('logger', _logger)
    if kw:
        raise TypeError('Unknow arguments: %s' % ', '.join(kw))

    def browse(ids):
        model.invalidate_cache(*cr_uid)
        args = cr_uid + (list(ids),)
        return model.browse(*args)

    def end():
        model.invalidate_cache(*cr_uid)
        if 0:
            yield

    it = chain.from_iterable(chunks(ids, chunk_size, fmt=browse))
    if logger:
        it = log_progress(it, qualifier=model._name,
                          logger=logger, size=len(ids))

    return chain(it, end())
