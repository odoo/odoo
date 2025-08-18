# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from pytz import UTC

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, get_lang
from odoo.tools.float_utils import float_compare, float_round
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _name = 'purchase.order.line'
    _inherit = ['analytic.mixin']
    _description = 'Purchase Order Line'
    _order = 'order_id, sequence, id'

    name = fields.Text(
        string='Description', required=True, compute='_compute_price_unit_and_date_planned_and_name', store=True, readonly=False)
    sequence = fields.Integer(string='Sequence', default=10)
    product_qty = fields.Float(string='Quantity', digits='Product Unit', required=True)
    product_uom_qty = fields.Float(string='Total Quantity', compute='_compute_product_uom_qty', store=True)
    date_planned = fields.Datetime(
        string='Expected Arrival', index=True,
        compute="_compute_price_unit_and_date_planned_and_name", readonly=False, store=True,
        help="Delivery date expected from vendor. This date respectively defaults to vendor pricelist lead time then today's date.")
    discount = fields.Float(
        string="Discount (%)",
        compute='_compute_price_unit_and_date_planned_and_name',
        digits='Discount',
        store=True, readonly=False)
    tax_ids = fields.Many2many('account.tax', string='Taxes', context={'active_test': False})
    allowed_uom_ids = fields.Many2many('uom.uom', compute='_compute_allowed_uom_ids')
    product_uom_id = fields.Many2one('uom.uom', string='Unit', domain="[('id', 'in', allowed_uom_ids)]")
    product_id = fields.Many2one('product.product', string='Product', domain=[('purchase_ok', '=', True)], change_default=True, index='btree_not_null', ondelete='restrict')
    product_type = fields.Selection(related='product_id.type', readonly=True)
    price_unit = fields.Float(
        string='Unit Price', required=True, digits='Product Price', aggregator='avg',
        compute="_compute_price_unit_and_date_planned_and_name", readonly=False, store=True)
    price_unit_discounted = fields.Float('Unit Price (Discounted)', compute='_compute_price_unit_discounted')

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)

    order_id = fields.Many2one('purchase.order', string='Order Reference', index=True, required=True, ondelete='cascade')

    company_id = fields.Many2one('res.company', related='order_id.company_id', string='Company', store=True, readonly=True)
    state = fields.Selection(related='order_id.state')

    invoice_lines = fields.One2many('account.move.line', 'purchase_line_id', string="Bill Lines", readonly=True, copy=False)

    # Replace by invoiced Qty
    qty_invoiced = fields.Float(compute='_compute_qty_invoiced', string="Billed Qty", digits='Product Unit', store=True)

    qty_received_method = fields.Selection([('manual', 'Manual')], string="Received Qty Method", compute='_compute_qty_received_method', store=True,
        help="According to product configuration, the received quantity can be automatically computed by mechanism:\n"
             "  - Manual: the quantity is set manually on the line\n"
             "  - Stock Moves: the quantity comes from confirmed pickings\n")
    qty_received = fields.Float("Received Qty", compute='_compute_qty_received', inverse='_inverse_qty_received', compute_sudo=True, store=True, digits='Product Unit')
    qty_received_manual = fields.Float("Manual Received Qty", digits='Product Unit', copy=False)
    qty_to_invoice = fields.Float(compute='_compute_qty_invoiced', string='To Invoice Quantity', store=True, readonly=True,
                                  digits='Product Unit')

    partner_id = fields.Many2one('res.partner', related='order_id.partner_id', string='Partner', readonly=True, store=True, index='btree_not_null')
    currency_id = fields.Many2one(related='order_id.currency_id', string='Currency')
    date_order = fields.Datetime(related='order_id.date_order', string='Order Date', readonly=True)
    date_approve = fields.Datetime(related="order_id.date_approve", string='Confirmation Date', readonly=True)
    tax_calculation_rounding_method = fields.Selection(
        related='company_id.tax_calculation_rounding_method',
        string='Tax calculation rounding method', readonly=True)
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_subsection', "Subsection"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")
    is_downpayment = fields.Boolean()
    selected_seller_id = fields.Many2one('product.supplierinfo', compute='_compute_selected_seller_id', help='Technical field to get the vendor pricelist used to generate this line')

    _accountable_required_fields = models.Constraint(
        'CHECK(display_type IS NOT NULL OR is_downpayment OR (product_id IS NOT NULL AND product_uom_id IS NOT NULL AND date_planned IS NOT NULL))',
        'Missing required fields on accountable purchase order line.',
    )
    _non_accountable_null_fields = models.Constraint(
        'CHECK(display_type IS NULL OR (product_id IS NULL AND price_unit = 0 AND product_uom_qty = 0 AND product_uom_id IS NULL AND date_planned is NULL))',
        'Forbidden values on non-accountable purchase order line',
    )
    product_template_attribute_value_ids = fields.Many2many(related='product_id.product_template_attribute_value_ids', readonly=True)
    product_no_variant_attribute_value_ids = fields.Many2many('product.template.attribute.value', string='Product attribute values that do not create variants', ondelete='restrict')
    purchase_line_warn_msg = fields.Text(related='product_id.purchase_line_warn_msg')
    section_line_id = fields.Many2one(
        comodel_name='purchase.order.line',
        compute='_compute_section_line_id',
        store=True,
    )

    @api.depends('product_qty', 'price_unit', 'tax_ids', 'discount')
    def _compute_amount(self):
        AccountTax = self.env['account.tax']
        for line in self:
            company = line.company_id or self.env.company
            base_line = line._prepare_base_line_for_taxes_computation()
            AccountTax._add_tax_details_in_base_line(base_line, company)
            AccountTax._round_base_lines_tax_details([base_line], company)
            line.price_subtotal = base_line['tax_details']['total_excluded_currency']
            line.price_total = base_line['tax_details']['total_included_currency']
            line.price_tax = line.price_total - line.price_subtotal

    def _prepare_base_line_for_taxes_computation(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        company = self.order_id.company_id or self.env.company
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            tax_ids=self.tax_ids,
            quantity=self.product_qty,
            partner_id=self.order_id.partner_id,
            currency_id=self.order_id.currency_id or company.currency_id,
            rate=self.order_id.currency_rate,
        )

    def _compute_tax_id(self):
        for line in self:
            line = line.with_company(line.company_id)
            fpos = line.order_id.fiscal_position_id or line.order_id.fiscal_position_id._get_fiscal_position(line.order_id.partner_id)
            # filter taxes by company
            taxes = line.product_id.supplier_taxes_id._filter_taxes_by_company(line.company_id)
            line.tax_ids = fpos.map_tax(taxes)

    @api.depends('discount', 'price_unit')
    def _compute_price_unit_discounted(self):
        for line in self:
            line.price_unit_discounted = line.price_unit * (1 - line.discount / 100)

    @api.depends('invoice_lines.move_id.state', 'invoice_lines.quantity', 'qty_received', 'product_uom_qty', 'order_id.state')
    def _compute_qty_invoiced(self):
        for line in self:
            # compute qty_invoiced
            qty = 0.0
            for inv_line in line._get_invoice_lines():
                if inv_line.move_id.state not in ['cancel'] or inv_line.move_id.payment_state == 'invoicing_legacy':
                    if inv_line.move_id.move_type == 'in_invoice':
                        qty += inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom_id)
                    elif inv_line.move_id.move_type == 'in_refund':
                        qty -= inv_line.product_uom_id._compute_quantity(inv_line.quantity, line.product_uom_id)
            line.qty_invoiced = qty

            # compute qty_to_invoice
            if line.order_id.state == 'purchase':
                if line.product_id.purchase_method == 'purchase':
                    line.qty_to_invoice = line.product_qty - line.qty_invoiced
                else:
                    line.qty_to_invoice = line.qty_received - line.qty_invoiced
            else:
                line.qty_to_invoice = 0

    def _get_invoice_lines(self):
        self.ensure_one()
        if self.env.context.get('accrual_entry_date'):
            return self.invoice_lines.filtered(
                lambda l: l.move_id.invoice_date and l.move_id.invoice_date <= self.env.context['accrual_entry_date']
            )
        else:
            return self.invoice_lines

    @api.depends('product_id', 'product_id.type')
    def _compute_qty_received_method(self):
        for line in self:
            if line.product_id and line.product_id.type in ['consu', 'service']:
                line.qty_received_method = 'manual'
            else:
                line.qty_received_method = False

    @api.depends('qty_received_method', 'qty_received_manual')
    def _compute_qty_received(self):
        for line in self:
            if line.qty_received_method == 'manual':
                line.qty_received = line.qty_received_manual or 0.0
            else:
                line.qty_received = 0.0

    @api.onchange('qty_received')
    def _inverse_qty_received(self):
        """ When writing on qty_received, if the value should be modify manually (`qty_received_method` = 'manual' only),
            then we put the value in `qty_received_manual`. Otherwise, `qty_received_manual` should be False since the
            received qty is automatically compute by other mecanisms.
        """
        for line in self:
            if line.qty_received_method == 'manual':
                line.qty_received_manual = line.qty_received
            else:
                line.qty_received_manual = 0.0

    @api.depends('product_id', 'product_id.seller_ids', 'partner_id', 'product_qty', 'order_id.date_order', 'product_uom_id')
    def _compute_selected_seller_id(self):
        for line in self:
            if line.product_id:
                params = line._get_select_sellers_params()
                seller = line.product_id._select_seller(
                    partner_id=line.partner_id,
                    quantity=abs(line.product_qty),
                    date=line.order_id.date_order and line.order_id.date_order.date() or fields.Date.context_today(line),
                    uom_id=line.product_uom_id,
                    params=params)
                line.selected_seller_id = seller.id if seller else False
            else:
                line.selected_seller_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('display_type', self.default_get(['display_type'])['display_type']):
                values.update(product_id=False, price_unit=0, product_uom_qty=0, product_uom_id=False, date_planned=False)
            else:
                values.update(self._prepare_add_missing_fields(values))

        lines = super().create(vals_list)
        for line in lines:
            if line.product_id and line.order_id.state == 'purchase':
                msg = _("Extra line with %s ", line.product_id.display_name)
                line.order_id.message_post(body=msg)
        return lines

    def write(self, vals):
        values = vals
        if 'display_type' in values and self.filtered(lambda line: line.display_type != values.get('display_type')):
            raise UserError(_("You cannot change the type of a purchase order line. Instead you should delete the current line and create a new line of the proper type."))

        if 'product_qty' in values:
            precision = self.env['decimal.precision'].precision_get('Product Unit')
            for line in self:
                if (
                    line.order_id.state == "purchase"
                    and float_compare(line.product_qty, values["product_qty"], precision_digits=precision) != 0
                ):
                    line.order_id.message_post_with_source(
                        'purchase.track_po_line_template',
                        render_values={'line': line, 'product_qty': values['product_qty']},
                        subtype_xmlid='mail.mt_note',
                    )

        if 'qty_received' in values:
            for line in self:
                line._track_qty_received(values['qty_received'])
        return super().write(values)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_purchase(self):
        for line in self:
            if line.order_id.state == 'purchase' and line.display_type not in ['line_section', 'line_subsection', 'line_note']:
                state_description = {state_desc[0]: state_desc[1] for state_desc in self._fields['state']._description_selection(self.env)}
                raise UserError(_('Cannot delete a purchase order line which is in state “%s”.', state_description.get(line.state)))

    @api.model
    def _get_date_planned(self, seller, po=False):
        """Return the datetime value to use as Schedule Date (``date_planned``) for
           PO Lines that correspond to the given product.seller_ids,
           when ordered at `date_order_str`.

           :param Model seller: used to fetch the delivery delay (if no seller
                                is provided, the delay is 0)
           :param Model po: purchase.order, necessary only if the PO line is
                            not yet attached to a PO.
           :rtype: datetime
           :return: desired Schedule Date for the PO line
        """
        date_order = po.date_order if po else self.order_id.date_order
        if date_order:
            return date_order + relativedelta(days=seller.delay if seller else 0)
        else:
            return datetime.today() + relativedelta(days=seller.delay if seller else 0)

    @api.depends('product_id', 'order_id.partner_id')
    def _compute_analytic_distribution(self):
        for line in self:
            if not line.display_type:
                distribution = self.env['account.analytic.distribution.model']._get_distribution({
                    "product_id": line.product_id.id,
                    "product_categ_id": line.product_id.categ_id.id,
                    "partner_id": line.order_id.partner_id.id,
                    "partner_category_id": line.order_id.partner_id.category_id.ids,
                    "company_id": line.company_id.id,
                })
                line.analytic_distribution = distribution or line.analytic_distribution

    @api.onchange('product_id')
    def onchange_product_id(self):
        # TODO: Remove when onchanges are replaced with computes
        if not self.product_id or (self.env.context.get('origin_po_id') and self.product_qty):
            return

        # Reset date, price and quantity since _onchange_quantity will provide default values
        self.price_unit = self.product_qty = 0.0

        self._product_id_change()

        self._suggest_quantity()

    def _product_id_change(self):
        if not self.product_id:
            return

        self.product_uom_id = self.product_id.uom_id
        product_lang = self.product_id.with_context(
            lang=get_lang(self.env, self.partner_id.lang).code,
            partner_id=None,
            company_id=self.company_id.id,
        )
        self.name = self._get_product_purchase_description(product_lang)

        self._compute_tax_id()

    @api.depends('product_id', 'product_id.uom_id', 'product_id.uom_ids', 'product_id.seller_ids', 'product_id.seller_ids.product_uom_id')
    def _compute_allowed_uom_ids(self):
        for line in self:
            line.allowed_uom_ids = line.product_id.uom_id | line.product_id.uom_ids | line.product_id.seller_ids.product_uom_id

    @api.depends('product_qty', 'product_uom_id', 'company_id', 'order_id.partner_id')
    def _compute_price_unit_and_date_planned_and_name(self):
        for line in self:
            if not line.product_id or line.invoice_lines or not line.company_id or self.env.context.get('skip_uom_conversion'):
                continue
            params = line._get_select_sellers_params()

            if line.selected_seller_id or not line.date_planned:
                line.date_planned = line._get_date_planned(line.selected_seller_id).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

            # If not seller, use the standard price. It needs a proper currency conversion.
            if not line.selected_seller_id:
                unavailable_seller = line.product_id.seller_ids.filtered(
                    lambda s: s.partner_id == line.order_id.partner_id)
                if not unavailable_seller and line.price_unit and line.product_uom_id == line._origin.product_uom_id:
                    # Avoid to modify the price unit if there is no price list for this partner and
                    # the line has already one to avoid to override unit price set manually.
                    continue
                line.discount = 0
                po_line_uom = line.product_uom_id or line.product_id.uom_id
                price_unit = line.env['account.tax']._fix_tax_included_price_company(
                    line.product_id.uom_id._compute_price(line.product_id.standard_price, po_line_uom),
                    line.product_id.supplier_taxes_id,
                    line.tax_ids,
                    line.company_id,
                )
                price_unit = line.product_id.cost_currency_id._convert(
                    price_unit,
                    line.currency_id,
                    line.company_id,
                    line.date_order or fields.Date.context_today(line),
                    False
                )
                line.price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places, self.env['decimal.precision'].precision_get('Product Price')))

            elif line.selected_seller_id:
                price_unit = line.env['account.tax']._fix_tax_included_price_company(line.selected_seller_id.price, line.product_id.supplier_taxes_id, line.tax_ids, line.company_id) if line.selected_seller_id else 0.0
                price_unit = line.selected_seller_id.currency_id._convert(price_unit, line.currency_id, line.company_id, line.date_order or fields.Date.context_today(line), False)
                price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places, self.env['decimal.precision'].precision_get('Product Price')))
                line.price_unit = line.selected_seller_id.product_uom_id._compute_price(price_unit, line.product_uom_id)
                line.discount = line.selected_seller_id.discount or 0.0

            # record product names to avoid resetting custom descriptions
            default_names = []
            vendors = line.product_id._prepare_sellers(params=params)
            product_ctx = {'seller_id': None, 'partner_id': None, 'lang': get_lang(line.env, line.partner_id.lang).code}
            default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
            for vendor in vendors:
                product_ctx = {'seller_id': vendor.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
            if not line.name or line.name in default_names:
                product_ctx = {'seller_id': line.selected_seller_id.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                line.name = line._get_product_purchase_description(line.product_id.with_context(product_ctx))

    @api.depends('product_uom_id', 'product_qty', 'product_id.uom_id')
    def _compute_product_uom_qty(self):
        for line in self:
            if line.product_id and line.product_id.uom_id != line.product_uom_id:
                line.product_uom_qty = line.product_uom_id._compute_quantity(line.product_qty, line.product_id.uom_id)
            else:
                line.product_uom_qty = line.product_qty

    def _get_gross_price_unit(self):
        self.ensure_one()
        price_unit = self.price_unit
        if self.discount:
            price_unit = price_unit * (1 - self.discount / 100)
        if self.tax_ids:
            qty = self.product_qty or 1
            price_unit = self.tax_ids.compute_all(
                price_unit,
                currency=self.order_id.currency_id,
                quantity=qty,
                rounding_method='round_globally',
            )['total_void']
            price_unit = price_unit / qty
        if self.product_uom_id.id != self.product_id.uom_id.id:
            price_unit *= self.product_id.uom_id.factor / self.product_uom_id.factor
        return price_unit

    @api.depends('order_id.order_line.sequence')
    def _compute_section_line_id(self):
        for order, lines in self.grouped('order_id').items():
            current_section_line = False
            for line in lines.sorted('sequence'):
                if line.display_type == 'line_section':
                    current_section_line = line
                    line.section_line_id = False
                else:
                    line.section_line_id = current_section_line

    def action_add_from_catalog(self):
        order = self.env['purchase.order'].browse(self.env.context.get('order_id'))
        return order.with_context(child_field='order_line').action_add_from_catalog()

    def _suggest_quantity(self):
        ''' Suggest a minimal quantity based on the seller
        '''
        if not self.product_id:
            return
        date = self.order_id.date_order and self.order_id.date_order.date() or fields.Date.context_today(self)
        seller_min_qty = self.product_id.seller_ids\
            .filtered(lambda r: r.partner_id == self.order_id.partner_id and
                      (not r.product_id or r.product_id == self.product_id) and
                      (not r.date_start or r.date_start <= date) and
                      (not r.date_end or r.date_end >= date))\
            .sorted(key=lambda r: r.min_qty)
        if seller_min_qty:
            self.product_qty = seller_min_qty[0].min_qty or 1.0
            self.product_uom_id = seller_min_qty[0].product_uom_id
        else:
            self.product_qty = 1.0

    def _get_product_catalog_lines_data(self, **kwargs):
        """ Return information about purchase order lines in `self`.

        If `self` is empty, this method returns only the default value(s) needed for the product
        catalog. In this case, the quantity that equals 0.

        Otherwise, it returns a quantity and a price based on the product of the POL(s) and whether
        the product is read-only or not.

        A product is considered read-only if the order is considered read-only (see
        ``PurchaseOrder._is_readonly`` for more details) or if `self` contains multiple records.

        Note: This method cannot be called with multiple records that have different products linked.

        :raise odoo.exceptions.ValueError: ``len(self.product_id) != 1``
        :rtype: dict
        :return: A dict with the following structure:
            {
                'quantity': float,
                'price': float,
                'readOnly': bool,
                'uomDisplayName': String,
                'packaging': dict,
                'warning': String,
            }
        """
        if len(self) == 1:
            catalog_info = self.order_id._get_product_price_and_data(self.product_id)
            catalog_info.update(
                quantity=self.product_qty,
                price=self.price_unit * (1 - self.discount / 100),
                readOnly=self.order_id._is_readonly(),
            )
            if self.product_id.uom_id != self.product_uom_id:
                catalog_info['uomDisplayName'] = self.product_uom_id.display_name
            return catalog_info
        elif self:
            self.product_id.ensure_one()
            order_line = self[0]
            catalog_info = order_line.order_id._get_product_price_and_data(order_line.product_id)
            catalog_info['quantity'] = sum(self.mapped(
                lambda line: line.product_uom_id._compute_quantity(
                    qty=line.product_qty,
                    to_unit=line.product_id.uom_id,
            )))
            catalog_info['readOnly'] = True
            return catalog_info
        return {'quantity': 0}

    def _get_product_purchase_description(self, product_lang):
        self.ensure_one()
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        return name

    def _prepare_account_move_line(self, move=False):
        self.ensure_one()
        aml_currency = move and move.currency_id or self.currency_id
        date = move and move.date or fields.Date.today()

        res = {
            'display_type': self.display_type or 'product',
            'name': self.env['account.move.line']._get_journal_items_full_name(self.name, self.product_id.display_name),
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom_id.id,
            'quantity': -self.qty_to_invoice if move and move.move_type == 'in_refund' else self.qty_to_invoice,
            'discount': self.discount,
            'price_unit': self.currency_id._convert(self.price_unit, aml_currency, self.company_id, date, round=False),
            'tax_ids': [(6, 0, self.tax_ids.ids)],
            'purchase_line_id': self.id,
            'is_downpayment': self.is_downpayment,
        }
        return res

    @api.model
    def _prepare_add_missing_fields(self, values):
        """ Deduce missing required fields from the onchange """
        res = {}
        onchange_fields = ['name', 'price_unit', 'product_qty', 'product_uom_id', 'tax_ids', 'date_planned']
        if values.get('order_id') and values.get('product_id') and any(f not in values for f in onchange_fields):
            line = self.new(values)
            line.onchange_product_id()
            for field in onchange_fields:
                if field not in values:
                    res[field] = line._fields[field].convert_to_write(line[field], line)
        return res

    @api.model
    def _prepare_purchase_order_line(self, product_id, product_qty, product_uom, company_id, supplier, po):
        values = self.env.context.get('procurement_values', {})
        partner = supplier.partner_id
        uom_po_qty = product_uom._compute_quantity(product_qty, product_id.uom_id, rounding_method='HALF-UP')
        # _select_seller is used if the supplier have different price depending
        # the quantities ordered.
        today = fields.Date.today()
        seller = product_id.with_company(company_id)._select_seller(
            partner_id=partner,
            quantity=product_qty if values.get('force_uom') else uom_po_qty,
            date=po.date_order and max(po.date_order.date(), today) or today,
            uom_id=product_uom if values.get('force_uom') else product_id.uom_id,
            params={'force_uom': values.get('force_uom')}
        )
        if seller and (seller.product_uom_id or seller.product_tmpl_id.uom_id) != product_uom:
            uom_po_qty = product_id.uom_id._compute_quantity(uom_po_qty, seller.product_uom_id, rounding_method='HALF-UP')

        product_taxes = product_id.supplier_taxes_id.filtered(lambda x: x.company_id in company_id.parent_ids)
        taxes = po.fiscal_position_id.map_tax(product_taxes)

        if seller:
            price_unit = (seller.product_uom_id._compute_price(seller.price, product_uom) if product_uom else seller.price)
            price_unit = self.env['account.tax']._fix_tax_included_price_company(
            price_unit, product_taxes, taxes, company_id)
        else:
            price_unit = 0
        if price_unit and seller and po.currency_id and seller.currency_id != po.currency_id:
            price_unit = seller.currency_id._convert(
                price_unit, po.currency_id, po.company_id, po.date_order or fields.Date.today())

        product_lang = product_id.with_prefetch().with_context(
            lang=partner.lang,
            partner_id=partner.id,
        )
        name = product_lang.with_context(seller_id=seller.id).display_name
        if product_lang.description_purchase:
            name += '\n' + product_lang.description_purchase

        date_planned = self.order_id.date_planned or self._get_date_planned(seller, po=po)
        discount = seller.discount or 0.0

        return {
            'name': name,
            'product_qty': product_qty if product_uom else uom_po_qty,
            'product_id': product_id.id,
            'product_uom_id': product_uom.id or seller.product_uom_id.id,
            'price_unit': price_unit,
            'date_planned': date_planned,
            'tax_ids': [(6, 0, taxes.ids)],
            'order_id': po.id,
            'discount': discount,
        }

    def _convert_to_middle_of_day(self, date):
        """Return a datetime which is the noon of the input date(time) according
        to order user's time zone, convert to UTC time.
        """
        return self.order_id.get_order_timezone().localize(datetime.combine(date, time(12))).astimezone(UTC).replace(tzinfo=None)

    def _update_date_planned(self, updated_date):
        self.date_planned = updated_date

    def _track_qty_received(self, new_qty):
        self.ensure_one()
        # don't track anything when coming from the accrued expense entry wizard, as it is only computing fields at a past date to get relevant amounts
        # and doesn't actually change anything to the current record
        if  self.env.context.get('accrual_entry_date'):
            return
        if new_qty != self.qty_received and self.order_id.state == 'purchase':
            self.order_id.message_post_with_source(
                'purchase.track_po_line_qty_received_template',
                render_values={'line': self, 'qty_received': new_qty},
                subtype_xmlid='mail.mt_note',
            )

    def _validate_analytic_distribution(self):
        for line in self:
            if line.display_type:
                continue
            line._validate_distribution(
                product=line.product_id.id,
                business_domain='purchase_order',
                company_id=line.company_id.id,
            )

    def action_open_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': self.order_id.id,
            'view_mode': 'form',
        }

    def _merge_po_line(self, rfq_line):
        self.product_qty += rfq_line.product_qty
        self.price_unit = min(self.price_unit, rfq_line.price_unit)

    def _get_select_sellers_params(self):
        self.ensure_one()
        return {
            "order_id": self.order_id,
            "force_uom": True,
        }
