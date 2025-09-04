# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import psycopg2

from odoo import tools

from . import models
from . import wizard


def pgvector_is_available(env):
    try:
        with tools.mute_logger('odoo.sql_db'), env.cr.savepoint():
            env.cr.execute(tools.SQL("CREATE EXTENSION IF NOT EXISTS vector"))
        return True
    except Exception:  # noqa: BLE001
        return False


def _auto_install_apps(env):
    modules_to_install = []
    if tools.config.get('default_productivity_apps', False):
        modules_to_install.extend([
            # Community
            'hr', 'mass_mailing', 'project', 'survey',
            # Enterprise
            'appointment', 'knowledge', 'planning', 'sign',
        ])

    if pgvector_is_available(env):
        modules_to_install.append('ai')

    if modules_to_install:
        env['ir.module.module'].sudo().search([
            ('name', 'in', modules_to_install),
            ('state', '=', 'uninstalled')
        ]).button_install()
