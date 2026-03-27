# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class IrConfigParameter(models.Model):

    _inherit = 'ir.config_parameter'

    def write(self, vals):
        ''' When this paramater is changed, dynamic fields needs to be recomputed '''
        param = self.filtered(lambda x: x.key == 'analytic.project_plan')
        if not param:
            return super().write(vals)
        old_plan_id = param.value
        new_plan_id = vals.get('value')
        if not (
            new_plan_id
            and str(new_plan_id).isnumeric()
            and (plan := self.env['account.analytic.plan'].browse(int(new_plan_id)))
            and (plan_field := plan._find_plan_column())
        ):
            raise UserError(_('The value for %s must be the ID to a valid analytic plan that is not a subplan', param.key))
        res = super().write(vals)
        self.env['account.analytic.plan'].browse(int(old_plan_id))._sync_all_plan_column()
        plan_field.unlink()
        return res
