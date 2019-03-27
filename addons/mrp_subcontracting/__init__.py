# -*- coding: utf-8 -*-

from . import models
from odoo import api, SUPERUSER_ID

def _create_subcontracting_rules(cr, registry):
    """ This hook is used to add the default subcontracting rules on every warehouse/company. It is
    necessary if the mrp_subcontracting module is installed after some warehouses
    were already created.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    warehouse_ids = env['stock.warehouse'].search(['|', ('subcontracting_mto_pull_id', '=', False), ('subcontracting_pull_id', '=', False)])
    for warehouse_id in warehouse_ids:
        warehouse_id.write({'subcontracting_to_resupply': warehouse_id.subcontracting_to_resupply})
    company_ids = env['res.company'].search([('subcontracting_location_id', '!=', False)])
    for company_id in company_ids:
        wh = env['stock.warehouse'].search([('company_id', '=', company_id.id), ('active', '=', True)], limit=1)
        production_location = wh._get_production_location()
        rsoo_rule = env['stock.rule'].search([
            ('location_src_id', '=', company_id.subcontracting_location_id.id),
            ('location_id', '=', production_location.id),
            ('picking_type_id', '=', wh.manu_type_id.id)
        ])
        if not rsoo_rule:
            company_id._create_resupply_subcontractor_rules()
