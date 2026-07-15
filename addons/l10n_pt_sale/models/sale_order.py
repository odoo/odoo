from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import float_repr

from odoo.addons.l10n_pt_sale.models.l10n_pt_at_series import AT_SERIES_SALES_DOCUMENT_TYPES

AT_SERIES_WORKING_DOCUMENT_SAFT_TYPE_MAP = {
    'quotation': 'OR',
    'sales_order': 'NE',
}


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    l10n_pt_line_discount = fields.Float(string="Line Discount", digits='Discount', default=0.0)

    @api.onchange('l10n_pt_line_discount')
    def _set_discount(self):
        """
        Compute the total discount considering both the line discount and the global discount.
        Ex: A line with unit price of 100, a line discount of 10% and a global discount of 10%.
        The total discount is 19%: 1 - (1 - 0.1) * (1 - 0.1) = 0.19
        """
        self.ensure_one()
        # PT does not accept negative lines, so global discounts need to be handled via a separate field
        global_discount = (self.order_id.l10n_pt_global_discount or 0.0) / 100
        line_discount = (self.l10n_pt_line_discount or 0.0) / 100
        self.discount = (1 - (1 - global_discount) * (1 - line_discount)) * 100

    @api.onchange('l10n_pt_line_discount')
    def _inverse_l10n_pt_line_discount(self):
        for line in self.filtered(lambda l: l.company_id.account_fiscal_country_id.code == 'PT'):
            line._set_discount()

    @api.constrains('l10n_pt_line_discount')
    def _check_l10n_pt_line_discount(self):
        # The PT tax authority requires that discounts are in the range between 0% and 100%.
        for line in self:
            if line.l10n_pt_line_discount < 0.0 or line.l10n_pt_line_discount > 100.0:
                raise ValidationError(_("Discount amounts should be between 0% and 100%."))

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

    def _l10n_pt_get_line_vat_exemptions_reasons(self, as_string=True):
        """
        Returns a string with the VAT exemption reason codes per line. E.g: [M16]
        It is added to the tax name in the invoice PDF to satisfy the following requirement by the PT tax authority:
        "In case the reason for exemption is not presented on the correspondent line, any other type of reference
        must be used allowing linking the exempted line to the correspondent reason."
        """
        self.ensure_one()
        exemption_reasons = sorted(set(
            self.tax_ids.filtered(lambda tax: tax.l10n_pt_tax_exemption_reason)
            .mapped('l10n_pt_tax_exemption_reason')
        ))
        return ", ".join(f"[{reason}]" for reason in exemption_reasons) if as_string else exemption_reasons

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
    _inherit = ['sale.order', 'l10n.pt.hashed.document.mixin']

    l10n_pt_at_series_id = fields.Many2one(
        compute='_compute_l10n_pt_at_series_id',
        readonly=False,
        store=True,
        domain="[('active', '=', True), ('document_type', 'in', ('quotation', 'sales_order'))]",
    )
    l10n_pt_document_number = fields.Char(
        readonly=True,
        help="Internal identifier for Portuguese documents, made up of the document type code, "
             "the series name, and the number of the document within the series.",
    )
    l10n_pt_show_future_date_warning = fields.Boolean(compute='_compute_l10n_pt_show_future_date_warning')
    # Document type used in invoice template (when printed, documents have to present the document type on each page)
    l10n_pt_document_type = fields.Selection(
        selection=AT_SERIES_SALES_DOCUMENT_TYPES,
        string="Portuguese Document Type",
        compute='_compute_l10n_pt_document_type',
        store=True,
    )
    l10n_pt_cancel_reason = fields.Char(
        string="Cancellation Reason",
        copy=False,
        readonly=True,
        help="Reason given by the user for cancelling this move",
    )
    l10n_pt_global_discount = fields.Float(
        string="Global Discount %",
        digits='Discount',
        inverse='_inverse_l10n_pt_global_discount',
    )
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
    # OVERRIDES
    ####################################

    def action_quotation_send(self):
        if not self.env.context.get('has_reprint_reason'):
            self._check_l10n_pt_dates()
            self._l10n_pt_check_at_series()
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

    def _create_invoices(self, grouped=False, final=False, date=None):
        if self.env.company.country_id.code == 'PT':
            self._check_l10n_pt_dates()
            orders = self.sudo().search([
                ('company_id', '=', self.env.company.id),
                ('l10n_pt_inalterable_hash', '=', False),
                ('l10n_pt_document_number', '=', False),
            ], order='date_order')
            orders._l10n_pt_check_at_series()
            orders.filtered(lambda so: so.state == 'sale')._set_l10n_pt_document_number()
        return super()._create_invoices(grouped=grouped, final=final, date=date)

    def action_preview_sale_order(self):
        self.ensure_one()
        self._check_l10n_pt_dates()
        self._l10n_pt_check_at_series()
        self._set_l10n_pt_document_number()
        if self.state == 'sale':
            self._l10n_pt_compute_missing_hashes()
        return super().action_preview_sale_order()

    def _prepare_invoice(self):
        invoice_vals = super()._prepare_invoice()
        if self.country_code == 'PT':
            invoice_vals['l10n_pt_global_discount'] = self.l10n_pt_global_discount
        return invoice_vals

    def action_cancel(self):
        for order in self:
            order.action_unlock()
        return super().action_cancel()

    def _action_cancel(self):
        super()._action_cancel()
        # Call cancellation wizard
        action = self.env['ir.actions.actions']._for_xml_id('l10n_pt_certification.action_l10n_pt_cancel')
        action['context'] = {
            'model': 'sale.order',
            'order_ids': self.ids,
        }
        return action

    ####################################
    # ACTIONS
    ####################################

    def action_l10n_pt_create_sales_order(self):
        self.ensure_one()
        self._check_l10n_pt_dates()
        self._l10n_pt_check_at_series()
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
    # MISC REQUIREMENTS
    ####################################

    @api.depends('sales_order_ids')
    def _compute_related_so_count(self):
        for order in self:
            order.sales_order_count = len(order.sales_order_ids)

    @api.onchange('l10n_pt_global_discount')
    def _inverse_l10n_pt_global_discount(self):
        for order in self:
            for line in order.order_line:
                line._set_discount()

    @api.constrains('l10n_pt_global_discount')
    def _check_l10n_pt_global_discount(self):
        for order in self.filtered(lambda o: o.country_code == 'PT'):
            if order.l10n_pt_global_discount < 0.0 or order.l10n_pt_global_discount > 100.0:
                raise ValidationError(_("Discount amounts should be between 0% and 100%."))

    @api.depends('state', 'date_order', 'country_code')
    def _compute_l10n_pt_show_future_date_warning(self):
        """
        No other documents may be issued with the current or previous date within the same series as
        a document issued in the future. If user enters an invoice date ahead of current date,
        a warning will be displayed.
        """
        for order in self:
            order.l10n_pt_show_future_date_warning = (
                    order.country_code == 'PT'
                    and order.state != 'cancel'
                    and order.date_order
                    and order.date_order > fields.Datetime.now()
            )

    def _check_l10n_pt_dates(self):
        """
        According to the Portuguese tax authority:
        "When the document issuing date is later than the current date, or superior than the date on the system,
        no other document may be issued with the current or previous date within the same series"
        """
        now = fields.Datetime.now()
        series = self.mapped('l10n_pt_at_series_id')

        grouped = self.env['sale.order']._read_group(
            domain=[
                ('l10n_pt_at_series_id', 'in', series.ids),
            ],
            groupby=['l10n_pt_at_series_id'],
            aggregates=['date_order:max', 'l10n_pt_hashed_on:max'],
        )
        max_dates_per_series = {
            at_series.id: {
                'max_order_date': max_order_date,
                'max_hashed_on_date': max_hashed_on_date,
            }
            for at_series, max_order_date, max_hashed_on_date in grouped
        }

        for order in self:
            if not order.l10n_pt_at_series_id:
                continue

            series_id = order.l10n_pt_at_series_id.id
            max_dates = max_dates_per_series.get(series_id)
            if not max_dates:
                continue

            max_order_date = max_dates['max_order_date']
            max_hashed_on_date = max_dates['max_hashed_on_date']
            order_date = order.date_order or now

            if max_order_date and max_order_date > now and order_date < max_order_date:
                raise UserError(_(
                    "You cannot create a quotation or sales order with a date earlier than the date of the last "
                    "document issued in this AT series (%(name)s - %(prefix)s).",
                    name=order.l10n_pt_at_series_id.name,
                    prefix=order.l10n_pt_at_series_id.prefix,
                ))

            if max_hashed_on_date and max_hashed_on_date > now:
                raise UserError(_(
                    "There exists secured sales orders with a lock date ahead of the present time in this AT series (%(name)s - %(prefix)s).",
                    name=order.l10n_pt_at_series_id.name,
                    prefix=order.l10n_pt_at_series_id.prefix,
                ))

    def _l10n_pt_check_at_series(self):
        sale_orders = self.filtered(lambda so: not so.l10n_pt_at_series_id)
        if not sale_orders:
            return
        if len(sale_orders) == 1:
            action_error = {
                'view_mode': 'form',
                'name': _('AT Series'),
                'res_model': 'l10n_pt.at.series',
                'type': 'ir.actions.act_window',
                'views': [[self.env.ref('l10n_pt_certification.view_l10n_pt_at_series_tree').id, 'list']],
                'target': 'new',
            }
            document_types = sale_orders.mapped('l10n_pt_document_type')
            if len(document_types) > 1:
                document_type = "types Quotation (OR), Sales Order (NE)"
            else:
                document_type = "type " + dict(sale_orders[0]._fields['l10n_pt_document_type'].selection).get(document_types[0])
            raise RedirectWarning(
                _("There is no AT series for the document %(document_type)s. "
                  "Create a new series or view existing series via the Accounting Settings.",
                  document_type=document_type),
                action_error,
                _('Add an AT Series'),
            )
        else:
            action_error = {
                'view_mode': 'form',
                'name': _('AT Series'),
                'res_model': 'l10n_pt.at.series',
                'type': 'ir.actions.act_window',
                'views': [[self.env.ref('l10n_pt_certification.view_l10n_pt_at_series_tree').id, 'list']],
            }
            raise RedirectWarning(
                _("Please ensure that there are AT series for the document types Quotation (OR) and Sales Order (NE)."),
                action_error,
                _('Add an AT Series'),
            )

    def _l10n_pt_get_vat_exemptions_reasons(self):
        self.ensure_one()
        exemption_selection = dict(self.env['account.tax']._fields['l10n_pt_tax_exemption_reason'].selection)
        exemption_reasons = set()
        for line in self.order_line:
            for reason_code in line._l10n_pt_get_line_vat_exemptions_reasons(as_string=False):
                exemption_reasons.add(exemption_selection.get(reason_code))
        return sorted(exemption_reasons)

    ####################################
    # PT FIELDS - ATCUD, AT SERIES
    ####################################

    @api.constrains('l10n_pt_at_series_id')
    def _check_l10n_pt_at_series_id(self):
        for order in self.filtered(lambda o: o.country_code == 'PT'):
            if not order.l10n_pt_at_series_id.active:
                raise UserError(_("An inactive series cannot be used."))

    @api.depends('state', 'company_id')
    def _compute_l10n_pt_at_series_id(self):
        sale_orders = self.filtered(lambda so: not so.l10n_pt_at_series_id and so.state != 'cancel')
        for (company, state_sale), orders in sale_orders.grouped(lambda o: (o.company_id, o.state == 'sale')).items():
            domain = [('company_id', '=', company.id)]
            if not state_sale and not self.env.context.get('create_sales_order'):
                domain.append(('state', 'in', ('draft', 'sent')))
            else:
                domain.append(('state', '=', 'sale'))

            last_order = self.env['sale.order'].search(domain, order='id desc', limit=1)
            last_series = last_order.l10n_pt_at_series_id
            if last_series:
                orders.l10n_pt_at_series_id = last_series
            else:
                orders.l10n_pt_at_series_id = self.env['l10n_pt.at.series'].search([
                    '|',
                    '&',
                    ('company_id', '=', company.id),
                    ('company_exclusive_series', '=', True),
                    '&',
                    ('company_id', 'in', company.parent_ids.ids),
                    ('company_exclusive_series', '=', False),
                    ('active', '=', True),
                    ('document_type', 'in', self._l10n_pt_series_document_types()),
                ], limit=1)

    def _set_l10n_pt_document_number(self):
        for order in self.filtered(lambda o: o.country_code == 'PT').sorted('date_order'):
            if order.l10n_pt_at_series_id and not order.l10n_pt_document_number:
                order.l10n_pt_document_number = order.l10n_pt_at_series_id._l10n_pt_get_document_number_sequence().next_by_id()
        self._check_l10n_pt_document_number()

    @api.depends('state', 'country_code')
    def _compute_l10n_pt_document_type(self):
        for order in self.filtered(lambda o: o.country_code == 'PT'):
            if order.state in ('draft', 'sent'):
                order.l10n_pt_document_type = 'quotation'
            elif order.state == 'sale':
                order.l10n_pt_document_type = 'sales_order'

    ####################################
    # HASH AND QR CODE
    ####################################

    def _l10n_pt_get_document_date(self):
        self.ensure_one()
        return self.date_order

    def _l10n_pt_get_document_number(self):
        """ Allows patching in tests """
        self.ensure_one()
        return self.l10n_pt_document_number

    def _l10n_pt_get_gross_total(self):
        self.ensure_one()
        return self.amount_total

    def _l10n_pt_get_saft_doc_type(self):
        self.ensure_one()
        return AT_SERIES_WORKING_DOCUMENT_SAFT_TYPE_MAP[self.l10n_pt_document_type]

    def _l10n_pt_series_document_types(self):
        return ('sales_order', 'quotation')

    def _l10n_pt_protected_fields(self):
        return super()._l10n_pt_protected_fields() + ['l10n_pt_at_series_id']

    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return []
        return ['date_order', 'l10n_pt_hashed_on', 'name', 'l10n_pt_document_number', 'amount_total', 'partner_id', 'company_id', 'sale_order_option_ids']

    @api.model
    def _l10n_pt_find_last_hashed(self, at_series):
        return self.sudo().search([
            ('l10n_pt_at_series_id', '=', at_series.id),
            ('l10n_pt_inalterable_hash', '!=', False),
        ], order='date_order desc, l10n_pt_document_number desc', limit=1)

    def _l10n_pt_get_unhashed_records(self, at_series):
        return self.sudo().search([
            ('l10n_pt_at_series_id', '=', at_series.id),
            ('l10n_pt_inalterable_hash', '=', False),
        ], order='date_order')

    def _l10n_pt_post_hash_hook(self):
        self.locked = True

    def _l10n_pt_compute_missing_hashes(self, company=None):
        """
        Compute the hash/atcud for all records that do not have one yet
        (because they were not printed/previewed yet)
        """
        # When printing an order before previewing or creating an invoice from it, at series may not be set yet
        orders_to_check = self.filtered(lambda so: not so.l10n_pt_at_series_id)
        orders_to_check._l10n_pt_check_at_series()
        orders_to_check._set_l10n_pt_document_number()
        return super()._l10n_pt_compute_missing_hashes(company=company)

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
