from odoo import Command, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.fields import Domain

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

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._l10n_pt_name_product_in_label()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if {'name', 'product_id'} & vals.keys():
            self._l10n_pt_name_product_in_label()
        return res

    def _l10n_pt_is_labelled(self):
        # EXTENDS l10n_pt_certification
        # A down payment is described in words ("Down payment of ...").
        self.ensure_one()
        return (
            not self.display_type
            and bool(self.product_id)
            and not self.is_downpayment
            and self.order_id._l10n_pt_country_ok()
        )

    def _l10n_pt_get_label_lang(self):
        # EXTENDS l10n_pt_certification
        # As `_compute_name`: the order's language.
        self.ensure_one()
        return self.order_id._get_lang()

    def _compute_name(self):
        # EXTENDS sale
        # A Portuguese order names its products by their name on Portuguese documents, any other order by
        # their name, whichever company is active.
        pt_lines = self.filtered(lambda line: line.company_id.account_fiscal_country_id.code == 'PT')
        super(SaleOrderLine, (self - pt_lines).with_context(l10n_pt_frozen_product_name=False))._compute_name()
        super(SaleOrderLine, pt_lines.with_context(l10n_pt_frozen_product_name=True))._compute_name()

    @api.constrains('tax_ids')
    def _check_l10n_pt_tax_id(self):
        pt_lines = self.filtered(lambda line: not line.display_type and line.company_id.account_fiscal_country_id.code == 'PT')
        if pt_lines.filtered(lambda line: not line.tax_ids):
            raise ValidationError(self.env._("You cannot create a line without VAT tax."))
        # The SAF-T (PT) has room for one tax per line, withholding taxes (negative) aside.
        if pt_lines.filtered(lambda line: len(line.tax_ids.filtered(lambda t: t.amount >= 0)) > 1):
            raise ValidationError(self.env._(
                "A line can only carry one tax, withholding taxes aside. "
                "Split the line to apply several taxes.",
            ))

    @api.constrains('price_subtotal')
    def _check_l10n_pt_negative_lines(self):
        if non_positive_lines := self.filtered(
            lambda line: not line.display_type
            and line.company_id.account_fiscal_country_id.code == 'PT'
            and (
                (line.price_total <= 0.0 and not line.is_downpayment)
                or (line.price_unit <= 0.0 and line.is_downpayment)
            ),
        ):
            if any(line.price_total < 0.0 for line in non_positive_lines):
                raise ValidationError(self.env._(
                    "You cannot create a %s with negative lines on it. "
                    "To add a discount, add a Line Discount or a Global Discount.",
                    non_positive_lines[0].order_id.type_name,
                ))
            raise ValidationError(self.env._(
                "%s lines with an amount of 0 are not allowed.", non_positive_lines[0].order_id.type_name,
            ))

    def _prepare_invoice_line(self, **optional_values):
        values = super()._prepare_invoice_line(**optional_values)
        if self.company_id.account_fiscal_country_id.code == 'PT':
            values['l10n_pt_line_discount'] = self.l10n_pt_line_discount
            # A PT invoice line needs a product; core leaves down payment lines, and the final
            # invoice's deduction of them, without one.
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
        index='btree_not_null',
        ondelete='set null',
        help="The quotation from which this sales order was created.",
    )
    sales_order_ids = fields.One2many(
        comodel_name='sale.order',
        inverse_name='quotation_id',
        string="Sales Orders",
        copy=False,
        help="Sales orders created from this quotation.",
    )
    sales_order_count = fields.Integer(compute="_compute_sales_order_count", string="Sales Order Count")
    l10n_pt_ordered = fields.Boolean(
        string="Ordered",
        compute='_compute_l10n_pt_ordered',
        search='_search_l10n_pt_ordered',
        help="A sales order was confirmed from this quotation, and is not cancelled.",
    )

    ####################################
    # COMPUTE, INVERSE AND CONSTRAINS
    ####################################

    @api.depends('state', 'company_id', 'l10n_pt_document_type')
    def _compute_l10n_pt_at_series_id(self):
        # An issued document keeps the series it was issued under, even once that series expires.
        # Anything not yet issued has to end up on a series that is still valid, or the constraint
        # below rejects it. `.active` is False on an empty series too, so orders with no series yet
        # are covered by the same test. A quotation confirmed in place
        # before it was issued becomes a sales order, so its quotation series no longer fits either.
        sale_orders = self.filtered(lambda so: (
            so.state != 'cancel'
            and not so.l10n_pt_document_number
            and (
                not so.l10n_pt_at_series_id.active
                or so.l10n_pt_at_series_id.document_type != so.l10n_pt_document_type
            )
        ))
        # Match on the document type rather than on `state`: an issued quotation confirmed in place
        # (core's `action_confirm` called directly) is in state 'sale' but keeps its quotation type and
        # series, which a sales order must not inherit. Either mismatch is rejected by
        # `_check_l10n_pt_at_series_id`.
        for (company, document_type), orders in sale_orders.grouped(lambda o: (o.company_id, o.l10n_pt_document_type)).items():
            if not document_type:
                continue
            # The series' own type too: the orders being computed already have their new type, and
            # would otherwise hand back the quotation series they are leaving.
            last_order = self.env['sale.order'].search([
                ('company_id', '=', company.id),
                ('l10n_pt_document_type', '=', document_type),
                ('l10n_pt_at_series_id.document_type', '=', document_type),
                ('l10n_pt_at_series_id.active', '=', True),
            ], order='id desc', limit=1)
            orders.l10n_pt_at_series_id = last_order.l10n_pt_at_series_id or self.env['l10n_pt.at.series'].search([
                *self.env['l10n_pt.at.series']._l10n_pt_company_domain(company),
                ('active', '=', True),
                ('document_type', '=', document_type),
            ], limit=1)

    @api.depends('sales_order_ids')
    def _compute_sales_order_count(self):
        for order in self:
            order.sales_order_count = len(order.sales_order_ids)

    @api.depends('sales_order_ids.state')
    def _compute_l10n_pt_ordered(self):
        for order in self:
            order.l10n_pt_ordered = bool(order._l10n_pt_live_sales_orders())

    def _search_l10n_pt_ordered(self, operator, value):
        if operator != 'in':
            return NotImplemented
        ordered = Domain('sales_order_ids', 'any', [('state', '!=', 'cancel')])
        if True in value and False in value:
            return Domain.TRUE
        return ordered if True in value else ~ordered

    @api.constrains('l10n_pt_at_series_id')
    def _check_l10n_pt_at_series_id(self):
        # A cancelled order that was never issued has no document type: it is not an AT document,
        # and its series may never have been computed.
        orders = self.filtered(lambda so: so.country_code == 'PT' and so.l10n_pt_document_type)
        if missing_series := orders.filtered(lambda so: not so.l10n_pt_at_series_id):
            document_types = dict(self._fields['l10n_pt_document_type']._description_selection(self.env))
            missing_types = list(dict.fromkeys(missing_series.mapped('l10n_pt_document_type')))
            # A quotation's form asks for its own series; this is reached from a form on confirmation,
            # where the sales order is created server-side. Open the missing series, prefilled.
            raise RedirectWarning(
                self.env._(
                    "There is no AT series for the document type %(document_type)s. "
                    "Create a new series or view existing series via the Accounting Settings.",
                    document_type=[document_types[document_type] for document_type in missing_types],
                ),
                {
                    'name': self.env._('New AT Series'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'l10n_pt.at.series',
                    'view_mode': 'form',
                    'context': {
                        'l10n_pt_series_document_types': missing_types,
                        'default_company_id': missing_series.company_id[:1].id,
                    },
                    'target': 'new',
                },
                self.env._('Add an AT Series'),
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
            if self.env.context.get('check_document_layout') and any(
                order.country_code == 'PT' and order.l10n_pt_print_version for order in self
            ):
                return {
                    'name': self.env._('Reprint Reason'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'l10n_pt.reprint.reason',
                    'view_mode': 'form',
                    'target': 'new',
                }
        return super().action_quotation_send()

    def write(self, vals):
        # A quotation is sent as the document it is, so no quotation is ever sent unissued, however it
        # is marked sent: the send wizard (`mark_so_as_sent`), Mark as Sent, a pending online payment.
        if vals.get('state') == 'sent':
            self.filtered(lambda o: o.state == 'draft')._l10n_pt_issue()
        # Issuing locks an order, and the lock is what keeps its lines (core's `_get_protected_fields`):
        # an issued order is never unlocked, from the form (no button) or otherwise.
        if 'locked' in vals and not vals['locked'] and self._l10n_pt_issued_orders().filtered('locked'):
            raise UserError(self.env._("An issued Portuguese quotation or sales order cannot be unlocked."))
        return super().write(vals)

    def _validate_order(self):
        # EXTENDS sale
        # The customer accepts the quotation on its portal page (signature, no payment due), or checks
        # out a cart: confirmed as from the form (`action_l10n_pt_confirm`).
        to_copy = self.filtered(lambda o: not o._l10n_pt_confirms_in_place())
        super(SaleOrder, self - to_copy)._validate_order()
        for quotation in to_copy:
            quotation.with_context(send_email=True)._l10n_pt_create_sales_order()

    def _l10n_pt_issued_orders(self):
        return self.filtered(lambda o: o.country_code == 'PT' and o.l10n_pt_document_number)

    def action_cancel(self):
        # An issued order is cancelled with a reason (Portaria 302/2016 4.3.4.3.3), asked for before
        # anything changes: the wizard writes it, then cancels.
        if self._l10n_pt_issued_orders().filtered(lambda o: not o.l10n_pt_cancel_reason):
            action = self.env['ir.actions.actions']._for_xml_id('l10n_pt_certification.action_l10n_pt_cancel')
            action['context'] = {
                'active_model': 'sale.order',
                'active_ids': self.ids,
            }
            return action
        # Issued PT orders are locked, and never unlocked, but the AT still requires them to be
        # cancellable: they skip core's "cannot cancel a locked order" guard, which other countries keep.
        # A PT order not issued has no Unlock button: it is unlocked to be cancelled.
        pt_orders = self.filtered(lambda o: o.country_code == 'PT')
        issued = pt_orders._l10n_pt_issued_orders()
        (pt_orders - issued).action_unlock()
        issued._action_cancel()
        return super(SaleOrder, self - issued).action_cancel()

    def _action_cancel(self):
        # Every path to a cancelled order comes here, the mass cancel and RPC included.
        if self._l10n_pt_issued_orders().filtered(lambda o: not o.l10n_pt_cancel_reason):
            raise UserError(self.env._("An issued Portuguese quotation or sales order can only be cancelled with a reason."))
        res = super()._action_cancel()
        self._l10n_pt_record_cancellation()
        return res

    def action_draft(self):
        if self._l10n_pt_issued_orders().filtered(lambda o: o.state == 'cancel'):
            raise UserError(self.env._("A cancelled Portuguese quotation or sales order that was issued cannot be reset to draft."))
        return super().action_draft()

    def _create_invoices(self, grouped=False, final=False, date=None):
        # The invoice references the orders it invoices, so those are issued first; no other order
        # is touched.
        self.filtered(lambda so: so.state == 'sale')._l10n_pt_issue()
        return super()._create_invoices(grouped=grouped, final=final, date=date)

    def _prepare_confirmation_values(self):
        values = super()._prepare_confirmation_values()
        # An issued quotation confirmed in place (core's `action_confirm` called directly, e.g. over
        # RPC) keeps the date it was signed with.
        if any(order._l10n_pt_country_ok() and order.l10n_pt_inalterable_hash for order in self):
            values.pop('date_order', None)
        return values

    def _has_to_be_signed(self):
        # A quotation confirmed into a sales order is accepted: it is not signed, paid or confirmed again.
        return super()._has_to_be_signed() and not self.sales_order_ids

    def _has_to_be_paid(self):
        return super()._has_to_be_paid() and not self.sales_order_ids

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.country_code == 'PT':
            invoice_vals['l10n_pt_global_discount'] = self.l10n_pt_global_discount
        return invoice_vals

    def _get_invoice_grouping_keys(self):
        # An invoice has one global discount, applied to all its lines.
        return super()._get_invoice_grouping_keys() + ['l10n_pt_global_discount']

    ####################################
    # ACTIONS
    ####################################

    def action_l10n_pt_confirm(self):
        """
        The form's Confirm: a quotation nobody issued yet is confirmed in place and the form reloads on
        it; an issued one opens the new sales order confirmed from it. One already confirmed into a
        sales order opens that sales order instead.
        """
        self.ensure_one()
        if not (sales_order := self._l10n_pt_live_sales_orders()[-1:]):
            if self._l10n_pt_confirms_in_place():
                # What confirming returns (a wizard, a notification) is the form's to show.
                return self.action_confirm()
            sales_order = self._l10n_pt_create_sales_order()
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['context'] = dict(self.env.context)
        action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
        action['res_id'] = sales_order.id
        return action

    def _l10n_pt_confirms_in_place(self):
        """
        Whether confirming the order makes it the sales order itself: any order outside Portugal, and a
        PT quotation nobody issued yet (a draft: a sent quotation is always issued, see `write`), whose
        document type and AT series then become those of a sales order. An issued quotation was
        presented to the customer as it is: it stays so, and a new sales order is confirmed from it
        (`_l10n_pt_create_sales_order`).
        """
        self.ensure_one()
        return not self._l10n_pt_country_ok() or not self.l10n_pt_document_number

    def _l10n_pt_create_sales_order(self, transactions=None):
        """
        Confirm an issued quotation as a PT company does: the quotation stays as it was issued, and
        a new sales order is created from it and confirmed. ``transactions`` paying the quotation are
        moved to the sales order before it is confirmed: they pay for it.
        """
        self.ensure_one()
        if sales_orders := self._l10n_pt_live_sales_orders():
            # One quotation, one order: a repeat order is a duplicated quotation.
            raise UserError(self.env._(
                "The quotation %(quotation)s was already confirmed into the sales order %(sales_order)s.",
                quotation=self.l10n_pt_document_number or self.name,
                sales_order=sales_orders.mapped(lambda so: so.l10n_pt_document_number or so.name),
            ))
        self._l10n_pt_issue()
        sales_order = self.with_context(l10n_pt_create_sales_order=True).copy(default={
            'quotation_id': self.id,
            'locked': False,
            # The customer accepted the order by signing its quotation: core keeps the signature on the
            # order, and prints it there. None of these is covered by the AT signature.
            'signature': self.signature,
            'signed_by': self.signed_by,
            'signed_on': self.signed_on,
        })
        # The copy is a sales order from its creation: its document type and series are computed
        # under the context that says so, which goes no further than the copy.
        sales_order.flush_recordset(['l10n_pt_document_type', 'l10n_pt_at_series_id'])
        sales_order = sales_order.with_env(self.env)
        if transactions:
            transactions.sale_order_ids = [Command.set(sales_order.ids)]
        sales_order.action_confirm()
        # Presented and accepted: a quotation issued while a draft (printed, shared) is no longer one.
        self.filtered(lambda o: o.state == 'draft').write({'state': 'sent'})
        return sales_order

    def _l10n_pt_is_unissued_document(self):
        """Whether the order is a PT document (a quotation or sales order) not issued yet."""
        self.ensure_one()
        return self.country_code == 'PT' and bool(self.l10n_pt_document_type) and not self.l10n_pt_document_number

    def _l10n_pt_live_sales_orders(self):
        """The sales orders confirmed from this quotation and not cancelled since."""
        self.ensure_one()
        return self.sales_order_ids.filtered(lambda so: so.state != 'cancel')

    def action_view_sale_orders(self):
        self.ensure_one()
        sale_orders = self.sales_order_ids
        result = self.env['ir.actions.act_window']._for_xml_id('sale.action_orders')
        if len(sale_orders) > 1:
            result['domain'] = [('id', 'in', sale_orders.ids)]
        elif len(sale_orders) == 1:
            result['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            result['res_id'] = sale_orders.id
        return result

    def action_view_origin_quotation(self):
        self.ensure_one()
        result = self.env['ir.actions.act_window']._for_xml_id('sale.action_quotations')
        result['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
        result['res_id'] = self.quotation_id.id
        return result

    ####################################
    # AT DOCUMENT HOOKS
    ####################################

    def _l10n_pt_get_document_date(self):
        self.ensure_one()
        return self.date_order

    def _l10n_pt_get_responsible_issuer(self):
        # When no person issues the order (the customer accepting or paying online): the issuer of its
        # quotation, who presented it, else its salesperson.
        self.ensure_one()
        return self._l10n_pt_first_person(self.quotation_id.l10n_pt_issue_user_id | self.user_id)

    def _l10n_pt_get_document_type(self):
        self.ensure_one()
        if self.state == 'sale' or self.env.context.get('l10n_pt_create_sales_order'):
            return 'sales_order'
        if self.state in ('draft', 'sent'):
            return 'quotation'
        # A cancelled order that was never issued is not an AT document at all.
        return False

    def _l10n_pt_get_lines(self):
        return self.order_line

    def _l10n_pt_name_products_in_labels(self):
        # EXTENDS l10n_pt_certification
        self._l10n_pt_get_lines()._l10n_pt_name_product_in_label()

    def _l10n_pt_get_product_templates(self):
        # EXTENDS l10n_pt_certification
        return self.order_line.product_id.product_tmpl_id

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

    def _get_integrity_hash_fields(self):
        if hash_fields := super()._get_integrity_hash_fields():
            return [*hash_fields, 'date_order', 'amount_total', 'partner_id', 'company_id']
        return hash_fields

    def _l10n_pt_post_hash_hook(self):
        self.locked = True

    def _l10n_pt_document_label(self, at_series):
        if at_series.document_type == 'sales_order':
            return self.env._("sales order"), self.env._("sales orders"), self.env._("Sales Orders")
        return self.env._("quotation"), self.env._("quotations"), self.env._("Quotations")

    def _l10n_pt_issue(self):
        """
        Issue the orders: number, sign and lock them in one step.

        AT wants a document signed as soon as it is numbered, and frozen from then on (Despacho
        8632/2014 2.1.1 and 1.11), so no order may exist numbered but unsigned. Called wherever an
        order first reaches the customer or another document: print, send, share, confirmation into a
        sales order, invoicing. Not the salesperson's Preview, nor the
        customer's portal page.
        """
        # Only PT orders: signing no record at all would sign every series of the active company.
        if pt_orders := self.filtered(lambda o: o.country_code == 'PT'):
            pt_orders._l10n_pt_compute_missing_hashes()

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
