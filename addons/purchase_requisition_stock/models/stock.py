from odoo import models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _prepare_purchase_order_vals(self, company_id, origins, values):
        _debug.pipeline("requisition_po_vals", rules=self, company=company_id)
        res = super()._prepare_purchase_order_vals(company_id, origins, values)
        values = values[0]
        res["partner_ref"] = values["supplier"].purchase_requisition_id.name
        res["requisition_id"] = values["supplier"].purchase_requisition_id.id
        if values["supplier"].purchase_requisition_id.currency_id:
            res["currency_id"] = values[
                "supplier"
            ].purchase_requisition_id.currency_id.id
        return res

    def _get_fallback_supplier(self, product_id, company_id):
        _debug.logic("requisition_fallback_supplier", rules=self, product=product_id)
        return product_id._prepare_sellers(False).filtered(
            lambda s: (
                not s.purchase_requisition_id
                and (not s.company_id or s.company_id == company_id)
            ),
        )[:1]

    def _get_domain_po(self, company_id, values, partner):
        _debug.logic("requisition_po_domain", rules=self, partner=partner)
        domain = super()._get_domain_po(company_id, values, partner)
        if "supplier" in values and values["supplier"].purchase_requisition_id:
            domain += (
                ("requisition_id", "=", values["supplier"].purchase_requisition_id.id),
            )
        return domain
