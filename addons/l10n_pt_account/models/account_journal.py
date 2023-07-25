from odoo import models, fields, _
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    l10n_pt_account_invoice_official_series_id = fields.Many2one("l10n_pt_account.official.series", string="Official Series for Invoices")
    l10n_pt_account_refund_official_series_id = fields.Many2one("l10n_pt_account.official.series", string="Official Series for Refunds")

    def _prepare_liquidity_account_vals(self, company, code, vals):
        account_vals = super()._prepare_liquidity_account_vals(company, code, vals)
        if company.account_fiscal_country_id.code == 'PT':
            if vals.get('type') == 'cash':
                account_vals['l10n_pt_taxonomy_code'] = 1
            elif vals.get('type') == 'bank':
                account_vals['l10n_pt_taxonomy_code'] = 2
        return account_vals

    def write(self, vals):
        res = super().write(vals)
        for journal in self:
            if (
                (vals.get('l10n_pt_account_invoice_official_series_id') and journal.l10n_pt_account_invoice_official_series_id)
                or
                (vals.get('l10n_pt_account_refund_official_series_id') and journal.l10n_pt_account_refund_official_series_id)
            ):
                if self.env['account.move'].search_count([('journal_id', '=', journal.id)]):
                    raise UserError(_("You cannot change the official series of a journal once it has been used."))
        return res
