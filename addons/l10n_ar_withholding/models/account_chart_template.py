from odoo import models, api
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

    @api.model
    def _l10n_ar_add_wth_sequences(self, company):
        """ Agregamos etiquetas en repartition lines de impuestos de percepciones de iva, ganancias e ingresos brutos.  """
        company.ensure_one()

        # creacion de secuencias y agregado de etiquetas para liquidación de impuestos
        withholdings_domain = [
            ('company_id', '=', company.id),
            ('type_tax_use', '=', 'none'),
            ('country_code', '=', 'AR'),
            ('l10n_ar_withholding_payment_type', '=', 'supplier'),
        ]
        non_profits_domain = withholdings_domain + [('l10n_ar_tax_type', 'not in', ['earnings', 'earnings_scale'])]

        for tax in self.env['account.tax'].with_context(active_test=False).search(non_profits_domain):
            sequence = self.env['ir.sequence'].create({
                'name': tax.invoice_label or tax.name,
                'prefix': '%(year)s-',
                'padding': 8,
                'number_increment': 1,
                'implementation': 'standard',
                'company_id': company.id,
            })
            tax.l10n_ar_withholding_sequence_id = sequence.id

        profits_domain = withholdings_domain + [('l10n_ar_tax_type', 'in', ['earnings', 'earnings_scale'])]
        sequence = self.env['ir.sequence'].create({
                'name': tax.invoice_label or 'Retención de Ganancias',
                'prefix': '%(year)s-',
                'padding': 8,
                'number_increment': 1,
                'implementation': 'standard',
                'company_id': company.id,
            })
        profits_taxes = self.env['account.tax'].with_context(active_test=False).search(profits_domain)
        profits_taxes.l10n_ar_withholding_sequence_id = sequence.id

    def _load(self, template_code, company, install_demo):
        """ Luego de que creen los impuestos del archivo account.tax-ar_ri.csv de l10n_ar al instalar el plan de cuentas en la nueva compañìa argentina agregamos en este método las etiquetas que correspondan en los repartition lines. """
        # Llamamos a super para que se creen los impuestos
        res = super()._load(template_code, company, install_demo)
        company = company or self.env.company
        if company.chart_template in ('ar_ri', 'ar_ex', 'ar_base'):
            self.sudo()._add_wh_taxes(company)
        return res
