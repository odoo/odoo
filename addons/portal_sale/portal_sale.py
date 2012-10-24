# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (c) 2012 OpenERP S.A. <http://openerp.com>
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

from openerp.osv import osv, fields

class sale_order(osv.Model):
    _inherit = 'sale.order'

    _payment_block_proxy = lambda self,*a,**kw: self._portal_payment_block(*a, **kw)

    _columns = {
        'portal_payment_options': fields.function(_payment_block_proxy, type="html", string="Portal Payment Options"),
    }

    def _portal_payment_block(self, cr, uid, ids, fieldname, arg, context=None):
        result = dict.fromkeys(ids, False)
        payment_acquirer = self.pool.get('portal.payment.acquirer')
        for this in self.browse(cr, uid, ids, context=context):
            if this.state != 'draft':
                result[this.id] = payment_acquirer.render_payment_block(cr, uid, this, this.name,
                    this.pricelist_id.currency_id, this.amount_total, context=context)
        return result