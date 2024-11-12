# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

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

    l10n_it_edi_doi_amount = fields.Monetary(
        string='Declaration of Intent Amount',
        compute='_compute_l10n_it_edi_doi_amount',
        store=True,
        readonly=True,
        help="Total amount of sales under the Declaration of Intent of this document",
    )

    l10n_it_edi_doi_warning = fields.Text(
        string="Declaration of Intent Threshold Warning",
        compute='_compute_l10n_it_edi_doi_warning',
    )

    @api.depends('invoice_date')
    def _compute_l10n_it_edi_doi_date(self):
        for move in self:
            move.l10n_it_edi_doi_date = move.invoice_date or fields.Date.context_today(self)

    @api.depends('l10n_it_edi_doi_id', 'country_code', 'move_type')
    def _compute_l10n_it_edi_doi_use(self):
        sale_types = self.env['account.move'].get_sale_types()
        for move in self:
            move.l10n_it_edi_doi_use = (
                move.l10n_it_edi_doi_id
                or (move.country_code == "IT" and move.move_type in sale_types)
            )

    @api.depends('company_id', 'partner_id.commercial_partner_id', 'l10n_it_edi_doi_date', 'currency_id')
    def _compute_l10n_it_edi_doi_id(self):
        for move in self:
            if not move.l10n_it_edi_doi_use or move.state != 'draft' and not move.l10n_it_edi_doi_id:
                move.l10n_it_edi_doi_id = False
                continue
            partner = move.partner_id.commercial_partner_id

            # Avoid a query or changing a manually set declaration of intent
            # (if the declaration is still valid).
            validity_warnings = move.l10n_it_edi_doi_id._get_validity_warnings(
                move.company_id, partner, move.currency_id, move.l10n_it_edi_doi_date
            )
            if move.l10n_it_edi_doi_id and not validity_warnings:
                continue

            declaration = self.env['l10n_it_edi_doi.declaration_of_intent']\
                ._fetch_valid_declaration_of_intent(move.company_id, partner, move.currency_id, move.l10n_it_edi_doi_date)
            move.l10n_it_edi_doi_id = declaration

    @api.depends('l10n_it_edi_doi_id', 'tax_totals', 'move_type')
    def _compute_l10n_it_edi_doi_amount(self):
        """
        Consider all the lines in self that belong to declaration of intent `declaration`
        and have the special declaration of intent tax applied.
        This function computes the signed sum of the price_total of all those lines
        (the tax amount of the lines is always 0).
        The direction_sign determines the sign: 1 (-1) for inbound (outbound) types.
        """
        for move in self:
            tax = move.company_id.l10n_it_edi_doi_tax_id
            if not tax or not move.l10n_it_edi_doi_id:
                move.l10n_it_edi_doi_amount = 0
                continue
            declaration_lines = move.invoice_line_ids.filtered(
                # The declaration tax cannot be used with other taxes on a single line
                # (checked in `_post`)
                lambda line: line.tax_ids.ids == tax.ids
            )
            move.l10n_it_edi_doi_amount = sum(declaration_lines.mapped('price_total')) * -move.direction_sign

    @api.depends('l10n_it_edi_doi_id', 'l10n_it_edi_doi_amount', 'state')
    def _compute_l10n_it_edi_doi_warning(self):
        for move in self:
            move.l10n_it_edi_doi_warning = ''
            declaration = move.l10n_it_edi_doi_id

            show_warning = (
                declaration
                and move.is_sale_document(include_receipts=False)
                and move.state != 'cancel'
            )
            if not show_warning:
                continue

            declaration_invoiced = declaration.invoiced
            declaration_not_yet_invoiced = declaration.not_yet_invoiced
            if move.state != 'posted':  # exactly the 'posted' invoices are included in declaration.invoiced
                # Here we replicate what would happen when posting the invoice.
                # Note: lines manually added to a move linked to a sales order are not added to the sales order
                declaration_invoiced += move.l10n_it_edi_doi_amount
                additional_invoiced_qty = {}
                linked_orders = self.env['sale.order']
                for invoice_line in move.invoice_line_ids:
                    for sale_line in invoice_line.sale_line_ids:
                        order = sale_line.order_id
                        if order.l10n_it_edi_doi_id == declaration:
                            linked_orders |= order
                        qty_invoiced = invoice_line.product_uom_id._compute_quantity(invoice_line.quantity, sale_line.product_uom_id) * -move.direction_sign
                        sale_line_id = sale_line.ids[0]  # do not just use `id` in case of NewId
                        additional_invoiced_qty[sale_line_id] = additional_invoiced_qty.get(sale_line_id, 0) + qty_invoiced
                for order in linked_orders:
                    not_yet_invoiced = order.l10n_it_edi_doi_not_yet_invoiced
                    not_yet_invoiced_after_posting = order._l10n_it_edi_doi_get_amount_not_yet_invoiced(
                        declaration,
                        additional_invoiced_qty=additional_invoiced_qty,
                    )
                    declaration_not_yet_invoiced -= not_yet_invoiced - not_yet_invoiced_after_posting

            validity_warnings = declaration._get_validity_warnings(
                move.company_id, move.commercial_partner_id, move.currency_id, move.l10n_it_edi_doi_date,
                invoiced_amount=declaration_invoiced,
            )

            threshold_warning = declaration._build_threshold_warning_message(declaration_invoiced, declaration_not_yet_invoiced)

            move.l10n_it_edi_doi_warning = '{}\n\n{}'.format('\n'.join(validity_warnings), threshold_warning).strip()

    @api.depends('l10n_it_edi_doi_id')
    def _compute_fiscal_position_id(self):
        super()._compute_fiscal_position_id()
        for move in self:
            declaration_fiscal_position = move.company_id.l10n_it_edi_doi_fiscal_position_id
            if declaration_fiscal_position and move.l10n_it_edi_doi_id:
                move.fiscal_position_id = declaration_fiscal_position

    def copy_data(self, default=None):
        data_list = super().copy_data(default)
        for move, data in zip(self, data_list):
            date = fields.Date.context_today(self)
            validity_warnings = move.l10n_it_edi_doi_id._get_validity_warnings(
                move.company_id, move.commercial_partner_id, move.currency_id, date,
                only_blocking=True,
            )
            if validity_warnings:
                del data['l10n_it_edi_doi_id']
                del data['fiscal_position_id']
        return data_list

    @api.constrains('l10n_it_edi_doi_id')
    def _check_l10n_it_edi_doi_id(self):
        for move in self:
            validity_errors = move.l10n_it_edi_doi_id._get_validity_errors(
                move.company_id, move.partner_id.commercial_partner_id, move.currency_id
            )
            if validity_errors:
                raise UserError('\n'.join(validity_errors))

    def _post(self, soft=True):
        errors = []
        for move in self:
            declaration = move.l10n_it_edi_doi_id
            if declaration:
                validity_warnings = declaration._get_validity_warnings(
                    move.company_id, move.commercial_partner_id, move.currency_id, move.l10n_it_edi_doi_date,
                    invoiced_amount=move.l10n_it_edi_doi_amount,
                    only_blocking=True
                )
                errors.extend(validity_warnings)

            declaration_of_intent_tax = move.company_id.l10n_it_edi_doi_tax_id
            if not declaration_of_intent_tax:
                continue

            declaration_lines = move.invoice_line_ids.filtered(
                lambda line: declaration_of_intent_tax in line.tax_ids
            )
            if declaration_lines and not declaration:
                errors.append(_('Given the tax %s is applied, there should be a Declaration of Intent selected.',
                                declaration_of_intent_tax.name))
            if any(line.tax_ids != declaration_of_intent_tax for line in declaration_lines):
                errors.append(_('A line using tax %s should not contain any other taxes',
                                declaration_of_intent_tax.name))
        if errors:
            raise UserError('\n'.join(errors))

        return super()._post(soft)

    def action_open_declaration_of_intent(self):
        self.ensure_one()
        return {
            'name': _("Declaration of Intent for %s", self.display_name),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'l10n_it_edi_doi.declaration_of_intent',
            'res_id': self.l10n_it_edi_doi_id.id,
        }
