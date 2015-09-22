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
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string='Picking associated to this sale')
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_ids')

    @api.multi
    @api.depends('procurement_group_id')
    def _compute_picking_ids(self):
        for order in self:
            order.picking_ids = self.env['stock.picking'].search([('group_id', '=', order.procurement_group_id.id)]) if order.procurement_group_id else []
            order.delivery_count = len(order.picking_ids)

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
    def action_cancel(self):
        self.order_line.mapped('procurement_ids').cancel()
        super(SaleOrder, self).action_cancel()

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
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
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
            if float_compare(product.virtual_available, self.product_uom_qty, precision_digits=precision) == -1:
                # Check if MTO, Cross-Dock or Drop-Shipping
                is_available = False
                for route in self.route_id+self.product_id.route_ids:
                    for pull in route.pull_ids:
                        if pull.location_id.id == self.order_id.warehouse_id.lot_stock_id.id:
                            is_available = True
                if not is_available:
                    warning_mess = {
                        'title': _('Not enough inventory!'),
                        'message' : _('You plan to sell %.2f %s but you only have %.2f %s available!\nThe stock on hand is %.2f %s.') % \
                            (self.product_uom_qty, self.product_uom.name or self.product_id.uom_id.name, product.virtual_available, self.product_uom.name or self.product_id.uom_id.name, product.qty_available, self.product_uom.name or self.product_id.uom_id.name)
                    }
                    return {'warning': warning_mess}
        return {}

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        if self.state == 'sale' and self.product_id.type != 'service' and self.product_uom_qty < self._origin.product_uom_qty:
            warning_mess = {
                'title': _('Ordered quantity decreased!'),
                'message' : _('You are decreasing the ordered quantity! Do not forget to manually update the delivery order if needed.'),
            }
            return {'warning': warning_mess}
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
        return qty

    @api.multi
    def _check_package(self):
        default_uom = self.product_id.uom_id
        pack = self.product_packaging
        qty = self.product_uom_qty
        q = self.env['product.uom']._compute_qty_obj(default_uom, pack.qty, self.product_uom)
        if qty and q and (qty % q):
            newqty = qty - (qty % q) + q
            return {
                'warning': {
                    'title': _('Warning'),
                    'message': _("This product is packaged by %d . You should sell %d .") % (pack.qty, newqty),
                },
            }
        return {}


class StockLocationRoute(models.Model):
    _inherit = "stock.location.route"

    sale_selectable = fields.Boolean(string="Selectable on Sales Order Line")


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


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    @api.model
    def invoice_line_move_line_get(self):
        res = super(AccountInvoice,self).invoice_line_move_line_get()
        if self.company_id.anglo_saxon_accounting:
            if self.type in ('out_invoice','out_refund'):
                for i_line in self.invoice_line_ids:
                    res.extend(self._anglo_saxon_sale_move_lines(i_line))
        return res

    @api.model
    def _anglo_saxon_sale_move_lines(self, i_line):
        """Return the additional move lines for sales invoices and refunds.

        i_line: An account.invoice.line object.
        """
        inv = i_line.invoice_id
        company_currency = inv.company_id.currency_id.id
        uom_obj = self.env['product.uom']
        if i_line.product_id.type in ('product', 'consu') and i_line.product_id.valuation == 'real_time':
            # debit account dacc will be the output account
            # first check the product, if empty check the category
            dacc = i_line.product_id.property_stock_account_output and i_line.product_id.property_stock_account_output.id
            if not dacc:
                dacc = i_line.product_id.categ_id.property_stock_account_output_categ_id and i_line.product_id.categ_id.property_stock_account_output_categ_id.id
            # in both cases the credit account cacc will be the expense account
            # first check the product, if empty check the category
            cacc = i_line.product_id.property_account_expense_id and i_line.product_id.property_account_expense_id.id
            if not cacc:
                cacc = i_line.product_id.categ_id.property_account_expense_categ_id and i_line.product_id.categ_id.property_account_expense_categ_id.id
            if dacc and cacc:
                # Search for moves and check for just a part being paid
                if i_line.product_id.invoice_policy == 'delivery':
                    # Search moves that have not been invoiced yet: search according to default order
                    for s_line in i_line.sale_line_ids:
                        #Check qtys already invoiced
                        qty_done = sum([uom_obj._compute_qty_obj(x.product_uom, x.product_uom_qty, x.product_id.uom_id) for x in s_line.invoice_lines if x.invoice_id.state in ('open', 'paid')])
                        qty_from_moves = 0.0
                        average = 0.0
                        qty_done_rest = qty_done
                        i_qty = uom_obj._compute_qty_obj(i_line.uom_id, i_line.quantity, i_line.product_id.uom_id)
                        i_qty_rest = i_qty
                        # Put moves in fixed order by date executed
                        moves = self.env['stock.move'].browse()
                        for procurement in s_line.procurement_ids:
                            moves |= procurement.move_ids
                        sorted(moves, lambda x: x.date)
                        # Go through all the moves and do nothing until you get to qty_done
                        # Beyond qty_done we need to calculate the average of the price_unit
                        # on the moves we encounter.
                        for move in moves:
                            if move.state != 'done':
                                continue
                            if i_qty_rest <= 0.0:
                                break
                            qty_to_take = 0
                            if qty_done_rest > 0.0 and qty_done_rest >= move.product_qty:
                                qty_done_rest -= move.product_qty
                            else:
                                qty_to_take = move.product_qty - qty_done_rest
                                qty_done_rest = 0
                                # Check qty
                                if i_qty_rest > qty_to_take:
                                    i_qty_rest -= qty_to_take
                                else:
                                    qty_to_take = i_qty_rest
                                    i_qty_rest = 0
                                # Take average
                                if qty_from_moves == 0:
                                    average = move.price_unit
                                    qty_from_moves = qty_to_take
                                else:
                                    average = (average * qty_from_moves + move.price_unit * qty_to_take) / (qty_from_moves + qty_to_take)
                                    qty_from_moves += qty_to_take
                        if qty_from_moves:
                            price_unit = average
                        else:
                            price_unit = i_line.product_id.standard_price
                else:
                    price_unit = i_line.product_id.standard_price

                return [
                    {
                        'type':'src',
                        'name': i_line.name[:64],
                        'price_unit':price_unit,
                        'quantity':i_line.quantity,
                        'price': i_line._get_price(inv, company_currency, i_line, price_unit),
                        'account_id':dacc,
                        'product_id':i_line.product_id.id,
                        'uom_id':i_line.uom_id.id,
                        'account_analytic_id': False,
                        'taxes':i_line.invoice_line_tax_ids,
                    },

                    {
                        'type':'src',
                        'name': i_line.name[:64],
                        'price_unit':price_unit,
                        'quantity':i_line.quantity,
                        'price': -1 * i_line._get_price(inv, company_currency, i_line, price_unit),
                        'account_id':cacc,
                        'product_id':i_line.product_id.id,
                        'uom_id':i_line.uom_id.id,
                        'account_analytic_id': False,
                        'taxes':i_line.invoice_line_tax_ids,
                    },
                ]
        return []
