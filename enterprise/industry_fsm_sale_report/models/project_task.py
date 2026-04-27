# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class Task(models.Model):
    _inherit = "project.task"

    @api.depends(
        'allow_worksheets', 'allow_material', 'timer_start', 'worksheet_signature',
        'display_satisfied_conditions_count', 'display_enabled_conditions_count'
    )
    def _compute_display_sign_report_buttons(self):
        for task in self:
            sign_p, sign_s = True, True
            if (
                not (task.allow_worksheets or task.allow_material)
                or task.timer_start
                or task.worksheet_signature
                or not task.display_satisfied_conditions_count
            ):
                sign_p, sign_s = False, False
            else:
                if task.display_enabled_conditions_count == task.display_satisfied_conditions_count:
                    sign_s = False
                else:
                    sign_p = False
            task.update({
                'display_sign_report_primary': sign_p,
                'display_sign_report_secondary': sign_s,
            })

    @api.depends(
        'allow_worksheets', 'allow_material', 'timer_start',
        'display_satisfied_conditions_count', 'display_enabled_conditions_count', 'fsm_is_sent'
    )
    def _compute_display_send_report_buttons(self):
        for task in self:
            send_p, send_s = True, True
            if (
                not (task.allow_worksheets or task.allow_material)
                or task.timer_start
                or not task.display_satisfied_conditions_count
                or task.fsm_is_sent
            ):
                send_p, send_s = False, False
            else:
                if task.display_enabled_conditions_count == task.display_satisfied_conditions_count:
                    send_s = False
                else:
                    send_p = False
            task.update({
                'display_send_report_primary': send_p,
                'display_send_report_secondary': send_s,
            })
