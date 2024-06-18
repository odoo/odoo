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
    l10n_pl_delivery_date_onchange = fields.Boolean(
        compute='_compute_delivery_date_onchange',
        export_string_translation=False,
    )

    @api.depends('delivery_date')
    def _compute_show_delivery_date(self):
        for move in self:
            move.show_delivery_date = move.delivery_date

    @api.depends('delivery_date')
    def _compute_delivery_date_onchange(self):
        for move in self:
            move.show_delivery_date = move.delivery_date

    @api.depends('l10n_pl_delivery_date_onchange')
    def _compute_date(self):
        super()._compute_date()
        for move in self:
            if move.delivery_date:
                if move.invoice_filter_type_domain == 'sale':
                    move.date = move.delivery_date
                elif move.invoice_filter_type_domain == 'purchase':
                    move.date = min(move.delivery_date, move.invoice_date)
                self.env.add_to_compute(move.line_ids._fields['date'], move.line_ids)
                self.env.add_to_compute(self._fields['name'], move)

    def action_post(self):
        for move in self:
            affects_tax_report = move._affect_tax_report()
            lock_dates = move._get_violated_lock_dates(move.date, affects_tax_report)
            if lock_dates:
                move.date = move._get_accounting_date(move.invoice_date or move.date, affects_tax_report)
                move.delivery_date = move._get_accounting_date(move.invoice_date or move.delivery_date, affects_tax_report)
        return super().action_post()
