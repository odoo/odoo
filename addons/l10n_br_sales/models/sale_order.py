from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_name_portal_content_view(self):
        self.check_singleton()
        _debug.logic(
            "portal_content_view", order=self, country=self.company_id.country_code
        )
        return (
            "l10n_br_sales.sale_order_portal_content_brazil"
            if self.company_id.country_code == "BR"
            else super()._get_name_portal_content_view()
        )

    def _get_name_tax_totals_view(self):
        self.check_singleton()
        return (
            "l10n_br_sales.document_tax_totals_brazil"
            if self.company_id.country_code == "BR"
            else super()._get_name_tax_totals_view()
        )
