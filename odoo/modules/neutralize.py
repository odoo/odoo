# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import logging
from contextlib import suppress

_logger = logging.getLogger(__name__)

def get_installed_modules(cursor):
    """
    Retrieves the list of installed modules or those pending update/removal.
    Optimization: Use of a single SQL query.
    """
    cursor.execute('''
        SELECT name
          FROM ir_module_module
         WHERE state IN ('installed', 'to upgrade', 'to remove');
    ''')
    return [row[0] for row in cursor.fetchall()]


def get_neutralization_queries(modules):
    """
    Generates neutralization queries for the installed modules.
    Optimization: Use of suppress with logging for missing files.
    """
    for module in modules:
        filename = f'{module}/data/neutralize.sql'
        with suppress(FileNotFoundError):
            try:
                with odoo.tools.misc.file_open(filename) as file:
                    query = file.read().strip()
                    if query:
                        yield query
            except Exception as e:
                _logger.warning(f"Error reading neutralization file for module {module}: {e}")


def neutralize_database(cursor):
    """
    Executes neutralization queries for each installed module.
    Optimization: Batch the queries to reduce multiple database calls.
    """
    installed_modules = get_installed_modules(cursor)
    queries = get_neutralization_queries(installed_modules)

    batch_queries = []
    for query in queries:
        batch_queries.append(query)

    if batch_queries:
        cursor.execute(';'.join(batch_queries))  # Batch query execution

    _logger.info("Neutralization finished")
