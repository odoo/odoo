# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard
from . import report
from odoo import api, SUPERUSER_ID


def _set_product_image_ids(cr, registry):
    '''Write the default product_image_ids on product.template and
       product_product_ids on product.product
    '''
    env = api.Environment(cr, SUPERUSER_ID, {})

    for template in env['product.template'].search([('image', '!=', False)]):
        env['product.image'].create({'image': template.image, 'product_tmpl_id': template.id, 'name': template.name, 'sequence': 0})

    for product in env['product.product'].search([('image_variant', '!=', False)]):
        env['product.image'].create({'image': product.image, 'product_product_id': product.id, 'name': product.name, 'sequence': 0})
