# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from openerp.osv import fields, osv

import openerp.addons.product.product


class ean_wizard(osv.osv_memory):
    _name = 'pos.ean_wizard'
    _columns = {
        'ean13_pattern': fields.char('Reference', size=13, required=True, translate=True),
    }

    def sanitize_ean13(self, cr, uid, ids, context):
        for r in self.browse(cr,uid,ids):
            ean13 = openerp.addons.product.product.sanitize_ean13(r.ean13_pattern)
            m = context.get('active_model')
            m_id =  context.get('active_id')
            self.pool[m].write(cr,uid,[m_id],{'barcode':ean13})
        return { 'type' : 'ir.actions.act_window_close' }
