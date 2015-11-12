# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError


class MrpRepair(models.Model):
    _name = 'mrp.repair'
    _inherit = 'mail.thread'
    _description = 'Repair Order'

    @api.depends('operations_ids.price_unit', 'operations_ids.tax_id', 'fees_lines_ids.price_unit', 'fees_lines_ids.tax_id')
    def _compute_all(self):
        """ Calculates untaxed , taxed and total amount.
        """
        for repair in self:
            untaxed_amt = 0.0
            val = 0.0
            cur = repair.pricelist_id.currency_id
            for line in repair.operations_ids:
                untaxed_amt += line.price_subtotal
                # manage prices with tax included use compute_all instead of compute
                if line.to_invoice and line.tax_id:
                    tax_calculate = line.tax_id.compute_all(line.price_unit, cur, line.product_uom_qty, line.product_id, repair.partner_id)
                    for cal_tax in tax_calculate['taxes']:
                        val += cal_tax['amount']
            for line in repair.fees_lines_ids:
                untaxed_amt += line.price_subtotal
                if line.to_invoice and line.tax_id:
                    tax_calculate = line.tax_id.compute_all(line.price_unit, cur, line.product_uom_qty, line.product_id, repair.partner_id)
                    for cal_tax in tax_calculate['taxes']:
                        val += cal_tax['amount']
            repair.amount_untaxed = cur.round(untaxed_amt)
            repair.amount_tax = cur.round(val)
            repair.amount_total = repair.amount_untaxed + repair.amount_tax

    @api.multi
    def _get_default_address(self):
        ResPartner = self.env['res.partner']
        for data in self:
            adr_id = False
            if data.partner_id:
                adr_id = ResPartner.address_get([data.partner_id.id], ['default'])['default']
            data.default_address_id = adr_id

    name = fields.Char(string='Repair Reference', required=True, states={'confirmed': [('readonly', True)]}, default=lambda self: self.env['ir.sequence'].next_by_code('mrp.repair'), copy=False)
    product_id = fields.Many2one('product.product', string='Product to Repair', required=True, readonly=True, states={'draft': [('readonly', False)]})
    product_qty = fields.Float(string='Product Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True, readonly=True, default=1.0, states={'draft': [('readonly', False)]})
    product_uom_id = fields.Many2one('product.uom', string='Product Unit of Measure', required=True, readonly=True, states={'draft': [('readonly', False)]}, oldname="product_uom")
    partner_id = fields.Many2one('res.partner', string='Partner', index=True, help='Choose partner for whom the order will be invoiced and delivered.', states={'confirmed': [('readonly', True)]})
    address_id = fields.Many2one('res.partner', string='Delivery Address', states={'confirmed': [('readonly', True)]})
    default_address_id = fields.Many2one('res.partner', compute="_get_default_address")
    state = fields.Selection([('draft', 'Quotation'), ('cancel', 'Cancelled'), ('confirmed', 'Confirmed'), ('under_repair', 'Under Repair'), ('ready', 'Ready to Repair'), ('2binvoiced', 'To be Invoiced'), ('invoice_except', 'Invoice Exception'), ('done', 'Repaired')], 'Status', readonly=True, track_visibility='onchange', copy=False, default=lambda *a: 'draft', help=' * The \'Draft\' status is used when a user is encoding a new and unconfirmed repair order. \
                            \n* The \'Confirmed\' status is used when a user confirms the repair order. \
                            \n* The \'Ready to Repair\' status is used to start to repairing, user can start repairing only after repair order is confirmed. \
                            \n* The \'To be Invoiced\' status is used to generate the invoice before or after repairing done. \
                            \n* The \'Done\' status is set when repairing is completed.\
                            \n* The \'Cancelled\' status is used when user cancel repair order.')
    location_id = fields.Many2one('stock.location', string='Current Location', index=True, required=True, readonly=True, default=lambda self: self.env.ref('stock.warehouse0').lot_stock_id.id or False, states={'draft': [('readonly', False)], 'confirmed': [('readonly', True)]})
    location_dest_id = fields.Many2one('stock.location', string='Delivery Location', readonly=True, required=True, states={'draft': [('readonly', False)], 'confirmed': [('readonly', True)]})
    lot_id = fields.Many2one('stock.production.lot', string='Repaired Lot', domain="[('product_id','=', product_id)]", help="Products repaired are all belonging to this lot", oldname="prodlot_id")
    guarantee_limit = fields.Date(string='Warranty Expiration', states={'confirmed': [('readonly', True)]})
    operations_ids = fields.One2many('mrp.repair.line', 'repair_id', string='Operation Lines', readonly=True, states={'draft': [('readonly', False)]}, copy=True, oldname="operations")
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', default=lambda self: self.env['product.pricelist'].search([], limit=1), help='Pricelist of the selected partner.')
    partner_invoice_id = fields.Many2one('res.partner', string='Invoicing Address')
    invoice_method = fields.Selection([("none", "No Invoice"), ("b4repair", "Before Repair"), ("after_repair", "After Repair")], string="Invoice Method", index=True, required=True, default=lambda *a: 'none', states={'draft': [('readonly', False)]}, readonly=True, help='Selecting \'Before Repair\' or \'After Repair\' will allow you to generate invoice before or after the repair is done respectively. \'No invoice\' means you don\'t want to generate invoice for this repair order.')
    invoice_id = fields.Many2one('account.invoice', string='Invoice', readonly=True, track_visibility="onchange", copy=False)
    move_id = fields.Many2one('stock.move', string='Move', readonly=True, help="Move created by the repair order", track_visibility="onchange", copy=False)
    fees_lines_ids = fields.One2many('mrp.repair.fee', 'repair_id', string='Fees', readonly=True, states={'draft': [('readonly', False)]}, copy=True, oldname="fees_lines")
    internal_notes = fields.Text(string='Internal Notes')
    quotation_notes = fields.Text(string='Quotation Notes')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get('mrp.repair'))
    invoiced = fields.Boolean(string='Invoiced', readonly=True, copy=False)
    repaired = fields.Boolean(string='Repaired', readonly=True, copy=False)
    amount_untaxed = fields.Float(string='Untaxed Amount', compute='_compute_all', store=True)
    amount_tax = fields.Float(string='Taxes', compute='_compute_all', store=True)
    amount_total = fields.Float(string='Total', compute='_compute_all', store=True)

    _sql_constraints = [('name', 'unique (name)', 'The name of the Repair Order must be unique!'), ]

    @api.onchange('product_id')
    def onchange_product_id(self):
        """ On change of product sets some values.
        """
        if self.product_id:
            self.guarantee_limit = False
            self.lot_id = False
            self.product_uom_id = self.product_id.uom_id.id

    @api.onchange('product_uom_id')
    def onchange_product_uom_id(self):
        res = []
        if not self.product_uom_id or not self.product_id:
            return res
        if self.product_uom_id.category_id.id != self.product_id.uom_id.category_id.id:
            self.product_uom_id = self.product_id.uom_id.category_id.id
            res['warning'] = {'title': _('Warning'), 'message': _('The Product Unit of Measure you chose has a different category than in the product form.')}
            return res

    @api.onchange('location_id')
    def onchange_location_id(self):
        """ On change of location
        """
        self.location_dest_id = self.location_id.id

    @api.multi
    def button_dummy(self):
        return True

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """ On change of partner sets the values of partner address,
        partner invoice address and pricelist.
        """
        if not self.partner_id:
            self.address_id = False
            self.partner_invoice_id = False
            self.pricelist_id = self.env['product.pricelist'].search([], limit=1).id

        addr = self.partner_id.address_get(['delivery', 'invoice', 'default'])
        pricelist = self.partner_id.property_product_pricelist.id

        self.address_id = addr['delivery'] or addr['default']
        self.partner_invoice_id = addr['invoice']
        self.pricelist_id = pricelist

    @api.multi
    def action_cancel_draft(self):
        """ Cancels repair order when it is in 'Draft' state.
        @return: True
        """
        if not self:
            return False
        for repair in self:
            repair.operations_ids.write({'state': 'draft'})
        self.state = 'draft'
        return self.create_workflow()

    @api.multi
    def action_confirm(self):
        """ Repair order state is set to 'To be invoiced' when invoice method
        is 'Before repair' else state becomes 'Confirmed'.
        @return: True
        """
        for order in self:
            if (order.invoice_method == 'b4repair'):
                order.state = '2binvoiced'
            else:
                order.state = 'confirmed'
                for line in order.operations_ids:
                    if line.product_id.tracking != 'none' and not line.lot_id:
                        raise UserError(_("Serial number is required for operation line with product '%s'") % (line.product_id.name))
                order.operations_ids.write({'state': 'confirmed'})
        return True

    @api.multi
    def action_cancel(self):
        """ Cancels repair order.
        @return: True
        """
        for repair in self:
            if not repair.invoiced:
                repair.operations_ids.write({'state': 'cancel'})
            else:
                raise UserError(_('Repair order is already invoiced.'))
        self.state = 'cancel'

    def wkf_invoice_create(self):
        self.action_invoice_create()
        return True

    @api.multi
    def action_invoice_create(self, group=False):
        """ Creates invoice(s) for repair order.
        @param group: It is set to true when group invoice is to be generated.
        @return: Invoice Ids.
        """
        res = {}
        invoices_group = {}
        AccountInvoiceLine = self.env['account.invoice.line']
        AccountInvoice = self.env['account.invoice']
        for repair in self.filtered(lambda r: not (r.state in ('draft', 'cancel') or r.invoice_id)):
            res[repair.id] = False
            if not (repair.partner_id.id and repair.partner_invoice_id.id):
                raise UserError(_('You have to select a Partner Invoice Address in the repair form!'))
            comment = repair.quotation_notes
            if (repair.invoice_method != 'none'):
                if group and repair.partner_invoice_id.id in invoices_group:
                    invoice = invoices_group[repair.partner_invoice_id.id]
                    invoice_vals = {
                        'name': invoice.name + ', ' + repair.wwww,
                        'origin': invoice.origin + ', ' + repair.name,
                        'comment': (comment and (invoice.comment and invoice.comment + "\n" + comment or comment)) or (invoice.comment and invoice.comment or ''),
                    }
                    AccountInvoice.write([invoice], invoice_vals)
                else:
                    if not repair.partner_id.property_account_receivable_id:
                        raise UserError(_('No account defined for partner "%s".') % repair.partner_id.name)
                    account_id = repair.partner_id.property_account_receivable_id.id
                    inv = {
                        'name': repair.name,
                        'origin': repair.name,
                        'type': 'out_invoice',
                        'account_id': account_id,
                        'partner_id': repair.partner_invoice_id.id or repair.partner_id.id,
                        'currency_id': repair.pricelist_id.currency_id.id,
                        'comment': repair.quotation_notes,
                        'fiscal_position_id': repair.partner_id.property_account_position_id.id
                    }
                    invoice = AccountInvoice.create(inv)
                    invoices_group[repair.partner_invoice_id.id] = invoice
                repair.write({'invoiced': True, 'invoice_id': invoice.id})

                for operation in repair.operations_ids:
                    if operation.to_invoice:
                        if group:
                            name = repair.name + '-' + operation.name
                        else:
                            name = operation.name

                        if operation.product_id.property_account_income_id:
                            account_id = operation.product_id.property_account_income_id.id
                        elif operation.product_id.categ_id.property_account_income_categ_id:
                            account_id = operation.product_id.categ_id.property_account_income_categ_id.id
                        else:
                            raise UserError(_('No account defined for product "%s".') % operation.product_id.name)

                        invoice_line = AccountInvoiceLine.create({
                            'invoice_id': invoice.id,
                            'name': name,
                            'origin': repair.name,
                            'account_id': account_id,
                            'quantity': operation.product_uom_qty,
                            'invoice_line_tax_ids': [(6, 0, [x.id for x in operation.tax_id])],
                            'uom_id': operation.product_uom_id.id,
                            'price_unit': operation.price_unit,
                            'price_subtotal': operation.product_uom_qty * operation.price_unit,
                            'product_id': operation.product_id and operation.product_id.id or False
                        })
                        operation.write({'invoiced': True, 'invoice_line_id': invoice_line.id})
                for fee in repair.fees_lines_ids:
                    if fee.to_invoice:
                        if group:
                            name = repair.name + '-' + fee.name
                        else:
                            name = fee.name
                        if not fee.product_id:
                            raise UserError(_('No product defined on Fees!'))

                        if fee.product_id.property_account_income_id:
                            account_id = fee.product_id.property_account_incomed_id.id
                        elif fee.product_id.categ_id.property_account_income_categ_id:
                            account_id = fee.product_id.categ_id.property_account_income_categ_id.id
                        else:
                            raise UserError(_('No account defined for product "%s".') % fee.product_id.name)

                        invoice_fee = AccountInvoiceLine.create({
                            'invoice_id': invoice.id,
                            'name': name,
                            'origin': repair.name,
                            'account_id': account_id,
                            'quantity': fee.product_uom_qty,
                            'invoice_line_tax_ids': [(6, 0, [x.id for x in fee.tax_id])],
                            'uom_id': fee.product_uom_id.id,
                            'product_id': fee.product_id and fee.product_id.id or False,
                            'price_unit': fee.price_unit,
                            'price_subtotal': fee.product_uom_qty * fee.price_unit
                        })
                        fee.write({'invoiced': True, 'invoice_line_id': invoice_fee.id})
                res[repair.id] = invoice.id
        return res

    @api.multi
    def action_repair_ready(self):
        """ Writes repair order state to 'Ready'
        @return: True
        """
        for repair in self:
            repair.operations_ids.write({'state': 'confirmed'})
            repair.state = 'ready'
        return True

    @api.multi
    def action_repair_start(self):
        """ Writes repair order state to 'Under Repair'
        @return: True
        """
        for repair in self:
            repair.operations_ids.write({'state': 'confirmed'})
            repair.state = 'under_repair'
        return True

    @api.multi
    def action_repair_end(self):
        """ Writes repair order state to 'To be invoiced' if invoice method is
        After repair else state is set to 'Ready'.
        @return: True
        """
        for order in self:
            val = {}
            val['repaired'] = True
            if (not order.invoiced and order.invoice_method == 'after_repair'):
                val['state'] = '2binvoiced'
            elif (not order.invoiced and order.invoice_method == 'b4repair'):
                val['state'] = 'ready'
            else:
                pass
            order.write(val)
        return True

    @api.multi
    def wkf_repair_done(self):
        self.action_repair_done()
        return True

    @api.model
    def action_repair_done(self):
        """ Creates stock move for operation and stock move for final product of repair order.
        @return: Move ids of final products
        """
        res = {}
        StockMove = self.env['stock.move']
        for repair in self:
            moves = StockMove
            for move in repair.operations_ids:
                create_move = StockMove.create({
                    'name': move.name,
                    'product_id': move.product_id.id,
                    'restrict_lot_id': move.lot_id.id,
                    'product_uom_qty': move.product_uom_qty,
                    'product_uom': move.product_uom_id.id,
                    'partner_id': repair.address_id and repair.address_id.id or False,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                })
                moves |= create_move
                move.write({'move_id': create_move.id, 'state': 'done'})
            create_move = StockMove.create({
                'name': repair.name,
                'product_id': repair.product_id.id,
                'product_uom': repair.product_uom_id.id or repair.product_id.uom_id.id,
                'product_uom_qty': repair.product_qty,
                'partner_id': repair.address_id and repair.address_id.id or False,
                'location_id': repair.location_id.id,
                'location_dest_id': repair.location_dest_id.id,
                'restrict_lot_id': repair.lot_id.id,
            })
            moves |= create_move
            moves.action_done()
            repair.write({'state': 'done', 'move_id': create_move.id})
            res[repair.id] = create_move.id
        return res


class ProductChangeMixin(object):
    @api.multi
    def product_id_change(self, pricelist, product, uom=False,
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
        ctx = self.env.context.copy()
        ctx['uom'] = uom

        if not product_uom_qty:
            product_uom_qty = 1
        result['product_uom_qty'] = product_uom_qty

        if product:
            product_obj = self.with_context(ctx).env['product.product'].browse(product)

            if partner_id:
                partner = self.env['res.partner'].browse(partner_id)

                result['tax_id'] = partner.property_account_position_id.with_context(ctx).map_tax(product_obj.taxes_id)
            result['name'] = product_obj.display_name
            result['product_uom_id'] = product_obj.uom_id and product_obj.uom_id.id or False
            if not pricelist:
                warning = {
                    'title': _('No Pricelist!'),
                    'message':
                        _('You have to select a pricelist in the Repair form !\n'
                        'Please set one before choosing a product.')
                }
            else:
                pricelist_obj = self.env['product.pricelist'].browse(pricelist)
                price = pricelist_obj.price_get(product, product_uom_qty, partner_id)[pricelist]
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


class MrpRepairLine(models.Model, ProductChangeMixin):
    _name = 'mrp.repair.line'
    _description = 'Repair Line'

    @api.multi
    def _amount_line(self):
        """ Calculates amount.
        """
        for line in self:
            cur = line.repair_id.pricelist_id.currency_id
            temp = cur.round(line.to_invoice and line.price_unit * line.product_uom_qty or 0)
            line.price_subtotal = temp

    name = fields.Char(string='Description', required=True)
    repair_id = fields.Many2one('mrp.repair', string='Repair Order Reference', ondelete='cascade', index=True)
    repair_type = fields.Selection([('add', 'Add'), ('remove', 'Remove')], string='Type', required=True, oldname="type")
    to_invoice = fields.Boolean(string='To Invoice')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    invoiced = fields.Boolean(string='Invoiced', readonly=True, copy=False)
    price_unit = fields.Float(string='Unit Price', required=True, digits_compute=dp.get_precision('Product Price'))
    price_subtotal = fields.Float(compute='_amount_line', string='Subtotal', digits_compute=dp.get_precision('Account'))
    tax_id = fields.Many2many('account.tax', 'repair_operation_line_tax', 'repair_operation_line_id', 'tax_id', string='Taxes')
    product_uom_qty = fields.Float(string='Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), default=lambda *a: 1, required=True)
    product_uom_id = fields.Many2one('product.uom', string='Product Unit of Measure', required=True, oldname="product_uom")
    invoice_line_id = fields.Many2one('account.invoice.line', string='Invoice Line', readonly=True, copy=False)
    location_id = fields.Many2one('stock.location', string='Source Location', required=True, select=True)
    location_dest_id = fields.Many2one('stock.location', 'Dest.Location', required=True, select=True)
    move_id = fields.Many2one('stock.move', string='Inventory Move', readonly=True, copy=False)
    lot_id = fields.Many2one('stock.production.lot', string='Lot')
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('cancel', 'Cancelled')], default=lambda *a: 'draft', string='Status', required=True, readonly=True, copy=False, help=' * The \'Draft\' status is set automatically as draft when repair order in draft status. \
                        \n* The \'Confirmed\' status is set automatically as confirm when repair order in confirm status. \
                        \n* The \'Done\' status is set automatically when repair order is completed.\
                        \n* The \'Cancelled\' status is set automatically when user cancel repair order.')

    @api.multi
    def onchange_operation_type(self, repair_type, guarantee_limit, company_id=False):
        """ On change of operation type it sets source location, destination location
        and to invoice field.
        @param product: Changed operation type.
        @param guarantee_limit: Guarantee limit of current record.
        @return: Dictionary of values.
        """
        if not repair_type:
            return {'value': {
                'location_id': False,
                'location_dest_id': False
            }}
        StockLocation = self.env['stock.location']
        StockWarehose = self.env['stock.warehouse']
        location_id = StockLocation.search([('usage', '=', 'production')])
        location_id = location_id and location_id.id or False

        if repair_type == 'add':
            # TOCHECK: Find stock location for user's company warehouse or
            # repair order's company's warehouse (company_id field is added in fix of lp:831583)
            args = company_id and [('company_id', '=', company_id)] or []
            warehouse_ids = StockWarehose.search(args)
            stock_id = False
            if warehouse_ids:
                stock_id = StockWarehose.browse(warehouse_ids[0].id).lot_stock_id.id
            to_invoice = (guarantee_limit and fields.Date.from_string(guarantee_limit) < fields.Date.from_string(fields.Date.today()))

            return {'value': {
                'to_invoice': to_invoice,
                'location_id': stock_id,
                'location_dest_id': location_id
            }}
        scrap_location_ids = StockLocation.search([('scrap_location', '=', True)])

        return {'value': {
                'to_invoice': False,
                'location_id': location_id,
                'location_dest_id': scrap_location_ids and scrap_location_ids[0] or False,
                }}


class MrpRepairFee(models.Model, ProductChangeMixin):
    _name = 'mrp.repair.fee'
    _description = 'Repair Fees Line'

    @api.multi
    def _amount_line(self):
        """ Calculates amount.
        """
        for line in self:
            cur = line.repair_id.pricelist_id.currency_id
            line.price_subtotal = cur.round(line.to_invoice and line.price_unit * line.product_uom_qty or 0)

    repair_id = fields.Many2one('mrp.repair', string='Repair Order Reference', required=True, ondelete='cascade', index=True)
    name = fields.Char(string='Description', index=True, required=True)
    product_id = fields.Many2one('product.product', string='Product')
    product_uom_qty = fields.Float(string='Quantity', digits_compute=dp.get_precision('Product Unit of Measure'), required=True)
    price_unit = fields.Float(string='Unit Price', required=True)
    product_uom_id = fields.Many2one('product.uom', string='Product Unit of Measure', required=True, oldname="product_uom")
    price_subtotal = fields.Float(compute='_amount_line', string='Subtotal', digits_compute=dp.get_precision('Account'))
    tax_id = fields.Many2many('account.tax', 'repair_fee_line_tax', 'repair_fee_line_id', 'tax_id', string='Taxes')
    invoice_line_id = fields.Many2one('account.invoice.line', string='Invoice Line', readonly=True, copy=False)
    to_invoice = fields.Boolean(string='To Invoice', default=lambda *a: True)
    invoiced = fields.Boolean(string='Invoiced', readonly=True, copy=False)
