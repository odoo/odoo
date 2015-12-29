# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval as eval
import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_round
from openerp.exceptions import UserError


class product_template(osv.osv):
    _name = 'product.template'
    _inherit = 'product.template'

    _columns = {
        'location_id': fields.dummy(string='Location', relation='stock.location', type='many2one'),
        'warehouse_id': fields.dummy(string='Warehouse', relation='stock.warehouse', type='many2one'),
    }
