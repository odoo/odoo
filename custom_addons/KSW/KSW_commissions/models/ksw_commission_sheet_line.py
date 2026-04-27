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
    amount = fields.Monetary(required=True, default=0.0)
    description = fields.Char()
    currency_id = fields.Many2one(
        related='sheet_id.currency_id', store=True, readonly=True,
    )

    # Holiday-uniqueness constraint. Includes ``sheet_id`` and
    # ``category_id``; ``holiday_id`` is NULL for non-holiday lines.
    # Postgres treats NULL as distinct, so non-holiday duplicates
    # (e.g. multiple "Other" lines) are still allowed — that matches
    # the agreed behaviour in the planning round.
    _unique_holiday_per_sheet = models.Constraint(
        'UNIQUE(sheet_id, category_id, holiday_id)',
        'A given holiday can only be entered once per sheet under '
        'the same category.',
    )

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

