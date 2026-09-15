from odoo import fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    partners_count = fields.Integer(compute="_compute_partners_count")
    partners_label = fields.Char(related="company_id.partnership_label")

    def _compute_partners_count(self):
        partners_data = self.env["res.partner"]._read_group(
            domain=[("specific_property_product_pricelist", "in", self.ids)],
            groupby=["specific_property_product_pricelist"],
            aggregates=["__count"],
        )
        mapped_data = {pricelist.id: count for pricelist, count in partners_data}
        _debug.perf.count(
            "pricelist_partner_count", pricelists=len(self), rows=len(mapped_data)
        )
        for pricelist in self:
            pricelist.partners_count = mapped_data.get(pricelist.id, 0)
