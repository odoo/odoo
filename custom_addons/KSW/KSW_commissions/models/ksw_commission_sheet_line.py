"""KSW Commission Sheet Line — one allowance/commission entry."""
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


# 4 paid Saudi public holidays — also drives the holiday-bonus uniqueness.
HOLIDAY_OPTIONS = [
    ('foundation_day', 'Foundation Day'),
    ('national_day', 'National Day'),
    ('eid_fitr', 'Eid Al-Fitr'),
    ('eid_adha', 'Eid Al-Adha'),
]


class KswCommissionSheetLine(models.Model):
    _name = 'ksw.commission.sheet.line'
    _description = 'KSW Commission Sheet Line'
    _order = 'sheet_id, sequence, id'

    sheet_id = fields.Many2one(
        'ksw.commission.sheet', required=True, ondelete='cascade',
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
        help='Required when the category is "Holiday Bonus". Also '
             'enforces unique (sheet, category, holiday) so the same '
             'holiday cannot be entered twice on one sheet.',
    )

    # ------------------------------------------------------------------
    # Quantity-based amount (mirrors of the category configuration)
    # ------------------------------------------------------------------
    is_quantity_based = fields.Boolean(
        related='category_id.is_quantity_based',
        store=True, readonly=True,
        help='Mirrored from the category. Drives readonly on Amount '
             'and shows the Quantity column.',
    )
    quantity_label = fields.Char(
        related='category_id.quantity_label', readonly=True,
    )
    min_quantity = fields.Float(
        related='category_id.min_quantity', readonly=True,
    )
    max_quantity = fields.Float(
        related='category_id.max_quantity', readonly=True,
    )
    quantity = fields.Float(
        default=0.0,
        help='Used when the category is Quantity-Based. The line '
             'amount is computed by the category formula from this '
             'quantity (e.g. Fridays = quantity × 100 SAR).',
    )

    # Stored, writable computed amount: when the category is
    # quantity-based, the formula recomputes amount from quantity; when
    # it isn't, the user types the amount directly and the compute is
    # a no-op (returns the existing value).
    amount = fields.Monetary(
        required=True, default=0.0,
        compute='_compute_amount', store=True, readonly=False,
    )
    description = fields.Char()
    currency_id = fields.Many2one(
        related='sheet_id.currency_id', store=True, readonly=True,
    )

    _unique_holiday_per_sheet = models.Constraint(
        'UNIQUE(sheet_id, category_id, holiday_id)',
        'A given holiday can only be entered once per sheet under '
        'the same category.',
    )

    # ------------------------------------------------------------------
    # Compute & validation
    # ------------------------------------------------------------------
    @api.depends('quantity', 'category_id',
                 'category_id.is_quantity_based',
                 'category_id.formula')
    def _compute_amount(self):
        """Recompute amount from the category formula when the
        category is quantity-based; otherwise leave the user-entered
        amount untouched.
        """
        for rec in self:
            cat = rec.category_id
            if cat and cat.is_quantity_based:
                rec.amount = cat._eval_formula(rec.quantity)
            else:
                # Preserve any value the user typed; new records start
                # at 0.0 via the default.
                rec.amount = rec.amount or 0.0

    @api.constrains('kind', 'holiday_id')
    def _check_holiday_required(self):
        for rec in self:
            if rec.kind == 'holiday_bonus' and not rec.holiday_id:
                raise ValidationError(_(
                    "Holiday-bonus lines must specify which holiday "
                    "(Foundation Day, National Day, Eid Al-Fitr, "
                    "Eid Al-Adha)."
                ))
            if rec.kind != 'holiday_bonus' and rec.holiday_id:
                raise ValidationError(_(
                    "Only Holiday-Bonus lines can carry a holiday "
                    "selector."))

    @api.onchange('quantity')
    def _onchange_quantity(self):
        for rec in self:
            if not rec.is_quantity_based:
                continue
            if rec.quantity < 0:
                return {
                    'warning': {
                        'title': _('Invalid Quantity'),
                        'message': _(
                            "Quantity on '%(c)s' cannot be negative.",
                            c=rec.category_id.name or '',
                        ),
                    }
                }
            if rec.min_quantity and rec.quantity < rec.min_quantity:
                return {
                    'warning': {
                        'title': _('Quantity Too Low'),
                        'message': _(
                            "Quantity on '%(c)s' (%(q)s) is below the "
                            "minimum (%(mn)s) configured on the category.",
                            c=rec.category_id.name or '',
                            q=rec.quantity, mn=rec.min_quantity,
                        ),
                    }
                }
            if rec.max_quantity and rec.quantity > rec.max_quantity:
                return {
                    'warning': {
                        'title': _('Quantity Too High'),
                        'message': _(
                            "Quantity on '%(c)s' (%(q)s) exceeds the "
                            "maximum (%(mx)s) configured on the category.",
                            c=rec.category_id.name or '',
                            q=rec.quantity, mx=rec.max_quantity,
                        ),
                    }
                }

    @api.constrains('quantity', 'is_quantity_based',
                    'min_quantity', 'max_quantity')
    def _check_quantity_bounds(self):
        for rec in self:
            if not rec.is_quantity_based:
                continue
            if rec.quantity < 0:
                raise ValidationError(_(
                    "Quantity on '%(c)s' cannot be negative.",
                    c=rec.category_id.name or '',
                ))
            if rec.min_quantity and rec.quantity < rec.min_quantity:
                raise ValidationError(_(
                    "Quantity on '%(c)s' (%(q)s) is below the minimum "
                    "(%(mn)s) configured on the category.",
                    c=rec.category_id.name or '',
                    q=rec.quantity, mn=rec.min_quantity,
                ))
            if rec.max_quantity and rec.quantity > rec.max_quantity:
                raise ValidationError(_(
                    "Quantity on '%(c)s' (%(q)s) exceeds the maximum "
                    "(%(mx)s) configured on the category.",
                    c=rec.category_id.name or '',
                    q=rec.quantity, mx=rec.max_quantity,
                ))
