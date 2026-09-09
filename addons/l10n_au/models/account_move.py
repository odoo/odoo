# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_name_invoice_report(self):
        if self.company_id.account_fiscal_country_id.code == 'AU':
            return 'l10n_au.report_invoice_document'
        return super()._get_name_invoice_report()

    def _get_automatic_balancing_account(self):
        """ Override to manage the DGST use case.
        We want the automatic line to balance the DGST account to itself, as we only want the tax lines to have a real
        impact.
        """
        # OVERRIDE account
        self.ensure_one()

        # We only consider moves comprised of a single DGST line. (one invoice line, one tax)
        has_single_line = len(self.invoice_line_ids) == 1 and len(self.invoice_line_ids.tax_ids) == 1
        if has_single_line and self.move_type == 'entry':
            # We identify that it is DGST based on a tag on the account.
            # This is the simplest solution to keep it configurable while avoiding a new setting for a niche feature.
            # At worse, they don't get the correct account assigned automatically and need manual adjustment.
            with_dgst_account = self.invoice_line_ids.account_id.tag_ids == self.env.ref("l10n_au.account_tag_dgst")
            if with_dgst_account:
                # In this case, we want the balancing line to balance IN THE SAME ACCOUNT.
                return self.invoice_line_ids.account_id.id
        return super()._get_automatic_balancing_account()

    def _get_document_title(self, proforma=False, is_debit_note=False):
        self.ensure_one()

        if (
            self.company_id.account_fiscal_country_id.code != 'AU'
            or is_debit_note
            or not self.company_id.l10n_au_is_gst_registered
        ):
            return super()._get_document_title(proforma=proforma, is_debit_note=is_debit_note)

        if self.move_type == 'out_invoice':
            doc_name = self.env._("Tax Invoice")
        elif self.move_type == 'out_refund':
            doc_name = self.env._("Tax Credit Note")
        elif self.move_type == 'in_refund':
            doc_name = self.env._("Tax Vendor Credit Note")
        elif self.move_type == 'in_invoice':
            doc_name = self.env._("Tax Vendor Bill")
        else:
            doc_name = ""

        if proforma:
            doc_name = self.env._("Proforma %(doc_name)s", doc_name=doc_name)

        if self.is_sale_document():
            if self.state == 'draft':
                doc_name = self.env._("Draft %(doc_name)s", doc_name=doc_name)
            elif self.state == 'cancel':
                doc_name = self.env._("Cancelled %(doc_name)s", doc_name=doc_name)

        return doc_name
