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

from openerp.osv import fields, osv
from datetime import datetime
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class mrp_repair(osv.osv):
    _name = 'mrp.repair'
    _inherit = 'mail.thread'
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
                    tax_calculate = tax_obj.compute_all(cr, uid, line.tax_id, line.price_unit, line.product_uom_qty, line.product_id, repair.partner_id)
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
        return self.pool['mrp.repair'].search(cr, uid, [('operations', 'in', ids)], context=context)

    def _get_fee_lines(self, cr, uid, ids, context=None):
        return self.pool['mrp.repair'].search(cr, uid, [('fees_lines', 'in', ids)], context=context)

    _columns = {
        'name': fields.char('Repair Reference', required=True, states={'confirmed': [('readonly', True)]}),
        'product_id': fields.many2one('product.product', string='Product to Repair', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_qty': fields.float('Product Quantity', digits_compute=dp.get_precision('Product Unit of Measure'),
                                    required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'partner_id': fields.many2one('res.partner', 'Partner', select=True, help='Choose partner for whom the order will be invoiced and delivered.', states={'confirmed': [('readonly', True)]}),
        'address_id': fields.many2one('res.partner', 'Delivery Address', domain="[('parent_id','=',partner_id)]", states={'confirmed': [('readonly', True)]}),
        'default_address_id': fields.function(_get_default_address, type="many2one", relation="res.partner"),
        'state': fields.selection([
            ('draft', 'Quotation'),
            ('cancel', 'Cancelled'),
            ('confirmed', 'Confirmed'),
            ('under_repair', 'Under Repair'),
            ('ready', 'Ready to Repair'),
            ('2binvoiced', 'To be Invoiced'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Repaired')
            ], 'Status', readonly=True, track_visibility='onchange',
            help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed repair order. \
            \n* The \'Confirmed\' status is used when a user confirms the repair order. \
            \n* The \'Ready to Repair\' status is used to start to repairing, user can start repairing only after repair order is confirmed. \
            \n* The \'To be Invoiced\' status is used to generate the invoice before or after repairing done. \
            \n* The \'Done\' status is set when repairing is completed.\
            \n* The \'Cancelled\' status is used when user cancel repair order.'),
        'location_id': fields.many2one('stock.location', 'Current Location', select=True, required=True, readonly=True, states={'draft': [('readonly', False)], 'confirmed': [('readonly', True)]}),
        'location_dest_id': fields.many2one('stock.location', 'Delivery Location', readonly=True, required=True, states={'draft': [('readonly', False)], 'confirmed': [('readonly', True)]}),
        'lot_id': fields.many2one('stock.production.lot', 'Repaired Lot', domain="[('product_id','=', product_id)]", help="Products repaired are all belonging to this lot"),
        'guarantee_limit': fields.date('Warranty Expiration', help="The warranty expiration limit is computed as: last move date + warranty defined on selected product. If the current date is below the warranty expiration limit, each operation and fee you will add will be set as 'not to invoiced' by default. Note that you can change manually afterwards.", states={'confirmed': [('readonly', True)]}),
        'operations': fields.one2many('mrp.repair.line', 'repair_id', 'Operation Lines', readonly=True, states={'draft': [('readonly', False)]}),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', help='Pricelist of the selected partner.'),
        'partner_invoice_id': fields.many2one('res.partner', 'Invoicing Address'),
        'invoice_method': fields.selection([
            ("none", "No Invoice"),
            ("b4repair", "Before Repair"),
            ("after_repair", "After Repair")
           ], "Invoice Method",
            select=True, required=True, states={'draft': [('readonly', False)]}, readonly=True, help='Selecting \'Before Repair\' or \'After Repair\' will allow you to generate invoice before or after the repair is done respectively. \'No invoice\' means you don\'t want to generate invoice for this repair order.'),
        'invoice_id': fields.many2one('account.invoice', 'Invoice', readonly=True, track_visibility="onchange"),
        'move_id': fields.many2one('stock.move', 'Move', readonly=True, help="Move created by the repair order", track_visibility="onchange"),
        'fees_lines': fields.one2many('mrp.repair.fee', 'repair_id', 'Fees', readonly=True, states={'draft': [('readonly', False)]}),
        'internal_notes': fields.text('Internal Notes'),
        'quotation_notes': fields.text('Quotation Notes'),
        'company_id': fields.many2one('res.company', 'Company'),
        'invoiced': fields.boolean('Invoiced', readonly=True),
        'repaired': fields.boolean('Repaired', readonly=True),
        'amount_untaxed': fields.function(_amount_untaxed, string='Untaxed Amount',
            store={
                'mrp.repair': (lambda self, cr, uid, ids, c={}: ids, ['operations', 'fees_lines'], 10),
                'mrp.repair.line': (_get_lines, ['price_unit', 'price_subtotal', 'product_id', 'tax_id', 'product_uom_qty', 'product_uom'], 10),
                'mrp.repair.fee': (_get_fee_lines, ['price_unit', 'price_subtotal', 'product_id', 'tax_id', 'product_uom_qty', 'product_uom'], 10),
            }),
        'amount_tax': fields.function(_amount_tax, string='Taxes',
            store={
                'mrp.repair': (lambda self, cr, uid, ids, c={}: ids, ['operations', 'fees_lines'], 10),
                'mrp.repair.line': (_get_lines, ['price_unit', 'price_subtotal', 'product_id', 'tax_id', 'product_uom_qty', 'product_uom'], 10),
                'mrp.repair.fee': (_get_fee_lines, ['price_unit', 'price_subtotal', 'product_id', 'tax_id', 'product_uom_qty', 'product_uom'], 10),
            }),
        'amount_total': fields.function(_amount_total, string='Total',
            store={
                'mrp.repair': (lambda self, cr, uid, ids, c={}: ids, ['operations', 'fees_lines'], 10),
                'mrp.repair.line': (_get_lines, ['price_unit', 'price_subtotal', 'product_id', 'tax_id', 'product_uom_qty', 'product_uom'], 10),
                'mrp.repair.fee': (_get_fee_lines, ['price_unit', 'price_subtotal', 'product_id', 'tax_id', 'product_uom_qty', 'product_uom'], 10),
            }),
    }

    def _default_stock_location(self, cr, uid, context=None):
        try:
            warehouse = self.pool.get('ir.model.data').get_object(cr, uid, 'stock', 'warehouse0')
            return warehouse.lot_stock_id.id
        except:
            return False

    _defaults = {
        'state': lambda *a: 'draft',
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'mrp.repair'),
        'invoice_method': lambda *a: 'none',
        'company_id': lambda self, cr, uid, context: self.pool.get('res.company')._company_default_get(cr, uid, 'mrp.repair', context=context),
        'pricelist_id': lambda self, cr, uid, context: self.pool.get('product.pricelist').search(cr, uid, [('type', '=', 'sale')])[0],
        'product_qty': 1.0,
        'location_id': _default_stock_location,
    }

    _sql_constraints = [
        ('name', 'unique (name)', 'The name of the Repair Order must be unique!'),
    ]

    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'state': 'draft',
            'repaired': False,
            'invoiced': False,
            'invoice_id': False,
            'move_id': False,
            'name': self.pool.get('ir.sequence').get(cr, uid, 'mrp.repair'),
        })
        return super(mrp_repair, self).copy(cr, uid, id, default, context)

    def onchange_product_id(self, cr, uid, ids, product_id=None):
        """ On change of product sets some values.
        @param product_id: Changed product
        @return: Dictionary of values.
        """
        product = False
        if product_id:
            product = self.pool.get("product.product").browse(cr, uid, product_id)
        return {'value': {
                    'guarantee_limit': False,
                    'lot_id': False,
                    'product_uom': product and product.uom_id.id or False,
                }
        }

    def onchange_product_uom(self, cr, uid, ids, product_id, product_uom, context=None):
        res = {'value': {}}
        if not product_uom or not product_id:
            return res
        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        uom = self.pool.get('product.uom').browse(cr, uid, product_uom, context=context)
        if uom.category_id.id != product.uom_id.category_id.id:
            res['warning'] = {'title': _('Warning'), 'message': _('The Product Unit of Measure you chose has a different category than in the product form.')}
            res['value'].update({'product_uom': product.uom_id.id})
        return res

    def onchange_location_id(self, cr, uid, ids, location_id=None):
        """ On change of location
        """
        return {'value': {'location_dest_id': location_id}}

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
                        'pricelist_id': pricelist_obj.search(cr, uid, [('type', '=', 'sale')])[0]
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
        self.write(cr, uid, ids, {'state': 'draft'})
        return self.create_workflow(cr, uid, ids)

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
                for line in o.operations:
                    if line.product_id.track_production:
                        raise osv.except_osv(_('Warning!'), _("Serial number is required for operation line with product '%s'") % (line.product_id.name))
                mrp_line_obj.write(cr, uid, [l.id for l in o.operations], {'state': 'confirmed'})
        return True

    def action_cancel(self, cr, uid, ids, context=None):
        """ Cancels repair order.
        @return: True
        """
        mrp_line_obj = self.pool.get('mrp.repair.line')
        for repair in self.browse(cr, uid, ids, context=context):
            if not repair.invoiced:
                mrp_line_obj.write(cr, uid, [l.id for l in repair.operations], {'state': 'cancel'}, context=context)
            else:
                raise osv.except_osv(_('Warning!'), _('Repair order is already invoiced.'))
        return self.write(cr, uid, ids, {'state': 'cancel'})

    def wkf_invoice_create(self, cr, uid, ids, *args):
        self.action_invoice_create(cr, uid, ids)
        return True

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
            if repair.state in ('draft', 'cancel') or repair.invoice_id:
                continue
            if not (repair.partner_id.id and repair.partner_invoice_id.id):
                raise osv.except_osv(_('No partner!'), _('You have to select a Partner Invoice Address in the repair form!'))
            comment = repair.quotation_notes
            if (repair.invoice_method != 'none'):
                if group and repair.partner_invoice_id.id in invoices_group:
                    inv_id = invoices_group[repair.partner_invoice_id.id]
                    invoice = inv_obj.browse(cr, uid, inv_id)
                    invoice_vals = {
                        'name': invoice.name + ', ' + repair.name,
                        'origin': invoice.origin + ', ' + repair.name,
                        'comment': (comment and (invoice.comment and invoice.comment + "\n" + comment or comment)) or (invoice.comment and invoice.comment or ''),
                    }
                    inv_obj.write(cr, uid, [inv_id], invoice_vals, context=context)
                else:
                    if not repair.partner_id.property_account_receivable:
                        raise osv.except_osv(_('Error!'), _('No account defined for partner "%s".') % repair.partner_id.name)
                    account_id = repair.partner_id.property_account_receivable.id
                    inv = {
                        'name': repair.name,
                        'origin': repair.name,
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
                    if operation.to_invoice:
                        if group:
                            name = repair.name + '-' + operation.name
                        else:
                            name = operation.name

                        if operation.product_id.property_account_income:
                            account_id = operation.product_id.property_account_income.id
                        elif operation.product_id.categ_id.property_account_income_categ:
                            account_id = operation.product_id.categ_id.property_account_income_categ.id
                        else:
                            raise osv.except_osv(_('Error!'), _('No account defined for product "%s".') % operation.product_id.name)

                        invoice_line_id = inv_line_obj.create(cr, uid, {
                            'invoice_id': inv_id,
                            'name': name,
                            'origin': repair.name,
                            'account_id': account_id,
                            'quantity': operation.product_uom_qty,
                            'invoice_line_tax_id': [(6, 0, [x.id for x in operation.tax_id])],
                            'uos_id': operation.product_uom.id,
                            'price_unit': operation.price_unit,
                            'price_subtotal': operation.product_uom_qty * operation.price_unit,
                            'product_id': operation.product_id and operation.product_id.id or False
                        })
                        repair_line_obj.write(cr, uid, [operation.id], {'invoiced': True, 'invoice_line_id': invoice_line_id})
                for fee in repair.fees_lines:
                    if fee.to_invoice:
                        if group:
                            name = repair.name + '-' + fee.name
                        else:
                            name = fee.name
                        if not fee.product_id:
                            raise osv.except_osv(_('Warning!'), _('No product defined on Fees!'))

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
                            'invoice_line_tax_id': [(6, 0, [x.id for x in fee.tax_id])],
                            'uos_id': fee.product_uom.id,
                            'product_id': fee.product_id and fee.product_id.id or False,
                            'price_unit': fee.price_unit,
                            'price_subtotal': fee.product_uom_qty * fee.price_unit
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
            if (not order.invoiced and order.invoice_method == 'after_repair'):
                val['state'] = '2binvoiced'
            elif (not order.invoiced and order.invoice_method == 'b4repair'):
                val['state'] = 'ready'
            else:
                pass
            self.write(cr, uid, [order.id], val)
        return True

    def wkf_repair_done(self, cr, uid, ids, *args):
        self.action_repair_done(cr, uid, ids)
        return True

    def action_repair_done(self, cr, uid, ids, context=None):
        """ Creates stock move for operation and stock move for final product of repair order.
        @return: Move ids of final products
        """
        res = {}
        move_obj = self.pool.get('stock.move')
        repair_line_obj = self.pool.get('mrp.repair.line')
        for repair in self.browse(cr, uid, ids, context=context):
            move_ids = []
            for move in repair.operations:
                move_id = move_obj.create(cr, uid, {
                    'name': move.name,
                    'product_id': move.product_id.id,
                    'restrict_lot_id': move.lot_id.id,
                    'product_uom_qty': move.product_uom_qty,
                    'product_uom': move.product_uom.id,
                    'partner_id': repair.address_id and repair.address_id.id or False,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'state': 'assigned',
                })
                move_ids.append(move_id)
                repair_line_obj.write(cr, uid, [move.id], {'move_id': move_id, 'state': 'done'}, context=context)
            move_id = move_obj.create(cr, uid, {
                'name': repair.name,
                'product_id': repair.product_id.id,
                'product_uom': repair.product_uom.id or repair.product_id.uom_id.id,
                'product_uom_qty': repair.product_qty,
                'partner_id': repair.address_id and repair.address_id.id or False,
                'location_id': repair.location_id.id,
                'location_dest_id': repair.location_dest_id.id,
                'restrict_lot_id': repair.lot_id.id,
            })
            move_ids.append(move_id)
            move_obj.action_done(cr, uid, move_ids, context=context)
            self.write(cr, uid, [repair.id], {'state': 'done', 'move_id': move_id}, context=context)
            res[repair.id] = move_id
        return res


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
                    'title': _('No Pricelist!'),
                    'message':
                        _('You have to select a pricelist in the Repair form !\n'
                        'Please set one before choosing a product.')
                }
            else:
                price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                            product, product_uom_qty, partner_id, {'uom': uom})[pricelist]

                if price is False:
                    warning = {
                        'title': _('No valid pricelist line found !'),
                        'message':
                            _("Couldn't find a pricelist line matching this product and quantity.\n"
                            "You have to change either the product, the quantity or the pricelist.")
                     }
                else:
                    result.update({'price_unit': price, 'price_subtotal': price * product_uom_qty})

        return {'value': result, 'warning': warning}


class mrp_repair_line(osv.osv, ProductChangeMixin):
    _name = 'mrp.repair.line'
    _description = 'Repair Line'

    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({'invoice_line_id': False, 'move_id': False, 'invoiced': False, 'state': 'draft'})
        return super(mrp_repair_line, self).copy_data(cr, uid, id, default, context)

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
        'name': fields.char('Description', required=True),
        'repair_id': fields.many2one('mrp.repair', 'Repair Order Reference', ondelete='cascade', select=True),
        'type': fields.selection([('add', 'Add'), ('remove', 'Remove')], 'Type', required=True),
        'to_invoice': fields.boolean('To Invoice'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'invoiced': fields.boolean('Invoiced', readonly=True),
        'price_unit': fields.float('Unit Price', required=True, digits_compute=dp.get_precision('Product Price')),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute=dp.get_precision('Account')),
        'tax_id': fields.many2many('account.tax', 'repair_operation_line_tax', 'repair_operation_line_id', 'tax_id', 'Taxes'),
        'product_uom_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'invoice_line_id': fields.many2one('account.invoice.line', 'Invoice Line', readonly=True),
        'location_id': fields.many2one('stock.location', 'Source Location', required=True, select=True),
        'location_dest_id': fields.many2one('stock.location', 'Dest. Location', required=True, select=True),
        'move_id': fields.many2one('stock.move', 'Inventory Move', readonly=True),
        'lot_id': fields.many2one('stock.production.lot', 'Lot'),
        'state': fields.selection([
                    ('draft', 'Draft'),
                    ('confirmed', 'Confirmed'),
                    ('done', 'Done'),
                    ('cancel', 'Cancelled')], 'Status', required=True, readonly=True,
                    help=' * The \'Draft\' status is set automatically as draft when repair order in draft status. \
                        \n* The \'Confirmed\' status is set automatically as confirm when repair order in confirm status. \
                        \n* The \'Done\' status is set automatically when repair order is completed.\
                        \n* The \'Cancelled\' status is set automatically when user cancel repair order.'),
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
        location_obj = self.pool.get('stock.location')
        warehouse_obj = self.pool.get('stock.warehouse')
        location_id = location_obj.search(cr, uid, [('usage', '=', 'production')], context=context)
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
        scrap_location_ids = location_obj.search(cr, uid, [('scrap_location', '=', True)], context=context)

        return {'value': {
                'to_invoice': False,
                'location_id': location_id,
                'location_dest_id': scrap_location_ids and scrap_location_ids[0] or False,
                }}


class mrp_repair_fee(osv.osv, ProductChangeMixin):
    _name = 'mrp.repair.fee'
    _description = 'Repair Fees Line'

    def copy_data(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
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
        'name': fields.char('Description', select=True, required=True),
        'product_id': fields.many2one('product.product', 'Product'),
        'product_uom_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True),
        'price_unit': fields.float('Unit Price', required=True),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure', required=True),
        'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute=dp.get_precision('Account')),
        'tax_id': fields.many2many('account.tax', 'repair_fee_line_tax', 'repair_fee_line_id', 'tax_id', 'Taxes'),
        'invoice_line_id': fields.many2one('account.invoice.line', 'Invoice Line', readonly=True),
        'to_invoice': fields.boolean('To Invoice'),
        'invoiced': fields.boolean('Invoiced', readonly=True),
    }

    _defaults = {
        'to_invoice': lambda *a: True,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
