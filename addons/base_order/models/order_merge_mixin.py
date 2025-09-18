"""
Order Merge Mixin

Abstract mixin that consolidates the O(1) hash-based merge system shared
between sale.order and purchase.order (~90% identical).

Full workflow::

    action_merge → validate → group → merge_group →
        lines / metadata / messages → finalize → result action

Hooks for model-specific behaviour:
    ``_merge_get_eligible_orders`` — eligibility (sale: draft; purchase: draft+sent)
    ``_prepare_grouped_data`` — grouping key (sale: +shipping; purchase: +destination)
    ``_merge_metadata_refs`` — reference field (sale: client_order_ref; purchase: partner_ref)
    ``_merge_finalize`` — cleanup (purchase: alternative PO handling)
    ``_get_merge_result_name`` — action label ("Merged Quotations" / "Merged RFQs")
    ``_get_merge_group_description`` — error message criteria list
"""

from collections import defaultdict

from odoo import _, models
from odoo.exceptions import UserError

# Threshold for fuzzy date matching in merge operations (24 hours)
DATE_MATCH_THRESHOLD_SECONDS = 86400


class OrderMergeMixin(models.AbstractModel):
    """O(1) hash-based order merge system.

    Lines are matched by ``(product, UoM, analytic distribution, discount)``
    for constant-time lookup during merge.  Date matching (``date_planned``)
    is duck-typed — works with or without the stock module installed.

    Requires ``order.mixin`` for ``_get_order_type()``, ``date_order``,
    ``partner_id``, ``currency_id``, ``origin``, ``partner_ref``.
    Requires ``line_ids`` from the concrete model.
    """

    _name = "order.merge.mixin"
    _description = "Order Merge System"

    # ─── Public Action ─────────────────────────────────────────────

    def action_merge(self):
        """Merge selected orders into oldest one per compatible group.

        :returns: action to display merged order(s)
        :rtype: dict
        """
        orders_to_merge = self._merge_get_eligible_orders()
        self._merge_validate_selection(orders_to_merge)

        groups = self._merge_group_orders(orders_to_merge)
        self._merge_validate_groups(groups)

        merged_ids = []
        for orders in groups:
            if len(orders) > 1:
                merged_id = self._merge_order_group(orders)
                merged_ids.append(merged_id)

        return self._merge_build_result_action(merged_ids)

    # ─── Eligibility ───────────────────────────────────────────────

    def _merge_get_eligible_orders(self):
        """Return orders eligible for merging.

        Default: draft orders only.
        Purchase overrides to include ``sent`` state.
        """
        return self.filtered(lambda r: r.state == "draft")

    # ─── Validation ────────────────────────────────────────────────

    def _merge_validate_selection(self, orders):
        """Validate that at least 2 orders are selected for merge."""
        if len(orders) < 2:
            raise UserError(
                _("Please select at least two orders to merge."),
            )

    def _merge_validate_groups(self, groups):
        """Validate that at least one mergeable group exists."""
        if not groups:
            raise UserError(
                _(
                    "No compatible orders to merge. Orders must have the same:\n%s",
                    self._get_merge_group_description(),
                ),
            )

    def _get_merge_group_description(self):
        """Return human-readable grouping criteria for error messages.

        Sale: ``"- Customer\\n- Currency\\n- Delivery address"``.
        Purchase: ``"- Vendor\\n- Currency\\n- Destination\\n..."``.
        """
        return _("- Partner\n- Currency")

    # ─── Grouping ──────────────────────────────────────────────────

    def _merge_group_orders(self, orders):
        """Group orders by compatible attributes using ``_prepare_grouped_data``.

        :returns: list of recordsets, each containing mergeable orders
        """
        groups = defaultdict(lambda: self.env[self._name])
        for order in orders:
            key = self._prepare_grouped_data(order)
            groups[key] += order
        return [g for g in groups.values() if len(g) > 1]

    def _prepare_grouped_data(self, order):
        """Return grouping key for a single order.

        Orders with the same key can be merged.  Base provides
        ``(partner_id, currency_id)``.  Sale adds ``partner_shipping_id``,
        purchase adds ``dest_address_id``.

        :param order: single order record
        :returns: hashable tuple
        """
        return (
            order.partner_id.id,
            order.currency_id.id,
        )

    # ─── Target Selection ──────────────────────────────────────────

    def _merge_get_target(self, orders):
        """Return the target order (receives merged data).

        Default: oldest order by ``date_order``.
        """
        return min(orders, key=lambda r: r.date_order)

    # ─── Order Group Merge ─────────────────────────────────────────

    def _merge_order_group(self, orders):
        """Merge a group of compatible orders into one.

        Orchestrates: target selection → line merge → metadata →
        chatter messages → finalization.

        :param orders: recordset of compatible orders
        :returns: ID of the merged (target) order
        """
        target = self._merge_get_target(orders)
        sources = orders - target

        line_index = self._merge_build_line_index(target)
        self._merge_lines(target, sources, line_index)
        self._merge_metadata(target, sources)
        self._merge_post_messages(target, sources)
        self._merge_finalize(target, sources)

        return target.id

    # ─── Line Merging ──────────────────────────────────────────────

    def _merge_build_line_index(self, target):
        """Build hash index for O(1) line lookups during merge.

        :returns: ``{merge_key: [lines]}`` for constant-time lookup
        """
        index = defaultdict(list)
        for line in target.line_ids:
            if line.display_type:
                continue
            key = self._merge_get_line_key(line)
            index[key].append(line)
        return index

    def _merge_get_line_key(self, line):
        """Return the key used to match lines for merging.

        Identical in sale.order and purchase.order.

        :returns: ``(product_id, product_uom_id, analytic_distribution, discount)``
        """
        return (
            line.product_id.id,
            line.product_uom_id.id,
            frozenset(line.analytic_distribution.items())
            if line.analytic_distribution
            else frozenset(),
            line.discount,
        )

    def _merge_lines(self, target, sources, line_index):
        """Merge lines from source orders into target.

        Display lines (sections/notes) are moved directly.
        Product lines are matched via ``_merge_find_matching_line``
        and merged via ``_merge_order_line()`` on the line model.
        """
        for source_line in sources.line_ids:
            if source_line.display_type:
                source_line.order_id = target
                continue

            key = self._merge_get_line_key(source_line)
            match = self._merge_find_matching_line(
                source_line, line_index.get(key, []),
            )

            if match:
                match._merge_order_line(source_line)
            else:
                source_line.order_id = target
                line_index[key].append(source_line)

    def _merge_find_matching_line(self, source_line, candidates):
        """Find a matching target line for the source line.

        Matches by date within threshold (fuzzy matching).
        If multiple matches exist, consolidates them first.

        :returns: matching line record or empty recordset
        """
        line_model = f"{self._name}.line"
        matches = self.env[line_model]

        for candidate in candidates:
            if self._merge_lines_match_date(candidate, source_line):
                matches |= candidate

        # Multiple matches → consolidate into first
        if len(matches) > 1:
            matches[0].product_qty += sum(matches[1:].mapped("product_qty"))
            matches[1:].unlink()
            return matches[0]

        return matches[:1]

    def _merge_lines_match_date(self, line1, line2):
        """Check if two lines have compatible dates for merging.

        Duck-typed: returns ``True`` if ``date_planned`` doesn't exist
        (base sale/purchase without stock module).  When the field
        exists, matches within ``DATE_MATCH_THRESHOLD_SECONDS`` (24h).

        Purchase may override for stricter date handling.
        """
        if "date_planned" not in line1._fields:
            return True
        if not line1.date_planned or not line2.date_planned:
            return not line1.date_planned and not line2.date_planned
        delta = abs(line1.date_planned - line2.date_planned).total_seconds()
        return delta <= DATE_MATCH_THRESHOLD_SECONDS

    # ─── Metadata ──────────────────────────────────────────────────

    def _merge_metadata(self, target, sources):
        """Merge metadata fields from sources into target.

        Merges ``origin`` and delegates reference fields to
        ``_merge_metadata_refs()`` hook.
        """
        all_origins = [target.origin] + list(sources.mapped("origin"))
        target.origin = ", ".join(filter(None, all_origins))
        self._merge_metadata_refs(target, sources)

    def _merge_metadata_refs(self, target, sources):
        """Merge model-specific reference fields.

        Default: merges ``partner_ref`` (used by purchase).
        Sale overrides to merge ``client_order_ref`` instead.
        """
        all_refs = [target.partner_ref] + list(sources.mapped("partner_ref"))
        target.partner_ref = ", ".join(filter(None, all_refs))

    # ─── Messages ──────────────────────────────────────────────────

    def _merge_post_messages(self, target, sources):
        """Post chatter messages about the merge.

        Identical in sale.order and purchase.order.
        """
        source_names = ", ".join(sources.mapped("name"))
        target.message_post(
            body=_("Merged with: %(sources)s", sources=source_names),
        )
        target_link = target._get_html_link()
        for source in sources:
            source.message_post(
                body=_("Merged into %s", target_link),
            )

    # ─── Finalization ──────────────────────────────────────────────

    def _merge_finalize(self, target, sources):
        """Cancel source orders after merge.

        Purchase overrides to also handle alternative PO references.
        """
        sources.filtered(lambda r: r.state != "cancel").action_cancel()

    # ─── Result Action ─────────────────────────────────────────────

    def _merge_build_result_action(self, merged_ids):
        """Build action dict to display merged order(s).

        Uses ``self._name`` for ``res_model`` — resolves to the concrete
        model (``sale.order`` or ``purchase.order``) at runtime.
        """
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
        """Return action window name for merged results.

        Sale: ``'Merged Quotations'``.  Purchase: ``'Merged RFQs'``.
        """
        return _("Merged Orders")
