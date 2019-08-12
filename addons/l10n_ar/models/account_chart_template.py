# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
from odoo.exceptions import UserError
from odoo.http import request


class AccountChartTemplate(models.Model):

    _inherit = 'account.chart.template'

    def _get_fp_vals(self, company, position):
        res = super()._get_fp_vals(company, position)
        if company.country_id == self.env.ref('base.ar'):
            res['l10n_ar_afip_responsibility_type_ids'] = [
                (6, False, position.l10n_ar_afip_responsibility_type_ids.ids)]
        return res

    def _prepare_all_journals(self, acc_template_ref, company, journals_dict=None):
        """ If Argentinian chart, we don't create sales journal as we need more
        data to create it properly """
        res = super()._prepare_all_journals(acc_template_ref, company, journals_dict=journals_dict)
        if company.country_id == self.env.ref('base.ar'):
            for vals in res:
                if vals['type'] == 'sale':
                    res.remove(vals)
        return res

    @api.model
    def _get_ar_responsibility_match(self, chart_template_id=False):
        """ If not chart_template_id: return the {recordset(coa): recordset(responsibility recordset)} match dictionary
            if chart_template_id: return responsibility type that match with the given chart_template_id
        """
        match = {
            self.env.ref('l10n_ar.l10nar_base_chart_template').id: self.env.ref('l10n_ar.res_RM'),
            self.env.ref('l10n_ar.l10nar_ex_chart_template').id: self.env.ref('l10n_ar.res_IVAE'),
            self.env.ref('l10n_ar.l10nar_ri_chart_template').id: self.env.ref('l10n_ar.res_IVARI'),
        }
        if chart_template_id:
            return match.get(chart_template_id)
        return match

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        """ Set companies AFIP Responsibility and Country if AR CoA is installed, also set tax calculation rounding
        method required in order to properly validate match AFIP invoices.

        Also, raise a warning if the user is trying to install a CoA that does not match with the defined AFIP
        Responsibility defined in the company
        """
        self.ensure_one()
        if company.country_id == self.env.ref('base.ar'):
            company_responsibility = company.l10n_ar_afip_responsibility_type_id
            coa_responsibility = self._get_ar_responsibility_match(self.id)
            if coa_responsibility:
                company.write({
                    'l10n_ar_afip_responsibility_type_id': coa_responsibility.id,
                    'country_id': self.env.ref('base.ar').id,
                    'tax_calculation_rounding_method': 'round_globally',
                })

            if company_responsibility and company_responsibility != coa_responsibility:
                raise UserError(_(
                    'You are trying to install a chart of account for the %s responsibility but your company is configured'
                    ' as %s type' % (coa_responsibility.name, company_responsibility.name)))
        return super()._load(sale_tax_rate, purchase_tax_rate, company)
