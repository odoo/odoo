from collections import defaultdict
from datetime import datetime

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models
from odoo.api import SUPERUSER_ID
from odoo.fields import Command
from odoo.tools import groupby
from odoo.tools.translate import _

from odoo.addons.stock.models.stock_rule import ProcurementException


class StockRule(models.Model):
    _inherit = "stock.rule"

    action = fields.Selection(
        selection_add=[("buy", "Buy")],
        ondelete={"buy": "cascade"},
    )

    def _get_domain_picking_type_code(self):
        codes = super()._get_domain_picking_type_code()
        if self.action == "buy":
            codes = [*codes, "incoming"]
        return codes

    @api.onchange("action")
    def _onchange_action(self):
        if self.action == "buy":
            self.location_src_id = False

    def _has_buy_action(self):
        return any(rule.action == "buy" for rule in self)

    @api.model
    def _search_buy_rules(self, company=None, warehouse=None, picking_code=None):
        domain = [("action", "=", "buy")]
        if company is not None:
            domain.append(("company_id", "=", company.id))
        if warehouse is not None:
            domain.append(("warehouse_id", "=", warehouse.id))
        if picking_code is not None:
            domain.append(("picking_type_id.code", "=", picking_code))
        return self.env["stock.rule"].search(domain)

    @api.model
    def _get_buy_routes(self, company=None, warehouse=None, picking_code=None):
        return self._search_buy_rules(company, warehouse, picking_code).route_id

    def _is_route_usable_for(self, product, route):
        if route._has_buy_rule():
            return bool(product.seller_ids) and super()._is_route_usable_for(
                product, route
            )
        return super()._is_route_usable_for(product, route)

    def _get_lead_days(self, product, **values):
        delays, delay_description = super()._get_lead_days(product, **values)
        buy_rule = self.filtered(lambda r: r.action == "buy")
        if not buy_rule:
            return delays, delay_description
        bypass_delay_description = self.env.context.get("bypass_delay_description")
        seller = (
            "supplierinfo" in values and values["supplierinfo"]
        ) or product.with_company(buy_rule.company_id)._select_seller(quantity=None)
        if not seller:
            delays["total_delay"] += 365
            delays["no_vendor_found_delay"] += 365
            if not bypass_delay_description:
                delay_description.append((_("No Vendor Found"), _("+ %s day(s)", 365)))
            return delays, delay_description
        buy_rule.check_singleton()
        if not self.env.context.get("ignore_vendor_lead_time"):
            supplier_delay = seller[:1].delay
            delays["total_delay"] += supplier_delay
            delays["purchase_delay"] += supplier_delay
            if not bypass_delay_description:
                delay_description.append((_("Receipt Date"), supplier_delay))
                delay_description.append(
                    (_("Vendor Lead Time"), _("+ %d day(s)", supplier_delay)),
                )
        days_to_order = buy_rule.company_id.days_to_purchase
        delays["total_delay"] += days_to_order
        if not bypass_delay_description:
            delay_description.append((_("Order Deadline"), days_to_order))
            delay_description.append(
                (_("Days to Purchase"), _("+ %d day(s)", days_to_order)),
            )
        return delays, delay_description

    def _get_matching_supplier(
        self,
        product_id,
        product_qty,
        product_uom_id,
        company_id,
        values,
    ):
        supplier = False
        if "date_planned" in values:
            date = max(
                fields.Datetime.from_string(values["date_planned"]).date(),
                fields.Date.today(),
            )
        else:
            date = None

        if values.get("supplierinfo_id"):
            supplier = values["supplierinfo_id"]
        elif values.get("orderpoint_id") and values["orderpoint_id"].supplier_id:
            supplier = values["orderpoint_id"].supplier_id
        else:
            supplier = product_id.with_company(company_id.id)._select_seller(
                partner_id=self._get_partner_id(values, self),
                quantity=product_qty,
                date=date,
                uom_id=product_uom_id,
                params={"force_uom": values.get("force_uom")},
            )

        return supplier or self._get_fallback_supplier(product_id, company_id)

    def _get_fallback_supplier(self, product_id, company_id):
        return product_id._prepare_sellers(False).filtered(
            lambda s: not s.company_id or s.company_id == company_id,
        )[:1]

    def _get_action_messages(self):
        message_dict = super()._get_action_messages()
        __, destination, __, __ = self._get_message_labels()
        message_dict.update(
            {
                "buy": _(
                    "When products are needed in <b>%s</b>, <br/> "
                    "a request for quotation is created to fulfill the need.<br/>"
                    "Note: This rule will be used in combination with the rules<br/>"
                    "of the reception route(s)",
                    destination,
                ),
            },
        )
        return message_dict

    def _get_partner_id(self, values, rule):
        return values.get("supplierinfo_name") or (
            values.get("force_uom") and values.get("partner_id")
        )

    @api.model
    def _get_procurements_to_merge_groupby(self, procurement):
        return (
            procurement.product_id,
            procurement.product_uom_id,
            procurement.values["propagate_cancel"],
            procurement.values.get("product_description_variants"),
            (
                procurement.values.get("orderpoint_id")
                and not procurement.values.get("move_dest_ids")
            )
            and procurement.values["orderpoint_id"],
        )

    @api.model
    def _get_procurements_to_merge(self, procurements):
        return [
            pro_g
            for __, pro_g in groupby(
                procurements,
                key=self._get_procurements_to_merge_groupby,
            )
        ]

    def _get_domain_po(self, company_id, values, partner):
        currency = (
            ("supplier" in values and values["supplier"].currency_id)
            or partner.with_company(company_id).property_purchase_currency_id
            or company_id.currency_id
        )
        domain = (
            ("partner_id", "=", partner.id),
            ("state", "=", "draft"),
            ("picking_type_id", "=", self.picking_type_id.id),
            ("company_id", "=", company_id.id),
            ("user_id", "=", partner.user_purchase_id.id),
            ("currency_id", "=", currency.id),
        )
        if partner.group_rfq == "default" or self.picking_type_id.code == "dropship":
            if values.get("reference_ids"):
                domain += (("reference_ids", "in", tuple(values["reference_ids"].ids)),)
            elif partner.group_rfq == "default":
                domain += (("reference_ids", "=", False),)
        date_planned = fields.Datetime.from_string(values["date_planned"])
        if partner.group_rfq == "day":
            start_dt = datetime.combine(date_planned, datetime.min.time())
            end_dt = datetime.combine(date_planned, datetime.max.time())
            domain += (
                ("date_commitment", ">=", start_dt),
                ("date_commitment", "<=", end_dt),
            )
        if partner.group_rfq == "week":
            if partner.group_on == "default":
                start_dt = datetime.combine(
                    date_planned - relativedelta(days=date_planned.isoweekday()),
                    datetime.min.time(),
                )
                end_dt = datetime.combine(
                    date_planned + relativedelta(days=6 - date_planned.isoweekday()),
                    datetime.max.time(),
                )
                domain += (
                    ("date_commitment", ">=", start_dt),
                    ("date_commitment", "<=", end_dt),
                )
            else:
                delta_days = (7 + int(partner.group_on) - date_planned.isoweekday()) % 7
                date = date_planned + relativedelta(days=delta_days)
                start_dt = datetime.combine(date, datetime.min.time())
                end_dt = datetime.combine(date, datetime.max.time())
                domain += (
                    ("date_commitment", ">=", start_dt),
                    ("date_commitment", "<=", end_dt),
                )

        return domain

    @api.model
    def _merge_procurements(self, procurements_to_merge):
        merged_procurements = []
        for procurements in procurements_to_merge:
            quantity = 0
            move_dest_ids = self.env["stock.move"]
            orderpoint_id = self.env["stock.warehouse.orderpoint"]
            for procurement in procurements:
                if procurement.values.get("move_dest_ids"):
                    move_dest_ids |= procurement.values["move_dest_ids"]
                if not orderpoint_id and procurement.values.get("orderpoint_id"):
                    orderpoint_id = procurement.values["orderpoint_id"]
                quantity += procurement.product_qty
            values = dict(procurement.values)
            values.update(
                {
                    "move_dest_ids": move_dest_ids,
                    "orderpoint_id": orderpoint_id,
                },
            )
            merged_procurement = self.env["stock.rule"].Procurement(
                procurement.product_id,
                quantity,
                procurement.product_uom_id,
                procurement.location_id,
                procurement.name,
                procurement.origin,
                procurement.company_id,
                values,
            )
            merged_procurements.append(merged_procurement)
        return merged_procurements

    def _notify_responsible(self, procurement):
        pass

    def _post_vendor_notification(self, records_to_notify, users_to_notify, product):
        notification_msg = Markup(" ").join(
            Markup("%s") % user._get_html_link(f"@{user.name}")
            for user in users_to_notify
        )
        notification_msg += Markup("<br/>%s <strong>%s</strong>, %s") % (
            _("No supplier has been found to replenish"),
            product.display_name,
            _("this product should be manually replenished."),
        )
        records_to_notify.message_post(
            body=notification_msg,
            partner_ids=users_to_notify.ids,
        )

    def _prepare_purchase_order_vals(self, company_id, origins, values):
        purchase_date = min(
            value.get("date_order")
            or fields.Datetime.from_string(value["date_planned"])
            - relativedelta(days=int(value["supplier"].delay))
            for value in values
        )

        values = values[0]
        partner = values["supplier"].partner_id
        currency = values["supplier"].currency_id

        fpos = (
            self.env["account.fiscal.position"]
            .with_company(company_id)
            ._get_fiscal_position(partner)
        )

        return {
            "partner_id": partner.id,
            "user_id": partner.user_purchase_id.id,
            "picking_type_id": self.picking_type_id.id,
            "company_id": company_id.id,
            "currency_id": currency.id
            or partner.with_company(company_id).property_purchase_currency_id.id
            or company_id.currency_id.id,
            "dest_address_id": values.get("partner_id", False),
            "origin": ", ".join(origins),
            "payment_term_id": partner.with_company(
                company_id,
            ).property_supplier_payment_term_id.id,
            "date_order": purchase_date,
            "fiscal_position_id": fpos.id,
            "reference_ids": [
                Command.set(
                    values.get("reference_ids", self.env["stock.reference"]).ids,
                ),
            ],
        }

    def _prepare_push_move_copy_values(self, move_to_copy, new_date):
        res = super()._prepare_push_move_copy_values(
            move_to_copy,
            new_date,
        )
        res["purchase_line_id"] = None
        if self.location_dest_id.usage == "supplier":
            res["purchase_line_id"], res["partner_id"] = (
                move_to_copy._get_purchase_line_and_partner_from_chain()
            )
        return res

    @api.model
    def _get_action_runners(self):
        return {**super()._get_action_runners(), "buy": "_run_buy"}

    @api.model
    def _run_buy(self, procurements):
        procurements_by_po_domain = defaultdict(list)
        errors = []
        for procurement, rule in procurements:
            company_id = rule.company_id or procurement.company_id
            supplier = rule._get_matching_supplier(
                procurement.product_id,
                procurement.product_qty,
                procurement.product_uom_id,
                company_id,
                procurement.values,
            )

            if not supplier and self.env.context.get("from_orderpoint"):
                msg = _(
                    "There is no matching vendor price to generate the purchase order for product %s (no vendor defined, minimum quantity not reached, dates not valid, ...). Go on the product form and complete the list of vendors.",
                    procurement.product_id.display_name,
                )
                errors.append((procurement, msg))
            elif not supplier:
                moves = (
                    procurement.values.get("move_dest_ids") or self.env["stock.move"]
                )
                if moves.propagate_cancel:
                    moves._action_cancel()
                moves.procure_method = "make_to_stock"
                self._notify_responsible(procurement)
                continue

            partner = supplier.partner_id
            procurement.values["supplier"] = supplier
            procurement.values["propagate_cancel"] = rule.propagate_cancel
            domain = rule._get_domain_po(company_id, procurement.values, partner)
            procurements_by_po_domain[domain].append((procurement, rule))

        if errors:
            raise ProcurementException(errors)

        for domain, procurements_rules in procurements_by_po_domain.items():
            procurements, rules = zip(*procurements_rules, strict=False)
            origins = {p.origin for p in procurements if p.origin}
            po = self.env["purchase.order"].sudo().search(list(domain), limit=1)  # noqa: E8507 - one probe per distinct purchase-order domain; procurements sharing one were merged above
            company_id = rules[0].company_id or procurements[0].company_id
            if not po:
                positive_values = [
                    p.values
                    for p in procurements
                    if p.product_uom_id.compare(p.product_qty, 0.0) >= 0
                ]
                if positive_values:
                    vals = rules[0]._prepare_purchase_order_vals(
                        company_id,
                        origins,
                        positive_values,
                    )
                    po = (
                        self.env["purchase.order"]
                        .with_company(company_id)
                        .with_user(SUPERUSER_ID)
                        .create(vals)
                    )
            else:
                reference_ids = set()

                for procurement in procurements:
                    reference_ids |= set(
                        procurement.values.get(
                            "reference_ids",
                            self.env["stock.reference"],
                        ).ids,
                    )

                po.reference_ids = [Command.link(ref_id) for ref_id in reference_ids]

                if po.origin:
                    missing_origins = origins - set(po.origin.split(", "))
                    if missing_origins:
                        po.write(
                            {"origin": po.origin + ", " + ", ".join(missing_origins)},
                        )
                else:
                    po.write({"origin": ", ".join(origins)})

            procurements_to_merge = self._get_procurements_to_merge(procurements)
            procurements = self._merge_procurements(procurements_to_merge)
            po_lines_by_product = {}
            grouped_po_lines = groupby(
                po.line_ids.filtered(lambda l: not l.display_type),
                key=lambda l: l.product_id.id,
            )

            for product, po_lines in grouped_po_lines:
                po_lines_by_product[product] = self.env["purchase.order.line"].concat(
                    *po_lines,
                )

            po_line_values = []
            earliest_date_commitment = None

            for procurement in procurements:
                po_lines = po_lines_by_product.get(
                    procurement.product_id.id,
                    self.env["purchase.order.line"],
                )
                po_line = po_lines._get_candidate(*procurement)

                if po_line:
                    vals = self._update_purchase_order_line(
                        procurement.product_id,
                        procurement.product_qty,
                        procurement.product_uom_id,
                        company_id,
                        procurement.values,
                        po_line,
                    )
                    po_line.sudo().write(vals)
                else:
                    if (
                        procurement.product_uom_id.compare(procurement.product_qty, 0)
                        <= 0
                    ):
                        continue
                    line_vals = self.env[
                        "purchase.order.line"
                    ]._prepare_purchase_order_line_from_procurement(
                        *procurement,
                        po,
                    )
                    po_line_values.append(line_vals)
                    if (
                        earliest_date_commitment is None
                        or line_vals["date_commitment"] < earliest_date_commitment
                    ):
                        earliest_date_commitment = line_vals["date_commitment"]
                    date_commitment = po.date_commitment or earliest_date_commitment
                    order_date_commitment = date_commitment - relativedelta(
                        days=procurement.values["supplier"].delay,
                    )
                    if fields.Date.to_date(order_date_commitment) < fields.Date.to_date(
                        po.date_order,
                    ):
                        po.date_order = order_date_commitment

            self.env["purchase.order.line"].sudo().create(po_line_values)

    @api.model
    def run(self, procurements, raise_user_error=True):
        wh_by_comp = {}
        for procurement in procurements:
            routes = procurement.values.get("route_ids")
            if routes and routes._has_buy_rule():
                company = procurement.company_id
                if company not in wh_by_comp:
                    wh_by_comp[company] = self.env["stock.warehouse"].search(  # noqa: E8507 - one lookup per company, cached across procurements
                        [("company_id", "=", company.id)],
                    )
                wh = wh_by_comp[company]
                procurement.values["route_ids"] |= wh.reception_route_id
        return super().run(procurements, raise_user_error=raise_user_error)

    def _update_purchase_order_line(
        self,
        product_id,
        product_qty,
        product_uom_id,
        company_id,
        values,
        line,
    ):
        partner = values["supplier"].partner_id
        procurement_uom_po_qty = product_uom_id._get_quantity_in_unit(
            product_qty,
            line.product_uom_id,
            rounding_method="HALF-UP",
        )
        seller = self.env["purchase.price.resolver"]._get_seller(
            product_id,
            partner=partner,
            quantity=line.product_qty + procurement_uom_po_qty,
            uom=line.product_uom_id,
            date=line.order_id.date_order and line.order_id.date_order.date(),
            company=company_id,
            params={"force_uom": values.get("force_uom")},
        )

        res = {
            "product_qty": line.product_qty + procurement_uom_po_qty,
            "move_dest_ids": [
                Command.link(x.id) for x in values.get("move_dest_ids", [])
            ],
        }
        if (
            seller
            and seller.product_uom_id != line.product_uom_id
            and not values.get("force_uom")
        ):
            res["product_qty"] = line.product_uom_id._get_quantity_in_unit(
                res["product_qty"],
                seller.product_uom_id,
                rounding_method="HALF-UP",
            )
            res["product_uom_id"] = seller.product_uom_id
        orderpoint_id = values.get("orderpoint_id")
        if orderpoint_id:
            res["orderpoint_id"] = orderpoint_id.id
        return res
