# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import timedelta
from itertools import groupby

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.osv import expression
from odoo.tools import float_is_zero, format_amount, format_date, html_keep_url, is_html_empty
from odoo.tools.sql import create_index

from odoo.addons.payment import utils as payment_utils

INVOICE_STATUS = [
    ('upselling', 'Upselling Opportunity'),
    ('invoiced', 'Fully Invoiced'),
    ('to invoice', 'To Invoice'),
    ('no', 'Nothing to Invoice')
]

SALE_ORDER_STATE = [
    ('draft', "Quotation"),
    ('sent', "Quotation Sent"),
    ('sale', "Sales Order"),
    ('cancel', "Cancelled"),
]


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['portal.mixin', 'product.catalog.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Sales Order"
    _order = 'date_order desc, id desc'
    _check_company_auto = True

    _sql_constraints = [
        ('date_order_conditional_required',
         "CHECK((state = 'sale' AND date_order IS NOT NULL) OR state != 'sale')",
         "A confirmed sales order requires a confirmation date."),
    ]

    @property
    def _rec_names_search(self):
        if self._context.get('sale_show_partner_name'):
            return ['name', 'partner_id.name']
        return ['name']

    #=== FIELDS ===#

    name = fields.Char(
        string="Order Reference",
        required=True, copy=False, readonly=False,
        index='trigram',
        default=lambda self: _('New'))

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True, index=True,
        default=lambda self: self.env.company)
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string="Customer",
        required=True, change_default=True, index=True,
        tracking=1,
        domain="[('company_id', 'in', (False, company_id))]")
    state = fields.Selection(
        selection=SALE_ORDER_STATE,
        string="Status",
        readonly=True, copy=False, index=True,
        tracking=3,
        default='draft')
    locked = fields.Boolean(default=False, copy=False, help="Locked orders cannot be modified.")

    client_order_ref = fields.Char(string="Customer Reference", copy=False)
    create_date = fields.Datetime(  # Override of default create_date field from ORM
        string="Creation Date", index=True, readonly=True)
    commitment_date = fields.Datetime(
        string="Delivery Date", copy=False,
        help="This is the delivery date promised to the customer. "
             "If set, the delivery order will be scheduled based on "
             "this date rather than product lead times.")
    date_order = fields.Datetime(
        string="Order Date",
        required=True, copy=False,
        help="Creation date of draft/sent orders,\nConfirmation date of confirmed orders.",
        default=fields.Datetime.now)
    origin = fields.Char(
        string="Source Document",
        help="Reference of the document that generated this sales order request")
    reference = fields.Char(
        string="Payment Ref.",
        help="The payment communication of this sale order.",
        copy=False)

    require_signature = fields.Boolean(
        string="Online signature",
        compute='_compute_require_signature',
        store=True, readonly=False, precompute=True,
        help="Request a online signature from the customer to confirm the order.")
    require_payment = fields.Boolean(
        string="Online payment",
        compute='_compute_require_payment',
        store=True, readonly=False, precompute=True,
        help="Request a online payment from the customer to confirm the order.")
    prepayment_percent = fields.Float(
        string="Prepayment percentage",
        compute='_compute_prepayment_percent',
        store=True, readonly=False, precompute=True,
        help="The percentage of the amount needed that must be paid by the customer to confirm the order.")

    signature = fields.Image(
        string="Signature",
        copy=False, attachment=True, max_width=1024, max_height=1024)
    signed_by = fields.Char(
        string="Signed By", copy=False)
    signed_on = fields.Datetime(
        string="Signed On", copy=False)

    validity_date = fields.Date(
        string="Expiration",
        compute='_compute_validity_date',
        store=True, readonly=False, copy=False, precompute=True)
    journal_id = fields.Many2one(
        'account.journal', string="Invoicing Journal",
        compute="_compute_journal_id", store=True, readonly=False, precompute=True,
        domain=[('type', '=', 'sale')], check_company=True,
        help="If set, the SO will invoice in this journal; "
             "otherwise the sales journal with the lowest sequence is used.")

    # Partner-based computes
    note = fields.Html(
        string="Terms and conditions",
        compute='_compute_note',
        store=True, readonly=False, precompute=True)

    partner_invoice_id = fields.Many2one(
        comodel_name='res.partner',
        string="Invoice Address",
        compute='_compute_partner_invoice_id',
        store=True, readonly=False, required=True, precompute=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    partner_shipping_id = fields.Many2one(
        comodel_name='res.partner',
        string="Delivery Address",
        compute='_compute_partner_shipping_id',
        store=True, readonly=False, required=True, precompute=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)

    fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position',
        string="Fiscal Position",
        compute='_compute_fiscal_position_id',
        store=True, readonly=False, precompute=True, check_company=True,
        help="Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices."
            "The default value comes from the customer.",
        domain="[('company_id', '=', company_id)]")
    payment_term_id = fields.Many2one(
        comodel_name='account.payment.term',
        string="Payment Terms",
        compute='_compute_payment_term_id',
        store=True, readonly=False, precompute=True, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    pricelist_id = fields.Many2one(
        comodel_name='product.pricelist',
        string="Pricelist",
        compute='_compute_pricelist_id',
        store=True, readonly=False, precompute=True, check_company=True,  # Unrequired company
        tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="If you change the pricelist, only newly added lines will be affected.")
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        compute='_compute_currency_id',
        store=True,
        precompute=True,
        ondelete='restrict'
    )
    currency_rate = fields.Float(
        string="Currency Rate",
        compute='_compute_currency_rate',
        digits=(12, 6),
        store=True, precompute=True)
    user_id = fields.Many2one(
        comodel_name='res.users',
        string="Salesperson",
        compute='_compute_user_id',
        store=True, readonly=False, precompute=True, index=True,
        tracking=2,
        domain=lambda self: "[('groups_id', '=', {}), ('share', '=', False), ('company_ids', '=', company_id)]".format(
            self.env.ref("sales_team.group_sale_salesman").id
        ))
    team_id = fields.Many2one(
        comodel_name='crm.team',
        string="Sales Team",
        compute='_compute_team_id',
        store=True, readonly=False, precompute=True, ondelete="set null",
        change_default=True, check_company=True,  # Unrequired company
        tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    # Lines and line based computes
    order_line = fields.One2many(
        comodel_name='sale.order.line',
        inverse_name='order_id',
        string="Order Lines",
        copy=True, auto_join=True)

    amount_untaxed = fields.Monetary(string="Untaxed Amount", store=True, compute='_compute_amounts', tracking=5)
    amount_tax = fields.Monetary(string="Taxes", store=True, compute='_compute_amounts')
    amount_total = fields.Monetary(string="Total", store=True, compute='_compute_amounts', tracking=4)
    amount_to_invoice = fields.Monetary(string="Amount to invoice", store=True, compute='_compute_amount_to_invoice')
    amount_invoiced = fields.Monetary(string="Already invoiced", compute='_compute_amount_invoiced')

    invoice_count = fields.Integer(string="Invoice Count", compute='_get_invoiced')
    invoice_ids = fields.Many2many(
        comodel_name='account.move',
        string="Invoices",
        compute='_get_invoiced',
        search='_search_invoice_ids',
        copy=False)
    invoice_status = fields.Selection(
        selection=INVOICE_STATUS,
        string="Invoice Status",
        compute='_compute_invoice_status',
        store=True)

    # Payment fields
    transaction_ids = fields.Many2many(
        comodel_name='payment.transaction',
        relation='sale_order_transaction_rel', column1='sale_order_id', column2='transaction_id',
        string="Transactions",
        copy=False, readonly=True)
    authorized_transaction_ids = fields.Many2many(
        comodel_name='payment.transaction',
        string="Authorized Transactions",
        compute='_compute_authorized_transaction_ids',
        copy=False,
        compute_sudo=True)
    amount_paid = fields.Float(compute='_compute_amount_paid', compute_sudo=True)

    # UTMs - enforcing the fact that we want to 'set null' when relation is unlinked
    campaign_id = fields.Many2one(ondelete='set null')
    medium_id = fields.Many2one(ondelete='set null')
    source_id = fields.Many2one(ondelete='set null')

    # Followup ?
    analytic_account_id = fields.Many2one(
        comodel_name='account.analytic.account',
        string="Analytic Account",
        copy=False, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    tag_ids = fields.Many2many(
        comodel_name='crm.tag',
        relation='sale_order_tag_rel', column1='order_id', column2='tag_id',
        string="Tags")

    # Remaining non stored computed fields (hide/make fields readonly, ...)
    amount_undiscounted = fields.Float(
        string="Amount Before Discount",
        compute='_compute_amount_undiscounted', digits=0)
    country_code = fields.Char(related='company_id.account_fiscal_country_id.code', string="Country code")
    expected_date = fields.Datetime(
        string="Expected Date",
        compute='_compute_expected_date', store=False,  # Note: can not be stored since depends on today()
        help="Delivery date you can promise to the customer, computed from the minimum lead time of the order lines.")
    is_expired = fields.Boolean(string="Is Expired", compute='_compute_is_expired')
    partner_credit_warning = fields.Text(
        compute='_compute_partner_credit_warning')
    tax_calculation_rounding_method = fields.Selection(
        related='company_id.tax_calculation_rounding_method',
        depends=['company_id'])
    tax_country_id = fields.Many2one(
        comodel_name='res.country',
        compute='_compute_tax_country_id',
        # Avoid access error on fiscal position when reading a sale order with company != user.company_ids
        compute_sudo=True)  # used to filter available taxes depending on the fiscal country and position
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)
    terms_type = fields.Selection(related='company_id.terms_type')
    type_name = fields.Char(string="Type Name", compute='_compute_type_name')

    # Remaining ux fields (not computed, not stored)

    show_update_fpos = fields.Boolean(
        string="Has Fiscal Position Changed", store=False)  # True if the fiscal position was changed
    has_active_pricelist = fields.Boolean(
        compute='_compute_has_active_pricelist')
    show_update_pricelist = fields.Boolean(
        string="Has Pricelist Changed", store=False)  # True if the pricelist was changed

    def init(self):
        create_index(self._cr, 'sale_order_date_order_id_idx', 'sale_order', ["date_order desc", "id desc"])

    #=== COMPUTE METHODS ===#

    @api.depends('partner_id')
    @api.depends_context('sale_show_partner_name')
    def _compute_display_name(self):
        if not self._context.get('sale_show_partner_name'):
            return super()._compute_display_name()
        for order in self:
            name = order.name
            if order.partner_id.name:
                name = f'{name} - {order.partner_id.name}'
            order.display_name = name

    @api.depends('company_id')
    def _compute_require_signature(self):
        for order in self:
            order.require_signature = order.company_id.portal_confirmation_sign

    @api.depends('company_id')
    def _compute_require_payment(self):
        for order in self:
            order.require_payment = order.company_id.portal_confirmation_pay

    @api.depends('require_payment')
    def _compute_prepayment_percent(self):
        for order in self:
            order.prepayment_percent = order.company_id.prepayment_percent

    @api.depends('company_id')
    def _compute_validity_date(self):
        today = fields.Date.context_today(self)
        for order in self:
            days = order.company_id.quotation_validity_days
            if days > 0:
                order.validity_date = today + timedelta(days)
            else:
                order.validity_date = False

    def _compute_journal_id(self):
        self.journal_id = False

    @api.depends('partner_id')
    def _compute_note(self):
        use_invoice_terms = self.env['ir.config_parameter'].sudo().get_param('account.use_invoice_terms')
        if not use_invoice_terms:
            return
        for order in self:
            order = order.with_company(order.company_id)
            if order.terms_type == 'html' and self.env.company.invoice_terms_html:
                baseurl = html_keep_url(order._get_note_url() + '/terms')
                context = {'lang': order.partner_id.lang or self.env.user.lang}
                order.note = _('Terms & Conditions: %s', baseurl)
                del context
            elif not is_html_empty(self.env.company.invoice_terms):
                order.note = order.with_context(lang=order.partner_id.lang).env.company.invoice_terms

    @api.model
    def _get_note_url(self):
        return self.env.company.get_base_url()

    @api.depends('partner_id')
    def _compute_partner_invoice_id(self):
        for order in self:
            order.partner_invoice_id = order.partner_id.address_get(['invoice'])['invoice'] if order.partner_id else False

    @api.depends('partner_id')
    def _compute_partner_shipping_id(self):
        for order in self:
            order.partner_shipping_id = order.partner_id.address_get(['delivery'])['delivery'] if order.partner_id else False

    @api.depends('partner_shipping_id', 'partner_id', 'company_id')
    def _compute_fiscal_position_id(self):
        """
        Trigger the change of fiscal position when the shipping address is modified.
        """
        cache = {}
        for order in self:
            if not order.partner_id:
                order.fiscal_position_id = False
                continue
            key = (order.company_id.id, order.partner_id.id, order.partner_shipping_id.id)
            if key not in cache:
                cache[key] = self.env['account.fiscal.position'].with_company(
                    order.company_id
                )._get_fiscal_position(order.partner_id, order.partner_shipping_id)
            order.fiscal_position_id = cache[key]

    @api.depends('partner_id')
    def _compute_payment_term_id(self):
        for order in self:
            order = order.with_company(order.company_id)
            order.payment_term_id = order.partner_id.property_payment_term_id

    @api.depends('partner_id', 'company_id')
    def _compute_pricelist_id(self):
        for order in self:
            if order.state != 'draft':
                continue
            if not order.partner_id:
                order.pricelist_id = False
                continue
            order = order.with_company(order.company_id)
            order.pricelist_id = order.partner_id.property_product_pricelist

    @api.depends('pricelist_id', 'company_id')
    def _compute_currency_id(self):
        for order in self:
            order.currency_id = order.pricelist_id.currency_id or order.company_id.currency_id

    @api.depends('currency_id', 'date_order', 'company_id')
    def _compute_currency_rate(self):
        for order in self:
            order.currency_rate = self.env['res.currency']._get_conversion_rate(
                from_currency=order.company_id.currency_id,
                to_currency=order.currency_id,
                company=order.company_id,
                date=order.date_order.date(),
            )

    @api.depends('company_id')
    def _compute_has_active_pricelist(self):
        for order in self:
            order.has_active_pricelist = bool(self.env['product.pricelist'].search(
                [('company_id', 'in', (False, order.company_id.id)), ('active', '=', True)],
                limit=1,
            ))

    @api.depends('partner_id')
    def _compute_user_id(self):
        for order in self:
            if order.partner_id and not (order._origin.id and order.user_id):
                # Recompute the salesman on partner change
                #   * if partner is set (is required anyway, so it will be set sooner or later)
                #   * if the order is not saved or has no salesman already
                order.user_id = (
                    order.partner_id.user_id
                    or order.partner_id.commercial_partner_id.user_id
                    or (self.user_has_groups('sales_team.group_sale_salesman') and self.env.user)
                )

    @api.depends('partner_id', 'user_id')
    def _compute_team_id(self):
        cached_teams = {}
        for order in self:
            default_team_id = self.env.context.get('default_team_id', False) or order.team_id.id or order.partner_id.team_id.id
            user_id = order.user_id.id
            company_id = order.company_id.id
            key = (default_team_id, user_id, company_id)
            if key not in cached_teams:
                cached_teams[key] = self.env['crm.team'].with_context(
                    default_team_id=default_team_id,
                )._get_default_team_id(
                    user_id=user_id,
                    domain=self.env['crm.team']._check_company_domain(company_id),
                )
            order.team_id = cached_teams[key]

    @api.depends('order_line.price_subtotal', 'order_line.price_tax', 'order_line.price_total')
    def _compute_amounts(self):
        """Compute the total amounts of the SO."""
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                amount_tax = sum(order_lines.mapped('price_tax'))

            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_total = order.amount_untaxed + order.amount_tax

    @api.depends('order_line.invoice_lines')
    def _get_invoiced(self):
        # The invoice_ids are obtained thanks to the invoice lines of the SO
        # lines, and we also search for possible refunds created directly from
        # existing invoices. This is necessary since such a refund is not
        # directly linked to the SO.
        for order in self:
            invoices = order.order_line.invoice_lines.move_id.filtered(lambda r: r.move_type in ('out_invoice', 'out_refund'))
            order.invoice_ids = invoices
            order.invoice_count = len(invoices)

    def _search_invoice_ids(self, operator, value):
        if operator == 'in' and value:
            self.env.cr.execute("""
                SELECT array_agg(so.id)
                    FROM sale_order so
                    JOIN sale_order_line sol ON sol.order_id = so.id
                    JOIN sale_order_line_invoice_rel soli_rel ON soli_rel.order_line_id = sol.id
                    JOIN account_move_line aml ON aml.id = soli_rel.invoice_line_id
                    JOIN account_move am ON am.id = aml.move_id
                WHERE
                    am.move_type in ('out_invoice', 'out_refund') AND
                    am.id = ANY(%s)
            """, (list(value),))
            so_ids = self.env.cr.fetchone()[0] or []
            return [('id', 'in', so_ids)]
        elif operator == '=' and not value:
            # special case for [('invoice_ids', '=', False)], i.e. "Invoices is not set"
            #
            # We cannot just search [('order_line.invoice_lines', '=', False)]
            # because it returns orders with uninvoiced lines, which is not
            # same "Invoices is not set" (some lines may have invoices and some
            # doesn't)
            #
            # A solution is making inverted search first ("orders with invoiced
            # lines") and then invert results ("get all other orders")
            #
            # Domain below returns subset of ('order_line.invoice_lines', '!=', False)
            order_ids = self._search([
                ('order_line.invoice_lines.move_id.move_type', 'in', ('out_invoice', 'out_refund'))
            ])
            return [('id', 'not in', order_ids)]
        return [
            ('order_line.invoice_lines.move_id.move_type', 'in', ('out_invoice', 'out_refund')),
            ('order_line.invoice_lines.move_id', operator, value),
        ]

    @api.depends('state', 'order_line.invoice_status')
    def _compute_invoice_status(self):
        """
        Compute the invoice status of a SO. Possible statuses:
        - no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
          invoice. This is also the default value if the conditions of no other status is met.
        - to invoice: if any SO line is 'to invoice', the whole SO is 'to invoice'
        - invoiced: if all SO lines are invoiced, the SO is invoiced.
        - upselling: if all SO lines are invoiced or upselling, the status is upselling.
        """
        confirmed_orders = self.filtered(lambda so: so.state == 'sale')
        (self - confirmed_orders).invoice_status = 'no'
        if not confirmed_orders:
            return
        line_invoice_status_all = [
            (order.id, invoice_status)
            for order, invoice_status in self.env['sale.order.line']._read_group([
                    ('order_id', 'in', confirmed_orders.ids),
                    ('is_downpayment', '=', False),
                    ('display_type', '=', False),
                ],
                ['order_id', 'invoice_status'])]
        for order in confirmed_orders:
            line_invoice_status = [d[1] for d in line_invoice_status_all if d[0] == order.id]
            if order.state != 'sale':
                order.invoice_status = 'no'
            elif any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                order.invoice_status = 'to invoice'
            elif line_invoice_status and all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                order.invoice_status = 'invoiced'
            elif line_invoice_status and all(invoice_status in ('invoiced', 'upselling') for invoice_status in line_invoice_status):
                order.invoice_status = 'upselling'
            else:
                order.invoice_status = 'no'

    @api.depends('transaction_ids')
    def _compute_authorized_transaction_ids(self):
        for trans in self:
            trans.authorized_transaction_ids = trans.transaction_ids.filtered(lambda t: t.state == 'authorized')

    @api.depends('transaction_ids')
    def _compute_amount_paid(self):
        """ Sum of the amount paid through all transactions for this SO. """
        for order in self:
            order.amount_paid = sum(
                tx.amount for tx in order.transaction_ids if tx.state in ('authorized', 'done')
            )

    def _compute_amount_undiscounted(self):
        for order in self:
            total = 0.0
            for line in order.order_line:
                total += (line.price_subtotal * 100)/(100-line.discount) if line.discount != 100 else (line.price_unit * line.product_uom_qty)
            order.amount_undiscounted = total

    @api.depends('order_line.customer_lead', 'date_order', 'state')
    def _compute_expected_date(self):
        """ For service and consumable, we only take the min dates. This method is extended in sale_stock to
            take the picking_policy of SO into account.
        """
        self.mapped("order_line")  # Prefetch indication
        for order in self:
            if order.state == 'cancel':
                order.expected_date = False
                continue
            dates_list = order.order_line.filtered(
                lambda line: not line.display_type and not line._is_delivery()
            ).mapped(lambda line: line and line._expected_date())
            if dates_list:
                order.expected_date = min(dates_list)
            else:
                order.expected_date = False

    def _compute_is_expired(self):
        today = fields.Date.today()
        for order in self:
            order.is_expired = order.state == 'sent' and order.validity_date and order.validity_date < today

    @api.depends('company_id', 'fiscal_position_id')
    def _compute_tax_country_id(self):
        for record in self:
            if record.fiscal_position_id.foreign_vat:
                record.tax_country_id = record.fiscal_position_id.country_id
            else:
                record.tax_country_id = record.company_id.account_fiscal_country_id

    @api.depends('invoice_ids.state', 'currency_id', 'amount_total')
    def _compute_amount_to_invoice(self):
        for order in self:
            # If the invoice status is 'Fully Invoiced' force the amount to invoice to equal zero and return early.
            if order.invoice_status == 'invoiced':
                order.amount_to_invoice = 0.0
                return

            order.amount_to_invoice = order.amount_total
            for invoice in order.invoice_ids.filtered(lambda x: x.state == 'posted'):
                prices = sum(invoice.line_ids.filtered(lambda x: order in x.sale_line_ids.order_id).mapped('price_total'))
                invoice_amount_currency = invoice.currency_id._convert(
                    prices * -invoice.direction_sign,
                    order.currency_id,
                    invoice.company_id,
                    invoice.date,
                )
                order.amount_to_invoice -= invoice_amount_currency

    @api.depends('amount_total', 'amount_to_invoice')
    def _compute_amount_invoiced(self):
        for order in self:
            order.amount_invoiced = order.amount_total - order.amount_to_invoice

    @api.depends('company_id', 'partner_id', 'amount_total')
    def _compute_partner_credit_warning(self):
        for order in self:
            order.with_company(order.company_id)
            order.partner_credit_warning = ''
            show_warning = order.state in ('draft', 'sent') and \
                           order.company_id.account_use_credit_limit
            if show_warning:
                order.partner_credit_warning = self.env['account.move']._build_credit_warning_message(
                    order,
                    current_amount=(order.amount_total / order.currency_rate),
                )

    @api.depends('order_line.tax_id', 'order_line.price_unit', 'amount_total', 'amount_untaxed', 'currency_id')
    def _compute_tax_totals(self):
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type)
            order.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id or order.company_id.currency_id,
            )

    @api.depends('state')
    def _compute_type_name(self):
        for record in self:
            if record.state in ('draft', 'sent', 'cancel'):
                record.type_name = _("Quotation")
            else:
                record.type_name = _("Sales Order")

    # portal.mixin override
    def _compute_access_url(self):
        super()._compute_access_url()
        for order in self:
            order.access_url = f'/my/orders/{order.id}'

    #=== CONSTRAINT METHODS ===#

    @api.constrains('company_id', 'order_line')
    def _check_order_line_company_id(self):
        for order in self:
            companies = order.order_line.product_id.company_id
            if companies and companies != order.company_id:
                bad_products = order.order_line.product_id.filtered(lambda p: p.company_id and p.company_id != order.company_id)
                raise ValidationError(_(
                    "Your quotation contains products from company %(product_company)s whereas your quotation belongs to company %(quote_company)s. \n Please change the company of your quotation or remove the products from other companies (%(bad_products)s).",
                    product_company=', '.join(companies.mapped('display_name')),
                    quote_company=order.company_id.display_name,
                    bad_products=', '.join(bad_products.mapped('display_name')),
                ))

    @api.constrains('prepayment_percent')
    def _check_prepayment_percent(self):
        for order in self:
            if order.require_payment and not (0 < order.prepayment_percent <= 1.0):
                raise ValidationError(_("Prepayment percentage must be a valid percentage."))

    #=== ONCHANGE METHODS ===#

    @api.onchange('commitment_date', 'expected_date')
    def _onchange_commitment_date(self):
        """ Warn if the commitment dates is sooner than the expected date """
        if self.commitment_date and self.expected_date and self.commitment_date < self.expected_date:
            return {
                'warning': {
                    'title': _('Requested date is too soon.'),
                    'message': _("The delivery date is sooner than the expected date."
                                 " You may be unable to honor the delivery date.")
                }
            }

    @api.onchange('company_id')
    def _onchange_company_id_warning(self):
        self.show_update_pricelist = True
        if self.order_line and self.state == 'draft':
            return {
                'warning': {
                    'title': _("Warning for the change of your quotation's company"),
                    'message': _("Changing the company of an existing quotation might need some "
                                 "manual adjustments in the details of the lines. You might "
                                 "consider updating the prices."),
                }
            }

    @api.onchange('fiscal_position_id')
    def _onchange_fpos_id_show_update_fpos(self):
        if self.order_line and (
            not self.fiscal_position_id
            or (self.fiscal_position_id and self._origin.fiscal_position_id != self.fiscal_position_id)
        ):
            self.show_update_fpos = True

    @api.onchange('partner_id')
    def _onchange_partner_id_warning(self):
        if not self.partner_id:
            return

        partner = self.partner_id

        # If partner has no warning, check its company
        if partner.sale_warn == 'no-message' and partner.parent_id:
            partner = partner.parent_id

        if partner.sale_warn and partner.sale_warn != 'no-message':
            # Block if partner only has warning but parent company is blocked
            if partner.sale_warn != 'block' and partner.parent_id and partner.parent_id.sale_warn == 'block':
                partner = partner.parent_id

            if partner.sale_warn == 'block':
                self.partner_id = False

            return {
                'warning': {
                    'title': _("Warning for %s", partner.name),
                    'message': partner.sale_warn_msg,
                }
            }

    @api.onchange('pricelist_id')
    def _onchange_pricelist_id_show_update_prices(self):
        self.show_update_pricelist = bool(self.order_line)

    @api.onchange('prepayment_percent')
    def _onchange_prepayment_percent(self):
        if not self.prepayment_percent:
            self.require_payment = False

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'company_id' in vals:
                self = self.with_company(vals['company_id'])
            if vals.get('name', _("New")) == _("New"):
                seq_date = fields.Datetime.context_timestamp(
                    self, fields.Datetime.to_datetime(vals['date_order'])
                ) if 'date_order' in vals else None
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'sale.order', sequence_date=seq_date) or _("New")

        return super().create(vals_list)

    def copy_data(self, default=None):
        if default is None:
            default = {}
        if 'order_line' not in default:
            default['order_line'] = [
                Command.create(line.copy_data()[0])
                for line in self.order_line.filtered(lambda l: not l.is_downpayment)
            ]
        return super().copy_data(default)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        for order in self:
            if order.state not in ('draft', 'cancel'):
                raise UserError(_(
                    "You can not delete a sent quotation or a confirmed sales order."
                    " You must first cancel it."))

    #=== ACTION METHODS ===#

    def action_open_discount_wizard(self):
        self.ensure_one()
        return {
            'name': _("Discount"),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.discount',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_draft(self):
        orders = self.filtered(lambda s: s.state in ['cancel', 'sent'])
        return orders.write({
            'state': 'draft',
            'signature': False,
            'signed_by': False,
            'signed_on': False,
        })

    def action_quotation_send(self):
        """ Opens a wizard to compose an email, with relevant mail template loaded by default """
        self.ensure_one()
        self.order_line._validate_analytic_distribution()
        lang = self.env.context.get('lang')
        mail_template = self._find_mail_template()
        if mail_template and mail_template.lang:
            lang = mail_template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'sale.order',
            'default_res_ids': self.ids,
            'default_template_id': mail_template.id if mail_template else None,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'default_email_layout_xmlid': 'mail.mail_notification_layout_with_responsible_signature',
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'model_description': self.with_context(lang=lang).type_name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def _find_mail_template(self):
        """ Get the appropriate mail template for the current sales order based on its state.

        If the SO is confirmed, we return the mail template for the sale confirmation.
        Otherwise, we return the quotation email template.

        :return: The correct mail template based on the current status
        :rtype: record of `mail.template` or `None` if not found
        """
        self.ensure_one()
        if self.env.context.get('proforma') or self.state != 'sale':
            return self.env.ref('sale.email_template_edi_sale', raise_if_not_found=False)
        else:
            return self._get_confirmation_template()

    def _get_confirmation_template(self):
        """ Get the mail template sent on SO confirmation (or for confirmed SO's).

        :return: `mail.template` record or None if default template wasn't found
        """
        self.ensure_one()
        default_confirmation_template_id = self.env['ir.config_parameter'].sudo().get_param(
            'sale.default_confirmation_template'
        )
        default_confirmation_template = default_confirmation_template_id \
            and self.env['mail.template'].browse(int(default_confirmation_template_id)).exists()
        if default_confirmation_template:
            return default_confirmation_template
        else:
            return self.env.ref('sale.mail_template_sale_confirmation', raise_if_not_found=False)

    def action_quotation_sent(self):
        """ Mark the given draft quotation(s) as sent.

        :raise: UserError if any given SO is not in draft state.
        """
        if any(order.state != 'draft' for order in self):
            raise UserError(_("Only draft orders can be marked as sent directly."))

        for order in self:
            order.message_subscribe(partner_ids=order.partner_id.ids)

        self.write({'state': 'sent'})

    def action_confirm(self):
        """ Confirm the given quotation(s) and set their confirmation date.

        If the corresponding setting is enabled, also locks the Sale Order.

        :return: True
        :rtype: bool
        :raise: UserError if trying to confirm cancelled SO's
        """
        if not all(order._can_be_confirmed() for order in self):
            raise UserError(_(
                "The following orders are not in a state requiring confirmation: %s",
                ", ".join(self.mapped('display_name')),
            ))

        self.order_line._validate_analytic_distribution()

        for order in self:
            order.validate_taxes_on_sales_order()
            if order.partner_id in order.message_partner_ids:
                continue
            order.message_subscribe([order.partner_id.id])

        self.write(self._prepare_confirmation_values())

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = self._context.copy()
        context.pop('default_name', None)

        self.with_context(context)._action_confirm()
        if self.env.user.has_group('sale.group_auto_done_setting'):
            self.action_lock()

        return True

    def _can_be_confirmed(self):
        self.ensure_one()
        return self.state in {'draft', 'sent'}

    def _prepare_confirmation_values(self):
        """ Prepare the sales order confirmation values.

        Note: self can contain multiple records.

        :return: Sales Order confirmation values
        :rtype: dict
        """
        return {
            'state': 'sale',
            'date_order': fields.Datetime.now()
        }

    def _action_confirm(self):
        """ Implementation of additional mechanism of Sales Order confirmation.
            This method should be extended when the confirmation should generated
            other documents. In this method, the SO are in 'sale' state (not yet 'done').
        """
        # create an analytic account if at least an expense product
        for order in self:
            if any(expense_policy not in [False, 'no'] for expense_policy in order.order_line.product_id.mapped('expense_policy')):
                if not order.analytic_account_id:
                    order._create_analytic_account()

    def _send_order_confirmation_mail(self):
        """ Send a mail to the SO customer to inform them that their order has been confirmed.

        :return: None
        """
        for order in self:
            mail_template = order._get_confirmation_template()
            order._send_order_notification_mail(mail_template)

    def _send_payment_succeeded_for_order_mail(self):
        """ Send a mail to the SO customer to inform them that a payment has been initiated.

        :return: None
        """
        mail_template = self.env.ref(
            'sale.mail_template_sale_payment_executed', raise_if_not_found=False
        )
        for order in self:
            order._send_order_notification_mail(mail_template)

    def _send_order_notification_mail(self, mail_template):
        """ Send a mail to the customer

        Note: self.ensure_one()

        :param mail.template mail_template: the template used to generate the mail
        :return: None
        """
        self.ensure_one()

        if not mail_template:
            return

        if self.env.su:
            # sending mail in sudo was meant for it being sent from superuser
            self = self.with_user(SUPERUSER_ID)

        self.with_context(force_send=True).message_post_with_source(
            mail_template,
            email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature',
            subtype_xmlid='mail.mt_comment',
        )

    def action_lock(self):
        for order in self:
            tx = order.sudo().transaction_ids._get_last()
            if tx and tx.state == 'pending' and tx.provider_id.code == 'custom' and tx.provider_id.custom_mode == 'wire_transfer':
                tx._set_done()
                tx.write({'is_post_processed': True})
        self.locked = True

    def action_unlock(self):
        self.locked = False

    def action_cancel(self):
        """ Cancel SO after showing the cancel wizard when needed. (cfr :meth:`_show_cancel_wizard`)

        For post-cancel operations, please only override :meth:`_action_cancel`.

        note: self.ensure_one() if the wizard is shown.
        """
        if any(order.locked for order in self):
            raise UserError(_("You cannot cancel a locked order. Please unlock it first."))
        cancel_warning = self._show_cancel_wizard()
        if cancel_warning:
            self.ensure_one()
            template_id = self.env['ir.model.data']._xmlid_to_res_id(
                'sale.mail_template_sale_cancellation', raise_if_not_found=False
            )
            lang = self.env.context.get('lang')
            template = self.env['mail.template'].browse(template_id)
            if template.lang:
                lang = template._render_lang(self.ids)[self.id]
            ctx = {
                'default_template_id': template_id,
                'default_order_id': self.id,
                'mark_so_as_canceled': True,
                'default_email_layout_xmlid': "mail.mail_notification_layout_with_responsible_signature",
                'model_description': self.with_context(lang=lang).type_name,
            }
            return {
                'name': _('Cancel %s', self.type_name),
                'view_mode': 'form',
                'res_model': 'sale.order.cancel',
                'view_id': self.env.ref('sale.sale_order_cancel_view_form').id,
                'type': 'ir.actions.act_window',
                'context': ctx,
                'target': 'new'
            }
        else:
            return self._action_cancel()

    def _action_cancel(self):
        inv = self.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        inv.button_cancel()
        return self.write({'state': 'cancel'})

    def _show_cancel_wizard(self):
        """ Decide whether the sale.order.cancel wizard should be shown to cancel specified orders.

        :return: True if there is any non-draft order in the given orders
        :rtype: bool
        """
        if self.env.context.get('disable_cancel_warning'):
            return False
        return any(so.state != 'draft' for so in self)

    def action_preview_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }

    def action_update_taxes(self):
        self.ensure_one()

        self._recompute_taxes()

        if self.partner_id:
            self.message_post(body=_("Product taxes have been recomputed according to fiscal position %s.",
                self.fiscal_position_id._get_html_link() if self.fiscal_position_id else "")
            )

    def _recompute_taxes(self):
        lines_to_recompute = self.order_line.filtered(lambda line: not line.display_type)
        lines_to_recompute._compute_tax_id()
        self.show_update_fpos = False

    def action_update_prices(self):
        self.ensure_one()

        self._recompute_prices()

        if self.pricelist_id:
            message = _("Product prices have been recomputed according to pricelist %s.",
                self.pricelist_id._get_html_link())
        else:
            message = _("Product prices have been recomputed.")
        self.message_post(body=message)

    def _recompute_prices(self):
        lines_to_recompute = self._get_update_prices_lines()
        lines_to_recompute.invalidate_recordset(['pricelist_item_id'])
        lines_to_recompute._compute_price_unit()
        # Special case: we want to overwrite the existing discount on _recompute_prices call
        # i.e. to make sure the discount is correctly reset
        # if pricelist discount_policy is different than when the price was first computed.
        lines_to_recompute.discount = 0.0
        lines_to_recompute._compute_discount()
        self.show_update_pricelist = False

    def _default_order_line_values(self):
        default_data = super()._default_order_line_values()
        new_default_data = self.env['sale.order.line']._get_product_catalog_lines_data()
        return {**default_data, **new_default_data}

    def _get_action_add_from_catalog_extra_context(self):
        return {
            **super()._get_action_add_from_catalog_extra_context(),
            'product_catalog_currency_id': self.currency_id.id,
            'product_catalog_digits': self.order_line._fields['price_unit'].get_digits(self.env),
        }

    def _get_product_catalog_domain(self):
        return expression.AND([super()._get_product_catalog_domain(), [('sale_ok', '=', True)]])

    # INVOICING #

    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        self.ensure_one()

        values = {
            'ref': self.client_order_ref or '',
            'move_type': 'out_invoice',
            'narration': self.note,
            'currency_id': self.currency_id.id,
            'campaign_id': self.campaign_id.id,
            'medium_id': self.medium_id.id,
            'source_id': self.source_id.id,
            'team_id': self.team_id.id,
            'partner_id': self.partner_invoice_id.id,
            'partner_shipping_id': self.partner_shipping_id.id,
            'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id._get_fiscal_position(self.partner_invoice_id)).id,
            'invoice_origin': self.name,
            'invoice_payment_term_id': self.payment_term_id.id,
            'invoice_user_id': self.user_id.id,
            'payment_reference': self.reference,
            'transaction_ids': [Command.set(self.transaction_ids.ids)],
            'company_id': self.company_id.id,
            'invoice_line_ids': [],
            'user_id': self.user_id.id,
        }
        if self.journal_id:
            values['journal_id'] = self.journal_id.id
        return values

    def action_view_invoice(self, invoices=False):
        if not invoices:
            invoices = self.mapped('invoice_ids')
        action = self.env['ir.actions.actions']._for_xml_id('account.action_move_out_invoice_type')
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_move_type': 'out_invoice',
        }
        if len(self) == 1:
            context.update({
                'default_partner_id': self.partner_id.id,
                'default_partner_shipping_id': self.partner_shipping_id.id,
                'default_invoice_payment_term_id': self.payment_term_id.id or self.partner_id.property_payment_term_id.id or self.env['account.move'].default_get(['invoice_payment_term_id']).get('invoice_payment_term_id'),
                'default_invoice_origin': self.name,
            })
        action['context'] = context
        return action

    def _get_invoice_grouping_keys(self):
        return ['company_id', 'partner_id', 'currency_id']

    def _nothing_to_invoice_error_message(self):
        return _(
            "Cannot create an invoice. No items are available to invoice.\n\n"
            "To resolve this issue, please ensure that:\n"
            "   \u2022 The products have been delivered before attempting to invoice them.\n"
            "   \u2022 The invoicing policy of the product is configured correctly.\n\n"
            "If you want to invoice based on ordered quantities instead:\n"
            "   \u2022 For consumable or storable products, open the product, go to the 'General Information' tab and change the 'Invoicing Policy' from 'Delivered Quantities' to 'Ordered Quantities'.\n"
            "   \u2022 For services (and other products), change the 'Invoicing Policy' to 'Prepaid/Fixed Price'.\n"
        )

    def _get_update_prices_lines(self):
        """ Hook to exclude specific lines which should not be updated based on price list recomputation """
        return self.order_line.filtered(lambda line: not line.display_type)

    def _get_invoiceable_lines(self, final=False):
        """Return the invoiceable lines for order `self`."""
        down_payment_line_ids = []
        invoiceable_line_ids = []
        pending_section = None
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        for line in self.order_line:
            if line.display_type == 'line_section':
                # Only invoice the section if one of its lines is invoiceable
                pending_section = line
                continue
            if line.display_type != 'line_note' and float_is_zero(line.qty_to_invoice, precision_digits=precision):
                continue
            if line.qty_to_invoice > 0 or (line.qty_to_invoice < 0 and final) or line.display_type == 'line_note':
                if line.is_downpayment:
                    # Keep down payment lines separately, to put them together
                    # at the end of the invoice, in a specific dedicated section.
                    down_payment_line_ids.append(line.id)
                    continue
                if pending_section:
                    invoiceable_line_ids.append(pending_section.id)
                    pending_section = None
                invoiceable_line_ids.append(line.id)

        return self.env['sale.order.line'].browse(invoiceable_line_ids + down_payment_line_ids)

    def _create_invoices(self, grouped=False, final=False, date=None):
        """ Create invoice(s) for the given Sales Order(s).

        :param bool grouped: if True, invoices are grouped by SO id.
            If False, invoices are grouped by keys returned by :meth:`_get_invoice_grouping_keys`
        :param bool final: if True, refunds will be generated if necessary
        :param date: unused parameter
        :returns: created invoices
        :rtype: `account.move` recordset
        :raises: UserError if one of the orders has no invoiceable lines.
        """
        if not self.env['account.move'].check_access_rights('create', False):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                return self.env['account.move']

        # 1) Create invoices.
        invoice_vals_list = []
        invoice_item_sequence = 0 # Incremental sequencing to keep the lines order on the invoice.
        for order in self:
            order = order.with_company(order.company_id).with_context(lang=order.partner_invoice_id.lang)

            invoice_vals = order._prepare_invoice()
            invoiceable_lines = order._get_invoiceable_lines(final)

            if not any(not line.display_type for line in invoiceable_lines):
                continue

            invoice_line_vals = []
            down_payment_section_added = False
            for line in invoiceable_lines:
                if not down_payment_section_added and line.is_downpayment:
                    # Create a dedicated section for the down payments
                    # (put at the end of the invoiceable_lines)
                    invoice_line_vals.append(
                        Command.create(
                            order._prepare_down_payment_section_line(sequence=invoice_item_sequence)
                        ),
                    )
                    down_payment_section_added = True
                    invoice_item_sequence += 1
                invoice_line_vals.append(
                    Command.create(
                        line._prepare_invoice_line(sequence=invoice_item_sequence)
                    ),
                )
                invoice_item_sequence += 1

            invoice_vals['invoice_line_ids'] += invoice_line_vals
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list and self._context.get('raise_if_nothing_to_invoice', True):
            raise UserError(self._nothing_to_invoice_error_message())

        # 2) Manage 'grouped' parameter: group by (partner_id, currency_id).
        if not grouped:
            new_invoice_vals_list = []
            invoice_grouping_keys = self._get_invoice_grouping_keys()
            invoice_vals_list = sorted(
                invoice_vals_list,
                key=lambda x: [
                    x.get(grouping_key) for grouping_key in invoice_grouping_keys
                ]
            )
            for _grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: [x.get(grouping_key) for grouping_key in invoice_grouping_keys]):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

        # 3) Create invoices.

        # As part of the invoice creation, we make sure the sequence of multiple SO do not interfere
        # in a single invoice. Example:
        # SO 1:
        # - Section A (sequence: 10)
        # - Product A (sequence: 11)
        # SO 2:
        # - Section B (sequence: 10)
        # - Product B (sequence: 11)
        #
        # If SO 1 & 2 are grouped in the same invoice, the result will be:
        # - Section A (sequence: 10)
        # - Section B (sequence: 10)
        # - Product A (sequence: 11)
        # - Product B (sequence: 11)
        #
        # Resequencing should be safe, however we resequence only if there are less invoices than
        # orders, meaning a grouping might have been done. This could also mean that only a part
        # of the selected SO are invoiceable, but resequencing in this case shouldn't be an issue.
        if len(invoice_vals_list) < len(self):
            SaleOrderLine = self.env['sale.order.line']
            for invoice in invoice_vals_list:
                sequence = 1
                for line in invoice['invoice_line_ids']:
                    line[2]['sequence'] = SaleOrderLine._get_invoice_line_sequence(new=sequence, old=line[2]['sequence'])
                    sequence += 1

        # Manage the creation of invoices in sudo because a salesperson must be able to generate an invoice from a
        # sale order without "billing" access rights. However, he should not be able to create an invoice from scratch.
        moves = self.env['account.move'].sudo().with_context(default_move_type='out_invoice').create(invoice_vals_list)

        # 4) Some moves might actually be refunds: convert them if the total amount is negative
        # We do this after the moves have been created since we need taxes, etc. to know if the total
        # is actually negative or not
        if final:
            moves.sudo().filtered(lambda m: m.amount_total < 0).action_switch_move_type()
        for move in moves:
            if final:
                # Downpayment might have been determined by a fixed amount set by the user.
                # This amount is tax included. This can lead to rounding issues.
                # E.g. a user wants a 100€ DP on a product with 21% tax.
                # 100 / 1.21 = 82.64, 82.64 * 1,21 = 99.99
                # This is already corrected by adding/removing the missing cents on the DP invoice,
                # but must also be accounted for on the final invoice.

                delta_amount = 0
                for order_line in self.order_line:
                    if not order_line.is_downpayment:
                        continue
                    inv_amt = order_amt = 0
                    for invoice_line in order_line.invoice_lines:
                        if invoice_line.move_id == move:
                            inv_amt += invoice_line.price_total
                        elif invoice_line.move_id.state != 'cancel':  # filter out canceled dp lines
                            order_amt += invoice_line.price_total
                    if inv_amt and order_amt:
                        # if not inv_amt, this order line is not related to current move
                        # if no order_amt, dp order line was not invoiced
                        delta_amount += (inv_amt * (1 if move.is_inbound() else -1)) + order_amt

                if not move.currency_id.is_zero(delta_amount):
                    receivable_line = move.line_ids.filtered(
                        lambda aml: aml.account_id.account_type == 'asset_receivable')[:1]
                    product_lines = move.line_ids.filtered(
                        lambda aml: aml.display_type == 'product' and aml.is_downpayment)
                    tax_lines = move.line_ids.filtered(
                        lambda aml: aml.tax_line_id.amount_type not in (False, 'fixed'))
                    if tax_lines and product_lines and receivable_line:
                        line_commands = [Command.update(receivable_line.id, {
                            'amount_currency': receivable_line.amount_currency + delta_amount,
                        })]
                        delta_sign = 1 if delta_amount > 0 else -1
                        for lines, attr, sign in (
                            (product_lines, 'price_total', -1 if move.is_inbound() else 1),
                            (tax_lines, 'amount_currency', 1),
                        ):
                            remaining = delta_amount
                            lines_len = len(lines)
                            for line in lines:
                                if move.currency_id.compare_amounts(remaining, 0) != delta_sign:
                                    break
                                amt = delta_sign * max(
                                    move.currency_id.rounding,
                                    abs(move.currency_id.round(remaining / lines_len)),
                                )
                                remaining -= amt
                                line_commands.append(Command.update(line.id, {attr: line[attr] + amt * sign}))
                        move.line_ids = line_commands

            move.message_post_with_source(
                'mail.message_origin_link',
                render_values={'self': move, 'origin': move.line_ids.sale_line_ids.order_id},
                subtype_xmlid='mail.mt_note',
            )
        return moves

    # MAIL #

    def _track_finalize(self):
        """ Override of `mail` to prevent logging changes when the SO is in a draft state. """
        if (len(self) == 1
            # The method _track_finalize is sometimes called too early or too late and it
            # might cause a desynchronization with the cache, thus this condition is needed.
            and self.env.cache.contains(self, self._fields['state']) and self.state == 'draft'):
            self.env.cr.precommit.data.pop(f'mail.tracking.{self._name}', {})
            self.env.flush_all()
            return
        return super()._track_finalize()

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_so_as_sent'):
            self.filtered(lambda o: o.state == 'draft').with_context(tracking_disable=True).write({'state': 'sent'})
        so_ctx = {'mail_post_autofollow': self.env.context.get('mail_post_autofollow', True)}
        if self.env.context.get('mark_so_as_sent') and 'mail_notify_author' not in kwargs:
            kwargs['notify_author'] = self.env.user.partner_id.id in (kwargs.get('partner_ids') or [])
        return super(SaleOrder, self.with_context(**so_ctx)).message_post(**kwargs)

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        """ Give access button to users and portal customer as portal is integrated
        in sale. Customer and portal group have probably no right to see
        the document so they don't have the access button. """
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        self.ensure_one()
        if self._context.get('proforma'):
            for group in [g for g in groups if g[0] in ('portal_customer', 'portal', 'follower', 'customer')]:
                group[2]['has_button_access'] = False
            return groups
        local_msg_vals = dict(msg_vals or {})

        # portal customers have full access (existence not granted, depending on partner_id)
        try:
            customer_portal_group = next(group for group in groups if group[0] == 'portal_customer')
        except StopIteration:
            pass
        else:
            access_opt = customer_portal_group[2].setdefault('button_access', {})
            is_tx_pending = self.get_portal_last_transaction().state == 'pending'
            if self._has_to_be_signed():
                if self._has_to_be_paid():
                    access_opt['title'] = _("View Quotation") if is_tx_pending else _("Sign & Pay Quotation")
                else:
                    access_opt['title'] = _("Accept & Sign Quotation")
            elif self._has_to_be_paid() and not is_tx_pending:
                access_opt['title'] = _("Accept & Pay Quotation")
            elif self.state in ('draft', 'sent'):
                access_opt['title'] = _("View Quotation")

        # enable followers that have access through portal
        follower_group = next(group for group in groups if group[0] == 'follower')
        follower_group[2]['active'] = True
        follower_group[2]['has_button_access'] = True
        access_opt = follower_group[2].setdefault('button_access', {})
        if self.state in ('draft', 'sent'):
            access_opt['title'] = _("View Quotation")
        else:
            access_opt['title'] = _("View Order")
        access_opt['url'] = self._notify_get_action_link('view', **local_msg_vals)

        return groups

    def _notify_by_email_prepare_rendering_context(self, message, msg_vals, model_description=False,
                                                   force_email_company=False, force_email_lang=False):
        render_context = super()._notify_by_email_prepare_rendering_context(
            message, msg_vals, model_description=model_description,
            force_email_company=force_email_company, force_email_lang=force_email_lang
        )
        lang_code = render_context.get('lang')
        subtitles = [
            render_context['record'].name,
        ]

        if self.amount_total:
            # Do not show the price in subtitles if zero (e.g. e-commerce orders are created empty)
            subtitles.append(
                format_amount(self.env, self.amount_total, self.currency_id, lang_code=lang_code),
            )

        if self.validity_date and self.state in ['draft', 'sent']:
            formatted_date = format_date(self.env, self.validity_date, lang_code=lang_code)
            subtitles.append(_("Expires on %(date)s", date=formatted_date))

        render_context['subtitles'] = subtitles
        return render_context

    def _phone_get_number_fields(self):
        """ No phone or mobile field is available on sale model. Instead SMS will
        fallback on partner-based computation using ``_mail_get_partner_fields``. """
        return []

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'state' in init_values and self.state == 'sale':
            return self.env.ref('sale.mt_order_confirmed')
        elif 'state' in init_values and self.state == 'sent':
            return self.env.ref('sale.mt_order_sent')
        return super()._track_subtype(init_values)

    # PAYMENT #

    def _force_lines_to_invoice_policy_order(self):
        """Force the qty_to_invoice to be computed as if the invoice_policy
        was set to "Ordered quantities", independently of the product configuration.

        This is needed for the automatic invoice logic, as we want to automatically
        invoice the full SO when it's paid.
        """
        for line in self.order_line:
            if line.state == 'sale':
                # No need to set 0 as it is already the standard logic in the compute method.
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced

    def payment_action_capture(self):
        """ Capture all transactions linked to this sale order. """
        self.ensure_one()
        payment_utils.check_rights_on_recordset(self)

        # In sudo mode to bypass the checks on the rights on the transactions.
        return self.transaction_ids.sudo().action_capture()

    def payment_action_void(self):
        """ Void all transactions linked to this sale order. """
        payment_utils.check_rights_on_recordset(self)

        # In sudo mode to bypass the checks on the rights on the transactions.
        self.authorized_transaction_ids.sudo().action_void()

    def get_portal_last_transaction(self):
        self.ensure_one()
        return self.transaction_ids.sudo()._get_last()

    def _get_order_lines_to_report(self):
        down_payment_lines = self.order_line.filtered(lambda line:
            line.is_downpayment
            and not line.display_type
            and not line._get_downpayment_state()
        )

        def show_line(line):
            if not line.is_downpayment:
                return True
            elif line.display_type and down_payment_lines:
                return True  # Only show the down payment section if down payments were posted
            elif line in down_payment_lines:
                return True  # Only show posted down payments
            else:
                return False

        return self.order_line.filtered(show_line)

    def _get_default_payment_link_values(self):
        self.ensure_one()
        amount_max = self.amount_total - self.amount_paid

        # Always default to the minimum value needed to confirm the order:
        # - order is not confirmed yet
        # - can be confirmed online
        # - we have still not paid enough for confirmation.
        prepayment_amount = self._get_prepayment_required_amount()
        if (
            self.state in ('draft', 'sent')
            and self.require_payment
            and self.currency_id.compare_amounts(prepayment_amount, self.amount_paid) > 0
        ):
            amount = prepayment_amount - self.amount_paid
        else:
            amount = amount_max

        return {
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_invoice_id.id,
            'amount': amount,
            'amount_max': amount_max,
            'amount_paid': self.amount_paid,
        }

    # PORTAL #

    def _has_to_be_signed(self):
        """A sale order has to be signed when:
        - its state is 'draft' or `sent`
        - it's not expired;
        - it requires a signature;
        - it's not already signed.

        Note: self.ensure_one()

        :return: Whether the sale order has to be signed.
        :rtype: bool
        """
        self.ensure_one()
        return (
            self.state in ['draft', 'sent']
            and not self.is_expired
            and self.require_signature
            and not self.signature
        )

    def _has_to_be_paid(self):
        """A sale order has to be paid when:
        - its state is 'draft' or `sent`;
        - it's not expired;
        - it requires a payment;
        - the last transaction's state isn't `done`;
        - the total amount is strictly positive.

        Note: self.ensure_one()

        :return: Whether the sale order has to be paid.
        :rtype: bool
        """
        self.ensure_one()
        transaction = self.get_portal_last_transaction()
        return (
            self.state in ['draft', 'sent']
            and not self.is_expired
            and self.require_payment
            and transaction.state != 'done'
            and self.amount_total > 0
        )

    def _get_portal_return_action(self):
        """ Return the action used to display orders when returning from customer portal. """
        self.ensure_one()
        return self.env.ref('sale.action_quotations_with_onboarding')

    def _get_name_portal_content_view(self):
        """ This method can be inherited by localizations who want to localize the online quotation view. """
        self.ensure_one()
        return 'sale.sale_order_portal_content'

    def _get_name_tax_totals_view(self):
        """ This method can be inherited by localizations who want to localize the taxes displayed on the portal and sale order report. """
        return 'sale.document_tax_totals'

    def _get_report_base_filename(self):
        self.ensure_one()
        return f'{self.type_name} {self.name}'

    #=== CORE METHODS OVERRIDES ===#

    @api.model
    def get_empty_list_help(self, help_msg):
        self = self.with_context(
            empty_list_help_document_name=_("sale order"),
        )
        return super().get_empty_list_help(help_msg)

    def _compute_field_value(self, field):
        if field.name != 'invoice_status' or self.env.context.get('mail_activity_automation_skip'):
            return super()._compute_field_value(field)

        filtered_self = self.filtered(
            lambda so: so.ids
                and (so.user_id or so.partner_id.user_id)
                and so._origin.invoice_status != 'upselling')
        super()._compute_field_value(field)

        upselling_orders = filtered_self.filtered(lambda so: so.invoice_status == 'upselling')
        upselling_orders._create_upsell_activity()

    #=== BUSINESS METHODS ===#

    def _create_upsell_activity(self):
        if not self:
            return

        self.activity_unlink(['sale.mail_act_sale_upsell'])
        for order in self:
            order_ref = order._get_html_link()
            customer_ref = order.partner_id._get_html_link()
            order.activity_schedule(
                'sale.mail_act_sale_upsell',
                user_id=order.user_id.id or order.partner_id.user_id.id,
                note=_("Upsell %(order)s for customer %(customer)s", order=order_ref, customer=customer_ref))

    def _prepare_analytic_account_data(self, prefix=None):
        """ Prepare SO analytic account creation values.

        :param str prefix: The prefix of the to-be-created analytic account name
        :return: `account.analytic.account` creation values
        :rtype: dict
        """
        self.ensure_one()
        name = self.name
        if prefix:
            name = prefix + ": " + self.name
        plan = self.env['account.analytic.plan'].sudo().search([], limit=1)
        if not plan:
            plan = self.env['account.analytic.plan'].sudo().create({
                'name': 'Default',
            })
        return {
            'name': name,
            'code': self.client_order_ref,
            'company_id': self.company_id.id,
            'plan_id': plan.id,
            'partner_id': self.partner_id.id,
        }

    def _create_analytic_account(self, prefix=None):
        """ Create a new analytic account for the given orders.

        :param str prefix: if specified, the account name will be '<prefix>: <so_reference>'.
            If not, the account name will be the Sales Order reference.
        :return: None
        """
        for order in self:
            analytic = self.env['account.analytic.account'].create(order._prepare_analytic_account_data(prefix))
            order.analytic_account_id = analytic

    def _prepare_down_payment_section_line(self, **optional_values):
        """ Prepare the values to create a new down payment section.

        :param dict optional_values: any parameter that should be added to the returned down payment section
        :return: `account.move.line` creation values
        :rtype: dict
        """
        self.ensure_one()
        context = {'lang': self.partner_id.lang}
        down_payments_section_line = {
            'display_type': 'line_section',
            'name': _("Down Payments"),
            'product_id': False,
            'product_uom_id': False,
            'quantity': 0,
            'discount': 0,
            'price_unit': 0,
            'account_id': False,
            **optional_values
        }
        del context
        return down_payments_section_line

    def _get_prepayment_required_amount(self):
        """ Return the minimum amount needed to confirm automatically the quotation.

        Note: self.ensure_one()

        :return: The minimum amount needed to confirm automatically the quotation.
        :rtype: float
        """
        self.ensure_one()
        if self.prepayment_percent == 1.0 or not self.require_payment:
            return self.amount_total
        else:
            return self.currency_id.round(self.amount_total * self.prepayment_percent)

    def _is_confirmation_amount_reached(self):
        """ Return whether `self.amount_paid` is higher than the prepayment required amount.

        Note: self.ensure_one()

        :return: Whether `self.amount_paid` is higher than the prepayment required amount.
        :rtype: bool
        """
        self.ensure_one()
        amount_comparison = self.currency_id.compare_amounts(
            self._get_prepayment_required_amount(), self.amount_paid,
        )
        return amount_comparison <= 0

    def _generate_downpayment_invoices(self):
        """ Generate invoices as down payments for sale order.

        :return: The generated down payment invoices.
        :rtype: recordset of `account.move`
        """
        generated_invoices = self.env['account.move']

        for order in self:
            downpayment_wizard = order.env['sale.advance.payment.inv'].create({
                'sale_order_ids': order,
                'advance_payment_method': 'fixed',
                'fixed_amount': order.amount_paid,
            })
            generated_invoices |= downpayment_wizard._create_invoices(order)

        return generated_invoices

    def _get_product_catalog_order_data(self, products, **kwargs):
        pricelist = self.pricelist_id._get_products_price(
            quantity=1.0,
            products=products,
            currency=self.currency_id,
            date=self.date_order,
            **kwargs,
        )
        return {product_id: {'price': price} for product_id, price in pricelist.items()}

    def _get_product_catalog_record_lines(self, product_ids):
        grouped_lines = defaultdict(lambda: self.env['sale.order.line'])
        for line in self.order_line:
            if line.display_type or line.product_id.id not in product_ids:
                continue
            grouped_lines[line.product_id] |= line
        return grouped_lines

    def _get_product_documents(self):
        self.ensure_one()

        documents = (
            self.order_line.product_id.product_document_ids
            | self.order_line.product_template_id.product_document_ids
        )
        return self._filter_product_documents(documents).sorted()

    def _filter_product_documents(self, documents):
        return documents.filtered(
            lambda document:
                document.attached_on == 'quotation'
                or (self.state == 'sale' and document.attached_on == 'sale_order')
        )

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        """ Update sale order line information for a given product or create a
        new one if none exists yet.
        :param int product_id: The product, as a `product.product` id.
        :return: The unit price of the product, based on the pricelist of the
                 sale order and the quantity selected.
        :rtype: float
        """
        sol = self.order_line.filtered(lambda line: line.product_id.id == product_id)
        if sol:
            if quantity != 0:
                sol.product_uom_qty = quantity
            elif self.state in ['draft', 'sent']:
                price_unit = self.pricelist_id._get_product_price(
                    product=sol.product_id,
                    quantity=1.0,
                    currency=self.currency_id,
                    date=self.date_order,
                    **kwargs,
                )
                sol.unlink()
                return price_unit
            else:
                sol.product_uom_qty = 0
        elif quantity > 0:
            sol = self.env['sale.order.line'].create({
                'order_id': self.id,
                'product_id': product_id,
                'product_uom_qty': quantity,
                'sequence': ((self.order_line and self.order_line[-1].sequence + 1) or 10),  # put it at the end of the order
            })
        return sol.price_unit

    #=== HOOKS ===#

    def add_option_to_order_with_taxcloud(self):
        self.ensure_one()

    def validate_taxes_on_sales_order(self):
        # Override for correct taxcloud computation
        # when using coupon and delivery
        return True

    #=== TOOLING ===#

    def _is_readonly(self):
        """ Return Whether the sale order is read-only or not based on the state or the lock status.

        A sale order is considered read-only if its state is 'cancel' or if the sale order is
        locked.

        :return: Whether the sale order is read-only or not.
        :rtype: bool
        """
        self.ensure_one()
        return self.state == 'cancel' or self.locked

    def _is_paid(self):
        """ Return whether the sale order is paid or not based on the linked transactions.

        A sale order is considered paid if the sum of all the linked transaction is equal to or
        higher than `self.amount_total`.

        :return: Whether the sale order is paid or not.
        :rtype: bool
        """
        self.ensure_one()
        return self.currency_id.compare_amounts(self.amount_paid, self.amount_total) >= 0

    def _get_lang(self):
        self.ensure_one()

        if self.partner_id.lang and not self.partner_id.is_public:
            return self.partner_id.lang

        return self.env.lang
