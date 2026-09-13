import itertools

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command

from . import approval_trace as trace

_BASE_SEQUENCE = 10
ROUTES_BY_STEPS_CONTEXT = "approval_category_routes_by_steps"
_MAX_COMBINATIONS = 32
_ALWAYS_MEASURED = ("amount", "quantity", "priority")

_COMPLEMENT = {
    "gt": "lte",
    "gte": "lt",
    "lt": "gte",
    "lte": "gt",
    "eq": "neq",
    "neq": "eq",
}


class ApprovalCategoryConversion(models.Model):
    """A flat category's routing rewritten as steps that route every request the same.

    What "the same" means is the routing contract in tests/test_routing_outcomes.py:
    the state, who could approve and who is asked, after every decision. The flat
    path counts approvals across all of a request's rows, so each translation keeps
    that count in one pool step, whose required members are the required approvers. A configuration whose outcome steps cannot reproduce exactly is
    refused with its reason rather than approximated.
    """

    _inherit = "approval.category"

    steps_conversion_blockers = fields.Text(
        string="Why It Cannot Convert",
        compute="_compute_steps_conversion_blockers",
        help="What keeps this category's approvers and routing rules from being "
        "rewritten as steps that route every request the same. Empty when it can.",
    )

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)
        if (
            "step_ids" in fields
            and "step_ids" not in defaults
            and self.env.context.get(ROUTES_BY_STEPS_CONTEXT)
        ):
            defaults["step_ids"] = [
                Command.create(
                    {
                        "name": self.env._("Approvers"),
                        "sequence": _BASE_SEQUENCE,
                        "minimum": 1,
                        "counts_added_approvers": True,
                    }
                )
            ]
            trace.STEPS.event("category_born_with_steps", fields=len(fields))
        return defaults

    @api.depends_context("lang")
    @api.depends(
        "step_ids",
        "approve_sequentially",
        "group_approval",
        "notify_pool_members",
        "company_id",
        "rule_ids.active",
        "rule_ids.action_type",
        "rule_ids.condition_type",
        "rule_ids.condition_field",
        "rule_ids.operator",
        "rule_ids.company_id",
        "rule_ids.currency_id",
    )
    def _compute_steps_conversion_blockers(self) -> None:
        for category in self:
            blockers = category._get_steps_conversion_blockers()
            category.steps_conversion_blockers = "\n".join(
                f"- {reason}" for reason in blockers
            )

    def _get_steps_conversion_blockers(self) -> list[str]:
        self.check_singleton()
        blockers = []
        added, bands = self._get_routing_rules_by_action()
        if self.step_ids:
            blockers.append(self.env._("The category already routes by steps."))
        combinations = (len(bands) + 1) * 2 ** len(added)
        if (
            not self.env.context.get("approval_conversion_uncapped")
            and not self._routes_by_figures(added, bands)
            and combinations > _MAX_COMBINATIONS
        ):
            blockers.append(
                self.env._(
                    "Its routing rules combine into %(count)s cases, each a step of "
                    "its own; at most %(maximum)s are converted.",
                    count=combinations,
                    maximum=_MAX_COMBINATIONS,
                )
            )
        trace.STEPS.event(
            "conversion_blockers",
            category=self.id,
            blockers=len(blockers),
            adds=len(added),
            bands=len(bands),
            combinations=combinations,
            sequential=self.approve_sequentially,
            group=self.group_approval == "exclusive",
        )
        return blockers

    def _get_routing_rules(self):
        self.check_singleton()
        return self.rule_ids.filtered(
            lambda rule: (
                rule.active and rule.action_type in ("add_approver", "set_approvers")
            )
        )

    def _get_routing_rules_by_action(self) -> tuple:
        rules = self._get_routing_rules()
        added = rules.filtered(lambda rule: rule.action_type == "add_approver")
        bands = rules.filtered(lambda rule: rule.action_type == "set_approvers")
        if self.group_approval == "exclusive":
            bands = bands.browse()
        return added, bands

    def _routes_by_figures(self, added, bands) -> bool:
        rules = added | bands
        if any(
            rule.condition_type != "threshold"
            or rule.condition_field not in _ALWAYS_MEASURED
            or (rule.company_id and rule.company_id != self.company_id)
            for rule in rules
        ):
            routes, shape = False, "rule_not_on_an_always_measured_figure"
        elif added and bands:
            routes, shape = False, "adds_beside_bands"
        elif bands:
            routes, shape = self._are_rules_ranges(bands), "bands"
        elif len(added) > 1:
            routes, shape = self._are_rules_tiers(added), "adds"
        elif added:
            routes, shape = added.operator in _COMPLEMENT, "one_add"
        else:
            routes, shape = True, "no_rule"
        trace.STEPS.event(
            "figure_routing",
            category=self.id,
            routes=routes,
            shape=shape,
            rules=rules.ids,
        )
        return routes

    def _prepare_steps_from_flat_routing(self) -> list[dict]:
        self.check_singleton()
        listed = [
            (approver.user_id, approver.required, approver.sequence)
            for approver in self.approver_ids.sorted(lambda a: (a.sequence, a.id))
        ]
        added, bands = self._get_routing_rules_by_action()
        if self.group_approval == "exclusive":
            listed = []
        if not self._routes_by_figures(added, bands):
            translation = "rule_combinations"
            steps = self._prepare_rule_combination_steps(listed, added, bands)
        elif bands:
            translation = "ranged_bands"
            steps = self._prepare_ranged_band_steps(listed, bands)
        elif len(added) > 1:
            translation = "tiers"
            steps = self._prepare_tiered_steps(listed, added)
        elif added:
            translation = "one_add_rule"
            with_rule = listed + self._get_rule_approvers(added)
            steps = self._prepare_pooled_steps(
                listed,
                self.approval_minimum,
                {**self._complement_condition(added), **self._rule_links(unless=added)},
            ) + self._prepare_pooled_steps(
                with_rule,
                self.approval_minimum,
                {**self._rule_condition(added), **self._rule_links(when=added)},
            )
        else:
            translation = "approver_list"
            steps = self._prepare_pooled_steps(listed, self.approval_minimum, {})
        trace.STEPS.event(
            "flat_translation",
            category=self.id,
            translation=translation,
            listed=len(listed),
            steps=len(steps),
        )
        return steps

    def _prepare_rule_combination_steps(self, listed, added, bands) -> list[dict]:
        rules = self.env["approval.rule"]
        ordered_bands = bands.sorted(lambda rule: (rule.sequence, rule.id))
        cases = [(rules, listed, self.approval_minimum, ordered_bands)] + [
            (
                band,
                self._get_band_approvers(band),
                band.approval_minimum,
                ordered_bands[:index],
            )
            for index, band in enumerate(ordered_bands)
        ]
        steps = []
        for band, base, minimum, unless_bands in cases:
            for size in range(len(added) + 1):
                for matched in itertools.combinations(added, size):
                    matched = rules.union(*matched)
                    approvers = base + [
                        approver
                        for rule in matched
                        for approver in self._get_rule_approvers(rule)
                    ]
                    condition = {
                        "when_rule_ids": [Command.set((band | matched).ids)],
                        "unless_rule_ids": [
                            Command.set((unless_bands | (added - matched)).ids)
                        ],
                    }
                    steps += self._prepare_pooled_steps(approvers, minimum, condition)
        trace.STEPS.event(
            "rule_combinations",
            category=self.id,
            cases=len(cases) * 2 ** len(added),
            bands=ordered_bands.ids,
            adds=added.ids,
            steps=len(steps),
        )
        return steps

    @staticmethod
    def _are_rules_tiers(rules) -> bool:
        return (
            len(set(rules.mapped("condition_field"))) == 1
            and set(rules.mapped("operator")) == {"gte"}
            and len(rules.currency_id) <= 1
        )

    @staticmethod
    def _are_rules_ranges(rules) -> bool:
        return (
            len(set(rules.mapped("condition_field"))) == 1
            and set(rules.mapped("operator")) <= {"between", "gte", "lt"}
            and len(rules.currency_id) <= 1
        )

    @staticmethod
    def _rule_interval(rule) -> tuple[float, float]:
        infinity = float("inf")
        if rule.operator == "lt":
            return (-infinity, rule.threshold)
        if rule.operator == "between" and rule.threshold_max:
            return (rule.threshold, rule.threshold_max)
        return (rule.threshold, infinity)

    @staticmethod
    def _interval_condition(low: float, high: float) -> dict:
        infinity = float("inf")
        if low == -infinity:
            return {"operator": "lt", "threshold": high, "threshold_max": 0}
        if high == infinity:
            return {"operator": "gte", "threshold": low, "threshold_max": 0}
        return {"operator": "between", "threshold": low, "threshold_max": high}

    def _prepare_ranged_band_steps(self, listed, bands) -> list[dict]:
        """Each band's approvers over its own range; the category's own approvers over
        every range no band covers. Bands of one figure cannot overlap (the rule's
        constraint), so the ranges and the gaps between them never do either."""
        infinity = float("inf")
        first = bands[0]
        base = {
            "condition_field": first.condition_field,
            "currency_id": first.currency_id.id,
        }
        steps = []
        cursor = -infinity
        for band in bands.sorted(lambda rule: (self._rule_interval(rule), rule.id)):
            low, high = self._rule_interval(band)
            if cursor < low:
                steps += self._prepare_pooled_steps(
                    listed,
                    self.approval_minimum,
                    {
                        **base,
                        **self._interval_condition(cursor, low),
                        **self._rule_links(unless=bands),
                    },
                )
            steps += self._prepare_pooled_steps(
                self._get_band_approvers(band),
                band.approval_minimum,
                {
                    **base,
                    **self._interval_condition(low, high),
                    **self._rule_links(when=band),
                },
            )
            cursor = high
        if cursor < infinity:
            steps += self._prepare_pooled_steps(
                listed,
                self.approval_minimum,
                {
                    **base,
                    **self._interval_condition(cursor, infinity),
                    **self._rule_links(unless=bands),
                },
            )
        return steps

    def _prepare_tiered_steps(self, listed, added) -> list[dict]:
        """One pool per range of the figure, listing the approvers of every rule the
        range matches: the flat path counts their approvals toward the minimum."""
        tiers = added.sorted(lambda rule: (rule.threshold, rule.id))
        thresholds = sorted(set(tiers.mapped("threshold")))
        first = tiers[0]
        base = {
            "condition_field": first.condition_field,
            "currency_id": first.currency_id.id,
        }
        steps = self._prepare_pooled_steps(
            listed,
            self.approval_minimum,
            {
                **base,
                "operator": "lt",
                "threshold": thresholds[0],
                "threshold_max": 0,
                **self._rule_links(unless=tiers),
            },
        )
        for index, low in enumerate(thresholds):
            high = thresholds[index + 1] if index + 1 < len(thresholds) else 0
            matched = tiers.filtered(lambda rule, low=low: rule.threshold <= low)
            approvers = listed + [
                approver
                for rule in matched
                for approver in self._get_rule_approvers(rule)
            ]
            steps += self._prepare_pooled_steps(
                approvers,
                self.approval_minimum,
                {
                    **base,
                    "operator": "between",
                    "threshold": low,
                    "threshold_max": high,
                    **self._rule_links(when=matched, unless=tiers - matched),
                },
            )
        return steps

    def _get_conversion_group_vals(self) -> dict:
        if self.group_approval != "exclusive":
            return {}
        return {
            "group_id": self.approver_group_id.id,
            "asks_group_members": self.notify_pool_members,
        }

    def _get_conversion_pool_source(self) -> dict:
        """Step values naming approvers every request of the category adds to its pool
        beyond the listed ones (an approver path, typically on the request itself)."""
        return {}

    def _get_conversion_required_sources(self) -> list[tuple[str, dict]]:
        """(name, step values) for each required approver a request adds beyond the
        listed ones, named by a path rather than a user."""
        return []

    def _get_band_approvers(self, band) -> list[tuple]:
        sequence = self.env["approval.request"]._get_sequence_replacement()
        return [(user, band.approver_required, sequence) for user in band.approver_ids]

    @staticmethod
    def _get_rule_approvers(rule) -> list[tuple]:
        return [
            (user, rule.approver_required, rule.approver_sequence)
            for user in rule.approver_ids
        ]

    def _prepare_pooled_steps(self, approvers, minimum, condition) -> list[dict]:
        merged = {}
        for user, is_required, sequence in approvers:
            if user in merged:
                was_required, was_sequence = merged[user]
                merged[user] = (
                    was_required or is_required,
                    min(was_sequence, sequence),
                )
            else:
                merged[user] = (is_required, sequence)
        members = [(user, *merged[user]) for user in merged]
        steps = [
            self._prepare_conversion_step(name, [], 1, **condition, **source)
            for name, source in self._get_conversion_required_sources()
        ]
        pool_source = {
            **self._get_conversion_pool_source(),
            **self._get_conversion_group_vals(),
        }
        has_required = any(is_required for _user, is_required, _sequence in members)
        trace.STEPS.event(
            "pool_prepared",
            category=self.id,
            members=len(members),
            required=sum(1 for _user, is_required, _sequence in members if is_required),
            minimum=minimum,
            in_order=self.approve_sequentially,
            group=pool_source.get("group_id"),
            path=pool_source.get("subject_user_path"),
            conditioned=sorted(condition),
            required_sources=len(steps),
        )
        if self.approve_sequentially:
            steps.append(
                self._prepare_conversion_step(
                    self.env._("In order"),
                    members,
                    max(minimum, 1),
                    in_order=True,
                    counts_added_approvers=True,
                    **condition,
                    **self._get_conversion_pool_source(),
                )
            )
        elif minimum > 0 or has_required or pool_source.get("group_id"):
            steps.append(
                self._prepare_conversion_step(
                    self.env._("Approvers"),
                    members,
                    max(minimum, 1),
                    counts_added_approvers=True,
                    **condition,
                    **pool_source,
                )
            )
        return steps

    def _prepare_conversion_step(self, name, members, minimum, **vals) -> dict:
        return {
            "name": name,
            "sequence": _BASE_SEQUENCE,
            "minimum": minimum,
            "member_ids": [
                Command.create(
                    {
                        "user_id": user.id,
                        "sequence": sequence,
                        "required": is_required,
                    }
                )
                for user, is_required, sequence in members
            ],
            **vals,
        }

    @staticmethod
    def _rule_links(when=None, unless=None) -> dict:
        links = {}
        if when:
            links["when_rule_ids"] = [Command.set(when.ids)]
        if unless:
            links["unless_rule_ids"] = [Command.set(unless.ids)]
        return links

    @staticmethod
    def _rule_condition(rule) -> dict:
        return {
            "condition_field": rule.condition_field,
            "operator": rule.operator,
            "threshold": rule.threshold,
            "threshold_max": rule.threshold_max,
            "currency_id": rule.currency_id.id,
        }

    @staticmethod
    def _complement_condition(rule) -> dict:
        operator = "lt" if rule.operator == "between" else _COMPLEMENT[rule.operator]
        return {
            "condition_field": rule.condition_field,
            "operator": operator,
            "threshold": rule.threshold,
            "threshold_max": 0,
            "currency_id": rule.currency_id.id,
        }

    def _add_approver(self, user, required=False, sequence=10) -> None:
        """Add `user` as an approver of every request, wherever this category routes:
        its approver list, or the pool step of a category that routes by steps."""
        for category in self:
            if not category.step_ids:
                self.env["approval.category.approver"].create(
                    {
                        "category_id": category.id,
                        "user_id": user.id,
                        "required": required,
                        "sequence": sequence,
                    }
                )
                trace.STEPS.event(
                    "approver_added_to_list",
                    category=category.id,
                    user=user.id,
                    required=required,
                )
                continue
            pool = (
                category.step_ids.filtered("counts_added_approvers")
                or category.step_ids
            )[:1]
            trace.STEPS.event(
                "approver_added_to_step",
                category=category.id,
                user=user.id,
                required=required,
                step=pool.id,
                counts_added=pool.counts_added_approvers,
            )
            pool.member_ids = [
                Command.create(
                    {"user_id": user.id, "required": required, "sequence": sequence}
                )
            ]

    @api.model
    def _convert_every_category_to_steps(self) -> dict:
        """Convert every category still routed by its approver list that has no
        blocker; the others keep that list. Returns what happened to each."""
        categories = (
            self.sudo()
            .with_context(active_test=False, approval_conversion_uncapped=True)
            .search([("step_ids", "=", False)])
        )
        converted = self.browse()
        blocked = {}
        for category in categories:
            blockers = category._get_steps_conversion_blockers()
            if blockers:
                blocked[category] = blockers
                continue
            category.action_convert_routing_to_steps()
            converted |= category
        trace.STEPS.note(
            "converted_every_category",
            converted=converted.ids,
            blocked=[category.id for category in blocked],
        )
        return {"converted": converted, "blocked": blocked}

    @api.model
    def _unorder_group_categories(self):
        categories = (
            self.sudo()
            .with_context(active_test=False)
            .search(
                [
                    ("group_approval", "=", "exclusive"),
                    ("approve_sequentially", "=", True),
                ]
            )
        )
        trace.STEPS.note("group_categories_unordered", categories=categories.ids)
        categories.write({"approve_sequentially": False})
        return categories

    def _route_by_steps_on_first_use(self) -> None:
        listed = self.sudo().filtered(
            lambda category: (
                not category.step_ids and not category._has_steps_from_its_module()
            )
        )
        for category in listed.with_context(approval_conversion_uncapped=True):
            blockers = category._get_steps_conversion_blockers()
            trace.STEPS.event(
                "converted_on_first_use",
                category=category.id,
                blockers=len(blockers),
            )
            if not blockers:
                category.action_convert_routing_to_steps()

    def _adopt_list_routed_requests(self):
        domain = [("state", "=", "pending"), ("category_id.step_ids", "!=", False)]
        if self:
            domain.append(("category_id", "in", self.ids))
        pending = self.env["approval.request"].sudo().search(domain)
        adopted = pending.filtered(
            lambda request: request._adopt_list_routing_into_steps()
        )
        trace.STEPS.note(
            "list_routed_requests_adopted",
            categories=self.ids,
            pending=len(pending),
            adopted=adopted.ids,
        )
        return adopted

    def _has_steps_from_its_module(self) -> bool:
        return False

    @api.model
    def _get_list_routing_census(self) -> dict:
        categories = (
            self.sudo()
            .search([("step_ids", "=", False)])
            .filtered(lambda category: not category._has_steps_from_its_module())
        )
        undecided = (
            self.env["approval.request"]
            .sudo()
            .search([("state", "in", ("new", "pending"))])
        )
        requests = undecided.filtered(
            lambda request: (
                request.category_id in categories
                or (request.state == "pending" and not request.approver_ids.step_ids)
            )
        )
        trace.STEPS.note(
            "list_routing_census",
            categories=categories.ids,
            requests=len(requests),
            undecided=len(undecided),
        )
        return {"categories": categories, "requests": requests}

    @api.model
    def _route_rules_of_step_categories_by_steps(self):
        rules = self.env["approval.rule"].search(
            [
                ("action_type", "in", ("add_approver", "set_approvers")),
                ("category_id.step_ids", "!=", False),
            ]
        )
        added = rules.filtered(lambda rule: rule.action_type == "add_approver")
        for rule in added:
            self.env["approval.category.step"].create(
                {
                    "category_id": rule.category_id.id,
                    "name": rule.name,
                    "sequence": _BASE_SEQUENCE,
                    "minimum": 1,
                    "advisory": not rule.approver_required,
                    "when_rule_ids": [Command.set(rule.ids)],
                    "member_ids": [
                        Command.create(
                            {
                                "user_id": user.id,
                                "sequence": rule.approver_sequence,
                                "required": rule.approver_required,
                            }
                        )
                        for user in rule.approver_ids
                    ],
                }
            )
        trace.STEPS.note(
            "step_category_rules_routed",
            added=added.ids,
            archived_bands=(rules - added).ids,
        )
        added.write({"action_type": "condition"})
        (rules - added).write({"active": False})
        return {"added": added, "archived": rules - added}

    def action_convert_routing_to_steps(self) -> None:
        for category in self:
            blockers = category._get_steps_conversion_blockers()
            if blockers:
                trace.REFUSAL.event(
                    "steps_conversion_blocked",
                    category=category.id,
                    blockers=len(blockers),
                )
                raise UserError(
                    self.env._(
                        "%(category)s cannot be converted to steps without changing "
                        "how its requests are routed:\n%(reasons)s",
                        category=category.display_name,
                        reasons="\n".join(f"- {reason}" for reason in blockers),
                    )
                )
            steps = category._prepare_steps_from_flat_routing()
            rules = category._get_routing_rules()
            trace.STEPS.note(
                "converted_from_flat",
                category=category.id,
                steps=len(steps),
                routing_rules=rules.ids,
                sequential=category.approve_sequentially,
                group=category.group_approval == "exclusive",
            )
            category.write(
                {
                    "approve_sequentially": False,
                    "step_ids": [Command.create(vals) for vals in steps],
                }
            )
            read = category.step_ids.when_rule_ids | category.step_ids.unless_rule_ids
            trace.STEPS.event(
                "conversion_rules_settled",
                category=category.id,
                conditions=read.ids,
                archived=(rules - read).ids,
            )
            read.write({"action_type": "condition"})
            (rules - read).write({"active": False})
            category._adopt_list_routed_requests()
