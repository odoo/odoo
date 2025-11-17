# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from . import controllers
from . import models
from . import report
from . import wizard


# TODO: Apply proper fix & remove in master
def pre_init_hook(env):
    env['ir.model.data'].search([
        ('model', 'like', 'stock'),
        ('module', '=', 'stock')
    ]).unlink()


def post_init_hook(env):
    _assign_default_mail_template_picking_id(env)
    _create_inventory_adjustment(env)


def uninstall_hook(env):
    picking_type_ids = env["stock.picking.type"].with_context({"active_test": False}).search([])
    picking_type_ids.sequence_id.unlink()


def _assign_default_mail_template_picking_id(env):
    company_ids_without_default_mail_template_id = env['res.company'].search([
        ('stock_mail_confirmation_template_id', '=', False)
    ])
    default_mail_template_id = env.ref('stock.mail_template_data_delivery_confirmation', raise_if_not_found=False)
    if default_mail_template_id:
        company_ids_without_default_mail_template_id.write({
            'stock_mail_confirmation_template_id': default_mail_template_id.id,
        })


def _create_inventory_adjustment(env):
    env.cr.execute("""SELECT id, qty_available FROM product_product WHERE qty_available IS NOT NULL;""")
    products = env.cr.fetchall()
    qty_available_by_company = defaultdict(lambda: defaultdict(float))
    for product_id, qty_available in products:
        for company_id, quantity in qty_available.items():
            qty_available_by_company[int(company_id)][product_id] = quantity

    for company_id, qty_available in qty_available_by_company.items():
        inventory_quant_vals = []
        location = env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1).lot_stock_id
        # Maybe we should automatically create a warehouse for them?
        if not location:
            continue
        for product, quantity in qty_available.items():
            inventory_quant_vals.append({
                'product_id': product,
                'inventory_quantity': quantity,
                'location_id': location.id,
            })
        env['stock.quant'].create(inventory_quant_vals)._apply_inventory()
