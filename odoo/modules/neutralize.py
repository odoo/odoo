# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import logging
from contextlib import suppress

_logger = logging.getLogger(__name__)

def get_installed_modules(cursor):
    """
    Récupère la liste des modules installés ou en attente de mise à jour/suppression.
    Optimisation : Utilisation d'une seule requête SQL.
    """
    cursor.execute('''
        SELECT name
          FROM ir_module_module
         WHERE state IN ('installed', 'to upgrade', 'to remove');
    ''')
    return [row[0] for row in cursor.fetchall()]


def get_neutralization_queries(modules):
    """
    Génère les requêtes de neutralisation pour les modules installés.
    Optimisation : Utilisation de suppress avec logging pour les fichiers manquants.
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
    Exécute les requêtes de neutralisation pour chaque module installé.
    Optimisation : Regroupement des requêtes pour réduire les appels multiples à la base de données.
    """
    installed_modules = get_installed_modules(cursor)
    queries = get_neutralization_queries(installed_modules)

    batch_queries = []
    for query in queries:
        batch_queries.append(query)

    if batch_queries:
        cursor.execute(';'.join(batch_queries))  # Exécution groupée des requêtes

    _logger.info("Neutralization finished")
