from odoo import models, _
from odoo.exceptions import RedirectWarning


class CzechTaxReportCustomHandler(models.AbstractModel):
    """
        Generate the VAT report for the Czech Republic.
        Generated using as a reference the documentation at
        https://adisspr.mfcr.cz/dpr/adis/idpr_pub/epo2_info/popis_struktury_detail.faces?zkratka=DPHDP3
    """
    _name = 'l10n_cz.tax.report.handler'
    _inherit = 'account.tax.report.handler'
    _description = 'Czech Tax Report Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        options.setdefault('buttons', []).append({
            'name': _('XML'),
            'sequence': 30,
            'action': 'export_file',
            'action_param': 'export_to_xml',
            'file_export_type': _('XML'),
        })

    def export_to_xml(self, options):
        raise RedirectWarning(
            message=_('Please install the module "Czech Republic - Accounting Reports 2025" to have this functionality.'),
            action=self.env['ir.module.module'].search(
                domain=[('name', '=', 'l10n_cz_reports_2025'), ('state', '=', 'uninstalled')],
                limit=1,
            )._get_records_action(),
            button_text=_('Install "Czech Republic - Accounting Reports 2025"'),
        )
