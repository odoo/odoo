# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID
from openerp.osv import orm


class website(orm.Model):
    _inherit = 'website'

    def _prepare_sale_order_values(self, cr, uid, w, partner, pricelist, context=None):
        values = super(website, self)._prepare_sale_order_values(cr, uid, w, partner, pricelist, context=context)
        if values['company_id']:
            warehouse_ids = self.pool['stock.warehouse'].search(cr, SUPERUSER_ID, [('company_id', '=', values['company_id'])], context=context)
            if warehouse_ids:
                values['warehouse_id'] = warehouse_ids[0]
        return values
