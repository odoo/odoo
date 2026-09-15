from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ee_rounding_difference_loss_account_id = fields.Many2one('account.account', check_company=True)
    l10n_ee_rounding_difference_profit_account_id = fields.Many2one('account.account', check_company=True)

    def _get_default_vat_disabled_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'EE':
            return super()._get_default_vat_disabled_tax()
        return self._get_or_create_chart_template_tax('l10n_ee_vat_out_not_subject')

    def _get_default_vat_disabled_purchase_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'EE':
            return super()._get_default_vat_disabled_purchase_tax()
        return self._get_or_create_chart_template_tax('l10n_ee_vat_in_disabled_nd')
