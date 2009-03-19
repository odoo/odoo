# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

##############################################################################
#
# Copyright (c) 2007 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields,osv
from osv import orm
import time

class account_analytic_default(osv.osv):
    _name = 'account.analytic.default'
    _description = 'Analytic Distributions'
    _rec_name = 'analytic_id'
    _order = 'sequence'
    _columns = {
        'sequence': fields.integer('Sequence'),
        'analytic_id': fields.many2one('account.analytic.account', 'Analytic Account'),
        'product_id': fields.many2one('product.product', 'Product', ondelete='cascade'),
        'partner_id': fields.many2one('res.partner', 'Partner', ondelete='cascade'),
        'user_id': fields.many2one('res.users', 'User', ondelete='cascade'),
        'company_id': fields.many2one('res.company', 'Company', ondelete='cascade'),
        'date_start': fields.date('Start Date'),
        'date_stop': fields.date('End Date'),
    }
    def account_get(self, cr, uid, product_id=None, partner_id=None, user_id=None, date=None, context={}):
        domain = []
        if product_id:
            domain += ['|',('product_id','=',product_id)]
        domain += [('product_id','=',False)]
        if partner_id:
            domain += ['|',('partner_id','=',partner_id)]
        domain += [('partner_id','=',False)]
        if user_id:
            domain += ['|',('user_id','=',uid)]
        domain += [('user_id','=',False)]
        if date:
            domain += ['|',('date_start','<=',date),('date_start','=',False)]
            domain += ['|',('date_stop','>=',date),('date_stop','=',False)]
        best_index = -1
        res = False
        for rec in self.browse(cr, uid, self.search(cr, uid, domain, context=context), context=context):
            index = 0
            if rec.product_id: index+=1
            if rec.partner_id: index+=1
            if rec.user_id: index+=1
            if rec.date_start: index+=1
            if rec.date_stop: index+=1
            if index>best_index:
                res = rec
                best_index = index
        return res
account_analytic_default()

class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'
    _description = 'account invoice line'
    def product_id_change(self, cr, uid, ids, product, uom, qty=0, name='', type='out_invoice', partner_id=False, fposition=False, price_unit=False, address_invoice_id=False, context={}):
        res_prod = super(account_invoice_line,self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, fposition, price_unit, address_invoice_id, context)
        rec = self.pool.get('account.analytic.default').account_get(cr, uid, product, partner_id, uid, time.strftime('%Y-%m-%d'), context)
        if rec:
            res_prod['value'].update({'account_analytic_id':rec.analytic_id.id})
        return res_prod
account_invoice_line()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
