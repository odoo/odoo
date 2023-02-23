# -*- coding: utf-8 -*-

from . import models

def _create_picking_seq(env):
    ptypes = env['stock.picking.type'].search([('code', '=', 'outgoing'), ('warehouse_id', '!=', False)])
    for ptype in ptypes:
        wh = ptype.warehouse_id
        ptype.l10n_it_ddt_sequence_id = env['ir.sequence'].create({
        'name': wh.name + ' ' + ' Sequence ' + ' ' + ptype.sequence_code,
        'prefix': wh.code + '/' + ptype.sequence_code + '/DDT', 'padding': 5,
        'company_id': wh.company_id.id,
        'implementation': 'no_gap',
    }).id
