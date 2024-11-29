# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


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

    @api.onchange('l10n_latam_document_type_id', 'l10n_latam_document_number')
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
