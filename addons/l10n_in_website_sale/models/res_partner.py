from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _update_l10n_in_gst_treatment_and_fp_from_iap_autocomplete(self):
        sez_fp = self.env['account.chart.template'].ref('fiscal_position_in_export_sez_in', raise_if_not_found=False)
        response = self.env['res.partner'].enrich_by_gst(self.vat) if self.vat else {}

        # Response is empty when GSTIN is invalid or removed.
        if not response:
            self.l10n_in_gst_treatment = 'consumer'
            if self.property_account_position_id == sez_fp:
                self.property_account_position_id = False
            return

        if response.get('error'):
            return

        gst_treatment = response.get('l10n_in_gst_treatment', 'regular')
        if sez_fp and (not self.property_account_position_id or self.property_account_position_id == sez_fp):
            self.property_account_position_id = sez_fp.id if gst_treatment == 'special_economic_zone' else False
        self.l10n_in_gst_treatment = gst_treatment
