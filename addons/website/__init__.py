# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

import odoo
from odoo import api, SUPERUSER_ID
from odoo.http import request
from functools import partial


def uninstall_hook(cr, registry):
    # Force remove ondelete='cascade' elements,
    # This might be prevented by another ondelete='restrict' field
    # TODO: This should be an Odoo generic fix, not a website specific one
    env = api.Environment(cr, SUPERUSER_ID, {})
    website_domain = [('website_id', '!=', False)]
    env['ir.asset'].search(website_domain).unlink()
    env['ir.ui.view'].search(website_domain).with_context(active_test=False, _force_unlink=True).unlink()

    # Cleanup records which are related to websites and will not be autocleaned
    # by the uninstall operation. This must be done here in the uninstall_hook
    # as during an uninstallation, `unlink` is not called for records which were
    # created by the user (not XML data). Same goes for @api.ondelete available
    # from 15.0 and above.
    env['website'].search([])._remove_attachments_on_website_unlink()

    # Properly unlink website_id from ir.model.fields
    def rem_website_id_null(dbname):
        db_registry = odoo.modules.registry.Registry.new(dbname)
        with db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['ir.model.fields'].search([
                ('name', '=', 'website_id'),
                ('model', '=', 'res.config.settings'),
            ]).unlink()

    cr.postcommit.add(partial(rem_website_id_null, cr.dbname))


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    if request:
        env = env(context=request.default_context())
        request.website_routing = env['website'].get_current_website().id
