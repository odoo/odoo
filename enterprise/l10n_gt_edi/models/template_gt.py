from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('gt', 'account.tax')
    def _get_gt_edi_account_tax(self):
        res = self._parse_csv('gt', 'account.tax', module='l10n_gt_edi')
        # Update the taxes created in l10n_gt module that can't be put inside the same CSV file here.
        res.update({
            'impuestos_plantilla_iva_por_cobrar': {
                'l10n_gt_edi_taxable_unit_code': 1,
                'l10n_gt_edi_short_name': 'IVA',
                'sequence': 1,
            },
            'impuestos_plantilla_iva_por_pagar': {
                'l10n_gt_edi_taxable_unit_code': 1,
                'l10n_gt_edi_short_name': 'IVA',
                'sequence': 2,
            },
            'tax_vat_withhold': {
                'sequence': 11,
            },
            'tax_isr_withhold': {
                'sequence': 12,
            },
        })
        return res

    @template('gt', 'account.fiscal.position')
    def _get_gt_edi_account_fiscal_position(self):
        return self._parse_csv('gt', 'account.fiscal.position', module='l10n_gt_edi')
