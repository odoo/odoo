from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_dk_currency_rate_at_transaction = fields.Float(
        string='Rate',
        compute='_compute_currency_rate_at_transaction', readonly=True, store=True,
        digits=0,
    )
    l10n_dk_show_currency_rate = fields.Boolean(compute='_compute_show_currency_rate')

    @api.depends('line_ids')
    def _compute_currency_rate_at_transaction(self):
        for record in self:
            if record.line_ids:
                record.l10n_dk_currency_rate_at_transaction = record.line_ids[0].currency_rate

    @api.depends('country_code', 'company_currency_id', 'currency_id', 'line_ids')
    def _compute_show_currency_rate(self):
        for record in self:
            record.l10n_dk_show_currency_rate = record.country_code == 'DK' and record.company_currency_id != record.currency_id and record.line_ids
