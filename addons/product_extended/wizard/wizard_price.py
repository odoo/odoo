# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2011 OpenERP S.A. (<http://www.openerp.com>).
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

from openerp.exceptions import except_orm
from openerp.osv import fields, osv
from openerp.tools.translate import _

class wizard_price(osv.osv):
    _name = "wizard.price"
    _description = "Compute price wizard"
    _columns = {
        'info_field': fields.text('Info', readonly=True), 
        'real_time_accounting': fields.boolean("Generate accounting entries when real-time"),
        'recursive': fields.boolean("Change prices of child BoMs too"),
        }

    def default_get(self, cr, uid, fields, context=None):
        res = super(wizard_price, self).default_get(cr, uid, fields, context=context)
        product_pool = self.pool.get('product.template')
        product_obj = product_pool.browse(cr, uid, context.get('active_id', False))
        if context is None:
            context = {}
        rec_id = context and context.get('active_id', False)
        assert rec_id, _('Active ID is not set in Context.')
        res['info_field'] = str(product_pool.compute_price(cr, uid, [], template_ids=[product_obj.id], test=True, context=context))
        return res

    def compute_from_bom(self, cr, uid, ids, context=None):
        assert len(ids) == 1
        if context is None:
            context = {}
        model = context.get('active_model')
        if model != 'product.template':
            raise except_orm(_('Wrong model!'), _('This wizard is build for product templates, while you are currently running it from a product variant.'))
        rec_id = context and context.get('active_id', False)
        assert rec_id, _('Active ID is not set in Context.')
        prod_obj = self.pool.get('product.template')
        res = self.browse(cr, uid, ids, context=context)
        prod = prod_obj.browse(cr, uid, rec_id, context=context)
        prod_obj.compute_price(cr, uid, [], template_ids=[prod.id], real_time_accounting=res[0].real_time_accounting, recursive=res[0].recursive, test=False, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
