# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4
from markupsafe import Markup

from odoo import api, Command, fields, models, _
from odoo.tools import float_is_zero
from odoo.exceptions import UserError


class PosOrderLine(models.Model):
    _name = 'pos.order.line'
    _description = "Point of Sale Order Line"
    _rec_name = 'product_id'
    _inherit = ['pos.load.mixin']

    company_id = fields.Many2one('res.company', string='Company', related='order_id.company_id', store=True)
    name = fields.Char(string='Line No', required=True, copy=False)
    notice = fields.Char(string='Discount Notice')
    product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], required=True)
    attribute_value_ids = fields.Many2many('product.template.attribute.value', string="Selected Attributes")
    custom_attribute_value_ids = fields.One2many(
        comodel_name='product.attribute.custom.value', inverse_name='pos_order_line_id',
        string="Custom Values",
        store=True, readonly=False)
    price_unit = fields.Float(string='Unit Price', digits=0)
    qty = fields.Float('Quantity', digits='Product Unit', default=1)
    price_subtotal = fields.Monetary(string='Tax Excl.',
        readonly=True, required=True)
    price_subtotal_incl = fields.Monetary(string='Tax Incl.',
        readonly=True, required=True)
    price_extra = fields.Float(string="Price extra")
    price_type = fields.Selection([
        ('original', 'Original'),
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
    ], string='Price Type', default='original')
    margin = fields.Monetary(string="Margin", compute='_compute_margin')
    margin_percent = fields.Float(string="Margin (%)", compute='_compute_margin', digits=(12, 4))
    total_cost = fields.Float(string='Total cost', min_display_digits='Product Price', readonly=True)
    is_total_cost_computed = fields.Boolean(help="Allows to know if the total cost has already been computed or not")
    discount = fields.Float(string='Discount (%)', digits=0)
    order_id = fields.Many2one('pos.order', string='Order Ref', ondelete='cascade', required=True, index=True)
    tax_ids = fields.Many2many('account.tax', string='Taxes', readonly=True)
    tax_ids_after_fiscal_position = fields.Many2many('account.tax', compute='_get_tax_ids_after_fiscal_position', string='Taxes to Apply')
    product_uom_id = fields.Many2one('uom.uom', string='Product Unit', related='product_id.uom_id')
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id')
    full_product_name = fields.Char('Full Product Name')
    customer_note = fields.Char('Customer Note')
    refund_orderline_ids = fields.One2many('pos.order.line', 'refunded_orderline_id', 'Refund Order Lines', help='Orderlines in this field are the lines that refunded this orderline.')
    refunded_orderline_id = fields.Many2one('pos.order.line', 'Refunded Order Line', index='btree_not_null', help='If this orderline is a refund, then the refunded orderline is specified in this field.')
    refunded_qty = fields.Float('Refunded Quantity', compute='_compute_refund_qty', help='Number of items refunded in this orderline.')
    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)
    note = fields.Char('Product Note')

    combo_parent_id = fields.Many2one('pos.order.line', string='Combo Parent', index='btree_not_null')  # FIXME rename to parent_line_id
    combo_line_ids = fields.One2many('pos.order.line', 'combo_parent_id', string='Combo Lines')  # FIXME rename to child_line_ids

    combo_item_id = fields.Many2one('product.combo.item', string='Combo Item')
    is_edited = fields.Boolean('Edited')
    # Technical field holding custom data for the taxes computation engine.
    extra_tax_data = fields.Json()

    _unique_uuid = models.Constraint('unique (uuid)', 'An order line with this uuid already exists')

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('order_id', 'in', [order['id'] for order in data['pos.order']])]

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            'qty', 'attribute_value_ids', 'custom_attribute_value_ids', 'price_unit',
            'uuid', 'price_subtotal', 'price_subtotal_incl', 'order_id', 'note', 'price_type',
            'product_id', 'discount', 'tax_ids', 'customer_note',
            'refunded_qty', 'price_extra', 'full_product_name', 'refunded_orderline_id',
            'combo_parent_id', 'combo_line_ids', 'combo_item_id', 'refund_orderline_ids',
            'extra_tax_data', 'write_date',
        ]

    @api.depends('refund_orderline_ids', 'refund_orderline_ids.order_id.state')
    def _compute_refund_qty(self):
        for orderline in self:
            refund_order_line = orderline.refund_orderline_ids.filtered(lambda l: l.order_id.state != 'cancel')
            orderline.refunded_qty = -sum(refund_order_line.mapped('qty'))

    def _prepare_refund_data(self, refund_order, PosPackOperationLot=False):
        """
        This prepares data for refund order line. Inheritance may inject more data here

        @param refund_order: the pre-created refund order
        @type refund_order: pos.order

        @param PosPackOperationLot: the pre-created Pack operation Lot
        @type PosPackOperationLot: pos.pack.operation.lot

        @return: dictionary of data which is for creating a refund order line from the original line
        @rtype: dict
        """
        self.ensure_one()
        return {
            'name': _('%(name)s REFUND', name=self.name),
            'qty': -(self.qty - self.refunded_qty),
            'order_id': refund_order.id,
            'is_total_cost_computed': False,
            'refunded_orderline_id': self.id,
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            order = self.env['pos.order'].browse(vals['order_id']) if vals.get('order_id') else False
            if order and order.exists() and not vals.get('name'):
                # set name based on the sequence specified on the config
                config = order.session_id.config_id
                if config.order_line_seq_id:
                    vals['name'] = config.order_line_seq_id._next()
            if not vals.get('name'):
                # fallback on any pos.order sequence
                vals['name'] = self.env['ir.sequence'].next_by_code('pos.order.line')
        return super().create(vals_list)

    def write(self, vals):
        if self.order_id.config_id.order_edit_tracking and vals.get('qty') is not None and vals.get('qty') < self.qty:
            self.is_edited = True
            body = _("%(product_name)s: Ordered quantity: %(old_qty)s", product_name=self.full_product_name, old_qty=self.qty)
            body += Markup("&rarr;") + str(vals.get('qty'))
            for line in self:
                line.order_id.message_post(body=line.order_id._prepare_pos_log(body))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_order_state(self):
        if self.filtered(lambda x: x.order_id.state not in ["draft", "cancel"]):
            raise UserError(_("You can only unlink PoS order lines that are related to orders in new or cancelled state."))
        for line in self.filtered(lambda l: l.order_id.config_id.order_edit_tracking):
            line.order_id.has_deleted_line = True
            body = _("%(product_name)s: Deleted line (quantity: %(qty)s)", product_name=line.full_product_name, qty=line.qty)
            line.order_id.message_post(body=line.order_id._prepare_pos_log(body))

    @api.onchange('price_unit', 'tax_ids', 'qty', 'discount', 'product_id')
    def _onchange_amount_line_all(self):
        for line in self:
            res = line._compute_amount_line_all()
            line.update(res)

    def _compute_amount_line_all(self, qty=None):
        self.ensure_one()
        fpos = self.order_id.fiscal_position_id
        tax_ids_after_fiscal_position = fpos.map_tax(self.tax_ids)
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        line_qty = qty or self.qty
        taxes = tax_ids_after_fiscal_position.compute_all(price, self.order_id.currency_id, line_qty, product=self.product_id, partner=self.order_id.partner_id)
        return {
            'price_subtotal_incl': taxes['total_included'],
            'price_subtotal': taxes['total_excluded'],
        }

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            price = self.order_id.pricelist_id._get_product_price(
                self.product_id, self.qty or 1.0, currency=self.currency_id
            )
            self.tax_ids = self.product_id.taxes_id.filtered_domain(self.env['account.tax']._check_company_domain(self.company_id))
            tax_ids_after_fiscal_position = self.order_id.fiscal_position_id.map_tax(self.tax_ids)
            self.price_unit = self.env['account.tax']._fix_tax_included_price_company(price, self.tax_ids, tax_ids_after_fiscal_position, self.company_id)
            self._onchange_qty()

    @api.onchange('qty', 'discount', 'price_unit', 'tax_ids')
    def _onchange_qty(self):
        if self.product_id:
            price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
            self.price_subtotal = self.price_subtotal_incl = price * self.qty
            if (self.tax_ids):
                taxes = self.tax_ids.compute_all(price, self.order_id.currency_id, self.qty, product=self.product_id, partner=False)
                self.price_subtotal = taxes['total_excluded']
                self.price_subtotal_incl = taxes['total_included']

    @api.depends('order_id', 'order_id.fiscal_position_id', 'tax_ids')
    def _get_tax_ids_after_fiscal_position(self):
        for line in self:
            line.tax_ids_after_fiscal_position = line.order_id.fiscal_position_id.map_tax(line.tax_ids)

    def _prepare_reference_vals(self):
        return {
            'name': self.order_id.name,
            'pos_order_ids': [Command.link(self.order_id.id)],
        }

    def _compute_total_cost(self, stock_moves=False):
        """
        Compute the total cost of the order lines.
        :param stock_moves: recordset of `stock.move`, used for fifo/avco lines
        """
        for line in self.filtered(lambda l: not l.is_total_cost_computed):
            product = line.product_id
            cost_currency = product.sudo().cost_currency_id
            product_cost = product.standard_price
            line.total_cost = line.qty * cost_currency._convert(
                from_amount=product_cost,
                to_currency=line.currency_id,
                company=line.company_id or self.env.company,
                date=line.order_id.date_order or fields.Date.today(),
                round=False,
            )
            line.is_total_cost_computed = True

    @api.depends('price_subtotal', 'total_cost')
    def _compute_margin(self):
        for line in self:
            sign = -1 if line.order_id.is_refund else 1
            if line.product_id.type == 'combo':
                line.margin = 0
                line.margin_percent = 0
            else:
                line.margin = (line.price_subtotal * sign) - line.total_cost
                line.margin_percent = not float_is_zero(line.price_subtotal, precision_rounding=line.currency_id.rounding) \
                                        and line.margin / (line.price_subtotal * sign) \
                                        or 0

    def _prepare_base_line_for_taxes_computation(self):
        self.ensure_one()
        commercial_partner = self.order_id.partner_id.commercial_partner_id
        fiscal_position = self.order_id.fiscal_position_id
        line = self.with_company(self.order_id.company_id)
        account = line.product_id._get_product_accounts()['income'] or self.order_id.config_id.journal_id.default_account_id
        if not account:
            raise UserError(_(
                "Please define income account for this product: '%(product)s' (id:%(id)d).",
                product=line.product_id.name, id=line.product_id.id,
            ))

        if fiscal_position:
            account = fiscal_position.map_account(account)

        is_refund_order = line.order_id.amount_total < 0.0
        is_refund_line = line.qty * line.price_unit < 0

        lang = line.order_id.partner_id.lang or self.env.user.lang
        product_name = line.with_context(lang=lang).full_product_name or line.product_id.with_context(lang=lang).display_name
        if line.product_id.description_sale:
            product_name += '\n' + line.product_id.with_context(lang=lang).description_sale
        return {
            **self.env['account.tax']._prepare_base_line_for_taxes_computation(
                line,
                partner_id=commercial_partner,
                currency_id=self.order_id.currency_id,
                rate=self.order_id.currency_rate,
                product_id=line.product_id,
                tax_ids=line.tax_ids_after_fiscal_position,
                price_unit=line.price_unit,
                quantity=line.qty * (-1 if is_refund_order else 1),
                discount=line.discount,
                account_id=account,
                is_refund=is_refund_line,
                sign=1 if is_refund_order else -1,
            ),
            'uom_id': line.product_uom_id,
            'name': product_name,
        }

    def _prepare_tax_base_line_values(self):
        """
        Convert pos order lines into dictionaries that would be used to compute taxes later.
        :return: A list of python dictionaries (see '_prepare_base_line_for_taxes_computation' in account.tax).
        """
        return [line._prepare_base_line_for_taxes_computation() for line in self]

    def _get_discount_amount(self):
        self.ensure_one()
        original_price = self.tax_ids.compute_all(self.price_unit, self.currency_id, self.qty, product=self.product_id, partner=self.order_id.partner_id)['total_included']
        return original_price - self.price_subtotal_incl

    def _compute_qty_available(self):
        for line in self:
            if line.product_id.is_storable:
                line.product_id.qty_available -= line.qty
