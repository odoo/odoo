# -*- coding: utf-8 -*-
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
import netsvc
import time

class sale_journal_invoice_type(osv.osv):
    _name = 'sale_journal.invoice.type'
    _description = 'Invoice Types'
    _columns = {
        'name': fields.char('Invoice Type', size=64, required=True),
        'active': fields.boolean('Active', help="If the active field is set to true, it will allow you to hide the invoice type without removing it."),
        'note': fields.text('Note'),
        'invoicing_method': fields.selection([('simple','Non grouped'),('grouped','Grouped')], 'Invoicing method', required=True),
    }
    _defaults = {
        'active': lambda *a: True,
        'invoicing_method': lambda *a:'simple'
    }
sale_journal_invoice_type()

class sale_journal(osv.osv):
    _name = 'sale_journal.sale.journal'
    _description = 'Sale Journal'
    _columns = {
        'name': fields.char('Journal', size=64, required=True),
        'code': fields.char('Code', size=16, required=True),
        'user_id': fields.many2one('res.users', 'Responsible', required=True),
        'date': fields.date('Journal date', required=True),
        'date_created': fields.date('Creation date', readonly=True, required=True),
        'date_validation': fields.date('Validation date', readonly=True),
        'sale_stats_ids': fields.one2many("sale.journal.report", "journal_id", 'Sale Stats', readonly=True),
        'state': fields.selection([
            ('draft','Draft'),
            ('open','Open'),
            ('done','Done'),
        ], 'State', required=True),
        'note': fields.text('Note'),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'date_created': lambda *a: time.strftime('%Y-%m-%d'),
        'user_id': lambda self,cr,uid,context: uid,
        'state': lambda self,cr,uid,context: 'draft',
    }
    def button_sale_cancel(self, cr, uid, ids, context={}):
        for id in ids:
            sale_ids = self.pool.get('sale.order').search(cr, uid, [('journal_id','=',id),('state','=','draft')])
            for saleid in sale_ids:
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'sale.order', saleid, 'cancel', cr)
        return True
    def button_sale_confirm(self, cr, uid, ids, context={}):
        for id in ids:
            sale_ids = self.pool.get('sale.order').search(cr, uid, [('journal_id','=',id),('state','=','draft')])
            for saleid in sale_ids:
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'sale.order', saleid, 'order_confirm', cr)
        return True

    def button_open(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'open'})
        return True
    def button_draft(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'draft'})
        return True
    def button_close(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'done', 'date_validation':time.strftime('%Y-%m-%d')})
        return True
sale_journal()

class picking_journal(osv.osv):
    _name = 'sale_journal.picking.journal'
    _description = 'Picking Journal'
    _columns = {
        'name': fields.char('Journal', size=64, required=True),
        'code': fields.char('Code', size=16, required=True),
        'user_id': fields.many2one('res.users', 'Responsible', required=True),
        'date': fields.date('Journal date', required=True),
        'date_created': fields.date('Creation date', readonly=True, required=True),
        'date_validation': fields.date('Validation date', readonly=True),
        'picking_stats_ids': fields.one2many("sale.journal.picking.report", "journal_id", 'Journal Stats', readonly=True),
        'state': fields.selection([
            ('draft','Draft'),
            ('open','Open'),
            ('done','Done'),
        ], 'Creation date', required=True),
        'note': fields.text('Note'),
    }
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d'),
        'date_created': lambda *a: time.strftime('%Y-%m-%d'),
        'user_id': lambda self,cr,uid,context: uid,
        'state': lambda self,cr,uid,context: 'draft',
    }
    def button_picking_cancel(self, cr, uid, ids, context={}):
        for id in ids:
            pick_ids = self.pool.get('stock.picking').search(cr, uid, [('journal_id','=',id)])
            for pickid in pick_ids:
                wf_service = netsvc.LocalService("workflow")
                wf_service.trg_validate(uid, 'stock.picking', pickid, 'button_cancel', cr)
        return True
    def button_open(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'open'})
        return True
    def button_draft(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'draft'})
        return True
    def button_close(self, cr, uid, ids, context={}):
        self.write(cr, uid, ids, {'state':'done', 'date_validation':time.strftime('%Y-%m-%d')})
        return True
picking_journal()

#==============================================
# sale journal inherit
#==============================================

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'property_invoice_type': fields.property(
        'sale_journal.invoice.type',
        type='many2one',
        relation='sale_journal.invoice.type',
        string="Invoicing Method",
        method=True,
        view_load=True,
        group_name="Accounting Properties",
        help="The type of journal used for sales and picking."),
    }
res_partner()

class picking(osv.osv):
    _inherit="stock.picking"
    _columns = {
        'journal_id': fields.many2one('sale_journal.picking.journal', 'Journal'),
        'sale_journal_id': fields.many2one('sale_journal.sale.journal', 'Sale Journal'),
        'invoice_type_id': fields.many2one('sale_journal.invoice.type', 'Invoice Type', readonly=True)
    }
picking()

class sale(osv.osv):
    _inherit="sale.order"
    _columns = {
        'journal_id': fields.many2one('sale_journal.sale.journal', 'Journal'),
        'invoice_type_id': fields.many2one('sale_journal.invoice.type', 'Invoice Type')
    }
    def action_ship_create(self, cr, uid, ids, *args):
        result = super(sale, self).action_ship_create(cr, uid, ids, *args)
        for order in self.browse(cr, uid, ids, context={}):
            pids = [ x.id for x in order.picking_ids]
            self.pool.get('stock.picking').write(cr, uid, pids, {
                'invoice_type_id': order.invoice_type_id.id,
                'sale_journal_id': order.journal_id.id
            })
        return result

    def onchange_partner_id(self, cr, uid, ids, part):
        result = super(sale, self).onchange_partner_id(cr, uid, ids, part)
        if part:
            itype = self.pool.get('res.partner').browse(cr, uid, part).property_invoice_type.id
            result['value']['invoice_type_id'] = itype
        return result
sale()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
