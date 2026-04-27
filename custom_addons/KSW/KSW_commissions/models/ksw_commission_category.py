from odoo import _, api, fields, models
from odoo.exceptions import UserError


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

    _unique_code = models.Constraint(
        'UNIQUE(code)',
        'Category code must be unique.',
    )

    def unlink(self):
        for rec in self:
            if rec.is_system and not self.env.su:
                raise UserError(_(
                    "Category '%(name)s' is a system category and cannot "
                    "be deleted. Archive it instead.",
                    name=rec.name or rec.code,
                ))
        return super().unlink()

