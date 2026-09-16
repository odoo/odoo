# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields
from odoo.tools.sql import column_exists, create_column


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        result = super()._get_l10n_latam_documents_domain()
        if self.company_id.country_id.code != "PE" or not self.journal_id.l10n_latam_use_documents or self.journal_id.type != "sale":
            return result
        result.append(("code", "in", ("01", "03", "07", "08", "20", "40")))
        if self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code != '6' and self.move_type == 'out_invoice':
            result.append(('id', 'in', (
                self.env.ref('l10n_pe.document_type08b')
                | self.env.ref('l10n_pe.document_type02')
                | self.env.ref('l10n_pe.document_type07b')
            ).ids))
        return result

    @api.onchange('l10n_latam_document_type_id', 'l10n_latam_document_number', 'partner_id')
    def _inverse_l10n_latam_document_number(self):
        """Inherit to complete the l10n_latam_document_number with the expected 8 characters after that a '-'
        Example: Change FFF-32 by FFF-00000032, to avoid incorrect values on the reports"""
        super()._inverse_l10n_latam_document_number()
        to_review = self.filtered(
            lambda x: x.journal_id.type == "purchase"
            and x.l10n_latam_document_type_id.code in ("01", "03", "07", "08")
            and x.l10n_latam_document_number
            and "-" in x.l10n_latam_document_number
            and x.l10n_latam_document_type_id.country_id.code == "PE"
        )
        for rec in to_review:
            number = rec.l10n_latam_document_number.split("-")
            rec.l10n_latam_document_number = "%s-%s" % (number[0], number[1].zfill(8))


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_pe_group_id = fields.Many2one("account.group", related="account_id.group_id", store=True)

    def _auto_init(self):
        """
        Create column to stop ORM from computing it himself (too slow)
        """
        if not column_exists(self.env.cr, self._table, 'l10n_pe_group_id'):
            create_column(self.env.cr, self._table, 'l10n_pe_group_id', 'int4')
            self.env.cr.execute("""
                UPDATE account_move_line line
                SET l10n_pe_group_id = account.group_id
                FROM account_account account
                WHERE account.id = line.account_id
            """)
        return super()._auto_init()

    @api.depends('move_id.reversed_entry_id', 'move_id.debit_origin_id')
    def _compute_currency_rate(self):
        super()._compute_currency_rate()

    def _get_rate_date(self):
        # EXTENDS 'account'
        self.ensure_one()
        move = self.move_id
        origin_move = move.reversed_entry_id or move.debit_origin_id
        if move.country_code == 'PE' and move.is_invoice(include_receipts=True) and origin_move.invoice_date:
            # In Peru, credit and debit notes use the currency rate of the document they modify, which can be a note too.
            while (origin_move.reversed_entry_id or origin_move.debit_origin_id).invoice_date:
                origin_move = origin_move.reversed_entry_id or origin_move.debit_origin_id
            return origin_move.invoice_date
        return super()._get_rate_date()
