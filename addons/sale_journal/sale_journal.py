# -*- coding: utf-8 -*-
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
import netsvc
import time

class sale_journal_invoice_type(osv.osv):
    _name = 'sale_journal.invoice.type'
    _description = 'Invoice Types'
    _columns = {
        'name': fields.char('Invoice Type', size=64, required=True),
        'active': fields.boolean('Active'),
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
        'sale_stats_ids': fields.one2many("sale_journal.sale.stats", "journal_id", 'Sale Stats', readonly=True),
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
    _description = 'Packing Journal'
    _columns = {
        'name': fields.char('Journal', size=64, required=True),
        'code': fields.char('Code', size=16, required=True),
        'user_id': fields.many2one('res.users', 'Responsible', required=True),
        'date': fields.date('Journal date', required=True),
        'date_created': fields.date('Creation date', readonly=True, required=True),
        'date_validation': fields.date('Validation date', readonly=True),
        'picking_stats_ids': fields.one2many("sale_journal.picking.stats", "journal_id", 'Journal Stats', readonly=True),
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

