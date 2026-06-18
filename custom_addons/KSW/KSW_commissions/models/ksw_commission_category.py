from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval


class KswCommissionCategory(models.Model):
    """Admin-managed catalog of allowance / commission types.

    Each ``ksw.commission.sheet.line`` references one category. Categories
    are seeded at install (see ``data/category_data.xml``) and admins can
    add custom ones. Seeded categories are flagged ``is_system=True`` and
    cannot be unlinked.
    """
    _name = 'ksw.commission.category'
    _description = 'KSW Commission / Allowance Category'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True,
        help='Stable identifier used in reports / exports. Must be unique.',
    )
    kind = fields.Selection(
        [
            ('allowance', 'Allowance'),
            ('commission', 'Commission'),
            ('holiday_bonus', 'Holiday Bonus'),
            ('bonus', 'Bonus'),
            ('other', 'Other'),
        ],
        required=True, default='allowance',
        help="Drives UI hints. 'holiday_bonus' enables the holiday "
             "selector on the line and a unique-per-holiday constraint.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    is_system = fields.Boolean(
        readonly=True, copy=False,
        help='Set on seeded categories. Blocks unlink.',
    )
    description = fields.Text()

    # ------------------------------------------------------------------
    # Quantity-based amount computation
    # ------------------------------------------------------------------
    is_quantity_based = fields.Boolean(
        string='Quantity-Based Amount',
        default=False,
        help='When checked, sheet lines using this category disable '
             'the "Amount" field and compute it from a Python formula '
             'applied to the entered quantity (e.g. Friday Work '
             'Allowance = quantity × 100 SAR).',
    )
    formula = fields.Char(
        string='Amount Formula',
        help='Python expression evaluated to compute the line amount '
             'from the entered quantity. The variable ``quantity`` '
             '(alias ``qty``) is in scope; assign the final amount to '
             '``result``.\n\n'
             'Example: result = quantity * 100\n'
             'Example: result = qty * 50 + (100 if qty >= 5 else 0)',
    )
    quantity_label = fields.Char(
        string='Quantity Label',
        translate=True,
        help='Display label for the quantity field on the sheet line '
             '(e.g. "Days", "Trips", "Hours"). Falls back to '
             '"Quantity" when empty.',
    )
    min_quantity = fields.Float(
        string='Min Quantity', default=0.0,
        help='Minimum quantity accepted on a sheet line. 0 = no '
             'lower bound (negative quantities are still rejected).',
    )
    max_quantity = fields.Float(
        string='Max Quantity', default=0.0,
        help='Maximum quantity accepted on a sheet line. 0 means no '
             'upper bound (e.g. unlimited Fridays).',
    )

    _unique_code = models.Constraint(
        'UNIQUE(code)',
        'Category code must be unique.',
    )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('is_quantity_based', 'formula')
    def _check_formula(self):
        """Validate the formula compiles and produces a numeric result.

        Run the formula with ``quantity = 1.0`` as a smoke-test; if it
        raises or doesn't assign ``result`` to a number, reject the
        save. Catches typos at admin time rather than at supervisor
        time.
        """
        for rec in self:
            if not rec.is_quantity_based:
                continue
            if not rec.formula or not rec.formula.strip():
                raise ValidationError(_(
                    "Category '%(n)s' is marked Quantity-Based but has "
                    "no formula. Set a Python expression like "
                    "``result = quantity * 100``.",
                    n=rec.name or rec.code,
                ))
            try:
                value = rec._eval_formula(1.0)
            except Exception as e:
                raise ValidationError(_(
                    "Formula on category '%(n)s' could not be evaluated:\n"
                    "%(err)s\n\n"
                    "Use ``quantity`` (or ``qty``) and assign the final "
                    "amount to ``result``. Example: "
                    "``result = quantity * 100``.",
                    n=rec.name or rec.code, err=str(e),
                ))
            if not isinstance(value, (int, float)):
                raise ValidationError(_(
                    "Formula on category '%(n)s' must produce a "
                    "numeric result; got %(t)s instead.",
                    n=rec.name or rec.code, t=type(value).__name__,
                ))

    @api.constrains('min_quantity', 'max_quantity', 'is_quantity_based')
    def _check_quantity_bounds(self):
        for rec in self:
            if not rec.is_quantity_based:
                continue
            if rec.min_quantity < 0:
                raise ValidationError(_(
                    "Min Quantity cannot be negative."))
            if rec.max_quantity and rec.max_quantity < rec.min_quantity:
                raise ValidationError(_(
                    "Max Quantity (%(mx)s) must be greater than or "
                    "equal to Min Quantity (%(mn)s).",
                    mx=rec.max_quantity, mn=rec.min_quantity,
                ))

    # ------------------------------------------------------------------
    # Public helper — used by sheet/template lines to evaluate amount.
    # ------------------------------------------------------------------
    def _eval_formula(self, quantity):
        """Evaluate ``self.formula`` against ``quantity``, return the
        numeric ``result``. Falls back to ``0.0`` when the category
        is not quantity-based or has no formula.
        """
        self.ensure_one()
        if not self.is_quantity_based or not self.formula:
            return 0.0
        qty = float(quantity or 0.0)
        ctx = {'quantity': qty, 'qty': qty, 'result': 0.0}
        safe_eval(self.formula, ctx, mode='exec')
        return float(ctx.get('result') or 0.0)

    def unlink(self):
        for rec in self:
            if rec.is_system and not self.env.su:
                raise UserError(_(
                    "Category '%(name)s' is a system category and cannot "
                    "be deleted. Archive it instead.",
                    name=rec.name or rec.code,
                ))
        return super().unlink()
