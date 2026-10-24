from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError

from odoo.addons.l10n_pt_sale.models.l10n_pt_at_series import (
    AT_SERIES_SALES_DOCUMENT_TYPES,
    AT_SERIES_WORKING_DOCUMENT_SAFT_TYPE_MAP,
)


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'l10n.pt.priced.line.mixin']

    def _l10n_pt_get_document(self):
        self.ensure_one()
        return self.order_id

    @api.constrains('tax_ids')
    def _check_l10n_pt_tax_id(self):
        pt_lines = self.filtered(lambda l: not l.display_type and l.company_id.account_fiscal_country_id.code == 'PT')
        if pt_lines.filtered(lambda l: not l.tax_ids):
            raise ValidationError(_("You cannot create a line without VAT tax."))
        # The SAF-T (PT) has room for one tax per line, withholding taxes (negative) aside.
        if pt_lines.filtered(lambda l: len(l.tax_ids.filtered(lambda t: t.amount >= 0)) > 1):
            raise ValidationError(_(
                "A line can only carry one tax, withholding taxes aside. "
                "Split the line to apply several taxes."
            ))

    @api.constrains('price_subtotal')
    def _check_l10n_pt_negative_lines(self):
        if non_positive_lines := self.filtered(
            lambda l: not l.display_type
            and l.company_id.account_fiscal_country_id.code == 'PT'
            and (
                (l.price_total <= 0.0 and not l.is_downpayment)
                or (l.price_unit <= 0.0 and l.is_downpayment)
            )
        ):
            if any(line.price_total < 0.0 for line in non_positive_lines):
                raise ValidationError(_("You cannot create a %s with negative lines on it. "
                                        "To add a discount, add a Line Discount or a Global Discount.", self.order_id.type_name))
            else:
                raise ValidationError(_("%s lines with an amount of 0 are not allowed.", self.order_id.type_name))

    def _prepare_invoice_line(self, **optional_values):
        """
            If the sale order line isn't linked to a sale order which already have a default analytic account,
            this method allows to retrieve the analytic account which is linked to project or task directly linked
            to this sale order line, or the analytic account of the project which uses this sale order line, if it exists.
        """
        values = super()._prepare_invoice_line(**optional_values)
        if self.company_id.account_fiscal_country_id.code == 'PT':
            values['l10n_pt_line_discount'] = self.l10n_pt_line_discount
            # A PT invoice line needs a product (D-4); core leaves down payment lines, and the final
            # invoice's deduction of them, without one
            if self.is_downpayment and not self.display_type and not values.get('product_id'):
                product = self.company_id._l10n_pt_get_down_payment_product()
                values['product_id'] = product.id
                values['product_uom_id'] = values.get('product_uom_id') or product.uom_id.id
        return values


class SaleOrder(models.Model):
    _name = 'sale.order'
    _inherit = ['sale.order', 'l10n.pt.hashed.document.mixin', 'l10n.pt.priced.document.mixin']

    _l10n_pt_date_field = "date_order"
    _l10n_pt_document_type_depends = ('state', 'country_code')

    l10n_pt_at_series_id = fields.Many2one(
        compute='_compute_l10n_pt_at_series_id',
        readonly=False,
        store=True,
        domain="[('active', '=', True), ('document_type', '=', l10n_pt_document_type)]",
    )
    l10n_pt_document_type = fields.Selection(selection_add=AT_SERIES_SALES_DOCUMENT_TYPES)
    quotation_id = fields.Many2one(
        comodel_name='sale.order',
        string="Quotation",
        copy=False,
        ondelete='set null',
        help="The quotation from which this sale order was created.",
    )
    sales_order_ids = fields.One2many(
        comodel_name='sale.order',
        inverse_name='quotation_id',
        string="Sale Order",
        copy=False,
        help="Sale orders created from this quotation."
    )
    sales_order_count = fields.Integer(compute="_compute_related_so_count", string='Sale Order Count')

    ####################################
    # COMPUTE, INVERSE AND CONSTRAINS
    ####################################

    @api.depends('state', 'company_id')
    def _compute_l10n_pt_at_series_id(self):
        # An issued document keeps the series it was issued under, even once that series expires.
        # Anything not yet issued has to end up on a series that is still valid, or the constraint
        # below rejects it -- which used to deadlock order creation on the day the series that the
        # previous order used reached its end date. `.active` is False on an empty series too, so
        # orders with no series yet are covered by the same test.
        sale_orders = self.filtered(lambda so: (
            so.state != 'cancel'
            and not so.l10n_pt_document_number
            and not so.l10n_pt_at_series_id.active
        ))
        # Match on the document type rather than on `state`: a quotation confirmed in place (portal
        # sign & pay) is in state 'sale' but keeps its quotation type and series, which a sales
        # order must not inherit. Either mismatch is rejected by `_check_l10n_pt_at_series_id`.
        for (company, document_type), orders in sale_orders.grouped(lambda o: (o.company_id, o.l10n_pt_document_type)).items():
            if not document_type:
                continue
            last_order = self.env['sale.order'].search([
                ('company_id', '=', company.id),
                ('l10n_pt_document_type', '=', document_type),
                ('l10n_pt_at_series_id', '!=', False),
                ('l10n_pt_at_series_id.active', '=', True),
            ], order='id desc', limit=1)
            orders.l10n_pt_at_series_id = last_order.l10n_pt_at_series_id or self.env['l10n_pt.at.series'].search([
                *self.env['l10n_pt.at.series']._l10n_pt_company_domain(company),
                ('active', '=', True),
                ('document_type', '=', document_type),
            ], limit=1)

    @api.depends('sales_order_ids')
    def _compute_related_so_count(self):
        for order in self:
            order.sales_order_count = len(order.sales_order_ids)

    @api.constrains('l10n_pt_at_series_id')
    def _check_l10n_pt_at_series_id(self):
        # A cancelled order that was never issued has no document type: it is not an AT document,
        # and its series may never have been computed.
        orders = self.filtered(lambda so: so.country_code == 'PT' and so.l10n_pt_document_type)
        if missing_series := orders.filtered(lambda so: not so.l10n_pt_at_series_id):
            document_types = dict(self._fields['l10n_pt_document_type']._description_selection(self.env))
            missing_types = [document_type for document_type in dict.fromkeys(missing_series.mapped('l10n_pt_document_type')) if document_type]
            # A quotation's form asks for its own series; this is reached from a form on confirmation,
            # where the sales order is created server-side. Open the missing series, prefilled.
            raise RedirectWarning(
                _("There is no AT series for the document type %(document_type)s. "
                  "Create a new series or view existing series via the Accounting Settings.",
                  document_type=" and ".join(document_types[document_type] for document_type in missing_types)),
                {
                    'name': _('New AT Series'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'l10n_pt.at.series',
                    'view_mode': 'form',
                    'context': {
                        'l10n_pt_series_document_types': missing_types,
                        'default_company_id': missing_series.company_id[:1].id,
                    },
                    'target': 'new',
                },
                _('Add an AT Series'),
            )
        # Only documents still to be issued need a currently valid series: one already issued keeps
        # the series it was issued under, which will expire in the normal course of things.
        to_issue = orders.filtered(lambda so: not so.l10n_pt_document_number)
        super(SaleOrder, to_issue)._check_l10n_pt_at_series_id()

    ####################################
    # OVERRIDES
    ####################################

    def action_quotation_send(self):
        if not self.env.context.get('has_reprint_reason'):
            self._l10n_pt_issue()
            reprint = False
            for order in self.filtered(lambda o: o.country_code == 'PT'):
                if order.l10n_pt_print_version:
                    reprint = True
            if self.env.context.get('check_document_layout') and reprint:
                return {
                    'name': _('Reprint Reason'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'l10n_pt.reprint.reason',
                    'view_mode': 'form',
                    'target': 'new',
                }
        return super().action_quotation_send()

    def action_preview_sale_order(self):
        self.ensure_one()
        self._l10n_pt_issue()
        return super().action_preview_sale_order()

    def _l10n_pt_issued_orders(self):
        return self.filtered(lambda o: o.country_code == 'PT' and o.l10n_pt_document_number)

    def action_cancel(self):
        # An issued order is cancelled with a reason (Portaria 302/2016 4.3.4.3.3), asked for before
        # anything changes: the wizard writes it, then cancels.
        if self._l10n_pt_issued_orders().filtered(lambda o: not o.l10n_pt_cancel_reason):
            action = self.env['ir.actions.actions']._for_xml_id('l10n_pt_certification.action_l10n_pt_cancel')
            action['context'] = {
                'model': 'sale.order',
                'order_ids': self.ids,
            }
            return action
        # PT orders are locked once they are hashed, but the AT still requires them to be cancellable.
        # Other countries keep the standard "cannot cancel a locked order" guard.
        self.filtered(lambda o: o.country_code == 'PT').action_unlock()
        res = super().action_cancel()
        self._l10n_pt_issued_orders().action_lock()
        return res

    def _action_cancel(self):
        # Every path to a cancelled order comes here, the mass cancel and RPC included.
        if self._l10n_pt_issued_orders().filtered(lambda o: not o.l10n_pt_cancel_reason):
            raise UserError(_("An issued Portuguese quotation or sales order can only be cancelled with a reason."))
        res = super()._action_cancel()
        self._l10n_pt_record_cancellation()
        return res

    def action_draft(self):
        if self._l10n_pt_issued_orders().filtered(lambda o: o.state == 'cancel'):
            raise UserError(_("A cancelled Portuguese quotation or sales order that was issued cannot be reset to draft."))
        return super().action_draft()

    def _create_invoices(self, grouped=False, final=False, date=None):
        # The invoice references the orders it invoices, so those are issued first; no other order
        # is touched.
        self.filtered(lambda so: so.state == 'sale')._l10n_pt_issue()
        return super()._create_invoices(grouped=grouped, final=final, date=date)

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.country_code == 'PT':
            invoice_vals['l10n_pt_global_discount'] = self.l10n_pt_global_discount
        return invoice_vals

    ####################################
    # ACTIONS
    ####################################

    def action_l10n_pt_create_sales_order(self):
        self.ensure_one()
        self._l10n_pt_issue()

        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['context'] = dict(self.env.context)
        action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
        sales_order = self.with_context(create_sales_order=True).copy(default={'quotation_id': self.id, 'locked': False})
        sales_order.action_confirm()
        action['res_id'] = sales_order.id
        return action

    def action_view_sale_orders(self):
        self.ensure_one()
        sale_orders = self.sales_order_ids
        result = self.env['ir.actions.act_window']._for_xml_id('sale.action_orders')
        if len(sale_orders) > 1:
            result['domain'] = [('id', 'in', sale_orders.ids)]
        elif len(sale_orders) == 1:
            result['views'] = [(self.env.ref('sale.view_order_form', False).id, 'form')]
            result['res_id'] = sale_orders.id
        return result

    def action_view_origin_quotation(self):
        self.ensure_one()
        result = self.env['ir.actions.act_window']._for_xml_id('sale.action_quotations')
        result['views'] = [(self.env.ref('sale.view_order_form', False).id, 'form')]
        result['res_id'] = self.quotation_id.id
        return result

    ####################################
    # AT DOCUMENT HOOKS
    ####################################

    def _l10n_pt_get_document_date(self):
        self.ensure_one()
        return self.date_order

    def _l10n_pt_get_document_type(self):
        self.ensure_one()
        if self.state == 'sale' or self.env.context.get('create_sales_order'):
            return 'sales_order'
        if self.state in ('draft', 'sent'):
            return 'quotation'
        # A cancelled order that was never issued is not an AT document at all.
        return False

    def _l10n_pt_get_lines(self):
        self.ensure_one()
        return self.order_line

    def _l10n_pt_document_is_open(self):
        # A quotation stays editable until it is cancelled, unlike a move or a payment.
        self.ensure_one()
        return self.state != 'cancel'

    def _l10n_pt_get_gross_total(self):
        # In EUR whatever the order's currency, as the QR code's `O:` (Despacho 8632/2014 2.1.7).
        self.ensure_one()
        return self._l10n_pt_amount_to_eur(self.amount_total)

    def _l10n_pt_get_saft_doc_type(self):
        self.ensure_one()
        return AT_SERIES_WORKING_DOCUMENT_SAFT_TYPE_MAP[self.l10n_pt_document_type]

    def _l10n_pt_protected_fields(self):
        return super()._l10n_pt_protected_fields() + ['l10n_pt_at_series_id']

    def _get_integrity_hash_fields(self):
        if not self._l10n_pt_country_ok():
            return []
        return ['date_order', 'l10n_pt_hashed_on', 'name', 'l10n_pt_document_number', 'amount_total', 'partner_id', 'company_id', 'sale_order_option_ids']

    @api.model
    def _l10n_pt_find_last_hashed(self, at_series):
        return self.sudo().search([
            ('l10n_pt_at_series_id', '=', at_series.id),
            ('l10n_pt_inalterable_hash', '!=', False),
        ], order='l10n_pt_sequence_number desc', limit=1)

    def _l10n_pt_get_unhashed_records(self, at_series):
        # Numbering is the act of issuing an order (`_l10n_pt_issue`): drafts nobody issued stay
        # out of the chain, unnumbered, unsigned and editable.
        return self.sudo().search([
            ('l10n_pt_at_series_id', '=', at_series.id),
            ('l10n_pt_document_number', '!=', False),
            ('l10n_pt_inalterable_hash', '=', False),
        ], order='l10n_pt_sequence_number')

    def _l10n_pt_post_hash_hook(self):
        self.locked = True

    def _l10n_pt_document_label(self, at_series):
        if at_series.document_type == 'sales_order':
            return 'sales order', 'sales orders', self.env._('Sales Orders')
        return 'quotation', 'quotations', self.env._('Quotations')

    def _l10n_pt_issue(self):
        """
        Issue the orders: number, sign and lock them in one step.

        AT wants a document signed as soon as it is numbered, and frozen from then on (Despacho
        8632/2014 2.1.1 and 1.11), so no order may exist numbered but unsigned. Called wherever an
        order first reaches the customer or another document: print, send, preview, confirmation
        into a sales order, invoicing.
        """
        self._l10n_pt_compute_missing_hashes()

    def _l10n_pt_compute_missing_hashes(self, company=None):
        """
        Number the orders given, then sign them along with every other order of their series that
        was issued but is not signed yet.
        """
        to_issue = self.filtered(lambda so: (
            so.country_code == 'PT'
            and so.l10n_pt_document_type
            and not so.l10n_pt_document_number
        ))
        to_issue._check_l10n_pt_dates()
        to_issue._check_l10n_pt_at_series_id()
        to_issue._check_l10n_pt_lines_exemption_reasons()
        to_issue._set_l10n_pt_document_number()
        return super()._l10n_pt_compute_missing_hashes(company=company)

    ####################################
    # QR CODE
    ####################################

    def _l10n_pt_qr_get_totals(self):
        self.ensure_one()
        return self._l10n_pt_qr_format_amount(self.amount_tax), self._l10n_pt_qr_format_amount(self.amount_total)

    def _l10n_pt_get_tax_details_by_region(self):
        return self._l10n_pt_split_not_subject_bases(super()._l10n_pt_get_tax_details_by_region())
