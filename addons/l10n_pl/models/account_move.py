from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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

    def action_post(self):
        "Validation to avoid having credit notes with more than the invoice"
        if self.filtered(lambda record: record.country_code == 'PL' and record.reversed_entry_id and
                record.reversed_entry_id.amount_total < record.amount_total and record.move_type != 'entry'):
            raise ValidationError(_("Credit notes can't have a total amount greater than the invoice's"))
        return super().action_post()

    @api.depends('delivery_date')
    def _compute_show_delivery_date(self):
        # EXTENDS 'account'
        pl_moves = self.filtered(lambda move: move.country_code == 'PL')
        for move in pl_moves:
            move.show_delivery_date = bool(move.delivery_date)
        super(AccountMove, self - pl_moves)._compute_show_delivery_date()

    @api.depends('delivery_date')
    def _compute_date(self):
        # EXTENDS 'account'
        pl_drafts = self.filtered(lambda move:
            move.country_code == 'PL'
            and move.delivery_date
            and move.state == 'draft'
        )
        for move in pl_drafts:
            accounting_date = move.date
            if move.is_sale_document(True):
                accounting_date = move.delivery_date
            elif move.is_purchase_document(True):
                accounting_date = min(move.delivery_date, move.date or move.invoice_date or fields.Date.context_today(self))
            if accounting_date and accounting_date != move.date:
                move.date = move._get_accounting_date(accounting_date, move._affect_tax_report())
                # non purchase/sale shouldn't have a delivery_date
                # _affect_tax_report may trigger premature recompute of line_ids.date
                self.env.add_to_compute(move.line_ids._fields['date'], move.line_ids)
                # might be protected because `_get_accounting_date` requires the `name`
                self.env.add_to_compute(self._fields['name'], move)
        super(AccountMove, self - pl_drafts)._compute_date()
