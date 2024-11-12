# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @api.model
    def _get_ar_responsibility_match(self, chart_template):
        """ return responsibility type that match with the given chart_template code
        """
        match = {
            'ar_base': self.env.ref('l10n_ar.res_RM'),
            'ar_ex': self.env.ref('l10n_ar.res_IVAE'),
            'ar_ri': self.env.ref('l10n_ar.res_IVARI'),
        }
        return match.get(chart_template)

    def _load(self, template_code, company, install_demo):
        """ Set companies AFIP Responsibility and Country if AR CoA is installed, also set tax calculation rounding
        method required in order to properly validate match AFIP invoices.

        Also, raise a warning if the user is trying to install a CoA that does not match with the defined AFIP
        Responsibility defined in the company
        """
        coa_responsibility = self._get_ar_responsibility_match(template_code)
        if coa_responsibility:
            company.write({
                'l10n_ar_afip_responsibility_type_id': coa_responsibility.id,
                'country_id': self.env['res.country'].search([('code', '=', 'AR')]).id,
                'tax_calculation_rounding_method': 'round_globally',
            })
            # set CUIT identification type (which is the argentinean vat) in the created company partner instead of
            # the default VAT type.
            company.partner_id.l10n_latam_identification_type_id = self.env.ref('l10n_ar.it_cuit')

        res = super()._load(template_code, company, install_demo)

        # If Responsable Monotributista remove the default purchase tax
        if template_code in ('ar_base', 'ar_ex'):
            company.account_purchase_tax_id = self.env['account.tax']

        return res

    def try_loading(self, template_code, company, install_demo=False):
        # During company creation load template code corresponding to the AFIP Responsibility
        if not company:
            return
        if isinstance(company, int):
            company = self.env['res.company'].browse([company])
        if company.country_code == 'AR' and not company.chart_template:
            match = {
                self.env.ref('l10n_ar.res_RM'): 'ar_base',
                self.env.ref('l10n_ar.res_IVAE'): 'ar_ex',
                self.env.ref('l10n_ar.res_IVARI'): 'ar_ri',
            }
            template_code = match.get(company.l10n_ar_afip_responsibility_type_id, template_code)
        return super().try_loading(template_code, company, install_demo)
