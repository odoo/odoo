# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    l10n_it_edi_doi_date = fields.Date(
        string="Date on which Declaration of Intent is applied",
        compute='_compute_l10n_it_edi_doi_date',
    )

    l10n_it_edi_doi_use = fields.Boolean(
        string="Use Declaration of Intent",
        compute='_compute_l10n_it_edi_doi_use',
    )

    l10n_it_edi_doi_id = fields.Many2one(
        string="Declaration of Intent",
        compute='_compute_l10n_it_edi_doi_id',
        store=True,
        readonly=False,
        precompute=True,
        comodel_name='l10n_it_edi_doi.declaration_of_intent',
    )

    l10n_it_edi_doi_not_yet_invoiced = fields.Monetary(
        string='Declaration of Intent Amount Not Yet Invoiced',
        compute='_compute_l10n_it_edi_doi_not_yet_invoiced',
        store=True,
        readonly=True,
        help="Total under the Declaration of Intent of this document that can still be invoiced",
    )

    l10n_it_edi_doi_warning = fields.Text(
        string="Declaration of Intent Threshold Warning",
        compute='_compute_l10n_it_edi_doi_warning',
    )

    @api.depends('date_order')
    def _compute_l10n_it_edi_doi_date(self):
        for order in self:
            order.l10n_it_edi_doi_date = order.date_order or fields.Date.context_today(self)

    @api.depends('l10n_it_edi_doi_id', 'country_code')
    def _compute_l10n_it_edi_doi_use(self):
        for order in self:
            order.l10n_it_edi_doi_use = order.l10n_it_edi_doi_id \
                or order.country_code == "IT"

    @api.depends('company_id', 'partner_id.commercial_partner_id', 'l10n_it_edi_doi_date', 'currency_id')
    def _compute_l10n_it_edi_doi_id(self):
        for order in self:
            if not order.l10n_it_edi_doi_use or order.state != 'draft' and not order.l10n_it_edi_doi_id:
                order.l10n_it_edi_doi_id = False
                continue
            partner = order.partner_id.commercial_partner_id

            # Avoid a query or changing a manually set declaration of intent
            # (if the declaration is still valid).
            validity_warnings = order.l10n_it_edi_doi_id._get_validity_warnings(
                order.company_id, partner, order.currency_id, order.l10n_it_edi_doi_date, sales_order=True
            )
            if order.l10n_it_edi_doi_id and not validity_warnings:
                continue

            declaration = self.env['l10n_it_edi_doi.declaration_of_intent']\
                ._fetch_valid_declaration_of_intent(order.company_id, partner, order.currency_id, order.l10n_it_edi_doi_date)
            order.l10n_it_edi_doi_id = declaration

    @api.depends('l10n_it_edi_doi_id', 'tax_totals', 'order_line', 'order_line.qty_invoiced_posted')
    def _compute_l10n_it_edi_doi_not_yet_invoiced(self):
        for order in self:
            declaration = order.l10n_it_edi_doi_id
            order.l10n_it_edi_doi_not_yet_invoiced = order._l10n_it_edi_doi_get_amount_not_yet_invoiced(declaration)

    @api.depends('l10n_it_edi_doi_id', 'l10n_it_edi_doi_id.remaining', 'state', 'tax_totals')
    def _compute_l10n_it_edi_doi_warning(self):
        for order in self:
            order.l10n_it_edi_doi_warning = ''
            declaration = order.l10n_it_edi_doi_id

            show_warning = declaration and order.state != 'cancelled'
            if not show_warning:
                continue

            declaration_not_yet_invoiced = declaration.not_yet_invoiced
            # Exactly the confirmed SOs (state == 'sale') are included in `declaration.not_yet_invoiced`.
            # The amount of `declaration.not_yet_invoiced` may change due to confirming or saving `order`.
            #   * An unconfirmed order is being confirmed:
            #     We have to add the order amount to `declaration.not_yet_invoiced`.
            #   * A confirmed SO is being edited:
            #     The field `declaration.not_yet_invoiced` will be updated when saving.
            #     But we want to update the warning during the editing already (before saving).
            #     We first have to remove the "old amount" from `declaration.not_yet_invoiced`
            #     before adding the current amount.
            if order.state == 'sale':
                old_order_state = order._origin
                declaration_not_yet_invoiced -= old_order_state.l10n_it_edi_doi_not_yet_invoiced
            declaration_not_yet_invoiced += order.l10n_it_edi_doi_not_yet_invoiced

            validity_warnings = declaration._get_validity_warnings(
                order.company_id, order.partner_id.commercial_partner_id, order.currency_id, order.l10n_it_edi_doi_date,
                sales_order=True
            )

            threshold_warning = declaration._build_threshold_warning_message(declaration.invoiced, declaration_not_yet_invoiced)

            order.l10n_it_edi_doi_warning = '{}\n\n{}'.format('\n'.join(validity_warnings), threshold_warning).strip()

    @api.depends('l10n_it_edi_doi_id')
    def _compute_fiscal_position_id(self):
        super()._compute_fiscal_position_id()
        for order in self:
            declaration_fiscal_position = order.company_id.l10n_it_edi_doi_fiscal_position_id
            if declaration_fiscal_position and order.l10n_it_edi_doi_id:
                order.fiscal_position_id = declaration_fiscal_position

    def _prepare_invoice(self):
        """
        Prepare the dict of values to create the new invoice for a sales order. This method may be
        overridden to implement custom invoice generation (making sure to call super() to establish
        a clean extension chain).
        """
        vals = super()._prepare_invoice()
        declaration = self.l10n_it_edi_doi_id
        if declaration:
            date = fields.Date.context_today(self)
            validity_warnings = declaration._get_validity_warnings(
                self.company_id, self.partner_id.commercial_partner_id, self.currency_id, date, sales_order=True
            )
            if not validity_warnings:
                vals['l10n_it_edi_doi_id'] = declaration.id
        return vals

    def copy_data(self, default=None):
        data_list = super().copy_data(default)
        for order, data in zip(self, data_list):
            partner = order.partner_id.commercial_partner_id
            date = fields.Date.context_today(self)
            if order.l10n_it_edi_doi_id._get_validity_warnings(order.company_id, partner, order.currency_id, date, sales_order=True):
                del data['l10n_it_edi_doi_id']
                del data['fiscal_position_id']
        return data_list

    def _l10n_it_edi_doi_check_configuration(self):
        """
        Raise a UserError in case the configuration of the sale order is invalid.
        """
        errors = []
        for order in self:
            declaration = order.l10n_it_edi_doi_id
            if declaration:
                validity_warnings = declaration._get_validity_warnings(
                    order.company_id, order.partner_id.commercial_partner_id, order.currency_id, order.l10n_it_edi_doi_date,
                    only_blocking=True, sales_order=True,
                )
                errors.extend(validity_warnings)

            declaration_of_intent_tax = order.company_id.l10n_it_edi_doi_tax_id
            if not declaration_of_intent_tax:
                continue
            declaration_tax_lines = order.order_line.filtered(
                lambda line: declaration_of_intent_tax in line.tax_id
            )
            if declaration_tax_lines and not order.l10n_it_edi_doi_id:
                errors.append(_('Given the tax %s is applied, there should be a Declaration of Intent selected.',
                                declaration_of_intent_tax.name))
            if any(line.tax_id != declaration_of_intent_tax for line in declaration_tax_lines):
                errors.append(_('A line using tax %s should not contain any other taxes',
                                declaration_of_intent_tax.name))
        if errors:
            raise UserError('\n'.join(errors))

    def action_quotation_send(self):
        self._l10n_it_edi_doi_check_configuration()
        return super().action_quotation_send()

    def action_quotation_sent(self):
        self._l10n_it_edi_doi_check_configuration()
        return super().action_quotation_sent()

    def action_confirm(self):
        self._l10n_it_edi_doi_check_configuration()
        return super().action_confirm()

    @api.constrains('l10n_it_edi_doi_id')
    def _check_l10n_it_edi_doi_id(self):
        for order in self:
            declaration = order.l10n_it_edi_doi_id
            if not declaration:
                return
            partner = order.partner_id.commercial_partner_id
            errors = declaration._get_validity_warnings(
                order.company_id, partner, order.currency_id, order.l10n_it_edi_doi_date, only_blocking=True, sales_order=True
            )
            if errors:
                raise ValidationError('\n'.join(errors))

    def action_open_declaration_of_intent(self):
        self.ensure_one()
        return {
            'name': _("Declaration of Intent for %s", self.display_name),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'l10n_it_edi_doi.declaration_of_intent',
            'res_id': self.l10n_it_edi_doi_id.id,
        }

    def _l10n_it_edi_doi_get_amount_not_yet_invoiced(self, declaration, additional_invoiced_qty=None):
        """
        Consider sales orders in self that use declaration of intent `declaration`.
        For each sales order we compute the amount that is tax exempt due to the declaration of intent
        (line has special declaration of intent tax applied) but not yet invoiced.
        For each line of the SO we i.e. use the not yet invoiced quantity to compute this amount.
        The aforementioned quantity is computed from field `qty_invoiced_posted` and parameter `additional_invoiced_qty`
        Return the sum of all these amounts on the SOs.
        :param declaration:             We only consider sales orders using Declaration of Intent `declaration`.
        :param additional_invoiced_qty: Dictionary (sale order line id -> float)
                                        The float represents additional invoiced amount qty for the sale order.
                                        This can i.e. be used to simulate posting an already linked invoice.
        """
        if not declaration:
            return 0

        if additional_invoiced_qty is None:
            additional_invoiced_qty = {}

        tax = declaration.company_id.l10n_it_edi_doi_tax_id
        if not tax:
            return 0

        not_yet_invoiced = 0
        for order in self:
            if declaration != order.l10n_it_edi_doi_id:
                continue

            order_lines = order.order_line.filtered(
                # The declaration tax cannot be used with other taxes on a single line
                # (checked in `action_confirm`)
                lambda line: line.tax_id.ids == tax.ids
            )
            order_not_yet_invoiced = 0
            for line in order_lines:
                price_reduce = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                qty_invoiced = line.qty_invoiced_posted
                if line.ids and additional_invoiced_qty:
                    qty_invoiced += additional_invoiced_qty.get(line.ids[0], 0)
                qty_to_invoice = line.product_uom_qty - qty_invoiced
                order_not_yet_invoiced += price_reduce * qty_to_invoice
            if declaration.currency_id.compare_amounts(order_not_yet_invoiced, 0) > 0:
                not_yet_invoiced += order_not_yet_invoiced

        return not_yet_invoiced
