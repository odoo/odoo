# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict


class PurchaseRequisition(models.Model):
    _name = 'purchase.requisition'
    _description = "Purchase Requisition"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    name = fields.Char(
        string='Agreement', copy=False, readonly=True, required=True,
        default=lambda self: _('New'))
    active = fields.Boolean('Active', default=True)
    reference = fields.Char(string='Reference')
    order_count = fields.Integer(compute='_compute_orders_number', string='Number of Orders')
    vendor_id = fields.Many2one('res.partner', string='Vendor', check_company=True)
    requisition_type = fields.Selection([
        ('blanket_order', 'Blanket Order'), ('purchase_template', 'Purchase Template')],
         string='Agreement Type', required=True, default='blanket_order')
    date_start = fields.Date(string='Start Date', tracking=True)
    date_end = fields.Date(string='End Date', tracking=True)
    user_id = fields.Many2one(
        'res.users', string='Purchase Representative',
        default=lambda self: self.env.user, check_company=True)
    description = fields.Html()
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    purchase_ids = fields.One2many('purchase.order', 'requisition_id', string='Purchase Orders')
    line_ids = fields.One2many('purchase.requisition.line', 'requisition_id', string='Products to Purchase', copy=True)
    product_id = fields.Many2one('product.product', related='line_ids.product_id', string='Product')
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('done', 'Closed'),
            ('cancel', 'Cancelled')
        ],
        string='Status', tracking=True, required=True,
        copy=False, default='draft')
    currency_id = fields.Many2one(
        'res.currency', 'Currency', required=True, precompute=True,
        compute='_compute_currency_id', store=True, readonly=False)

    @api.onchange('vendor_id')
    def _onchange_vendor(self):
        requisitions = self.env['purchase.requisition'].search([
            ('vendor_id', '=', self.vendor_id.id),
            ('state', '=', 'confirmed'),
            ('requisition_type', '=', 'blanket_order'),
            ('company_id', '=', self.company_id.id),
        ])
        if any(requisitions):
            title = _("Warning for %s", self.vendor_id.name)
            message = _("There is already an open blanket order for this supplier. We suggest you complete this open blanket order, instead of creating a new one.")
            warning = {
                'title': title,
                'message': message
            }
            return {'warning': warning}

    @api.depends('vendor_id')
    def _compute_currency_id(self):
        for requisition in self:
            if not requisition.vendor_id or not requisition.vendor_id.property_purchase_currency_id:
                requisition.currency_id = requisition.company_id.currency_id.id
            else:
                requisition.currency_id = requisition.vendor_id.property_purchase_currency_id.id

    @api.depends('purchase_ids')
    def _compute_orders_number(self):
        for requisition in self:
            requisition.order_count = len(requisition.purchase_ids)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        invalid_requsitions = self.filtered(lambda r: r.date_end and r.date_start and r.date_end < r.date_start)
        if invalid_requsitions:
            raise ValidationError(_(
                "End date cannot be earlier than start date. Please check dates for agreements: %s", ', '.join(invalid_requsitions.mapped('name'))
            ))

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(['requisition_type', 'company_id'])
        for vals in vals_list:
            requisition_type = vals.get('requisition_type', defaults['requisition_type'])
            company_id = vals.get('company_id', defaults['company_id'])
            if requisition_type == 'blanket_order':
                vals['name'] = self.env['ir.sequence'].with_company(company_id).next_by_code('purchase.requisition.blanket.order')
            else:
                vals['name'] = self.env['ir.sequence'].with_company(company_id).next_by_code('purchase.requisition.purchase.template')
        return super().create(vals_list)

    def write(self, vals):
        requisitions_to_rename = self.env['purchase.requisition']
        if 'requisition_type' in vals or 'company_id' in vals:
            requisitions_to_rename = self.filtered(lambda r:
                r.requisition_type != vals.get('requisition_type', r.requisition_type) or
                r.company_id.id != vals.get('company_id', r.company_id.id))
        res = super().write(vals)
        for requisition in requisitions_to_rename:
            if requisition.state != 'draft':
                raise UserError(_("You cannot change the Agreement Type or Company of a not draft purchase agreement."))
            if requisition.requisition_type == 'purchase_template':
                requisition.date_start = requisition.date_end = False
            code = requisition.requisition_type == 'blanket_order' and 'purchase.requisition.blanket.order' or 'purchase.requisition.purchase.template'
            requisition.name = self.env['ir.sequence'].with_company(requisition.company_id).next_by_code(code)
        return res

    def unlink(self):
        # Draft requisitions could have some requisition lines.
        self.line_ids.unlink()
        return super().unlink()

    def action_cancel(self):
        # try to set all associated quotations to cancel state
        for requisition in self:
            for requisition_line in requisition.line_ids:
                requisition_line.supplier_info_ids.sudo().unlink()
            requisition.purchase_ids.button_cancel()
            for po in requisition.purchase_ids:
                po.message_post(body=_('Cancelled by the agreement associated to this quotation.'))
        self.state = 'cancel'

    def action_confirm(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("You cannot confirm agreement '%(agreement)s' because it does not contain any product lines.", agreement=self.name))
        if self.requisition_type == 'blanket_order':
            for requisition_line in self.line_ids:
                if requisition_line.price_unit <= 0.0:
                    raise UserError(_('You cannot confirm a blanket order with lines missing a price.'))
                if requisition_line.product_qty <= 0.0:
                    raise UserError(_('You cannot confirm a blanket order with lines missing a quantity.'))
                requisition_line._create_supplier_info()
        self.state = 'confirmed'

    def action_draft(self):
        self.ensure_one()
        self.state = 'draft'

    def action_done(self):
        """
        Generate all purchase order based on selected lines, should only be called on one agreement at a time
        """
        if any(purchase_order.state in ['draft', 'sent', 'to approve'] for purchase_order in self.mapped('purchase_ids')):
            raise UserError(_("To close this purchase requisition, cancel related Requests for Quotation.\n\n"
                "Imagine the mess if someone confirms these duplicates: double the order, double the trouble :)"))
        for requisition in self:
            for requisition_line in requisition.line_ids:
                requisition_line.supplier_info_ids.sudo().unlink()
        self.write({'state': 'done'})

    @api.ondelete(at_uninstall=False)
    def _unlink_if_draft_or_cancel(self):
        if any(requisition.state not in ('draft', 'cancel') for requisition in self):
            raise UserError(_('You can only delete draft or cancelled requisitions.'))


class PurchaseRequisitionLine(models.Model):
    _name = 'purchase.requisition.line'
    _inherit = ['analytic.mixin']
    _description = "Purchase Requisition Line"
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        compute='_compute_product_uom_id', store=True, readonly=False, precompute=True)
    product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure')
    product_description_variants = fields.Char('Description')
    price_unit = fields.Float(
        string='Unit Price', digits='Product Price', default=0.0,
        compute="_compute_price_unit", readonly=False, store=True)
    qty_ordered = fields.Float(compute='_compute_ordered_qty', string='Ordered')
    requisition_id = fields.Many2one('purchase.requisition', required=True, string='Purchase Agreement', ondelete='cascade')
    company_id = fields.Many2one('res.company', related='requisition_id.company_id', string='Company', store=True, readonly=True)
    supplier_info_ids = fields.One2many('product.supplierinfo', 'purchase_requisition_line_id')

    @api.depends('requisition_id.purchase_ids.state')
    def _compute_ordered_qty(self):
        line_found = defaultdict(set)
        for line in self:
            total = 0.0
            for po in line.requisition_id.purchase_ids.filtered(lambda purchase_order: purchase_order.state in ['purchase', 'done']):
                for po_line in po.order_line.filtered(lambda order_line: order_line.product_id == line.product_id):
                    if po_line.product_uom_id != line.product_uom_id:
                        total += po_line.product_uom_id._compute_quantity(po_line.product_qty, line.product_uom_id)
                    else:
                        total += po_line.product_qty
            if line.product_id not in line_found[line.requisition_id]:
                line.qty_ordered = total
                line_found[line.requisition_id].add(line.product_id)
            else:
                line.qty_ordered = 0

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for line in self:
            line.product_uom_id = line.product_id.uom_id

    @api.depends('product_id', 'company_id', 'requisition_id.date_start', 'product_qty', 'product_uom_id', 'requisition_id.vendor_id', 'requisition_id.requisition_type')
    def _compute_price_unit(self):
        for line in self:
            if line.requisition_id.state != 'draft' or line.requisition_id.requisition_type != 'purchase_template' or not line.requisition_id.vendor_id or not line.product_id:
                continue
            seller = line.product_id._select_seller(
                partner_id=line.requisition_id.vendor_id, quantity=line.product_qty,
                date=line.requisition_id.date_start, uom_id=line.product_uom_id)
            line.price_unit = seller.price if seller else line.product_id.standard_price

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line, vals in zip(lines, vals_list):
            if line.requisition_id.requisition_type == 'blanket_order' and line.requisition_id.state not in ['draft', 'cancel', 'done']:
                if vals['price_unit'] <= 0.0:
                    raise UserError(_("You cannot have a negative or unit price of 0 for an already confirmed blanket order."))
                supplier_infos = self.env['product.supplierinfo'].search([
                    ('product_id', '=', vals.get('product_id')),
                    ('partner_id', '=', line.requisition_id.vendor_id.id),
                ])
                if not any(s.purchase_requisition_id for s in supplier_infos):
                    line._create_supplier_info()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if 'price_unit' not in vals:
            return res
        if vals['price_unit'] <= 0.0 and any(
                requisition.requisition_type == 'blanket_order' and
                requisition.state not in ['draft', 'cancel', 'done'] for requisition in self.mapped('requisition_id')):
            raise UserError(_("You cannot have a negative or unit price of 0 for an already confirmed blanket order."))
        # If the price is updated, we have to update the related SupplierInfo
        self.supplier_info_ids.write({'price': vals['price_unit']})
        return res

    def unlink(self):
        to_unlink = self.filtered(lambda r: r.requisition_id.state not in ['draft', 'cancel', 'done'])
        to_unlink.supplier_info_ids.unlink()
        return super().unlink()

    def _create_supplier_info(self):
        self.ensure_one()
        purchase_requisition = self.requisition_id
        if purchase_requisition.requisition_type == 'blanket_order' and purchase_requisition.vendor_id:
            # create a supplier_info only in case of blanket order
            self.env['product.supplierinfo'].sudo().create({
                'partner_id': purchase_requisition.vendor_id.id,
                'product_id': self.product_id.id,
                'product_tmpl_id': self.product_id.product_tmpl_id.id,
                'price': self.price_unit,
                'currency_id': self.requisition_id.currency_id.id,
                'purchase_requisition_line_id': self.id,
            })

    def _prepare_purchase_order_line(self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False):
        self.ensure_one()
        if self.product_description_variants:
            name += '\n' + self.product_description_variants
        date_planned = fields.Datetime.now()
        if self.requisition_id.date_start:
            date_planned = max(date_planned, fields.Datetime.to_datetime(self.requisition_id.date_start))
        return {
            'name': name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_id.uom_po_id.id,
            'product_qty': product_qty,
            'price_unit': price_unit,
            'taxes_id': [(6, 0, taxes_ids)],
            'date_planned': date_planned,
            'analytic_distribution': self.analytic_distribution,
        }
