# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from .utils import _format_carrier_name
from odoo import api, SUPERUSER_ID, _

def create_pos_onsite_carriers(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    pos_configs = env['pos.config'].with_context(active_test=False).search([])
    product = env.ref('payment_onsite.onsite_delivery_product')

    delivery_carriers = env['delivery.carrier'].create([{
        'name': _format_carrier_name(pos_config.name),
        'product_id': product.id,
        'delivery_type': 'onsite'
    } for pos_config in pos_configs])

    for carrier, pos in zip(delivery_carriers, pos_configs):
        pos.sudo().write({
            'delivery_carrier_id': carrier.id
        })
    acquirer_onsite = env.ref('payment_onsite.payment_acquirer_onsite')
    acquirer_onsite.carrier_ids |= delivery_carriers
