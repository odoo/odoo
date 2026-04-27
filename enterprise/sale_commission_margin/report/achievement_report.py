# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models


class SaleAchievementReport(models.Model):
    _inherit = "sale.commission.achievement.report"

    def _get_sale_rates(self):
        return super()._get_sale_rates() + ['margin']

    def _get_sale_rates_product(self):
        return super()._get_sale_rates_product() + "+ rules.margin_rate * COALESCE(sol.margin, 0) / so.currency_rate"
