# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_nl_rounding_difference_loss_account_id = fields.Many2one('account.account', check_company=True)
    l10n_nl_rounding_difference_profit_account_id = fields.Many2one('account.account', check_company=True)
    l10n_nl_sbr_ob_nummer = fields.Char(related='partner_id.l10n_nl_sbr_ob_nummer', readonly=False)

    def _get_default_vat_disabled_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'NL':
            return super()._get_default_vat_disabled_tax()
        return self._get_or_create_chart_template_tax('btw_0_d')
