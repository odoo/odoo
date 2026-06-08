# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

from odoo.http import request


def uninstall_hook(env):
    # Force remove ondelete='cascade' elements,
    # This might be prevented by another ondelete='restrict' field
    # TODO: This should be an Odoo generic fix, not a website specific one
    website_domain = [('website_id', '!=', False)]
    env['ir.asset'].search(website_domain).unlink()
    env['ir.ui.view'].search(website_domain).with_context(active_test=False, force_delete=True).unlink()

    # Cleanup records which are related to websites and will not be autocleaned
    # by the uninstall operation. This must be done here in the uninstall_hook
    # as during an uninstallation, `unlink` is not called for records which were
    # created by the user (not XML data). Same goes for @api.ondelete available
    # from 15.0 and above.
    env['website'].search([])._remove_attachments_on_website_unlink()


def post_init_hook(env):
    env.cr.execute("UPDATE website SET default_lang_id=%s", (env['website']._default_language(),))
    lang_ids = env['website']._active_languages()
    websites = env['website'].search([])

    for website in websites:
        website.language_ids = lang_ids
        website.company_id._compute_website_id()
        website._bootstrap_homepage()

    if not env.user.has_group('website.group_multi_website') and len(websites) > 1:
        all_user_groups = 'base.group_portal,base.group_user,base.group_public'
        groups = env['res.groups'].concat(env.ref(it) for it in all_user_groups.split(','))
        groups.write({'implied_ids': [(4, env.ref('website.group_multi_website').id)]})

    if request:
        env = env(context=request.default_context())
        request.update_context(website_id=env.website.id)
