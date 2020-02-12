# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard


from odoo import api, SUPERUSER_ID


# TODO: Apply proper fix & remove in master
def pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.model.data'].search([
        ('model', 'like', '%stock%'),
        ('module', '=', 'stock')
    ]).unlink()

def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    default = env['product.template']._fields['type'].default(env['product.template'])
    def _reset_product_template_type():
        # stock introduces an option on the `type` Selection field of `product.template`
        # if this module is uninstalled and any `product.template` record still points to this option
        # the registry will find itself in an unstable state and will most likely crash (eventually)
        cr.execute("UPDATE product_template SET type = %s WHERE type = %s", (default, 'product'))
    cr.after('commit', _reset_product_template_type)
