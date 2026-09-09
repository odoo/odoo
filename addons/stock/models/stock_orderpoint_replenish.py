import logging
from collections import defaultdict
from datetime import UTC, datetime, time
from itertools import batched

from dateutil import relativedelta
from psycopg import OperationalError

from odoo import SUPERUSER_ID, _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.fields import Domain
from odoo.libs.datetime import timezone
from odoo.modules.registry import Registry
from odoo.tools import format_date

from ..tools import debug_log as dbg
from odoo.addons.stock.models.stock_procurement import ProcurementException

_logger = logging.getLogger(__name__)


class StockWarehouseOrderpointReplenish(models.Model):
    _inherit = "stock.warehouse.orderpoint"

    @dbg.timed
    def action_replenish(self, force_to_max=False):
        dbg.pipeline.debug(
            "action_replenish on %s force_to_max=%s", dbg.rec(self), force_to_max
        )
        now = self.env.cr.now()
        forced_quantities = None
        if force_to_max:
            forced_quantities = {
                orderpoint.id: orderpoint._get_multiple_rounded_qty(
                    orderpoint.product_max_qty - orderpoint.qty_forecast,
                )
                for orderpoint in self
            }
        try:
            self._procure_orderpoint_confirm(
                company_id=self.env.company,
                forced_quantities=forced_quantities,
            )
        except UserError as e:
            if len(self) != 1:
                raise
            raise RedirectWarning(
                e,
                {
                    "name": self.product_id.display_name,
                    "type": "ir.actions.act_window",
                    "res_model": "product.product",
                    "res_id": self.product_id.id,
                    "views": [
                        (
                            self.env.ref("product.view_product_product_form_normal").id,
                            "form",
                        ),
                    ],
                },
                _("Edit Product"),
            ) from e
        notification = False
        if len(self) == 1:
            notification = self.with_context(
                written_after=now,
            )._prepare_action_replenishment_order_notification()
        self.action_remove_manual_qty_to_order()
        self._remove_processed_orderpoints()
        return notification

    def action_replenish_auto(self):
        self.trigger = "auto"
        return self.action_replenish()

    def action_remove_manual_qty_to_order(self):
        self.write({"qty_to_order_manual": 0, "qty_to_order_manual_set": False})

    def _get_default_rule(self):
        self.check_singleton()
        return self.env["stock.rule"]._get_rule(
            self.product_id,
            self.location_id,
            {
                "route_ids": self.route_id,
                "warehouse_id": self.warehouse_id,
            },
        )

    def _get_default_route_map(self):
        to_compute = self.filtered("location_id")
        empty_route = self.env["stock.route"]
        result = {orderpoint.id: empty_route for orderpoint in self}
        if not to_compute:
            return result
        rules_groups = self.env["stock.rule"]._read_group(
            [
                "|",
                ("route_id.product_selectable", "!=", False),
                ("route_id.product_categ_selectable", "!=", False),
                ("location_dest_id", "in", to_compute.location_id.ids),
                ("action", "in", ["pull_push", "pull"]),
                ("route_id.active", "!=", False),
            ],
            ["location_dest_id", "route_id"],
        )
        routes_by_location = defaultdict(list)
        for location_dest, route in rules_groups:
            routes_by_location[location_dest.id].append(route)
        for orderpoint in to_compute:
            product_routes = (
                orderpoint.product_id.route_ids
                | orderpoint.product_id.categ_id.route_ids
            )
            result[orderpoint.id] = next(
                (
                    route
                    for route in routes_by_location.get(orderpoint.location_id.id, ())
                    if route in product_routes
                ),
                empty_route,
            )
        return result

    def _get_replenishment_multiple_alternative(self, qty_to_order):
        self.check_singleton()
        return self._get_replenishment_multiple_alternative_map(
            {self.id: qty_to_order},
        ).get(self.id, False)

    def _get_replenishment_multiple_alternative_map(self, qty_by_orderpoint):
        return dict.fromkeys(self.ids, False)

    @dbg.timed
    def _get_qty_to_order_map(self):
        orderpoints_to_compute = self.filtered(
            lambda orderpoint: orderpoint.product_id and orderpoint.location_id,
        )
        result = {orderpoint.id: 0.0 for orderpoint in self - orderpoints_to_compute}
        if not orderpoints_to_compute:
            return result
        forecast_by_orderpoint = orderpoints_to_compute._get_qty_forecast_map()
        for orderpoint in orderpoints_to_compute:
            qty_forecast = forecast_by_orderpoint[orderpoint.id]
            if (
                orderpoint.product_uom_id.compare(
                    qty_forecast, orderpoint.product_min_qty
                )
                >= 0
            ):
                result[orderpoint.id] = 0.0
                continue
            qty_to_order = (
                max(orderpoint.product_min_qty, orderpoint.product_max_qty)
                - qty_forecast
            )
            result[orderpoint.id] = orderpoint._get_multiple_rounded_qty(qty_to_order)
            dbg.logic.debug(
                "[orderpoint:%s] forecast %s < min %s: order %s (rounded %s)",
                orderpoint.id,
                qty_forecast,
                orderpoint.product_min_qty,
                qty_to_order,
                result[orderpoint.id],
            )
        return result

    def _prepare_lead_time_params(self):
        self.check_singleton()
        return {
            "days_to_order": self.days_to_order,
        }

    def _prepare_lead_time_params_map(self):
        return {
            orderpoint.id: orderpoint._prepare_lead_time_params() for orderpoint in self
        }

    def _prepare_product_context(self):
        self.check_singleton()
        return {
            "location": self.location_id.id,
            "to_date": datetime.combine(self.lead_horizon_date, time.max),
        }

    @api.model
    def _prepare_action_orderpoint_replenish(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_orderpoint_replenish",
        )
        action["context"] = {
            key: value
            for key, value in self.env.context.items()
            if key.startswith(("search_default_", "searchpanel_default_", "default_"))
            or key in ("global_horizon_days", "allowed_company_ids", "lang", "tz")
        }
        orderpoints = (
            self.env["stock.warehouse.orderpoint"]
            .with_context(active_test=False)
            .search([])
        )
        if self.env.context.get("force_orderpoint_recompute", False):
            orderpoints._update_stored_values()
        orderpoints -= orderpoints._remove_processed_orderpoints()
        self.env["stock.replenishment.report"]._create_missing_orderpoints(
            orderpoints,
        )
        return action

    def _update_stored_values(self):
        stored = ("qty_to_order_computed", "deadline_date", "actual_lead_time_avg")
        for field_name in stored:
            self.env.add_to_compute(self._fields[field_name], self)
        self.flush_recordset(stored)

    @api.model
    def _prepare_orderpoint_vals(self, product_id, location_id):
        return {
            "product_id": product_id,
            "location_id": location_id,
            "product_max_qty": 0.0,
            "product_min_qty": 0.0,
            "trigger": "manual",
            "is_autogenerated": True,
        }

    def _get_domain_replenishment_source(self):
        auto = self.filtered(lambda orderpoint: orderpoint.trigger == "auto")
        domain = Domain("orderpoint_id", "in", auto.ids)
        written_after = self.env.context.get("written_after")
        if not written_after:
            return domain
        manual = self - auto
        if manual:
            domain |= Domain("product_id", "in", manual.product_id.ids) & Domain(
                "company_id",
                "in",
                manual.company_id.ids,
            )
        return domain & Domain("write_date", ">=", written_after)

    @api.model
    def _prepare_action_replenishment_notification(self, title, label, url):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": "%s",
                "links": [{"label": label, "url": url}],
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _prepare_action_replenishment_order_notification(self):
        self.check_singleton()
        move = self.env["stock.move"].search(
            self._get_domain_replenishment_source(),
            limit=1,
        )
        if (
            (
                move.location_id.warehouse_id
                and move.location_id.warehouse_id != self.warehouse_id
            )
            or move.location_id.usage == "transit"
        ) and move.picking_id:
            return self._prepare_action_replenishment_notification(
                _("The inter-warehouse transfers have been generated"),
                move.picking_id.name,
                "/odoo/action-stock.stock_picking_action_picking_type/"
                f"{move.picking_id.id}",
            )
        return False

    def _get_orderpoint_procurement_date(self):
        self.check_singleton()
        return (
            datetime.combine(self.lead_horizon_date, time(12))
            .replace(tzinfo=timezone(self.company_id.partner_id.tz or "UTC"))
            .astimezone(UTC)
            .replace(tzinfo=None)
        )

    def _get_multiple_rounded_qty(self, qty_to_order):
        replenishment_multiple = (
            self.replenishment_uom_id
            or self._get_replenishment_multiple_alternative(qty_to_order)
        )
        if replenishment_multiple and self.product_id.uom_id._has_common_reference(
            replenishment_multiple
        ):
            qty_to_order = self.product_id.uom_id._get_quantity_in_unit(
                qty_to_order,
                replenishment_multiple,
            )
            qty_to_order = fields.Float.round(
                qty_to_order,
                precision_digits=0,
                rounding_method="UP",
            )
            qty_to_order = replenishment_multiple._get_quantity_in_unit(
                qty_to_order,
                self.product_id.uom_id,
            )
        return qty_to_order

    def get_horizon_days(self):
        return self._get_canonical_horizon_days()

    def _get_horizon_days(self, company=None):
        return self.env.context.get(
            "global_horizon_days",
            self._get_canonical_horizon_days(company),
        )

    def _get_canonical_horizon_days(self, company=None):
        company = company or self.company_id or self.env.company
        return company.horizon_days

    def _with_canonical_horizon(self):
        if "global_horizon_days" not in self.env.context:
            return self
        return self.with_context(
            {
                key: value
                for key, value in self.env.context.items()
                if key != "global_horizon_days"
            },
        )

    def _prepare_procurement_vals(self, date=False):
        date_deadline = date or fields.Date.today()
        dates_info = self.product_id._get_dates_info(
            date_deadline,
            self.location_id,
            route_ids=self.route_id,
        )
        values = {
            "route_ids": self.route_id,
            "date_planned": dates_info["date_planned"],
            "date_order": dates_info["date_order"],
            "date_deadline": date or False,
            "warehouse_id": self.warehouse_id,
            "orderpoint_id": self.trigger == "auto" and self,
        }
        reference = self.env.context.get("origins")
        if reference:
            values["reference_ids"] = self.env["stock.reference"].browse(
                reference.get(self.id),
            )
        return values

    def _prepare_procurements(self, forced_quantities):
        procurements = []
        origins_by_orderpoint = self.env.context.get("origins", {})
        for orderpoint in self:
            quantity = forced_quantities.get(orderpoint.id, orderpoint.qty_to_order)
            if orderpoint.product_uom_id.compare(quantity, 0.0) != 1:
                dbg.logic.debug(
                    "[orderpoint:%s] nothing to procure (qty %s)",
                    orderpoint.id,
                    quantity,
                )
                continue
            origin_ids = origins_by_orderpoint.get(orderpoint.id, False)
            if origin_ids:
                references = self.env["stock.reference"].browse(origin_ids)
                origin = (
                    f"{orderpoint.display_name} - {','.join(references.mapped('name'))}"
                )
            else:
                origin = orderpoint.name
            date = orderpoint._get_orderpoint_procurement_date()
            horizon_days = orderpoint._get_horizon_days()
            if horizon_days:
                date -= relativedelta.relativedelta(days=horizon_days)
            dbg.pipeline.debug(
                "[orderpoint:%s] procurement product=%s qty=%s date=%s origin=%s",
                orderpoint.id,
                orderpoint.product_id.id,
                quantity,
                date,
                origin,
            )
            procurements.append(
                self.env["stock.rule"].Procurement(
                    orderpoint.product_id,
                    quantity,
                    orderpoint.product_uom_id,
                    orderpoint.location_id,
                    orderpoint.name,
                    origin,
                    orderpoint.company_id,
                    orderpoint._prepare_procurement_vals(date=date),
                ),
            )
        return procurements

    def _run_procurement_batch(
        self,
        forced_quantities,
        raise_user_error=True,
        can_retry=False,
    ):
        orderpoints = self
        failures = []
        remaining_retries = self._PROCUREMENT_RETRIES
        while orderpoints:
            procurements = orderpoints._prepare_procurements(forced_quantities)
            dbg.pipeline.debug(
                "_run_procurement_batch: %d orderpoints -> %d procurements (retries left %d)",
                len(orderpoints),
                len(procurements),
                remaining_retries,
            )
            try:
                with self.env.cr.savepoint():
                    self.env["stock.rule"].with_context(from_orderpoint=True).run(
                        procurements,
                        raise_user_error=raise_user_error,
                    )
            except ProcurementException as errors:
                batch_failures = [
                    (
                        procurement.values.get("orderpoint_id") or self.browse(),
                        error_msg,
                    )
                    for procurement, error_msg in errors.procurement_exceptions
                ]
                failures += batch_failures
                failed = self.browse().concat(
                    *[failure[0] for failure in batch_failures]
                )
                dbg.logic.debug(
                    "_run_procurement_batch: %d failures on %s, retrying without them",
                    len(batch_failures),
                    dbg.rec(failed),
                )
                if not failed:
                    _logger.error(
                        "Unable to attribute a procurement failure to an orderpoint;"
                        " %d orderpoints were rolled back and not retried: %s",
                        len(orderpoints),
                        "; ".join(msg for _op, msg in batch_failures),
                    )
                    break
                orderpoints -= failed
            except OperationalError as error:
                if error.sqlstate not in ("40001", "40P01") or not can_retry:
                    raise
                dbg.logic.debug(
                    "_run_procurement_batch: serialization failure %s, rolling back",
                    error.sqlstate,
                )
                self.env.cr.rollback()
                remaining_retries -= 1
                if remaining_retries <= 0:
                    _logger.error(
                        "Serialization failure while processing a batch of %d "
                        "orderpoints; giving up after %d retries.",
                        len(orderpoints),
                        self._PROCUREMENT_RETRIES,
                    )
                    break
            else:
                orderpoints._post_process_scheduler()
                break
        return failures

    def _schedule_procurement_failure_activities(self, failures):
        model_product_template_id = self.env.ref("product.model_product_template").id
        reported = []
        for orderpoint, error_msg in failures:
            if orderpoint:
                reported.append((orderpoint, error_msg))
            else:
                _logger.error("Orderpoint procurement failed: %s", error_msg)

        orderpoints = self.browse()
        for orderpoint, _error_msg in reported:
            orderpoints |= orderpoint
        templates = orderpoints.product_id.product_tmpl_id
        notes_per_template = defaultdict(list)
        for activity in self.env["mail.activity"].search(
            [
                ("res_id", "in", templates.ids),
                ("res_model_id", "=", model_product_template_id),
            ]
        ):
            notes_per_template[activity.res_id].append(activity.note or "")

        for orderpoint, error_msg in reported:
            template = orderpoint.product_id.product_tmpl_id
            if any(error_msg in note for note in notes_per_template[template.id]):
                continue
            template.with_user(SUPERUSER_ID).activity_schedule(
                "mail.mail_activity_data_warning",
                note=error_msg,
                user_id=orderpoint.product_id.responsible_id.id or SUPERUSER_ID,
            )
            notes_per_template[template.id].append(error_msg)

    @dbg.timed
    def _procure_orderpoint_confirm(
        self,
        use_new_cursor=False,
        company_id=None,
        raise_user_error=True,
        forced_quantities=None,
    ):
        dbg.lifecycle.debug(
            "_procure_orderpoint_confirm on %s new_cursor=%s company=%s forced=%d",
            dbg.rec(self),
            use_new_cursor,
            getattr(company_id, "id", company_id),
            len(forced_quantities or ()),
        )
        scoped = self.with_company(company_id)
        forced_quantities = forced_quantities or {}
        dbname = self.env.cr.dbname

        for batch_ids in batched(scoped.ids, 1000, strict=False):
            cr = Registry(dbname).cursor() if use_new_cursor else None
            batch_env = scoped.env(cr=cr) if cr is not None else scoped.env
            committed = False
            try:
                batch = batch_env["stock.warehouse.orderpoint"].browse(batch_ids)
                failures = batch._run_procurement_batch(
                    forced_quantities,
                    raise_user_error=raise_user_error,
                    can_retry=use_new_cursor,
                )
                batch._schedule_procurement_failure_activities(failures)
                if cr is not None:
                    cr.commit()
                    committed = True
                    _logger.info(
                        "A batch of %d orderpoints is processed and committed",
                        len(batch_ids),
                    )
            finally:
                if cr is not None:
                    try:
                        if not committed:
                            cr.rollback()
                            _logger.warning(
                                "A batch of %d orderpoints failed and was rolled back",
                                len(batch_ids),
                            )
                    finally:
                        cr.close()

        return {}

    def _post_process_scheduler(self):
        return True

    def _get_quantity_in_progress(self):
        return dict.fromkeys(self._ids, 0.0)

    @api.autovacuum
    def _remove_processed_orderpoints(self):
        domain = Domain(
            [
                ("is_autogenerated", "=", True),
                ("trigger", "=", "manual"),
                ("qty_to_order", "<=", 0.0),
            ],
        )
        if self.ids:
            domain &= Domain("id", "in", self.ids)
        orderpoints_to_remove = (
            self.env["stock.warehouse.orderpoint"]
            .with_context(active_test=False)
            .search(domain)
        )
        dbg.lifecycle.debug(
            "_remove_processed_orderpoints: %s", dbg.rec(orderpoints_to_remove)
        )
        orderpoints_to_remove.unlink()
        return orderpoints_to_remove

    def action_stock_replenishment_info(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_stock_replenishment_info",
        )
        action["name"] = _(
            "Replenishment Information for %(product)s in %(warehouse)s",
            product=self.product_id.display_name,
            warehouse=self.warehouse_id.display_name,
        )
        res = self.env["stock.replenishment.info"].create(
            {
                "orderpoint_id": self.id,
            },
        )
        action["res_id"] = res.id
        return action

    def action_product_forecast_report(self):
        self.check_singleton()
        action = self.product_id.action_product_forecast_report()
        action["context"] = {
            "active_id": self.product_id.id,
            "active_model": "product.product",
            "lead_horizon_date": format_date(self.env, self.lead_horizon_date),
            "qty_to_order": self.qty_to_order,
        }
        warehouse = self.warehouse_id
        if warehouse:
            action["context"]["warehouse_id"] = warehouse.id
        return action

    @api.model
    def action_view_orderpoints(self):
        return self._prepare_action_orderpoint_replenish()
