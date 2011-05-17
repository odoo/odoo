# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

from osv import osv, fields
import time

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
    def line_get_convert(self, cr, uid, x, part, date, context={}):
        res = super(account_invoice, self).line_get_convert(cr, uid, x, part, date, context)
        res['asset_category_id'] = x.get('asset_category_id', False)
        return res
account_invoice()

class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'
    _columns = {
        'asset_category_id': fields.many2one('account.asset.category', 'Asset Category'),
    }
    def move_line_get_item(self, cr, uid, line, context={}):
        res = super(account_invoice_line, self).move_line_get_item(cr, uid, line, context)
        res['asset_category_id'] = line.asset_category_id.id or False
        asset_obj = self.pool.get('account.asset.asset')
        if line.asset_category_id.id:
            vals = {
                'name': line.name + ": " + (line.product_id and line.product_id.name),
                'category_id': line.asset_category_id.id,
                'purchase_value': line.price_subtotal
            }
            asset_id = asset_obj.create(cr, uid, vals, context=context)
            if line.asset_category_id.skip_draft_state:
                asset_obj.validate(cr, uid, [asset_id], context=context)
        return res
account_invoice_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

