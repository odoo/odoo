# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, fields


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    # MOVER A LOGICA DE def _get_fp_vals(self, company, position):
    @api.multi
    def generate_fiscal_position(
            self, tax_template_ref, acc_template_ref, company):
        """
        if chart is argentina localization, then we add l10n_ar_afip_code to
        fiscal positions.
        We also add other data to add fiscal positions automatically
        """
        res = super(AccountChartTemplate, self).generate_fiscal_position(
            tax_template_ref, acc_template_ref, company)
        if company.country_id.code != 'AR':
            return res
        positions = self.env['account.fiscal.position.template'].search(
            [('chart_template_id', '=', self.id)])
        for position in positions:
            created_position = self.env['account.fiscal.position'].search([
                ('company_id', '=', company.id),
                ('name', '=', position.name),
                ('note', '=', position.note)], limit=1)
            if created_position:
                created_position.update({
                    'l10n_ar_afip_code': position.l10n_ar_afip_code,
                })
        return res

    @api.multi
    def _prepare_all_journals(self, acc_template_ref, company,
                              journals_dict=None):
        """ If argentinian chart, we don't create sales journal as we need more
        data to create it properly
        """
        res = super(
            AccountChartTemplate, self)._prepare_all_journals(
            acc_template_ref, company, journals_dict=journals_dict)

        if company.country_id.code == 'AR':
            res = [item for item in res if item.get('type') == 'sale']
        return res
