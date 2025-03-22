# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _l10n_ec_setup_location_accounts(self, companies):
        parent_location = self.env.ref('stock.stock_location_locations_virtual', raise_if_not_found=False)
        loss_locs = parent_location and parent_location.child_ids.filtered(lambda l: l.usage == 'inventory' and l.company_id in companies and not l.scrap_location)
        loss_loc_accounts = self._get_account_from_template(companies, self.env.ref('l10n_ec.ec510112', raise_if_not_found=False))
        prod_locs = parent_location and parent_location.child_ids.filtered(lambda l: l.usage == 'production' and l.company_id in companies and not l.scrap_location)
        prod_loc_accounts = self._get_account_from_template(companies, self.env.ref('l10n_ec.ec110302', raise_if_not_found=False))
        for company in companies:
            loss_loc = loss_locs.filtered(lambda l: l.company_id == company)
            loss_loc_account = loss_loc_accounts.filtered(lambda l: l.company_id == company)
            if loss_loc and loss_loc_account:
                loss_loc.write({
                    'valuation_in_account_id': loss_loc_account.id,
                    'valuation_out_account_id': loss_loc_account.id,
                })
            prod_loc = prod_locs.filtered(lambda l: l.company_id == company)
            prod_loc_account = prod_loc_accounts.filtered(lambda l: l.company_id == company)
            if prod_loc and prod_loc_account:
                prod_loc.write({
                    'valuation_in_account_id': prod_loc_account.id,
                    'valuation_out_account_id': prod_loc_account.id,
                })
