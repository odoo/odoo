# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _prepare_journals(self, loaded_data):
        # OVERRIDE
        # In case of an Argentinean CoA, we modify the default values of the sales journal to be a preprinted journal.
        res = super()._prepare_journals(loaded_data)
        if self.env.company.country_code == 'AR':
            res['sale'][0].update({
                'name': 'Ventas Preimpreso',
                'code': '0001',
                'l10n_ar_afip_pos_number': 1,
                'l10n_ar_afip_pos_partner_id': self.env.company.partner_id.id,
                'l10n_ar_afip_pos_system': 'II_IM',
                'l10n_ar_share_sequences': True,
                'refund_sequence': False
            })
        return res

    @api.model
    def _get_ar_responsibility_match(self, chart_template_id):
        """ return responsibility type that match with the given chart_template_id
        """
        match = {
            self.env.ref('l10n_ar.l10nar_base_chart_template').id: self.env.ref('l10n_ar.res_RM'),
            self.env.ref('l10n_ar.l10nar_ex_chart_template').id: self.env.ref('l10n_ar.res_IVAE'),
            self.env.ref('l10n_ar.l10nar_ri_chart_template').id: self.env.ref('l10n_ar.res_IVARI'),
        }
        return match.get(chart_template_id)

    def _update_company_after_loading(self, loaded_data):
        # OVERRIDE
        # Set companies AFIP Responsibility and Country if AR CoA is installed, also set tax calculation rounding
        # method required in order to properly validate match AFIP invoices.
        #
        # Also, raise a warning if the user is trying to install a CoA that does not match with the defined AFIP
        # Responsibility defined in the company
        res = super()._update_company_after_loading(loaded_data)

        company = self.env.company
        if company.country_code == 'AR':
            to_write = {}

            coa_responsibility = self._get_ar_responsibility_match(self.id)
            if coa_responsibility:
                to_write['l10n_ar_afip_responsibility_type_id'] = coa_responsibility.id
                to_write['tax_calculation_rounding_method'] = 'round_globally'

                # set CUIT identification type (which is the argentinean vat) in the created company partner instead of
                # the default VAT type.
                company.partner_id.l10n_latam_identification_type_id = self.env.ref('l10n_ar.it_cuit')

            # If Responsable Monotributista remove the default purchase tax
            if self == self.env.ref('l10n_ar.l10nar_base_chart_template') or \
               self == self.env.ref('l10n_ar.l10nar_ex_chart_template'):
                to_write['account_purchase_tax_id'] = False

            if to_write:
                company.write(to_write)

        return res
