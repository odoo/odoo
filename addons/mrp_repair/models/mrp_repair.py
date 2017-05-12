# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError


class Repair(models.Model):
    _name = 'mrp.repair'
    _description = 'Repair Order'
    _inherit = 'mail.thread'

    @api.model
    def _default_stock_location(self):
        warehouse = self.env.ref('stock.warehouse0', raise_if_not_found=False)
        if warehouse:
            return warehouse.lot_stock_id.id
        return False

    name = fields.Char(
        'Repair Reference',
        default=lambda self: self.env['ir.sequence'].next_by_code('mrp.repair'),
        copy=False, required=True,
        states={'confirmed': [('readonly', True)]})
    product_id = fields.Many2one(
        'product.product', string='Product to Repair',
        readonly=True, required=True, states={'draft': [('readonly', False)]})
    product_qty = fields.Float(
        'Product Quantity',
        default=1.0, digits=dp.get_precision('Product Unit of Measure'),
        readonly=True, required=True, states={'draft': [('readonly', False)]})
    product_uom = fields.Many2one(
        'product.uom', 'Product Unit of Measure',
        readonly=True, required=True, states={'draft': [('readonly', False)]})
    partner_id = fields.Many2one(
        'res.partner', 'Partner',
        index=True, states={'confirmed': [('readonly', True)]},
        help='Choose partner for whom the order will be invoiced and delivered.')
    address_id = fields.Many2one(
        'res.partner', 'Delivery Address',
        domain="[('parent_id','=',partner_id)]",
        states={'confirmed': [('readonly', True)]})
    default_address_id = fields.Many2one('res.partner', compute='_compute_default_address_id')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('cancel', 'Cancelled'),
        ('confirmed', 'Confirmed'),
        ('under_repair', 'Under Repair'),
        ('ready', 'Ready to Repair'),
        ('2binvoiced', 'To be Invoiced'),
        ('invoice_except', 'Invoice Exception'),
        ('done', 'Repaired')], string='Status',
        copy=False, default='draft', readonly=True, track_visibility='onchange',
        help="* The \'Draft\' status is used when a user is encoding a new and unconfirmed repair order.\n"
             "* The \'Confirmed\' status is used when a user confirms the repair order.\n"
             "* The \'Ready to Repair\' status is used to start to repairing, user can start repairing only after repair order is confirmed.\n"
             "* The \'To be Invoiced\' status is used to generate the invoice before or after repairing done.\n"
             "* The \'Done\' status is set when repairing is completed.\n"
             "* The \'Cancelled\' status is used when user cancel repair order.")
    location_id = fields.Many2one(
        'stock.location', 'Current Location',
        default=_default_stock_location,
        index=True, readonly=True, required=True,
        states={'draft': [('readonly', False)], 'confirmed': [('readonly', True)]})
    location_dest_id = fields.Many2one(
        'stock.location', 'Delivery Location',
        readonly=True, required=True,
        states={'draft': [('readonly', False)], 'confirmed': [('readonly', True)]})
    lot_id = fields.Many2one(
        'stock.production.lot', 'Repaired Lot',
        domain="[('product_id','=', product_id)]",
        help="Products repaired are all belonging to this lot", oldname="prodlot_id")
    guarantee_limit = fields.Date('Warranty Expiration', states={'confirmed': [('readonly', True)]})
    operations = fields.One2many(
        'mrp.repair.line', 'repair_id', 'Operation Lines',
        copy=True, readonly=True, states={'draft': [('readonly', False)]})
    pricelist_id = fields.Many2one(
        'product.pricelist', 'Pricelist',
        default=lambda self: self.env['product.pricelist'].search([], limit=1).id,
        help='Pricelist of the selected partner.')
    partner_invoice_id = fields.Many2one('res.partner', 'Invoicing Address')
    invoice_method = fields.Selection([
        ("none", "No Invoice"),
        ("b4repair", "Before Repair"),
        ("after_repair", "After Repair")], string="Invoice Method",
        default='none', index=True, readonly=True, required=True,
        states={'draft': [('readonly', False)]},
        help='Selecting \'Before Repair\' or \'After Repair\' will allow you to generate invoice before or after the repair is done respectively. \'No invoice\' means you don\'t want to generate invoice for this repair order.')
    invoice_id = fields.Many2one(
        'account.invoice', 'Invoice',
        copy=False, readonly=True, track_visibility="onchange")
    move_id = fields.Many2one(
        'stock.move', 'Move',
        copy=False, readonly=True, track_visibility="onchange",
        help="Move created by the repair order")
    fees_lines = fields.One2many(
        'mrp.repair.fee', 'repair_id', 'Fees',
        copy=True, readonly=True, states={'draft': [('readonly', False)]})
    internal_notes = fields.Text('Internal Notes')
    quotation_notes = fields.Text('Quotation Notes')
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('mrp.repair'))
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    repaired = fields.Boolean('Repaired', copy=False, readonly=True)
    amount_untaxed = fields.Float('Untaxed Amount', compute='_amount_untaxed', store=True)
    amount_tax = fields.Float('Taxes', compute='_amount_tax', store=True)
    amount_total = fields.Float('Total', compute='_amount_total', store=True)

    @api.one
    @api.depends('partner_id')
    def _compute_default_address_id(self):
        if self.partner_id:
            self.default_address_id = self.partner_id.address_get(['contact'])['contact']

    @api.one
    @api.depends('operations.price_subtotal', 'fees_lines.price_subtotal', 'pricelist_id.currency_id')
    def _amount_untaxed(self):
        total = sum(operation.price_subtotal for operation in self.operations)
        total += sum(fee.price_subtotal for fee in self.fees_lines)
        self.amount_untaxed = self.pricelist_id.currency_id.round(total)

    @api.one
    @api.depends('operations.price_unit', 'operations.product_uom_qty', 'operations.product_id',
                 'fees_lines.price_unit', 'fees_lines.product_uom_qty', 'fees_lines.product_id',
                 'pricelist_id.currency_id', 'partner_id')
    def _amount_tax(self):
        val = 0.0
        for operation in self.operations:
            if operation.to_invoice and operation.tax_id:
                tax_calculate = operation.tax_id.compute_all(operation.price_unit, self.pricelist_id.currency_id, operation.product_uom_qty, operation.product_id, self.partner_id)
                for c in tax_calculate['taxes']:
                    val += c['amount']
        for fee in self.fees_lines:
            if fee.to_invoice and fee.tax_id:
                tax_calculate = fee.tax_id.compute_all(fee.price_unit, self.pricelist_id.currency_id, fee.product_uom_qty, fee.product_id, self.partner_id)
                for c in tax_calculate['taxes']:
                    val += c['amount']
        self.amount_tax = val

    @api.one
    @api.depends('amount_untaxed', 'amount_tax')
    def _amount_total(self):
        self.amount_total = self.pricelist_id.currency_id.round(self.amount_untaxed + self.amount_tax)

    _sql_constraints = [
        ('name', 'unique (name)', 'The name of the Repair Order must be unique!'),
    ]

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.guarantee_limit = False
        self.lot_id = False
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id

    @api.onchange('product_uom')
    def onchange_product_uom(self):
        res = {}
        if not self.product_id or not self.product_uom:
            return res
        if self.product_uom.category_id != self.product_id.uom_id.category_id:
            res['warning'] = {'title': _('Warning'), 'message': _('The Product Unit of Measure you chose has a different category than in the product form.')}
            self.product_uom = self.product_id.uom_id.id
        return res

    @api.onchange('location_id')
    def onchange_location_id(self):
        self.location_dest_id = self.location_id.id

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if not self.partner_id:
            self.address_id = False
            self.partner_invoice_id = False
            self.pricelist_id = self.env['product.pricelist'].search([], limit=1).id
        else:
            addresses = self.partner_id.address_get(['delivery', 'invoice', 'contact'])
            self.address_id = addresses['delivery'] or addresses['contact']
            self.partner_invoice_id = addresses['invoice']
            self.pricelist_id = self.partner_id.property_product_pricelist.id

    @api.multi
    def button_dummy(self):
        # TDE FIXME: this button is very interesting
        return True

    @api.multi
    def action_repair_cancel_draft(self):
        if self.filtered(lambda repair: repair.state != 'cancel'):
            raise UserError(_("Repair must be canceled in order to reset it to draft."))
        self.mapped('operations').write({'state': 'draft'})
        return self.write({'state': 'draft'})

    @api.multi
    def action_repair_confirm(self):
        """ Repair order state is set to 'To be invoiced' when invoice method
        is 'Before repair' else state becomes 'Confirmed'.
        @param *arg: Arguments
        @return: True
        """
        if self.filtered(lambda repair: repair.state != 'draft'):
            raise UserError(_("Can only confirm draft repairs."))
        before_repair = self.filtered(lambda repair: repair.invoice_method == 'b4repair')
        before_repair.write({'state': '2binvoiced'})
        to_confirm = self - before_repair
        to_confirm_operations = to_confirm.mapped('operations')
        for operation in to_confirm_operations:
            if operation.product_id.tracking != 'none' and not operation.lot_id:
                raise UserError(_("Serial number is required for operation line with product '%s'") % (operation.product_id.name))
        to_confirm_operations.write({'state': 'confirmed'})
        to_confirm.write({'state': 'confirmed'})
        return True

    @api.multi
    def action_repair_cancel(self):
        if self.filtered(lambda repair: repair.state == 'done'):
            raise UserError(_("Cannot cancel completed repairs."))
        if any(repair.invoiced for repair in self):
            raise UserError(_('Repair order is already invoiced.'))
        self.mapped('operations').write({'state': 'cancel'})
        return self.write({'state': 'cancel'})

    @api.multi
    def action_repair_invoice_create(self):
        self.action_invoice_create()
        if self.invoice_method == 'b4repair':
            self.action_repair_ready()
        elif self.invoice_method == 'after_repair':
            self.write({'state': 'done'})
        return True

    @api.multi
    def action_invoice_create(self, group=False):
        """ Creates invoice(s) for repair order.
        @param group: It is set to true when group invoice is to be generated.
        @return: Invoice Ids.
        """
        res = dict.fromkeys(self.ids, False)
        invoices_group = {}
        InvoiceLine = self.env['account.invoice.line']
        Invoice = self.env['account.invoice']
        for repair in self.filtered(lambda repair: repair.state not in ('draft', 'cancel') and not repair.invoice_id):
            if not repair.partner_id.id and not repair.partner_invoice_id.id:
                raise UserError(_('You have to select a Partner Invoice Address in the repair form!'))
            comment = repair.quotation_notes
            if repair.invoice_method != 'none':
                if group and repair.partner_invoice_id.id in invoices_group:
                    invoice = invoices_group[repair.partner_invoice_id.id]
                    invoice.write({
                        'name': invoice.name + ', ' + repair.name,
                        'origin': invoice.origin + ', ' + repair.name,
                        'comment': (comment and (invoice.comment and invoice.comment + "\n" + comment or comment)) or (invoice.comment and invoice.comment or ''),
                    })
                else:
                    if not repair.partner_id.property_account_receivable_id:
                        raise UserError(_('No account defined for partner "%s".') % repair.partner_id.name)
                    invoice = Invoice.create({
                        'name': repair.name,
                        'origin': repair.name,
                        'type': 'out_invoice',
                        'account_id': repair.partner_id.property_account_receivable_id.id,
                        'partner_id': repair.partner_invoice_id.id or repair.partner_id.id,
                        'currency_id': repair.pricelist_id.currency_id.id,
                        'comment': repair.quotation_notes,
                        'fiscal_position_id': repair.partner_id.property_account_position_id.id
                    })
                    invoices_group[repair.partner_invoice_id.id] = invoice
                repair.write({'invoiced': True, 'invoice_id': invoice.id})

                for operation in repair.operations.filtered(lambda operation: operation.to_invoice):
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

                    invoice_line = InvoiceLine.create({
                        'invoice_id': invoice.id,
                        'name': name,
                        'origin': repair.name,
                        'account_id': account_id,
                        'quantity': operation.product_uom_qty,
                        'invoice_line_tax_ids': [(6, 0, [x.id for x in operation.tax_id])],
                        'uom_id': operation.product_uom.id,
                        'price_unit': operation.price_unit,
                        'price_subtotal': operation.product_uom_qty * operation.price_unit,
                        'product_id': operation.product_id and operation.product_id.id or False
                    })
                    operation.write({'invoiced': True, 'invoice_line_id': invoice_line.id})
                for fee in repair.fees_lines.filtered(lambda fee: fee.to_invoice):
                    if group:
                        name = repair.name + '-' + fee.name
                    else:
                        name = fee.name
                    if not fee.product_id:
                        raise UserError(_('No product defined on Fees!'))

                    if fee.product_id.property_account_income_id:
                        account_id = fee.product_id.property_account_income_id.id
                    elif fee.product_id.categ_id.property_account_income_categ_id:
                        account_id = fee.product_id.categ_id.property_account_income_categ_id.id
                    else:
                        raise UserError(_('No account defined for product "%s".') % fee.product_id.name)

                    invoice_line = InvoiceLine.create({
                        'invoice_id': invoice.id,
                        'name': name,
                        'origin': repair.name,
                        'account_id': account_id,
                        'quantity': fee.product_uom_qty,
                        'invoice_line_tax_ids': [(6, 0, [x.id for x in fee.tax_id])],
                        'uom_id': fee.product_uom.id,
                        'product_id': fee.product_id and fee.product_id.id or False,
                        'price_unit': fee.price_unit,
                        'price_subtotal': fee.product_uom_qty * fee.price_unit
                    })
                    fee.write({'invoiced': True, 'invoice_line_id': invoice_line.id})
                invoice.compute_taxes()
                res[repair.id] = invoice.id
        return res

    @api.multi
    def action_repair_ready(self):
        self.mapped('operations').write({'state': 'confirmed'})
        return self.write({'state': 'ready'})

    @api.multi
    def action_repair_start(self):
        """ Writes repair order state to 'Under Repair'
        @return: True
        """
        if self.filtered(lambda repair: repair.state not in ['confirmed', 'ready']):
            raise UserError(_("Repair must be confirmed before starting reparation."))
        self.mapped('operations').write({'state': 'confirmed'})
        return self.write({'state': 'under_repair'})

    @api.multi
    def action_repair_end(self):
        """ Writes repair order state to 'To be invoiced' if invoice method is
        After repair else state is set to 'Ready'.
        @return: True
        """
        if self.filtered(lambda repair: repair.state != 'under_repair'):
            raise UserError(_("Repair must be under repair in order to end reparation."))
        for repair in self:
            repair.write({'repaired': True})
            vals = {'state': 'done'}
            vals['move_id'] = repair.action_repair_done().get(repair.id)
            if not repair.invoiced and repair.invoice_method == 'after_repair':
                vals['state'] = '2binvoiced'
            repair.write(vals)
        return True

    @api.multi
    def action_repair_done(self):
        """ Creates stock move for operation and stock move for final product of repair order.
        @return: Move ids of final products

        """
        if self.filtered(lambda repair: not repair.repaired):
            raise UserError(_("Repair must be repaired in order to make the product moves."))
        res = {}
        Move = self.env['stock.move']
        for repair in self:
            moves = self.env['stock.move']
            for operation in repair.operations:
                move = Move.create({
                    'name': operation.name,
                    'product_id': operation.product_id.id,
                    'restrict_lot_id': operation.lot_id.id,
                    'product_uom_qty': operation.product_uom_qty,
                    'product_uom': operation.product_uom.id,
                    'partner_id': repair.address_id.id,
                    'location_id': operation.location_id.id,
                    'location_dest_id': operation.location_dest_id.id,
                })
                moves |= move
                operation.write({'move_id': move.id, 'state': 'done'})
            move = Move.create({
                'name': repair.name,
                'product_id': repair.product_id.id,
                'product_uom': repair.product_uom.id or repair.product_id.uom_id.id,
                'product_uom_qty': repair.product_qty,
                'partner_id': repair.address_id.id,
                'location_id': repair.location_id.id,
                'location_dest_id': repair.location_dest_id.id,
                'restrict_lot_id': repair.lot_id.id,
            })
            moves |= move
            moves.action_done()
            res[repair.id] = move.id
        return res


class RepairLine(models.Model):
    _name = 'mrp.repair.line'
    _description = 'Repair Line'

    name = fields.Char('Description', required=True)
    repair_id = fields.Many2one(
        'mrp.repair', 'Repair Order Reference',
        index=True, ondelete='cascade')
    type = fields.Selection([
        ('add', 'Add'),
        ('remove', 'Remove')], 'Type', required=True)
    to_invoice = fields.Boolean('To Invoice')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    price_unit = fields.Float('Unit Price', required=True, digits=dp.get_precision('Product Price'))
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', digits=0)
    tax_id = fields.Many2many(
        'account.tax', 'repair_operation_line_tax', 'repair_operation_line_id', 'tax_id', 'Taxes')
    product_uom_qty = fields.Float(
        'Quantity', default=1.0,
        digits=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom = fields.Many2one(
        'product.uom', 'Product Unit of Measure',
        required=True)
    invoice_line_id = fields.Many2one(
        'account.invoice.line', 'Invoice Line',
        copy=False, readonly=True)
    location_id = fields.Many2one(
        'stock.location', 'Source Location',
        index=True, required=True)
    location_dest_id = fields.Many2one(
        'stock.location', 'Dest. Location',
        index=True, required=True)
    move_id = fields.Many2one(
        'stock.move', 'Inventory Move',
        copy=False, readonly=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], 'Status', default='draft',
        copy=False, readonly=True, required=True,
        help='The status of a repair line is set automatically to the one of the linked repair order.')

    @api.one
    @api.depends('to_invoice', 'price_unit', 'repair_id', 'product_uom_qty', 'product_id')
    def _compute_price_subtotal(self):
        if not self.to_invoice:
            self.price_subtotal = 0.0
        else:
            taxes = self.tax_id.compute_all(self.price_unit, self.repair_id.pricelist_id.currency_id, self.product_uom_qty, self.product_id, self.repair_id.partner_id)
            self.price_subtotal = taxes['total_excluded']

    @api.onchange('type', 'repair_id')
    def onchange_operation_type(self):
        """ On change of operation type it sets source location, destination location
        and to invoice field.
        @param product: Changed operation type.
        @param guarantee_limit: Guarantee limit of current record.
        @return: Dictionary of values.
        """
        if not self.type:
            self.location_id = False
            self.Location_dest_id = False
        elif self.type == 'add':
            args = self.repair_id.company_id and [('company_id', '=', self.repair_id.company_id.id)] or []
            warehouse = self.env['stock.warehouse'].search(args, limit=1)
            self.location_id = warehouse.lot_stock_id
            self.location_dest_id = self.env['stock.location'].search([('usage', '=', 'production')], limit=1).id
            self.to_invoice = self.repair_id.guarantee_limit and datetime.strptime(self.repair_id.guarantee_limit, '%Y-%m-%d') < datetime.now()
        else:
            self.location_id = self.env['stock.location'].search([('usage', '=', 'production')], limit=1).id
            self.location_dest_id = self.env['stock.location'].search([('scrap_location', '=', True)], limit=1).id
            self.to_invoice = False

    @api.onchange('repair_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        """ On change of product it sets product quantity, tax account, name,
        uom of product, unit price and price subtotal. """
        partner = self.repair_id.partner_id
        pricelist = self.repair_id.pricelist_id

        if not self.product_id or not self.product_uom_qty:
            return
        if partner and self.product_id:
            self.tax_id = partner.property_account_position_id.map_tax(self.product_id.taxes_id, self.product_id, partner).ids
        if self.product_id:
            if partner:
                self.name = self.product_id.with_context(lang=partner.lang).display_name
            else:
                self.name = self.product_id.display_name
            self.product_uom = self.product_id.uom_id.id

        warning = False
        if not pricelist:
            warning = {
                'title': _('No Pricelist!'),
                'message':
                    _('You have to select a pricelist in the Repair form !\n Please set one before choosing a product.')}
        else:
            price = pricelist.get_product_price(self.product_id, self.product_uom_qty, partner)
            if price is False:
                warning = {
                    'title': _('No valid pricelist line found !'),
                    'message':
                        _("Couldn't find a pricelist line matching this product and quantity.\nYou have to change either the product, the quantity or the pricelist.")}
            else:
                self.price_unit = price
        if warning:
            return {'warning': warning}


class RepairFee(models.Model):
    _name = 'mrp.repair.fee'
    _description = 'Repair Fees Line'

    repair_id = fields.Many2one(
        'mrp.repair', 'Repair Order Reference',
        index=True, ondelete='cascade', required=True)
    name = fields.Char('Description', index=True, required=True)
    product_id = fields.Many2one('product.product', 'Product')
    product_uom_qty = fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0)
    price_unit = fields.Float('Unit Price', required=True)
    product_uom = fields.Many2one('product.uom', 'Product Unit of Measure', required=True)
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', digits=0)
    tax_id = fields.Many2many('account.tax', 'repair_fee_line_tax', 'repair_fee_line_id', 'tax_id', 'Taxes')
    invoice_line_id = fields.Many2one('account.invoice.line', 'Invoice Line', copy=False, readonly=True)
    to_invoice = fields.Boolean('To Invoice', default=True)
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)

    @api.one
    @api.depends('to_invoice', 'price_unit', 'repair_id', 'product_uom_qty', 'product_id')
    def _compute_price_subtotal(self):
        if not self.to_invoice:
            self.price_subtotal = 0.0
        else:
            taxes = self.tax_id.compute_all(self.price_unit, self.repair_id.pricelist_id.currency_id, self.product_uom_qty, self.product_id, self.repair_id.partner_id)
            self.price_subtotal = taxes['total_excluded']

    @api.onchange('repair_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        """ On change of product it sets product quantity, tax account, name,
        uom of product, unit price and price subtotal. """
        if not self.product_id or not self.product_uom_qty:
            return

        partner = self.repair_id.partner_id
        pricelist = self.repair_id.pricelist_id

        if partner and self.product_id:
            self.tax_id = partner.property_account_position_id.map_tax(self.product_id.taxes_id, self.product_id, partner).ids
        if self.product_id:
            self.name = self.product_id.display_name
            self.product_uom = self.product_id.uom_id.id

        warning = False
        if not pricelist:
            warning = {
                'title': _('No Pricelist!'),
                'message':
                    _('You have to select a pricelist in the Repair form !\n Please set one before choosing a product.')}
        else:
            price = pricelist.get_product_price(self.product_id, self.product_uom_qty, partner)
            if price is False:
                warning = {
                    'title': _('No valid pricelist line found !'),
                    'message':
                        _("Couldn't find a pricelist line matching this product and quantity.\nYou have to change either the product, the quantity or the pricelist.")}
            else:
                self.price_unit = price
        if warning:
            return {'warning': warning}
