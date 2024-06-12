# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard


def _assign_default_sms_template_picking_id(env):
    company_ids_without_default_sms_template_id = env['res.company'].search([
        ('stock_sms_confirmation_template_id', '=', False)
    ])
    default_sms_template_id = env.ref('stock_sms.sms_template_data_stock_delivery', raise_if_not_found=False)
    if default_sms_template_id:
        company_ids_without_default_sms_template_id.write({
            'stock_sms_confirmation_template_id': default_sms_template_id.id,
        })
