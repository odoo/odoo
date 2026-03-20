# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_name_invoice_report(self):
        if self.company_id.account_fiscal_country_id.code == 'AU' and self.company_id.l10n_au_is_gst_registered:
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
