# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment import reset_payment_acquirer
from odoo.addons.payment.models.payment_acquirer import create_missing_journals


from . import models
from . import controllers


def post_init_hook(cr, registry):
    # This little hack is normally not necessary but it is here used to fix the following behavior:
    # If the acquirer module is installed manually (through the INSTALL button), the method set as
    # post-init hook in the manifest would be called as expected and it would create a new journal
    # for the acquirer. However, when the acquirer module is installed through the -i option of
    # odoo-bin, the post-init hook would not be triggered if it is an imported function. This
    # locally defined function temporarily fix this behavior while waiting for a proper fix.
    create_missing_journals(cr, registry)

def uninstall_hook(cr, registry):
    reset_payment_acquirer(cr, registry, 'test')
