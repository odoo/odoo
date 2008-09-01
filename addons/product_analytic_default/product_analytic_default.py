# -*- encoding: utf-8 -*-

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

class product_product(osv.osv):
    _name = 'product.product'
    _inherit = 'product.product'
    _description = 'Product'

    _columns = {
        'property_account_analytic': fields.property(
            'account.analytic.account',
            type='many2one',
            relation='account.analytic.account',
            string="Analytic Account",
            method=True,
            view_load=True,
            group_name="Accounting Properties",
            help="This Analytic Account will be use in sale order line and invoice lines",
            ),
                }

product_product()

class account_invoice_line(osv.osv):
    _inherit = 'account.invoice.line'
    _description = 'account invoice line'

    def product_id_change(self, cr, uid, ids, product, uom, qty=0, name='', type='out_invoice', partner_id=False, price_unit=False, address_invoice_id=False, context={}):
        res_prod = super(account_invoice_line,self).product_id_change(cr, uid, ids, product, uom, qty, name, type, partner_id, price_unit, address_invoice_id, context)
        if product:
            res = self.pool.get('product.product').browse(cr, uid, product, context=context)
            res_prod['value'].update({'account_analytic_id':res.property_account_analytic.id})
        return res_prod

account_invoice_line()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

