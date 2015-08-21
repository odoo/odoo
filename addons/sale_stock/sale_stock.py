# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from openerp import api, fields, models, _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _default_warehouse_id(self):
        company = self.env.user.company_id.id
        warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
        return warehouse_ids

    incoterm = fields.Many2one('stock.incoterms', 'Incoterms', help="International Commercial Terms are a series of predefined commercial terms used in international transactions.")
    picking_policy = fields.Selection([
        ('direct', 'Deliver each product when available'),
        ('one', 'Deliver all products at once')],
        string='Shipping Policy', required=True, readonly=True, default='direct',
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
        required=True, readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        default=_default_warehouse_id)
    picking_ids = fields.One2many('stock.picking', compute='_compute_picking_ids', string='Picking associated to this sale')
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_ids')

    @api.multi
    @api.depends('procurement_group_id')
    def _compute_picking_ids(self):
        for order in self:
            if not order.procurement_group_id:
                order.picking_ids = []
                order.delivery_count = 0
            else:
                order.picking_ids = self.env['stock.picking'].search([('group_id', '=', order.procurement_group_id.id)]).ids
                order.delivery_count = len(order.picking_ids.ids)

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        if self.warehouse_id.company_id:
            self.company_id = self.warehouse_id.company_id.id

    @api.multi
    def action_view_delivery(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env.ref('stock.action_picking_tree_all')

        result = {
            'name': action.name,
            'help': action.help,
            'type': action.type,
            'view_type': action.view_type,
            'view_mode': action.view_mode,
            'target': action.target,
            'context': action.context,
            'res_model': action.res_model,
        }

        pick_ids = sum([order.picking_ids.ids for order in self], [])

        if len(pick_ids) > 1:
            result['domain'] = "[('id','in',["+','.join(map(str, pick_ids))+"])]"
        elif len(pick_ids) == 1:
            form = self.env.ref('stock.view_picking_form', False)
            form_id = form.id if form else False
            result['views'] = [(form_id, 'form')]
            result['res_id'] = pick_ids[0]
        return result

    @api.multi
    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals['incoterms_id'] = self.incoterm.id or False
        return invoice_vals

    @api.model
    def _prepare_procurement_group(self):
        res = super(SaleOrder, self)._prepare_procurement_group()
        res.update({'move_type': self.picking_policy, 'partner_id': self.partner_shipping_id.id})
        return res


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_packaging = fields.Many2one('product.packaging', string='Packaging', default=False)
    route_id = fields.Many2one('stock.location.route', string='Route', domain=[('sale_selectable', '=', True)])
    product_tmpl_id = fields.Many2one('product.template', related='product_id.product_tmpl_id', string='Product Template')
    procurement_ids = fields.One2many('procurement.order', 'so_line_id', string='Procurements')

    @api.multi
    @api.depends('product_id')
    def _compute_qty_delivered_updateable(self):
        for line in self:
            if line.product_id.type not in ('consu', 'product'):
                return super(SaleOrderLine, self)._compute_qty_delivered_updateable()
            line.qty_delivered_updateable = False

    @api.onchange('product_id')
    def _onchange_product_id_set_customer_lead(self):
        self.customer_lead = self.product_id.sale_delay
        return {}

    @api.onchange('product_packaging')
    def _onchange_product_packaging(self):
        if self.product_packaging:
            return self._check_package()
        return {}

    @api.onchange('product_id', 'product_uom_qty')
    def _onchange_product_id_check_availability(self):
        if not self.product_id:
            self.product_packaging = False
            return {}
        self.product_tmpl_id = self.product_id.product_tmpl_id
        if self.product_id.type == 'product':
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner_id=self.order_id.partner_id.id,
                date_order=self.order_id.date_order,
                pricelist_id=self.order_id.pricelist_id.id,
                uom=self.product_uom.id,
                warehouse_id=self.order_id.warehouse_id.id
            )
            if float_compare(product.virtual_available, self.product_uom_qty, precision_rounding=self.product_uom.rounding) == -1:
                # Check if MTO, Cross-Dock or Drop-Shipping
                is_available = False
                for route in self.route_id+self.product_id.route_ids:
                    for pull in route.pull_ids:
                        if pull.location_id.id == self.order_id.warehouse_id.lot_stock_id.id:
                            is_available = True
                if not is_available:
                    return {
                        'title': _('Not enough inventory!'),
                        'message' : _('You plan to sell %.2f %s but you only have %.2f %s available!\nThe stock on hand is %.2f %s.') % \
                            (self.product_uom_qty, self.product_uom.name, product.virtual_available, self.product_uom.name, product.qty_available, self.product_uom.name)
                    }
        return {}

    @api.multi
    def _prepare_order_line_procurement(self, group_id=False):
        vals = super(SaleOrderLine, self)._prepare_order_line_procurement(group_id=group_id)
        date_planned = datetime.strptime(self.order_id.date_order, DEFAULT_SERVER_DATETIME_FORMAT)\
            + timedelta(days=self.customer_lead or 0.0) - timedelta(days=self.order_id.company_id.security_lead)
        vals.update({
            'date_planned': date_planned.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            'location_id': self.order_id.partner_shipping_id.property_stock_customer.id,
            'route_ids': self.route_id and [(4, self.route_id.id)] or [],
            'warehouse_id': self.order_id.warehouse_id and self.order_id.warehouse_id.id or False,
            'partner_dest_id': self.order_id.partner_shipping_id.id,
            'so_line_id': self.id,
        })
        return vals

    @api.multi
    def _get_delivered_qty(self):
        self.ensure_one()
        super(SaleOrderLine, self)._get_delivered_qty()
        qty = 0.0
        for move in self.procurement_ids.mapped('move_ids').filtered(lambda r: r.state == 'done' and not r.scrapped):
            if move.location_dest_id.usage == "customer":
                qty += self.env['product.uom']._compute_qty_obj(move.product_uom, move.product_uom_qty, self.product_uom)
            elif move.location_id.usage == "customer":
                qty -= self.env['product.uom']._compute_qty_obj(move.product_uom, move.product_uom_qty, self.product_uom)
        return qty

    @api.multi
    def _check_package(self):
        default_uom = self.product_id.product_uom
        pack = self.product_packaging
        qty = self.product_uom_qty
        q = self.product_id.product_uom._compute_qty(pack.qty, default_uom)
        if qty and q and (qty % q):
            newqty = qty - (qty % q) + q
            return {
               'title': _('Warning!'),
               'message': _("This product is packaged by %d %s. You should sell %d %s.") % (pack.qty, default_uom, newqty, default_uom)
            }
        return {}


class StockLocationRoute(models.Model):
    _inherit = "stock.location.route"


class stock_picking(osv.osv):
    _inherit = "stock.picking"

    def action_view_sale_order(self, cr, uid, ids, context=None):
        sale_ids = []
        picking = self.browse(cr, uid, ids)[0]
        result = self.pool['ir.actions.act_window'].for_xml_id(cr, uid, 'sale', 'action_orders', context=context)
        if picking.move_lines:
            for move in picking.move_lines:
                if move.procurement_id and move.procurement_id.sale_line_id:
                    sale_ids.append(move.procurement_id.sale_line_id.order_id.id)

        view_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, 'sale.view_order_form')
        result['views'] = [(view_id, 'form')]
        result['res_id'] = sale_ids[0] or False
        return result


    def action_view_invoice(self, cr, uid, ids, context=None):
        '''
        This function returns an action that display existing invoices of given Transfer ids. It can either be a in a list or in a form view, if there is only one invoice to show.
        '''
        ModelData = self.pool['ir.model.data']
        InvoiceLine = self.pool['account.invoice.line']
        result = self.pool['ir.actions.act_window'].for_xml_id(cr, uid, 'account', 'action_invoice_tree1', context=context)
        inv_ids = []
        cr.execute('select ai.id as invoice_id from stock_picking sp '\
                        'left join stock_move sm on (sm.picking_id=sp.id) '\
                        'left join account_invoice_line ail on (ail.move_id=sm.id) '\
                        'left join account_invoice ai on (ail.invoice_id = ai.id) '\
                        'where sp.id in %s and ail.move_id is not null '
                        'group by sp.id,ai.id', (tuple(ids),))
        inv_ids =  cr.fetchone()
        view_id = ModelData.xmlid_to_res_id(cr, uid, 'account.invoice_form')
        result['views'] = [(view_id or False, 'form')]
        result['res_id'] = inv_ids and inv_ids[0] or False
        return result

    def _get_partner_to_invoice(self, cr, uid, picking, context=None):
        """ Inherit the original function of the 'stock' module
            We select the partner of the sales order as the partner of the customer invoice
        """
        if picking.sale_id:
            saleorder_ids = self.pool['sale.order'].search(cr, uid, [('procurement_group_id' ,'=', picking.group_id.id)], context=context)
            saleorders = self.pool['sale.order'].browse(cr, uid, saleorder_ids, context=context)
            if saleorders and saleorders[0] and saleorders[0].order_policy == 'picking':
                saleorder = saleorders[0]
                return saleorder.partner_invoice_id.id
        return super(stock_picking, self)._get_partner_to_invoice(cr, uid, picking, context=context)
    
    def _get_sale_id(self, cr, uid, ids, name, args, context=None):
        sale_obj = self.pool.get("sale.order")
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = False
            if picking.group_id:
                sale_ids = sale_obj.search(cr, uid, [('procurement_group_id', '=', picking.group_id.id)], context=context)
                if sale_ids:
                    res[picking.id] = sale_ids[0]
        return res
    
    _columns = {
        'sale_id': fields.function(_get_sale_id, type="many2one", relation="sale.order", string="Sale Order"),
    }

    def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, moves, context=None):
        inv_vals = super(stock_picking, self)._get_invoice_vals(cr, uid, key, inv_type, journal_id, moves, context=context)
        if inv_type in ('out_invoice', 'out_refund'):
            sales = [x.picking_id.sale_id or x.origin_returned_move_id.picking_id.sale_id for x in moves if x.picking_id.sale_id or x.origin_returned_move_id.picking_id.sale_id]
            if sales:
                sale = sales[0]
                inv_vals.update({
                    'fiscal_position_id': sale.fiscal_position_id.id,
                    'payment_term_id': sale.payment_term_id.id,
                    'user_id': sale.user_id.id,
                    'team_id': sale.team_id.id,
                    'name': sale.client_order_ref or '',
                    'sale_ids': [(6, 0, list(set([x.id for x in sales])))],
                    })
        return inv_vals

    def get_service_line_vals(self, cr, uid, moves, partner, inv_type, context=None):
        res = super(stock_picking, self).get_service_line_vals(cr, uid, moves, partner, inv_type, context=context)
        if inv_type == 'out_invoice':
            sale_line_obj = self.pool.get('sale.order.line')
            orders = list(set([x.procurement_id.sale_line_id.order_id.id for x in moves if x.procurement_id.sale_line_id]))
            sale_line_ids = sale_line_obj.search(cr, uid, [('order_id', 'in', orders), ('invoiced', '=', False), '|', ('product_id', '=', False),
                                                           ('product_id.type', '=', 'service')], context=context)
            if sale_line_ids:
                created_lines = sale_line_obj.invoice_line_create(cr, uid, sale_line_ids, context=context)
                res += [(4, x) for x in created_lines]
        return res


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    incoterms_id = fields.Many2one('stock.incoterms', string="Incoterms",
        help="Incoterms are series of sales terms. They are used to divide transaction costs and responsibilities between buyer and seller and reflect state-of-the-art transportation practices.",
        readonly=True, states={'draft': [('readonly', False)]})


class ProcurementOrder(models.Model):
    _inherit = "procurement.order"

    so_line_id = fields.Many2one('sale.order.line', string='Sale Order Line')

    @api.model
    def _run_move_create(self, procurement):
        vals = super(ProcurementOrder, self)._run_move_create(procurement)
        if self.sale_line_id:
            vals.update({'sequence': self.sale_line_id.sequence})
        return vals


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.multi
    def action_done(self):
        result = super(StockMove, self).action_done()

        # Update delivered quantities on sale order lines
        todo = self.env['sale.order.line']
        for move in self:
            if (move.procurement_id.so_line_id) and (move.product_id.invoice_policy in ('order', 'delivery')):
                todo |= move.procurement_id.so_line_id
        for line in todo:
            line.qty_delivered = line._get_delivered_qty()
        return result
