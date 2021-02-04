# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from random import randint

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    repair_id = fields.Many2one('repair.order', check_company=True)


class Repair(models.Model):
    _name = 'repair.order'
    _description = 'Repair Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        'Repair Reference',
        default='/',
        copy=False, required=True,
        states={'confirmed': [('readonly', True)]})
    product_id = fields.Many2one(
        'product.product', string='Product to Repair',
        domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', company_id), ('company_id', '=', False)]",
        readonly=True, required=True, states={'draft': [('readonly', False)]}, check_company=True)
    product_qty = fields.Float(
        'Product Quantity',
        default=1.0, digits='Product Unit of Measure',
        readonly=True, required=True, states={'draft': [('readonly', False)]})
    product_uom = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        readonly=True, required=True, states={'draft': [('readonly', False)]}, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    partner_id = fields.Many2one(
        'res.partner', 'Customer',
        index=True, states={'confirmed': [('readonly', True)]}, check_company=True, change_default=True,
        help='Choose partner for whom the order will be invoiced and delivered. You can find a partner by its Name, TIN, Email or Internal Reference.')
    address_id = fields.Many2one(
        'res.partner', 'Delivery Address',
        domain="[('parent_id','=',partner_id)]", check_company=True,
        states={'confirmed': [('readonly', True)]})
    default_address_id = fields.Many2one('res.partner', compute='_compute_default_address_id')
    state = fields.Selection([
        ('draft', 'Quotation'),
        ('confirmed', 'Confirmed'),
        ('under_repair', 'Under Repair'),
        ('ready', 'Ready to Repair'),
        ('2binvoiced', 'To be Invoiced'),
        ('invoice_except', 'Invoice Exception'),
        ('done', 'Repaired'),
        ('cancel', 'Cancelled')], string='Status',
        copy=False, default='draft', readonly=True, tracking=True,
        help="* The \'Draft\' status is used when a user is encoding a new and unconfirmed repair order.\n"
             "* The \'Confirmed\' status is used when a user confirms the repair order.\n"
             "* The \'Ready to Repair\' status is used to start to repairing, user can start repairing only after repair order is confirmed.\n"
             "* The \'To be Invoiced\' status is used to generate the invoice before or after repairing done.\n"
             "* The \'Done\' status is set when repairing is completed.\n"
             "* The \'Cancelled\' status is used when user cancel repair order.")
    location_id = fields.Many2one(
        'stock.location', 'Location',
        index=True, readonly=True, required=True, check_company=True,
        help="This is the location where the product to repair is located.",
        states={'draft': [('readonly', False)], 'confirmed': [('readonly', True)]})
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial',
        domain="[('product_id','=', product_id), ('company_id', '=', company_id)]", check_company=True,
        help="Products repaired are all belonging to this lot")
    guarantee_limit = fields.Date('Warranty Expiration', states={'confirmed': [('readonly', True)]})
    operations = fields.One2many(
        'repair.line', 'repair_id', 'Parts',
        copy=True, readonly=True, states={'draft': [('readonly', False)]})
    pricelist_id = fields.Many2one(
        'product.pricelist', 'Pricelist',
        default=lambda self: self.env['product.pricelist'].search([('company_id', 'in', [self.env.company.id, False])], limit=1).id,
        help='Pricelist of the selected partner.', check_company=True)
    currency_id = fields.Many2one(related='pricelist_id.currency_id')
    partner_invoice_id = fields.Many2one('res.partner', 'Invoicing Address', check_company=True)
    invoice_method = fields.Selection([
        ("none", "No Invoice"),
        ("b4repair", "Before Repair"),
        ("after_repair", "After Repair")], string="Invoice Method",
        default='none', index=True, readonly=True, required=True,
        states={'draft': [('readonly', False)]},
        help='Selecting \'Before Repair\' or \'After Repair\' will allow you to generate invoice before or after the repair is done respectively. \'No invoice\' means you don\'t want to generate invoice for this repair order.')
    invoice_id = fields.Many2one(
        'account.move', 'Invoice',
        copy=False, readonly=True, tracking=True,
        domain=[('move_type', '=', 'out_invoice')])
    move_id = fields.Many2one(
        'stock.move', 'Move',
        copy=False, readonly=True, tracking=True, check_company=True,
        help="Move created by the repair order")
    fees_lines = fields.One2many(
        'repair.fee', 'repair_id', 'Operations',
        copy=True, readonly=True, states={'draft': [('readonly', False)]})
    internal_notes = fields.Text('Internal Notes')
    quotation_notes = fields.Text('Quotation Notes')
    user_id = fields.Many2one('res.users', string="Responsible", default=lambda self: self.env.user, check_company=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        readonly=True, required=True, index=True,
        default=lambda self: self.env.company)
    tag_ids = fields.Many2many('repair.tags', string="Tags")
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    repaired = fields.Boolean('Repaired', copy=False, readonly=True)
    amount_untaxed = fields.Float('Untaxed Amount', compute='_amount_untaxed', store=True)
    amount_tax = fields.Float('Taxes', compute='_amount_tax', store=True)
    amount_total = fields.Float('Total', compute='_amount_total', store=True)
    tracking = fields.Selection(string='Product Tracking', related="product_id.tracking", readonly=False)
    invoice_state = fields.Selection(string='Invoice State', related='invoice_id.state')

    @api.depends('partner_id')
    def _compute_default_address_id(self):
        for order in self:
            if order.partner_id:
                order.default_address_id = order.partner_id.address_get(['contact'])['contact']

    @api.depends('operations.price_subtotal', 'invoice_method', 'fees_lines.price_subtotal', 'pricelist_id.currency_id')
    def _amount_untaxed(self):
        for order in self:
            total = sum(operation.price_subtotal for operation in order.operations)
            total += sum(fee.price_subtotal for fee in order.fees_lines)
            order.amount_untaxed = order.pricelist_id.currency_id.round(total)

    @api.depends('operations.price_unit', 'operations.product_uom_qty', 'operations.product_id',
                 'fees_lines.price_unit', 'fees_lines.product_uom_qty', 'fees_lines.product_id',
                 'pricelist_id.currency_id', 'partner_id')
    def _amount_tax(self):
        for order in self:
            val = 0.0
            for operation in order.operations:
                if operation.tax_id:
                    tax_calculate = operation.tax_id.compute_all(operation.price_unit, order.pricelist_id.currency_id, operation.product_uom_qty, operation.product_id, order.partner_id)
                    for c in tax_calculate['taxes']:
                        val += c['amount']
            for fee in order.fees_lines:
                if fee.tax_id:
                    tax_calculate = fee.tax_id.compute_all(fee.price_unit, order.pricelist_id.currency_id, fee.product_uom_qty, fee.product_id, order.partner_id)
                    for c in tax_calculate['taxes']:
                        val += c['amount']
            order.amount_tax = val

    @api.depends('amount_untaxed', 'amount_tax')
    def _amount_total(self):
        for order in self:
            order.amount_total = order.pricelist_id.currency_id.round(order.amount_untaxed + order.amount_tax)

    _sql_constraints = [
        ('name', 'unique (name)', 'The name of the Repair Order must be unique!'),
    ]

    @api.onchange('product_id')
    def onchange_product_id(self):
        self.guarantee_limit = False
        if (self.product_id and self.lot_id and self.lot_id.product_id != self.product_id) or not self.product_id:
            self.lot_id = False
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id

    @api.onchange('product_uom')
    def onchange_product_uom(self):
        res = {}
        if not self.product_id or not self.product_uom:
            return res
        if self.product_uom.category_id != self.product_id.uom_id.category_id:
            res['warning'] = {'title': _('Warning'), 'message': _('The product unit of measure you chose has a different category than the product unit of measure.')}
            self.product_uom = self.product_id.uom_id.id
        return res

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self = self.with_company(self.company_id)
        if not self.partner_id:
            self.address_id = False
            self.partner_invoice_id = False
            self.pricelist_id = self.env['product.pricelist'].search([
                ('company_id', 'in', [self.env.company.id, False]),
            ], limit=1)
        else:
            addresses = self.partner_id.address_get(['delivery', 'invoice', 'contact'])
            self.address_id = addresses['delivery'] or addresses['contact']
            self.partner_invoice_id = addresses['invoice']
            self.pricelist_id = self.partner_id.property_product_pricelist.id

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
            self.location_id = warehouse.lot_stock_id
        else:
            self.location_id = False

    def unlink(self):
        for order in self:
            if order.state not in ('draft', 'cancel'):
                raise UserError(_('You can not delete a repair order once it has been confirmed. You must first cancel it.'))
            if order.state == 'cancel' and order.invoice_id and order.invoice_id.posted_before:
                raise UserError(_('You can not delete a repair order which is linked to an invoice which has been posted once.'))
        return super().unlink()

    @api.model
    def create(self, vals):
        # To avoid consuming a sequence number when clicking on 'Create', we preprend it if the
        # the name starts with '/'.
        vals['name'] = vals.get('name') or '/'
        if vals['name'].startswith('/'):
            vals['name'] = (self.env['ir.sequence'].next_by_code('repair.order') or '/') + vals['name']
            vals['name'] = vals['name'][:-1] if vals['name'].endswith('/') and vals['name'] != '/' else vals['name']
        return super(Repair, self).create(vals)

    def button_dummy(self):
        # TDE FIXME: this button is very interesting
        return True

    def action_repair_cancel_draft(self):
        if self.filtered(lambda repair: repair.state != 'cancel'):
            raise UserError(_("Repair must be canceled in order to reset it to draft."))
        self.mapped('operations').write({'state': 'draft'})
        return self.write({'state': 'draft', 'invoice_id': False})

    def action_validate(self):
        self.ensure_one()
        if self.filtered(lambda repair: any(op.product_uom_qty < 0 for op in repair.operations)):
            raise UserError(_("You can not enter negative quantities."))
        if self.product_id.type == 'consu':
            return self.action_repair_confirm()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        available_qty_owner = self.env['stock.quant']._get_available_quantity(self.product_id, self.location_id, self.lot_id, owner_id=self.partner_id, strict=True)
        available_qty_noown = self.env['stock.quant']._get_available_quantity(self.product_id, self.location_id, self.lot_id, strict=True)
        repair_qty = self.product_uom._compute_quantity(self.product_qty, self.product_id.uom_id)
        for available_qty in [available_qty_owner, available_qty_noown]:
            if float_compare(available_qty, repair_qty, precision_digits=precision) >= 0:
                return self.action_repair_confirm()
        else:
            return {
                'name': self.product_id.display_name + _(': Insufficient Quantity To Repair'),
                'view_mode': 'form',
                'res_model': 'stock.warn.insufficient.qty.repair',
                'view_id': self.env.ref('repair.stock_warn_insufficient_qty_repair_form_view').id,
                'type': 'ir.actions.act_window',
                'context': {
                    'default_product_id': self.product_id.id,
                    'default_location_id': self.location_id.id,
                    'default_repair_id': self.id,
                    'default_quantity': repair_qty,
                    'default_product_uom_name': self.product_id.uom_name
                },
                'target': 'new'
            }

    def action_repair_confirm(self):
        """ Repair order state is set to 'To be invoiced' when invoice method
        is 'Before repair' else state becomes 'Confirmed'.
        @param *arg: Arguments
        @return: True
        """
        if self.filtered(lambda repair: repair.state != 'draft'):
            raise UserError(_("Only draft repairs can be confirmed."))
        self._check_company()
        self.operations._check_company()
        self.fees_lines._check_company()
        before_repair = self.filtered(lambda repair: repair.invoice_method == 'b4repair')
        before_repair.write({'state': '2binvoiced'})
        to_confirm = self - before_repair
        to_confirm_operations = to_confirm.mapped('operations')
        to_confirm_operations.write({'state': 'confirmed'})
        to_confirm.write({'state': 'confirmed'})
        return True

    def action_repair_cancel(self):
        invoice_to_cancel = self.filtered(lambda repair: repair.invoice_id.state == 'draft').invoice_id
        if invoice_to_cancel:
            invoice_to_cancel.button_cancel()
        self.mapped('operations').write({'state': 'cancel'})
        return self.write({'state': 'cancel'})

    def action_send_mail(self):
        self.ensure_one()
        template_id = self.env.ref('repair.mail_template_repair_quotation').id
        ctx = {
            'default_model': 'repair.order',
            'default_res_id': self.id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'custom_layout': 'mail.mail_notification_light',
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'target': 'new',
            'context': ctx,
        }

    def print_repair_order(self):
        return self.env.ref('repair.action_report_repair_order').report_action(self)

    def action_repair_invoice_create(self):
        for repair in self:
            repair._create_invoices()
            if repair.invoice_method == 'b4repair':
                repair.action_repair_ready()
            elif repair.invoice_method == 'after_repair':
                repair.write({'state': 'done'})
        return True

    def _create_invoices(self, group=False):
        """ Creates invoice(s) for repair order.
        @param group: It is set to true when group invoice is to be generated.
        @return: Invoice Ids.
        """
        grouped_invoices_vals = {}
        repairs = self.filtered(lambda repair: repair.state not in ('draft', 'cancel')
                                               and not repair.invoice_id
                                               and repair.invoice_method != 'none')
        for repair in repairs:
            repair = repair.with_company(repair.company_id)
            partner_invoice = repair.partner_invoice_id or repair.partner_id
            if not partner_invoice:
                raise UserError(_('You have to select an invoice address in the repair form.'))

            narration = repair.quotation_notes
            currency = repair.pricelist_id.currency_id
            company = repair.env.company

            journal = repair.env['account.move'].with_context(move_type='out_invoice')._get_default_journal()
            if not journal:
                raise UserError(_('Please define an accounting sales journal for the company %s (%s).') % (company.name, company.id))

            if (partner_invoice.id, currency.id) not in grouped_invoices_vals:
                grouped_invoices_vals[(partner_invoice.id, currency.id, company.id)] = []
            current_invoices_list = grouped_invoices_vals[(partner_invoice.id, currency.id, company.id)]

            if not group or len(current_invoices_list) == 0:
                fpos = self.env['account.fiscal.position'].get_fiscal_position(partner_invoice.id, delivery_id=repair.address_id.id)
                invoice_vals = {
                    'move_type': 'out_invoice',
                    'partner_id': partner_invoice.id,
                    'partner_shipping_id': repair.address_id.id,
                    'currency_id': currency.id,
                    'narration': narration,
                    'line_ids': [],
                    'invoice_origin': repair.name,
                    'repair_ids': [(4, repair.id)],
                    'invoice_line_ids': [],
                    'fiscal_position_id': fpos.id
                }
                if partner_invoice.property_payment_term_id:
                    invoice_vals['invoice_payment_term_id'] = partner_invoice.property_payment_term_id.id
                current_invoices_list.append(invoice_vals)
            else:
                # if group == True: concatenate invoices by partner and currency
                invoice_vals = current_invoices_list[0]
                invoice_vals['invoice_origin'] += ', ' + repair.name
                invoice_vals['repair_ids'].append((4, repair.id))
                if not invoice_vals['narration']:
                    invoice_vals['narration'] = narration
                else:
                    invoice_vals['narration'] += '\n' + narration

            # Create invoice lines from operations.
            for operation in repair.operations.filtered(lambda op: op.type == 'add'):
                if group:
                    name = repair.name + '-' + operation.name
                else:
                    name = operation.name

                account = operation.product_id.product_tmpl_id._get_product_accounts()['income']
                if not account:
                    raise UserError(_('No account defined for product "%s".', operation.product_id.name))

                invoice_line_vals = {
                    'name': name,
                    'account_id': account.id,
                    'quantity': operation.product_uom_qty,
                    'tax_ids': [(6, 0, operation.tax_id.ids)],
                    'product_uom_id': operation.product_uom.id,
                    'price_unit': operation.price_unit,
                    'product_id': operation.product_id.id,
                    'repair_line_ids': [(4, operation.id)],
                }

                if currency == company.currency_id:
                    balance = -(operation.product_uom_qty * operation.price_unit)
                    invoice_line_vals.update({
                        'debit': balance > 0.0 and balance or 0.0,
                        'credit': balance < 0.0 and -balance or 0.0,
                    })
                else:
                    amount_currency = -(operation.product_uom_qty * operation.price_unit)
                    balance = currency._convert(amount_currency, company.currency_id, company, fields.Date.today())
                    invoice_line_vals.update({
                        'amount_currency': amount_currency,
                        'debit': balance > 0.0 and balance or 0.0,
                        'credit': balance < 0.0 and -balance or 0.0,
                        'currency_id': currency.id,
                    })
                invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

            # Create invoice lines from fees.
            for fee in repair.fees_lines:
                if group:
                    name = repair.name + '-' + fee.name
                else:
                    name = fee.name

                if not fee.product_id:
                    raise UserError(_('No product defined on fees.'))

                account = fee.product_id.product_tmpl_id._get_product_accounts()['income']
                if not account:
                    raise UserError(_('No account defined for product "%s".', fee.product_id.name))

                invoice_line_vals = {
                    'name': name,
                    'account_id': account.id,
                    'quantity': fee.product_uom_qty,
                    'tax_ids': [(6, 0, fee.tax_id.ids)],
                    'product_uom_id': fee.product_uom.id,
                    'price_unit': fee.price_unit,
                    'product_id': fee.product_id.id,
                    'repair_fee_ids': [(4, fee.id)],
                }

                if currency == company.currency_id:
                    balance = -(fee.product_uom_qty * fee.price_unit)
                    invoice_line_vals.update({
                        'debit': balance > 0.0 and balance or 0.0,
                        'credit': balance < 0.0 and -balance or 0.0,
                    })
                else:
                    amount_currency = -(fee.product_uom_qty * fee.price_unit)
                    balance = currency._convert(amount_currency, company.currency_id, company,
                                                fields.Date.today())
                    invoice_line_vals.update({
                        'amount_currency': amount_currency,
                        'debit': balance > 0.0 and balance or 0.0,
                        'credit': balance < 0.0 and -balance or 0.0,
                        'currency_id': currency.id,
                    })
                invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

        # Create invoices.
        invoices_vals_list_per_company = defaultdict(list)
        for (partner_invoice_id, currency_id, company_id), invoices in grouped_invoices_vals.items():
            for invoice in invoices:
                invoices_vals_list_per_company[company_id].append(invoice)

        for company_id, invoices_vals_list in invoices_vals_list_per_company.items():
            # VFE TODO remove the default_company_id ctxt key ?
            # Account fallbacks on self.env.company, which is correct with with_company
            self.env['account.move'].with_company(company_id).with_context(default_company_id=company_id, default_move_type='out_invoice').create(invoices_vals_list)

        repairs.write({'invoiced': True})
        repairs.mapped('operations').filtered(lambda op: op.type == 'add').write({'invoiced': True})
        repairs.mapped('fees_lines').write({'invoiced': True})

        return dict((repair.id, repair.invoice_id.id) for repair in repairs)

    def action_created_invoice(self):
        self.ensure_one()
        return {
            'name': _('Invoice created'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.move',
            'view_id': self.env.ref('account.view_move_form').id,
            'target': 'current',
            'res_id': self.invoice_id.id,
            }

    def action_repair_ready(self):
        self.mapped('operations').write({'state': 'confirmed'})
        return self.write({'state': 'ready'})

    def action_repair_start(self):
        """ Writes repair order state to 'Under Repair'
        @return: True
        """
        if self.filtered(lambda repair: repair.state not in ['confirmed', 'ready']):
            raise UserError(_("Repair must be confirmed before starting reparation."))
        self.mapped('operations').write({'state': 'confirmed'})
        return self.write({'state': 'under_repair'})

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
            if not repair.invoice_id and repair.invoice_method == 'after_repair':
                vals['state'] = '2binvoiced'
            repair.write(vals)
        return True

    def action_repair_done(self):
        """ Creates stock move for operation and stock move for final product of repair order.
        @return: Move ids of final products

        """
        if self.filtered(lambda repair: not repair.repaired):
            raise UserError(_("Repair must be repaired in order to make the product moves."))
        self._check_company()
        self.operations._check_company()
        self.fees_lines._check_company()
        res = {}
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        Move = self.env['stock.move']
        for repair in self:
            # Try to create move with the appropriate owner
            owner_id = False
            available_qty_owner = self.env['stock.quant']._get_available_quantity(repair.product_id, repair.location_id, repair.lot_id, owner_id=repair.partner_id, strict=True)
            if float_compare(available_qty_owner, repair.product_qty, precision_digits=precision) >= 0:
                owner_id = repair.partner_id.id

            moves = self.env['stock.move']
            for operation in repair.operations:
                move = Move.create({
                    'name': repair.name,
                    'product_id': operation.product_id.id,
                    'product_uom_qty': operation.product_uom_qty,
                    'product_uom': operation.product_uom.id,
                    'partner_id': repair.address_id.id,
                    'location_id': operation.location_id.id,
                    'location_dest_id': operation.location_dest_id.id,
                    'repair_id': repair.id,
                    'origin': repair.name,
                    'company_id': repair.company_id.id,
                })

                # Best effort to reserve the product in a (sub)-location where it is available
                product_qty = move.product_uom._compute_quantity(
                    operation.product_uom_qty, move.product_id.uom_id, rounding_method='HALF-UP')
                available_quantity = self.env['stock.quant']._get_available_quantity(
                    move.product_id,
                    move.location_id,
                    lot_id=operation.lot_id,
                    strict=False,
                )
                move._update_reserved_quantity(
                    product_qty,
                    available_quantity,
                    move.location_id,
                    lot_id=operation.lot_id,
                    strict=False,
                )
                # Then, set the quantity done. If the required quantity was not reserved, negative
                # quant is created in operation.location_id.
                move._set_quantity_done(operation.product_uom_qty)

                if operation.lot_id:
                    move.move_line_ids.lot_id = operation.lot_id

                moves |= move
                operation.write({'move_id': move.id, 'state': 'done'})
            move = Move.create({
                'name': repair.name,
                'product_id': repair.product_id.id,
                'product_uom': repair.product_uom.id or repair.product_id.uom_id.id,
                'product_uom_qty': repair.product_qty,
                'partner_id': repair.address_id.id,
                'location_id': repair.location_id.id,
                'location_dest_id': repair.location_id.id,
                'move_line_ids': [(0, 0, {'product_id': repair.product_id.id,
                                           'lot_id': repair.lot_id.id,
                                           'product_uom_qty': 0,  # bypass reservation here
                                           'product_uom_id': repair.product_uom.id or repair.product_id.uom_id.id,
                                           'qty_done': repair.product_qty,
                                           'package_id': False,
                                           'result_package_id': False,
                                           'owner_id': owner_id,
                                           'location_id': repair.location_id.id, #TODO: owner stuff
                                           'company_id': repair.company_id.id,
                                           'location_dest_id': repair.location_id.id,})],
                'repair_id': repair.id,
                'origin': repair.name,
                'company_id': repair.company_id.id,
            })
            consumed_lines = moves.mapped('move_line_ids')
            produced_lines = move.move_line_ids
            moves |= move
            moves._action_done()
            produced_lines.write({'consume_line_ids': [(6, 0, consumed_lines.ids)]})
            res[repair.id] = move.id
        return res


class RepairLine(models.Model):
    _name = 'repair.line'
    _description = 'Repair Line (parts)'

    name = fields.Text('Description', required=True)
    repair_id = fields.Many2one(
        'repair.order', 'Repair Order Reference', required=True,
        index=True, ondelete='cascade', check_company=True)
    company_id = fields.Many2one(
        related='repair_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(
        related='repair_id.currency_id')
    type = fields.Selection([
        ('add', 'Add'),
        ('remove', 'Remove')], 'Type', default='add', required=True)
    product_id = fields.Many2one(
        'product.product', 'Product', required=True, check_company=True,
        domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', company_id), ('company_id', '=', False)]")
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price')
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', store=True, digits=0)
    tax_id = fields.Many2many(
        'account.tax', 'repair_operation_line_tax', 'repair_operation_line_id', 'tax_id', 'Taxes',
        domain="[('type_tax_use','=','sale'), ('company_id', '=', company_id)]", check_company=True)
    product_uom_qty = fields.Float(
        'Quantity', default=1.0,
        digits='Product Unit of Measure', required=True)
    product_uom = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    invoice_line_id = fields.Many2one(
        'account.move.line', 'Invoice Line',
        copy=False, readonly=True, check_company=True)
    location_id = fields.Many2one(
        'stock.location', 'Source Location',
        index=True, required=True, check_company=True)
    location_dest_id = fields.Many2one(
        'stock.location', 'Dest. Location',
        index=True, required=True, check_company=True)
    move_id = fields.Many2one(
        'stock.move', 'Inventory Move',
        copy=False, readonly=True)
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial',
        domain="[('product_id','=', product_id), ('company_id', '=', company_id)]", check_company=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')], 'Status', default='draft',
        copy=False, readonly=True, required=True,
        help='The status of a repair line is set automatically to the one of the linked repair order.')

    @api.constrains('lot_id', 'product_id')
    def constrain_lot_id(self):
        for line in self.filtered(lambda x: x.product_id.tracking != 'none' and not x.lot_id):
            raise ValidationError(_("Serial number is required for operation line with product '%s'") % (line.product_id.name))

    @api.depends('price_unit', 'repair_id', 'product_uom_qty', 'product_id', 'repair_id.invoice_method')
    def _compute_price_subtotal(self):
        for line in self:
            taxes = line.tax_id.compute_all(line.price_unit, line.repair_id.pricelist_id.currency_id, line.product_uom_qty, line.product_id, line.repair_id.partner_id)
            line.price_subtotal = taxes['total_excluded']

    @api.onchange('type')
    def onchange_operation_type(self):
        """ On change of operation type it sets source location, destination location
        and to invoice field.
        @param product: Changed operation type.
        @param guarantee_limit: Guarantee limit of current record.
        @return: Dictionary of values.
        """
        if not self.type:
            self.location_id = False
            self.location_dest_id = False
        elif self.type == 'add':
            self.onchange_product_id()
            args = self.repair_id.company_id and [('company_id', '=', self.repair_id.company_id.id)] or []
            warehouse = self.env['stock.warehouse'].search(args, limit=1)
            self.location_id = warehouse.lot_stock_id
            self.location_dest_id = self.env['stock.location'].search([('usage', '=', 'production'), ('company_id', '=', self.repair_id.company_id.id)], limit=1)
        else:
            self.price_unit = 0.0
            self.tax_id = False
            self.location_id = self.env['stock.location'].search([('usage', '=', 'production')], limit=1).id
            self.location_dest_id = self.env['stock.location'].search([('scrap_location', '=', True), ('company_id', 'in', [self.repair_id.company_id.id, False])], limit=1).id

    @api.onchange('repair_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        """ On change of product it sets product quantity, tax account, name,
        uom of product, unit price and price subtotal. """
        if not self.product_id or not self.product_uom_qty:
            return
        self = self.with_company(self.company_id)
        partner = self.repair_id.partner_id
        partner_invoice = self.repair_id.partner_invoice_id or partner
        if partner:
            self = self.with_context(lang=partner.lang)
        product = self.product_id
        self.name = product.display_name
        if product.description_sale:
            if partner:
                self.name += '\n' + self.product_id.with_context(lang=partner.lang).description_sale
            else:
                self.name += '\n' + self.product_id.description_sale
        self.product_uom = product.uom_id.id
        if self.type != 'remove':
            if partner:
                fpos = self.env['account.fiscal.position'].get_fiscal_position(partner_invoice.id, delivery_id=self.repair_id.address_id.id)
                self.tax_id = fpos.map_tax(self.product_id.taxes_id, self.product_id, partner)
            warning = False
            pricelist = self.repair_id.pricelist_id
            if not pricelist:
                warning = {
                    'title': _('No pricelist found.'),
                    'message':
                        _('You have to select a pricelist in the Repair form !\n Please set one before choosing a product.')}
                return {'warning': warning}
            else:
                self._onchange_product_uom()

    @api.onchange('product_uom')
    def _onchange_product_uom(self):
        partner = self.repair_id.partner_id
        pricelist = self.repair_id.pricelist_id
        if pricelist and self.product_id and self.type != 'remove':
            price = pricelist.get_product_price(self.product_id, self.product_uom_qty, partner, uom_id=self.product_uom.id)
            if price is False:
                warning = {
                    'title': _('No valid pricelist line found.'),
                    'message':
                        _("Couldn't find a pricelist line matching this product and quantity.\nYou have to change either the product, the quantity or the pricelist.")}
                return {'warning': warning}
            else:
                self.price_unit = price


class RepairFee(models.Model):
    _name = 'repair.fee'
    _description = 'Repair Fees'

    repair_id = fields.Many2one(
        'repair.order', 'Repair Order Reference',
        index=True, ondelete='cascade', required=True)
    company_id = fields.Many2one(
        related="repair_id.company_id", index=True, store=True)
    currency_id = fields.Many2one(
        related="repair_id.currency_id")
    name = fields.Text('Description', index=True, required=True)
    product_id = fields.Many2one(
        'product.product', 'Product', check_company=True,
        domain="[('type', '=', 'service'), '|', ('company_id', '=', company_id), ('company_id', '=', False)]")
    product_uom_qty = fields.Float('Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price')
    product_uom = fields.Many2one('uom.uom', 'Product Unit of Measure', required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    price_subtotal = fields.Float('Subtotal', compute='_compute_price_subtotal', store=True, digits=0)
    tax_id = fields.Many2many(
        'account.tax', 'repair_fee_line_tax', 'repair_fee_line_id', 'tax_id', 'Taxes',
        domain="[('type_tax_use','=','sale'), ('company_id', '=', company_id)]", check_company=True)
    invoice_line_id = fields.Many2one('account.move.line', 'Invoice Line', copy=False, readonly=True, check_company=True)
    invoiced = fields.Boolean('Invoiced', copy=False, readonly=True)

    @api.depends('price_unit', 'repair_id', 'product_uom_qty', 'product_id')
    def _compute_price_subtotal(self):
        for fee in self:
            taxes = fee.tax_id.compute_all(fee.price_unit, fee.repair_id.pricelist_id.currency_id, fee.product_uom_qty, fee.product_id, fee.repair_id.partner_id)
            fee.price_subtotal = taxes['total_excluded']

    @api.onchange('repair_id', 'product_id', 'product_uom_qty')
    def onchange_product_id(self):
        """ On change of product it sets product quantity, tax account, name,
        uom of product, unit price and price subtotal. """
        if not self.product_id:
            return

        self = self.with_company(self.company_id)

        partner = self.repair_id.partner_id
        partner_invoice = self.repair_id.partner_invoice_id or partner
        pricelist = self.repair_id.pricelist_id

        if partner and self.product_id:
            fpos = self.env['account.fiscal.position'].get_fiscal_position(partner_invoice.id, delivery_id=self.repair_id.address_id.id)
            self.tax_id = fpos.map_tax(self.product_id.taxes_id, self.product_id, partner).ids
        if partner:
            self.name = self.product_id.with_context(lang=partner.lang).display_name
        else:
            self.name = self.product_id.display_name
        self.product_uom = self.product_id.uom_id.id
        if self.product_id.description_sale:
            if partner:
                self.name += '\n' + self.product_id.with_context(lang=partner.lang).description_sale
            else:
                self.name += '\n' + self.product_id.description_sale

        warning = False
        if not pricelist:
            warning = {
                'title': _('No pricelist found.'),
                'message':
                    _('You have to select a pricelist in the Repair form !\n Please set one before choosing a product.')}
            return {'warning': warning}
        else:
            self._onchange_product_uom()

    @api.onchange('product_uom')
    def _onchange_product_uom(self):
        partner = self.repair_id.partner_id
        pricelist = self.repair_id.pricelist_id
        if pricelist and self.product_id:
            price = pricelist.get_product_price(self.product_id, self.product_uom_qty, partner, uom_id=self.product_uom.id)
            if price is False:
                warning = {
                    'title': _('No valid pricelist line found.'),
                    'message':
                        _("Couldn't find a pricelist line matching this product and quantity.\nYou have to change either the product, the quantity or the pricelist.")}
                return {'warning': warning}
            else:
                self.price_unit = price


class RepairTags(models.Model):
    """ Tags of Repair's tasks """
    _name = "repair.tags"
    _description = "Repair Tags"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Tag Name', required=True)
    color = fields.Integer(string='Color Index', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]
