"""KSW Salesperson Profile — yearly target with 12-month breakdown.

Defines the role of a salesperson (sales / collect / both) and the
per-year sales / collection target. The yearly figure is split into
12 monthly target rows on creation; admins may override individual
months for seasonality.

The :class:`ksw.sales.commission.line` reads the matching monthly
target via :meth:`_get_targets` so the accountant entering achieved
numbers immediately sees the achievement percentage.
"""
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


ROLE_SELECTION = [
    ('sales', 'Salesman'),
    ('collect', 'Collector'),
    ('both', 'Salesman & Collector'),
]


class KswSalespersonProfile(models.Model):
    _name = 'ksw.salesperson.profile'
    _description = 'KSW Salesperson Profile (yearly target)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year desc, employee_id'
    _rec_name = 'display_name'

    employee_id = fields.Many2one(
        'hr.employee', required=True, ondelete='restrict', tracking=True,
        domain="[('x_is_attendance_sheet', '=', True)]",
    )
    year = fields.Integer(
        required=True, tracking=True,
        default=lambda s: fields.Date.context_today(s).year,
    )
    role = fields.Selection(
        ROLE_SELECTION, required=True, default='sales', tracking=True,
        help='Drives which kind of commission rules apply: sales, '
             'collection, or combined.',
    )
    annual_sales_target = fields.Monetary(tracking=True)
    annual_collection_target = fields.Monetary(tracking=True)
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id,
        required=True,
    )
    target_line_ids = fields.One2many(
        'ksw.salesperson.target.line', 'profile_id', copy=True,
    )
    active = fields.Boolean(default=True)
    note = fields.Text()

    display_name = fields.Char(compute='_compute_display_name', store=True)

    _unique_employee_year = models.Constraint(
        'UNIQUE(employee_id, year)',
        'A salesperson can only have one profile per year.',
    )

    @api.depends('employee_id', 'year')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f"{rec.employee_id.name or ''} — {rec.year}"
                if rec.employee_id else (str(rec.year) if rec.year else '')
            )

    # ------------------------------------------------------------------
    # CRUD — seed 12 monthly rows on create / when annual totals change
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        for rec in recs:
            if not rec.target_line_ids:
                rec._seed_monthly_lines()
        return recs

    def _seed_monthly_lines(self):
        """Create 12 monthly target rows, evenly splitting the
        annual figures across months. Existing rows are kept.
        """
        Line = self.env['ksw.salesperson.target.line']
        for rec in self:
            existing = {l.month: l for l in rec.target_line_ids}
            sales_share = (rec.annual_sales_target or 0.0) / 12.0
            coll_share = (rec.annual_collection_target or 0.0) / 12.0
            for m in range(1, 13):
                if str(m) in existing:
                    continue
                Line.create({
                    'profile_id': rec.id,
                    'month': str(m),
                    'sales_target': sales_share,
                    'collection_target': coll_share,
                })

    def action_redistribute_targets(self):
        """Reset the 12 monthly rows to an even split of the current
        annual totals — overwrites manual overrides.
        """
        for rec in self:
            sales_share = (rec.annual_sales_target or 0.0) / 12.0
            coll_share = (rec.annual_collection_target or 0.0) / 12.0
            for line in rec.target_line_ids:
                line.write({
                    'sales_target': sales_share,
                    'collection_target': coll_share,
                })

    # ------------------------------------------------------------------
    # Public lookup
    # ------------------------------------------------------------------
    @api.model
    def _get_targets(self, employee, period):
        """Return ``(sales_target, collection_target, profile)`` for the
        given employee/period. ``period`` is a date (first-of-month).
        Falls back to ``(0, 0, False)`` when no profile is found.
        """
        if not employee or not period:
            return (0.0, 0.0, self.browse())
        period = fields.Date.to_date(period)
        profile = self.sudo().search([
            ('employee_id', '=', employee.id),
            ('year', '=', period.year),
            ('active', '=', True),
        ], limit=1)
        if not profile:
            return (0.0, 0.0, self.browse())
        line = profile.target_line_ids.filtered(
            lambda l: l.month == str(period.month))
        if line:
            return (
                line[0].sales_target or 0.0,
                line[0].collection_target or 0.0,
                profile,
            )
        # No row for that month — fall back to even split.
        return (
            (profile.annual_sales_target or 0.0) / 12.0,
            (profile.annual_collection_target or 0.0) / 12.0,
            profile,
        )


class KswSalespersonTargetLine(models.Model):
    _name = 'ksw.salesperson.target.line'
    _description = 'KSW Salesperson Monthly Target'
    _order = 'profile_id, month'

    profile_id = fields.Many2one(
        'ksw.salesperson.profile', required=True, ondelete='cascade',
    )
    month = fields.Selection(
        [(str(i), date(2000, i, 1).strftime('%B')) for i in range(1, 13)],
        required=True,
    )
    sales_target = fields.Monetary()
    collection_target = fields.Monetary()
    currency_id = fields.Many2one(
        related='profile_id.currency_id', store=True, readonly=True,
    )

    _unique_profile_month = models.Constraint(
        'UNIQUE(profile_id, month)',
        'Each month can only appear once per profile.',
    )

    @api.constrains('sales_target', 'collection_target')
    def _check_non_negative(self):
        for rec in self:
            if (rec.sales_target or 0.0) < 0 \
                    or (rec.collection_target or 0.0) < 0:
                raise ValidationError(_(
                    "Monthly targets must be zero or positive."))





