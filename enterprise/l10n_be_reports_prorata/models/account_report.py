from odoo import models


class BelgianTaxReportCustomHandler(models.AbstractModel):
    _inherit = 'l10n_be.tax.report.handler'
    _description = 'Belgian Tax Report Custom Prorata Handler'

    def _get_deduction_text(self, options):
        # OVERRIDES 'l10n_be_reports'
        deduction_dict = options.get('prorata_deduction', {})
        if not deduction_dict.get('prorata'):
            return super()._get_deduction_text(options)

        return self.env['ir.qweb']._render('l10n_be_reports_prorata.vat_export_prorata', deduction_dict)
