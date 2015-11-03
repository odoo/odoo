# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp


class sale_order_line(osv.Model):
    _inherit = "sale.order.line"

    def _fnct_get_discounted_price(self, cr, uid, ids, field_name, args, context=None):
        res = dict.fromkeys(ids, False)
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = (line.price_unit * (1.0 - (line.discount or 0.0) / 100.0))
        return res

    _columns = {
        'discounted_price': fields.function(_fnct_get_discounted_price, string='Discounted price', type='float', digits_compute=dp.get_precision('Product Price')),
    }
