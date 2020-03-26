# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

import odoo
from odoo import api, SUPERUSER_ID


def uninstall_hook(cr, registry):
    dbname = cr.dbname

    @cr.postcommit
    def rem_website_id_null():
        db_registry = odoo.modules.registry.Registry.new(dbname)
        with api.Environment.manage(), db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['ir.model.fields'].search([
                ('name', '=', 'website_id'),
                ('model', '=', 'res.config.settings'),
            ]).unlink()


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.module.module'].update_theme_images()
