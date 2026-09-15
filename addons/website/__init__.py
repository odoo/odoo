from . import controllers
from . import models
from . import wizards

from odoo.http import request


def uninstall_hook(env):
    website_domain = [("website_id", "!=", False)]
    env["ir.asset"].search(website_domain).unlink()
    env["ir.ui.view"].search(website_domain).with_context(
        active_test=False, _force_unlink=True
    ).unlink()

    env["website"].search([])._remove_attachments_on_website_unlink()


def post_init_hook(env):
    if request:
        env = env(context=request.prepare_default_context())
        request.website_routing = env["website"].get_current_website().id
