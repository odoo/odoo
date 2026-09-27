from odoo import models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    def _l10n_fr_pdp_is_oss(self):
        """Return whether the tax was generated for the EU OSS scheme."""
        self.ensure_one()
        # l10n_eu_oss is optional: avoid introducing a stable dependency while
        # still recognizing the taxes it generates when it is installed.
        oss_tag = self.env.ref('l10n_eu_oss.tag_oss', raise_if_not_found=False)
        repartition_tags = (self.invoice_repartition_line_ids | self.refund_repartition_line_ids).tag_ids
        return bool(oss_tag and oss_tag in repartition_tags)
