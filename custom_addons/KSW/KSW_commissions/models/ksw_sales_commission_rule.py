"""KSW Sales / Collection Commission Rule + Tier.

Admin-managed rule catalog. Each rule defines:
  • a *kind* — sales / collection / combined (the latter is used for
    Salesman & Collector employees where the condition couples the
    two metrics, e.g. "sales ≥63% AND collection ≥63%"),
   • a *scope* — general / employee-specific / client-specific /
     employee+client, used by :meth:`_resolve_rule` to pick the
     most-specific rule that applies to a given line,
  • a *condition* — single-threshold (one metric ≥ X%), dual-threshold
    (sales% AND collection% both ≥ their respective thresholds), or a
    free-form Python ``condition_formula`` (escape hatch),
  • a *tier ladder* — one ``ksw.sales.commission.tier`` per
    achievement-percent range, each carrying:
        - ``rate_pct``  — the commission ratio,
        - ``base``      — whether the ratio is applied to the *target*
                          amount or to the *actual achieved* amount.

    The tier ladder uses a **progressive (waterfall)** calculation.
    Each tier contributes commission only on the proportional slice of
    the base amount that was earned within its effective range.

    **Band convention:** ``from_pct`` labels the tier (e.g. 1, 51, 76)
    but the actual band starts at ``from_pct - 1`` so consecutive tiers
    are perfectly contiguous with no gap or overlap:

    =========  =====  =================  =================================
    Tier label  pts    Effective range    Meaning
    =========  =====  =================  =================================
    1 – 50      50    0 % → 50 %         First 50% of target
    51 – 75     25    50 % → 75 %        Next 25% of target
    76 – 100     *    75 % → actual%     Remaining up to achievement
    =========  =====  =================  =================================

    Example (collection_target = 412 688, collection_pct = 94.15%)::

        Tier  1–50   @ 1.0%  of COLLECTION_TARGET
            band = 50 pts → 50/100 × 412 688 × 1.0%  = 2 063.44
        Tier 51–75   @ 2.5%  of COLLECTION_TARGET
            band = 25 pts → 25/100 × 412 688 × 2.5%  = 2 579.30
        Tier 76–100  @ 4.0%  of COLLECTION_TARGET
            band = 19.15 pts → 19.15/100 × 412 688 × 4.0% = 3 161.66
        Total commission = 7 804.40

Example admin setup::

    Rule: "Sales — General"
        kind=sales · scope=general · condition=single_threshold
        sales_min_pct = 50.0
        Tiers:
            0% – 50%   →  1.0% of TARGET
            50% – 75%  →  2.5% of TARGET
            75% – 100% →  4.0% of TARGET

    Rule: "Sales — Ahmed (override)"
        kind=sales · scope=employee · employee_id=Ahmed
        priority=1 (wins over the general rule)
        ...own tiers...

The resolver returns the most-specific active rule matching ``kind``;
within the same scope, lower ``priority`` wins.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval


KIND_SELECTION = [
    ('sales', 'Sales'),
    ('collection', 'Collection'),
    ('combined', 'Combined (Sales & Collection)'),
]

SCOPE_SELECTION = [
    ('general', 'General (default)'),
    ('client', 'Client-specific'),
    ('employee', 'Employee-specific'),
    ('employee_client', 'Employee + Client'),
]

CONDITION_TYPE = [
    ('single_threshold', 'Single Threshold (one metric ≥ X%)'),
    ('dual_threshold',
     'Dual Threshold (sales% AND collection% both ≥ X%)'),
    ('formula', 'Custom Formula (advanced)'),
]

# Scope-specificity ordering used by _resolve_rule. Higher number =
# more specific = wins.
SCOPE_RANK = {
    'general': 0,
    'client': 1,
    'employee': 2,
    'employee_client': 3,
}


class KswSalesCommissionRule(models.Model):
    _name = 'ksw.sales.commission.rule'
    _description = 'KSW Sales / Collection Commission Rule'
    _order = 'kind, sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    priority = fields.Integer(
        default=10,
        help='Tie-breaker within the same scope. Lower priority wins. '
             'Use this to layer multiple employee-specific rules.',
    )

    kind = fields.Selection(KIND_SELECTION, required=True, default='sales')
    scope = fields.Selection(SCOPE_SELECTION, required=True, default='general')
    employee_id = fields.Many2one('hr.employee', ondelete='cascade')
    partner_ids = fields.Many2many(
        'res.partner', string='Clients',
        domain=[('customer_rank', '>', 0)],
        help='One or more clients this rule applies to. '
             'Leave empty when scope is General or Employee-specific.',
    )

    condition_type = fields.Selection(
        CONDITION_TYPE, required=True, default='single_threshold',
    )
    single_threshold_metric = fields.Selection(
        [('sales', 'Sales %'), ('collection', 'Collection %')],
        string='Threshold Metric',
        default='sales',
        help='Which metric the single threshold is checked against. '
             '"Sales %" compares sales_pct ≥ Sales Min %. '
             '"Collection %" compares collection_pct ≥ Collection Min %. '
             'Only used when Condition Type = Single Threshold.',
    )
    sales_min_pct = fields.Float(
        string='Sales Min %', default=0.0,
        help='Minimum achievement percentage on sales for the '
             'condition to pass (used by single_threshold when metric=sales '
             'or kind=combined, and by dual_threshold).',
    )
    collection_min_pct = fields.Float(
        string='Collection Min %', default=0.0,
        help='Minimum achievement percentage on collection for the '
             'condition to pass (used by single_threshold when '
             'metric=collection, and by dual_threshold).',
    )
    condition_formula = fields.Char(
        help='Python expression assigning a boolean to ``result``. '
             'Variables in scope: ``sales_pct``, ``collection_pct``, '
             '``sales_target``, ``collection_target``, '
             '``sales_achieved``, ``collection_achieved``, '
             '``employee``, ``client``.\n'
             'Example: result = sales_pct >= 50 and collection_pct >= 60',
    )

    tier_ids = fields.One2many(
        'ksw.sales.commission.tier', 'rule_id', copy=True,
    )
    description = fields.Text()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('scope', 'employee_id', 'partner_ids')
    def _check_scope_fields(self):
        for rec in self:
            if rec.scope in ('employee', 'employee_client') \
                    and not rec.employee_id:
                raise ValidationError(_(
                    "Rule '%(n)s' has scope %(s)s but no employee.",
                    n=rec.name, s=rec.scope,
                ))
            if rec.scope in ('client', 'employee_client') \
                    and not rec.partner_ids:
                raise ValidationError(_(
                    "Rule '%(n)s' has scope %(s)s but no clients selected.",
                    n=rec.name, s=rec.scope,
                ))

    @api.constrains('condition_type', 'condition_formula')
    def _check_formula(self):
        for rec in self:
            if rec.condition_type != 'formula':
                continue
            if not (rec.condition_formula or '').strip():
                raise ValidationError(_(
                    "Rule '%(n)s' uses 'Custom Formula' but no "
                    "formula was provided.", n=rec.name))
            ctx = {
                'sales_pct': 0.0, 'collection_pct': 0.0,
                'sales_target': 0.0, 'collection_target': 0.0,
                'sales_achieved': 0.0, 'collection_achieved': 0.0,
                'employee': False, 'client': False, 'result': False,
            }
            try:
                safe_eval(rec.condition_formula, ctx, mode='exec')
            except Exception as e:
                raise ValidationError(_(
                    "Formula on rule '%(n)s' could not be evaluated:\n"
                    "%(err)s", n=rec.name, err=str(e),
                ))

    @api.constrains('tier_ids')
    def _check_has_tiers(self):
        for rec in self:
            if not rec.tier_ids:
                raise ValidationError(_(
                    "Rule '%(n)s' must define at least one tier.",
                    n=rec.name,
                ))

    # ------------------------------------------------------------------
    # Resolver — used by ksw.sales.commission.line._compute_commission.
    # ------------------------------------------------------------------
    @api.model
    def _resolve_rule(self, employee, kind, partner=None):
        """Return the single most-specific active rule for the given
        ``employee`` / ``kind`` / ``partner`` (client), or an empty recordset.

        Resolution order (most specific first):
            employee+client → employee → client → general
        Within the same scope, lowest ``priority`` wins.
        """
        if not employee or not kind:
            return self.browse()
        domain = [('active', '=', True), ('kind', '=', kind)]
        candidates = self.sudo().search(domain)
        eid = employee.id
        pid = partner.id if partner else False

        def matches(rule):
            if rule.scope == 'general':
                return True
            if rule.scope == 'employee':
                return rule.employee_id.id == eid
            if rule.scope == 'client':
                return pid and pid in rule.partner_ids.ids
            if rule.scope == 'employee_client':
                return (
                    rule.employee_id.id == eid
                    and pid and pid in rule.partner_ids.ids
                )
            return False

        matched = candidates.filtered(matches)
        if not matched:
            return self.browse()
        # Sort by (-scope_rank, priority, sequence, id) so the most
        # specific rule, then lowest priority, comes first.
        sorted_rules = matched.sorted(
            key=lambda r: (
                -SCOPE_RANK.get(r.scope, 0),
                r.priority or 0,
                r.sequence or 0,
                r.id,
            )
        )
        return sorted_rules[:1]

    # ------------------------------------------------------------------
    # Per-rule evaluation — returns the commission amount for one line.
    # ------------------------------------------------------------------
    def _evaluate(self, sales_target, collection_target,
                  sales_achieved, collection_achieved,
                  employee=None, partner=None, force_pass=False):
        """Evaluate this rule against the given metrics and return
        ``(amount, applied_tier, achievement_pct)``.

        Returns ``(0.0, browse(), pct)`` when the rule's condition does
        not pass. When ``force_pass=True`` (sales-manager override on
        the line) the condition gate is bypassed and the tier ladder
        is consulted unconditionally.

        **Per-tier metric resolution** — when a tier has an explicit
        ``base`` of ``collection_target`` / ``collection_achieved`` the
        waterfall uses ``collection_pct`` (not the rule-level metric) to
        determine how far into that tier the salesperson reached.
        Likewise ``sales_target`` / ``sales_achieved`` forces
        ``sales_pct``.  The auto bases ``target`` / ``achieved`` keep
        using the rule-level ``metric_pct`` (derived from ``kind``).
        This means a Combined rule's tier ladder can independently measure
        each side:

        Example — Combined rule, target_sales=400 000, target_collection=412 000,
        sales_pct=63%, collection_pct=94%::

            Tier 1–50%  @ 1.0% of SALES_TARGET     (metric=sales_pct=63%)
                band=49 pts → 49/100 × 400 000 × 1.0% = 1 960
            Tier 1–50%  @ 1.0% of COLLECTION_TARGET (metric=collection_pct=94%)
                ... defined as a separate tier with base=collection_target
        """
        self.ensure_one()
        sales_pct = (
            (sales_achieved / sales_target) * 100.0
            if sales_target else 0.0
        )
        collection_pct = (
            (collection_achieved / collection_target) * 100.0
            if collection_target else 0.0
        )

        # The "achievement percentage" used to pick a tier depends on
        # the rule's kind:
        if self.kind == 'sales':
            metric_pct = sales_pct
            target_amt = sales_target
            achieved_amt = sales_achieved
        elif self.kind == 'collection':
            metric_pct = collection_pct
            target_amt = collection_target
            achieved_amt = collection_achieved
        else:  # combined
            # The slowest-moving metric drives the combined tier.
            metric_pct = min(sales_pct, collection_pct) \
                if (sales_target and collection_target) \
                else (sales_pct or collection_pct)
            target_amt = (sales_target or 0.0) + (collection_target or 0.0)
            achieved_amt = (
                (sales_achieved or 0.0) + (collection_achieved or 0.0))

        # ------------------------------------------------------------------
        # Condition gate
        # ------------------------------------------------------------------
        passes = False
        if self.condition_type == 'single_threshold':
            # Use the explicit metric selector; fall back to kind-based default
            # for backward compatibility with rules saved before the field existed.
            st_metric = self.single_threshold_metric or (
                'collection' if self.kind == 'collection' else 'sales'
            )
            if st_metric == 'collection':
                passes = collection_pct >= (self.collection_min_pct or 0.0)
            else:  # 'sales'
                passes = sales_pct >= (self.sales_min_pct or 0.0)
        elif self.condition_type == 'dual_threshold':
            passes = (
                sales_pct >= (self.sales_min_pct or 0.0)
                and collection_pct >= (self.collection_min_pct or 0.0)
            )
        elif self.condition_type == 'formula':
            ctx = {
                'sales_pct': sales_pct,
                'collection_pct': collection_pct,
                'sales_target': sales_target,
                'collection_target': collection_target,
                'sales_achieved': sales_achieved,
                'collection_achieved': collection_achieved,
                'employee': employee,
                'client': partner,
                'result': False,
            }
            try:
                safe_eval(self.condition_formula or '', ctx, mode='exec')
                passes = bool(ctx.get('result'))
            except Exception:
                passes = False

        if not passes:
            if not force_pass:
                return (0.0, self.env['ksw.sales.commission.tier'], metric_pct)
            # Manager override — fall through to tier matching.

        # ------------------------------------------------------------------
        # Progressive (waterfall) tier computation.
        #
        # Two base families, two walking strategies:
        #
        # TARGET bases (target / sales_target / collection_target):
        #   Walk tier ladder using the real achievement% (sales_pct,
        #   collection_pct, or metric_pct).  A tier is only reached if
        #   the employee's achievement% exceeds its lower bound.
        #   Slice formula: band_pct / 100 × target_amount
        #
        #   Example (target=412 688, collection_pct=94.15%):
        #     Tier  1–50%  @ 1%  → 50/100 × 412 688 × 1%  = 2 063.44
        #     Tier 51–75%  @ 2.5%→ 25/100 × 412 688 × 2.5% = 2 579.30
        #     Tier 76–100% @ 4%  → 19.15/100 × 412 688 × 4% = 3 161.68
        #     Total = 7 804.42
        #
        # ACHIEVED bases (achieved / sales_achieved / collection_achieved):
        #   Walk ALL tiers unconditionally (t_metric = 100) — every tier
        #   band represents a proportional slice of the actual earned amount.
        #   Slice formula: band_pct / 100 × achieved_amount
        #
        #   Example (sales_achieved=91 272, tiers 0-70% @ 1%, 70-∞ @ 2%):
        #     Tier  1–70%  @ 1%  → 70/100 × 91 272 × 1%  = 638.90
        #     Tier 71–∞    @ 2%  → 30/100 × 91 272 × 2%  = 547.63
        #     Total = 1 186.53
        #
        # Reduced rate: always checked against the REAL achievement% (not
        # the tier-walking metric), so that a 0.7 multiplier still fires
        # when sales_pct=53% is inside the reduced zone even on an achieved
        # base tier where t_metric=100.
        # ------------------------------------------------------------------
        sorted_tiers = self.tier_ids.sorted(key=lambda t: (t.sequence, t.id))
        total_amount = 0.0
        applied = self.env['ksw.sales.commission.tier']  # highest reached

        def _resolve_raw(base_key):
            """Return the full raw monetary amount for a given base key."""
            if base_key == 'sales_target':
                return sales_target or 0.0
            if base_key == 'sales_achieved':
                return sales_achieved or 0.0
            if base_key == 'collection_target':
                return collection_target or 0.0
            if base_key == 'collection_achieved':
                return collection_achieved or 0.0
            if base_key == 'achieved':
                return achieved_amt or 0.0
            return target_amt or 0.0  # default: 'target'

        def _resolve_tier_metric(base_key):
            """Return the virtual achievement % used to *walk* the tier ladder.

            For *target* bases the ladder is walked proportionally to the
            real achievement% (how far along the target the employee reached).
            For *achieved* bases the entire achieved amount is always
            available to split across tiers, so we use 100 as the metric
            (all tiers are reachable; each covers a fixed % slice of the
            earned amount).
            """
            if base_key in ('achieved', 'sales_achieved', 'collection_achieved'):
                return 100.0  # walk all tiers; slice achieved amount directly
            if base_key == 'collection_target':
                return collection_pct
            if base_key == 'sales_target':
                return sales_pct
            return metric_pct  # 'target' (auto)

        def _resolve_achievement_metric(base_key):
            """Return the REAL achievement % for conditional checks such as
            the reduced-rate zone.  Always based on actual performance,
            regardless of whether the tier uses target or achieved as base.
            """
            if base_key in ('collection_target', 'collection_achieved'):
                return collection_pct
            if base_key in ('sales_target', 'sales_achieved'):
                return sales_pct
            return metric_pct

        for tier in sorted_tiers:
            hi = tier.to_pct or 0.0
            t_metric = _resolve_tier_metric(tier.base)
            # Band convention: "from_pct" labels the tier (e.g. 1, 51, 76)
            # but the actual band starts at (from_pct - 1) so that
            # consecutive tiers are contiguous with zero gap:
            #   1–50  →  0%–50%   (50 pts)
            #  51–75  → 50%–75%   (25 pts)
            #  76–100 → 75%–max   (max-75 pts)
            lo = max((tier.from_pct or 0.0) - 1.0, 0.0)
            # Did the salesperson reach this tier at all?
            if t_metric <= lo:
                continue
            # How far into this tier (percentage points)?
            tier_hi = min(t_metric, hi) if hi > 0.0 else t_metric
            band_pct = tier_hi - lo
            if band_pct <= 0.0:
                continue
            # Slice formula is identical for both target and achieved bases
            # once t_metric is normalised:
            #   target  → band_pct / 100 × target_amount  (t_metric = pct)
            #   achieved → band_pct / 100 × achieved_amount (t_metric = 100)
            tier_base = band_pct / 100.0 * _resolve_raw(tier.base)
            effective_rate = tier.rate_pct or 0.0
            # Apply optional intra-tier reduced rate when the real
            # achievement % falls in the "reduced zone" (≤ reduced_rate_max_pct).
            # We use the real achievement%, NOT t_metric (which is 100 for
            # achieved bases and would otherwise bypass this check).
            rr_max = tier.reduced_rate_max_pct or 0.0
            rr_mul = tier.reduced_rate_multiplier
            if rr_mul is False:
                rr_mul = 1.0
            achieve_pct = _resolve_achievement_metric(tier.base)
            if rr_max > 0.0 and achieve_pct <= rr_max:
                effective_rate = effective_rate * rr_mul
            total_amount += effective_rate / 100.0 * tier_base
            applied = tier  # track highest tier reached

        # Override floor: manager forced the condition but metric is below
        # every tier's effective lo so no band contributed anything.
        if total_amount == 0.0 and force_pass and sorted_tiers:
            floor_tier = sorted_tiers[0]
            floor_metric = _resolve_tier_metric(floor_tier.base)
            floor_lo = max((floor_tier.from_pct or 0.0) - 1.0, 0.0)
            floor_hi = floor_tier.to_pct or 0.0
            if floor_metric > floor_lo:
                tier_hi = min(floor_metric, floor_hi) if floor_hi > 0.0 else floor_metric
                band_pct = tier_hi - floor_lo
                floor_base = band_pct / 100.0 * _resolve_raw(floor_tier.base)
                total_amount = (floor_tier.rate_pct or 0.0) / 100.0 * floor_base
            else:
                floor_base = _resolve_raw(floor_tier.base)
                total_amount = (floor_tier.rate_pct or 0.0) / 100.0 * floor_base
            applied = floor_tier

        if not applied:
            return (0.0, applied, metric_pct)

        return (total_amount, applied, metric_pct)


class KswSalesCommissionTier(models.Model):
    _name = 'ksw.sales.commission.tier'
    _description = 'KSW Sales / Collection Commission Tier'
    _order = 'rule_id, sequence, from_pct'

    rule_id = fields.Many2one(
        'ksw.sales.commission.rule', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    from_pct = fields.Float(string='From %', default=0.0)
    to_pct = fields.Float(
        string='To %', default=0.0,
        help='Upper bound (inclusive). Leave at 0 for an unbounded top tier '
             '(captures ALL achievement above its lower bound, including '
             'achievements that exceed 100%% of target on target-based tiers). '
             'Use this for the highest sales tier so over-achievers are rewarded.',
    )
    rate_pct = fields.Float(
        string='Rate %', default=0.0,
        help='Commission ratio applied to the base amount (target or '
             'achieved). E.g. 1.5 means 1.5% of base.',
    )
    base = fields.Selection(
        [
            ('target',             'Target Amount (auto)'),
            ('achieved',           'Achieved Amount (auto)'),
            ('sales_target',       'Sales Target'),
            ('sales_achieved',     'Sales Achieved'),
            ('collection_target',  'Collection Target'),
            ('collection_achieved', 'Collection Achieved'),
        ],
        required=True, default='target',
        help=(
            'Controls which monetary amount the Rate %% is applied to AND '
            'how the tier ladder is walked.\n\n'
            'TARGET bases (Target / Sales Target / Collection Target):\n'
            '  Walk the ladder using the real achievement %%. A tier is only '
            'reached once %%achievement exceeds its lower bound.\n'
            '  Slice = band_pts / 100 × target.\n'
            '  → Use when commission is proportional to the target amount.\n\n'
            'ACHIEVED bases (Achieved / Sales Achieved / Collection Achieved):\n'
            '  Walk ALL tiers unconditionally — the earned amount is split '
            'proportionally across every tier band.\n'
            '  Tier 1 (0-70%%) always gets 70%% of achieved; Tier 2 (70-∞) '
            'gets the rest — regardless of %%achievement.\n'
            '  → Use when commission is proportional to the actual earned amount.\n\n'
            '• "(auto)" variants use the rule\'s own metric.\n'
            '• Explicit "Sales …" / "Collection …" are useful on Combined rules.'
        ),
    )
    reduced_rate_max_pct = fields.Float(
        string='Reduced Rate Up To %', default=0.0,
        help='Optional: when the achievement % is at or below this value '
             'the rate is multiplied by the Reduced Rate Multiplier. '
             'Leave at 0 to always use the full Rate %. '
             'Example: set to 69 with multiplier 0.7 so that employees '
             'achieving 50–69% earn only 70 %% of the normal rate.',
    )
    reduced_rate_multiplier = fields.Float(
        string='Reduced Rate Multiplier', default=1.0,
        help='Factor applied to Rate % when achievement is in the reduced '
             'zone (≤ Reduced Rate Up To %). E.g. 0.7 = 70 %% of the normal '
             'rate. Has no effect when Reduced Rate Up To % is 0.',
    )
    description = fields.Char()

    @api.constrains('from_pct', 'to_pct', 'rate_pct', 'reduced_rate_max_pct', 'reduced_rate_multiplier')
    def _check_bounds(self):
        for rec in self:
            if (rec.from_pct or 0.0) < 0 or (rec.to_pct or 0.0) < 0 \
                    or (rec.rate_pct or 0.0) < 0:
                raise ValidationError(_(
                    "Tier percentages and rates must be non-negative."))
            if rec.to_pct and rec.to_pct < rec.from_pct:
                raise ValidationError(_(
                    "Tier 'To %%' (%(to)s) must be greater than or "
                    "equal to 'From %%' (%(fr)s).",
                    to=rec.to_pct, fr=rec.from_pct,
                ))
            if (rec.reduced_rate_max_pct or 0.0) < 0:
                raise ValidationError(_(
                    "Reduced Rate Up To %% must be non-negative."))
            mul = rec.reduced_rate_multiplier
            if mul is not False and (mul or 0.0) < 0:
                raise ValidationError(_(
                    "Reduced Rate Multiplier must be non-negative."))







