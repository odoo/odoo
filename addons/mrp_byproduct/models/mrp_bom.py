# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class mrp_bom(osv.osv):
    _name = 'mrp.bom'
    _description = 'Bill of Material'
    _inherit='mrp.bom'

    _columns={
        'sub_products':fields.one2many('mrp.subproduct', 'bom_id', 'Byproducts', copy=True),
    }