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

def _assign_default_mail_template_picking_id(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    company_ids_without_default_mail_template_id = env['res.company'].search([
        ('stock_mail_confirmation_template_id', '=', False)
    ])
    default_mail_template_id = env.ref('stock.mail_template_data_delivery_confirmation', raise_if_not_found=False)
    if default_mail_template_id:
        company_ids_without_default_mail_template_id.write({
            'stock_mail_confirmation_template_id': default_mail_template_id.id,
        })


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    default = env['product.template']._fields['type'].default(env['product.template'])
    # stock introduces an option on the `type` Selection field of `product.template`
    # if this module is uninstalled and any `product.template` record still points to this option
    # the registry will find itself in an unstable state and will most likely crash (eventually)
    cr.execute("UPDATE product_template SET type = %s WHERE type = %s", (default, 'product'))
