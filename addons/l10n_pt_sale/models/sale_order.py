from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, ValidationError
from odoo.tools import float_repr

from odoo.addons.l10n_pt_sale.models.l10n_pt_at_series import (
    AT_SERIES_SALES_DOCUMENT_TYPES,
)

AT_SERIES_WORKING_DOCUMENT_SAFT_TYPE_MAP = {
    'quotation': 'OR',
    'sales_order': 'NE',
}


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'l10n.pt.priced.line.mixin']

    def _l10n_pt_get_document(self):
        self.ensure_one()
        return self.order_id

    @api.constrains('tax_ids')
    def _check_l10n_pt_tax_id(self):
        if self.filtered(
            lambda l: not l.display_type
            and l.company_id.account_fiscal_country_id.code == 'PT'
            and not l.tax_ids
        ):
            raise ValidationError(_("You cannot create a line without VAT tax."))

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
        domain="[('active', '=', True), ('document_type', 'in', ('quotation', 'sales_order'))]",
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
        for (company, state_sale), orders in sale_orders.grouped(lambda o: (o.company_id, o.state == 'sale')).items():
            domain = [
                ('company_id', '=', company.id),
                ('l10n_pt_at_series_id', '!=', False),
                ('l10n_pt_at_series_id.active', '=', True),
            ]
            if not state_sale and not self.env.context.get('create_sales_order'):
                domain.append(('state', 'in', ('draft', 'sent')))
            else:
                domain.append(('state', '=', 'sale'))

            last_order = self.env['sale.order'].search(domain, order='id desc', limit=1)
            orders.l10n_pt_at_series_id = last_order.l10n_pt_at_series_id or self.env['l10n_pt.at.series'].search([
                *self.env['l10n_pt.at.series']._l10n_pt_company_domain(company),
                ('active', '=', True),
                ('document_type', 'in', self._l10n_pt_series_document_types()),
            ], limit=1)

    @api.depends('sales_order_ids')
    def _compute_related_so_count(self):
        for order in self:
            order.sales_order_count = len(order.sales_order_ids)

    @api.constrains('l10n_pt_at_series_id')
    def _check_l10n_pt_at_series_id(self):
        orders = self.filtered(lambda so: so.country_code == 'PT')
        if missing_series := orders.filtered(lambda so: not so.l10n_pt_at_series_id):
            document_types = dict(self._fields['l10n_pt_document_type']._description_selection(self.env))
            raise RedirectWarning(
                _("There is no AT series for the document type %(document_type)s. "
                  "Create a new series or view existing series via the Accounting Settings.",
                  document_type=" and ".join(
                      document_types[document_type]
                      for document_type in dict.fromkeys(missing_series.mapped('l10n_pt_document_type'))
                      if document_type
                  )),
                {
                    'name': _('AT Series'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'l10n_pt.at.series',
                    'view_mode': 'list',
                    'views': [[self.env.ref('l10n_pt_certification.view_l10n_pt_at_series_tree').id, 'list']],
                    'context': {'search_default_sales_document_types': 1},
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
            self._check_l10n_pt_dates()
            self._check_l10n_pt_at_series_id()
            self._set_l10n_pt_document_number()
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
        self._check_l10n_pt_dates()
        self._check_l10n_pt_at_series_id()
        self._set_l10n_pt_document_number()
        if self.state == 'sale':
            self._l10n_pt_compute_missing_hashes()
        return super().action_preview_sale_order()

    def action_cancel(self):
        # PT orders are locked once they are hashed, but the AT still requires them to be cancellable.
        # Other countries keep the standard "cannot cancel a locked order" guard.
        self.filtered(lambda o: o.country_code == 'PT').action_unlock()
        return super().action_cancel()

    def _action_cancel(self):
        res = super()._action_cancel()
        pt_orders = self.filtered(lambda o: o.country_code == 'PT')
        if not pt_orders:
            return res
        # The AT requires a reason to be recorded for every cancelled document.
        action = self.env['ir.actions.actions']._for_xml_id('l10n_pt_certification.action_l10n_pt_cancel')
        action['context'] = {
            'model': 'sale.order',
            'order_ids': pt_orders.ids,
        }
        return action

    def _create_invoices(self, grouped=False, final=False, date=None):
        if self.env.company.account_fiscal_country_id.code == 'PT':
            self._check_l10n_pt_dates()
            orders = self.sudo().search([
                ('company_id', '=', self.env.company.id),
                ('l10n_pt_inalterable_hash', '=', False),
                ('l10n_pt_document_number', '=', False),
            ], order='date_order')
            orders._check_l10n_pt_at_series_id()
            orders.filtered(lambda so: so.state == 'sale')._set_l10n_pt_document_number()
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
        self._check_l10n_pt_dates()
        self._check_l10n_pt_at_series_id()
        self._set_l10n_pt_document_number()

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
        self.ensure_one()
        return self.amount_total

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
        ], order='l10n_pt_document_number desc', limit=1)

    def _l10n_pt_get_unhashed_records(self, at_series):
        return self.sudo().search([
            ('l10n_pt_at_series_id', '=', at_series.id),
            ('l10n_pt_inalterable_hash', '=', False),
        ], order='l10n_pt_document_number')

    def _l10n_pt_post_hash_hook(self):
        self.locked = True

    def _l10n_pt_compute_missing_hashes(self, company=None):
        """
        Compute the hash/atcud for all records that do not have one yet
        (because they were not printed/previewed yet)
        """
        # When printing an order before previewing or creating an invoice from it, at series may not be set yet
        self._check_l10n_pt_at_series_id()
        self._set_l10n_pt_document_number()
        return super()._l10n_pt_compute_missing_hashes(company=company)

    ####################################
    # QR CODE
    ####################################

    def _l10n_pt_qr_add_tax_details(self, qr_code_dict, tax_letter):
        self.ensure_one()
        details_by_tax_group = self._l10n_pt_get_details_by_tax_category()
        if details_by_tax_group.get('E'):
            qr_code_dict[f'{tax_letter}2:'] = f"{details_by_tax_group.get('E')['base']}*"
        for i, tax_category in enumerate(('R', 'I', 'N')):
            if details_by_tax_group.get(tax_category):
                qr_code_dict[f'{tax_letter}{i * 2 + 3}:'] = f"{details_by_tax_group.get(tax_category)['base']}*"
                qr_code_dict[f'{tax_letter}{i * 2 + 4}:'] = f"{details_by_tax_group.get(tax_category)['vat']}*"

    def _l10n_pt_qr_get_totals(self):
        self.ensure_one()
        return self._l10n_pt_qr_format_amount(self.amount_tax), self._l10n_pt_qr_format_amount(self.amount_total)

    def _l10n_pt_qr_format_amount(self, amount):
        """
        Convert amount to EUR based on the rate of the order's date.
        Format amount to 2 decimals as per SAF-T (PT) requirements.
        """
        self.ensure_one()
        amount_eur = self.currency_id._convert(amount, self.env.ref('base.EUR'), self.company_id, self.date_order)
        return float_repr(amount_eur, 2)

    def _l10n_pt_get_details_by_tax_category(self):
        """
        :return: {tax_category : {'base': base, 'vat': vat}}
        """
        self.ensure_one()
        res = {}
        tax_groups = self.tax_totals['subtotals'][0]['tax_groups']
        for group in tax_groups:
            tax_group = self.env['account.tax.group'].browse(group['id'])
            if (
                tax_group.l10n_pt_tax_region == 'PT-ALL'
                or (
                    tax_group.l10n_pt_tax_region
                    and tax_group.l10n_pt_tax_region == self.company_id.l10n_pt_region_code
                )
            ):
                res[tax_group.l10n_pt_tax_category] = {
                    'base': self._l10n_pt_qr_format_amount(group['base_amount']),
                    'vat': self._l10n_pt_qr_format_amount(group['tax_amount']),
                }
        return res
