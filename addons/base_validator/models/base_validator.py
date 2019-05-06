# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.tools.safe_eval import safe_eval
import re


class BaseValidator(models.Model):

    _name = "base.validator"
    _description = "Base Validator"

    def _default_validation_code(self):
        return _(
            "\n# Python code. Use:\n"
            "#  -  failed = True: specify that the value is not "
            "valid.\n"
            "#  -  value = 'something': overwrite value"
            " value (for formatting for eg.).\n"
            "#  -  parts = ['part_one', 'part_two']: parts of the value "
            "parsed by the validator.\n"
            "# You can use the following:\n"
            "#  - re: regex Python library\n"
            "#  - self: browse_record of the current document type "
            "browse_record\n"
            "#  - value: string with the value to validate"
        )

    name = fields.Char(
        required=True
    )
    validation_code = fields.Text(
        'Validation code',
        help="Python code called to validate and format a document number.",
        required=True,
        default=_default_validation_code
    )
    help_message = fields.Text(
    )
    input_test_string = fields.Char(
    )
    output_test_string = fields.Char(
        compute='_compute_output_test_string',
    )

    @api.multi
    def _validation_eval_context(self, value):
        self.ensure_one()
        return {'self': self,
                'value': value,
                're': re,
                }

    @api.multi
    def validate_value(self, value, do_not_raise=False, return_parts=False):
        """Validate the given ID number
        The method raises an odoo.exceptions.ValidationError if the eval of
        python validation code fails
        If you call with return_parts=True, then we will return the parts list
        """
        # if we call it without any record, we return value
        if not self:
            return value
        self.ensure_one()
        self = self.sudo()
        eval_context = self._validation_eval_context(value)
        msg = None

        if return_parts:
            key = 'parts'
        else:
            key = 'value'

        try:
            safe_eval(self.validation_code,
                      eval_context,
                      mode='exec',
                      nocopy=True)
        except Exception as e:
            msg = (_(
                'Error when evaluating %s. Please check validation code.\n'
                'Error:\n%s') % (self.name, e))
        if eval_context.get('failed', False):
            msg = (_(
                "'%s' is not a valid value for '%s'.\n%s") % (
                value, self.name, self.help_message or ''))
        elif eval_context.get(key, False):
            value = eval_context.get(key, False)
        if msg:
            if do_not_raise:
                return msg
            else:
                raise ValidationError(msg)
        return value
        # return {
        #     key: value, 'message': message, 'failed': failed,

    @api.depends(
        'validation_code',
        'input_test_string',
    )
    def _compute_output_test_string(self):
        for rec in self:
            rec.output_test_string = rec.validate_value(
                rec.input_test_string, True)
