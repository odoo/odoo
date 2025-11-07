# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('pt', 'account.tax')
    def _get_pt_certification_account_tax(self):
        return self._parse_csv('pt', 'account.tax', module='l10n_pt_certification')

    @template('pt', 'account.tax.group')
    def _get_pt_certification_account_tax_group(self):
        return self._parse_csv('pt', 'account.tax.group', module='l10n_pt_certification')

    def _l10n_pt_load_certification_tax_data(self, company):
        """
        Add to the taxes and tax groups of ``company``'s PT chart what the certification defines on
        them (VAT exemption reasons, tax regions and categories), for a chart loaded before this module.

        Only the records the chart holds are completed. A tax deleted by the user, or added to the PT
        chart after this chart was loaded, has nothing to certify: loading its row would create it from
        that row alone, without a name, and fail the install. A chart update that adds it later loads
        the whole template, the certification's values included.
        """
        template = self.with_company(company)
        data = {
            'account.tax': template._get_pt_certification_account_tax(),
            'account.tax.group': template._get_pt_certification_account_tax_group(),
        }
        # The names under which `ref` finds them: the company's own records, else its root company's.
        names = {
            xmlid: {f'{c.id}_{xmlid}' for c in company | company.root_id}
            for records in data.values() for xmlid in records
        }
        existing = set(self.env['ir.model.data'].search([
            ('module', '=', 'account'),
            ('model', 'in', list(data)),
            ('name', 'in', list(set().union(*names.values()))),
        ]).mapped('name'))
        template._load_data({
            model: {xmlid: vals for xmlid, vals in records.items() if names[xmlid] & existing}
            for model, records in data.items()
        })
