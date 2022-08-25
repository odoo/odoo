# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
from odoo.exceptions import UserError
from odoo.http import request


class AccountChartTemplate(models.Model):

    _inherit = 'account.chart.template'

    def _get_fp_vals(self, company, position):
        res = super()._get_fp_vals(company, position)
        if company.country_id.code == "AR":
            res['l10n_ar_afip_responsibility_type_ids'] = [
                (6, False, position.l10n_ar_afip_responsibility_type_ids.ids)]
        return res

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        """ In case of an Argentinean CoA, we modify the default values of the sales journal to be a preprinted journal"""
        res = super()._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)
        if company.country_id.code == "AR":
            for vals in res:
                if vals['type'] == 'sale':
                    vals.update({
                        "name": "Ventas Preimpreso",
                        "code": "0001",
                        "l10n_ar_afip_pos_number": 1,
                        "l10n_ar_afip_pos_partner_id": company.partner_id.id,
                        "l10n_ar_afip_pos_system": 'II_IM',
                        "refund_sequence": False
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

    def _load(self, company):
        """ Set companies AFIP Responsibility and Country if AR CoA is installed, also set tax calculation rounding
        method required in order to properly validate match AFIP invoices.

        Also, raise a warning if the user is trying to install a CoA that does not match with the defined AFIP
        Responsibility defined in the company
        """
        self.ensure_one()
        coa_responsibility = self._get_ar_responsibility_match(self.id)
        if coa_responsibility:
            company_responsibility = company.l10n_ar_afip_responsibility_type_id
            company.write({
                'l10n_ar_afip_responsibility_type_id': coa_responsibility.id,
                'country_id': self.env['res.country'].search([('code', '=', 'AR')]).id,
                'tax_calculation_rounding_method': 'round_globally',
            })
            # set CUIT identification type (which is the argentinean vat) in the created company partner instead of
            # the default VAT type.
            company.partner_id.l10n_latam_identification_type_id = self.env.ref('l10n_ar.it_cuit')

        res = super()._load(company)

        # If Responsable Monotributista remove the default purchase tax
        if self == self.env.ref('l10n_ar.l10nar_base_chart_template') or \
           self == self.env.ref('l10n_ar.l10nar_ex_chart_template'):
            company.account_purchase_tax_id = self.env['account.tax']

        return res
