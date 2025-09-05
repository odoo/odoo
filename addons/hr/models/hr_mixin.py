# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

from .hr_employee import _ALLOW_READ_HR_EMPLOYEE


class HrMixin(models.AbstractModel):
    _name = _description = 'hr.mixin'

    # Those overrides deal with many2many fields to comodel 'hr.employee'. In
    # the past, one could assign such a many2many field without having any
    # access to its comodel. Since Odoo 19, one must have read access to the
    # comodel to modify the relation. The hack consists in passing a special
    # value in the context, and pretend 'hr.employee' records to be readable
    # when that value is present.

    @api.model_create_multi
    def create(self, vals_list):
        special_self = self.with_context(_allow_read_hr_employee=_ALLOW_READ_HR_EMPLOYEE)
        records = super(HrMixin, special_self).create(vals_list)
        return records.with_env(self.env)

    def write(self, vals):
        special_self = self.with_context(_allow_read_hr_employee=_ALLOW_READ_HR_EMPLOYEE)
        return super(HrMixin, special_self).write(vals)
