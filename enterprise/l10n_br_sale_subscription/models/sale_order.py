# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_name_portal_content_view(self):
        self.ensure_one()
        return 'l10n_br_sale_subscription.subscription_portal_content_brazil' if self.is_subscription and self.company_id.country_code == 'BR' else super()._get_name_portal_content_view()
