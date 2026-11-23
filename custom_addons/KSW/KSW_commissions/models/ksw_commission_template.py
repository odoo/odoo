"""KSW Commission Template — reusable line preset for commission sheets.

A supervisor creates a named template (e.g. "Drivers — Sites A&B"),
configures the standard lines (category + default amount), and assigns
the employees who use that template.  When a new ``ksw.commission.sheet``
is created for an employee that has a template, the template lines are
automatically copied into the sheet so the supervisor only needs to
adjust amounts rather than building every sheet from scratch.

Rules
-----
* An employee can belong to **at most one template** (enforced by
  ``@api.constrains`` — the Many2many makes the bulk-assign UI
  convenient while the constraint prevents duplicates).
* Already-created (existing) sheets are never mutated retroactively;
  the auto-fill only fires in ``create()``.
* The ``_apply_to_sheet(sheet)`` helper is the single write path so
  it can also be called from a view button to backfill existing empty
  draft sheets.
"""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .ksw_commission_sheet_line import HOLIDAY_OPTIONS


class KswCommissionTemplate(models.Model):
    _name = 'ksw.commission.template'
    _description = 'KSW Commission Sheet Template'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    description = fields.Text(
        help='Optional notes about when/how to use this template.',
    )

    line_ids = fields.One2many(
        'ksw.commission.template.line', 'template_id',
        string='Template Lines', copy=True,
    )
    employee_ids = fields.Many2many(
        'hr.employee',
        'ksw_commission_template_employee_rel',
        'template_id', 'employee_id',
        string='Assigned Employees',
        domain="[('x_is_attendance_sheet', '=', True)]",
    )

    # Convenience counter shown in the list view.
    employee_count = fields.Integer(
        compute='_compute_employee_count', string='# Employees',
    )

    @api.depends('employee_ids')
    def _compute_employee_count(self):
        for rec in self:
            rec.employee_count = len(rec.employee_ids)

    def action_view_employees(self):
        """Open the list of employees assigned to this template."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Assigned Employees — %s') % self.name,
            'res_model': 'hr.employee',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.employee_ids.ids)],
        }

    # ------------------------------------------------------------------
    # Validation: one employee → at most one template
    # ------------------------------------------------------------------
    @api.constrains('employee_ids')
    def _check_unique_employee_assignment(self):
        """Ensure that no employee appears in more than one template."""
        for rec in self:
            if not rec.employee_ids:
                continue
            emp_ids = rec.employee_ids.ids
            # Look for other templates that share any of these employees.
            duplicates = self.search([
                ('id', '!=', rec.id),
                ('employee_ids', 'in', emp_ids),
            ])
            if duplicates:
                # Find the actual conflicting employees for the message.
                conflict_emps = duplicates.mapped('employee_ids').filtered(
                    lambda e: e.id in emp_ids
                )
                conflict_names = ', '.join(
                    conflict_emps.mapped('name')[:5]
                )
                raise ValidationError(_(
                    "The following employee(s) are already assigned to "
                    "another commission template: %(names)s.\n"
                    "An employee can only belong to one template at a time.",
                    names=conflict_names,
                ))

    # ------------------------------------------------------------------
    # Apply helper
    # ------------------------------------------------------------------
    def _apply_to_sheet(self, sheet):
        """Copy this template's lines into ``sheet``, skipping any
        category/holiday combination that already exists on the sheet.

        This is called both from ``ksw.commission.sheet.create()``
        (auto-fill on new sheets) and from the "Apply Template" button
        on existing draft sheets.

        :param sheet: a single ``ksw.commission.sheet`` record
        """
        self.ensure_one()
        if not self.line_ids:
            return
        # Build a set of (category_id, holiday_id) already on the sheet
        # so we don't create duplicates when called on a non-empty sheet.
        existing = {
            (ln.category_id.id, ln.holiday_id)
            for ln in sheet.line_ids
        }
        to_create = []
        for tl in self.line_ids:
            key = (tl.category_id.id, tl.holiday_id)
            if key in existing:
                continue
            to_create.append({
                'sheet_id': sheet.id,
                'sequence': tl.sequence,
                'category_id': tl.category_id.id,
                'holiday_id': tl.holiday_id,
                'quantity': tl.quantity,
                'amount': tl.amount,
                'description': tl.description,
            })
        if to_create:
            self.env['ksw.commission.sheet.line'].sudo().create(to_create)

    # ------------------------------------------------------------------
    # Helper used by the sheet model: find template for an employee
    # ------------------------------------------------------------------
    @api.model
    def _get_template_for_employee(self, employee):
        """Return the active template assigned to ``employee``, or empty."""
        return self.search([
            ('employee_ids', 'in', employee.id),
            ('active', '=', True),
        ], limit=1)

    # ------------------------------------------------------------------
    # Auto-create sheets when employees are added to a template
    # ------------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        if 'employee_ids' in vals:
            # Ensure every currently-assigned employee has a draft sheet
            # for the current month.  Idempotent — existing sheets are
            # never touched.
            Sheet = self.env['ksw.commission.sheet']
            new_employees = self.mapped('employee_ids')
            if new_employees:
                Sheet._ensure_current_period_sheets(employees=new_employees)
        return res


class KswCommissionTemplateLine(models.Model):
    _name = 'ksw.commission.template.line'
    _description = 'KSW Commission Template Line'
    _order = 'template_id, sequence, id'

    template_id = fields.Many2one(
        'ksw.commission.template', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    category_id = fields.Many2one(
        'ksw.commission.category', required=True,
        domain="[('active', '=', True)]",
        ondelete='restrict',
    )
    kind = fields.Selection(
        related='category_id.kind', store=True, readonly=True,
    )
    holiday_id = fields.Selection(
        HOLIDAY_OPTIONS,
        help='Required when the category is "Holiday Bonus".',
    )
    is_quantity_based = fields.Boolean(
        related='category_id.is_quantity_based',
        store=True, readonly=True,
    )
    quantity_label = fields.Char(
        related='category_id.quantity_label', readonly=True,
    )
    quantity = fields.Float(
        default=0.0,
        help='Default quantity pre-filled on new sheets when the '
             'category is Quantity-Based. The supervisor can adjust '
             'it on each sheet.',
    )
    amount = fields.Monetary(
        required=True, default=0.0,
        compute='_compute_amount', store=True, readonly=False,
        help='Default amount pre-filled on new sheets. For '
             'Quantity-Based categories this is auto-computed from '
             'the formula × default quantity.',
    )
    description = fields.Char()
    currency_id = fields.Many2one(
        'res.currency',
        default=lambda s: s.env.company.currency_id,
    )

    @api.depends('quantity', 'category_id',
                 'category_id.is_quantity_based',
                 'category_id.formula')
    def _compute_amount(self):
        for rec in self:
            cat = rec.category_id
            if cat and cat.is_quantity_based:
                rec.amount = cat._eval_formula(rec.quantity)
            else:
                rec.amount = rec.amount or 0.0

    @api.constrains('kind', 'holiday_id')
    def _check_holiday_required(self):
        for rec in self:
            if rec.kind == 'holiday_bonus' and not rec.holiday_id:
                raise ValidationError(_(
                    "Holiday-bonus lines must specify which holiday."
                ))
            if rec.kind != 'holiday_bonus' and rec.holiday_id:
                raise ValidationError(_(
                    "Only Holiday-Bonus lines can carry a holiday selector."
                ))
