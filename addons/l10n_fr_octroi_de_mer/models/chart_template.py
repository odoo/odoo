from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('fr', 'account.tax')
    def _get_fr_octroi_de_mer_taxes(self):
        taxes = self._parse_csv('fr', 'account.tax', module='l10n_fr_octroi_de_mer')
        existing_taxes = self.env['account.tax'].search([('company_id', 'child_of', self.env.company.root_id.id)])
        existing_tax_names = set(existing_taxes.mapped('name'))
        taxes_to_create = {name: tax for name, tax in taxes.items() if tax['name'] not in existing_tax_names}
        return taxes_to_create

    @template('fr', 'account.tax.group')
    def _get_fr_octroi_de_mer_tax_groups(self):
        tax_groups = self._parse_csv('fr', 'account.tax.group', module='l10n_fr_octroi_de_mer')
        existing_tax_groups = self.env['account.tax.group'].search([('company_id', 'child_of', self.env.company.root_id.id)])
        existing_tax_group_names = set(existing_tax_groups.mapped('name'))
        tax_groups_to_create = {name: tax_group for name, tax_group in tax_groups.items() if tax_group['name'] not in existing_tax_group_names}
        return tax_groups_to_create
