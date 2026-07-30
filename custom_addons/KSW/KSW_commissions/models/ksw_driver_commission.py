"""KSW Driver Commission Sheet & Line — per-site monthly trip tally.

Phase B model. The supervisor opens a driver-commission sheet for a site
and fills in one line per driver (employee).  The tiered commission is
computed automatically with the rates defined on ``ksw.site``, then
written back to the parent ``ksw.commission.sheet`` as the read-only
``driver_commission_amount``.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class KswDriverCommissionSheet(models.Model):
    """One driver-commission tally per (site, period)."""
    _name = 'ksw.driver.commission.sheet'
    _description = 'KSW Driver Commission Sheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'period desc, site_id'

    name = fields.Char(readonly=True, default='New', copy=False)
    site_id = fields.Many2one(
        'ksw.site', required=True, ondelete='restrict', tracking=True,
    )
    period = fields.Date(
        required=True,
        default=lambda s: fields.Date.context_today(s).replace(day=1),
        tracking=True,
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('confirmed', 'Confirmed')],
        default='draft', required=True, copy=False, tracking=True,
    )
    is_locked = fields.Boolean(readonly=True, copy=False)
    line_ids = fields.One2many(
        'ksw.driver.commission.line', 'sheet_id', copy=True,
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id,
        required=True,
    )
    total_commission = fields.Monetary(
        compute='_compute_total', store=True,
    )

    _unique_site_period = models.Constraint(
        'UNIQUE(site_id, period)',
        'Only one driver commission sheet per site per month.',
    )

    @api.depends('line_ids.total_commission')
    def _compute_total(self):
        for rec in self:
            rec.total_commission = sum(rec.line_ids.mapped('total_commission'))

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for v in vals_list:
            if not v.get('name') or v['name'] == 'New':
                v['name'] = seq.next_by_code('ksw.driver.commission.sheet') or 'New'
            if v.get('period'):
                d = fields.Date.to_date(v['period'])
                v['period'] = d.replace(day=1)
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only draft sheets can be confirmed."))
            rec.write({'state': 'confirmed', 'is_locked': True})
            # Push commission amounts to the linked commission sheets.
            rec._sync_to_commission_sheets()
            rec.message_post(
                body=_('Driver commission sheet confirmed. Total: %(t).2f',
                       t=rec.total_commission),
                subtype_xmlid='mail.mt_note',
            )

    def action_reset_to_draft(self):
        for rec in self:
            rec.write({'state': 'draft', 'is_locked': False})
            rec._sync_to_commission_sheets()

    def _sync_to_commission_sheets(self):
        """Recompute driver_commission_amount on linked commission sheets.

        Uses sudo() so that already-Done commission sheets receive the
        updated driver commission without triggering the write guard.
        Auto-creates a draft commission sheet for any newly added driver
        that does not yet have one for this period (template lines are
        applied automatically via the sheet's create() hook).
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
                    # New driver added — create their commission sheet so
                    # the driver commission amount is visible immediately.
                    sheet = Sheet.sudo().create({
                        'employee_id': line.employee_id.id,
                        'period': rec.period,
                    })
                # Recompute in sudo context so the write guard on Done
                # commission sheets is bypassed (this is a system-level
                # sync, not a human edit).
                sheet.sudo()._compute_driver_commission()
                sheet.sudo().flush_recordset(['driver_commission_amount'])

    # ==================================================================
    # Report helpers — called from QWeb templates.
    # Lambdas that close over outer-scope variables are forbidden in
    # QWeb's safe_eval, so all aggregation lives here.
    # ==================================================================
    def _report_get_period_labels(self):
        """Return 'Month YYYY' labels for all distinct periods, newest first."""
        periods = sorted(
            {o.period for o in self if o.period}, reverse=True)
        return [p.strftime('%B %Y') for p in periods]

    def _report_get_driver_rollup(self):
        """Return a list of dicts for the per-driver cumulative table.

        Each dict: name, sheet_count, total_trips, total_commission.
        Sorted alphabetically by driver name.
        """
        driver_map = {}
        for ln in self.mapped('line_ids'):
            if not ln.employee_id:
                continue
            eid = ln.employee_id.id
            if eid not in driver_map:
                driver_map[eid] = {
                    'name': ln.employee_id.name or '',
                    'sheet_count': 0,
                    'total_trips': 0,
                    'total_commission': 0.0,
                }
            driver_map[eid]['sheet_count'] += 1
            driver_map[eid]['total_trips'] += ln.multiplied_trips or 0
            driver_map[eid]['total_commission'] += ln.total_commission or 0.0
        return sorted(driver_map.values(), key=lambda d: d['name'])


class KswDriverCommissionLine(models.Model):
    """One row per driver on a driver-commission sheet."""
    _name = 'ksw.driver.commission.line'
    _description = 'KSW Driver Commission Line'
    _order = 'sheet_id, sequence'

    sheet_id = fields.Many2one(
        'ksw.driver.commission.sheet', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    employee_id = fields.Many2one(
        'hr.employee', required=True, ondelete='restrict',
        domain="[('x_is_attendance_sheet', '=', True)]",
    )
    vehicle_number = fields.Char()
    worked_days = fields.Integer(
        default=0, help='Actual days worked this month (entered by supervisor).',
    )

    # Trip counts
    required_trips = fields.Integer(
        compute='_compute_required_trips', store=True,
        help='Tier-1 threshold: round(site.required_trips_full_month × '
             'worked_days / 30). No commission earned until this is exceeded.',
    )
    actual_trips = fields.Integer(default=0)
    multiplied_trips = fields.Integer(
        default=0,
        help='Effective trip count after any manual adjustment by the '
             'supervisor. Entered directly — not computed.',
    )

    # Tier breakdown (informational)
    tier1_trips = fields.Integer(compute='_compute_tiers', store=True)
    tier2_trips = fields.Integer(compute='_compute_tiers', store=True)
    tier3_trips = fields.Integer(compute='_compute_tiers', store=True)
    tier4_trips = fields.Integer(compute='_compute_tiers', store=True)
    tier5_trips = fields.Integer(compute='_compute_tiers', store=True)

    total_commission = fields.Monetary(
        compute='_compute_tiers', store=True,
    )
    currency_id = fields.Many2one(
        related='sheet_id.currency_id', store=True, readonly=True,
    )

    # --- CRUD — auto-sync on confirmed sheets ----------------------------

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        # Sync any lines added to an already-confirmed sheet immediately.
        confirmed_sheets = lines.mapped('sheet_id').filtered(
            lambda s: s.state == 'confirmed')
        confirmed_sheets._sync_to_commission_sheets()
        return lines

    def write(self, vals):
        res = super().write(vals)
        # Re-sync if the trip data changed on a confirmed sheet.
        trip_fields = {'actual_trips', 'multiplied_trips', 'worked_days',
                       'employee_id'}
        if trip_fields & set(vals):
            confirmed_sheets = self.mapped('sheet_id').filtered(
                lambda s: s.state == 'confirmed')
            confirmed_sheets._sync_to_commission_sheets()
        return res

    # --- Computed helpers -------------------------------------------

    @api.depends('sheet_id.site_id.required_trips_full_month', 'worked_days')
    def _compute_required_trips(self):
        for l in self:
            site = l.sheet_id.site_id
            base = site.required_trips_full_month if site else 50
            l.required_trips = round(base * (l.worked_days or 0) / 30)

    @api.depends(
        'multiplied_trips', 'required_trips',
        'sheet_id.site_id.tier2_trips', 'sheet_id.site_id.tier2_rate',
        'sheet_id.site_id.tier3_trips', 'sheet_id.site_id.tier3_rate',
        'sheet_id.site_id.tier4_trips', 'sheet_id.site_id.tier4_rate',
        'sheet_id.site_id.tier5_rate',
    )
    def _compute_tiers(self):
        for l in self:
            site = l.sheet_id.site_id
            if not site:
                l.tier1_trips = l.tier2_trips = l.tier3_trips = 0
                l.tier4_trips = l.tier5_trips = 0
                l.total_commission = 0.0
                continue

            above = max((l.multiplied_trips or 0) - (l.required_trips or 0), 0)
            l.tier1_trips = (l.required_trips or 0)

            # Waterfall through tiers 2–5
            t2 = min(above, site.tier2_trips)
            above -= t2
            t3 = min(above, site.tier3_trips)
            above -= t3
            t4 = min(above, site.tier4_trips)
            above -= t4
            t5 = above  # remainder

            l.tier2_trips = t2
            l.tier3_trips = t3
            l.tier4_trips = t4
            l.tier5_trips = t5

            l.total_commission = (
                t2 * (site.tier2_rate or 0.0)
                + t3 * (site.tier3_rate or 0.0)
                + t4 * (site.tier4_rate or 0.0)
                + t5 * (site.tier5_rate or 0.0)
            )
