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

from osv import fields,osv
import netsvc
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tools.translate import _
import decimal_precision as dp

class mrp_repair(osv.osv):
    _name = 'mrp.repair'
    _description = 'Repair Order'

    def _amount_untaxed(self, cr, uid, ids, field_name, arg, context=None):
        """ Calculates untaxed amount.
        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param field_name: Name of field.
        @param arg: Argument
        @param context: A standard dictionary for contextual values
        @return: Dictionary of values.
        """
        res = {}
        cur_obj = self.pool.get('res.currency')

        for repair in self.browse(cr, uid, ids, context=context):
            res[repair.id] = 0.0
            for line in repair.operations:
                res[repair.id] += line.price_subtotal
            for line in repair.fees_lines:
                res[repair.id] += line.price_subtotal
            cur = repair.pricelist_id.currency_id
            res[repair.id] = cur_obj.round(cr, uid, cur, res[repair.id])
        return res

    def _amount_tax(self, cr, uid, ids, field_name, arg, context=None):
        """ Calculates taxed amount.
        @param field_name: Name of field.
        @param arg: Argument
        @return: Dictionary of values.
        """
        res = {}
        #return {}.fromkeys(ids, 0)
        cur_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        for repair in self.browse(cr, uid, ids, context=context):
            val = 0.0
            cur = repair.pricelist_id.currency_id
            for line in repair.operations:
                #manage prices with tax included use compute_all instead of compute
                if line.to_invoice:
                    tax_calculate = tax_obj.compute_all(cr, uid, line.tax_id, line.price_unit, line.product_uom_qty, line.product_id, repair.partner_id)
                    for c in tax_calculate['taxes']:
                        val += c['amount']
            for line in repair.fees_lines:
                if line.to_invoice:
                    tax_calculate = tax_obj.compute_all(cr, uid, line.tax_id, line.price_unit, line.product_uom_qty,  line.product_id, repair.partner_id)
                    for c in tax_calculate['taxes']:
                        val += c['amount']
            res[repair.id] = cur_obj.round(cr, uid, cur, val)
        return res

    def _amount_total(self, cr, uid, ids, field_name, arg, context=None):
        """ Calculates total amount.
        @param field_name: Name of field.
        @param arg: Argument
        @return: Dictionary of values.
        """
        res = {}
        untax = self._amount_untaxed(cr, uid, ids, field_name, arg, context=context)
        tax = self._amount_tax(cr, uid, ids, field_name, arg, context=context)
        cur_obj = self.pool.get('res.currency')
        for id in ids:
            repair = self.browse(cr, uid, id, context=context)
            cur = repair.pricelist_id.currency_id
            res[id] = cur_obj.round(cr, uid, cur, untax.get(id, 0.0) + tax.get(id, 0.0))
        return res

    def _get_default_address(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        partner_obj = self.pool.get('res.partner')
        for data in self.browse(cr, uid, ids, context=context):
            adr_id = False
            if data.partner_id:
                adr_id = partner_obj.address_get(cr, uid, [data.partner_id.id], ['default'])['default']
            res[data.id] = adr_id
        return res

    def _get_lines(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('mrp.repair.line').browse(cr, uid, ids, context=context):
            result[line.repair_id.id] = True
        return result.keys()

    _columns = {
        'name': fields.char('Repair Reference',size=24, required=True),
        'product_id': fields.many2one('product.product', string='Product to Repair', required=True, readonly=True, states={'draft':[('readonly',False)]}),
        'partner_id' : fields.many2one('res.partner', 'Partner', select=True, help='Choose partner for whom the order will be invoiced and delivered.'),
        'address_id': fields.many2one('res.partner', 'Delivery Address', domain="[('parent_id','=',partner_id)]"),
        'default_address_id': fields.function(_get_default_address, type="many2one", relation="res.partner"),
        'prodlot_id': fields.many2one('stock.production.lot', 'Lot Number', select=True, domain="[('product_id','=',product_id)]"),
        'state': fields.selection([
            ('draft','Quotation'),
            ('cancel','Cancel'),
            ('confirmed','Confirmed'),
            ('under_repair','Under Repair'),
            ('ready','Ready to Repair'),
            ('2binvoiced','To be Invoiced'),
            ('invoice_except','Invoice Exception'),
            ('done','Done')
            ], 'Status', readonly=True,
            help=' * The \'Draft\' state is used when a user is encoding a new and unconfirmed repair order. \
            \n* The \'Confirmed\' state is used when a user confirms the repair order. \
            \n* The \'Ready to Repair\' state is used to start to repairing, user can start repairing only after repair order is confirmed. \
            \n* The \'To be Invoiced\' state is used to generate the invoice before or after repairing done. \
            \n* The \'Done\' state is set when repairing is completed.\
            \n* The \'Cancelled\' state is used when user cancel repair order.'),
        'location_id': fields.many2one('stock.location', 'Current Location', select=True, readonly=True, states={'draft':[('readonly',False)]}),
        'location_dest_id': fields.many2one('stock.location', 'Delivery Location', readonly=True, states={'draft':[('readonly',False)]}),
        'move_id': fields.many2one('stock.move', 'Move',required=True, domain="[('product_id','=',product_id)]", readonly=True, states={'draft':[('readonly',False)]}),
        'guarantee_limit': fields.date('Guarantee limit', help="The guarantee limit is computed as: last move date + warranty defined on selected product. If the current date is below the guarantee limit, each operation and fee you will add will be set as 'not to invoiced' by default. Note that you can change manually afterwards."),
        'operations' : fields.one2many('mrp.repair.line', 'repair_id', 'Operation Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', help='Pricelist of the selected partner.'),
        'partner_invoice_id':fields.many2one('res.partner', 'Invoicing Address'),
        'invoice_method':fields.selection([
            ("none","No Invoice"),
            ("b4repair","Before Repair"),
            ("after_repair","After Repair")
           ], "Invoice Method",
            select=True, required=True, states={'draft':[('readonly',False)]}, readonly=True, help='Selecting \'Before Repair\' or \'After Repair\' will allow you to generate invoice before or after the repair is done respectively. \'No invoice\' means you don\'t want to generate invoice for this repair order.'),
        'invoice_id': fields.many2one('account.invoice', 'Invoice', readonly=True),
        'picking_id': fields.many2one('stock.picking', 'Picking',readonly=True),
        'fees_lines': fields.one2many('mrp.repair.fee', 'repair_id', 'Fees Lines', readonly=True, states={'draft':[('readonly',False)]}),
        'internal_notes': fields.text('Internal Notes'),
        'quotation_notes': fields.text('Quotation Notes'),
        'company_id': fields.many2one('res.company', 'Company'),
        'deliver_bool': fields.boolean('Deliver', help="Check this box if you want to manage the delivery once the product is repaired and create a picking with selected product. Note that you can select the locations in the Info tab, if you have the extended view."),
        'invoiced': fields.boolean('Invoiced', readonly=True),
        'repaired': fields.boolean('Repaired', readonly=True),
        'amount_untaxed': fields.function(_amount_untaxed, string='Untaxed Amount',
            store={
                'mrp.repair': (lambda self, cr, uid, ids, c={}: ids, ['operations'], 10),
                'mrp.repair.line': (_get_lines, ['price_unit', 'price_subtotal', 'product_id', 'tax_id', 'product_uom_qty', 'product_uom'], 10),
            }),
        'amount_tax': fields.function(_amount_tax, string='Taxes',
            store={
                'mrp.repair': (lambda self, cr, uid, ids, c={}: ids, ['operations'], 10),
                'mrp.repair.line': (_get_lines, ['price_unit', 'price_subtotal', 'product_id', 'tax_id', 'product_uom_qty', 'product_uom'], 10),
            }),
        'amount_total': fields.function(_amount_total, string='Total',
            store={
                'mrp.repair': (lambda self, cr, uid, ids, c={}: ids, ['operations'], 10),
                'mrp.repair.line': (_get_lines, ['price_unit', 'price_subtotal', 'product_id', 'tax_id', 'product_uom_qty', 'product_uom'], 10),
            }),
    }

    _defaults = {
        'state': lambda *a: 'draft',
        'deliver_bool': lambda *a: True,
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'mrp.repair'),
        'invoice_method': lambda *a: 'none',
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.repair', context=context),
        'pricelist_id': lambda self, cr, uid,context : self.pool.get('product.pricelist').search(cr, uid, [('type','=','sale')])[0]
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'state':'draft',
            'repaired':False,
            'invoiced':False,
            'invoice_id': False,
            'picking_id': False,
            'name': self.pool.get('ir.sequence').get(cr, uid, 'mrp.repair'),
        })
        return super(mrp_repair, self).copy(cr, uid, id, default, context)

    def onchange_product_id(self, cr, uid, ids, product_id=None):
        """ On change of product sets some values.
        @param product_id: Changed product
        @return: Dictionary of values.
        """
        return {'value': {
                    'prodlot_id': False,
                    'move_id': False,
                    'guarantee_limit' :False,
                    'location_id':  False,
                    'location_dest_id': False,
                }
        }

    def onchange_move_id(self, cr, uid, ids, prod_id=False, move_id=False):
        """ On change of move id sets values of guarantee limit, source location,
        destination location, partner and partner address.
        @param prod_id: Id of product in current record.
        @param move_id: Changed move.
        @return: Dictionary of values.
        """
        data = {}
        data['value'] = {}
        if not prod_id:
            return data
        if move_id:
            move =  self.pool.get('stock.move').browse(cr, uid, move_id)
            product = self.pool.get('product.product').browse(cr, uid, prod_id)
            limit = datetime.strptime(move.date_expected, '%Y-%m-%d %H:%M:%S') + relativedelta(months=int(product.warranty))
            data['value']['guarantee_limit'] = limit.strftime('%Y-%m-%d')
            data['value']['location_id'] = move.location_dest_id.id
            data['value']['location_dest_id'] = move.location_dest_id.id
            if move.partner_id:
                data['value']['partner_id'] = move.partner_id.id
            else:
                data['value']['partner_id'] = False
            d = self.onchange_partner_id(cr, uid, ids, data['value']['partner_id'], data['value']['partner_id'])
            data['value'].update(d['value'])
        return data

    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def onchange_partner_id(self, cr, uid, ids, part, address_id):
        """ On change of partner sets the values of partner address,
        partner invoice address and pricelist.
        @param part: Changed id of partner.
        @param address_id: Address id from current record.
        @return: Dictionary of values.
        """
        part_obj = self.pool.get('res.partner')
        pricelist_obj = self.pool.get('product.pricelist')
        if not part:
            return {'value': {
                        'address_id': False,
                        'partner_invoice_id': False,
                        'pricelist_id': pricelist_obj.search(cr, uid, [('type','=','sale')])[0]
                    }
            }
        addr = part_obj.address_get(cr, uid, [part], ['delivery', 'invoice', 'default'])
        partner = part_obj.browse(cr, uid, part)
        pricelist = partner.property_product_pricelist and partner.property_product_pricelist.id or False
        return {'value': {
                    'address_id': addr['delivery'] or addr['default'],
                    'partner_invoice_id': addr['invoice'],
                    'pricelist_id': pricelist
                }
        }

    def onchange_lot_id(self, cr, uid, ids, lot, product_id):
        """ On change of Serial Number sets the values of source location,
        destination location, move and guarantee limit.
        @param lot: Changed id of Serial Number.
        @param product_id: Product id from current record.
        @return: Dictionary of values.
        """
        move_obj = self.pool.get('stock.move')
        data = {}
        data['value'] = {
            'location_id': False,
            'location_dest_id': False,
            'move_id': False,
            'guarantee_limit': False
        }

        if not lot:
            return data
        move_ids = move_obj.search(cr, uid, [('prodlot_id', '=', lot)])

        if not len(move_ids):
            return data

        def get_last_move(lst_move):
            while lst_move.move_dest_id and lst_move.move_dest_id.state == 'done':
                lst_move = lst_move.move_dest_id
            return lst_move

        move_id = move_ids[0]
        move = get_last_move(move_obj.browse(cr, uid, move_id))
        data['value']['move_id'] = move.id
        d = self.onchange_move_id(cr, uid, ids, product_id, move.id)
        data['value'].update(d['value'])
        return data

    def action_cancel_draft(self, cr, uid, ids, *args):
        """ Cancels repair order when it is in 'Draft' state.
        @param *arg: Arguments
        @return: True
        """
        if not len(ids):
            return False
        mrp_line_obj = self.pool.get('mrp.repair.line')
        for repair in self.browse(cr, uid, ids):
            mrp_line_obj.write(cr, uid, [l.id for l in repair.operations], {'state': 'draft'})
        self.write(cr, uid, ids, {'state':'draft'})
        wf_service = netsvc.LocalService("workflow")
        for id in ids:
            wf_service.trg_create(uid, 'mrp.repair', id, cr)
        return True

    def action_confirm(self, cr, uid, ids, *args):
        """ Repair order state is set to 'To be invoiced' when invoice method
        is 'Before repair' else state becomes 'Confirmed'.
        @param *arg: Arguments
        @return: True
        """
        mrp_line_obj = self.pool.get('mrp.repair.line')
        for o in self.browse(cr, uid, ids):
            if (o.invoice_method == 'b4repair'):
                self.write(cr, uid, [o.id], {'state': '2binvoiced'})
            else:
                self.write(cr, uid, [o.id], {'state': 'confirmed'})
                if not o.operations:
                    raise osv.except_osv(_('Error!'),_('You cannot confirm a repair order which has no line.'))
                for line in o.operations:
                    if line.product_id.track_production and not line.prodlot_id:
                        raise osv.except_osv(_('Warning'), _("Serial number is required for operation line with product '%s'") % (line.product_id.name))
                mrp_line_obj.write(cr, uid, [l.id for l in o.operations], {'state': 'confirmed'})
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        """ Cancels repair order.
        @return: True
        """
        mrp_line_obj = self.pool.get('mrp.repair.line')
        for repair in self.browse(cr, uid, ids, context=context):
            mrp_line_obj.write(cr, uid, [l.id for l in repair.operations], {'state': 'cancel'}, context=context)
        self.write(cr,uid,ids,{'state':'cancel'})
        return True

    def wkf_invoice_create(self, cr, uid, ids, *args):
        return self.action_invoice_create(cr, uid, ids)

    def action_invoice_create(self, cr, uid, ids, group=False, context=None):
        """ Creates invoice(s) for repair order.
        @param group: It is set to true when group invoice is to be generated.
        @return: Invoice Ids.
        """
        res = {}
        invoices_group = {}
        inv_line_obj = self.pool.get('account.invoice.line')
        inv_obj = self.pool.get('account.invoice')
        repair_line_obj = self.pool.get('mrp.repair.line')
        repair_fee_obj = self.pool.get('mrp.repair.fee')
        for repair in self.browse(cr, uid, ids, context=context):
            res[repair.id] = False
            if repair.state in ('draft','cancel') or repair.invoice_id:
                continue
            if not (repair.partner_id.id and repair.partner_invoice_id.id):
                raise osv.except_osv(_('No partner !'),_('You have to select a Partner Invoice Address in the repair form !'))
            comment = repair.quotation_notes
            if (repair.invoice_method != 'none'):
                if group and repair.partner_invoice_id.id in invoices_group:
                    inv_id = invoices_group[repair.partner_invoice_id.id]
                    invoice = inv_obj.browse(cr, uid, inv_id)
                    invoice_vals = {
                        'name': invoice.name +', '+repair.name,
                        'origin': invoice.origin+', '+repair.name,
                        'comment':(comment and (invoice.comment and invoice.comment+"\n"+comment or comment)) or (invoice.comment and invoice.comment or ''),
                    }
                    inv_obj.write(cr, uid, [inv_id], invoice_vals, context=context)
                else:
                    if not repair.partner_id.property_account_receivable:
                        raise osv.except_osv(_('Error!'), _('No account defined for partner "%s".') % repair.partner_id.name )
                    account_id = repair.partner_id.property_account_receivable.id
                    inv = {
                        'name': repair.name,
                        'origin':repair.name,
                        'type': 'out_invoice',
                        'account_id': account_id,
                        'partner_id': repair.partner_id.id,
                        'currency_id': repair.pricelist_id.currency_id.id,
                        'comment': repair.quotation_notes,
                        'fiscal_position': repair.partner_id.property_account_position.id
                    }
                    inv_id = inv_obj.create(cr, uid, inv)
                    invoices_group[repair.partner_invoice_id.id] = inv_id
                self.write(cr, uid, repair.id, {'invoiced': True, 'invoice_id': inv_id})

                for operation in repair.operations:
                    if operation.to_invoice == True:
                        if group:
                            name = repair.name + '-' + operation.name
                        else:
                            name = operation.name

                        if operation.product_id.property_account_income:
                            account_id = operation.product_id.property_account_income.id
                        elif operation.product_id.categ_id.property_account_income_categ:
                            account_id = operation.product_id.categ_id.property_account_income_categ.id
                        else:
                            raise osv.except_osv(_('Error!'), _('No account defined for product "%s".') % operation.product_id.name )

                        invoice_line_id = inv_line_obj.create(cr, uid, {
                            'invoice_id': inv_id,
                            'name': name,
                            'origin': repair.name,
                            'account_id': account_id,
                            'quantity': operation.product_uom_qty,
                            'invoice_line_tax_id': [(6,0,[x.id for x in operation.tax_id])],
                            'uos_id': operation.product_uom.id,
                            'price_unit': operation.price_unit,
                            'price_subtotal': operation.product_uom_qty*operation.price_unit,
                            'product_id': operation.product_id and operation.product_id.id or False
                        })
                        repair_line_obj.write(cr, uid, [operation.id], {'invoiced': True, 'invoice_line_id': invoice_line_id})
                for fee in repair.fees_lines:
                    if fee.to_invoice == True:
                        if group:
                            name = repair.name + '-' + fee.name
                        else:
                            name = fee.name
                        if not fee.product_id:
                            raise osv.except_osv(_('Warning !'), _('No product defined on Fees!'))

                        if fee.product_id.property_account_income:
                            account_id = fee.product_id.property_account_income.id
                        elif fee.product_id.categ_id.property_account_income_categ:
                            account_id = fee.product_id.categ_id.property_account_income_categ.id
                        else:
                            raise osv.except_osv(_('Error!'), _('No account defined for product "%s".') % fee.product_id.name)

                        invoice_fee_id = inv_line_obj.create(cr, uid, {
                            'invoice_id': inv_id,
                            'name': name,
                            'origin': repair.name,
                            'account_id': account_id,
                            'quantity': fee.product_uom_qty,
                            'invoice_line_tax_id': [(6,0,[x.id for x in fee.tax_id])],
                            'uos_id': fee.product_uom.id,
                            'product_id': fee.product_id and fee.product_id.id or False,
                            'price_unit': fee.price_unit,
                            'price_subtotal': fee.product_uom_qty*fee.price_unit
                        })
                        repair_fee_obj.write(cr, uid, [fee.id], {'invoiced': True, 'invoice_line_id': invoice_fee_id})
                res[repair.id] = inv_id
        return res

    def action_repair_ready(self, cr, uid, ids, context=None):
        """ Writes repair order state to 'Ready'
        @return: True
        """
        for repair in self.browse(cr, uid, ids, context=context):
            self.pool.get('mrp.repair.line').write(cr, uid, [l.id for
                    l in repair.operations], {'state': 'confirmed'}, context=context)
            self.write(cr, uid, [repair.id], {'state': 'ready'})
        return True

    def action_repair_start(self, cr, uid, ids, context=None):
        """ Writes repair order state to 'Under Repair'
        @return: True
        """
        repair_line = self.pool.get('mrp.repair.line')
        for repair in self.browse(cr, uid, ids, context=context):
            repair_line.write(cr, uid, [l.id for
                    l in repair.operations], {'state': 'confirmed'}, context=context)
            repair.write({'state': 'under_repair'})
        return True

    def action_repair_end(self, cr, uid, ids, context=None):
        """ Writes repair order state to 'To be invoiced' if invoice method is
        After repair else state is set to 'Ready'.
        @return: True
        """
        for order in self.browse(cr, uid, ids, context=context):
            val = {}
            val['repaired'] = True
            if (not order.invoiced and order.invoice_method=='after_repair'):
                val['state'] = '2binvoiced'
            elif (not order.invoiced and order.invoice_method=='b4repair'):
                val['state'] = 'ready'
            else:
                pass
            self.write(cr, uid, [order.id], val)
        return True

    def wkf_repair_done(self, cr, uid, ids, *args):
        self.action_repair_done(cr, uid, ids)
        return True

    def action_repair_done(self, cr, uid, ids, context=None):
        """ Creates stock move and picking for repair order.
        @return: Picking ids.
        """
        res = {}
        move_obj = self.pool.get('stock.move')
        wf_service = netsvc.LocalService("workflow")
        repair_line_obj = self.pool.get('mrp.repair.line')
        seq_obj = self.pool.get('ir.sequence')
        pick_obj = self.pool.get('stock.picking')
        for repair in self.browse(cr, uid, ids, context=context):
            for move in repair.operations:
                move_id = move_obj.create(cr, uid, {
                    'name': move.name,
                    'product_id': move.product_id.id,
                    'product_qty': move.product_uom_qty,
                    'product_uom': move.product_uom.id,
                    'partner_id': repair.address_id and repair.address_id.id or False,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'tracking_id': False,
                    'prodlot_id': move.prodlot_id and move.prodlot_id.id or False,
                    'state': 'done',
                })
                repair_line_obj.write(cr, uid, [move.id], {'move_id': move_id, 'state': 'done'}, context=context)
            if repair.deliver_bool:
                pick_name = seq_obj.get(cr, uid, 'stock.picking.out')
                picking = pick_obj.create(cr, uid, {
                    'name': pick_name,
                    'origin': repair.name,
                    'state': 'draft',
                    'move_type': 'one',
                    'partner_id': repair.address_id and repair.address_id.id or False,
                    'note': repair.internal_notes,
                    'invoice_state': 'none',
                    'type': 'out',
                })
                move_id = move_obj.create(cr, uid, {
                    'name': repair.name,
                    'picking_id': picking,
                    'product_id': repair.product_id.id,
                    'product_qty': move.product_uom_qty or 1.0,
                    'product_uom': repair.product_id.uom_id.id,
                    'prodlot_id': repair.prodlot_id and repair.prodlot_id.id or False,
                    'partner_id': repair.address_id and repair.address_id.id or False,
                    'location_id': repair.location_id.id,
                    'location_dest_id': repair.location_dest_id.id,
                    'tracking_id': False,
                    'state': 'assigned',
                })
                wf_service.trg_validate(uid, 'stock.picking', picking, 'button_confirm', cr)
                self.write(cr, uid, [repair.id], {'state': 'done', 'picking_id': picking})
                res[repair.id] = picking
            else:
                self.write(cr, uid, [repair.id], {'state': 'done'})
        return res


mrp_repair()


class ProductChangeMixin(object):
    def product_id_change(self, cr, uid, ids, pricelist, product, uom=False,
                          product_uom_qty=0, partner_id=False, guarantee_limit=False):
        """ On change of product it sets product quantity, tax account, name,
        uom of product, unit price and price subtotal.
        @param pricelist: Pricelist of current record.
        @param product: Changed id of product.
        @param uom: UoM of current record.
        @param product_uom_qty: Quantity of current record.
        @param partner_id: Partner of current record.
        @param guarantee_limit: Guarantee limit of current record.
        @return: Dictionary of values and warning message.
        """
        result = {}
        warning = {}

        if not product_uom_qty:
            product_uom_qty = 1
        result['product_uom_qty'] = product_uom_qty

        if product:
            product_obj = self.pool.get('product.product').browse(cr, uid, product)
            if partner_id:
                partner = self.pool.get('res.partner').browse(cr, uid, partner_id)
                result['tax_id'] = self.pool.get('account.fiscal.position').map_tax(cr, uid, partner.property_account_position, product_obj.taxes_id)

            result['name'] = product_obj.partner_ref
            result['product_uom'] = product_obj.uom_id and product_obj.uom_id.id or False
            if not pricelist:
                warning = {
                    'title':'No Pricelist !',
                    'message':
                        'You have to select a pricelist in the Repair form !\n'
                        'Please set one before choosing a product.'
                }
            else:
                price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                            product, product_uom_qty, partner_id, {'uom': uom,})[pricelist]

                if price is False:
                     warning = {
                        'title':'No valid pricelist line found !',
                        'message':
                            "Couldn't find a pricelist line matching this product and quantity.\n"
                            "You have to change either the product, the quantity or the pricelist."
                     }
                else:
                    result.update({'price_unit': price, 'price_subtotal': price*product_uom_qty})

        return {'value': result, 'warning': warning}


class mrp_repair_line(osv.osv, ProductChangeMixin):
    _name = 'mrp.repair.line'
    _description = 'Repair Line'

    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default: default = {}
        default.update( {'invoice_line_id': False, 'move_id': False, 'invoiced': False, 'state': 'draft'})
        return super(mrp_repair_line, self).copy_data(cr, uid, id, default, context)

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        """ Calculates amount.
        @param field_name: Name of field.
        @param arg: Argument
        @return: Dictionary of values.
        """
        res = {}
        cur_obj=self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.to_invoice and line.price_unit * line.product_uom_qty or 0
            cur = line.repair_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
        return res

    _columns = {
        'name' : fields.char('Description',size=64,required=True),
        'repair_id': fields.many2one('mrp.repair', 'Repair Order Reference',ondelete='cascade', select=True),
        'type': fields.selection([('add','Add'),('remove','Remove')],'Type', required=True),
        'to_invoice': fields.boolean('To Invoice'),
        'product_id': fields.many2one('product.product', 'Product', domain=[('sale_ok','=',True)], required=True),
        'invoiced': fields.boolean('Invoiced',readonly=True),
        'price_unit': fields.float('Unit Price', required=True, digits_compute= dp.get_precision('Sale Price')),
        'price_subtotal': fields.function(_amount_line, string='Subtotal',digits_compute= dp.get_precision('Sale Price')),
        'tax_id': fields.many2many('account.tax', 'repair_operation_line_tax', 'repair_operation_line_id', 'tax_id', 'Taxes'),
        'product_uom_qty': fields.float('Quantity (Unit of Measure)', digits=(16,2), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'prodlot_id': fields.many2one('stock.production.lot', 'Lot Number',domain="[('product_id','=',product_id)]"),
        'invoice_line_id': fields.many2one('account.invoice.line', 'Invoice Line', readonly=True),
        'location_id': fields.many2one('stock.location', 'Source Location', required=True, select=True),
        'location_dest_id': fields.many2one('stock.location', 'Dest. Location', required=True, select=True),
        'move_id': fields.many2one('stock.move', 'Inventory Move', readonly=True),
        'state': fields.selection([
                    ('draft','Draft'),
                    ('confirmed','Confirmed'),
                    ('done','Done'),
                    ('cancel','Canceled')], 'Status', required=True, readonly=True,
                    help=' * The \'Draft\' state is set automatically as draft when repair order in draft state. \
                        \n* The \'Confirmed\' state is set automatically as confirm when repair order in confirm state. \
                        \n* The \'Done\' state is set automatically when repair order is completed.\
                        \n* The \'Cancelled\' state is set automatically when user cancel repair order.'),
    }
    _defaults = {
     'state': lambda *a: 'draft',
     'product_uom_qty': lambda *a: 1,
    }

    def onchange_operation_type(self, cr, uid, ids, type, guarantee_limit, company_id=False, context=None):
        """ On change of operation type it sets source location, destination location
        and to invoice field.
        @param product: Changed operation type.
        @param guarantee_limit: Guarantee limit of current record.
        @return: Dictionary of values.
        """
        if not type:
            return {'value': {
                'location_id': False,
                'location_dest_id': False
                }}
        warehouse_obj = self.pool.get('stock.warehouse')
        location_id = self.pool.get('stock.location').search(cr, uid, [('usage','=','production')], context=context)
        location_id = location_id and location_id[0] or False

        if type == 'add':
            # TOCHECK: Find stock location for user's company warehouse or
            # repair order's company's warehouse (company_id field is added in fix of lp:831583)
            args = company_id and [('company_id', '=', company_id)] or []
            warehouse_ids = warehouse_obj.search(cr, uid, args, context=context)
            stock_id = False
            if warehouse_ids:
                stock_id = warehouse_obj.browse(cr, uid, warehouse_ids[0], context=context).lot_stock_id.id
            to_invoice = (guarantee_limit and datetime.strptime(guarantee_limit, '%Y-%m-%d') < datetime.now())

            return {'value': {
                'to_invoice': to_invoice,
                'location_id': stock_id,
                'location_dest_id': location_id
                }}

        return {'value': {
                'to_invoice': False,
                'location_id': location_id,
                'location_dest_id': False
                }}

mrp_repair_line()

class mrp_repair_fee(osv.osv, ProductChangeMixin):
    _name = 'mrp.repair.fee'
    _description = 'Repair Fees Line'

    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default: default = {}
        default.update({'invoice_line_id': False, 'invoiced': False})
        return super(mrp_repair_fee, self).copy_data(cr, uid, id, default, context)

    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        """ Calculates amount.
        @param field_name: Name of field.
        @param arg: Argument
        @return: Dictionary of values.
        """
        res = {}
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.to_invoice and line.price_unit * line.product_uom_qty or 0
            cur = line.repair_id.pricelist_id.currency_id
            res[line.id] = cur_obj.round(cr, uid, cur, res[line.id])
        return res

    _columns = {
        'repair_id': fields.many2one('mrp.repair', 'Repair Order Reference', required=True, ondelete='cascade', select=True),
        'name': fields.char('Description', size=64, select=True,required=True),
        'product_id': fields.many2one('product.product', 'Product'),
        'product_uom_qty': fields.float('Quantity', digits=(16,2), required=True),
        'price_unit': fields.float('Unit Price', required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'price_subtotal': fields.function(_amount_line, string='Subtotal',digits_compute= dp.get_precision('Sale Price')),
        'tax_id': fields.many2many('account.tax', 'repair_fee_line_tax', 'repair_fee_line_id', 'tax_id', 'Taxes'),
        'invoice_line_id': fields.many2one('account.invoice.line', 'Invoice Line', readonly=True),
        'to_invoice': fields.boolean('To Invoice'),
        'invoiced': fields.boolean('Invoiced',readonly=True),
    }
    _defaults = {
        'to_invoice': lambda *a: True,
    }

mrp_repair_fee()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
