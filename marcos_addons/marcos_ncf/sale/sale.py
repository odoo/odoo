# -*- encoding: utf-8 -*-
##############################################################################
#
#    Marcos Organizador de Negocios SRL.
#    Copyright (C) 2013-2014
#
##############################################################################
from openerp.osv import orm, fields
from openerp import netsvc


class sale_order(orm.Model):
    _inherit = "sale.order"

    _defaults = {
        'date_order': fields.date.context_today,
        'order_policy': 'manual',
        'state': 'draft',
        'user_id': lambda obj, cr, uid, context: uid,
        'name': lambda obj, cr, uid, context: '/',
        # 'invoice_quantity': 'order',
        'partner_invoice_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').address_get(cr, uid, [context['partner_id']], ['invoice'])['invoice'],
        'partner_shipping_id': lambda self, cr, uid, context: context.get('partner_id', False) and self.pool.get('res.partner').address_get(cr, uid, [context['partner_id']], ['delivery'])['delivery'],
    }

    def create_sales_order(self, cr, uid, orderline, customer_id, context=None):
        if not context:
            context ={}
        if context.get('type', False) == 'bill_credit':
            total_lines = 0
            for line in orderline:
                line_value = line["price_unit"]*line["return_qty"]
                discount = (float(line["discount"])/100)+1
                total_lines += line_value/discount
            res_partner = self.pool.get('res.partner').browse(cr, uid, customer_id)
            new_credit = res_partner.credit+total_lines
            if new_credit > res_partner.credit_limit:
                raise orm.except_osv('Limite de credito agotado!', 'Cominiquese con el encargado.')

            so_name = super(sale_order, self).create_sales_order(cr, uid, orderline, customer_id, context)
            so_id = self.search(cr, uid, [("name", "=", so_name["sale_no"])], context=context)

            self.action_button_confirm(cr, uid, so_id, context)
            self.manual_invoice(cr, uid, so_id, context)
            inv_id = self.pool.get("account.invoice").search(cr, uid, [("origin", "=", so_name["sale_no"])])
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'account.invoice', inv_id[0], 'invoice_open', cr)
            ncf = self.pool.get("account.invoice").browse(cr, uid, inv_id)[0].number

            picking_obj = self.pool.get('stock.picking.out')
            picking_id = picking_obj.search(cr, uid, [('origin', '=', so_name["sale_no"])])
            picking_obj.write(cr, uid, picking_id, {'auto_picking': True})
            wf_service.trg_validate(uid, 'stock.picking', picking_id[0], 'button_confirm', cr)
            picking_obj.force_assign(cr, uid, picking_id, context)

            fiscal_type = res_partner.property_account_position.fiscal_type or 'final'
            if fiscal_type == "gov" or fiscal_type == "special":
                fiscal_type = "fiscal"

            return [inv_id[0], ncf, res_partner.ref, fiscal_type, res_partner.name, context.get("shop_id", False), uid, False]
        else:
            so = super(sale_order, self).create_sales_order(cr, uid, orderline, customer_id, context)
            return so

    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        values = super(sale_order, self).onchange_partner_id(cr, uid, ids, part, context=context)
        try:
            user_default_warehouse = self.pool.get('res.users').browse(cr, uid, uid, context=context).warehouse_id.id
            values['value']['warehouse_id'] = user_default_warehouse
        except:
            pass
        return values