# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

class account_invoice(osv.osv):

    _inherit = 'account.invoice'
    _columns = {
        'category_id': fields.many2one('account.asset.category', 'Asset category', required=True, change_default=True, readonly=True, states={'draft':[('readonly',False)]}),
    }
    def line_get_convert(self, cr, uid, x, part, date, context=None):
        res = super(account_invoice, self).line_get_convert(cr, uid, x, part, date, context=context)
        res['asset_id'] = x.get('asset_id', False)
        return res

account_invoice()

class account_invoice_line(osv.osv):

    _inherit = 'account.invoice.line'
    _columns = {
        'asset_category_id': fields.many2one('account.asset.category', 'Asset Category'),
    }

    def move_line_get_item(self, cr, uid, line, context=None):
        asset_obj = self.pool.get('account.asset.asset')
        res = super(account_invoice_line, self).move_line_get_item(cr, uid, line, context=context)
        if line.invoice_id and line.invoice_id.type not in ('out_invoice', 'out_refund') and line.asset_category_id:
                vals = {
                    'name': line.product_id and (line.name + ": " + line.product_id.name) or line.name,
                    'category_id': line.asset_category_id.id,
                    'purchase_value': line.price_subtotal,
                    'period_id': line.invoice_id.period_id.id,
                    'partner_id': line.invoice_id.partner_id.id,
                    'company_id': line.invoice_id.company_id.id,
                    'currency_id': line.invoice_id.currency_id.id,
                }
                asset_id = asset_obj.create(cr, uid, vals, context=context)
                if line.asset_category_id.open_asset:
                    asset_obj.validate(cr, uid, [asset_id], context=context)
        return res

account_invoice_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
