"""KSW Technician Location Allowance — per-period meal-occurrence tally.

Mirror of ``ksw.driver.commission.sheet`` but for technician meal
allowances.  The supervisor opens one location-allowance sheet per
month, adds a row per technician, fills in how many breakfasts /
lunches / dinners occurred, and confirms.  On confirm the per-line
``total_allowance`` is pushed to the matching
``ksw.commission.sheet.location_allowance_amount`` (auto-creating a
draft commission sheet if none exists yet).

Unit prices are NOT stored on this model — they are read live from
the KSW_commissions general configuration (``ir.config_parameter``)
via :meth:`res.config.settings._get_meal_prices` so the admin can
change them at any time without touching past sheets' computed totals
will refresh on next compute trigger.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class KswLocationAllowanceSheet(models.Model):
    """One technician location-allowance tally per period."""
    _name = 'ksw.location.allowance.sheet'
    _description = 'KSW Technician Location Allowance Sheet'
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
        'ksw.location.allowance.line', 'sheet_id', copy=True,
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda s: s.env.company.currency_id,
        required=True,
    )
    total_allowance = fields.Monetary(
        compute='_compute_total', store=True,
    )

    _unique_period = models.Constraint(
        'UNIQUE(period)',
        'Only one technician location-allowance sheet per month.',
    )

    @api.depends('line_ids.total_allowance')
    def _compute_total(self):
        for rec in self:
            rec.total_allowance = sum(
                rec.line_ids.mapped('total_allowance'))

    @api.model_create_multi
    def create(self, vals_list):
        Seq = self.env['ir.sequence']
        for v in vals_list:
            if not v.get('name') or v['name'] == 'New':
                v['name'] = (
                    Seq.next_by_code('ksw.location.allowance.sheet')
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
                    'Technician location-allowance sheet confirmed. '
                    'Total: %(t).2f',
                    t=rec.total_allowance,
                ),
                subtype_xmlid='mail.mt_note',
            )

    def action_reset_to_draft(self):
        for rec in self:
            rec.write({'state': 'draft', 'is_locked': False})
            # Re-sync so commission sheets clear / recompute the
            # location-allowance amount based on the new state.
            rec._sync_to_commission_sheets()

    # ------------------------------------------------------------------
    # Commission-sheet sync
    # ------------------------------------------------------------------
    def _sync_to_commission_sheets(self):
        """Recompute location_allowance_amount on the matching
        commission sheets.

        Auto-creates a draft commission sheet for any newly added
        technician that does not yet have one for this period
        (template lines are applied automatically via the sheet's
        create() hook).
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
                sheet.sudo()._compute_location_allowance()
                sheet.sudo().flush_recordset(
                    ['location_allowance_amount'])


class KswLocationAllowanceLine(models.Model):
    """One technician's monthly meal occurrences."""
    _name = 'ksw.location.allowance.line'
    _description = 'KSW Technician Location Allowance Line'
    _order = 'sheet_id, sequence, id'

    sheet_id = fields.Many2one(
        'ksw.location.allowance.sheet',
        required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    employee_id = fields.Many2one(
        'hr.employee', required=True, ondelete='restrict',
        domain="[('x_is_attendance_sheet', '=', True)]",
    )
    department_id = fields.Many2one(
        related='employee_id.department_id',
        store=True, readonly=True,
    )

    breakfast_qty = fields.Integer(default=0)
    lunch_qty = fields.Integer(default=0)
    dinner_qty = fields.Integer(default=0)

    breakfast_price = fields.Float(
        compute='_compute_prices', readonly=True,
        help='Live unit price from KSW_commissions general settings.',
    )
    lunch_price = fields.Float(
        compute='_compute_prices', readonly=True,
    )
    dinner_price = fields.Float(
        compute='_compute_prices', readonly=True,
    )

    breakfast_amount = fields.Monetary(
        compute='_compute_amounts', store=True,
    )
    lunch_amount = fields.Monetary(
        compute='_compute_amounts', store=True,
    )
    dinner_amount = fields.Monetary(
        compute='_compute_amounts', store=True,
    )
    total_allowance = fields.Monetary(
        compute='_compute_amounts', store=True,
    )
    currency_id = fields.Many2one(
        related='sheet_id.currency_id', store=True, readonly=True,
    )

    _unique_employee_per_sheet = models.Constraint(
        'UNIQUE(sheet_id, employee_id)',
        'A technician can only appear once per location-allowance '
        'sheet.',
    )

    # ------------------------------------------------------------------
    # CRUD — auto-sync confirmed sheets when meal counts change
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
        meal_fields = {'breakfast_qty', 'lunch_qty', 'dinner_qty',
                       'employee_id'}
        if meal_fields & set(vals):
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
    # Compute
    # ------------------------------------------------------------------
    def _compute_prices(self):
        """Read meal unit prices from ``ir.config_parameter`` (live).

        Non-stored on purpose — when the admin edits the prices in
        General Configuration, every line on every sheet immediately
        reflects the new value (and ``_compute_amounts`` recomputes
        because ``breakfast_price`` / ``lunch_price`` / ``dinner_price``
        are listed in its depends).
        """
        breakfast, lunch, dinner = self.env[
            'res.config.settings']._get_meal_prices()
        for rec in self:
            rec.breakfast_price = breakfast
            rec.lunch_price = lunch
            rec.dinner_price = dinner

    @api.depends('breakfast_qty', 'lunch_qty', 'dinner_qty',
                 'breakfast_price', 'lunch_price', 'dinner_price')
    def _compute_amounts(self):
        for rec in self:
            rec.breakfast_amount = (
                (rec.breakfast_qty or 0) * (rec.breakfast_price or 0.0))
            rec.lunch_amount = (
                (rec.lunch_qty or 0) * (rec.lunch_price or 0.0))
            rec.dinner_amount = (
                (rec.dinner_qty or 0) * (rec.dinner_price or 0.0))
            rec.total_allowance = (
                rec.breakfast_amount
                + rec.lunch_amount
                + rec.dinner_amount
            )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('breakfast_qty', 'lunch_qty', 'dinner_qty')
    def _check_non_negative(self):
        for rec in self:
            if (rec.breakfast_qty or 0) < 0 \
                    or (rec.lunch_qty or 0) < 0 \
                    or (rec.dinner_qty or 0) < 0:
                raise ValidationError(_(
                    "Meal occurrences must be zero or positive."))

