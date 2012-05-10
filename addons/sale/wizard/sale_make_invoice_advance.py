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

from osv import fields, osv
from tools.translate import _

class sale_advance_payment_inv(osv.osv_memory):
    _name = "sale.advance.payment.inv"
    _description = "Sales Advance Payment Invoice"

    def _default_product_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        product_id = False
        data_obj = self.pool.get('ir.model.data')
        try:
            product_id = data_obj.get_object_reference(cr, uid, 'sale', 'advance_product_0')[1]
        finally:
            return product_id

    _columns = {
        'product_id': fields.many2one('product.product', 'Advance Product', required=False,
            help="Select a product of type service which is called 'Advance Product'. You may have to create it and set it as a default value on this field."),
        'amount': fields.float('Advance Amount', digits=(16, 2), required=True, help="The amount to be invoiced in advance."),
        'qtty': fields.float('Quantity', digits=(16, 2), required=True),
        'pay_type':fields.selection([('percentage','Percentage'), ('fixed','Fixed Price')], 'Pay Type', required=True),
        'advance': fields.boolean('Advance'),
    }

    _defaults = {
        'qtty': 1.0,
        'pay_type': 'fixed',
        'product_id': _default_product_id,
    }

    def onchange_pay_type(self, cr, uid, ids, pay_type,product_id, context=None):
        if not product_id:
            return {'value': {'amount': 0}}
        if pay_type == 'percentage':
            return {'value': {'amount':0,'product_id':False }}
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        return {'value': {'amount':product.list_price}}

    def onchange_advance_product(self, cr, uid, ids, product_id, context=None):
        data_obj = self.pool.get('ir.model.data')
        value = {}
        value['advance'] = 'False'
        if not product_id:
            return {'value': {'amount': 0,'advance': False}}
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        value['amount'] = product.list_price
        try:
            advance_id = data_obj.get_object_reference(cr, uid, 'sale', 'advance_product_0')[1]
            if product.id ==  advance_id:
                value['advance'] = 'True'
        finally:
            return {'value': value}

    def create_invoices(self, cr, uid, ids, context=None):
        """
             To create invoices.

             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param ids: the ID or list of IDs if we want more than one
             @param context: A standard dictionary

             @return:

        """
        list_inv = []
        obj_sale = self.pool.get('sale.order')
        obj_lines = self.pool.get('account.invoice.line')
        inv_obj = self.pool.get('account.invoice')
        if context is None:
            context = {}

        for sale_adv_obj in self.browse(cr, uid, ids, context=context):
            for sale in obj_sale.browse(cr, uid, context.get('active_ids', []), context=context):
                create_ids = []
                ids_inv = []
                if sale.order_policy == 'postpaid':
                    raise osv.except_osv(
                        _('Error'),
                        _("You cannot make an advance on a sales order \
                             that is defined as 'Automatic Invoice after delivery'."))
                val = obj_lines.product_id_change(cr, uid, [], sale_adv_obj.product_id.id,
                        uom = False, partner_id = sale.partner_id.id, fposition_id = sale.fiscal_position.id)
                res = val['value']

                if not sale_adv_obj.product_id.id :
                    prop = self.pool.get('ir.property').get(cr, uid,
                                         'property_account_income_categ', 'product.category',
                                         context=context)
                    account_id = prop and prop.id or False
                    account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, sale.fiscal_position.id or False, account_id)
                    res['account_id'] = account_id
                    if not res.get('account_id'):
                        raise osv.except_osv(_('Configuration Error !'),
                                _('There is no income account defined '))

                if not res.get('account_id'):
                    raise osv.except_osv(_('Configuration Error !'),
                                _('There is no income account defined ' \
                                        'for this product: "%s" (id:%d)') % \
                                        (sale_adv_obj.product_id.name, sale_adv_obj.product_id.id,))

                final_amount = 0
                if sale_adv_obj.amount <= 0.00:
                    raise osv.except_osv(_('Data Insufficient !'),
                        _('Please check the Advance Amount, it should not be 0 or less!'))
                else:
                    if sale_adv_obj.pay_type == 'percentage':
                        final_amount = sale.amount_total * sale_adv_obj.amount / 100
                        if not res.get('name'):
                            res['name'] = "Advance of %s"%(final_amount)
                    else:
                        final_amount = sale_adv_obj.amount
                        if not res.get('name'):
                            res['name'] = "Advance of %s %s"%(final_amount,sale.pricelist_id.currency_id.symbol)

                if res.get('invoice_line_tax_id'):
                    res['invoice_line_tax_id'] = [(6, 0, res.get('invoice_line_tax_id'))]
                else:
                    res['invoice_line_tax_id'] = False

                line_id = obj_lines.create(cr, uid, {
                    'name': res.get('name'),
                    'account_id': res['account_id'],
                    'price_unit': final_amount,
                    'quantity': sale_adv_obj.qtty or 1.0,
                    'discount': False,
                    'uos_id': res.get('uos_id') or False,
                    'product_id': sale_adv_obj.product_id.id,
                    'invoice_line_tax_id': res.get('invoice_line_tax_id'),
                    'account_analytic_id': sale.project_id.id or False,
                    #'note':'',
                })
                create_ids.append(line_id)
                inv = {
                    'name': sale.client_order_ref or sale.name,
                    'origin': sale.name,
                    'type': 'out_invoice',
                    'reference': False,
                    'account_id': sale.partner_id.property_account_receivable.id,
                    'partner_id': sale.partner_id.id,
                    'invoice_line': [(6, 0, create_ids)],
                    'currency_id': sale.pricelist_id.currency_id.id,
                    'comment': '',
                    'payment_term': sale.payment_term.id,
                    'fiscal_position': sale.fiscal_position.id or sale.partner_id.property_account_position.id
                }

                inv_id = inv_obj.create(cr, uid, inv)
                inv_obj.button_reset_taxes(cr, uid, [inv_id], context=context)

                for inv in sale.invoice_ids:
                    ids_inv.append(inv.id)
                ids_inv.append(inv_id)
                obj_sale.write(cr, uid, [sale.id], {'invoice_ids': [(6, 0, ids_inv)]})
                list_inv.append(inv_id)
        #
        # If invoice on picking: add the cost on the SO
        # If not, the advance will be deduced when generating the final invoice
        #
                if sale.order_policy == 'picking':
                    vals = {
                        'order_id': sale.id,
                        'name': res.get('name')  or ("%s %s %s "%(sale_adv_obj.amount,sale_adv_obj.pay_type,"Advance.")),
                        'price_unit': -final_amount,
                        'product_uom_qty': sale_adv_obj.qtty or 1.0,
                        'product_uos_qty': sale_adv_obj.qtty or 1.0,
                        'product_uos': res.get('uos_id') or False,
                        'product_id': sale_adv_obj.product_id.id or False,
                        'discount': False,
                        'tax_id': res.get('invoice_line_tax_id'),
                    }
                    if res.get('uos_id'):
                        vals.update({'product_uom': res.get('uos_id')})
                    self.pool.get('sale.order.line').create(cr, uid, vals, context)

        context.update({'invoice_id':list_inv})

        if context.get('open_invoices'):
            return self.open_invoices( cr, uid, ids, context=context)
        else:
            return {'type': 'ir.actions.act_window_close'}

    def open_invoices(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        for advance_pay in self.browse(cr, uid, ids, context=context):
            form_res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
            form_id = form_res and form_res[1] or False
            tree_res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_tree')
            tree_id = tree_res and tree_res[1] or False

        return {
            'name': _('Advance Invoice'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'account.invoice',
            'res_id': int(context['invoice_id'][0]),
            'view_id': False,
            'views': [(form_id, 'form'), (tree_id, 'tree')],
            'context': "{'type': 'out_invoice'}",
            'type': 'ir.actions.act_window',
         }

sale_advance_payment_inv()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
