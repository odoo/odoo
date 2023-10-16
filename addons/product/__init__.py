# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import populate
from . import report
from . import wizard


def _set_default_pricelists(env):
    """Set the default pricelists for existing companies in case multicurrency has been enabled before the product module.
    E.g. when using demo localization module.
    """
    if env.user.user_has_groups("base.group_multi_currency"):
        group_user = env.ref("base.group_user").sudo()
        group_user._apply_group(env.ref("product.group_product_pricelist"))
        env["res.company"]._activate_or_create_pricelists()
