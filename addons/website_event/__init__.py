# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

import odoo
from odoo import api, SUPERUSER_ID
from functools import partial

def uninstall_hook(cr, registry):
    def delete_event_is_published(dbname):
        db_registry = odoo.modules.registry.Registry.new(dbname)
        with api.Environment.manage(), db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['ir.model.fields'].search([
                ('model', '=', 'event.event'),
                ('name', '=', 'is_published'),
            ]).with_context(_force_unlink=True).unlink()
    cr.after('commit', partial(delete_event_is_published, cr.dbname))

