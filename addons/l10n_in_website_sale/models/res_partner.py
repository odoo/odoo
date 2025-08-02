from odoo import models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _update_l10n_in_gst_treatment_and_fp_from_iap_autocomplete(self):
        response = self.env['res.partner'].enrich_by_gst(self.vat)
        if response.get('error'):
            return
        gst_treatment = response.get('l10n_in_gst_treatment', 'regular')
        fiscal_position = (
            gst_treatment == 'special_economic_zone'
            and self.env['account.chart.template'].ref('fiscal_position_in_export_sez_in', raise_if_not_found=False)
        )
        self.update({
            'l10n_in_gst_treatment': gst_treatment,
            'property_account_position_id': fiscal_position and fiscal_position.id or False
        })
