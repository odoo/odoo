# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions, models, _


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    def write(self, values):
        if 'res_model' in values:
            modified = False
            if values['res_model'] != 'hr.leave':
                approval = self.env.ref('mail.mail_act_leave_approval', raise_if_not_found=False)
                second = self.env.ref('mail.mail_act_leave_second_approval', raise_if_not_found=False)
                modified = (
                    (approval or self.env['mail.activity.type']) +
                    (second or self.env['mail.activity.type'])
                ) & self
            if values['res_model'] != 'hr.leave.allocation':
                allocation = self.env.ref('mail.mail_act_leave_allocation_approval', raise_if_not_found=False)
                modified = allocation and allocation in self
            if modified:
                raise exceptions.UserError(
                    _('You cannot modify %(activities_name)s target model as it is required for Time Off.',
                      activities_name=', '.join(act.name for act in modified),
                ))
        return super().write(values)
