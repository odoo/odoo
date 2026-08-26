# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

CODE_LENGTH = 5


class PosUniqueCode(models.Model):
    _name = 'pos.unique.code'
    _description = "Point of Sale Order Code"
    _order = 'is_used, unique_code'

    unique_code = fields.Char(
        string="Code",
        required=True,
        size=CODE_LENGTH,
        index=True,
        help="The digits a customer types to confirm an order. Each code works only once.",
    )
    is_used = fields.Boolean(
        string="Used",
        default=False,
        help="Ticked as soon as an order has been confirmed with this code.",
    )

    _unique_code_uniq = models.Constraint(
        'unique (unique_code)',
        "This code already exists. Please pick another one.",
    )

    @api.constrains('unique_code')
    def _check_unique_code(self):
        for record in self:
            code = record.unique_code or ''
            if len(code) != CODE_LENGTH or not code.isdigit():
                raise ValidationError(
                    _("An order code must be exactly %s digits, without letters or spaces.", CODE_LENGTH)
                )

    @api.model
    def consume_code(self, code):
        """Mark the given code as used, if it exists and is still free.

        The flag is flipped with a single conditional UPDATE so that two devices
        submitting the same code at the same time cannot both consume it.

        :return: ``{'success': bool, 'message': str}``
        """
        code = (code or '').strip()
        record = self.sudo().search([('unique_code', '=', code)], limit=1)
        if not record:
            return {'success': False, 'message': _("This code doesn't exist. Please check it and try again.")}

        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE pos_unique_code SET is_used = TRUE WHERE id = %s AND is_used = FALSE RETURNING id",
            [record.id],
        )
        if not self.env.cr.fetchone():
            return {'success': False, 'message': _("This code has already been used. Please use another one.")}

        record.invalidate_recordset(['is_used'])
        return {'success': True, 'message': _("Code accepted.")}
