# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template

class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pe', 'account.tax.group')
    def _get_pe_edi_account_tax_group(self):
        return {
            'tax_group_igv': {'l10n_pe_edi_code': 'IGV'},
            'tax_group_ivap': {'l10n_pe_edi_code': 'IVAP'},
            'tax_group_isc': {'l10n_pe_edi_code': 'ISC'},
            'tax_group_exp': {'l10n_pe_edi_code': 'EXP'},
            'tax_group_gra': {'l10n_pe_edi_code': 'GRA'},
            'tax_group_exo': {'l10n_pe_edi_code': 'EXO'},
            'tax_group_ina': {'l10n_pe_edi_code': 'INA'},
            'tax_group_other': {'l10n_pe_edi_code': 'OTROS'},
            'tax_group_det': {'l10n_pe_edi_code': 'DET'},
            'tax_group_icbper': {'l10n_pe_edi_code': 'ICBPER'},
            'tax_group_igv_g_ng': {'l10n_pe_edi_code': 'IGV'},
            'tax_group_igv_ng': {'l10n_pe_edi_code': 'IGV'},
        }
