from odoo import _, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockRule(models.Model):
    _inherit = "stock.rule"

    def _get_lead_days(self, product, **values):
        bypass_delay_description = self.env.context.get("bypass_delay_description")
        buy_rule = self.filtered(lambda r: r.action == "buy")
        seller = (
            "supplierinfo" in values and values["supplierinfo"]
        ) or product.with_company(buy_rule.company_id)._select_seller(quantity=None)
        if not buy_rule or not seller:
            _debug.logic(
                "subcontract_lead_days",
                product=product.id,
                by="no_buy_rule" if not buy_rule else "no_seller",
            )
            return super()._get_lead_days(product, **values)
        seller = seller[0]
        bom = (
            self.env["mrp.bom"]
            .sudo()
            ._get_subcontract_bom_by_product(
                product,
                company_id=buy_rule.picking_type_id.company_id.id,
                bom_type="subcontract",
                subcontractor=seller.partner_id,
            )
        )
        if not bom:
            _debug.logic(
                "subcontract_lead_days", product=product.id, by="no_subcontract_bom"
            )
            return super()._get_lead_days(product, **values)

        delays, delay_description = super(StockRule, self - buy_rule)._get_lead_days(
            product, **values
        )
        extra_delays, extra_delay_description = super(
            StockRule,
            buy_rule.with_context(ignore_vendor_lead_time=True, global_horizon_days=0),
        )._get_lead_days(product, **values)
        _debug.logic(
            "subcontract_lead_days",
            product=product.id,
            bom=bom.id,
            by="vendor_delay"
            if seller.delay >= bom.produce_delay + bom.days_to_prepare_mo
            else "manufacture_delay",
            seller_delay=seller.delay,
            produce_delay=bom.produce_delay,
            days_to_order=bom.days_to_prepare_mo,
        )
        if seller.delay >= bom.produce_delay + bom.days_to_prepare_mo:
            delays["total_delay"] += seller.delay
            delays["purchase_delay"] += seller.delay
            if not bypass_delay_description:
                delay_description.append((_("Receipt Date"), int(seller.delay)))
                delay_description.append(
                    (_("Vendor Lead Time"), _("+ %d day(s)", seller.delay))
                )
        else:
            manufacture_delay = bom.produce_delay
            delays["total_delay"] += manufacture_delay
            delays["purchase_delay"] += manufacture_delay
            if not bypass_delay_description:
                delay_description.append((_("Receipt Date"), manufacture_delay))
                delay_description.append(
                    (_("Manufacturing Lead Time"), _("+ %d day(s)", manufacture_delay))
                )
            days_to_order = bom.days_to_prepare_mo
            delays["total_delay"] += days_to_order
            delays["purchase_delay"] += days_to_order
            if not bypass_delay_description:
                delay_description.append((_("Production Start Date"), days_to_order))
                delay_description.append(
                    (_("Days to Supply Components"), _("+ %d day(s)", days_to_order))
                )

        for key, value in extra_delays.items():
            delays[key] += value
        return delays, delay_description + extra_delay_description

    def _notify_responsible(self, procurement):
        super()._notify_responsible(procurement)
        origin_order = self.env.context.get("po_to_notify")
        if origin_order:
            notified_users = (
                procurement.product_id.responsible_id.partner_id
                | origin_order.user_id.partner_id
            )
            self._post_vendor_notification(
                origin_order, notified_users, procurement.product_id
            )
