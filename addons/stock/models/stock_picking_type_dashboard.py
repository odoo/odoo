import json
from datetime import UTC

from odoo import _, api, models
from odoo.fields import Domain
from odoo.libs.sql import escape_psql
from odoo.tools import SQL

from ..tools import debug_log as dbg
from odoo.addons.base.models.ir_actions_actions import _eval_dict_or_default


class StockPickingTypeDashboard(models.Model):
    _inherit = "stock.picking.type"

    def _get_picking_count_buckets(self, query):
        picking = self.env["stock.picking"]
        table = picking._table
        state = picking._field_to_sql(table, "state", query)
        is_open = SQL("%s IN %s", state, self._OPEN_PICKING_STATES)
        late_cutoff = (
            self._get_date_category_boundaries()["today"]
            .astimezone(UTC)
            .replace(tzinfo=None)
        )
        return {
            "count_picking_ready": SQL("%s = 'assigned'", state),
            "count_picking_waiting": SQL("%s IN ('confirmed', 'waiting')", state),
            "count_picking_late": SQL(
                "%s AND (%s < %s OR %s)",
                is_open,
                picking._field_to_sql(table, "date_planned", query),
                late_cutoff,
                picking._field_to_sql(table, "has_deadline_issue", query),
            ),
            "count_picking_backorders": SQL(
                "%s AND %s IS NOT NULL",
                is_open,
                picking._field_to_sql(table, "backorder_id", query),
            ),
        }

    @dbg.timed
    def _compute_picking_count(self):
        picking = self.env["stock.picking"]
        query = picking._search(
            Domain("picking_type_id", "in", self.ids)
            & Domain("state", "in", self._OPEN_PICKING_STATES)
        )
        buckets = self._get_picking_count_buckets(query)
        counts = {}
        if not query.is_empty():
            group = picking._field_to_sql(picking._table, "picking_type_id", query)
            query.groupby = SQL("1")
            rows = self.env.execute_query(
                query.select(
                    group,
                    *(
                        SQL("COUNT(*) FILTER (WHERE %s)", condition)
                        for condition in buckets.values()
                    ),
                )
            )
            counts = {row[0]: row[1:] for row in rows}
            dbg.performance.debug(
                "_compute_picking_count: one grouped query for %d types, %d rows",
                len(self),
                len(rows),
            )
        empty = (0,) * len(buckets)
        for record in self:
            for field_name, count in zip(
                buckets, counts.get(record.id, empty), strict=True
            ):
                record[field_name] = count

    def _compute_count_move_ready(self):
        data = self.env["stock.move"]._read_group(
            [("state", "=", "assigned"), ("picking_type_id", "in", self.ids)],
            ["picking_type_id"],
            ["__count"],
        )
        count = {picking_type.id: count for picking_type, count in data}
        for record in self:
            record.count_move_ready = count.get(record.id, 0)

    @dbg.timed
    def _compute_kanban_dashboard_graph(self):
        summaries = {}
        for (
            picking_type_id,
            counts,
            data_series_name,
        ) in self._get_aggregated_records_by_date():
            summary = summaries.setdefault(
                picking_type_id, self._get_empty_graph_summary(data_series_name)
            )
            for date_category, count in counts.items():
                summary["total_" + date_category] += count
        self._update_graph_data(summaries)

    def _get_aggregated_records_by_date(self):
        if not self:
            return []
        counts_by_type = self._get_date_category_counts(
            "stock.picking",
            "date_planned",
            "picking_type_id",
            [("state", "in", ["assigned", "waiting", "confirmed"])],
        )
        label = self.env._("Transfers")
        return [
            (picking_type_id, counts, label)
            for picking_type_id, counts in counts_by_type.items()
        ]

    @api.model
    def _get_empty_graph_summary(self, data_series_name):
        return {
            "data_series_name": data_series_name,
            **{f"total_{key}": 0 for key, *_ in self.DATE_CATEGORIES},
        }

    def _update_graph_data(self, summaries):
        data_category_mapping = {}
        for key, _upper, label, kind in self.DATE_CATEGORIES:
            text = self.env._(label)  # pylint: disable=gettext-variable
            data_category_mapping[f"total_{key}"] = {"label": text, "type": kind}

        for picking_type in self:
            summary = summaries.get(picking_type.id) or self._get_empty_graph_summary(
                self.env._("Transfers")
            )
            empty = all(summary[key] == 0 for key in data_category_mapping)
            graph_data = [
                {
                    "key": _("Sample data") if empty else summary["data_series_name"],
                    "picking_type_id": None if empty else picking_type.id,
                    "values": [
                        dict(
                            value,
                            value=summary[key],
                            type="sample" if empty else value["type"],
                            category=key.removeprefix("total_"),
                        )
                        for key, value in data_category_mapping.items()
                    ],
                }
            ]
            picking_type.kanban_dashboard_graph = json.dumps(graph_data)

    def action_view_pickings_late(self):
        return self._prepare_action_by_xml_id("stock.action_picking_tree_late")

    def action_view_pickings_backorder(self):
        return self._prepare_action_by_xml_id("stock.action_picking_tree_backorder")

    def action_view_pickings_waiting(self):
        return self._prepare_action_by_xml_id("stock.action_picking_tree_waiting")

    def action_view_pickings_ready(self):
        return self._prepare_action_by_xml_id("stock.action_picking_tree_ready")

    def action_view_moves_ready(self):
        return self._prepare_action_by_xml_id(
            "stock.action_get_picking_type_ready_moves"
        )

    def action_view_moves_analysis(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.stock_move_action"
        )
        domains = [action["domain"] or []]
        if self:
            self.check_singleton()
            domains.append([("picking_type_id", "=", self.id)])
        action["domain"] = Domain.AND(domains)
        return action

    def action_view_pickings(self):
        self._check_single_or_empty()
        action_by_code = {
            "incoming": "stock.action_picking_tree_incoming",
            "outgoing": "stock.action_picking_tree_outgoing",
            "internal": "stock.action_picking_tree_internal",
        }
        return self._prepare_action_by_xml_id(
            action_by_code.get(self.code, "stock.stock_picking_action_picking_type")
        )

    def _prepare_action_by_xml_id(self, action_xmlid):
        self._check_single_or_empty()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(action_xmlid)
        context = {}

        if self:
            action["display_name"] = self.display_name
            context.update(
                {
                    "default_picking_type_id": self.id,
                    "default_company_id": self.company_id.id,
                }
            )
        else:
            allowed_company_ids = self.env.context.get("allowed_company_ids", [])
            if allowed_company_ids:
                context.update(
                    {
                        "default_company_id": allowed_company_ids[0],
                    }
                )

        action_context = _eval_dict_or_default(
            action["context"], dict(self.env.context), {}
        )
        context = {**action_context, **context}
        action["context"] = context
        if self:
            action["domain"] = [("picking_type_id", "=", self.id)]

        if action.get("res_model") == "stock.picking":
            action["help"] = self.env["ir.ui.view"]._render_template(
                "stock.help_message_template",
                {
                    "picking_type_code": context.get("restricted_picking_type_code")
                    or self.code,
                },
            )

        return action

    def _get_code_report_name(self):
        self.check_singleton()
        code_names = {
            "outgoing": _("Delivery Note"),
            "incoming": _("Goods Receipt Note"),
            "internal": _("Internal Move"),
        }
        return code_names.get(self.code)

    @api.model
    def action_redirect_to_barcode_installation(self):
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "base.open_module_tree"
        )
        action["context"] = dict(
            _eval_dict_or_default(action["context"], dict(self.env.context), {}),
            search_default_name="Barcode",
        )
        return action

    def _prepare_sequence_vals(self, warehouse_name=None, warehouse_code=None):
        self.check_singleton()
        warehouse = self.warehouse_id
        if not warehouse:
            return {
                "name": _("Sequence %(code)s", code=self.sequence_code),
                "prefix": self.sequence_code,
                "padding": 5,
                "company_id": self.company_id.id,
            }
        name = warehouse_name or warehouse.name
        code = warehouse._normalize_code(warehouse_code or warehouse.code)
        return {
            "name": _(
                "%(warehouse)s Sequence %(code)s",
                warehouse=name,
                code=self.sequence_code,
            ),
            "prefix": "%s/%s/" % (code, self.sequence_code),
            "padding": 5,
            "company_id": self.company_id.id,
        }

    @dbg.timed
    def _update_reference_sequences(self, only=None):
        missing = self.browse()
        for picking_type in self:
            if not picking_type.sequence_code:
                continue
            if not picking_type.sequence_id:
                missing |= picking_type
                continue
            wanted = picking_type._prepare_sequence_vals()
            if only is not None:
                wanted = {name: value for name, value in wanted.items() if name in only}
            sequence = picking_type.sequence_id.sudo()
            changed = {
                name: value
                for name, value in wanted.items()
                if sequence._fields[name].convert_to_write(sequence[name], sequence)
                != value
            }
            if changed:
                dbg.lifecycle.debug(
                    "[picking_type:%s] sequence %s updated: %s",
                    picking_type.id,
                    sequence.id,
                    dbg.keys(changed),
                )
                sequence.write(changed)
        if missing:
            dbg.lifecycle.debug(
                "_update_reference_sequences: creating for %s", dbg.rec(missing)
            )
            sequences = (
                self.env["ir.sequence"]
                .sudo()
                .create(
                    [picking_type._prepare_sequence_vals() for picking_type in missing]
                )
            )
            for picking_type, sequence in zip(missing, sequences, strict=True):
                picking_type.sequence_id = sequence.id

    @api.model
    def _remove_orphaned_sequences(self, sequences):
        if not sequences:
            return
        still_referenced = (
            self.with_context(active_test=False)
            .search([("sequence_id", "in", sequences.ids)])
            .sequence_id
        )
        dbg.lifecycle.debug(
            "_remove_orphaned_sequences: %s (kept %s)",
            dbg.rec(sequences - still_referenced),
            dbg.rec(still_referenced),
        )
        (sequences - still_referenced).sudo().unlink()

    def _get_domain_sequence_scope(self):
        self.check_singleton()
        return Domain("company_id", "=", self.company_id.id) & Domain(
            "warehouse_id", "=", self.warehouse_id.id or False
        )

    def _get_clashing_picking_type(self):
        self.check_singleton()
        domain = self._get_domain_sequence_scope() & Domain(
            "sequence_code", "=", self.sequence_code
        )
        if self._origin.id:
            domain &= Domain("id", "!=", self._origin.id)
        return (
            self.env["stock.picking.type"]
            .with_context(active_test=False)
            .search(domain, limit=1)
        )

    def _get_unique_sequence_code(self):
        self.check_singleton()
        pattern = escape_psql(self.sequence_code)
        taken = set(
            self.env["stock.picking.type"]
            .with_context(active_test=False)
            .search(
                self._get_domain_sequence_scope()
                & Domain("sequence_code", "=like", f"{pattern}%")
            )
            .mapped("sequence_code")
        )
        for index in range(2, len(taken) + 3):
            candidate = f"{self.sequence_code}{index}"
            if candidate not in taken:
                return candidate
        return self.sequence_code
