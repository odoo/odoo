# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial
import odoo
from odoo import api, SUPERUSER_ID

from . import models      # noqa
from . import report      # noqa


def uninstall_hook(cr, registry):
    def recreate_view(dbname):
        db_registry = odoo.modules.registry.Registry.new(dbname)
        with api.Environment.manage(), db_registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            if 'sale.report' in env:
                env['sale.report'].init()

    cr.after("commit", partial(recreate_view, cr.dbname))
