import logging
from collections import defaultdict

from odoo import _, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)

DATE_MATCH_THRESHOLD_SECONDS = 86400

_debug = DebugLog(__name__)


class MixinOrderMerge(models.AbstractModel):
    _name = "mixin.order.merge"
    _description = "Order Merge System"

    def action_merge(self):
        orders_to_merge = self._filtered_merge_eligible_orders()
        excluded = self - orders_to_merge
        if excluded:
            _logger.info(
                "Merge selection excluded %s non-draft order(s): %s",
                len(excluded),
                ", ".join(excluded.mapped("name")),
            )
        self._merge_check_selection(orders_to_merge)

        groups = self._merge_group_orders(orders_to_merge)
        self._merge_check_groups(groups)

        merged_ids = []
        for orders in groups:
            if len(orders) > 1:
                merged_id = self._merge_order_group(orders)
                merged_ids.append(merged_id)

        _debug.pipeline(
            "orders_merged",
            selected=self,
            eligible=orders_to_merge,
            groups=len(groups),
            merged=len(merged_ids),
        )
        return self._prepare_merge_result_action(merged_ids)

    def _filtered_merge_eligible_orders(self):
        return self.filtered(lambda r: r.state == "draft")

    def _merge_check_selection(self, orders):
        if len(orders) < 2:
            _debug.logic("merge_refused", orders=orders, reason="fewer_than_two")
            raise UserError(
                _("Please select at least two orders to merge."),
            )

    def _merge_check_groups(self, groups):
        if not groups:
            _debug.logic("merge_refused", orders=self, reason="no_compatible_group")
            raise UserError(
                _(
                    "No compatible orders to merge. Orders must have the same:\n%s",
                    self._get_merge_group_description(),
                ),
            )

    def _get_merge_group_description(self):
        return _("- Partner\n- Currency")

    def _merge_group_orders(self, orders):
        groups = defaultdict(lambda: self.env[self._name])
        for order in orders:
            key = self._prepare_grouped_data(order)
            groups[key] += order
        return [g for g in groups.values() if len(g) > 1]

    def _prepare_grouped_data(self, order):
        return (
            order.partner_id.id,
            order.currency_id.id,
        )

    def _merge_get_target(self, orders):
        return min(orders, key=lambda r: r.date_order)

    def _merge_order_group(self, orders):
        target = self._merge_get_target(orders)
        sources = orders - target
        _debug.lifecycle("merge_group", target=target, sources=sources)

        line_index = self._prepare_merge_line_index(target)
        self._merge_lines(target, sources, line_index)
        self._merge_metadata(target, sources)
        self._merge_post_messages(target, sources)
        self._merge_finalize(target, sources)

        return target.id

    def _prepare_merge_line_index(self, target):
        index = defaultdict(list)
        for line in target.line_ids:
            if line.display_type:
                continue
            key = self._merge_get_line_key(line)
            index[key].append(line)
        return index

    def _merge_get_line_key(self, line):
        return (
            line.product_id.id,
            line.product_uom_id.id,
            frozenset(line.analytic_distribution.items())
            if line.analytic_distribution
            else frozenset(),
            line.discount,
            line.price_unit,
            frozenset(line.tax_ids.ids),
        )

    def _merge_lines(self, target, sources, line_index):
        sequence = self._merge_next_sequence(target)
        for source in sources:
            for source_line in source.line_ids.sorted("sequence"):
                if source_line.display_type:
                    source_line.write({"order_id": target.id, "sequence": sequence})
                    sequence += 1
                    continue

                key = self._merge_get_line_key(source_line)
                candidates = line_index.get(key, [])
                match = self._merge_collapse_matches(
                    self._merge_find_matching_line(source_line, candidates),
                    candidates,
                )

                if match:
                    _debug.logic(
                        "merge_line", source=source_line, into=match, by="matched_key"
                    )
                    match._merge_order_line(source_line)
                else:
                    source_line.write({"order_id": target.id, "sequence": sequence})
                    sequence += 1
                    line_index[key].append(source_line)

    def _merge_next_sequence(self, target):
        return max(target.line_ids.mapped("sequence"), default=0) + 1

    def _merge_find_matching_line(self, source_line, candidates):
        matches = self.env[self._get_line_model()]
        for candidate in candidates:
            if self._merge_lines_match_date(candidate, source_line):
                matches |= candidate
        return matches

    def _merge_collapse_matches(self, matches, candidates):
        if len(matches) <= 1:
            return matches[:1]
        # Each candidate here only matched the *source* line's date -- two
        # candidates can individually be within threshold of the source line
        # while being more than the threshold apart from each other. Only
        # fold candidates that also mutually match one another, or a source
        # line would bridge two otherwise-unrelated lines into one.
        mutual = matches.filtered(
            lambda line: all(
                self._merge_lines_match_date(line, other)
                for other in matches
                if other != line
            ),
        )
        if len(mutual) <= 1:
            return matches[:1]
        keeper, folded = mutual[0], mutual[1:]
        _debug.logic("merge_candidates_collapsed", keeper=keeper, folded=folded)
        for line in folded:
            keeper._merge_order_line(line)
        for line in folded:
            if line in candidates:
                candidates.remove(line)
        folded.unlink()
        return keeper

    def _merge_lines_match_date(self, line1, line2):
        field_name = line1._get_merge_date_field()
        if not field_name:
            return True
        date1 = line1[field_name]
        date2 = line2[field_name]
        if not date1 or not date2:
            return not date1 and not date2
        delta = abs(date1 - date2).total_seconds()
        return delta <= DATE_MATCH_THRESHOLD_SECONDS

    def _merge_metadata(self, target, sources):
        all_origins = [target.origin] + list(sources.mapped("origin"))
        target.origin = ", ".join(dict.fromkeys(filter(None, all_origins)))
        self._merge_update_metadata_refs(target, sources)

    def _merge_update_metadata_refs(self, target, sources):
        all_refs = [target.partner_ref] + list(sources.mapped("partner_ref"))
        target.partner_ref = ", ".join(dict.fromkeys(filter(None, all_refs)))

    def _merge_post_messages(self, target, sources):
        source_names = ", ".join(sources.mapped("name"))
        target.message_post(
            body=_("Merged with: %(sources)s", sources=source_names),
        )
        target_link = target._get_html_link()
        for source in sources:
            source.message_post(
                body=_("Merged into %s", target_link),
            )

    def _merge_finalize(self, target, sources):
        _debug.lifecycle("merge_sources_cancelled", target=target, sources=sources)
        sources.filtered(lambda r: r.state != "cancel").action_cancel()

    def _prepare_merge_result_action(self, merged_ids):
        action = {
            "type": "ir.actions.act_window",
            "res_model": self._name,
        }
        if len(merged_ids) == 1:
            action["res_id"] = merged_ids[0]
            action["view_mode"] = "form"
        else:
            action["name"] = self._get_merge_result_name()
            action["view_mode"] = "list,kanban,form"
            action["domain"] = [("id", "in", merged_ids)]
        return action

    def _get_merge_result_name(self):
        return _("Merged Orders")
