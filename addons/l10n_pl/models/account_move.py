from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_pl_vat_b_spv = fields.Boolean(
        string='B_SPV',
        help="Transfer of a single-purpose voucher effected by a taxable person acting on his/its own behalf",
    )
    l10n_pl_vat_b_spv_dostawa = fields.Boolean(
        string='B_SPV_Dostawa',
        help="Supply of goods and/or services covered by a single-purpose voucher to a taxpayer",
    )
    l10n_pl_vat_b_mpv_prowizja = fields.Boolean(
        string='B_MPV_Prowizja',
        help="Supply of agency and other services pertaining to the transfer of a single-purpose voucher",
    )
    l10n_pl_mpp = fields.Boolean(
        string='MPP',
        compute='_compute_l10n_pl_mpp',
        default=False, store=True, copy=False,
        help="Split Payment Mechanism, indicates if a split payment is necessary",
    )
    l10n_pl_mpp_mode = fields.Selection([
        ('auto', 'Automatic'),
        ('manual', 'Manual'),
    ], default='auto', copy=False,
    )
    l10n_pl_is_currency_PLN = fields.Boolean(
        compute='_compute_l10n_pl_is_currency_PLN',
    )
    l10n_pl_show_mpp_warning = fields.Boolean(
        compute='_compute_l10n_pl_show_mpp_warning',
    )

    @api.depends('country_code')
    def _compute_show_taxable_supply_date(self):
        super()._compute_show_taxable_supply_date()
        for move in self.filtered(lambda m: m.country_code == 'PL' and m.move_type != 'entry' and (m.state == 'draft' or m.taxable_supply_date)):
            move.show_taxable_supply_date = True

    @api.depends('country_code')
    def _compute_taxable_supply_date_placeholder(self):
        super()._compute_taxable_supply_date_placeholder()
        for move in self.filtered(lambda m: m.country_code == 'PL'):
            move.taxable_supply_date_placeholder = self.env._("Invoice Date")

    @api.depends('invoice_line_ids', 'invoice_line_ids.price_subtotal', 'invoice_line_ids.product_id')
    def _compute_l10n_pl_mpp(self):
        for move in self:
            if move.l10n_pl_mpp_mode == 'manual':
                continue
            move.l10n_pl_mpp = (
                move.l10n_pl_is_currency_PLN and
                (sum(line.price_subtotal for line in move.invoice_line_ids) >= 15000 or
                 move._contains_subject_to_split_payment_product())
            )

    def _contains_subject_to_split_payment_product(self):
        for line in self.invoice_line_ids:
            if line.product_id.l10n_pl_subject_to_split_payment or line.product_id.categ_id.l10n_pl_subject_to_split_payment:
                return True
        return False

    @api.depends('currency_id')
    def _compute_l10n_pl_is_currency_PLN(self):
        for move in self:
            move.l10n_pl_is_currency_PLN = move.currency_id.name == 'PLN'

    @api.depends('l10n_pl_mpp')
    def _compute_l10n_pl_show_mpp_warning(self):
        """
        Warning if:
            * The invoice total amount is > 15000,
            * The invoice contains at least one subject to split payment product,
            * And the MPP is not checked (unchecked by the user)
        """
        for move in self:
            move.l10n_pl_show_mpp_warning = (
                not move.l10n_pl_mpp and
                sum(line.price_subtotal for line in move.invoice_line_ids) >= 15000 and
                move._contains_subject_to_split_payment_product()
            )

    def _get_accounting_date_source(self):
        self.ensure_one()
        if self.country_code == 'PL' and self.taxable_supply_date:
            return self.taxable_supply_date
        return super()._get_accounting_date_source()

    def _get_invoice_currency_rate_date(self):
        self.ensure_one()
        if self.country_code == 'PL' and self.taxable_supply_date:
            return self.taxable_supply_date
        return super()._get_invoice_currency_rate_date()

    def write(self, vals):
        """
        When the user explicitly changes the value of the MPP field,
        deactivate the automatic computation of the field.
        """
        if 'l10n_pl_mpp' in vals:
            vals['l10n_pl_mpp_mode'] = 'manual'

        return super().write(vals)
