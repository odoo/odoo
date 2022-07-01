# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from odoo import api, SUPERUSER_ID


def _create_repair_picking_type(cr, registry):
    """ This hook is used to add a default repair picking_type on every warehouses.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    for wh in env['stock.warehouse'].search([]):
        wh._create_or_update_sequences_and_picking_types()
