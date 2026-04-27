from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ma_reports_payment_method = fields.Selection(
        [
            ('1', 'Cash'),
            ('2', 'Check'),
            ('3', 'Direct Debit'),
            ('4', 'Bank Transfer'),
            ('5', 'Bill of Exchange'),
            ('6', 'Compensation'),
            ('7', 'Others'),
        ],
        string='Payment Channel',
        compute='_compute_l10n_ma_reports_payment_method',
        help='Payment method for Moroccan EDI. If left empty it will default to "Other" on the EDI declaration.'
    )

    @api.depends('origin_payment_id')
    def _compute_l10n_ma_reports_payment_method(self):
        for move in self:
            payments = move.sudo()._get_reconciled_payments()
            if payments:
                move.l10n_ma_reports_payment_method = payments.sorted(lambda p: p.date)[-1].l10n_ma_reports_payment_method
            else:
                move.l10n_ma_reports_payment_method = False
