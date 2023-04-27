# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

import odoo
from odoo import api, SUPERUSER_ID
from functools import partial


def uninstall_hook(cr, registry):
    # Cleanup records which are related to websites and will not be autocleaned
    # by the uninstall operation. This must be done here in the uninstall_hook
    # as during an uninstallation, `unlink` is not called for records which were
    # created by the user (not XML data). Same goes for @api.ondelete available
    # from 15.0 and above.
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['website'].search([])._remove_attachments_on_website_unlink()

    # Properly unlink website_id from ir.model.fields
    def rem_website_id_null(dbname):
        db_registry = odoo.modules.registry.Registry.new(dbname)
        with api.Environment.manage(), db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['ir.model.fields'].search([
                ('name', '=', 'website_id'),
                ('model', '=', 'res.config.settings'),
            ]).unlink()

    cr.postcommit.add(partial(rem_website_id_null, cr.dbname))


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.module.module'].update_theme_images()
