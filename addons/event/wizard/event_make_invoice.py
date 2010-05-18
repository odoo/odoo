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
from osv import fields, osv

class event_make_invoice(osv.osv_memory):
    """
    Make Invoices
    """
    _name = "event.make.invoice"
    _description = "Event Make Invoice"
    _columns = {
        'inv_created': fields.char('Invoice Created', size=32, readonly=True),
        'inv_rejected': fields.char('Invoice Rejected', size=32, readonly=True),
        'inv_rej_reason': fields.text('Error Messages', readonly=True),
#        'invoice_ids': fields.char('Invoice Ids', size=128), # Improve me
               }

    def _makeInvoices(self, cr, uid, context={}):
        invoices = {}
        invoice_ids = []
        create_ids=[]
        tax_ids=[]
        inv_create = 0
        inv_reject = 0
        inv_rej_reason = ""
        list_inv = []
        obj_event_reg = self.pool.get('event.registration')
        obj_lines = self.pool.get('account.invoice.line')
        inv_obj = self.pool.get('account.invoice')
        data_event_reg = obj_event_reg.browse(cr,uid, context['active_ids'], context=context)

        for reg in data_event_reg:
            if reg.state=='draft':
                inv_reject = inv_reject + 1
                inv_rej_reason += "ID "+str(reg.id)+": Invoice cannot be created if the registration is in draft state. \n"
                continue
            if (not reg.tobe_invoiced):
                inv_reject = inv_reject + 1
                inv_rej_reason += "ID "+str(reg.id)+": Registration is set as 'Cannot be invoiced'. \n"
                continue
            if reg.invoice_id:
                inv_reject = inv_reject + 1
                inv_rej_reason += "ID "+str(reg.id)+": Registration already has an invoice linked. \n"
                continue
            if not reg.event_id.product_id:
                inv_reject = inv_reject + 1
                inv_rej_reason += "ID "+str(reg.id)+": Event related doesn't have any product defined. \n"
                continue
            if not reg.partner_invoice_id:
                inv_reject = inv_reject + 1
                inv_rej_reason += "ID "+str(reg.id)+": Registration doesn't have any partner to invoice. \n"
                continue
            partner_address_list = reg.partner_invoice_id and self.pool.get('res.partner').address_get(cr, uid, [reg.partner_invoice_id.id], adr_pref=['invoice'])
            partner_address_id = partner_address_list['invoice']
            if not partner_address_id:
                inv_reject = inv_reject + 1
                inv_rej_reason += "ID "+str(reg.id)+": Registered partner doesn't have an address to make the invoice. \n"
                continue

            inv_create = inv_create + 1
            value = obj_lines.product_id_change(cr, uid, [], reg.event_id.product_id.id,uom =False, partner_id=reg.partner_invoice_id.id, fposition_id=reg.partner_invoice_id.property_account_position.id)
            data_product = self.pool.get('product.product').browse(cr,uid,[reg.event_id.product_id.id])
            for tax in data_product[0].taxes_id:
                tax_ids.append(tax.id)

            vals = value['value']
            c_name = reg.contact_id and ('-' + self.pool.get('res.partner.contact').name_get(cr, uid, [reg.contact_id.id])[0][1]) or ''
            vals.update({
                'name': reg.invoice_label + '-' + c_name,
                'price_unit': reg.unit_price,
                'quantity': reg.nb_register,
                'product_id':reg.event_id.product_id.id,
                'invoice_line_tax_id': [(6, 0, tax_ids)],
            })
            inv_line_ids = obj_event_reg._create_invoice_lines(cr, uid, [reg.id], vals)

            inv = {
                'name': reg.invoice_label,
                'origin': reg.invoice_label,
                'type': 'out_invoice',
                'reference': False,
                'account_id': reg.partner_invoice_id.property_account_receivable.id,
                'partner_id': reg.partner_invoice_id.id,
                'address_invoice_id':partner_address_id,
                'address_contact_id':partner_address_id,
                'invoice_line': [(6,0,[inv_line_ids])],
                'currency_id' :reg.partner_invoice_id.property_product_pricelist.currency_id.id,
                'comment': "",
                'payment_term':reg.partner_invoice_id.property_payment_term.id,
                'fiscal_position': reg.partner_invoice_id.property_account_position.id
            }

            inv_id = inv_obj.create(cr, uid, inv)
            list_inv.append(inv_id)
            obj_event_reg.write(cr, uid, reg.id, {'invoice_id': inv_id, 'state': 'done'})
            obj_event_reg._history(cr, uid, [reg.id], 'Invoiced', history=True)

#        {'inv_created' : str(inv_create) , 'inv_rejected' : str(inv_reject), 'invoice_ids': str(list_inv), 'inv_rej_reason': inv_rej_reason}
        return {'inv_created' : str(inv_create) , 'inv_rejected' : str(inv_reject), 'inv_rej_reason': inv_rej_reason}

    def default_get(self, cr, uid, fields_list, context=None):
        res = super(event_make_invoice, self).default_get(cr, uid, fields_list, context)
        res.update(self._makeInvoices(cr, uid, context=context))
        return res

    def confirm(self, cr, uid, ids, context={}):
        obj_model = self.pool.get('ir.model.data')
        data_inv = self.read(cr, uid, ids, [], context)[0]
        model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','invoice_form')])
        resource_id = obj_model.read(cr,uid,model_data_ids,fields=['res_id'])[0]['res_id']
        return {
#            'domain': "[('id','in', ["+','.join(map(str,data_inv['invoice_ids']))+"])]",
            'name': 'Invoices',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'views': [(False,'tree'),(resource_id,'form')],
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window'
        }

event_make_invoice()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: