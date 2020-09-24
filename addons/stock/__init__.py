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

def _create_warehouse(cr, registry):
    """ This hook is used to add a warehouse on existing companies
    when module stock is installed.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    company_ids  = env['res.company'].search([])
    company_with_warehouse = env['stock.warehouse'].search([]).mapped('company_id')
    company_without_warehouse = company_ids - company_with_warehouse
    for company in company_without_warehouse:
        company.create_transit_location()
        env['stock.warehouse'].create({
            'name': company.name,
            'code': company.name[:5],
            'company_id': company.id,
            'partner_id': company.partner_id.id
        })


def uninstall_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    default = env['product.template']._fields['type'].default(env['product.template'])
    def _reset_product_template_type():
        # stock introduces an option on the `type` Selection field of `product.template`
        # if this module is uninstalled and any `product.template` record still points to this option
        # the registry will find itself in an unstable state and will most likely crash (eventually)
        cr.execute("UPDATE product_template SET type = %s WHERE type = %s", (default, 'product'))
    cr.after('commit', _reset_product_template_type)
