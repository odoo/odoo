from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):

    _inherit = 'account.chart.template'

    # ar base
    @template('ar_base', 'account.account')
    def _get_ar_base_withholding_account_account(self):
        return self._parse_csv('ar_base', 'account.account', module='l10n_ar_withholding')

    # ri chart
    @template('ar_ri', 'account.tax.group')
    def _get_ar_ri_withholding_account_tax_group(self):
        return self._parse_csv('ar_ri', 'account.tax.group', module='l10n_ar_withholding')

    @template('ar_ri', 'account.tax')
    def _get_ar_ri_withholding_account_tax(self):
        additional = self._parse_csv('ar_ri', 'account.tax', module='l10n_ar_withholding')
        self._deref_account_tags('ar_ri', additional)
        return additional

    # ex chart
    @template('ar_ex', 'account.tax.group')
    def _get_ar_ex_withholding_account_tax_group(self):
        return self._parse_csv('ar_ex', 'account.tax.group', module='l10n_ar_withholding')

    @template('ar_ex', 'account.tax')
    def _get_ar_ex_withholding_account_tax(self):
        additional = self._parse_csv('ar_ex', 'account.tax', module='l10n_ar_withholding')
        self._deref_account_tags('ar_ex', additional)
        return additional

    @template('ar_base', 'res.company')
    def _get_ar_base_res_company(self):
        res = super()._get_ar_base_res_company()
        res[self.env.company.id].update({'l10n_ar_tax_base_account_id': 'base_tax_account'})
        return res

    def _add_wh_scales(self, company):
        """ Add earnings scales to earnings withholding groups.  """
        if company.country_id.code == 'AR' and company.l10n_ar_afip_responsibility_type_id.code == '1':
            # List of scales and earnings_withholding_groups in which is necessary to add the scales for the children_tax_ids of earnings_withholding_groups
            scales = ['ri_tax_withholding_scale_0_8000', 'ri_tax_withholding_scale_8000_16000', 'ri_tax_withholding_scale_16000_24000', 'ri_tax_withholding_scale_24000_32000', 'ri_tax_withholding_scale_32000_48000', 'ri_tax_withholding_scale_48000_64000', 'ri_tax_withholding_scale_64000_96000', 'ri_tax_withholding_scale_96000_999999999']
            earnings_withholding_groups = ['ri_tax_withholding_earnings_incurred_group_110_insc', 'ri_tax_withholding_earnings_incurred_group_25_insc', 'ri_tax_withholding_earnings_incurred_group_116I_insc', 'ri_tax_withholding_earnings_incurred_group_116II_insc', 'ri_tax_withholding_earnings_incurred_group_119_insc', 'ri_tax_withholding_earnings_incurred_group_124_insc']
            scales_records = self.env['account.tax']
            for scale in scales:
                scale_id = "account.%s_%s" % (company.id, scale)
                scales_records += self.env.ref(scale_id)
            for earnings_withholding_group in earnings_withholding_groups:
                earnings_withholding_group_id = "account.%s_%s" % (company.id, earnings_withholding_group)
                impuesto = self.env.ref(earnings_withholding_group_id)
                impuesto.children_tax_ids = scales_records

            scales_119 = ['ri_tax_withholding_119_scale_0_71000', 'ri_tax_withholding_119_scale_71000_142000', 'ri_tax_withholding_119_scale_142000_213000', 'ri_tax_withholding_119_scale_213000_284000', 'ri_tax_withholding_119_scale_284000_426000', 'ri_tax_withholding_119_scale_426000_568000', 'ri_tax_withholding_119_scale_568000_852000', 'ri_tax_withholding_119_scale_852000_999999999']
            scales_119_records = self.env['account.tax']
            for scale_119 in scales_119:
                scale_119_id = "account.%s_%s" % (company.id, scale_119)
                scales_119_records += self.env.ref(scale_119_id)
            earnings_withholding_119_group_id = "account.%s_%s" % (company.id, 'ri_tax_withholding_earnings_incurred_group_119_insc')
            tax_group_119 = self.env.ref(earnings_withholding_119_group_id)
            tax_group_119.children_tax_ids = scales_119_records

    def _load(self, template_code, company, install_demo):
        """ Add earnings scales to earnings withholding groups when a new chart of account is installed in an argentinean company."""
        res = super()._load(template_code, company, install_demo)
        company = self.env.company
        self._add_wh_scales(company)
        return res
