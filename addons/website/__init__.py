# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

from odoo.http import request
from odoo.tools.safe_eval import safe_whitelist


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
    if request:
        env = env(context=request.default_context())
        request.website_routing = env['website'].get_current_website().id


safe_whitelist.add_instance('odoo.addons.website.controllers.main.QueryURL')
safe_whitelist.add_function('odoo.addons.website.controllers.model_page.ModelPageController.generic_model.<locals>.*')
safe_whitelist.add_function('odoo.addons.website.models.ir_qweb.IrQweb._prepare_frontend_environment.<locals>.*')
