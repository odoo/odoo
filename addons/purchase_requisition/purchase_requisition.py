# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp

class purchase_requisition(osv.osv):
    _name = "purchase.requisition"
    _description = "Purchase Requisition"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _get_po_line(self, cr, uid, ids, field_names, arg=None, context=None):
        result = dict((res_id, []) for res_id in ids)
        for element in self.browse(cr, uid, ids, context=context):
            for po in element.purchase_ids:
                result[element.id] += [po_line.id for po_line in po.order_line]
        return result

    _columns = {
        'name': fields.char('Call for Bids Reference', required=True, copy=False),
        'origin': fields.char('Source Document'),
        'ordering_date': fields.date('Scheduled Ordering Date'),
        'date_end': fields.datetime('Bid Submission Deadline'),
        'schedule_date': fields.date('Scheduled Date', select=True, help="The expected and scheduled date where all the products are received"),
        'user_id': fields.many2one('res.users', 'Responsible'),
        'exclusive': fields.selection([('exclusive', 'Select only one RFQ (exclusive)'), ('multiple', 'Select multiple RFQ')], 'Bid Selection Type', required=True, help="Select only one RFQ (exclusive):  On the confirmation of a purchase order, it cancels the remaining purchase order.\nSelect multiple RFQ:  It allows to have multiple purchase orders.On confirmation of a purchase order it does not cancel the remaining orders"""),
        'description': fields.text('Description'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'purchase_ids': fields.one2many('purchase.order', 'requisition_id', 'Purchase Orders', states={'done': [('readonly', True)]}),
        'po_line_ids': fields.function(_get_po_line, method=True, type='one2many', relation='purchase.order.line', string='Products by supplier'),
        'line_ids': fields.one2many('purchase.requisition.line', 'requisition_id', 'Products to Purchase', states={'done': [('readonly', True)]}, copy=True),
        'procurement_id': fields.many2one('procurement.order', 'Procurement', ondelete='set null', copy=False),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
        'state': fields.selection([('draft', 'Draft'), ('in_progress', 'Confirmed'),
                                   ('open', 'Bid Selection'), ('done', 'PO Created'),
                                   ('cancel', 'Cancelled')],
                                  'Status', track_visibility='onchange', required=True,
                                  copy=False),
        'multiple_rfq_per_supplier': fields.boolean('Multiple RFQ per supplier'),
        'account_analytic_id': fields.many2one('account.analytic.account', 'Analytic Account'),
        'picking_type_id': fields.many2one('stock.picking.type', 'Picking Type', required=True),
    }

    def _get_picking_in(self, cr, uid, context=None):
        obj_data = self.pool.get('ir.model.data')
        return obj_data.get_object_reference(cr, uid, 'stock', 'picking_type_in')[1]

    _defaults = {
        'state': 'draft',
        'exclusive': 'multiple',
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'purchase.requisition', context=c),
        'user_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).id,
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'purchase.order.requisition'),
        'picking_type_id': _get_picking_in,
    }

    def tender_cancel(self, cr, uid, ids, context=None):
        purchase_order_obj = self.pool.get('purchase.order')
        # try to set all associated quotations to cancel state
        for tender in self.browse(cr, uid, ids, context=context):
            for purchase_order in tender.purchase_ids:
                purchase_order_obj.action_cancel(cr, uid, [purchase_order.id], context=context)
                purchase_order_obj.message_post(cr, uid, [purchase_order.id], body=_('Cancelled by the tender associated to this quotation.'), context=context)
        return self.write(cr, uid, ids, {'state': 'cancel'})

    def tender_in_progress(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'in_progress'}, context=context)

    def tender_open(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'open'}, context=context)

    def tender_reset(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'draft'})
        for p_id in ids:
            # Deleting the existing instance of workflow for PO
            self.delete_workflow(cr, uid, [p_id])
            self.create_workflow(cr, uid, [p_id])
        return True

    def tender_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def open_product_line(self, cr, uid, ids, context=None):
        """ This opens product line view to view all lines from the different quotations, groupby default by product and partner to show comparaison
            between supplier price
            @return: the product line tree view
        """
        if context is None:
            context = {}
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'purchase_requisition', 'purchase_line_tree', context=context)
        res['context'] = context
        po_lines = self.browse(cr, uid, ids, context=context)[0].po_line_ids
        res['context'] = {
            'search_default_groupby_product': True,
            'search_default_hide_cancelled': True,
            'tender_id': ids[0],
        }
        res['domain'] = [('id', 'in', [line.id for line in po_lines])]
        return res

    def open_rfq(self, cr, uid, ids, context=None):
        """ This opens rfq view to view all quotations associated to the call for bids
            @return: the RFQ tree view
        """
        if context is None:
            context = {}
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'purchase', 'purchase_rfq', context=context)
        res['context'] = context
        po_ids = [po.id for po in self.browse(cr, uid, ids, context=context)[0].purchase_ids]
        res['domain'] = [('id', 'in', po_ids)]
        return res

    def _prepare_purchase_order(self, cr, uid, requisition, supplier, context=None):
        supplier_pricelist = supplier.property_product_pricelist_purchase
        return {
            'origin': requisition.name,
            'date_order': requisition.date_end or fields.datetime.now(),
            'partner_id': supplier.id,
            'pricelist_id': supplier_pricelist.id,
            'currency_id': supplier_pricelist and supplier_pricelist.currency_id.id or requisition.company_id.currency_id.id,
            'location_id': requisition.procurement_id and requisition.procurement_id.location_id.id or requisition.picking_type_id.default_location_dest_id.id,
            'company_id': requisition.company_id.id,
            'fiscal_position': supplier.property_account_position and supplier.property_account_position.id or False,
            'requisition_id': requisition.id,
            'notes': requisition.description,
            'picking_type_id': requisition.picking_type_id.id
        }

    def _prepare_purchase_order_line(self, cr, uid, requisition, requisition_line, purchase_id, supplier, context=None):
        if context is None:
            context = {}
        po_line_obj = self.pool.get('purchase.order.line')
        product_uom = self.pool.get('product.uom')
        product = requisition_line.product_id
        default_uom_po_id = product.uom_po_id.id
        ctx = context.copy()
        ctx['tz'] = requisition.user_id.tz
        date_order = requisition.ordering_date and fields.date.date_to_datetime(self, cr, uid, requisition.ordering_date, context=ctx) or fields.datetime.now()
        qty = product_uom._compute_qty(cr, uid, requisition_line.product_uom_id.id, requisition_line.product_qty, default_uom_po_id)
        supplier_pricelist = supplier.property_product_pricelist_purchase and supplier.property_product_pricelist_purchase.id or False
        vals = po_line_obj.onchange_product_id(
            cr, uid, [], supplier_pricelist, product.id, qty, default_uom_po_id,
            supplier.id, date_order=date_order,
            fiscal_position_id=supplier.property_account_position.id,
            date_planned=requisition_line.schedule_date,
            name=False, price_unit=False, state='draft', context=context)['value']
        vals.update({
            'order_id': purchase_id,
            'product_id': product.id,
            'account_analytic_id': requisition_line.account_analytic_id.id,
            'taxes_id': [(6, 0, vals.get('taxes_id', []))],
        })
        return vals

    def make_purchase_order(self, cr, uid, ids, partner_id, context=None):
        """
        Create New RFQ for Supplier
        """
        context = dict(context or {})
        assert partner_id, 'Supplier should be specified'
        purchase_order = self.pool.get('purchase.order')
        purchase_order_line = self.pool.get('purchase.order.line')
        res_partner = self.pool.get('res.partner')
        supplier = res_partner.browse(cr, uid, partner_id, context=context)
        res = {}
        for requisition in self.browse(cr, uid, ids, context=context):
            if not requisition.multiple_rfq_per_supplier and supplier.id in filter(lambda x: x, [rfq.state != 'cancel' and rfq.partner_id.id or None for rfq in requisition.purchase_ids]):
                raise osv.except_osv(_('Warning!'), _('You have already one %s purchase order for this partner, you must cancel this purchase order to create a new quotation.') % rfq.state)
            context.update({'mail_create_nolog': True})
            purchase_id = purchase_order.create(cr, uid, self._prepare_purchase_order(cr, uid, requisition, supplier, context=context), context=context)
            purchase_order.message_post(cr, uid, [purchase_id], body=_("RFQ created"), context=context)
            res[requisition.id] = purchase_id
            for line in requisition.line_ids:
                purchase_order_line.create(cr, uid, self._prepare_purchase_order_line(cr, uid, requisition, line, purchase_id, supplier, context=context), context=context)
        return res

    def check_valid_quotation(self, cr, uid, quotation, context=None):
        """
        Check if a quotation has all his order lines bid in order to confirm it if its the case
        return True if all order line have been selected during bidding process, else return False

        args : 'quotation' must be a browse record
        """
        for line in quotation.order_line:
            if line.state != 'confirmed' or line.product_qty != line.quantity_bid:
                return False
        return True

    def _prepare_po_from_tender(self, cr, uid, tender, context=None):
        """ Prepare the values to write in the purchase order
        created from a tender.

        :param tender: the source tender from which we generate a purchase order
        """
        return {'order_line': [],
                'requisition_id': tender.id,
                'origin': tender.name}

    def _prepare_po_line_from_tender(self, cr, uid, tender, line, purchase_id, context=None):
        """ Prepare the values to write in the purchase order line
        created from a line of the tender.

        :param tender: the source tender from which we generate a purchase order
        :param line: the source tender's line from which we generate a line
        :param purchase_id: the id of the new purchase
        """
        return {'product_qty': line.quantity_bid,
                'order_id': purchase_id}

    def generate_po(self, cr, uid, ids, context=None):
        """
        Generate all purchase order based on selected lines, should only be called on one tender at a time
        """
        po = self.pool.get('purchase.order')
        poline = self.pool.get('purchase.order.line')
        id_per_supplier = {}
        for tender in self.browse(cr, uid, ids, context=context):
            if tender.state == 'done':
                raise osv.except_osv(_('Warning!'), _('You have already generate the purchase order(s).'))

            confirm = False
            #check that we have at least confirm one line
            for po_line in tender.po_line_ids:
                if po_line.state == 'confirmed':
                    confirm = True
                    break
            if not confirm:
                raise osv.except_osv(_('Warning!'), _('You have no line selected for buying.'))

            #check for complete RFQ
            for quotation in tender.purchase_ids:
                if (self.check_valid_quotation(cr, uid, quotation, context=context)):
                    #use workflow to set PO state to confirm
                    po.signal_workflow(cr, uid, [quotation.id], 'purchase_confirm')

            #get other confirmed lines per supplier
            for po_line in tender.po_line_ids:
                #only take into account confirmed line that does not belong to already confirmed purchase order
                if po_line.state == 'confirmed' and po_line.order_id.state in ['draft', 'sent', 'bid']:
                    if id_per_supplier.get(po_line.partner_id.id):
                        id_per_supplier[po_line.partner_id.id].append(po_line)
                    else:
                        id_per_supplier[po_line.partner_id.id] = [po_line]

            #generate po based on supplier and cancel all previous RFQ
            ctx = dict(context or {}, force_requisition_id=True)
            for supplier, product_line in id_per_supplier.items():
                #copy a quotation for this supplier and change order_line then validate it
                quotation_id = po.search(cr, uid, [('requisition_id', '=', tender.id), ('partner_id', '=', supplier)], limit=1)[0]
                vals = self._prepare_po_from_tender(cr, uid, tender, context=context)
                new_po = po.copy(cr, uid, quotation_id, default=vals, context=context)
                #duplicate po_line and change product_qty if needed and associate them to newly created PO
                for line in product_line:
                    vals = self._prepare_po_line_from_tender(cr, uid, tender, line, new_po, context=context)
                    poline.copy(cr, uid, line.id, default=vals, context=context)
                #use workflow to set new PO state to confirm
                po.signal_workflow(cr, uid, [new_po], 'purchase_confirm')

            #cancel other orders
            self.cancel_unconfirmed_quotations(cr, uid, tender, context=context)

            #set tender to state done
            self.signal_workflow(cr, uid, [tender.id], 'done')
        return True

    def cancel_unconfirmed_quotations(self, cr, uid, tender, context=None):
        #cancel other orders
        po = self.pool.get('purchase.order')
        for quotation in tender.purchase_ids:
            if quotation.state in ['draft', 'sent', 'bid']:
                self.pool.get('purchase.order').signal_workflow(cr, uid, [quotation.id], 'purchase_cancel')
                po.message_post(cr, uid, [quotation.id], body=_('Cancelled by the call for bids associated to this request for quotation.'), context=context)
        return True


class purchase_requisition_line(osv.osv):
    _name = "purchase.requisition.line"
    _description = "Purchase Requisition Line"
    _rec_name = 'product_id'

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', domain=[('purchase_ok', '=', True)]),
        'product_uom_id': fields.many2one('product.uom', 'Product Unit of Measure'),
        'product_qty': fields.float('Quantity', digits_compute=dp.get_precision('Product Unit of Measure')),
        'requisition_id': fields.many2one('purchase.requisition', 'Call for Bids', ondelete='cascade'),
        'company_id': fields.related('requisition_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'account_analytic_id': fields.many2one('account.analytic.account', 'Analytic Account',),
        'schedule_date': fields.date('Scheduled Date'),
    }

    def onchange_product_id(self, cr, uid, ids, product_id, product_uom_id, parent_analytic_account, analytic_account, parent_date, date, context=None):
        """ Changes UoM and name if product_id changes.
        @param name: Name of the field
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        value = {'product_uom_id': ''}
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
            value = {'product_uom_id': prod.uom_id.id, 'product_qty': 1.0}
        if not analytic_account:
            value.update({'account_analytic_id': parent_analytic_account})
        if not date:
            value.update({'schedule_date': parent_date})
        return {'value': value}

    _defaults = {
        'company_id': lambda self, cr, uid, c: self.pool.get('res.company')._company_default_get(cr, uid, 'purchase.requisition.line', context=c),
    }

class purchase_order(osv.osv):
    _inherit = "purchase.order"

    _columns = {
        'requisition_id': fields.many2one('purchase.requisition', 'Call for Bids', copy=False),
    }

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        res = super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context=context)
        proc_obj = self.pool.get('procurement.order')
        for po in self.browse(cr, uid, ids, context=context):
            if po.requisition_id and (po.requisition_id.exclusive == 'exclusive'):
                for order in po.requisition_id.purchase_ids:
                    if order.id != po.id:
                        proc_ids = proc_obj.search(cr, uid, [('purchase_id', '=', order.id)])
                        if proc_ids and po.state == 'confirmed':
                            proc_obj.write(cr, uid, proc_ids, {'purchase_id': po.id})
                        order.signal_workflow('purchase_cancel')
                    po.requisition_id.tender_done(context=context)
        return res

    def _prepare_order_line_move(self, cr, uid, order, order_line, picking_id, group_id, context=None):
        stock_move_lines = super(purchase_order, self)._prepare_order_line_move(cr, uid, order, order_line, picking_id, group_id, context=context)
        if order.requisition_id and order.requisition_id.procurement_id and order.requisition_id.procurement_id.move_dest_id:
            for i in range(0, len(stock_move_lines)):
                stock_move_lines[i]['move_dest_id'] = order.requisition_id.procurement_id.move_dest_id.id
        return stock_move_lines


class purchase_order_line(osv.osv):
    _inherit = 'purchase.order.line'

    _columns = {
        'quantity_bid': fields.float('Quantity Bid', digits_compute=dp.get_precision('Product Unit of Measure'), help="Technical field for not loosing the initial information about the quantity proposed in the bid"),
    }

    def action_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'state': 'draft'}, context=context)

    def action_confirm(self, cr, uid, ids, context=None):
        super(purchase_order_line, self).action_confirm(cr, uid, ids, context=context)
        for element in self.browse(cr, uid, ids, context=context):
            if not element.quantity_bid:
                self.write(cr, uid, ids, {'quantity_bid': element.product_qty}, context=context)
        return True

    def generate_po(self, cr, uid, tender_id, context=None):
        #call generate_po from tender with active_id. Called from js widget
        return self.pool.get('purchase.requisition').generate_po(cr, uid, [tender_id], context=context)


class product_template(osv.osv):
    _inherit = 'product.template'

    _columns = {
        'purchase_requisition': fields.boolean('Call for Bids', help="Check this box to generate Call for Bids instead of generating requests for quotation from procurement.")
    }


class procurement_order(osv.osv):
    _inherit = 'procurement.order'
    _columns = {
        'requisition_id': fields.many2one('purchase.requisition', 'Latest Requisition')
    }

    def _run(self, cr, uid, procurement, context=None):
        requisition_obj = self.pool.get('purchase.requisition')
        warehouse_obj = self.pool.get('stock.warehouse')
        if procurement.rule_id and procurement.rule_id.action == 'buy' and procurement.product_id.purchase_requisition:
            warehouse_id = warehouse_obj.search(cr, uid, [('company_id', '=', procurement.company_id.id)], context=context)
            requisition_id = requisition_obj.create(cr, uid, {
                'origin': procurement.origin,
                'date_end': procurement.date_planned,
                'warehouse_id': warehouse_id and warehouse_id[0] or False,
                'company_id': procurement.company_id.id,
                'procurement_id': procurement.id,
                'picking_type_id': procurement.rule_id.picking_type_id.id,
                'line_ids': [(0, 0, {
                    'product_id': procurement.product_id.id,
                    'product_uom_id': procurement.product_uom.id,
                    'product_qty': procurement.product_qty

                })],
            })
            self.message_post(cr, uid, [procurement.id], body=_("Purchase Requisition created"), context=context)
            return self.write(cr, uid, [procurement.id], {'requisition_id': requisition_id}, context=context)
        return super(procurement_order, self)._run(cr, uid, procurement, context=context)

    def _check(self, cr, uid, procurement, context=None):
        if procurement.rule_id and procurement.rule_id.action == 'buy' and procurement.product_id.purchase_requisition:
            if procurement.requisition_id.state == 'done':
                if any([purchase.shipped for purchase in procurement.requisition_id.purchase_ids]):
                    return True
            return False
        return super(procurement_order, self)._check(cr, uid, procurement, context=context)
