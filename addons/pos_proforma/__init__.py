# -*- coding: utf-8 -*-

from odoo import api, tools, _, SUPERUSER_ID
from . import models


def _init_ir_sequence_on_config(env):
    pos_configs = env['pos.config'].search([])
    IrSequence = env['ir.sequence'].sudo()

    for config in pos_configs:
        val = {
            'name': _('POS Profo Order %s', config['name']),
            'padding': 4,
            'prefix': "Profo %s/" % config['name'],
            'code': "pos.order_pro_forma",
            'company_id': config['company_id'].id,
        }
        config['profo_sequence_id'] = IrSequence.create(val).id
