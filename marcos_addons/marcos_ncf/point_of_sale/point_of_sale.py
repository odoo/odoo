# -*- encoding: utf-8 -*-
from openerp.osv import osv, fields
from openerp import netsvc
from openerp.tools.translate import _
import time
import datetime
import itertools
import operator
import logging

_logger = logging.getLogger(__name__)


class pos_config(osv.Model):
    _name = "pos.config"
    _inherit = "pos.config"

    _columns = {
        "iface_printer_host": fields.char("Host para impresora fiscal"),
        "iface_printer_model": fields.char("Modelo de impresora fiscal"),
        'not_show_zero_stock': fields.boolean("Solo mostrar productos con existencias"),
        'live_search': fields.boolean("Buscas productos sin precionar Enter"),
        'bill_credit': fields.boolean("Facturar a credito"),
        'payment_pos': fields.many2one("pos.config", u"Sesión de pago"),
    }

    _defaults = {
        'not_show_zero_stock': False,
        'live_search': False,
        'bill_credit': False
    }


class pos_order(osv.Model):
    _inherit = "pos.order"

    _columns = {
        'state': fields.selection([('draft', 'New'),
                                   ('cancel', 'Cancelled'),
                                   ('paid', 'Paid'),
                                   ('done', 'Posted'),
                                   ('invoiced', 'Invoiced')],
                                  'Status', readonly=True),
        'refund': fields.char('Refund', size=64, select=True, readonly=True),
        'ipf': fields.boolean("Impreso", readonly=True),
        'temp_name': fields.char("Cliente", size=64),
        'sale_journal': fields.many2one('account.journal', 'Diario de ventas', change_default=True, select=1, states={'draft': [('readonly', False)], 'paid': [('readonly', True)]}),
        'type': fields.selection([('order', 'Order'),
                                  ('receipt', 'Receipt')],
                                  'Type'),
    }

    _defaults = {
            'refund': lambda *a: False,
            'type': 'order'
            }

    def create_draft_from_ui(self, cr, uid, order, context=None):
        if order.get("default_partner", False):
            temp_name = order.get("temp_name", "Cliente de contado")
        elif order.get('parent_return_order', False):
            temp_name = self.read(cr, uid, order.get('parent_return_order'), ['temp_name'])['temp_name']
        else:
            temp_name = self.pool.get("res.partner").browse(cr, uid, order.get('partner_id')).name

        lot_obj = self.pool.get('stock.production.lot')
        session_obj = self.pool.get("pos.session")
        pos_config = session_obj.browse(cr, uid, order['pos_session_id']).config_id.payment_pos.id
        if pos_config:
            open_sesssion = session_obj.search(cr, uid, [('config_id', '=', pos_config), ('state', '=', 'opened')])
            if open_sesssion:
                order['pos_session_id'] = open_sesssion[0]
            else:
                raise osv.except_osv(_('Caja cerrada!'), _('La cajera no ha iniciado su terminal!'))

        if order.get('lines'):
            for line in order['lines']:
                l = line[2]
                if l.get('prodlot_id'):
                    lot = {'name': l['prodlot_id'],
                           'product_id': l['product_id']}
                    lot_id = lot_obj.create(cr, uid, lot)
                    l.update({'prodlot_id': lot_id})
                    line[2] = l
            self.create(cr, uid, {
                'temp_name': temp_name,
                'name': order['name'],
                'user_id': order['user_id'] or False,
                'session_id': order['pos_session_id'],
                'lines': order['lines'],
                'pos_reference':order['name'],
                'partner_id': order.get('partner_id'),
                'parent_return_order': order.get('parent_return_order', ''),
                'return_seq': order.get('return_seq', 0),
                'note': order.get('note')
            }, context)
        return True

    def action_create_invoice(self, cr, uid, id, context=None):
        if not context:
            context = {'none': True}
        context['active_model'] = 'pos.order'

        wf_service = netsvc.LocalService("workflow")
        inv_ref = self.pool.get('account.invoice')
        inv_line_ref = self.pool.get('account.invoice.line')
        product_obj = self.pool.get('product.product')

        inv_id = False
        order = self.pool.get('pos.order').browse(cr, uid, id, context=context)[0]
        partner_ref = order.partner_id.ref
        partner_name = order.partner_id.name

        shop = order.shop_id.id
        fiscal_type = order.partner_id.property_account_position.fiscal_type or 'final'
        fiscal_position = order.partner_id.property_account_position.id or 2

        #temp variable before finish with ipf 0 == ipf, 1 == star
        printer_type = 1

        if printer_type == 1:
            if fiscal_type == "gov" or fiscal_type == "special":
                fiscal_type = "fiscal"
        else:
            if fiscal_type == "special":
                fiscal_type = "special"
            elif fiscal_type == "gov":
                fiscal_type = "fiscal"

        if not order.partner_id:
            raise osv.except_osv(_('Error!'), _('Debe de seleccionar un cliente!'))
        acc = order.partner_id.property_account_receivable.id
        invoice_type = "out_invoice"
        refund_inv_ids = None
        ncf_reference = None
        if order.parent_return_order:

            if printer_type == 1:
                if fiscal_type == 'final':
                    fiscal_type = 'final_note'
                else:
                    fiscal_type = 'fiscal_note'
            else:

                if fiscal_type == 'final':
                    fiscal_type = 'final_note'
                elif fiscal_type == 'fiscal':
                    fiscal_type = 'fiscal_note'
                elif fiscal_type == 'special':
                    fiscal_type = "special_note"

            invoice_type = "out_refund"
            if context.get('none', False):
                try:
                    refund_order_name = self.browse(cr, uid, int(order.parent_return_order)).name
                    refund_inv_ids = self.pool.get('account.invoice').search(cr, uid, [("origin", "=", refund_order_name)])[0]
                    ncf_reference = inv_ref.browse(cr, uid, refund_inv_ids).number
                except Exception:
                    raise osv.except_osv(u'Factura sin cobrar!', u'No puede devolver dinero sin haber cobrado la factura de origen!')
            else:
                refund_inv_ids = context.get("refund_inv_ids", None)

        inv = {
            'name': order.name,
            'origin': order.name,
            'fiscal_position': fiscal_position,
            'account_id': acc,
            'journal_id': order.sale_journal.id or None,
            'type': invoice_type,
            'parent_id': refund_inv_ids,
            'reference': order.name,
            'partner_id': order.partner_id.id,
            'comment': order.note or '',
            'currency_id': order.pricelist_id.currency_id.id, # considering partner's sale pricelist's currency
        }
        inv.update(inv_ref.onchange_partner_id(cr, uid, [], 'out_invoice', order.partner_id.id)['value'])
        if not inv.get('account_id', None):
            inv['account_id'] = acc
        inv_id = inv_ref.create(cr, uid, inv, context=context)

        self.write(cr, uid, [order.id], {'invoice_id': inv_id, 'state': 'invoiced'}, context=context)

        for line in order.lines:
            if invoice_type == "out_refund":
                quantity = -line.qty
            else:
                quantity = line.qty
            inv_line = {
                'invoice_id': inv_id,
                'product_id': line.product_id.id,
                'quantity': quantity,
            }
            inv_name = product_obj.name_get(cr, uid, [line.product_id.id], context=context)[0][1]
            inv_line.update(inv_line_ref.product_id_change(cr, uid, [],
                                                           line.product_id.id,
                                                           line.product_id.uom_id.id,
                                                           line.qty, partner_id = order.partner_id.id,
                                                           fposition_id=order.partner_id.property_account_position.id)['value'])
            if line.product_id.description_sale:
                inv_line['note'] = line.product_id.description_sale
            inv_line['price_unit'] = line.price_unit
            inv_line['discount'] = line.discount
            inv_line['name'] = inv_name
            taxes_objs =  line.product_id.taxes_id
            line_obj = self.pool.get('pos.order.line')
            for i, tax_obj in enumerate(taxes_objs):
                taxes_objs[i] = line_obj.get_substitute_tax(cr, uid, tax_obj, line.order_id.partner_id)
            inv_line['invoice_line_tax_id'] = [(6, 0, [t.id for t in taxes_objs] )]
            inv_line_ref.create(cr, uid, inv_line, context=context)
        inv_ref.button_reset_taxes(cr, uid, [inv_id], context=context)
        wf_service.trg_validate(uid, 'account.invoice', inv_id, 'validate', cr)
        # Ejecuta el signal para generar la factura definitiva
        wf_service.trg_validate(uid, 'pos.order', order.id, 'invoice', cr)
        wf_service.trg_validate(uid, 'account.invoice', inv_id, 'invoice_open', cr)
        current_invoice = inv_ref.browse(cr, uid, inv_id)

        # Activate sending of notification if:
        #  Remaining amount of sequences it's equal or less than notification parameter, and
        #  remaining amount is divisible by 10 (send less notifications), and
        #  ncf_limit is different than 0 (0 means unlimited)
        # A notification will be sent to the responsible user
        number_next_actual = current_invoice.journal_id.sequence_id.number_next_actual
        ncf_limit = current_invoice.journal_id.sequence_id.ncf_limit
        ncf_remaining = ncf_limit - number_next_actual 
        ncf_notification = current_invoice.journal_id.sequence_id.ncf_notify
        notify_request_ncf = False
        if ncf_remaining <= ncf_notification \
            and not ncf_remaining%10 \
            and ncf_limit:
            notify_request_ncf = True
            responsible = current_invoice.journal_id.sequence_id.user_id.id
            # Only send notification if a user is assigned to sequence.
            # This was changed from raising an error message
            # because that resulted in sequence skipping.
            if responsible:
                responsible = self.pool.get('res.users').browse(cr, uid, responsible)
                responsible.message_post()

        return [inv_id, current_invoice.number, partner_ref, fiscal_type, partner_name, shop, uid, ncf_reference, notify_request_ncf, order.name]

    def action_invoice(self, cr, uid, ids, context=None):
        if not context:
            context ={}
        context['active_model'] = 'pos.order'
        return super(pos_order, self).action_invoice(cr, uid, ids, context)

    def create_picking(self, cr, uid, ids, context=None):
        """Create a picking for each order and validate it."""
        picking_obj = self.pool.get('stock.picking')
        partner_obj = self.pool.get('res.partner')
        move_obj = self.pool.get('stock.move')

        for order in self.browse(cr, uid, ids, context=context):
            if not order.state=='draft':
                continue
            if order.amount_total >= 0:
                type = 'out'
            else:
                type = 'in'

            addr = order.partner_id and partner_obj.address_get(cr, uid, [order.partner_id.id], ['delivery']) or {}
            picking_id = picking_obj.create(cr, uid, {
                'origin': order.name,
                'partner_id': addr.get('delivery',False),
                'type': type,
                'company_id': order.company_id.id,
                'move_type': 'direct',
                'note': order.note or "",
                'invoice_state': 'none',
                'auto_picking': True,
            }, context=context)
            self.write(cr, uid, [order.id], {'picking_id': picking_id}, context=context)
            location_id = order.shop_id.warehouse_id.lot_stock_id.id
            output_id = order.shop_id.warehouse_id.lot_output_id.id

            for line in order.lines:
                if line.product_id and line.product_id.type == 'service':
                    continue
                if line.qty < 0:
                    location_id, output_id = output_id, location_id

                move_obj.create(cr, uid, {
                    'name': line.name,
                    'product_uom': line.product_id.uom_id.id,
                    'product_uos': line.product_id.uom_id.id,
                    'picking_id': picking_id,
                    'product_id': line.product_id.id,
                    'product_uos_qty': abs(line.qty),
                    'product_qty': abs(line.qty),
                    'tracking_id': False,
                    'state': 'draft',
                    'location_id': location_id,
                    'location_dest_id': output_id,
                    'prodlot_id': line.prodlot_id and line.prodlot_id.id or False,
                }, context=context)
                if line.qty < 0:
                    location_id, output_id = output_id, location_id

            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'stock.picking', picking_id, 'button_confirm', cr)
            picking_obj.force_assign(cr, uid, [picking_id], context)
        return True

    def _get_journal_id(self, fiscal_type, shop_id, refund):
        if refund:
            return shop_id.notas_credito_id.id
        elif fiscal_type == "final" or fiscal_type is None:
            return shop_id.final_id.id
        elif fiscal_type == "fiscal":
            return shop_id.fiscal_id.id
        elif fiscal_type == "special":
            return shop_id.especiales_id.id
        elif fiscal_type == "gov":
            return shop_id.gubernamentales_id.id
        else:
            return False

    def create(self, cr, uid, values, context=None):
        context = context or {}
        if not values.get("lines", False) and not context.get('empty_order', False):
            raise osv.except_osv(_('Error!'), _("No puede grabar un pedido sin productos"))

        session = self.pool.get("pos.session").browse(cr, uid, [values["session_id"]], context)[0]
        if not values["partner_id"]:
            values["partner_id"] = session.config_id.shop_id.default_partner_id.id

        partner = self.pool.get("res.partner").browse(cr, uid, [values["partner_id"]], context)[0]
        fiscal_type = partner.property_account_position.fiscal_type or "final"
        shop_id = session.config_id.shop_id

        refund = False
        if str(values.get("parent_return_order")).isdigit():
            refund = True
        if values.get("type", False) == "receipt":
            pass
        else:
            values['sale_journal'] = self._get_journal_id(fiscal_type, shop_id, refund)

        # Create method of pos_order (super) won't be called,
        # since a different sequence needs to be used for receipt.
        # new_order = super(pos_order, self).create(cr, uid, values, context=context)
        if context.get('pos_receipt', False):
            values.update({'name': context.get("rec_pos_seq")})
        else:
            values.update({'name': self.pool.get('ir.sequence').get(cr, uid, 'pos.order')})

        new_order = osv.Model.create(self, cr, uid, values, context=context)

        return new_order

    def refund(self, cr, uid, ids, context=None):
        """Create a copy of order  for refund order"""
        clone_list = []
        line_obj = self.pool.get('pos.order.line')

        for order in self.browse(cr, uid, ids, context=context):
            pos_config_id = self.pool.get("res.users").browse(cr, uid, uid, context=context).pos_config.payment_pos.id
            if pos_config_id:
                current_session_ids = self.pool.get('pos.session').search(cr, uid, [('state', '!=', 'closed'), ('config_id', '=', pos_config_id)], context=context)
            else:
                pos_config_id = self.pool.get("res.users").browse(cr, uid, uid, context=context).pos_config.id
                current_session_ids = self.pool.get('pos.session').search(cr, uid, [('state', '!=', 'closed'), ('config_id', '=', pos_config_id)], context=context)

            if not current_session_ids:
                raise osv.except_osv(_('Error!'), _(u'Para devolver el producto (s), la sesión de caja debe de estar abierta.'))

            name = None
            if order.amount_total >= 0:
                name = order.name

            clone_id = self.copy(cr, uid, order.id, {
                'name': name,
                'session_id': current_session_ids[0],
                'date_order': time.strftime('%Y-%m-%d %H:%M:%S'),
                'refund': name,
                "parent_return_order": order.id
            }, context=context)
            clone_list.append(clone_id)

        for clone in self.browse(cr, uid, clone_list, context=context):
            for order_line in clone.lines:
                line_obj.write(cr, uid, [order_line.id], {'qty': -order_line.qty}, context=context)

        abs = {
            #'domain': "[('id', 'in', ["+new_order+"])]",
            'name': _('Return Products'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id':clone_list[0],
            'view_id': False,
            'context':context,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
        }
        return abs

    def set_printed(self, cr, uid, oid, context=None):
        oid = self.write(cr, uid, oid, {"ipf": True }, context)
        return oid

    def print_on_ipf(self, cr, uid, name, context=None):
        context = context or {}
        inv_obj = self.pool.get("account.invoice")

        inv_id = inv_obj.search(cr, uid, [["origin", "=", name]])
        ord_id = self.search(cr, uid, [["name", "=", name]])

        inv = inv_obj.browse(cr, uid, inv_id, context)[0]
        ord = self.browse(cr, uid, ord_id, context)[0]
        cashier = self.perm_read(cr, uid, ord_id,  details=True)[0].get("write_uid", None)[1]

        fiscal_type = ord.partner_id.property_account_position.fiscal_type or "final"

        if fiscal_type == "gov" or fiscal_type == "special":
            fiscal_type = "fiscal"

        refund_inv_ids = None
        # if ord.refund_inv_ids:
        #     refund_inv_ids = inv.parent_id.number
        #     if fiscal_type == "final":
        #         fiscal_type = "nota_final"
        #     else:
        #         fiscal_type = "nota_fiscal"

        address = ""
        if ord.company_id.street:
            address  = ord.company_id.street
        if ord.company_id.street2:
            address += " "+ord.company_id.street2
        if ord.company_id.city:
            address += " "+ord.company_id.city

        # Re-creating the invoice
        orderlines = []
        total_discount = 0.00
        for ln in ord.lines:
            if ln.discount != 0:
                total_discount += (ln.price_unit * ln.qty)*ln.discount/100
            line = {}
            line["quantity"] = ln.qty
            line["unit_name"] = ln.product_id.uom_id.name
            line["price"] = ln.price_unit
            line["discount"] = ln.discount
            line["product_name"] = ln.product_id.name
            line["price_display"] = ln.price_unit
            line["price_with_tax"] = ln.price_subtotal_incl
            line["price_without_tax"] = ln.price_subtotal
            line["tax"] = ln.order_id.amount_tax
            line["product_description"] = ln.product_id.description
            line["product_description_sale"] = ln.product_id.description_sale
            orderlines.append(line)


        paymentlines = []
        for ln in ord.statement_ids:
            line = {}
            line["amount"] = ln.amount
            line["journal"] = ln.journal_id.name
            line["ipf_payment_type"] = ln.journal_id.ipf_payment_type
            paymentlines.append(line)

        #Discount

        date = datetime.datetime.strptime(ord.date_order, '%Y-%m-%d %H:%M:%S')

        invoice = {
            'receipt': {
                'orderlines': orderlines,
                'paymentlines': paymentlines,
            "subtotal": inv.amount_untaxed,
            "total_with_tax": inv.amount_total,
            "total_without_tax": inv.amount_untaxed,
            "total_tax": inv.amount_tax,
            "total_paid": ord.amount_paid,
            "total_discount": total_discount,
            "change": ord.amount_return,
            "name": ord.pos_reference,
            "client": ord.partner_id.name,
            "invoice_id": inv.number,
            "cashier": cashier,
            "date": {
                "year": date.year,
                "month": date.month,
                "date": date.day,  # TODO esta asignando  el dia de hoy
                "day": 0,  # TODO a que correponde?
                "hour": date.hour,  # TODO porque elimina el primer digito?
                "minute": date.minute
                },
            "company": {
                "email": ord.company_id.email,
                "website": ord.company_id.website,
                "company_registry": ord.company_id.company_registry,
                "contact_address": address,
                "vat": ord.company_id.vat,
                "name": ord.company_id.name,
                "phone": ord.company_id.name
            },
            "shop": {
                "name": ord.shop_id.name
            },
            "currency": {
                "rounding": inv.currency_id.position,
                "position":  inv.currency_id.position,
                "symbol": inv.currency_id.symbol,
                "id": inv.currency_id.id,
                "accuracy": inv.currency_id.accuracy,
                },
            },
            "brand": ord.session_id.config_id.iface_printer_model,
            "host": ord.session_id.config_id.iface_printer_host,
            "ncf": inv.number,
            'rnc': ord.partner_id.ref,
            'fiscal_type': fiscal_type,
            "client": ord.partner_id.name,
            'branch': ord.shop_id.id,
            'uid': uid,
            "ncf_reference": inv.reference,
            'oid': [ord.id],
            'comment': u"Ref: "+ord.name
            }

        return invoice

    def action_pos_payment(self, cr, uid, ids, context=None):
        """
        Call pos_make_payment wizard.
        
        """

        view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'point_of_sale', 'view_pos_payment')[1]
        wizard = {
            'name': 'Pago',
            'view_mode': 'form',
            'view_id': False,
            'views': [(view_id, 'form')],
            'view_type': 'form',
            'res_model': 'pos.make.payment',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
        return wizard

    def _create_account_move_line(self, cr, uid, ids, session=None, move_id=None, context=None):
        for order in self.read(cr, uid, ids, ["type"]):
            if order.get("type", False) == "receipt":
                continue
            else:
                return super(pos_order, self)._create_account_move_line(cr, uid, ids, session=session, move_id=move_id, context=context)
        return True

    def add_payment(self, cr, uid, order_id, data, context=None):
        """Create a new payment for the order"""
        if not context:
            context = {}
        statement_line_obj = self.pool.get('account.bank.statement.line')
        property_obj = self.pool.get('ir.property')
        order = self.browse(cr, uid, order_id, context=context)
        args = {
            'amount': data['amount'],
            'date': data.get('payment_date', time.strftime('%Y-%m-%d')),
            'name': order.name + ': ' + (data.get('payment_name', '') or ''),
        }


        account_def = property_obj.get(cr, uid, 'property_account_receivable', 'res.partner', context=context)

        if order.type != u"receipt":
            args['account_id'] = (order.partner_id and order.partner_id.property_account_receivable and order.partner_id.property_account_receivable.id) or (account_def and account_def.id) or False
        else:
            args['account_id'] = order.sale_journal.default_credit_account_id.id

        args['partner_id'] = order.partner_id and order.partner_id.id or None
        if not args['account_id']:
            if not args['partner_id']:
                msg = _('There is no receivable account defined to make payment.')
            else:
                msg = _('There is no receivable account defined to make payment for the partner: "%s" (id:%d).') % (order.partner_id.name, order.partner_id.id,)
            raise osv.except_osv(_('Configuration Error!'), msg)

        context.pop('pos_session_id', False)

        journal_id = data.get('journal', False)
        statement_id = data.get('statement_id', False)
        assert journal_id or statement_id, "No statement_id or journal_id passed to the method!"

        for statement in order.session_id.statement_ids:
            if statement.id == statement_id:
                journal_id = statement.journal_id.id
                break
            elif statement.journal_id.id == journal_id:
                statement_id = statement.id
                break

        if not statement_id:
            raise osv.except_osv(_('Error!'), _('You have to open at least one cashbox.'))

        args.update({
            'statement_id' : statement_id,
            'pos_statement_id' : order_id,
            'journal_id' : journal_id,
            'type' : 'customer',
            'ref' : order.session_id.name,
        })

        statement_line_obj.create(cr, uid, args, context=context)

        return statement_id


class pos_order_line(osv.Model):
    _inherit = "pos.order.line"

    def get_substitute_tax(self, cr,  uid, tax_obj, partner_obj, context=None):
        """
        Apply tax substitution for the fiscal position of a partner.

        """

        if partner_obj.property_account_position:
            for tax_map in partner_obj.property_account_position.tax_ids:
                if tax_obj == tax_map.tax_src_id:
                    tax_obj = tax_map.tax_dest_id
        return tax_obj
        
    def _amount_line_all(self, cr, uid, ids, field_names, arg, context=None):
        """
        POS is not taking under consideration tax exemption when tax is included in price.
        A validation is being added to use the exempt configuration.

        price_subtotal and price_subtotal_incl are not modified, but had to overwrite them
        to overwrite there function method.

        """

        res = dict([(i, {}) for i in ids])
        account_tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids, context=context):
            taxes_ids = [ tax for tax in line.product_id.taxes_id if tax.company_id.id == line.order_id.company_id.id ]
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = account_tax_obj.compute_all(cr, uid, taxes_ids, price, line.qty, product=line.product_id, partner=line.order_id.partner_id or False)

            # Get substitute tax based on partner's fiscal position.
            if not context.get("type", False) == "receipt":
                for i, tax_obj in enumerate(taxes_ids):
                    taxes_ids[i] = self.get_substitute_tax(cr, uid, tax_obj, line.order_id.partner_id)
                # If main/first tax is exempt, use total with tax not included.
                if taxes_ids:
                    if taxes_ids[0].exempt:
                        taxes['total_included'] = taxes['total']

            cur = line.order_id.pricelist_id.currency_id
            res[line.id]['price_subtotal'] = cur_obj.round(cr, uid, cur, taxes['total'])
            res[line.id]['price_subtotal_incl'] = cur_obj.round(cr, uid, cur, taxes['total_included'])
        return res

    _columns = {
        'prodlot_id': fields.many2one('stock.production.lot', 'Serial No'),
        'price_subtotal': fields.function(_amount_line_all, multi='pos_order_line_amount', string='Subtotal w/o Tax', store=True),
        'price_subtotal_incl': fields.function(_amount_line_all, multi='pos_order_line_amount', string='Subtotal', store=True),
        'qty': fields.float('Quantity', digits=(16, 4))
    }


class pos_session(osv.Model):
    _inherit = "pos.session"

    def _confirm_orders(self, cr, uid, ids, context=None):
        wf_service = netsvc.LocalService("workflow")

        for session in self.browse(cr, uid, ids, context=context):
            # local_context = dict(context or {}, force_company=session.config_id.journal_id.company_id.id)
            #order_ids = [order.id for order in session.order_ids if order.state == 'invoiced']

            #move_id = self.pool.get('account.move').create(cr, uid, {'ref' : session.name, 'journal_id' : session.config_id.journal_id.id, }, context=context)

            #self.pool.get('pos.order')._create_account_move_line(cr, uid, order_ids, session, move_id, context=context)

            for order in session.order_ids:
                if order.state not in ('paid', 'invoiced'):
                    raise osv.except_osv(
                        _('Error!'),
                        _("You cannot confirm all orders of this session, because they have not the 'paid' status"))
                else:
                    invoice_ref = self.pool.get("account.invoice")
                    wf_service.trg_validate(uid, 'pos.order', order.id, 'done', cr)
                    invoice_ref.write(cr, uid, invoice_ref.search(cr, uid, [("reference", "=", order.name)]), {'state': 'paid'}, context=context)

        return True

    def wkf_action_closing_control(self, cr, uid, ids, context=None):
        # TODO cuando se cambia la forma de pago despues de cobrada la factura esta permanece en estado pagado aunque
        # TODO el pago no este completo esto debe de ser validado.
        for session in self.browse(cr, uid, ids, context=context):
            for statement in session.statement_ids:
                if statement.balance_end == 0:
                    self.pool.get('account.bank.statement').write(cr, uid, [statement.id], {'state': "draft"}, context=context)
                    self.pool.get('account.bank.statement').unlink(cr, uid, [statement.id], context=context)
                elif (statement != session.cash_register_id) and (statement.balance_end != statement.balance_end_real):
                    self.pool.get('account.bank.statement').write(cr, uid, [statement.id], {'balance_end_real': statement.balance_end})

        result = self.write(cr, uid, ids, {'state': 'closing_control', 'stop_at': time.strftime('%Y-%m-%d %H:%M:%S')}, context=context)
        return result

    def open_cb(self, cr, uid, ids, context=None):
        """
        call the Point Of Sale interface and set the pos.session to 'opened' (in progress)
        """
        if context is None:
            context = dict()

        if isinstance(ids, (int, long)):
            ids = [ids]

        this_record = self.browse(cr, uid, ids[0], context=context)
        this_record._workflow_signal('open')

        context.update(active_id=this_record.id)
        if this_record.config_id.payment_pos.id:
            return {
                'type': 'ir.actions.client',
                'name': _('Start Point Of Sale'),
                'tag': 'pos.ui',
                'context': context,
            }
        else:
            return {
                'view_type': 'form',
                'view_mode': 'tree',
                'res_model': 'pos.order',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'context': context,
            }

    def open_frontend_cb(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        if not ids:
            return {}
        sessions = self.browse(cr, uid, ids, context=context)
        for session in sessions:
            if session.user_id.id != uid:
                raise osv.except_osv(
                        _('Error!'),
                        _("You cannot use the session of another users. This session is owned by %s. Please first close this one to use this point of sale." % session.user_id.name))
        context.update({'active_id': ids[0]})
        if sessions[0].config_id.payment_pos.id:
            return {
                'type': 'ir.actions.client',
                'name': _('Start Point Of Sale'),
                'tag': 'pos.ui',
                'context': context,
            }
        else:
            return {
                'view_type':'form',
                'view_mode':'tree',
                'res_model':'pos.order',
                'view_id':False,
                'type':'ir.actions.act_window',
                'context':context,
            }

    def create(self, cr, uid, values, context=None):
        context = context or {}
        config_id = values.get('config_id', False) or context.get('default_config_id', False)
        if not config_id:
            raise osv.except_osv( _('Error!'),
                _("You should assign a Point of Sale to your session."))

        # journal_id is not required on the pos_config because it does not
        # exists at the installation. If nothing is configured at the
        # installation we do the minimal configuration. Impossible to do in
        # the .xml files as the CoA is not yet installed.
        jobj = self.pool.get('pos.config')
        pos_config = jobj.browse(cr, uid, config_id, context=context)
        context.update({'company_id': pos_config.shop_id.company_id.id})
        if pos_config.payment_pos == False: # Eneldo
            if not pos_config.journal_id:
                jid = jobj.default_get(cr, uid, ['journal_id'], context=context)['journal_id']
                if jid:
                    jobj.write(cr, uid, [pos_config.id], {'journal_id': jid}, context=context)
                else:
                    raise osv.except_osv( _('error!'),
                        _("Unable to open the session. You have to assign a sale journal to your point of sale."))

            # define some cash journal if no payment method exists
            if not pos_config.journal_ids:
                journal_proxy = self.pool.get('account.journal')
                cashids = journal_proxy.search(cr, uid, [('journal_user', '=', True), ('type','=','cash')], context=context)
                if not cashids:
                    cashids = journal_proxy.search(cr, uid, [('type', '=', 'cash')], context=context)
                    if not cashids:
                        cashids = journal_proxy.search(cr, uid, [('journal_user','=',True)], context=context)

                jobj.write(cr, uid, [pos_config.id], {'journal_ids': [(6,0, cashids)]})


        pos_config = jobj.browse(cr, uid, config_id, context=context)
        bank_statement_ids = []
        for journal in pos_config.journal_ids:
            bank_values = {
                'journal_id' : journal.id,
                'user_id' : uid,
                'company_id' : pos_config.shop_id.company_id.id
            }
            statement_id = self.pool.get('account.bank.statement').create(cr, uid, bank_values, context=context)
            bank_statement_ids.append(statement_id)

        values.update({
            'name' : pos_config.sequence_id._next(),
            'statement_ids' : [(6, 0, bank_statement_ids)],
            'config_id': config_id
        })

        return osv.Model.create(self, cr, uid, values, context=context)

    def wkf_action_close(self, cr, uid, ids, context=None):
        result = super(pos_session, self).wkf_action_close(cr, uid, ids, context=context)
        self.reconcilie_pos_invoice(cr, uid, ids, context=context)
        return result

    def reconcilie_pos_invoice(self,cr, uid, ids, context):
        date = time.strftime('%Y-%m-%d')
        period_id = self.pool.get('account.period').find(cr, uid, dt=date, context=context)
        if period_id:
            period_id = period_id[0]
        move_line_obj = self.pool.get("account.move.line")
        pos_obj = self.pool.get("pos.order")

        sessions = self.browse(cr, uid, ids, context=context)

        for session in sessions:
            move_line_ids = []
            order_ids = pos_obj.search(cr, uid, [('session_id', '=', session.id)])
            order_names = [order['name'] for order in pos_obj.read(cr, uid, order_ids, ['name'])]
            for name in order_names:
                try:
                    move_ids = move_line_obj.search(cr, uid, [('name', '=', name)])
                    inv_account_id = move_line_obj.read(cr, uid, move_ids, ['account_id'])[0]['account_id'][0]
                    move_ids += move_line_obj.search(cr, uid, [('name', 'like', '%s%s' % (name, ':%')), ('account_id', '=', inv_account_id)])
                    move_line_obj.reconcile(cr, uid, move_ids, 'manual', False, period_id, False, context)
                except:
                    continue