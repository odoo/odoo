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

    # make the real method inheritable
    _payment_block_proxy = lambda self,*a,**kw: self._portal_payment_block(*a, **kw)

    _columns = {
        'portal_payment_options': fields.function(_payment_block_proxy, type="html", string="Portal Payment Options"),
    }

    def _portal_payment_block(self, cr, uid, ids, fieldname, arg, context=None):
        result = dict.fromkeys(ids, False)
        payment_acquirer = self.pool.get('portal.payment.acquirer')
        for this in self.browse(cr, uid, ids, context=context):
            if this.state not in ('draft','cancel') and not this.invoiced:
                result[this.id] = payment_acquirer.render_payment_block(cr, uid, this, this.name,
                    this.pricelist_id.currency_id, this.amount_total, context=context)
        return result

    def action_quotation_send(self, cr, uid, ids, context=None):
        '''  Override to use a modified template that includes a portal signup link '''
        action_dict = super(sale_order, self).action_quotation_send(cr, uid, ids, context=context) 
        try:
            template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'portal_sale', 'email_template_edi_sale')[1]
            # assume context is still a dict, as prepared by super
            ctx = action_dict['context']
            ctx['default_template_id'] = template_id
            ctx['default_use_template'] = True
        except Exception:
            pass
        return action_dict

class account_invoice(osv.Model):
    _inherit = 'account.invoice'

    # make the real method inheritable
    _payment_block_proxy = lambda self,*a,**kw: self._portal_payment_block(*a, **kw)

    _columns = {
        'portal_payment_options': fields.function(_payment_block_proxy, type="html", string="Portal Payment Options"),
    }

    def _portal_payment_block(self, cr, uid, ids, fieldname, arg, context=None):
        result = dict.fromkeys(ids, False)
        payment_acquirer = self.pool.get('portal.payment.acquirer')
        for this in self.browse(cr, uid, ids, context=context):
            if this.type == 'out_invoice' and this.state not in ('draft','done') and not this.reconciled:
                result[this.id] = payment_acquirer.render_payment_block(cr, uid, this, this.number,
                    this.currency_id, this.residual, context=context)
        return result

    def action_invoice_sent(self, cr, uid, ids, context=None):
        '''  Override to use a modified template that includes a portal signup link '''
        action_dict = super(account_invoice, self).action_invoice_sent(cr, uid, ids, context=context) 
        try:
            template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'portal_sale', 'email_template_edi_invoice')[1]
            # assume context is still a dict, as prepared by super
            ctx = action_dict['context']
            ctx['default_template_id'] = template_id
            ctx['default_use_template'] = True
        except Exception:
            pass
        return action_dict
