# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID
from odoo.http import request


def uninstall_hook(env):
    # Force remove ondelete='cascade' elements,
    # This might be prevented by another ondelete='restrict' field
    # TODO: This should be an Odoo generic fix, not a website specific one
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
    @env.cr.postcommit.add
    def rem_website_id_null():
        with env.new_transaction(uid=SUPERUSER_ID, context={}) as nenv:
            nenv['ir.model.fields'].search([
                ('name', '=', 'website_id'),
                ('model', '=', 'res.config.settings'),
            ]).unlink()


def post_init_hook(env):
    env['ir.module.module'].update_theme_images()

    if request:
        env = env(context=request.default_context())
        request.website_routing = env['website'].get_current_website().id
