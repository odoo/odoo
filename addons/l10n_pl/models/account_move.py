from odoo import api, fields, models

MAX_AMOUNT_MPP = 15000


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
    l10n_pl_mpp = fields.Selection(
        selection=[('mpp', 'MPP'), ('no_mpp', 'No MPP')],
        compute='_compute_l10n_pl_mpp',
        store=True, copy=False,
    )
    l10n_pl_show_mpp = fields.Boolean(
        compute='_compute_l10n_pl_show_mpp',
    )
    l10n_pl_show_mpp_warning = fields.Boolean(
        compute='_compute_l10n_pl_show_mpp_warning',
    )
    l10n_pl_mpp_label = fields.Char(
        compute='_compute_l10n_pl_mpp_label',
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

    @api.depends(
        'l10n_pl_show_mpp',
        'commercial_partner_id.is_company',
        'amount_residual',
        'invoice_line_ids.product_id',
    )
    def _compute_l10n_pl_mpp(self):
        for move in self:
            move.l10n_pl_mpp = 'mpp' if move._is_mpp_mandatory() else 'no_mpp'

    def _is_mpp_mandatory(self):
        """
        The field MPP is mandatory if those 3 conditions are satisfied:
            * The transaction is B2B
            * The gross total reaches PLN 15,000 (=MAX_AMOUNT_MPP)
            * The invoice includes at least one 'split_payment' product
        """
        self.ensure_one()

        return (
            self.l10n_pl_show_mpp and
            self.commercial_partner_id.is_company and
            self.amount_residual >= MAX_AMOUNT_MPP and
            any(
                line.product_id.l10n_pl_split_payment
                for line in self.invoice_line_ids
            )
        )

    @api.depends('fiscal_position_id', 'currency_id')
    def _compute_l10n_pl_show_mpp(self):
        """
        The MPP field is shown when:
            * The fiscal position is Domestic
            * The currency is PLN
        """
        for move in self:
            move.l10n_pl_show_mpp = move.fiscal_position_id.is_domestic and move.currency_id.name == 'PLN'

    @api.depends('l10n_pl_mpp')
    def _compute_l10n_pl_show_mpp_warning(self):
        """
        Warning if MPP not checked when it is mandatory
        """
        for move in self:
            move.l10n_pl_show_mpp_warning = move._is_mpp_mandatory() and move.l10n_pl_mpp == 'no_mpp'

    @api.depends('l10n_pl_mpp', 'move_type')
    def _compute_l10n_pl_mpp_label(self):
        for move in self:
            if move.l10n_pl_mpp == 'mpp' and move.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                move.l10n_pl_mpp_label = "Mechanizm podzielonej płatności"
            else:
                move.l10n_pl_mpp_label = False

    def _get_accounting_date_source(self):
        return (self.country_code == 'PL' and self.taxable_supply_date) or super()._get_accounting_date_source()

    def _get_invoice_currency_rate_date(self):
        return (self.country_code == 'PL' and self.taxable_supply_date) or super()._get_invoice_currency_rate_date()

    def _get_default_currency_rate_date(self):
        return (self.country_code == 'PL' and self.taxable_supply_date) or super()._get_default_currency_rate_date()
