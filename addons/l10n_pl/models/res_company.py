from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pl_reports_tax_office_id = fields.Many2one('l10n_pl.l10n_pl_tax_office', string='Tax Office', groups="account.group_account_user")

    def _get_default_vat_disabled_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'PL':
            return super()._get_default_vat_disabled_tax()
        return self._get_or_create_chart_template_tax('vs_not_subject')

    def _get_default_vat_disabled_purchase_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'PL':
            return super()._get_default_vat_disabled_purchase_tax()
        return self._get_or_create_chart_template_tax('vp_vat_disabled_nd')
