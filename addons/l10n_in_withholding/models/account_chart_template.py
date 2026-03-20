from odoo import models
from odoo.addons.account.models.chart_template import template
from odoo.exceptions import UserError, RedirectWarning


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('in', 'account.account')
    def _get_in_withholding_account_account(self):
        return self._parse_csv('in', 'account.account', module='l10n_in_withholding')

    @template('in', 'account.tax')
    def _get_in_withholding_account_tax(self):
        tax_data = self._parse_csv('in', 'account.tax', module='l10n_in_withholding')
        self._deref_account_tags('in', tax_data)
        return tax_data

    @template('in', 'res.company')
    def _get_in_base_res_company(self):
        return {
            self.env.company.id: {
                'l10n_in_withholding_account_id': 'p100595',
            },
        }

    def _get_tag_mapper(self, country_id):
        original_mapper = super()._get_tag_mapper(country_id)
        if country_id != self.env.ref('base.in').id:
            return original_mapper

        def wrapped_mapper(*args):
            try:
                return original_mapper(*args)
            except UserError as e:
                raise RedirectWarning(
                    message=e.args[0],
                    action={
                        'name': self.env._('App need to update'),
                        'res_model': 'ir.module.module',
                        'type': 'ir.actions.act_window',
                        'views': [(self.env.ref('base.module_form').id, 'form')],
                        'res_id': self.env.ref('base.module_l10n_in').id,
                    },
                    button_text=self.env._("Update app"),
                )
        return wrapped_mapper
