# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_siret = fields.Char(related='partner_id.l10n_fr_siret', readonly=False)
    l10n_fr_siren = fields.Char(related='partner_id.l10n_fr_siren', readonly=False)
    l10n_fr_rounding_difference_loss_account_id = fields.Many2one('account.account', check_company=True)
    l10n_fr_rounding_difference_profit_account_id = fields.Many2one('account.account', check_company=True)

    def _get_default_vat_disabled_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'FR':
            return super()._get_default_vat_disabled_tax()
        return self._get_or_create_chart_template_tax('tva_sale_service_0')

    def _get_default_vat_disabled_purchase_tax(self):
        self.ensure_one()
        if self.account_fiscal_country_id.code != 'FR':
            return super()._get_default_vat_disabled_purchase_tax()
        return self._get_or_create_chart_template_tax('tva_purchase_disabled_nd')
