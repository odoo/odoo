"""KSW Sales / Collection Commission Sheet — monthly accountant entry.

Single source of truth for sales-commission and collection-commission
amounts. Each month the accountant opens (or auto-creates) one sheet
and adds one row per salesperson with the achieved sales /
collection amounts pulled from their external accountant module.

On confirm, the per-line amounts are pushed to the matching
``ksw.commission.sheet`` (mirror of the driver-commission +
location-allowance flow).
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .ksw_salesperson_profile import ROLE_SELECTION


class KswSalesCommissionSheet(models.Model):
    _name = 'ksw.sales.commission.sheet'
    _description = 'KSW Sales / Collection Commission Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period desc, id desc'

    name = fields.Char(readonly=True, default='New', copy=False)
    period = fields.Date(
        required=True, tracking=True,
        default=lambda s: fields.Date.context_today(s).replace(day=1),
        help='First day of the month covered by this sheet.',
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed')],
        default='draft', required=True, copy=False, tracking=True,
    )
    is_locked = fields.Boolean(readonly=True, copy=False)
    line_ids = fields.One2many(
        'ksw.sales.commission.line', 'sheet_id', copy=True,
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id,
        required=True,
    )
    total_commission = fields.Monetary(
        compute='_compute_total', store=True,
    )
    total_sales_commission = fields.Monetary(
        compute='_compute_total', store=True,
    )
    total_collection_commission = fields.Monetary(
        compute='_compute_total', store=True,
    )
    total_combined_commission = fields.Monetary(
        compute='_compute_total', store=True,
    )

    _unique_period = models.Constraint(
        'UNIQUE(period)',
        'Only one sales/collection commission sheet per month.',
    )

    @api.depends('line_ids.total_commission',
                 'line_ids.sales_commission_amount',
                 'line_ids.collection_commission_amount',
                 'line_ids.combined_commission_amount')
    def _compute_total(self):
        for rec in self:
            rec.total_sales_commission = sum(
                rec.line_ids.mapped('sales_commission_amount'))
            rec.total_collection_commission = sum(
                rec.line_ids.mapped('collection_commission_amount'))
            rec.total_combined_commission = sum(
                rec.line_ids.mapped('combined_commission_amount'))
            rec.total_commission = sum(
                rec.line_ids.mapped('total_commission'))

    @api.model_create_multi
    def create(self, vals_list):
        Seq = self.env['ir.sequence']
        for v in vals_list:
            if not v.get('name') or v['name'] == 'New':
                v['name'] = (
                    Seq.next_by_code('ksw.sales.commission.sheet')
                    or 'New'
                )
            if v.get('period'):
                d = fields.Date.to_date(v['period'])
                v['period'] = d.replace(day=1)
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------
    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_(
                    "Only draft sheets can be confirmed."))
            rec.write({'state': 'confirmed', 'is_locked': True})
            rec._sync_to_commission_sheets()
            rec.message_post(
                body=_(
                    'Sales/collection commission sheet confirmed. '
                    'Total: %(t).2f', t=rec.total_commission,
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_reset_to_draft(self):
        for rec in self:
            rec.write({'state': 'draft', 'is_locked': False})
            rec._sync_to_commission_sheets()

    def action_open_import_wizard(self):
        """Open the Excel import wizard pre-filled with this sheet."""
        self.ensure_one()
        return {
            'name': _("Import Sales & Collection from Excel"),
            'type': 'ir.actions.act_window',
            'res_model': 'ksw.sales.commission.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sheet_id': self.id,
            },
        }

    # ------------------------------------------------------------------
    # Commission-sheet sync
    # ------------------------------------------------------------------
    def _sync_to_commission_sheets(self):
        """Recompute sales / collection / combined amounts on the
        matching commission sheets. Auto-creates a draft commission
        sheet for any newly added salesperson lacking one this period.
        """
        Sheet = self.env['ksw.commission.sheet']
        for rec in self:
            for line in rec.line_ids:
                if not line.employee_id:
                    continue
                sheet = Sheet.sudo().search([
                    ('employee_id', '=', line.employee_id.id),
                    ('period', '=', rec.period),
                ], limit=1)
                if not sheet:
                    sheet = Sheet.sudo().create({
                        'employee_id': line.employee_id.id,
                        'period': rec.period,
                    })
                sheet.sudo()._compute_sales_commission()
                sheet.sudo().flush_recordset([
                    'sales_commission_amount',
                    'collection_commission_amount',
                    'combined_commission_amount',
                ])


class KswSalesCommissionLine(models.Model):
    _name = 'ksw.sales.commission.line'
    _description = 'KSW Sales / Collection Commission Line'
    _order = 'sheet_id, sequence, id'

    sheet_id = fields.Many2one(
        'ksw.sales.commission.sheet',
        required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    employee_id = fields.Many2one(
        'hr.employee', required=True, ondelete='restrict',
        domain="[('x_is_attendance_sheet', '=', True)]",
    )
    department_id = fields.Many2one(
        related='employee_id.department_id', store=True, readonly=True,
    )
    period = fields.Date(
        related='sheet_id.period', store=True, readonly=True,
    )
    role = fields.Selection(
        ROLE_SELECTION, compute='_compute_role_and_targets',
        store=True, readonly=False,
        help='Defaults to the salesperson profile role for the year. '
             'May be overridden per line if needed.',
    )
    partner_id = fields.Many2one(
        'res.partner', string='Client', ondelete='restrict',
        domain=[('customer_rank', '>', 0)],
        help='Optional. When set, client-specific commission rules '
             'will be matched first by the resolver.',
    )
    split_id = fields.Many2one(
        'ksw.salesperson.profile.client.split',
        string='Client Split', ondelete='set null',
        help='When set, this line covers only the clients defined in the '
             'split rule. The general line (split blank) receives the '
             'remaining totals.',
    )
    split_label = fields.Char(
        related='split_id.label', store=True, readonly=True,
        string='Split',
    )

    # Targets — computed from the salesperson profile, but editable so
    # that the accountant can override the auto-split for one month.
    target_sales = fields.Monetary(
        compute='_compute_role_and_targets', store=True, readonly=False,
    )
    target_collection = fields.Monetary(
        compute='_compute_role_and_targets', store=True, readonly=False,
    )

    achieved_sales = fields.Monetary(default=0.0)
    achieved_collection = fields.Monetary(default=0.0)

    sales_pct = fields.Float(
        string='Sales %', compute='_compute_commission', store=True,
    )
    collection_pct = fields.Float(
        string='Collection %', compute='_compute_commission', store=True,
    )

    sales_rule_id = fields.Many2one(
        'ksw.sales.commission.rule', readonly=True,
        compute='_compute_commission', store=True,
    )
    collection_rule_id = fields.Many2one(
        'ksw.sales.commission.rule', readonly=True,
        compute='_compute_commission', store=True,
    )
    combined_rule_id = fields.Many2one(
        'ksw.sales.commission.rule', readonly=True,
        compute='_compute_commission', store=True,
    )

    sales_commission_amount = fields.Monetary(
        compute='_compute_commission', store=True,
    )
    collection_commission_amount = fields.Monetary(
        compute='_compute_commission', store=True,
    )
    combined_commission_amount = fields.Monetary(
        compute='_compute_commission', store=True,
    )
    total_commission = fields.Monetary(
        compute='_compute_commission', store=True,
    )

    notes = fields.Char()

    # ------------------------------------------------------------------
    # Sales-manager override
    # ------------------------------------------------------------------
    # When True, the rule's condition gate is bypassed in
    # ``_compute_commission`` and the tier ladder is consulted
    # unconditionally. Used when the sales manager grants an
    # exception to a salesperson who didn't meet the threshold.
    x_condition_override = fields.Boolean(
        string='Condition Overridden',
        copy=False, readonly=True,
        help='Set by a Sales Manager via the "Override Condition" '
             'button. While True, the commission is paid even when '
             'the rule\'s condition (threshold / formula) does not '
             'pass — using the tier ladder applied to the actual '
             'achievement percentage (or the lowest tier as a floor).',
    )
    x_override_by = fields.Many2one(
        'res.users', string='Overridden By',
        readonly=True, copy=False,
    )
    x_override_date = fields.Datetime(
        string='Override Date', readonly=True, copy=False,
    )
    x_override_reason = fields.Char(
        string='Override Reason', readonly=True, copy=False,
    )

    currency_id = fields.Many2one(
        related='sheet_id.currency_id', store=True, readonly=True,
    )

    # Uniqueness enforced in Python (see _check_unique_line) because
    # a DB UNIQUE on (sheet_id, employee_id, split_id) does not prevent
    # duplicate NULL split_id rows in PostgreSQL.

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.constrains('sheet_id', 'employee_id', 'split_id')
    def _check_unique_line(self):
        for rec in self:
            domain = [
                ('sheet_id', '=', rec.sheet_id.id),
                ('employee_id', '=', rec.employee_id.id),
                ('id', '!=', rec.id),
                ('split_id', '=', rec.split_id.id if rec.split_id else False),
            ]
            if self.search_count(domain):
                if rec.split_id:
                    raise ValidationError(_(
                        "A split line '%(s)s' already exists for %(e)s on this sheet.",
                        s=rec.split_id.label, e=rec.employee_id.name,
                    ))
                else:
                    raise ValidationError(_(
                        "A general commission line for %(e)s already exists "
                        "on this sheet.", e=rec.employee_id.name,
                    ))
    @api.depends('employee_id', 'sheet_id.period', 'split_id')
    def _compute_role_and_targets(self):
        Profile = self.env['ksw.salesperson.profile']
        for rec in self:
            if not rec.employee_id or not rec.sheet_id.period:
                rec.role = rec.role or 'sales'
                rec.target_sales = 0.0
                rec.target_collection = 0.0
                continue
            if rec.split_id:
                # Split lines take their role from the split definition.
                # Targets default to 0 (set manually or via import).
                rec.role = rec.split_id.role
                rec.target_sales = 0.0
                rec.target_collection = 0.0
            else:
                sales_t, coll_t, profile = Profile._get_targets(
                    rec.employee_id, rec.sheet_id.period)
                rec.role = profile.role if profile else (rec.role or 'sales')
                rec.target_sales = sales_t
                rec.target_collection = coll_t

    def _get_profile_rule(self, rec, kind):
        """Return the commission rule for this line, using the priority:

        For **split lines** (``split_id`` is set):
            The rule is always ``split_id.rule_id`` if its kind matches.
            No profile/scope resolution is done for split lines.

        For **general lines** (``split_id`` blank):
        1. Explicit rule set on the employee's salesperson profile
           (``sales_rule_id`` / ``collection_rule_id`` / ``combined_rule_id``).
        2. Auto-resolved rule via ``_resolve_rule`` scope matching
           (most-specific active rule for the employee/kind/client).
        """
        Rule = self.env['ksw.sales.commission.rule']
        # --- Split line: rule comes directly from the split definition ---
        if rec.split_id:
            split_rule = rec.split_id.rule_id
            if split_rule and split_rule.kind == kind:
                return split_rule
            return Rule  # kind mismatch → no commission for that kind
        # --- General line: profile explicit rule → scope resolver ---------
        if rec.employee_id and rec.sheet_id.period:
            Profile = self.env['ksw.salesperson.profile']
            profile = Profile.sudo().search([
                ('employee_id', '=', rec.employee_id.id),
                ('year', '=', fields.Date.to_date(rec.sheet_id.period).year),
                ('active', '=', True),
            ], limit=1)
            if profile:
                explicit = {
                    'sales': profile.sales_rule_id,
                    'collection': profile.collection_rule_id,
                    'combined': profile.combined_rule_id,
                }.get(kind)
                if explicit:
                    return explicit
        # Fall back to generic scope-based resolution.
        return Rule._resolve_rule(rec.employee_id, kind, rec.partner_id)

    @api.depends('role', 'target_sales', 'target_collection',
                 'achieved_sales', 'achieved_collection',
                 'employee_id', 'partner_id', 'split_id', 'sheet_id.period',
                 'x_condition_override')
    def _compute_commission(self):
        Rule = self.env['ksw.sales.commission.rule']
        for rec in self:
            sales_amt = 0.0
            coll_amt = 0.0
            comb_amt = 0.0
            sales_rule = Rule
            coll_rule = Rule
            comb_rule = Rule
            force = bool(rec.x_condition_override)

            rec.sales_pct = (
                (rec.achieved_sales / rec.target_sales) * 100.0
                if rec.target_sales else 0.0
            )
            rec.collection_pct = (
                (rec.achieved_collection / rec.target_collection) * 100.0
                if rec.target_collection else 0.0
            )

            if rec.role in ('sales', 'both'):
                sales_rule = self._get_profile_rule(rec, 'sales')
                if sales_rule:
                    sales_amt, _t, _p = sales_rule._evaluate(
                        rec.target_sales, rec.target_collection,
                        rec.achieved_sales, rec.achieved_collection,
                        employee=rec.employee_id, partner=rec.partner_id,
                        force_pass=force,
                    )
            if rec.role in ('collect', 'both'):
                coll_rule = self._get_profile_rule(rec, 'collection')
                if coll_rule:
                    coll_amt, _t, _p = coll_rule._evaluate(
                        rec.target_sales, rec.target_collection,
                        rec.achieved_sales, rec.achieved_collection,
                        employee=rec.employee_id, partner=rec.partner_id,
                        force_pass=force,
                    )
            if rec.role == 'both':
                comb_rule = self._get_profile_rule(rec, 'combined')
                if comb_rule:
                    comb_amt, _t, _p = comb_rule._evaluate(
                        rec.target_sales, rec.target_collection,
                        rec.achieved_sales, rec.achieved_collection,
                        employee=rec.employee_id, partner=rec.partner_id,
                        force_pass=force,
                    )
                    # When a combined rule fires, it replaces the
                    # standalone sales + collection payouts (admin
                    # picks one model or the other per employee).
                    if comb_amt:
                        sales_amt = 0.0
                        coll_amt = 0.0

            rec.sales_rule_id = sales_rule.id if sales_rule else False
            rec.collection_rule_id = coll_rule.id if coll_rule else False
            rec.combined_rule_id = comb_rule.id if comb_rule else False
            rec.sales_commission_amount = sales_amt
            rec.collection_commission_amount = coll_amt
            rec.combined_commission_amount = comb_amt
            rec.total_commission = sales_amt + coll_amt + comb_amt

    # ------------------------------------------------------------------
    # CRUD — auto-sync confirmed sheets when achieved figures change
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        confirmed = lines.mapped('sheet_id').filtered(
            lambda s: s.state == 'confirmed')
        confirmed._sync_to_commission_sheets()
        return lines

    def write(self, vals):
        res = super().write(vals)
        watched = {
            'achieved_sales', 'achieved_collection',
            'target_sales', 'target_collection',
            'employee_id', 'partner_id', 'split_id', 'role',
        }
        if watched & set(vals):
            confirmed = self.mapped('sheet_id').filtered(
                lambda s: s.state == 'confirmed')
            confirmed._sync_to_commission_sheets()
        return res

    def unlink(self):
        confirmed_sheets = self.mapped('sheet_id').filtered(
            lambda s: s.state == 'confirmed')
        res = super().unlink()
        confirmed_sheets._sync_to_commission_sheets()
        return res

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('achieved_sales', 'achieved_collection',
                    'target_sales', 'target_collection')
    def _check_non_negative(self):
        for rec in self:
            if (rec.achieved_sales or 0.0) < 0 \
                    or (rec.achieved_collection or 0.0) < 0 \
                    or (rec.target_sales or 0.0) < 0 \
                    or (rec.target_collection or 0.0) < 0:
                raise ValidationError(_(
                    "Achieved and target amounts must be "
                    "zero or positive."))

    # ------------------------------------------------------------------
    # Sales-manager override actions
    # ------------------------------------------------------------------
    def _check_sales_manager(self):
        if self.env.su or self.env.user.has_group(
                'KSW_commissions.group_sales_commission_manager'):
            return
        raise UserError(_(
            "Only a Sales Manager can override the commission "
            "condition on a line."))

    def action_open_override_wizard(self):
        """Open the override-reason wizard for the manager to capture
        a justification before flipping ``x_condition_override``.
        """
        self.ensure_one()
        self._check_sales_manager()
        return {
            'name': _("Override Commission Condition"),
            'type': 'ir.actions.act_window',
            'res_model': 'ksw.sales.commission.override.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_line_id': self.id,
            },
        }

    def action_revoke_override(self):
        """Clear an existing override (manager-only)."""
        self._check_sales_manager()
        for rec in self:
            if not rec.x_condition_override:
                continue
            prev_user = rec.x_override_by
            prev_reason = rec.x_override_reason
            rec.sudo().write({
                'x_condition_override': False,
                'x_override_by': False,
                'x_override_date': False,
                'x_override_reason': False,
            })
            rec.sheet_id.message_post(
                body=_(
                    "↩ Override revoked on line for <b>%(emp)s</b> by "
                    "<b>%(user)s</b>. Previous reason: <i>%(reason)s</i>",
                    emp=rec.employee_id.display_name or '',
                    user=self.env.user.name,
                    reason=prev_reason or '—',
                ),
                subtype_xmlid='mail.mt_note',
            )
        # Re-sync any commission sheets that were already pushed.
        confirmed = self.mapped('sheet_id').filtered(
            lambda s: s.state == 'confirmed')
        confirmed._sync_to_commission_sheets()

    def _apply_override(self, reason):
        """Internal: stamp the override fields and chatter the sheet.
        Called by the wizard after capturing the reason.
        """
        self.ensure_one()
        self._check_sales_manager()
        self.sudo().write({
            'x_condition_override': True,
            'x_override_by': self.env.uid,
            'x_override_date': fields.Datetime.now(),
            'x_override_reason': reason or False,
        })
        self.sheet_id.message_post(
            body=_(
                "✔ Commission-condition <b>override granted</b> on line "
                "for <b>%(emp)s</b> by <b>%(user)s</b>.<br/>"
                "<b>Reason:</b> %(reason)s",
                emp=self.employee_id.display_name or '',
                user=self.env.user.name,
                reason=reason or '—',
            ),
            subtype_xmlid='mail.mt_note',
        )
        if self.sheet_id.state == 'confirmed':
            self.sheet_id._sync_to_commission_sheets()




