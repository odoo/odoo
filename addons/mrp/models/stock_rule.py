import logging
from collections import defaultdict
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog
from odoo.tools import OrderedSet

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class StockRule(models.Model):
    _inherit = "stock.rule"
    action = fields.Selection(
        selection_add=[("manufacture", "Manufacture")],
        ondelete={"manufacture": "cascade"},
    )

    MAX_MANUFACTURE_BATCHES = 1000

    def _get_action_messages(self):
        message_dict = super()._get_action_messages()
        source, destination, direct_destination, operation = self._get_message_labels()
        manufacture_message = _(
            "When products are needed in <b>%s</b>, <br/> a manufacturing order is created to fulfill the need.",
            destination,
        )
        if self.location_src_id:
            manufacture_message += _(
                " <br/><br/> The components will be taken from <b>%s</b>.", source
            )
        if direct_destination and not self.location_dest_from_rule:
            manufacture_message += _(
                " <br/><br/> The manufactured products will be moved towards <b>%(destination)s</b>, <br/> as specified from <b>%(operation)s</b> destination.",
                destination=direct_destination,
                operation=operation,
            )
        message_dict["manufacture"] = manufacture_message
        return message_dict

    def _get_domain_picking_type_code(self):
        codes = super()._get_domain_picking_type_code()
        if self.action == "manufacture":
            codes = [*codes, "mrp_operation"]
        return codes

    def _is_mo_auto_confirm_required(self, p):
        if not p.move_raw_ids:
            return not p.workorder_ids and (
                p.orderpoint_id
                or "make_to_stock" in p.move_dest_ids.mapped("procure_method")
            )
        return not p.orderpoint_id

    @api.model
    def run(self, procurements, raise_user_error=True):
        procurements_without_kit = []
        product_by_company = defaultdict(OrderedSet)
        for procurement in procurements:
            product_by_company[procurement.company_id].add(procurement.product_id.id)
        kits_by_company = {
            company: self.env["mrp.bom"]._get_bom_by_product(
                self.env["product.product"].browse(product_ids),
                company_id=company.id,
                bom_type="phantom",
            )
            for company, product_ids in product_by_company.items()
        }
        for procurement in procurements:
            bom_kit = kits_by_company[procurement.company_id].get(
                procurement.product_id
            )
            if bom_kit:
                order_qty = procurement.product_uom_id._get_quantity_in_unit(
                    procurement.product_qty, bom_kit.product_uom_id, round=False
                )
                qty_to_produce = order_qty / bom_kit.product_qty
                _dummy, bom_sub_lines = bom_kit._explode(
                    procurement.product_id,
                    qty_to_produce,
                    never_attribute_values=procurement.values.get(
                        "never_product_template_attribute_value_ids"
                    ),
                )
                for bom_line, bom_line_data in bom_sub_lines:
                    bom_line_uom = bom_line.product_uom_id
                    quant_uom = bom_line.product_id.uom_id
                    values = dict(procurement.values, bom_line_id=bom_line.id)
                    component_qty, procurement_uom = (
                        bom_line_uom._get_procurement_qty_and_uom(
                            bom_line_data["qty"], quant_uom
                        )
                    )
                    procurements_without_kit.append(
                        self.env["stock.rule"].Procurement(
                            bom_line.product_id,
                            component_qty,
                            procurement_uom,
                            procurement.location_id,
                            procurement.name,
                            procurement.origin,
                            procurement.company_id,
                            values,
                        )
                    )
            else:
                procurements_without_kit.append(procurement)
        return super().run(procurements_without_kit, raise_user_error=raise_user_error)

    def _is_route_usable_for(self, product, route):
        if route._has_manufacture_rule():
            return any(
                bom.type == "normal" for bom in product.bom_ids
            ) and super()._is_route_usable_for(product, route)
        return super()._is_route_usable_for(product, route)

    @api.model
    def _get_action_runners(self):
        return {**super()._get_action_runners(), "manufacture": "_run_manufacture"}

    @api.model
    def _run_manufacture(self, procurements):
        new_productions_values_by_company = defaultdict(lambda: defaultdict(list))
        _debug.pipeline("run_manufacture", procurements=len(procurements))
        for procurement, rule in procurements:
            if procurement.product_uom_id.compare(procurement.product_qty, 0) <= 0:
                _debug.logic("procurement_skipped", product=procurement.product_id)
                continue
            bom = rule._get_matching_bom(
                procurement.product_id, procurement.company_id, procurement.values
            )

            mo = self.env["mrp.production"]
            if procurement.origin != "MPS":
                domain = rule._get_domain_mo_for_procurement(procurement, bom)
                mo = self.env["mrp.production"].sudo().search(domain, limit=1)  # noqa: E8507 - one probe per procurement: the domain is the procurement's own product, company and values
            is_batch_size = bom and bom.enable_batch_size
            _debug.logic(
                "procurement_routed", bom=bom, mo=mo, batch=bool(is_batch_size)
            )
            if not mo or is_batch_size:
                if not bom:
                    waiting_moves = procurement.values.get("move_dest_ids")
                    log = _logger.warning if waiting_moves else _logger.debug
                    log(
                        "No bill of materials to manufacture %r in %r: rule %r produced"
                        " nothing, leaving %s.",
                        procurement.product_id.display_name,
                        procurement.location_id.display_name,
                        rule.display_name,
                        f"stock.move {waiting_moves.ids} waiting on it"
                        if waiting_moves
                        else "no demand unsatisfied",
                    )
                    continue
                vals = rule._prepare_mo_vals(procurement, bom)
                for batch_qty in rule._get_manufacture_batches(
                    procurement, bom, is_batch_size
                ):
                    new_productions_values_by_company[procurement.company_id.id][
                        "values"
                    ].append({**vals, "product_qty": batch_qty})
                    new_productions_values_by_company[procurement.company_id.id][
                        "procurements"
                    ].append(procurement)
            else:
                procurement_product_uom_qty = (
                    procurement.product_uom_id._get_quantity_in_unit(
                        procurement.product_qty, procurement.product_id.uom_id
                    )
                )
                self.env["change.production.qty"].sudo().with_context(
                    skip_activity=True
                ).create(
                    {
                        "mo_id": mo.id,
                        "product_qty": mo.product_id.uom_id._get_quantity_in_unit(
                            (mo.product_uom_qty + procurement_product_uom_qty),
                            mo.product_uom_id,
                        ),
                    }
                ).change_prod_qty()
                _debug.lifecycle(
                    "production_qty_increased", mo=mo, qty=procurement_product_uom_qty
                )
                if procurement.values.get("move_dest_ids"):
                    mo.move_finished_ids.filtered(
                        lambda m, procurement=procurement: (
                            m.product_id == procurement.product_id
                            and m.state not in ("done", "cancel")
                        )
                    ).move_dest_ids = [
                        Command.link(m.id) for m in procurement.values["move_dest_ids"]
                    ]

        for company_id in new_productions_values_by_company:
            productions_vals_list = new_productions_values_by_company[company_id][
                "values"
            ]
            productions = (
                self.env["mrp.production"]
                .with_user(SUPERUSER_ID)
                .sudo()
                .with_company(company_id)
                .create(productions_vals_list)
            )
            _debug.lifecycle("productions_created", productions=productions)
            productions.filtered(self._is_mo_auto_confirm_required).action_confirm()
            productions._post_run_manufacture(
                new_productions_values_by_company[company_id]["procurements"]
            )
        return True

    def _get_manufacture_batches(self, procurement, bom, is_batch_size):
        """Yield the quantity of each manufacturing order a procurement becomes.

        Every figure is in the BoM's unit, because that is the unit
        `batch_size` is written in. Converting the batch into the procurement's
        unit first and counting down there rounds the batch to the procurement
        unit's precision: a 0.4 kg batch procured in tonnes becomes 0.01 t,
        which is 10 kg, so the orders come out twenty-five times the size the
        BoM asked for and the count explodes to match.

        The count is capped the way `mrp.production.split` caps its own, and
        for the same reason: a batch size small against the demand is a
        configuration mistake, and answering it with thousands of orders is
        worse than refusing it.
        """
        uom = bom.product_uom_id
        quantity = procurement.product_uom_id._get_quantity_in_unit(
            procurement.product_qty, uom, round=False
        )
        if not is_batch_size:
            yield procurement.product_uom_id._get_quantity_in_unit(
                procurement.product_qty, uom
            )
            return
        batch_size = bom.batch_size
        if uom.compare(batch_size, 0) <= 0:
            _debug.logic(
                "manufacture_refused",
                reason="batch_size_not_positive",
                bom=bom.id,
                batch_size=batch_size,
            )
            raise UserError(
                self.env._(
                    "The batch size of %(bom)s must be positive to manufacture"
                    " %(product)s.",
                    bom=bom.display_name,
                    product=procurement.product_id.display_name,
                )
            )
        whole, remainder = divmod(quantity, batch_size)
        batches = max(int(whole) + (0 if uom.is_zero(remainder) else 1), 1)
        if batches > self.MAX_MANUFACTURE_BATCHES:
            _debug.logic(
                "manufacture_refused",
                reason="too_many_batches",
                bom=bom.id,
                batches=batches,
                maximum=self.MAX_MANUFACTURE_BATCHES,
            )
            raise UserError(
                self.env._(
                    "Manufacturing %(quantity)s %(unit)s of %(product)s in"
                    " batches of %(size)s would take %(count)s manufacturing"
                    " orders, more than the %(maximum)s allowed. Use a larger"
                    " batch size.",
                    quantity=quantity,
                    unit=uom.display_name,
                    product=procurement.product_id.display_name,
                    size=batch_size,
                    count=batches,
                    maximum=self.MAX_MANUFACTURE_BATCHES,
                )
            )
        _debug.logic(
            "manufacture_batched",
            bom=bom.id,
            quantity=quantity,
            batch_size=batch_size,
            batches=batches,
        )
        for _batch in range(batches):
            # `uom.round` is the 'Product Unit' decimal precision rounded
            # HALF-UP; sizing a record wants the unit's own `rounding`, rounded
            # UP, which is what `_get_quantity_in_unit` does and what the caller
            # this replaced did.
            yield uom._get_quantity_in_unit(batch_size, uom)

    def _prepare_stock_move_vals(self, procurement):
        res = super()._prepare_stock_move_vals(procurement)
        res["production_group_id"] = procurement.values.get("production_group_id")
        return res

    def _get_fields_custom_move(self):
        fields = super()._get_fields_custom_move()
        fields += ["bom_line_id"]
        return fields

    def _get_matching_bom(self, product_id, company_id, values):
        if values.get("bom_id", False):
            _debug.logic("rule_bom", by="values", product=product_id.id)
            return values["bom_id"]
        if values.get("orderpoint_id", False) and values["orderpoint_id"].bom_id:
            _debug.logic("rule_bom", by="orderpoint", product=product_id.id)
            return values["orderpoint_id"].bom_id
        bom = self.env["mrp.bom"]._get_bom_by_product(
            product_id,
            picking_type=self.picking_type_id,
            bom_type="normal",
            company_id=company_id.id,
        )[product_id]
        if bom:
            _debug.logic(
                "rule_bom", by="picking_type", product=product_id.id, bom=bom.id
            )
            return bom
        _debug.logic("rule_bom", by="any_picking_type", product=product_id.id)
        return self.env["mrp.bom"]._get_bom_by_product(
            product_id, picking_type=False, bom_type="normal", company_id=company_id.id
        )[product_id]

    def _get_domain_mo_for_procurement(self, procurement, bom):
        domain = (
            ("bom_id", "=", bom.id),
            ("product_id", "=", procurement.product_id.id),
            ("state", "in", ["draft", "confirmed"]),
            ("is_planned", "=", False),
            ("picking_type_id", "=", self.picking_type_id.id),
            ("company_id", "=", procurement.company_id.id),
            ("user_id", "=", False),
            (
                "reference_ids",
                "=",
                procurement.values.get(
                    "reference_ids", self.env["stock.reference"]
                ).ids,
            ),
        )
        if production_group_id := procurement.values.get("production_group_id"):
            domain += (("production_group_id.parent_ids", "=", production_group_id),)
        if procurement.values.get("orderpoint_id"):
            procurement_date = datetime.combine(
                fields.Date.to_date(procurement.values["date_planned"])
                - relativedelta(days=int(bom.produce_delay)),
                datetime.max.time(),
            )
            domain += (
                "|",
                "&",
                ("state", "=", "draft"),
                ("date_deadline", "<=", procurement_date),
                "&",
                ("state", "=", "confirmed"),
                ("date_start", "<=", procurement_date),
            )
        return domain

    def _prepare_mo_vals(self, procurement, bom):
        product_id = procurement.product_id
        product_uom_id = procurement.product_uom_id
        location_dest_id = procurement.location_id
        values = procurement.values
        date_planned = self._get_date_planned(bom, values)
        date_deadline = values.get("date_deadline") or date_planned + relativedelta(
            days=bom.produce_delay
        )
        picking_type = bom.picking_type_id or self.picking_type_id
        if not picking_type:
            warehouse = values.get("warehouse_id") or location_dest_id.warehouse_id
            picking_type = warehouse.manu_type_id
            if not picking_type:
                raise UserError(
                    _(
                        "No manufacturing operation type is configured for"
                        " %(product)s. Set one on the bill of materials, on the"
                        " manufacturing rule, or on the warehouse.",
                        product=product_id.display_name,
                    )
                )
        mo_values = {
            "origin": procurement.origin,
            "product_id": product_id.id,
            "product_description_variants": values.get("product_description_variants"),
            "never_product_template_attribute_value_ids": values.get(
                "never_product_template_attribute_value_ids"
            ),
            "product_qty": product_uom_id._get_quantity_in_unit(
                procurement.product_qty, bom.product_uom_id
            )
            if bom
            else procurement.product_qty,
            "product_uom_id": bom.product_uom_id.id if bom else product_uom_id.id,
            "location_src_id": picking_type.default_location_src_id.id,
            "location_dest_id": picking_type.default_location_dest_id.id
            or location_dest_id.id,
            "location_final_id": location_dest_id.id,
            "bom_id": bom.id,
            "date_deadline": date_deadline,
            "date_start": date_planned,
            "reference_ids": [
                Command.set(
                    values.get("reference_ids", self.env["stock.reference"]).ids
                )
            ],
            "propagate_cancel": self.propagate_cancel,
            "orderpoint_id": values.get("orderpoint_id", False)
            and values.get("orderpoint_id").id,
            "picking_type_id": picking_type.id,
            "company_id": procurement.company_id.id,
            "move_dest_ids": (
                values.get("move_dest_ids")
                and [(4, x.id) for x in values["move_dest_ids"]]
            )
            or False,
            "user_id": False,
        }
        if self.location_dest_from_rule:
            mo_values["location_dest_id"] = self.location_dest_id.id
        return mo_values

    def _get_date_planned(self, bom_id, values):
        format_date_planned = fields.Datetime.from_string(values["date_planned"])
        date_planned = format_date_planned - relativedelta(days=bom_id.produce_delay)
        if date_planned == format_date_planned:
            date_planned -= relativedelta(hours=1)
        return date_planned

    def _get_lead_days(self, product, **values):
        delays, delay_description = super()._get_lead_days(product, **values)
        bypass_delay_description = self.env.context.get("bypass_delay_description")
        manufacture_rule = self.filtered(lambda r: r.action == "manufacture")
        if not manufacture_rule:
            return delays, delay_description
        manufacture_rule.check_singleton()
        if "bom" in values:
            bom = values["bom"]
        else:
            bom = self.env["mrp.bom"]._get_bom_by_product(
                product,
                picking_type=manufacture_rule.picking_type_id,
                company_id=manufacture_rule.company_id.id,
            )[product]
        if not bom:
            _debug.logic(
                "lead_days_no_bom", product=product.id, rule=manufacture_rule.id
            )
            delays["total_delay"] += 365
            delays["no_bom_found_delay"] += 365
            if not bypass_delay_description:
                delay_description.append((_("No BoM Found"), _("+ %s day(s)", 365)))
        manufacture_delay = bom.produce_delay
        delays["total_delay"] += manufacture_delay
        delays["manufacture_delay"] += manufacture_delay
        if not bypass_delay_description:
            delay_description.append((_("Production End Date"), manufacture_delay))
            delay_description.append(
                (_("Manufacturing Lead Time"), _("+ %d day(s)", manufacture_delay))
            )
        if bom.type == "normal":
            warehouse = self.location_dest_id.warehouse_id
            for wh in warehouse:
                if wh.manufacture_steps != "mrp_one_step":
                    wh_manufacture_rules = product._get_rules_from_location(
                        product.property_stock_production, route_ids=wh.pbm_route_id
                    )
                    extra_delays, extra_delay_description = (
                        (wh_manufacture_rules - self)
                        .with_context(global_horizon_days=0)
                        ._get_lead_days(product, **values)
                    )
                    for key, value in extra_delays.items():
                        delays[key] += value
                    delay_description += extra_delay_description
        days_to_order = values.get("days_to_order", bom.days_to_prepare_mo)
        _debug.logic(
            "lead_days_manufacture",
            product=product.id,
            bom=bom.id,
            manufacture_delay=manufacture_delay,
            days_to_order=days_to_order,
            total=delays["total_delay"] + days_to_order,
        )
        delays["total_delay"] += days_to_order
        if not bypass_delay_description:
            delay_description.append((_("Production Start Date"), days_to_order))
            delay_description.append(
                (_("Days to Supply Components"), _("+ %d day(s)", days_to_order))
            )
        return delays, delay_description

    def _prepare_push_move_copy_values(self, move_to_copy, new_date):
        new_move_vals = super()._prepare_push_move_copy_values(move_to_copy, new_date)
        new_move_vals["production_group_id"] = move_to_copy.production_group_id.id
        new_move_vals["production_id"] = False
        return new_move_vals


class StockRoute(models.Model):
    _inherit = "stock.route"

    def _has_manufacture_rule(self):
        return self._has_rule_with_action("manufacture")

    def _is_valid_resupply_route_for_product(self, product):
        if self._has_manufacture_rule():
            return any(bom.type == "normal" for bom in product.bom_ids)
        return super()._is_valid_resupply_route_for_product(product)
