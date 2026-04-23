# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    def _get_simplified_journal(self):
        # Retieve the simplified journal or create it if it doesn't exist.
        journal_id = self.env["ir.config_parameter"].sudo().get_int('l10n_es_ecommerce.default_simplified_journal_id')

        if journal_id:
            if journal := self.env['account.journal'].browse(int(journal_id)).exists():
                return self._ensure_simplified_income_account(journal)

        # Not configured or deleted - Search or create
        journal = self.env['account.journal'].search([
            ('code', '=', 'SINV'),
            ('company_id', '=', self.company_id.id),
        ])
        if not journal:
            journal = self.env['account.journal'].sudo().create({
                'name': 'Simplified Journal',
                'code': 'SINV',
                'type': 'sale',
                'sequence': 99,
                'alias_name': 'sale_simplified',
            })
            # Safe to avoid creating it again
            self.env['ir.config_parameter'].sudo().set_int('l10n_es_ecommerce.default_simplified_journal_id', journal.id)

        return self._ensure_simplified_income_account(journal)

    def _ensure_simplified_income_account(self, journal):
        """Make sure the simplified journal's default income account matches the
        regular Sales journal. Runs every time the journal is fetched so that
        journals created before this behaviour existed get fixed too. Falls back
        to the company income account, which is what the Sales journal uses.
        """
        if journal and not journal.default_account_id:
            sale_journal = self.env['account.journal'].sudo().search(
                [
                    *self.env['account.journal']._check_company_domain(journal.company_id),
                    ('type', '=', 'sale'),
                    ('id', '!=', journal.id),
                ],
                order='sequence, id',
                limit=1,
            )
            account = sale_journal.default_account_id or journal.company_id.income_account_id
            if account:
                journal.sudo().default_account_id = account
        return journal

    def _create_account_invoices(self, invoice_vals_list):
        res = super()._create_account_invoices(invoice_vals_list)
        simplified_invoice_limit = self.env['ir.config_parameter'].sudo().search([('key', '=', 'l10n_es_ecommerce.simplified_invoice_limit')], limit=1)
        try:
            threshold_amount = float(simplified_invoice_limit.value)
        except (ValueError, TypeError):
            threshold_amount = 400.0
        for move in res:
            if move.country_code == 'ES' and move.amount_total < threshold_amount:
                move['journal_id'] = self._get_simplified_journal()
        return res
