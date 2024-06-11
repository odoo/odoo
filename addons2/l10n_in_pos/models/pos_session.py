# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        result['search_params']['fields'].append('l10n_in_hsn_code')
        return result

    def _loader_params_account_tax(self):
        account_tax_params = super()._loader_params_account_tax()
        account_tax_params['search_params']['fields'].append('tax_group_id')
        return account_tax_params

    @api.model
    def _load_onboarding_main_config_data(self, shop_config):
        if shop_config.company_id.country_code == 'IN' and not shop_config.company_id.state_id:
            return

        super()._load_onboarding_main_config_data(shop_config)
