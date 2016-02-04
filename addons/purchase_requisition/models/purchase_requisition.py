# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class PurchaseRequisition(models.Model):
    _name = "purchase.requisition"
    _description = "Purchase Requisition"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    def _default_get_picking_in(self):
        return self.env.ref('stock.picking_type_in')

    name = fields.Char(string='Call for Tenders Reference', required=True, copy=False, default=lambda obj: obj.env['ir.sequence'].next_by_code('purchase.order.requisition'))
    origin = fields.Char(string='Source Document')
    ordering_date = fields.Date(string='Scheduled Ordering Date')
    date_end = fields.Datetime(string='Tender Closing Deadline')
    schedule_date = fields.Date(string='Scheduled Date', index=True, help="The expected and scheduled delivery date where all the products are received")
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    exclusive = fields.Selection([('exclusive', 'Select only one RFQ (exclusive)'), ('multiple', 'Select multiple RFQ')], string='Tender Selection Type', required=True, help="Select only one RFQ (exclusive):  On the confirmation of a purchase order, it cancels the remaining purchase order.\nSelect multiple RFQ:  It allows to have multiple purchase orders.On confirmation of a purchase order it does not cancel the remaining orders""", default='multiple')
    description = fields.Text(string='Description')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    purchase_ids = fields.One2many('purchase.order', 'requisition_id', string='Purchase Orders', states={'done': [('readonly', True)]})
    po_line_ids = fields.One2many('purchase.order.line', compute='_compute_get_po_line', string='Products by vendor')
    line_ids = fields.One2many('purchase.requisition.line', 'requisition_id', string='Products to Purchase', states={'done': [('readonly', True)]}, copy=True)
    procurement_id = fields.Many2one('procurement.order', string='Procurement', ondelete='set null', copy=False)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    state = fields.Selection([('draft', 'Draft'), ('in_progress', 'Confirmed'),
                            ('open', 'Bid Selection'), ('done', 'PO Created'),
                            ('cancel', 'Cancelled')], string='Status', track_visibility='onchange', required=True, copy=False, default='draft')
    multiple_rfq_per_supplier = fields.Boolean(string='Multiple RFQ per vendor')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type', required=True, default=_default_get_picking_in)

    @api.depends('purchase_ids')
    def _compute_get_po_line(self):
        for element in self:
            result = []
            for po in element.purchase_ids:
                result += po.order_line.ids
            element.po_line_ids = result

    @api.multi
    def tender_cancel(self):
        # try to set all associated quotations to cancel state
        for tender in self:
            for purchase_order in tender.purchase_ids:
                purchase_order.button_cancel()
                purchase_order.message_post(body=_('Cancelled by the tender associated to this quotation.'))
        self.write({'state': 'cancel'})

    @api.multi
    def tender_in_progress(self):
        if not all(obj.line_ids for obj in self):
            raise UserError(_('You can not confirm call because there is no product line.'))
        self.write({'state': 'in_progress'})

    @api.multi
    def tender_open(self):
        self.write({'state': 'open'})

    @api.multi
    def tender_reset(self):
        self.write({'state': 'draft'})
        # Deleting the existing instance of workflow for PO
        self.delete_workflow()
        self.create_workflow()

    @api.multi
    def tender_done(self):
        self.write({'state': 'done'})

    @api.multi
    def open_product_line(self):
        """ This opens product line view to view all lines from the different quotations, groupby default by product and partner to show comparaison
            between vendor price
            @return: the product line tree view
        """
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('purchase_requisition', 'purchase_line_tree')
        res['context'] = literal_eval(res['context'])
        res['context'].update({
            'search_default_groupby_product': True,
            'search_default_hide_cancelled': True,
            'tender_id': self.id,
        })
        res['domain'] = [('id', 'in', self.po_line_ids.ids)]
        return res

    @api.multi
    def open_rfq(self):
        """ This opens rfq view to view all quotations associated to the call for tenders
            @return: the RFQ tree view
        """
        self.ensure_one()
        res = self.env['ir.actions.act_window'].for_xml_id('purchase', 'purchase_rfq')
        res['context'] = self.env.context
        res['domain'] = [('id', 'in', self.purchase_ids.ids)]
        return res

    def _prepare_purchase_order(self, supplier):
        self.ensure_one()
        return {
            'origin': self.name,
            'date_order': self.date_end or fields.Datetime.now(),
            'partner_id': supplier.id,
            'currency_id': self.company_id.currency_id.id,
            'company_id': self.company_id.id,
            'fiscal_position_id': self.env['account.fiscal.position'].get_fiscal_position(supplier.id),
            'requisition_id': self.id,
            'notes': self.description,
            'picking_type_id': self.picking_type_id.id,
        }

    def _prepare_purchase_order_line(self, requisition_line, purchase, supplier):
        product = requisition_line.product_id
        default_uom_po_id = product.uom_po_id.id
        date_order = self.ordering_date or fields.Datetime.now()
        qty = self.env['product.uom']._compute_qty(requisition_line.product_uom_id.id, requisition_line.product_qty, default_uom_po_id)
        fpos = supplier.property_account_position_id
        taxes_id = fpos.map_tax(product.supplier_taxes_id).ids

        seller = requisition_line.product_id._select_seller(
            requisition_line.product_id,
            partner_id=supplier,
            quantity=qty,
            date=date_order and date_order[:10],
            uom_id=product.uom_po_id)

        price_unit = seller.price if seller else 0.0
        if price_unit and seller and purchase.currency_id and seller.currency_id != purchase.currency_id:
            price_unit = seller.currency_id.compute(price_unit, purchase.currency_id)

        date_planned = fields.Datetime.to_string(self.env['purchase.order.line']._get_date_planned(seller, po=purchase))
        product_lang = requisition_line.product_id.with_context({
            'lang': supplier.lang,
            'partner_id': supplier.id,
        })
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        vals = {
            'name': name,
            'order_id': purchase.id,
            'product_qty': qty,
            'product_id': product.id,
            'product_uom': default_uom_po_id,
            'price_unit': price_unit,
            'date_planned': date_planned,
            'taxes_id': [(6, 0, taxes_id)],
            'account_analytic_id': requisition_line.account_analytic_id.id,
        }

        return vals

    @api.multi
    def make_purchase_order(self, partner_id):
        """
        Create New RFQ for Vendor
        """
        assert partner_id, 'Vendor should be specified'
        PurchaseOrder = self.env['purchase.order']
        PurchaseOrderLine = self.env['purchase.order.line']
        supplier = self.env['res.partner'].browse(partner_id)
        res = {}
        for requisition in self:
            if not requisition.multiple_rfq_per_supplier and supplier.id in [rfq.partner_id.id for rfq in requisition.purchase_ids.filtered(lambda x: x.state != 'cancel')]:
                raise UserError(_('You have already one %s purchase order for this partner, you must cancel this purchase order to create a new quotation.') % rfq.state)
            ctx = dict(self.env.context, mail_create_nolog=True)
            purchase = PurchaseOrder.with_context(ctx).create(requisition._prepare_purchase_order(supplier))
            purchase.message_post(body=_("RFQ created"))
            res[requisition.id] = purchase.id
            for line in requisition.line_ids:
                PurchaseOrderLine.create(requisition._prepare_purchase_order_line(line, purchase, supplier))
        return res

    def check_valid_quotation(self, quotation):
        """
        Check if a quotation has all his order lines bid in order to confirm it if its the case
        return True if all order line have been selected during tendering process, else return False

        args : 'quotation' must be a browse record
        """
        for line in quotation.order_line:
            if line.product_qty != line.quantity_tendered:
                return False
        return True

    def _prepare_po_from_tender(self):
        """ Prepare the values to write in the purchase order
        created from a tender.
        """
        self.ensure_one()
        return {'order_line': [],
                'requisition_id': self.id,
                'origin': self.name}

    def _prepare_po_line_from_tender(self, line, purchase):
        """ Prepare the values to write in the purchase order line
        created from a line of the tender.
        :param line: the source tender's line from which we generate a line
        :param purchase: the record of the new purchase
        """
        return {'product_qty': line.quantity_tendered,
                'order_id': purchase.id}

    @api.multi
    def generate_po(self):
        """
        Generate all purchase order based on selected lines, should only be called on one tender at a time
        """
        id_per_supplier = {}
        PurchaseOrder = self.env['purchase.order']
        for tender in self:
            if tender.state == 'done':
                raise UserError(_('You have already generate the purchase order(s).'))

            confirm = False
            #check that we have at least confirm one line
            for po_line in tender.po_line_ids:
                if po_line.quantity_tendered > 0:
                    confirm = True
                    break
            if not confirm:
                raise UserError(_('You have no line selected for buying.'))

            #check for complete RFQ
            for quotation in tender.purchase_ids:
                if (self.check_valid_quotation(quotation)):
                    #Set PO state to confirm
                    quotation.button_confirm()

            #get other confirmed lines per supplier
            for po_line in tender.po_line_ids:
                #only take into account confirmed line that does not belong to already confirmed purchase order
                if po_line.quantity_tendered > 0 and po_line.order_id.state in ['draft', 'sent', 'to approve']:
                    if id_per_supplier.get(po_line.partner_id.id):
                        id_per_supplier[po_line.partner_id.id].append(po_line)
                    else:
                        id_per_supplier[po_line.partner_id.id] = [po_line]

            #generate po based on supplier and cancel all previous RFQ
            for supplier, product_line in id_per_supplier.items():
                #copy a quotation for this supplier and change order_line then validate it
                quotation = PurchaseOrder.search([('requisition_id', '=', tender.id), ('partner_id', '=', supplier)], limit=1)
                vals = tender._prepare_po_from_tender()
                new_po = quotation.copy(default=vals)
                #duplicate po_line and change product_qty if needed and associate them to newly created PO
                for line in product_line:
                    vals = tender._prepare_po_line_from_tender(line, new_po)
                    line.copy(default=vals)
                #use workflow to set new PO state to confirm
                new_po.button_confirm()
            #cancel other orders
            tender.cancel_unconfirmed_quotations()

            #set tender to state done
            tender.signal_workflow('done')
        return True

    def cancel_unconfirmed_quotations(self):
        #cancel other orders
        for quotation in self.purchase_ids:
            if quotation.state in ['draft', 'sent', 'to approve']:
                quotation.button_cancel()
                quotation.message_post(body=_('Cancelled by the call for tenders associated to this request for quotation.'))
        return True


class PurchaseRequisitionLine(models.Model):
    _name = "purchase.requisition.line"
    _description = "Purchase Requisition Line"
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)])
    product_uom_id = fields.Many2one('product.uom', string='Product Unit of Measure')
    product_qty = fields.Float(string='Quantity', digits_compute=dp.get_precision('Product Unit of Measure'))
    requisition_id = fields.Many2one('purchase.requisition', string='Call for Tenders', ondelete='cascade')
    company_id = fields.Many2one('res.company', related='requisition_id.company_id', string='Company', store=True, readonly=True, default=lambda self: self.env['res.users']._get_company())
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account',)
    schedule_date = fields.Date(string='Scheduled Date')

    @api.onchange('product_id')
    def onchange_product_id(self):
        """ Changes UoM and name if product_id changes.
        """
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
            self.product_qty = 1.0
        if not self.account_analytic_id:
            self.account_analytic_id = self.requisition_id.account_analytic_id
        if not self.schedule_date:
            self.schedule_date = self.requisition_id.schedule_date
