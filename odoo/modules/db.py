# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2.extras import Json
import logging
from enum import IntEnum

import odoo.modules

_logger = logging.getLogger(__name__)

def is_initialized(cr):
    """ Check if a database has been initialized for the ORM.

    The database can be initialized with the 'initialize' function below.

    """
    return odoo.tools.table_exists(cr, 'ir_module_module')

def initialize(cr):
    """ Initialize a database with for the ORM.

    This executes base/data/base_data.sql, creates the ir_module_categories
    (taken from each module descriptor file), and creates the ir_module_module
    and ir_model_data entries.

    """
    try:
        f = odoo.tools.misc.file_path('base/data/base_data.sql')
    except FileNotFoundError:
        m = "File not found: 'base.sql' (provided by module 'base')."
        _logger.critical(m)
        raise IOError(m)

    with odoo.tools.misc.file_open(f) as base_sql_file:
        cr.execute(base_sql_file.read())  # pylint: disable=sql-injection

    for i in odoo.modules.get_modules():
        mod_path = odoo.modules.get_module_path(i)
        if not mod_path:
            continue

        # This will raise an exception if no/unreadable descriptor file.
        info = odoo.modules.get_manifest(i)

        if not info:
            continue
        categories = info['category'].split('/')
        category_id = create_categories(cr, categories)

        if info['installable']:
            state = 'uninstalled'
        else:
            state = 'uninstallable'

        cr.execute('INSERT INTO ir_module_module \
                (author, website, name, shortdesc, description, \
                    category_id, auto_install, state, web, license, application, icon, sequence, summary) \
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id', (
            info['author'],
            info['website'], i, Json({'en_US': info['name']}),
            Json({'en_US': info['description']}), category_id,
            info['auto_install'] is not False, state,
            info['web'],
            info['license'],
            info['application'], info['icon'],
            info['sequence'], Json({'en_US': info['summary']})))
        id = cr.fetchone()[0]
        cr.execute('INSERT INTO ir_model_data \
            (name,model,module, res_id, noupdate) VALUES (%s,%s,%s,%s,%s)', (
                'module_'+i, 'ir.module.module', 'base', id, True))
        dependencies = info['depends']
        for d in dependencies:
            cr.execute(
                'INSERT INTO ir_module_module_dependency (module_id, name, auto_install_required)'
                ' VALUES (%s, %s, %s)',
                (id, d, d in (info['auto_install'] or ()))
            )

    # Install recursively all auto-installing modules
    while True:
        # this selects all the auto_install modules whose auto_install_required
        # deps are marked as to install
        cr.execute("""
        SELECT m.name FROM ir_module_module m
        WHERE m.auto_install
        AND state not in ('to install', 'uninstallable')
        AND NOT EXISTS (
            SELECT 1 FROM ir_module_module_dependency d
            JOIN ir_module_module mdep ON (d.name = mdep.name)
            WHERE d.module_id = m.id
              AND d.auto_install_required
              AND mdep.state != 'to install'
        )""")
        to_auto_install = [x[0] for x in cr.fetchall()]
        # however if the module has non-required deps we need to install
        # those, so merge-in the modules which have a dependen*t* which is
        # *either* to_install or in to_auto_install and merge it in?
        cr.execute("""
        SELECT d.name FROM ir_module_module_dependency d
        JOIN ir_module_module m ON (d.module_id = m.id)
        JOIN ir_module_module mdep ON (d.name = mdep.name)
        WHERE (m.state = 'to install' OR m.name = any(%s))
            -- don't re-mark marked modules
        AND NOT (mdep.state = 'to install' OR mdep.name = any(%s))
        """, [to_auto_install, to_auto_install])
        to_auto_install.extend(x[0] for x in cr.fetchall())

        if not to_auto_install: break
        cr.execute("""UPDATE ir_module_module SET state='to install' WHERE name in %s""", (tuple(to_auto_install),))

def create_categories(cr, categories):
    """ Create the ir_module_category entries for some categories.

    categories is a list of strings forming a single category with its
    parent categories, like ['Grand Parent', 'Parent', 'Child'].

    Return the database id of the (last) category.

    """
    p_id = None
    category = []
    while categories:
        category.append(categories[0])
        xml_id = 'module_category_' + ('_'.join(x.lower() for x in category)).replace('&', 'and').replace(' ', '_')
        # search via xml_id (because some categories are renamed)
        cr.execute("SELECT res_id FROM ir_model_data WHERE name=%s AND module=%s AND model=%s",
                   (xml_id, "base", "ir.module.category"))

        c_id = cr.fetchone()
        if not c_id:
            cr.execute('INSERT INTO ir_module_category \
                    (name, parent_id) \
                    VALUES (%s, %s) RETURNING id', (Json({'en_US': categories[0]}), p_id))
            c_id = cr.fetchone()[0]
            cr.execute('INSERT INTO ir_model_data (module, name, res_id, model, noupdate) \
                       VALUES (%s, %s, %s, %s, %s)', ('base', xml_id, c_id, 'ir.module.category', True))
        else:
            c_id = c_id[0]
        p_id = c_id
        categories = categories[1:]
    return p_id

class FunctionStatus(IntEnum):
    MISSING = 0  # function is not present (falsy)
    PRESENT = 1  # function is present but not indexable (not immutable)
    INDEXABLE = 2  # function is present and indexable (immutable)

def has_unaccent(cr):
    """ Test whether the database has function 'unaccent' and return its status.

    The unaccent is supposed to be provided by the PostgreSQL unaccent contrib
    module but any similar function will be picked by OpenERP.

    :rtype: FunctionStatus
    """
    cr.execute("""
        SELECT p.provolatile
        FROM pg_proc p
            LEFT JOIN pg_catalog.pg_namespace ns ON p.pronamespace = ns.oid
        WHERE p.proname = 'unaccent'
              AND p.pronargs = 1
              AND ns.nspname = 'public'
    """)
    result = cr.fetchone()
    if not result:
        return FunctionStatus.MISSING
    # The `provolatile` of unaccent allows to know whether the unaccent function
    # can be used to create index (it should be 'i' - means immutable), see
    # https://www.postgresql.org/docs/current/catalog-pg-proc.html.
    return FunctionStatus.INDEXABLE if result[0] == 'i' else FunctionStatus.PRESENT

def has_trigram(cr):
    """ Test if the database has the a word_similarity function.

    The word_similarity is supposed to be provided by the PostgreSQL built-in
    pg_trgm module but any similar function will be picked by Odoo.

    """
    cr.execute("SELECT proname FROM pg_proc WHERE proname='word_similarity'")
    return len(cr.fetchall()) > 0
