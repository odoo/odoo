import re
import urllib.parse

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError, ValidationError
from odoo.tools import float_repr

from odoo.addons.l10n_pt_certification.utils import hashing as pt_hash_utils
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

    @api.constrains('tax_id')
    def _check_l10n_pt_tax_id(self):
        if self.filtered(
            lambda l: not l.display_type
            and l.company_id.account_fiscal_country_id.code == 'PT'
            and not l.tax_id
        ):
            raise ValidationError(_("You cannot create a line without VAT tax."))

    @api.constrains('price_subtotal')
    def _check_l10n_pt_negative_lines(self):
        if non_positive_lines := self.filtered(
            lambda l: not l.display_type
            and l.company_id.account_fiscal_country_id.code == 'PT'
            and l.price_total <= 0.0
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
            self.tax_id.filtered(lambda tax: tax.l10n_pt_tax_exemption_reason)
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
    _inherit = 'sale.order'

    l10n_pt_qr_code_str = fields.Char('Portuguese QR Code', compute='_compute_l10n_pt_qr_code_str', store=True)
    l10n_pt_sale_inalterable_hash = fields.Char(string="Inalterability Hash", readonly=True, copy=False)
    l10n_pt_inalterable_hash_short = fields.Char(
        'Short version of the Portuguese hash',
        compute='_compute_l10n_pt_inalterable_hash_info',
    )
    l10n_pt_inalterable_hash_version = fields.Integer(
        'Portuguese hash version',
        compute='_compute_l10n_pt_inalterable_hash_info',
    )
    l10n_pt_atcud = fields.Char(
        string='Portuguese ATCUD',
        compute='_compute_l10n_pt_atcud',
        store=True,
        help="Unique document code formed by the AT series validation code and the number of the document.",
    )
    l10n_pt_document_number = fields.Char(
        string="Unique Document Number",
        copy=False,
        readonly=True,
        help="Internal identifier for Portuguese documents, made up of the document type code, "
             "the series name, and the number of the document within the series.",
    )
    l10n_pt_show_future_date_warning = fields.Boolean(compute='_compute_l10n_pt_show_future_date_warning')
    l10n_pt_hashed_on = fields.Datetime(string="Hashed On", readonly=True)
    l10n_pt_at_series_id = fields.Many2one(
        comodel_name="l10n_pt.at.series",
        string="AT Series",
        compute='_compute_l10n_pt_at_series_id',
        readonly=False,
        store=True,
    )
    l10n_pt_at_series_line_id = fields.Many2one(
        comodel_name="l10n_pt.at.series.line",
        string="Document-specific AT Series",
        compute='_compute_l10n_pt_at_series_line_id',
        store=True,
    )
    # Document type used in invoice template (when printed, documents have to present the document type on each page)
    l10n_pt_document_type = fields.Selection(
        selection=AT_SERIES_SALES_DOCUMENT_TYPES,
        string="Portuguese Document Type",
        compute='_compute_l10n_pt_document_type',
        store=True,
    )
    l10n_pt_print_version = fields.Selection(
        selection=[
            ('original', 'Original print'),
            ('reprint', 'Reprint'),
        ],
        string="Version of Printed Document",
        copy=False,
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

    def write(self, vals):
        if not vals:
            return True
        for order in self.filtered(lambda o: o.country_code == 'PT'):
            violated_fields = set(vals).intersection(
                order._get_integrity_hash_fields() + ['l10n_pt_at_series_id', 'l10n_pt_sale_inalterable_hash']
            )
            if violated_fields and order.l10n_pt_sale_inalterable_hash:
                raise UserError(_(
                    "This document is protected by a hash. "
                    "Therefore, you cannot edit the following fields: %s.",
                    ', '.join(f['string'] for f in self.fields_get(violated_fields).values())
                ))
        return super().write(vals)

    def action_quotation_send(self):
        if not self.env.context.get('has_reprint_reason'):
            self._check_l10n_pt_dates()
            self._l10n_pt_check_so_at_series_line()
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
                ('l10n_pt_sale_inalterable_hash', '=', False),
                ('l10n_pt_document_number', '=', False),
            ], order='date_order')
            orders._l10n_pt_check_so_at_series_line()
            orders.filtered(lambda so: so.state == 'sale')._set_l10n_pt_document_number()
        return super()._create_invoices(grouped=grouped, final=final, date=date)

    def action_preview_sale_order(self):
        self.ensure_one()
        self._check_l10n_pt_dates()
        self._l10n_pt_check_so_at_series_line()
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
        self._l10n_pt_check_so_at_series_line()
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

    def update_l10n_pt_print_version(self):
        for order in self.filtered(lambda o: o.country_code == 'PT'):
            if not order.l10n_pt_print_version:
                order.l10n_pt_print_version = 'original'
            else:
                order.l10n_pt_print_version = 'reprint'

    def _check_l10n_pt_document_number(self):
        for order in self.filtered(lambda o: (
            o.country_code == 'PT'
            and o.l10n_pt_at_series_id
        )):
            if order.l10n_pt_document_number and not re.match(r'^[^ ]+ [^/^ ]+/[0-9]+$', order.l10n_pt_document_number):
                raise ValidationError(_(
                    "The document number (%s) is invalid. It must start with the internal code "
                    "of the document type, a space, the name of the series followed by a slash and the number of the "
                    "document within the series (e.g. NE 2025A/1). Please check if the series selected fulfill these "
                    "requirements.", order.l10n_pt_document_number
                ))

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
        series_ids = self.mapped('l10n_pt_at_series_line_id').ids

        grouped = self.env['sale.order'].read_group(
            domain=[
                ('l10n_pt_at_series_line_id', 'in', series_ids),
                ('l10n_pt_at_series_line_id', '!=', False),
            ],
            fields=['l10n_pt_at_series_line_id', 'date_order:max', 'l10n_pt_hashed_on:max'],
            groupby=['l10n_pt_at_series_line_id']
        )
        max_dates_per_series = {
            group['l10n_pt_at_series_line_id'][0]: {
                'max_order_date': group['date_order'],
                'max_hashed_on_date': group['l10n_pt_hashed_on']
            }
            for group in grouped
        }

        for order in self:
            if not order.l10n_pt_at_series_line_id:
                continue

            series_id = order.l10n_pt_at_series_line_id.id
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
                    prefix=order.l10n_pt_at_series_line_id.prefix,
                ))

            if max_hashed_on_date and max_hashed_on_date > now:
                raise UserError(_(
                    "There exists secured sales orders with a lock date ahead of the present time in this AT series (%(name)s - %(prefix)s).",
                    name=order.l10n_pt_at_series_id.name,
                    prefix=order.l10n_pt_at_series_line_id.prefix,
                ))

    def _l10n_pt_check_so_at_series_line(self):
        self._compute_l10n_pt_at_series_line_id()
        sale_orders = self.filtered(lambda so: so.l10n_pt_at_series_id and not so.l10n_pt_at_series_line_id)
        if len(sale_orders.l10n_pt_at_series_id) == 1:
            action_error = {
                'view_mode': 'form',
                'name': _('AT Series'),
                'res_model': 'l10n_pt.at.series',
                'res_id': sale_orders.l10n_pt_at_series_id.id,
                'type': 'ir.actions.act_window',
                'views': [[self.env.ref('l10n_pt_certification.view_l10n_pt_at_series_form').id, 'form']],
                'target': 'new',
            }
            document_types = sale_orders.mapped('l10n_pt_document_type')
            if len(document_types) > 1:
                document_type = "types Quotation (OR), Sales Order (NE)"
            else:
                document_type = "type " + dict(sale_orders[0]._fields['l10n_pt_document_type'].selection).get(document_types[0])
            raise RedirectWarning(
                _("There is no AT series for the document %(document_type)s registered under the series name %(series_name)s. "
                  "Create a new series or view existing series via the Accounting Settings.",
                  document_type=document_type,
                  series_name=sale_orders.l10n_pt_at_series_id.name),
                action_error,
                _('Add an AT Series'),
            )
        elif len(sale_orders.l10n_pt_at_series_id) > 1:
            action_error = {
                'view_mode': 'form',
                'name': _('AT Series'),
                'res_model': 'l10n_pt.at.series',
                'res_ids': sale_orders.l10n_pt_at_series_id.ids,
                'type': 'ir.actions.act_window',
                'views': [[self.env.ref('l10n_pt_certification.view_l10n_pt_at_series_tree').id, 'list']],
            }
            raise RedirectWarning(
                _("Please ensure that there are AT series for the document types Quotation (OR) and Sales Order (NE) "
                  "registered under the active series: %(series_names)s.",
                  series_name=",".join(sale_orders.l10n_pt_at_series_id.mapped('name'))),
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
                ], limit=1)

    @api.depends('l10n_pt_at_series_id')
    def _compute_l10n_pt_at_series_line_id(self):
        sales_orders = self.filtered(lambda o: not o.l10n_pt_at_series_line_id and o.l10n_pt_at_series_id)
        for (document_type, series), orders in sales_orders.grouped(lambda o: (o.l10n_pt_document_type, o.l10n_pt_at_series_id)).items():
            at_series_line = series._get_line_for_type(document_type)
            if at_series_line:
                orders.l10n_pt_at_series_line_id = at_series_line

    def _set_l10n_pt_document_number(self):
        for order in self.filtered(lambda o: o.country_code == 'PT').sorted('date_order'):
            if order.l10n_pt_at_series_id and not order.l10n_pt_at_series_line_id:
                order._compute_l10n_pt_at_series_line_id()
            if not order.l10n_pt_document_number:
                order.l10n_pt_document_number = order.l10n_pt_at_series_line_id._l10n_pt_get_document_number_sequence().next_by_id()
        self._check_l10n_pt_document_number()

    @api.depends('state', 'country_code')
    def _compute_l10n_pt_document_type(self):
        for order in self.filtered(lambda o: o.country_code == 'PT'):
            if order.state in ('draft', 'sent'):
                order.l10n_pt_document_type = 'quotation'
            elif order.state == 'sale':
                order.l10n_pt_document_type = 'sales_order'

    @api.depends('l10n_pt_document_number')
    def _compute_l10n_pt_atcud(self):
        for order in self:
            if order.country_code == 'PT' and not order.l10n_pt_atcud and order.l10n_pt_document_number:
                current_seq_number = int(order.l10n_pt_document_number.split('/')[-1])
                order.l10n_pt_atcud = f"{order.l10n_pt_at_series_line_id._get_at_code()}-{current_seq_number}"

    ####################################
    # HASH AND QR CODE
    ####################################

    def _get_integrity_hash_fields(self):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return []
        return ['date_order', 'l10n_pt_hashed_on', 'name', 'l10n_pt_document_number', 'amount_total', 'partner_id', 'company_id', 'sale_order_option_ids']

    def _get_l10n_pt_sale_document_number(self):
        """ Allows patching in tests """
        self.ensure_one()
        return self.l10n_pt_document_number

    def _calculate_hashes(self, previous_hash=None):
        if self.company_id.account_fiscal_country_id.code != 'PT':
            return {}
        self.l10n_pt_hashed_on = fields.Datetime.now()
        docs_to_sign = [{
            'id': order.id,
            'date': order.date_order.strftime('%Y-%m-%d'),
            'sorting_key': order.date_order.isoformat(),
            'system_entry_date': order.l10n_pt_hashed_on.isoformat(timespec='seconds'),
            'name': order._get_l10n_pt_sale_document_number(),
            'gross_total': float_repr(order.amount_total, precision_digits=2),
            'previous_signature': previous_hash,
        } for order in self]
        return pt_hash_utils.sign_records(self.env, docs_to_sign, 'sale.order')

    @api.depends('l10n_pt_sale_inalterable_hash')
    def _compute_l10n_pt_inalterable_hash_info(self):
        for order in self:
            if order.l10n_pt_sale_inalterable_hash:
                hash_version, hash_str = order.l10n_pt_sale_inalterable_hash.split("$")[1:]
                order.l10n_pt_inalterable_hash_version = int(hash_version)
                order.l10n_pt_inalterable_hash_short = hash_str[0] + hash_str[10] + hash_str[20] + hash_str[30]
            else:
                order.l10n_pt_inalterable_hash_version = False
                order.l10n_pt_inalterable_hash_short = False

    @api.model
    def _find_last_order(self, at_series_line):
        return self.sudo().search([
            ('l10n_pt_at_series_line_id', '=', at_series_line.id),
            ('l10n_pt_sale_inalterable_hash', '!=', False),
        ], order='date_order desc, l10n_pt_document_number desc', limit=1)

    def _l10n_pt_compute_missing_hashes(self, company=None, check_at_series=False):
        """
        Compute the hash/atcud for all records that do not have one yet
        (because they were not printed/previewed yet)
        """
        company = company or self.env.company

        # When printing an order before previewing or creating an invoice from it, at series may not be set yet
        if active_ids := self.env.context.get('active_ids'):
            orders_to_check = self.browse(active_ids).filtered(lambda so: not so.l10n_pt_at_series_line_id)
            orders_to_check._l10n_pt_check_so_at_series_line()
            orders_to_check._set_l10n_pt_document_number()

        # Get all AT series that apply to sale.order to find unhashed orders per series
        at_series_lines = self.env['l10n_pt.at.series.line'].search([
            '|',
            '&',
            ('company_id', '=', company.id),
            ('company_exclusive_series', '=', True),
            '&',
            ('company_id', 'in', company.parent_ids.ids),
            ('company_exclusive_series', '=', False),
            ('type', 'in', ('sales_order', 'quotation')),
        ])
        for at_series_line in at_series_lines:
            orders = self.sudo().search([
                ('l10n_pt_at_series_line_id', '=', at_series_line.id),
                ('l10n_pt_sale_inalterable_hash', '=', False),
            ], order='date_order')

            orders._set_l10n_pt_document_number()
            previous_order = self._find_last_order(at_series_line)
            try:
                previous_hash = previous_order.l10n_pt_sale_inalterable_hash.split("$")[2] if previous_order.l10n_pt_sale_inalterable_hash else ""
            except IndexError:  # hash is not correctly formatted (it has been altered!)
                previous_hash = "invalid_hash"  # will never be a valid hash

            orders_hashes = orders._calculate_hashes(previous_hash)
            for order, l10n_pt_sale_inalterable_hash in orders_hashes.items():
                order.l10n_pt_sale_inalterable_hash = l10n_pt_sale_inalterable_hash
                order.locked = True

    def l10n_pt_verify_prerequisites_qr_code(self):
        self.ensure_one()
        if self.country_code == 'PT':
            return pt_hash_utils.verify_prerequisites_qr_code(self, self.l10n_pt_sale_inalterable_hash, self.l10n_pt_atcud)

    @api.depends('l10n_pt_sale_inalterable_hash')
    def _compute_l10n_pt_qr_code_str(self):
        """
        Generate the informational QR code for Portugal invoicing.
        E.g.: A:509445535*B:123456823*C:BE*D:OR*E:N*F:20220103*G:OR 01P2022/1*H:0*I1:PT*I7:325.20*I8:74.80*N:74.80*O:400.00*P:0.00*Q:P0FE*R:2230
        """

        def format_amount(order, amount):
            """
            Convert amount to EUR based on the rate of a given account_move's date
            Format amount to 2 decimals as per SAF-T (PT) requirements
            """
            amount_eur = order.currency_id._convert(amount, self.env.ref('base.EUR'), order.company_id, order.date_order)
            return float_repr(amount_eur, 2)

        def get_details_by_tax_category(order):
            """
            :return: {tax_category : {'base': base, 'vat': vat}}
            """
            res = {}
            tax_groups = order.tax_totals['subtotals'][0]['tax_groups']

            for group in tax_groups:
                tax_group = self.env['account.tax.group'].browse(group['id'])
                if (
                    tax_group.l10n_pt_tax_region == 'PT-ALL'
                    or (
                        tax_group.l10n_pt_tax_region
                        and tax_group.l10n_pt_tax_region == order.company_id.l10n_pt_region_code
                    )
                ):
                    res[tax_group.l10n_pt_tax_category] = {
                        'base': format_amount(order, group['base_amount']),
                        'vat': format_amount(order, group['tax_amount']),
                    }
            return res

        for order in self.filtered(lambda o: (
            o.country_code == "PT"
            and o.l10n_pt_sale_inalterable_hash
            and not o.l10n_pt_qr_code_str  # Skip if already computed
        )):
            details_by_tax_group = get_details_by_tax_category(order)

            order.l10n_pt_verify_prerequisites_qr_code()
            # Most of the values needed to create the QR code string are filled in pt_hash_utils, also used by pt_pos and pt_stock
            qr_code_dict, tax_letter = pt_hash_utils.l10n_pt_common_qr_code_str(order, self.env, order.date_order)
            qr_code_dict['D:'] = f"{AT_SERIES_WORKING_DOCUMENT_SAFT_TYPE_MAP[order.l10n_pt_document_type]}*"
            qr_code_dict['H:'] = f"{order.l10n_pt_atcud}*"
            if details_by_tax_group.get('E'):
                qr_code_dict[f'{tax_letter}2:'] = f"{details_by_tax_group.get('E')['base']}*"
            for i, tax_category in enumerate(('R', 'I', 'N')):
                if details_by_tax_group.get(tax_category):
                    qr_code_dict[f'{tax_letter}{i * 2 + 3}:'] = f"{details_by_tax_group.get(tax_category)['base']}*"
                    qr_code_dict[f'{tax_letter}{i * 2 + 4}:'] = f"{details_by_tax_group.get(tax_category)['vat']}*"
            qr_code_dict['N:'] = f"{format_amount(order, order.amount_tax)}*"
            qr_code_dict['O:'] = f"{format_amount(order, order.amount_total)}*"
            qr_code_dict['Q:'] = f"{order.l10n_pt_inalterable_hash_short}*"
            # Create QR code string from dictionary
            qr_code_str = ''.join(f"{key}{value}" for key, value in sorted(qr_code_dict.items()))
            order.l10n_pt_qr_code_str = urllib.parse.quote_plus(qr_code_str)
