from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class ResBankSEBBANClearRange(models.Model):
    _name = 'se.bban.clear.range'
    _description = 'Swedish BBAN Clearing Number Range'

    min_num = fields.Integer(
        string='Min Number',
        required=True,
        help='The minimum number for the BBAN clearing number range.'
    )
    max_num = fields.Integer(
        string='Max Number',
        required=True,
        help='The maximum number for the BBAN clearing number range.'
    )
    name = fields.Char(
        string='Name',
        required=True,
        help='The name of the BBAN clearing number range.'
    )
    checksum = fields.Selection(
        [
            ('mod11_10_digits', 'Modulus 11, 10 digits (Type 1)'),
            ('mod11_11_digits', 'Modulus 11, 11 digits (Type 1)'),
            ('mod10_max_10_digits', 'Modulus 10, up to 10 digits (Type 2)'),
            ('mod10_max_10_digits_5', 'Modulus 10, up to 10 digits, 5 digits clearing number (Type 2)'),
            ('mod10_10_digits', 'Modulus 10, 10 digits (Type 2)'),
            ('mod11_9_digits', 'Modulus 11, 9 digits (Type 2)'),
            ('mod11_8_9_digits', 'Modulus 11, 8 or 9 digits (Type 2)'),
        ],
        string='Checksum Method',
        required=True,
        help='The checksum method used for the BBAN clearing number.'
    )

    @api.constrains('min_num', 'max_num')
    def _check_max_min_num(self):
        for range in self:
            if range.min_num > range.max_num:
                raise ValidationError(_('Maximum clearing number needs to be equal or bigger than Minimum number.'))
            if range.min_num < 1000 or range.max_num > 9999:
                raise ValidationError(_('Range must be between 1000 and 9999.'))
            overlapping_ranges = self.search(
                expression.AND([
                    [('id', '!=', range.id)],
                    expression.OR([
                        [('min_num', '<=', range.min_num), ('max_num', '>=', range.min_num)],
                        [('min_num', '<=', range.max_num), ('max_num', '>=', range.max_num)],
                        [('min_num', '>=', range.min_num), ('max_num', '<=', range.max_num)],
                    ])
                ]),
            )
            if overlapping_ranges:
                raise ValidationError(_(
                    'Clearing number range is overlapping the following range(s) :\n%s',
                    '\n'.join(overlapping_ranges.mapped('name'))
                ))
