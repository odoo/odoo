# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_account_invoices(self, invoice_vals_list):
        """Route qualifying eCommerce invoices to the simplified journal.

        Whether an invoice is a simplified one is already computed by l10n_es
        (``account.move.l10n_es_is_simplified``): Spanish company, customer
        without VAT, amount below ``company.l10n_es_simplified_invoice_limit``
        and an EU country. When that flag is set we switch the freshly-created
        draft move to the simplified journal configured on the originating
        website, falling back to the company's ``SINV`` journal (created by
        the Spanish Chart of Accounts) when there is no website.
        """
        moves = super()._create_account_invoices(invoice_vals_list)
        for move in moves:
            if self.journal_id:
                continue
            if not move.l10n_es_is_simplified:
                continue
            website = move.invoice_line_ids.sale_line_ids.order_id.website_id[:1]
            journal = website.simplified_invoice_journal_id or self.env['account.journal'].sudo().search([
                *self.env['account.journal']._check_company_domain(move.company_id),
                ('type', '=', 'sale'),
                ('code', '=', 'SINV'),
            ], limit=1)
            if journal and move.journal_id != journal:
                move.journal_id = journal
        return moves
