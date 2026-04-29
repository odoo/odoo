"""KSW Sales / Collection Commission Rule + Tier.

Admin-managed rule catalog. Each rule defines:
  • a *kind* — sales / collection / combined (the latter is used for
    Salesman & Collector employees where the condition couples the
    two metrics, e.g. "sales ≥63% AND collection ≥63%"),
  • a *scope* — general / employee-specific / product-specific /
    employee+product, used by :meth:`_resolve_rule` to pick the
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
    the base amount that was earned within its range.  All individual
    tier contributions are summed to give the final commission.

    Example (target = 412 688, achievement = 84.8%)::

        Tier  0% – 50%  @ 1.0%  of TARGET
            band = 50 pts → 50/100 × 412 688 × 1.0%  = 2 063.44
        Tier 50% – 75%  @ 2.5%  of TARGET
            band = 25 pts → 25/100 × 412 688 × 2.5%  = 2 579.30
        Tier 75% – 100% @ 4.0%  of TARGET
            band = 9.8 pts → 9.8/100 × 412 688 × 4.0% = 1 617.73
        Total commission = 6 260.47

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
    ('product', 'Product-specific'),
    ('employee', 'Employee-specific'),
    ('employee_product', 'Employee + Product'),
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
    'product': 1,
    'employee': 2,
    'employee_product': 3,
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
    product_id = fields.Many2one('product.product', ondelete='cascade')

    condition_type = fields.Selection(
        CONDITION_TYPE, required=True, default='single_threshold',
    )
    sales_min_pct = fields.Float(
        string='Sales Min %', default=0.0,
        help='Minimum achievement percentage on sales for the '
             'condition to pass (used by single_threshold when kind=sales '
             'or kind=combined, and by dual_threshold).',
    )
    collection_min_pct = fields.Float(
        string='Collection Min %', default=0.0,
        help='Minimum achievement percentage on collection for the '
             'condition to pass (used by single_threshold when '
             'kind=collection, and by dual_threshold).',
    )
    condition_formula = fields.Char(
        help='Python expression assigning a boolean to ``result``. '
             'Variables in scope: ``sales_pct``, ``collection_pct``, '
             '``sales_target``, ``collection_target``, '
             '``sales_achieved``, ``collection_achieved``, '
             '``employee``, ``product``.\n'
             'Example: result = sales_pct >= 50 and collection_pct >= 60',
    )

    tier_ids = fields.One2many(
        'ksw.sales.commission.tier', 'rule_id', copy=True,
    )
    description = fields.Text()

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('scope', 'employee_id', 'product_id')
    def _check_scope_fields(self):
        for rec in self:
            if rec.scope in ('employee', 'employee_product') \
                    and not rec.employee_id:
                raise ValidationError(_(
                    "Rule '%(n)s' has scope %(s)s but no employee.",
                    n=rec.name, s=rec.scope,
                ))
            if rec.scope in ('product', 'employee_product') \
                    and not rec.product_id:
                raise ValidationError(_(
                    "Rule '%(n)s' has scope %(s)s but no product.",
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
                'employee': False, 'product': False, 'result': False,
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
    def _resolve_rule(self, employee, kind, product=None):
        """Return the single most-specific active rule for the given
        ``employee`` / ``kind`` / ``product``, or an empty recordset.

        Resolution order (most specific first):
            employee+product → employee → product → general
        Within the same scope, lowest ``priority`` wins.
        """
        if not employee or not kind:
            return self.browse()
        domain = [('active', '=', True), ('kind', '=', kind)]
        candidates = self.sudo().search(domain)
        eid = employee.id
        pid = product.id if product else False

        def matches(rule):
            if rule.scope == 'general':
                return True
            if rule.scope == 'employee':
                return rule.employee_id.id == eid
            if rule.scope == 'product':
                return pid and rule.product_id.id == pid
            if rule.scope == 'employee_product':
                return (
                    rule.employee_id.id == eid
                    and pid and rule.product_id.id == pid
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
                  employee=None, product=None, force_pass=False):
        """Evaluate this rule against the given metrics and return
        ``(amount, applied_tier, achievement_pct)``.

        Returns ``(0.0, browse(), pct)`` when the rule's condition does
        not pass. When ``force_pass=True`` (sales-manager override on
        the line) the condition gate is bypassed and the tier ladder
        is consulted unconditionally; if no tier matches the metric
        percentage, the lowest-sequence tier is used as the floor so
        the override still produces a payout.
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
            if self.kind == 'collection':
                passes = collection_pct >= (self.collection_min_pct or 0.0)
            else:  # sales / combined
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
                'product': product,
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
        # Each tier contributes commission only on the slice of achievement
        # that falls within its range.  All tier contributions are summed.
        #
        # Example (target=412 688, metric_pct=84.8%):
        #   Tier 0-50%  @ 1%  → 50/100 * 412 688 * 1%  = 2 063.44
        #   Tier 50-75% @ 2.5%→ 25/100 * 412 688 * 2.5% = 2 579.30
        #   Tier 75-85% @ 4%  →  9.8/100 * 412 688 * 4% = 1 617.73
        #   Total = 6 260.47
        # ------------------------------------------------------------------
        sorted_tiers = self.tier_ids.sorted(key=lambda t: (t.sequence, t.id))
        total_amount = 0.0
        applied = self.env['ksw.sales.commission.tier']  # highest reached

        for tier in sorted_tiers:
            lo = tier.from_pct or 0.0
            hi = tier.to_pct or 0.0
            # Did the salesperson reach this tier at all?
            if metric_pct <= lo:
                continue
            # How far into this tier (percentage points)?
            tier_hi = min(metric_pct, hi) if hi > 0.0 else metric_pct
            band_pct = tier_hi - lo
            if band_pct <= 0.0:
                continue
            # Base amount for this band.
            if tier.base == 'target':
                tier_base = band_pct / 100.0 * (target_amt or 0.0)
            else:  # 'achieved' — proportional slice of actual achieved
                tier_base = (
                    band_pct / metric_pct * (achieved_amt or 0.0)
                    if metric_pct else 0.0
                )
            total_amount += (tier.rate_pct or 0.0) / 100.0 * tier_base
            applied = tier  # track highest tier reached

        # Override floor: manager forced the condition but metric is below
        # every tier's from_pct so no band contributed anything.
        if total_amount == 0.0 and force_pass and sorted_tiers:
            floor_tier = sorted_tiers[0]
            floor_base = (
                (target_amt or 0.0) if floor_tier.base == 'target'
                else (achieved_amt or 0.0)
            )
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
        help='Upper bound (inclusive). Leave at 0 for no upper bound '
             '(matches any achievement percentage ≥ From %).',
    )
    rate_pct = fields.Float(
        string='Rate %', default=0.0,
        help='Commission ratio applied to the base amount (target or '
             'achieved). E.g. 1.5 means 1.5% of base.',
    )
    base = fields.Selection(
        [('target', 'Target Amount'), ('achieved', 'Achieved Amount')],
        required=True, default='target',
        help='Whether the rate is applied to the salesperson\'s '
             'monthly target or to their actual achieved amount.',
    )
    description = fields.Char()

    @api.constrains('from_pct', 'to_pct', 'rate_pct')
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







